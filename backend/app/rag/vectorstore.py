"""Chroma 向量库封装：初始化、写入、按文档删除、相似检索。

嵌入式模式：Chroma 跟随进程一起运行，数据持久化在本地目录，
单机可跑；语料超 10 万块时可换 Chroma server 模式（接口已隔离在本模块）。
"""
import chromadb
from langchain_chroma import Chroma

from app.config import settings
from app.models.chunk import Chunk
from app.rag.embeddings import get_embeddings

_vectorstore: Chroma | None = None


def get_vectorstore() -> Chroma:
    """嵌入式 Chroma 单例（单进程应用内共享，多进程部署需换 server 模式）。"""
    global _vectorstore
    if _vectorstore is None:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        _vectorstore = Chroma(
            client=client,
            embedding_function=get_embeddings(),
            collection_name="knowledge_base",
        )
    return _vectorstore


def add_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """写入一批块（向量已在上游批量生成好，这里只负责入库）。"""
    get_vectorstore().add_texts(
        texts=[c.content for c in chunks],
        ids=[c.chroma_id for c in chunks],
        metadatas=[
            {"document_id": c.document_id, "chunk_id": c.id, **(c.meta or {})} for c in chunks
        ],
        embeddings=embeddings,
    )


def delete_document(document_id: int) -> None:
    """按文档删除全部向量（chroma_id 命名规则 + metadata 双保险）。"""
    get_vectorstore().delete(where={"document_id": document_id})


def search(query: str, top_k: int) -> list[dict]:
    """向量相似检索，返回统一格式的命中列表。"""
    results = get_vectorstore().similarity_search_with_score(query, k=top_k)
    return [
        {
            "chunk_id": doc.metadata.get("chunk_id"),
            "chroma_id": doc.id,
            "content": doc.page_content,
            "document_id": doc.metadata.get("document_id"),
            "score": float(score),
            "metadata": dict(doc.metadata),
        }
        for doc, score in results
    ]
