"""测试用假向量化：MD5 哈希词袋向量。

- 零 API 消耗、确定性（同一段文字在任何机器上得到相同向量）
- 相同词越多余弦相似度越高，语义可预期
"""
import hashlib

import jieba
from langchain_core.embeddings import Embeddings

DIM = 256


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        vec = [0.0] * DIM
        vec[0] += 1.0  # 哨兵分量：保证向量非零，避免余弦相似度出现零向量边界
        for token in jieba.cut_for_search(text):
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % DIM
            vec[idx] += 1.0
        return vec
