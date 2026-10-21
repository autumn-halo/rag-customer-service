"""预热答案缓存：把场景 B 的问题各问一遍（此后所有人问同样问题都秒回）。

用法：python scripts/loadtest/warm_cache.py [--host http://localhost:8000]
"""
import argparse
import json
import sys

import httpx

CACHED_QUESTIONS = [
    "你们的退货政策是怎样的？",
    "无线蓝牙耳机 Pro 续航多久？",
    "支持分期付款吗？",
    "发货要多久？",
    "怎么修改收货地址？",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    args = parser.parse_args()

    resp = httpx.post(
        f"{args.host}/api/auth/login",
        json={"username": "loaduser001", "password": "loadtest123"},
        timeout=15,
    )
    if resp.status_code != 200:
        sys.exit(f"登录失败：{resp.text[:100]}\n请先运行 prepare_users.py")
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    for q in CACHED_QUESTIONS:
        with httpx.stream(
            "POST",
            f"{args.host}/api/chat/stream",
            json={"message": q},
            headers=headers,
            timeout=180,
        ) as resp:
            # 消费完整流，确保答案已写入缓存
            for _ in resp.iter_lines():
                pass
        print(f"  已预热：{q}")

    print("缓存预热完成（缓存有效期 1 小时，场景 B 请在 1 小时内运行）")


if __name__ == "__main__":
    main()
