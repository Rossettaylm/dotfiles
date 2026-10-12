#!/usr/bin/env python3
"""状态栏 llmtoken 余额 —— 由 status-right 的 #() 每个 status-interval 调一次。

#() 的输出不会再被当 format 求值，拿不到 #{@thm_*} 主题色，所以跟 agentd 一样
把渲染好的格式串写进 @llm_balance，状态栏用 #{E:@llm_balance} 二次求值，
脚本本身不输出任何东西。

请求结果落盘缓存，TTL 内只读缓存；失败也刷新尝试时间，避免每轮都重试。
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".config" / "zsh" / "fzf" / "claude"))

from llm_balance import LLMTOKEN_TOKEN_ENV, fetch_llmtoken_balance

CACHE_FILE = Path.home() / ".cache" / "tmux-llm-balance" / "balance.json"
REFRESH_SECS = 180
OPT_KEY = "@llm_balance"

ICON_BALANCE = "\U000f0584"  # nf-md-wallet
WARN_RATIO = 0.2
CRIT_RATIO = 0.05


def tmux(*args: str) -> str:
    try:
        return subprocess.run(
            ("tmux", *args), capture_output=True, text=True, timeout=2,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def read_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_cache(data: dict) -> None:
    tmp = CACHE_FILE.with_suffix(f".{os.getpid()}.tmp")
    try:
        CACHE_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data))
        os.replace(tmp, CACHE_FILE)
    except OSError:
        tmp.unlink(missing_ok=True)


def refresh(cache: dict) -> dict:
    """拉一次余额；失败时保留旧值，只推进 fetched_at。"""
    data = {"fetched_at": time.time(), "balance": cache.get("balance")}
    token = os.environ.get(LLMTOKEN_TOKEN_ENV)
    if token:
        try:
            data["balance"] = fetch_llmtoken_balance(token)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    write_cache(data)
    return data


def render(balance: dict | None) -> str:
    if not balance:
        return ""
    available = balance["available"]
    granted = balance["granted"]
    ratio = available / granted if granted > 0 else (1.0 if available > 0 else 0.0)
    if ratio < CRIT_RATIO:
        color = "#{@thm_red},bold"
    elif ratio < WARN_RATIO:
        color = "#{@thm_yellow}"
    else:
        color = "#{@thm_green}"
    return (
        f"#[push-default]#[fg={color}]{ICON_BALANCE} "
        f"${available:.2f}/${granted:.2f}#[pop-default] "
    )


def main() -> None:
    cache = read_cache()
    stale = time.time() - cache.get("fetched_at", 0) >= REFRESH_SECS
    if stale:
        cache = refresh(cache)
    elif tmux("show", "-gqv", OPT_KEY).strip():
        return
    # 缓存未过期但 option 为空 = tmux server 刚重启，直接用缓存回填
    value = render(cache.get("balance"))
    if not value and not stale:
        return
    tmux("set", "-g", OPT_KEY, value, ";", "refresh-client", "-S")


if __name__ == "__main__":
    main()
