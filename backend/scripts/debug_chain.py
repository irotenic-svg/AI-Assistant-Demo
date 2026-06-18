"""
Chain 层调试脚本 v3 - 聚焦问题
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["HF_HUB_OFFLINE"] = "1"

from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings
from assistant.vectorstore import VectorStoreManager
from assistant.llm import create_llm
from assistant.prompts import create_rag_prompt
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough

settings = load_settings()

print("加载模型...")
embedding = BGEM3Embeddings(model_name=settings.embedding_model, device=settings.embedding_device)
vs = VectorStoreManager(persist_dir=settings.chroma_dir, embedding=embedding)
retriever = vs.as_retriever(search_kwargs={"k": 5})

query = "感冒和流感有什么区别？"

# ── 测试：create_retrieval_chain + chat_history=[] ──
print("\n" + "=" * 60)
print("测试: create_retrieval_chain with chat_history=[]")
print("=" * 60)

llm = create_llm(settings)
rag_prompt = create_rag_prompt()
qa_chain = create_stuff_documents_chain(llm, rag_prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

# 这应该能正常工作了
result = rag_chain.invoke({"input": query, "chat_history": []})
print(f"  Answer: {result.get('answer', 'N/A')[:300]}")
print(f"  Context docs: {len(result.get('context', []))}")
for i, doc in enumerate(result.get('context', [])[:5]):
    content_preview = doc.page_content[:150].replace('\n', ' ')
    print(f"  #{i+1} [{doc.metadata.get('source','?')}] {content_preview}...")

# ── 测试：直接在 chain 中插入调试 ──
print("\n" + "=" * 60)
print("测试: 手动模拟 chain 的检索步骤")
print("=" * 60)

# 这是 create_retrieval_chain 内部对 retriever 的调用方式:
# retrieval_docs = (lambda x: x["input"]) | retriever
retrieval_step = (lambda x: x["input"]) | retriever
docs = retrieval_step.invoke({"input": query, "chat_history": []})
print(f"  检索到 {len(docs)} 个文档:")
for i, doc in enumerate(docs):
    print(f"  #{i+1} [{doc.metadata.get('source','?')}] {doc.page_content[:120]}...")

# ── 测试：RunnableWithMessageHistory ──
print("\n" + "=" * 60)
print("测试: RunnableWithMessageHistory 完整流程")
print("=" * 60)

store = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

conv_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)

result2 = conv_chain.invoke(
    {"input": query},
    config={"configurable": {"session_id": "final_test"}},
)
print(f"  Answer: {result2.get('answer', 'N/A')[:300]}")
print(f"  Context docs: {len(result2.get('context', []))}")
for i, doc in enumerate(result2.get('context', [])[:5]):
    content_preview = doc.page_content[:150].replace('\n', ' ')
    print(f"  #{i+1} [{doc.metadata.get('source','?')}] {content_preview}...")

# ── 用和 Flask app.py 完全相同的方式测试 ──
print("\n" + "=" * 60)
print("测试: 完全模拟 Flask RAGChain.ask() 流程")
print("=" * 60)
from assistant.chain import RAGChain

rag = RAGChain(settings)
rag.initialize(vs)

result3 = rag.ask(query, session_id="simulated_flask")
print(f"  Answer: {result3.get('answer', 'N/A')[:300]}")
print(f"  Sources: {len(result3.get('sources', []))}")
for i, src in enumerate(result3.get('sources', [])[:5]):
    print(f"  #{i+1} [{src.get('source','?')}] {src.get('content','')[:120]}...")
