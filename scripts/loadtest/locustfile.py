"""100 用户并发压测脚本（Locust）。

三个场景（用 --tags 选择，单独运行）：
  scenario_a  登录 + 会话浏览 —— 零 API 消耗，测基础承载与数据库并发读
  scenario_b  聊天-缓存命中 —— 零 API 消耗，测系统自身吞吐上限
  scenario_c  聊天-真实大模型 —— 100 人各问 1 个独特问题，测端到端体验

自定义指标：chat_ttfb（流式回答首个字延迟，SSE 类型）

用法示例（backend 目录下）：
  .venv/Scripts/python -m locust -f ../scripts/loadtest/locustfile.py \\
      --host http://localhost:8000 --users 100 --spawn-rate 20 \\
      --tags scenario_b --run-time 3m --headless --only-summary \\
      --csv ../docs/loadtest-results/b
"""
import json
import random
import threading
import time

from locust import HttpUser, between, events, tag, task

USER_PASSWORD = "loadtest123"
USER_COUNT = 100

# 场景 B：预热后全部命中答案缓存（见 warm_cache.py）
CACHED_QUESTIONS = [
    "你们的退货政策是怎样的？",
    "无线蓝牙耳机 Pro 续航多久？",
    "支持分期付款吗？",
    "发货要多久？",
    "怎么修改收货地址？",
]

# 场景 C：题库按主题展开成 100+ 个不同措辞，保证每人一问不重复（不命中缓存）
_TOPIC_VARIANTS = {
    "退货": [
        "退货政策是怎样的", "退货有什么要求", "怎么申请退货", "退货需要什么条件",
        "退货流程是什么", "退货运费谁承担", "退货后多久退款", "哪些商品不能退货",
        "退货要保留吊牌吗", "退货后钱退到哪里",
    ],
    "发货": [
        "发货要多久", "什么时候发货", "物流用哪家快递", "偏远地区发货要几天",
        "怎么查物流单号", "发货后能改地址吗", "预售商品什么时候发", "发货会短信通知吗",
    ],
    "耳机": [
        "耳机续航多久", "耳机支持降噪吗", "耳机防水等级多少", "耳机怎么充电",
        "耳机保修多久", "耳机蓝牙版本是多少", "耳机能连两个设备吗", "耳机有几种颜色",
        "耳机充电十分钟能用多久", "耳机戴久了耳朵疼吗",
    ],
    "手表": [
        "手表续航多久", "手表支持NFC吗", "手表能测心率吗", "手表防水吗",
        "手表兼容苹果手机吗", "手表有几种运动模式", "手表屏幕多大", "手表能常亮显示吗",
    ],
    "保温杯": [
        "保温杯保温多久", "保温杯什么材质", "保温杯能进洗碗机吗", "保温杯容量多大",
        "保温杯保冷多久", "保温杯能装碳酸饮料吗",
    ],
    "支付": [
        "支持分期付款吗", "支持货到付款吗", "可以用微信支付吗", "支付失败怎么办",
        "订单多久不付会取消", "可以支付宝付款吗", "支持银联云闪付吗",
    ],
    "发票": [
        "怎么开发票", "能开专票吗", "发票多久能开好", "发票抬头能改吗",
        "电子发票怎么下载", "发票可以开商品明细吗",
    ],
    "优惠": [
        "有什么优惠活动", "会员有什么权益", "积分怎么用", "优惠券怎么领",
        "新人有什么礼包", "金卡会员有什么折扣", "积分会过期吗",
    ],
    "换货": [
        "怎么换货", "换货要多久", "尺码不合适能换吗", "换货运费谁出",
        "换货需要什么条件", "换货可以换其他商品吗",
    ],
    "售后": [
        "保修政策是什么", "耳机坏了怎么修", "质保期多久", "过了质保能修吗",
        "人为损坏保修吗", "维修要多久", "维修收费吗", "寄回检测要多久",
    ],
    "订单": [
        "怎么取消订单", "取消订单多久退款", "怎么修改收货地址", "订单在哪里查",
        "订单发货前能改地址吗", "怎么申请退款",
    ],
    "客服": [
        "客服工作时间是几点", "怎么联系人工客服", "客服电话是多少", "人工客服怎么找",
    ],
}

REAL_QUESTION_POOL = [
    variant if variant.endswith(("？", "吗")) else f"{variant}？"
    for variants in _TOPIC_VARIANTS.values()
    for variant in variants
]


class StressUser(HttpUser):
    wait_time = between(15, 30)  # 每个用户两次操作之间的思考时间

    _uid_counter = 0
    _uid_lock = threading.Lock()

    def on_start(self):
        # 压测用户已由 prepare_users.py 预注册，这里直接登录
        with self._uid_lock:
            StressUser._uid_counter += 1
            self.uid = StressUser._uid_counter
        username = f"loaduser{self.uid:03d}"
        resp = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": USER_PASSWORD},
            name="/api/auth/login",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"登录失败 {username}: {resp.text[:100]}")
        self.token = resp.json()["access_token"]
        self._real_done = False

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @task
    @tag("scenario_a")
    def browse(self):
        """浏览会话列表与历史消息。"""
        resp = self.client.get("/api/conversations", headers=self._auth())
        if resp.status_code == 200:
            convs = resp.json()
            if convs:
                cid = convs[0]["id"]
                self.client.get(f"/api/conversations/{cid}/messages", headers=self._auth())

    @task
    @tag("scenario_b")
    def cached_chat(self):
        """缓存命中的流式问答（先跑 warm_cache.py 预热）。"""
        question = random.choice(CACHED_QUESTIONS)
        self._stream_chat(question)

    @task
    @tag("scenario_c")
    def real_chat(self):
        """真实大模型问答：每人只问一次，问题互不重复。"""
        if self._real_done:
            return
        self._real_done = True
        question = REAL_QUESTION_POOL[(self.uid - 1) % len(REAL_QUESTION_POOL)]
        self._stream_chat(question)

    def _stream_chat(self, question: str) -> None:
        """流式问答：记录首个字延迟（chat_ttfb）自定义指标。"""
        start = time.perf_counter()
        first_token_at = None
        error = None
        try:
            with self.client.post(
                "/api/chat/stream",
                json={"message": question},
                headers=self._auth(),
                stream=True,
                timeout=120,
                catch_response=True,
            ) as resp:
                if resp.status_code != 200:
                    error = f"HTTP {resp.status_code}"
                for raw in resp.iter_lines():
                    if raw is None or first_token_at is not None:
                        continue
                    if raw.startswith(b"data: "):
                        try:
                            data = json.loads(raw[6:])
                            if data.get("content"):
                                first_token_at = time.perf_counter()
                        except (ValueError, KeyError):
                            pass
        except Exception as e:  # noqa: BLE001
            error = repr(e)
        end_at = time.perf_counter()
        # 完整流时长：请求发出到回答结束（含检索 + 生成 + 落库）
        events.request.fire(
            request_type="SSE",
            name="chat_total",
            response_time=(end_at - start) * 1000,
            response_length=0,
            exception=error,
        )
        if first_token_at is not None:
            ttfb_ms = (first_token_at - start) * 1000
            events.request.fire(
                request_type="SSE",
                name="chat_ttfb",
                response_time=ttfb_ms,
                response_length=0,
                exception=error,
            )
