"""
续建向量数据库 - 跳过已嵌入文档，从断点继续
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings


def main():
    settings = load_settings()
    data_dir = Path(settings.processed_data_dir)
    persist_dir = settings.chroma_dir

    # 加载预处理数据
    records = []
    with open(data_dir / "all_documents.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    print(f"Loaded {len(records)} records")

    # 切分文档
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
        keep_separator=True,
    )
    documents = []
    for record in records:
        content = record.get("content", "")
        metadata = record.get("metadata", {})
        doc_id = record.get("id", "")
        if not content or len(content.strip()) < 10:
            continue
        if len(content) <= 500:
            documents.append(Document(page_content=content, metadata={**metadata, "id": doc_id}))
        else:
            for i, chunk in enumerate(text_splitter.split_text(content)):
                if len(chunk.strip()) >= 10:
                    documents.append(Document(page_content=chunk, metadata={**metadata, "id": f"{doc_id}_chunk_{i}", "chunk_index": i}))
    print(f"Total chunks: {len(documents)}")

    # 加载嵌入模型
    print("Loading embedding model...")
    embedding = BGEM3Embeddings(model_name=settings.embedding_model, device=settings.embedding_device)

    # 加载已有 Chroma
    print("Loading existing vector store...")
    vectorstore = Chroma(
        collection_name="medical_knowledge",
        embedding_function=embedding,
        persist_directory=persist_dir,
    )
    existing_count = vectorstore._collection.count()
    print(f"Already embedded: {existing_count} documents")

    if existing_count >= len(documents):
        print("All documents already embedded!")
        return

    # 跳过已嵌入的，继续添加剩余
    remaining = documents[existing_count:]
    print(f"Remaining: {len(remaining)} documents")

    batch_size = 500
    total = len(remaining)

    for i in range(0, total, batch_size):
        batch = remaining[i : i + batch_size]
        batch_num = existing_count // batch_size + (i // batch_size) + 1
        total_batches = (existing_count + total - 1) // batch_size + 1
        print(f"Batch {batch_num}/{total_batches} ({len(batch)} docs)...")
        vectorstore.add_documents(batch)

    final_count = vectorstore._collection.count()
    print(f"\nDone! Total documents: {final_count}")


if __name__ == "__main__":
    main()
