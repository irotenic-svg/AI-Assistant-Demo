import requests, json

resp = requests.post('http://localhost:5000/api/chat',
    json={'question': '感冒和流感有什么区别？', 'session_id': 'python_test'})
data = resp.json()
print('=== ANSWER ===')
print(data['answer'][:300])
print()
print('=== SOURCES ===')
for src in data['sources'][:3]:
    print(f"[{src['source']}] {src['content'][:120]}")
