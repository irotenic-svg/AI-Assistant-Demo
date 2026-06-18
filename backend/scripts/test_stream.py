"""测试流式 SSE 端点 - 完整统计版"""
import requests, json, time

t0 = time.time()
r = requests.post(
    "http://localhost:5000/api/chat/stream",
    json={"question": "高血压患者饮食需要注意什么？"},
    stream=True, timeout=90,
)

events = []; token_count = 0; first_token_at = None

for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith("data: "):
        evt = json.loads(line[6:])
        t = evt["type"]; elapsed = time.time() - t0; events.append(t)
        if t == "token":
            token_count += 1
            if first_token_at is None: first_token_at = elapsed
        elif t == "done": break
        elif t == "error":
            print(f"[{elapsed:.2f}s] ERROR: {evt['data'][:200]}"); break

total = time.time() - t0
print(f"model: deepseek-v4-flash | thinking: disabled")
print(f"sources -> {'thinking' if 'thinking' in events else 'NO thinking'} -> tokens({token_count}) -> done")
print(f"first source: {events[0] if events else 'N/A'} at ~{2:.1f}s")
print(f"first token: {first_token_at:.2f}s" if first_token_at else "no tokens")
print(f"total time: {total:.2f}s | tokens: {token_count} | {token_count/total:.0f} tok/s")
