"""测试用假大模型：按分片流式输出预设答案，全程零 API 消耗。

实现 LangChain 的 BaseChatModel 接口，可直接替换 get_chat_model()。
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class FakeChatModel(BaseChatModel):
    """每次调用按顺序弹出一个预设答案，分片流式吐出。"""

    answers: list[str] = ["这是测试回答，包含商品信息。"]
    chunk_size: int = 5

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _take_answer(self) -> str:
        return self.answers.pop(0) if self.answers else "这是测试回答。"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        generation = ChatGeneration(message=AIMessage(content=self._take_answer()))
        return ChatResult(generations=[generation])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        answer = self._take_answer()
        for i in range(0, len(answer), self.chunk_size):
            chunk = AIMessageChunk(content=answer[i : i + self.chunk_size])
            yield ChatGenerationChunk(message=chunk)
