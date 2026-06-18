"""拦截 HTTP 请求看实际发出的 JSON body"""
import sys, os, logging, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 开启 HTTP 调试日志
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("openai").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

from assistant.config import load_settings
from assistant.llm import create_llm

settings = load_settings()
print(f"Config: model={settings.llm_model}, thinking={settings.deepseek_thinking}")

llm = create_llm(settings)
print(f"LLM extra_body: {llm.extra_body}")
print(f"LLM reasoning_effort: {getattr(llm, 'reasoning_effort', 'NOT FOUND')}")

# 尝试一次调用并捕获请求
messages = [{"role": "user", "content": "Hi"}]
print("\nCalling LLM.stream()...")
try:
    for i, chunk in enumerate(llm.stream(messages)):
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        if content and content.strip():
            print(f"  chunk[{i}]: {content[:60]}")
            break
        if i > 5:
            print(f"  chunk[{i}]: empty")
            break
except Exception as e:
    print(f"ERROR: {e}")
