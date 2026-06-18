import requests, json

tests = [
    ("今天天气怎么样？", "test_a"),
    ("帮我写一首诗", "test_b"),
    ("中国首都是哪里？", "test_c"),
    ("糖尿病的常见症状有哪些？", "test_d"),  # control: medical
]

for q, sid in tests:
    r = requests.post('http://localhost:5000/api/chat',
        json={'question': q, 'session_id': sid})
    d = r.json()
    print(f"=== Query: {q}")
    print(f"Answer: {d['answer'][:200]}")
    print(f"Sources: {len(d['sources'])}")
    for s in d['sources'][:3]:
        print(f"  [{s['source']}] {s['content'][:120]}")
    print()
