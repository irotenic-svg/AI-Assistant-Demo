"""绕过 Flask，直接测试 Chain 的 ask_stream"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Monkey-patch httpx
import httpx
_original_send = httpx.Client.send
def _patched_send(client, request, *args, **kwargs):
    try:
        body = json.loads(request.content)
        keys = ["model", "reasoning_effort", "reasoning", "thinking", "extra_body"]
        vals = {k: body[k] for k in keys if k in body}
        extra = {k: v for k, v in body.items() if k not in keys and k != "messages"}
        if extra: vals["EXTRA"] = extra
        print(f"  HTTP BODY: {vals}")
    except: pass
    return _original_send(client, request, *args, **kwargs)
httpx.Client.send = _patched_send

from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings
from assistant.vectorstore import VectorStoreManager
from assistant.chain import RAGChain

settings = load_settings()
print(f"Config: model={settings.llm_model}, thinking={settings.deepseek_thinking}, effort={settings.deepseek_reasoning_effort}")

# 初始化
embedding = BGEM3Embeddings(model_name=settings.embedding_model, device=settings.embedding_device)
vsm = VectorStoreManager(persist_dir=settings.chroma_dir, embedding=embedding)
chain = RAGChain(settings)
chain.initialize(vsm)

print(f"Chain LLM: reasoning_effort={chain._llm.reasoning_effort}, extra_body={chain._llm.extra_body}")

print("\nCalling chain.ask_stream()...")
events_seen = []
for event in chain.ask_stream("感冒了怎么办？", session_id="test"):
    events_seen.append(event["type"])
    if event["type"] == "error":
        print(f"  ERROR: {event['data'][:200]}")
        break
    elif event["type"] == "token" and len(events_seen) < 5:
        print(f"  TOKEN: {event['data'][:60]}")

print(f"Events: {events_seen[:8]}")
