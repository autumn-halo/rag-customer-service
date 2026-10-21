"""提示词模板：电商客服人设 + 强制引用格式约定。"""

# 带资料时的系统设定：严格依据资料作答、标注引用编号、不编造
SYSTEM_PROMPT_RAG = (
    "你是「XX商城」的智能客服助手。请严格依据【参考资料】回答用户问题，并遵守以下规则：\n"
    "1. 只能使用参考资料中的信息作答，禁止编造资料中不存在的内容。\n"
    "2. 引用资料时在句末标注来源编号，格式为 [1]、[2]。\n"
    '3. 若参考资料不足以回答，请如实说明"根据现有资料暂时无法解答"，'
    "并建议用户联系人工客服，不要猜测。\n"
    "4. 使用简体中文，语气亲切、专业、简洁。"
)

# 无资料时的系统设定：自由对话（寒暄、闲聊走这里）
SYSTEM_PROMPT_PLAIN = "你是「XX商城」的智能客服助手，请用简体中文亲切、专业地回答用户问题。"

# 检索到资料但相关度过低时的兜底话术（不调 LLM，省一次调用也防幻觉）
FALLBACK_ANSWER = "抱歉，根据现有资料暂时无法解答您的问题，建议您联系人工客服获取帮助。"


def build_context_block(references: list[dict]) -> str:
    """把引用片段拼成带编号和文档名的资料块，编号与 citations 数组一一对应。"""
    lines = [f"[{r['index']}]《{r['document_title']}》\n{r['content']}" for r in references]
    return "\n\n".join(lines)


def build_user_prompt(references: list[dict], history_text: str, question: str) -> str:
    """组装严格模式的用户消息：资料 + 对话历史 + 当前问题。"""
    parts = ["【参考资料】\n" + (build_context_block(references) if references else "（无）")]
    if history_text:
        parts.append(f"【对话历史】\n{history_text}")
    parts.append(f"【用户问题】\n{question}")
    return "\n\n".join(parts)


def build_plain_user_prompt(history_text: str, question: str) -> str:
    """组装自由对话模式的用户消息（不带参考资料区块）。"""
    parts = []
    if history_text:
        parts.append(f"【对话历史】\n{history_text}")
    parts.append(f"【用户问题】\n{question}")
    return "\n\n".join(parts)


def fit_context(references: list[dict], max_chars: int) -> list[dict]:
    """上下文预算控制：从最旧（编号最大）的引用开始丢弃，直到总字符数达标。"""
    while (
        len(references) > 1
        and sum(len(r["content"]) for r in references) > max_chars
    ):
        references = references[:-1]
    return references


def format_history(messages: list[dict]) -> str:
    """把消息列表转成提示词里的对话历史文本。"""
    lines = []
    for m in messages:
        speaker = "用户" if m["role"] == "user" else "助手"
        lines.append(f"{speaker}：{m['content']}")
    return "\n".join(lines)
