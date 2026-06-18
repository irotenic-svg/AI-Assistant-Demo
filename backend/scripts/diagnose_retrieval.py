"""
检索质量诊断脚本 - 直接测试 Chroma 向量检索
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["HF_HUB_OFFLINE"] = "1"

from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings
from assistant.vectorstore import VectorStoreManager

settings = load_settings()

print("=" * 60)
print("  检索质量诊断")
print("=" * 60)

# 加载 embedding
print(f"\n[1] 加载 Embedding: {settings.embedding_model}")
embedding = BGEM3Embeddings(
    model_name=settings.embedding_model,
    device=settings.embedding_device,
)
print(f"    设备: {embedding.device}")

# 加载 VectorStore
print(f"\n[2] 加载 Chroma: {settings.chroma_dir}")
vs = VectorStoreManager(
    persist_dir=settings.chroma_dir,
    embedding=embedding,
    collection_name="medical_knowledge",
)

stats = vs.get_collection_stats()
print(f"    集合: {stats['name']}, 文档数: {stats['count']}")

# 测试查询
test_queries = [
    "感冒和流感有什么区别？",
    "糖尿病的常见症状有哪些？",
    "高血压患者饮食需要注意什么？",
]

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"  查询: {query}")
    print(f"{'='*60}")

    # 1. 带分数的搜索
    results_with_scores = vs.similarity_search_with_score(query, k=5)
    print(f"\n  [带分数搜索] 返回 {len(results_with_scores)} 条:")
    for i, (doc, score) in enumerate(results_with_scores):
        content_preview = doc.page_content[:150].replace('\n', ' ')
        source = doc.metadata.get('source', '?')
        question = doc.metadata.get('question', '')[:80]
        print(f"  #{i+1} [{source}] score={score:.4f}")
        if question:
            print(f"     问题: {question}")
        print(f"     内容: {content_preview}...")
        print()

    # 2. 不带分数的搜索
    results = vs.similarity_search(query, k=5)
    print(f"\n  [不带分数搜索] 返回 {len(results)} 条:")
    for i, doc in enumerate(results):
        content_preview = doc.page_content[:150].replace('\n', ' ')
        source = doc.metadata.get('source', '?')
        print(f"  #{i+1} [{source}] {content_preview}...")

print("\n" + "=" * 60)
print("  诊断完成")
print("=" * 60)
