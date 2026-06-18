"""
RAG Chain 模块 - 组装 LangChain RAG 执行链
集成: History-Aware Retriever + RAG Chain + Conversation Memory
支持流式输出 (Streaming SSE)
"""
import re
from typing import Dict, Any, List, Generator

from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.documents import Document
from langchain_core.runnables.history import RunnableWithMessageHistory

from .config import Settings
from .llm import create_llm
from .prompts import create_rag_prompt, create_contextualize_q_prompt
from .vectorstore import VectorStoreManager


# ── 语言检测 ──────────────────────────────────────

def detect_language(text: str) -> str:
    """
    检测文本主要语言。

    通过统计中文字符（CJK 统一表意文字）占比来判断，
    阈值 0.15：超过 15% 的字符为中文则判定为中文。

    Args:
        text: 待检测文本

    Returns:
        'zh' 或 'en'
    """
    if not text:
        return "en"
    chinese_chars = len(re.findall(r"[一-鿿]", text))
    # 计算非空白字符总数
    total = len(re.sub(r"\s", "", text))
    if total == 0:
        return "en"
    return "zh" if chinese_chars / total > 0.15 else "en"


# ── 语言感知检索器 ────────────────────────────────

class LanguageRerankingRetriever:
    """
    包装基础检索器，按语言匹配度重排序结果。

    检索 k*2 个结果后，将与查询同语言的文档优先排列，
    确保用户看到与问题语言一致的引用来源。
    """

    def __init__(self, base_retriever, top_k: int = 5):
        """
        Args:
            base_retriever: 基础 Chroma 检索器（k 需 >= top_k * 2）
            top_k: 最终返回的文档数
        """
        self._base = base_retriever
        self._top_k = top_k
        self._last_query_lang = "en"

    @property
    def last_query_language(self) -> str:
        """获取最近一次查询的语言"""
        return self._last_query_lang

    def invoke(self, query: str, **kwargs) -> List[Document]:
        """
        检索并重排序文档。

        Args:
            query: 查询文本
            **kwargs: 传递给基础检索器的额外参数

        Returns:
            重排序后的文档列表（最多 top_k 个）
        """
        docs = self._base.invoke(query, **kwargs)
        if not docs:
            return docs

        self._last_query_lang = detect_language(query)

        # 按语言分组，保持各组的原始检索顺序
        same_lang_docs = []
        other_lang_docs = []
        for doc in docs:
            doc_lang = detect_language(doc.page_content)
            if doc_lang == self._last_query_lang:
                same_lang_docs.append(doc)
            else:
                other_lang_docs.append(doc)

        # 同语言在前，其他在后，截取 top_k
        reranked = same_lang_docs + other_lang_docs
        return reranked[: self._top_k]


class RAGChain:
    """
    RAG 执行链管理器
    提供完整的 RAG 问答能力，支持多轮对话与流式输出
    """

    def __init__(self, settings: Settings):
        """
        初始化 RAG Chain

        Args:
            settings: 应用配置
        """
        self._settings = settings
        self._llm = create_llm(settings)
        self._retriever = None       # 存储 retriever 供流式使用
        self._stuff_chain = None     # 存储 stuff documents chain 供流式使用
        self._chain = None
        self._conversational_chain = None

        # 会话历史存储 (in-memory)
        self._store: Dict[str, BaseChatMessageHistory] = {}

    def initialize(self, vectorstore_manager: VectorStoreManager) -> None:
        """
        初始化 RAG Chain（需要向量存储就绪后调用）

        Args:
            vectorstore_manager: 向量存储管理器
        """
        # 基础检索器：检索 2 倍数量，供语言重排序筛选
        base_retriever = vectorstore_manager.as_retriever(
            search_kwargs={
                "k": self._settings.retrieval_top_k * 2,
                "score_threshold": self._settings.retrieval_score_threshold,
            }
        )
        # 包装为语言感知检索器：优先返回与问题同语言的文档
        self._retriever = LanguageRerankingRetriever(
            base_retriever, top_k=self._settings.retrieval_top_k
        )

        # Step 1: 文档组合链 — 将检索文档 + 问题 → 答案
        rag_prompt = create_rag_prompt()
        self._stuff_chain = create_stuff_documents_chain(self._llm, rag_prompt)

        # Step 2: RAG 链 — 检索 + 生成
        self._chain = create_retrieval_chain(
            self._retriever, self._stuff_chain
        )

        # Step 3: 包装为可管理对话历史的链
        self._conversational_chain = RunnableWithMessageHistory(
            self._chain,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """获取或创建会话历史"""
        if session_id not in self._store:
            self._store[session_id] = ChatMessageHistory()
        return self._store[session_id]

    # ── 提取来源文档 ──────────────────────────────────────

    @staticmethod
    def _extract_sources(docs) -> List[Dict[str, str]]:
        """从检索文档列表中提取去重来源"""
        sources = []
        seen = set()
        for doc in docs:
            content = (
                doc.page_content[:300] + "..."
                if len(doc.page_content) > 300
                else doc.page_content
            )
            key = content[:100]
            if key not in seen:
                seen.add(key)
                sources.append({
                    "content": content,
                    "source": doc.metadata.get("source", "未知来源"),
                    "question": doc.metadata.get("question", ""),
                })
        return sources

    # ── 非流式问答 ────────────────────────────────────────

    def ask(
        self, question: str, session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        向 RAG 链提问（非流式，返回完整结果）

        Args:
            question: 用户问题
            session_id: 会话 ID（用于多轮对话）

        Returns:
            包含 answer 和 sources 的字典
        """
        if self._conversational_chain is None:
            return {
                "answer": "系统未初始化，请先构建向量数据库。",
                "sources": [],
                "error": True,
            }

        try:
            result = self._conversational_chain.invoke(
                {"input": question},
                config={"configurable": {"session_id": session_id}},
            )

            sources = []
            if "context" in result:
                sources = self._extract_sources(result["context"])

            return {
                "answer": result.get("answer", "抱歉，无法生成回答。"),
                "sources": sources,
                "session_id": session_id,
            }

        except Exception as e:
            return {
                "answer": f"处理问题时出错: {str(e)}",
                "sources": [],
                "error": True,
                "session_id": session_id,
            }

    # ── 流式问答 ──────────────────────────────────────────

    def ask_stream(
        self, question: str, session_id: str = "default"
    ) -> Generator[Dict[str, Any], None, None]:
        """
        向 RAG 链提问（流式输出）

        按顺序 yield 以下类型的事件:
        - {"type": "sources", "data": [...]}     来源文档
        - {"type": "token",  "data": "..."}      逐 token 回答文本
        - {"type": "done"}                        流结束
        - {"type": "error", "data": "..."}       出错

        Args:
            question: 用户问题
            session_id: 会话 ID

        Yields:
            流式事件字典
        """
        if self._conversational_chain is None:
            yield {"type": "error", "data": "系统未初始化，请先构建向量数据库。"}
            return

        try:
            # ── 1. 检索文档 ──
            history = self._get_session_history(session_id)
            docs = self._retriever.invoke(question)

            yield {
                "type": "sources",
                "data": self._extract_sources(docs) if docs else [],
            }

            # ── 2. 格式化上下文 ──
            if docs:
                context_parts = []
                for i, doc in enumerate(docs):
                    src = doc.metadata.get("source", "未知")
                    context_parts.append(
                        f"[文献 {i+1} · {src}]\n{doc.page_content}"
                    )
                context_str = "\n\n---\n\n".join(context_parts)
            else:
                context_str = "无相关医学文献。"

            # ── 3. 构建 Prompt 并流式调用 LLM ──
            prompt = create_rag_prompt()
            messages = prompt.format_messages(
                context=context_str,
                chat_history=list(history.messages),
                input=question,
            )

            full_answer = ""
            thinking_emitted = False

            for chunk in self._llm.stream(messages):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)

                if not token:
                    # 空内容 = 模型正在推理 (DeepSeek V4 reasoning phase)
                    if not thinking_emitted:
                        thinking_emitted = True
                        yield {"type": "thinking"}
                    continue

                # 第一个非空 token 到达，开始流式输出
                full_answer += token
                yield {"type": "token", "data": token}

            # ── 4. 写入对话历史 ──
            history.add_user_message(question)
            history.add_ai_message(full_answer)

            yield {"type": "done"}

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {"type": "error", "data": str(e)}

    # ── 会话管理 ──────────────────────────────────────────

    def get_history(self, session_id: str = "default") -> List[Dict[str, str]]:
        """
        获取会话历史

        Args:
            session_id: 会话 ID

        Returns:
            消息历史列表 [{"role": "human"|"ai", "content": "..."}]
        """
        if session_id not in self._store:
            return []
        messages = []
        for msg in self._store[session_id].messages:
            role = "human" if msg.type == "human" else "ai"
            messages.append({"role": role, "content": msg.content})
        return messages

    def clear_history(self, session_id: str = "default") -> None:
        """
        清空会话历史

        Args:
            session_id: 会话 ID
        """
        if session_id in self._store:
            del self._store[session_id]

    @property
    def is_ready(self) -> bool:
        """检查 RAG Chain 是否已初始化"""
        return self._conversational_chain is not None
