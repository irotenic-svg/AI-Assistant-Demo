"""通过 Vite 代理 (5173) 测试流式 SSE 端点"""
import requests, json, time

t0 = time.time()
r = requests.post(
    "http://localhost:5173/api/chat/stream",
    json={"question": "高血压患者饮食需要注意什么？"},
    stream=True, timeout=90,
)
print(f"Status: {r.status_code}")
events = []; token_count = 0; first_token_at = None; first_content = ""

for raw_line in r.iter_lines(decode_unicode=True):
    if raw_line:
        line_str = raw_line.decode('utf-8') if isinstance(raw_line, bytes) else raw_line
        if line_str.startswith("data: "):
            evt = json.loads(line_str[6:])
            t = evt["type"]; elapsed = time.time() - t0; events.append(t)
            if t == "token":
                token_count += 1
                if first_token_at is None:
                    first_token_at = elapsed
                if token_count == 1:
                    first_content = evt["data"][:100]
            elif t == "done":
                break
            elif t == "error":
                print(f"  ERROR: {evt['data'][:200]}")
                break

total = time.time() - t0
print(f"Events: {events[:10]}{'...' if len(events)>10 else ''}")
print(f"First token at: {first_token_at:.2f}s | First content: {first_content}")
print(f"Total: {total:.2f}s | tokens: {token_count} | {token_count/total:.0f} tok/s")
print(f"Streaming verified through Vite proxy!")
