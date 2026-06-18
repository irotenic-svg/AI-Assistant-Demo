"""抓取 langchain-openai 发出的完整 HTTP 请求体"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Monkey-patch httpx Client.send BEFORE anything else
import httpx
_original_send = httpx.Client.send
_last_body = [None]

def _patched_send(client, request, *args, **kwargs):
    try:
        body = json.loads(request.content)
        _last_body[0] = body
        keys = ["model", "reasoning_effort", "reasoning", "thinking",
                "extra_body", "temperature", "max_tokens", "stream"]
        for k in keys:
            if k in body:
                print(f"  REQUEST[{k}]: {body[k]}")
        # Print ALL keys (especially unknown ones)
        extra = [k for k in body if k not in keys and not k.startswith("messages")]
        if extra:
            print(f"  REQUEST[extra_keys]: {extra}")
            for k in extra:
                print(f"    {k}: {body[k]}")
    except:
        pass
    return _original_send(client, request, *args, **kwargs)

httpx.Client.send = _patched_send

from assistant.config import load_settings
from assistant.llm import create_llm

settings = load_settings()
print(f"Config: model={settings.llm_model}, thinking={settings.deepseek_thinking}, effort={settings.deepseek_reasoning_effort}")

llm = create_llm(settings)
print(f"LLM: reasoning_effort={llm.reasoning_effort}, extra_body={llm.extra_body}")

print("\nSending test request...")
try:
    for chunk in llm.stream([{"role": "user", "content": "说一个字：好"}]):
        if chunk.content and chunk.content.strip():
            print(f"  Response: {chunk.content.strip()}")
            break
    print("OK")
except Exception as e:
    print(f"Error: {e}")

body = _last_body[0]
if body:
    body_str = json.dumps(body)
    if '"off"' in body_str:
        import re
        for m in re.finditer(r'"off"', body_str):
            start = max(0, m.start() - 40)
            end = min(len(body_str), m.end() + 40)
            print(f"  FOUND 'off' at pos {m.start()}: ...{body_str[start:end]}...")
    else:
        print("  No 'off' found in request body!")
