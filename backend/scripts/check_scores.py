import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['HF_HUB_OFFLINE'] = '1'
from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings
from assistant.vectorstore import VectorStoreManager

settings = load_settings()
print("Loading model...")
embedding = BGEM3Embeddings(model_name=settings.embedding_model, device=settings.embedding_device)
vs = VectorStoreManager(persist_dir=settings.chroma_dir, embedding=embedding)

queries = [
    ("Non-med: weather", "今天天气怎么样？"),
    ("Non-med: poetry", "帮我写一首诗"),
    ("Non-med: capital", "中国首都是哪里？"),
    ("Non-med: cooking", "红烧肉怎么做？"),
    ("Medical: diabetes", "糖尿病的常见症状有哪些？"),
    ("Medical: flu", "感冒和流感有什么区别？"),
    ("Medical: hypertension", "高血压患者饮食需要注意什么？"),
]

for label, q in queries:
    print(f"\n{'='*60}")
    print(f"  {label}: {q}")
    print(f"{'='*60}")
    results = vs.similarity_search_with_score(q, k=5)
    for i, (doc, score) in enumerate(results):
        src = doc.metadata.get('source', '?')
        content = doc.page_content[:100].replace('\n', ' ')
        print(f"  #{i+1} score={score:.4f} [{src}] {content}...")
