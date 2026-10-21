"""提示词模板单元测试：资料块拼装、上下文预算、历史格式化。"""
from app.rag import prompt


def _ref(index: int, content: str) -> dict:
    return {
        "index": index,
        "chunk_id": index,
        "document_id": 1,
        "document_title": f"文档{index}.pdf",
        "score": 0.9,
        "content": content,
    }


def test_context_block_numbering():
    refs = [_ref(1, "内容一"), _ref(2, "内容二")]
    block = prompt.build_context_block(refs)
    assert "[1]《文档1.pdf》\n内容一" in block
    assert "[2]《文档2.pdf》\n内容二" in block


def test_build_user_prompt_without_references():
    text = prompt.build_user_prompt([], "", "你好")
    assert "【参考资料】\n（无）" in text
    assert "【用户问题】\n你好" in text
    assert "【对话历史】" not in text


def test_build_user_prompt_with_history():
    refs = [_ref(1, "资料内容")]
    text = prompt.build_user_prompt(refs, "用户：之前问过什么\n助手：回答过了", "新问题")
    assert "【参考资料】" in text and "【对话历史】" in text and "【用户问题】" in text


def test_fit_context_drops_oldest_first():
    refs = [_ref(1, "短"), _ref(2, "x" * 100), _ref(3, "y" * 100)]
    fitted = prompt.fit_context(refs, max_chars=150)
    assert [r["index"] for r in fitted] == [1, 2]  # 编号最大的（最旧）先被丢弃


def test_fit_context_keeps_one():
    refs = [_ref(1, "z" * 5000)]
    assert len(prompt.fit_context(refs, max_chars=100)) == 1  # 至少保留一条


def test_format_history_speakers():
    text = prompt.format_history(
        [{"role": "user", "content": "问"}, {"role": "assistant", "content": "答"}]
    )
    assert text == "用户：问\n助手：答"
