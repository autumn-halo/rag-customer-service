"""测试用假重排：查询与文档的关键词重叠率计分。"""
import jieba

from app.rag.reranker import Reranker


class FakeReranker(Reranker):
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        q_tokens = set(jieba.cut_for_search(query))
        scored = []
        for i, doc in enumerate(documents):
            overlap = len(q_tokens & set(jieba.cut_for_search(doc)))
            score = round(overlap / max(len(q_tokens), 1), 4)
            scored.append((i, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
