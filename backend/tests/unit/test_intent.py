"""意图识别单元测试：商品咨询与闲聊的边界。"""
from app.rag.intent import is_product_question


def test_product_questions():
    product_qs = [
        "退货流程是什么",
        "发货要多久",
        "这个多少钱",
        "你们卖苹果手机吗",
        "支持七天无理由退换吗",
        "怎么联系人工客服",
        "有没有优惠券",
        "尺码表在哪看",
    ]
    for q in product_qs:
        assert is_product_question(q), f"应当识别为商品咨询: {q}"


def test_non_product_questions():
    chat_qs = [
        "你是什么大模型",
        "你好呀",
        "今天天气怎么样",
        "讲个笑话",
        "帮我写一首诗",
        "你会说英语吗",
    ]
    for q in chat_qs:
        assert not is_product_question(q), f"不应当识别为商品咨询: {q}"


def test_empty_question():
    assert not is_product_question("")
