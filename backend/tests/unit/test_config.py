"""配置模块单元测试：默认值、派生路径、目录创建。"""
from pathlib import Path

from app.config import Settings, settings


def test_model_defaults():
    """大模型选型默认值：与 .env.example 保持一致。"""
    assert settings.model_chat == "qwen-plus"
    assert settings.model_embedding == "text-embedding-v3"
    assert settings.model_rerank == "qwen3-rerank"
    assert settings.embedding_dimensions == 1024


def test_cors_origin_list_parsing():
    s = Settings(cors_origins="http://a.com, http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_db_path_from_env():
    # conftest 已把 DATABASE_URL 指向临时库，settings 必须采用它
    assert settings.db_path.startswith("sqlite:///")


def test_db_path_fallback_when_env_empty():
    s = Settings(database_url="")
    assert s.db_path.startswith("sqlite:///")
    assert s.db_path.endswith("data/app.db")


def test_chroma_and_upload_fallback():
    s = Settings(chroma_dir="", upload_dir="")
    # Windows 路径用反斜杠，用 Path 对象比较以兼容两种格式
    assert Path(s.chroma_path).name == "chroma"
    assert s.upload_path.name == "uploads"


def test_ensure_runtime_dirs(tmp_path):
    s = Settings(
        database_url="",
        chroma_dir=str(tmp_path / "chroma"),
        upload_dir=str(tmp_path / "uploads"),
    )
    s.ensure_runtime_dirs()
    assert (tmp_path / "chroma").is_dir()
    assert (tmp_path / "uploads").is_dir()
    assert s.data_dir.is_dir()
