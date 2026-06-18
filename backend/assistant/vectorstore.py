"""
VectorStore 模块 - Chroma 向量数据库操作
"""
from typing import List, Dict, Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from .embeddings import BGEM3Embeddings


class VectorStoreManager:
    """
    Chroma 向量存储管理器
    负责创建、加载和管理向量集合
    """

    def __init__(
        self,
        persist_dir: str,
        embedding: BGEM3Embeddings,
        collection_name: str = "medical_knowledge",
    ):
        """
        初始化向量存储管理器

        Args:
            persist_dir: Chroma 持久化目录
            embedding: 嵌入模型实例
            collection_name: 集合名称
        """
        self._persist_dir = persist_dir
        self._embedding = embedding
        self._collection_name = collection_name
        self._vectorstore: Optional[Chroma] = None

    @property
    def vectorstore(self) -> Chroma:
        """获取或初始化向量存储"""
        if self._vectorstore is None:
            self._vectorstore = Chroma(
                collection_name=self._collection_name,
                embedding_function=self._embedding,
                persist_directory=self._persist_dir,
            )
        return self._vectorstore

    def add_documents(self, documents: List[Document]) -> None:
        """
        批量添加文档到向量存储

        Args:
            documents: LangChain Document 列表
        """
        self.vectorstore.add_documents(documents)

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """
        批量添加文本到向量存储

        Args:
            texts: 文本列表
            metadatas: 元数据列表
            ids: 文档 ID 列表
        """
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        """
        获取 LangChain Retriever

        Args:
            search_kwargs: 搜索参数 (如 {"k": 5, "score_threshold": 0.45})

        Returns:
            LangChain Retriever
        """
        if search_kwargs is None:
            search_kwargs = {"k": 5, "score_threshold": 0.45}
        return self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs,
        )

    def similarity_search(
        self, query: str, k: int = 5
    ) -> List[Document]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回文档数量

        Returns:
            相似文档列表
        """
        return self.vectorstore.similarity_search(query, k=k)

    def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> List[tuple]:
        """
        带分数的相似度搜索

        Args:
            query: 查询文本
            k: 返回文档数量

        Returns:
            (Document, score) 列表
        """
        return self.vectorstore.similarity_search_with_relevance_scores(query, k=k)

    def delete_collection(self) -> None:
        """删除当前集合"""
        if self._vectorstore is not None:
            self._vectorstore.delete_collection()
            self._vectorstore = None

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        collection = self.vectorstore._collection
        return {
            "name": collection.name,
            "count": collection.count(),
        }
