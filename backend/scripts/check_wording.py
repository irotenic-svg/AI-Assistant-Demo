"""检查 LLM 回答中是否仍有旧措辞"""
import requests, json

r = requests.post(
    "http://localhost:5000/api/chat/stream",
    json={"question": "鼻炎怎么治疗？"},
    stream=True, timeout=90,
)

content = ""
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith("data: "):
        evt = json.loads(line[6:])
        if evt["type"] == "token":
            content += evt["data"]
        elif evt["type"] == "done":
            break

# 检查旧措辞
old_phrases = ["根据您提供的上下文信息", "根据上下文信息", "上下文信息"]
print("=== LLM 回答 (前500字) ===")
print(content[:500])
print()
print("=== 措辞检查 ===")
found = False
for phrase in old_phrases:
    if phrase in content:
        print(f"WARNING: Found old phrase '{phrase}' in response!")
        found = True
if not found:
    print("OK: No old phrases found.")
