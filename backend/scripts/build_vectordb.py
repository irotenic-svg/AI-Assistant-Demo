"""
向量数据库构建脚本
加载预处理后的 JSONL 文档，切分、嵌入并存入 Chroma
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings
from assistant.vectorstore import VectorStoreManager


def load_documents(data_dir: Path) -> List[Dict[str, Any]]:
    """
    加载预处理后的 JSONL 文档

    Args:
        data_dir: 预处理数据目录

    Returns:
        文档记录列表
    """
    records = []
    jsonl_path = data_dir / "all_documents.jsonl"

    if not jsonl_path.exists():
        print(f"[Error] 预处理文件不存在: {jsonl_path}")
        print("请先运行: python scripts/preprocess_data.py")
        sys.exit(1)

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    print(f"加载了 {len(records)} 条预处理记录")
    return records


def chunk_documents(records: List[Dict[str, Any]]) -> List[Document]:
    """
    切分文档

    Args:
        records: 预处理记录列表

    Returns:
        LangChain Document 列表
    """
    # 中文友好的分隔符
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
        keep_separator=True,
    )

    documents = []
    skipped = 0

    for record in records:
        content = record.get("content", "")
        metadata = record.get("metadata", {})
        doc_id = record.get("id", "")

        if not content or len(content.strip()) < 10:
            skipped += 1
            continue

        # 短内容直接作为一个文档
        if len(content) <= 500:
            documents.append(
                Document(
                    page_content=content,
                    metadata={**metadata, "id": doc_id},
                )
            )
        else:
            # 长内容切分
            chunks = text_splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 10:
                    continue
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            **metadata,
                            "id": f"{doc_id}_chunk_{i}",
                            "chunk_index": i,
                        },
                    )
                )

    print(f"生成 {len(documents)} 个文档块 (跳过 {skipped} 条无效记录)")
    return documents


def build_vectorstore(
    documents: List[Document],
    settings,
    embedding: BGEM3Embeddings,
) -> None:
    """
    构建向量数据库

    Args:
        documents: 文档列表
        settings: 应用配置
        embedding: 嵌入模型
    """
    persist_dir = settings.chroma_dir

    print(f"\n开始构建向量数据库...")
    print(f"  持久化目录: {persist_dir}")
    print(f"  嵌入模型: {settings.embedding_model}")
    print(f"  设备: {settings.embedding_device}")
    print(f"  文档数量: {len(documents)}")

    # 确保目录存在
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    # 分批处理（避免一次嵌入太多导致 OOM）
    batch_size = 500
    total = len(documents)

    # 先创建第一批
    first_batch = documents[:batch_size]
    print(f"\n处理批次 1/{((total - 1) // batch_size) + 1} ({len(first_batch)} 文档)...")

    vectorstore = Chroma.from_documents(
        documents=first_batch,
        embedding=embedding,
        persist_directory=persist_dir,
        collection_name="medical_knowledge",
    )

    # 追加剩余批次
    for i in range(batch_size, total, batch_size):
        batch = documents[i : i + batch_size]
        batch_num = (i // batch_size) + 2
        print(f"处理批次 {batch_num}/{((total - 1) // batch_size) + 1} ({len(batch)} 文档)...")
        vectorstore.add_documents(batch)

    print(f"\n✓ 向量数据库构建完成！")
    print(f"  存储位置: {persist_dir}")


def main():
    """主流程"""
    print("=" * 60)
    print("  构建医疗知识向量数据库")
    print("=" * 60)

    # 加载配置
    settings = load_settings()
    data_dir = Path(settings.processed_data_dir)

    # 加载预处理数据
    print("\n[1/3] 加载预处理数据...")
    records = load_documents(data_dir)

    # 切分文档
    print("\n[2/3] 切分文档...")
    documents = chunk_documents(records)

    # 统计来源分布
    source_counts = {}
    for doc in documents:
        src = doc.metadata.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    print("  文档来源分布:")
    for src, count in source_counts.items():
        print(f"    - {src}: {count} 个块")

    # 初始化嵌入 & 构建向量库
    print("\n[3/3] 初始化嵌入模型并构建向量库...")
    print(f"  加载模型: {settings.embedding_model} (首次运行需下载)...")
    embedding = BGEM3Embeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )

    build_vectorstore(documents, settings, embedding)

    print(f"\n{'='*60}")
    print("  完成！现在可以启动 Flask 服务:")
    print("    python app.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
