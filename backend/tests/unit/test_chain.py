"""对话模型工厂单元测试：构造参数跟随配置。"""
from app.rag import chain


def test_get_chat_model_follows_settings(monkeypatch):
    monkeypatch.setattr(chain.settings, "model_chat", "qwen-turbo")
    monkeypatch.setattr(chain.settings, "dashscope_api_key", "sk-test-key")

    model = chain.get_chat_model()

    assert model.model_name == "qwen-turbo"
    assert model.openai_api_key.get_secret_value() == "sk-test-key"
    assert model.streaming is True
