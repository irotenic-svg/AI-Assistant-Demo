"""
RAG Chain 模块 - 组装 LangChain RAG 执行链
集成: History-Aware Retriever + RAG Chain + Conversation Memory
支持流式输出 (Streaming SSE)
"""
from typing import Dict, Any, List, Generator

from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from .config import Settings
from .llm import create_llm
from .prompts import create_rag_prompt, create_contextualize_q_prompt
from .vectorstore import VectorStoreManager


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
        self._retriever = vectorstore_manager.as_retriever(
            search_kwargs={
                "k": self._settings.retrieval_top_k,
                "score_threshold": self._settings.retrieval_score_threshold,
            }
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
