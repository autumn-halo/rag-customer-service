"""预注册 100 个压测用户（幂等，可重复执行）。

用法：python scripts/loadtest/prepare_users.py [--host http://localhost:8000] [--count 100]
"""
import argparse
import sys

import httpx

USER_PASSWORD = "loadtest123"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()

    created = skipped = failed = 0
    for i in range(1, args.count + 1):
        username = f"loaduser{i:03d}"
        resp = httpx.post(
            f"{args.host}/api/auth/register",
            json={"username": username, "password": USER_PASSWORD},
            timeout=15,
        )
        if resp.status_code == 200:
            created += 1
        elif resp.status_code == 400 and "已被注册" in resp.json().get("detail", ""):
            skipped += 1
        else:
            failed += 1
            print(f"  ❌ {username}: {resp.status_code} {resp.text[:100]}")
    print(f"完成：新注册 {created} 个，已存在跳过 {skipped} 个，失败 {failed} 个")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
