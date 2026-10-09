"""查询 llmtoken 额度余额，输出 `剩余/总额`。

数据来自 new-api 的 `/api/usage/token/`（token 维度，500000 quota = $1）。
tclaude 暂无可用的余额接口。

token 只从环境变量读取并放在请求头中，不会输出到终端或错误信息。
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

LLMTOKEN_BASE_URL = "https://qproxy.gtimg.com"
LLMTOKEN_TOKEN_ENV = "LLMTOKEN_API_KEY"
QUOTA_PER_USD = 500000
HTTP_TIMEOUT = 5


def fetch_llmtoken_balance(token: str) -> dict[str, float]:
    """返回 {"used", "available", "granted"}，单位美元；失败时抛出异常。"""
    req = urllib.request.Request(
        f"{LLMTOKEN_BASE_URL}/api/usage/token/",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        body = json.load(resp)
    if not body.get("code"):
        raise ValueError(body.get("message") or "接口返回失败")
    data = body["data"]
    return {
        "used": data["total_used"] / QUOTA_PER_USD,
        "available": data["total_available"] / QUOTA_PER_USD,
        "granted": data["total_granted"] / QUOTA_PER_USD,
    }


def short_balance() -> str | None:
    """`$136.10/$280.00`；无 token 或请求失败时返回 None。"""
    token = os.environ.get(LLMTOKEN_TOKEN_ENV)
    if not token:
        return None
    try:
        bal = fetch_llmtoken_balance(token)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return f"${bal['available']:.2f}/${bal['granted']:.2f}"


def main():
    token = os.environ.get(LLMTOKEN_TOKEN_ENV)
    if not token:
        shell.log_err(f"未设置 {LLMTOKEN_TOKEN_ENV}")
        return
    try:
        bal = fetch_llmtoken_balance(token)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        shell.log_err(f"查询失败: {exc}")
        return
    print(f"${bal['available']:.2f}/${bal['granted']:.2f}")


if __name__ == "__main__":
    main()
