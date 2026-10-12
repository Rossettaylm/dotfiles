"""模型 context window 查询。

`[1m]` 后缀是给 Claude Code 看的窗口声明：它判定窗口时对带该后缀的模型短路返回
1M，且发请求前会 `replace(/(\[1m\])+$/i, "")` 剥掉，所以贴错只会误导 CC，不会污染
上游 wire id。窗口按优先级取：

1. 模型 id 自带的声明（tclaude 的 `-1m` 后缀，如 claude-opus-5-1m）
2. llmtoken 网关 /api/pricing 的 tags（本站自己声明，最权威）
3. models.dev 目录（落盘缓存，24h TTL）
4. 查不到返回 None，调用方按「不贴 [1m]」处理

models.dev 是 5.4MB 的全量目录，只把派生的 id→window 映射落盘到 ~/.cache。

同一 id 在不同 provider 下的窗口常不一致（claude-sonnet-4-5：anthropic 报 200K，
多个转售商挂 1M），所以取众数而非最大值，平票取较小值——否则会把 200K 的模型误判成 1M。
"""

import json
import os
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

MODELS_DEV_URL = "https://models.dev/api.json"
CACHE_FILE = Path.home() / ".cache" / "switch-model" / "windows.json"
REFRESH_SECS = 24 * 3600
RETRY_SECS = 300
HTTP_TIMEOUT = 15

WINDOW_IN_TAG = re.compile(r"(\d+(?:\.\d+)?)\s*([KkMm])\b")
WINDOW_IN_ID = re.compile(r"-(\d+(?:\.\d+)?)m$", re.I)
# 网关给同一个上游模型起的分流后缀（tclaude 的 -ioa、llmtoken 的 -external 等）；
# 查窗口时剥掉它们按裸名算。只在 models.dev 里真的存在裸名时才生效。
VARIANT_SUFFIX = re.compile(r"-(external|official|aws|overseas|ptu|demo|ioa)$")


def windows_from_tags(tags: str | None) -> int | None:
    """从 /api/pricing 的 tags 里读窗口，形如 `推理,工具,多模态,1M` / `262.1K`。"""
    best = None
    for num, unit in WINDOW_IN_TAG.findall(tags or ""):
        scale = 1000 if unit.lower() == "k" else 1_000_000
        value = int(float(num) * scale)
        if value > (best or 0):
            best = value
    return best


def window_from_id(model_id: str) -> int | None:
    """模型 id 自己声明的窗口，如 tclaude 的 claude-opus-5-1m。"""
    match = WINDOW_IN_ID.search(model_id)
    if not match:
        return None
    value = float(match.group(1))
    return int(value * 1_000_000) if value >= 1 else None


def pick_window(
    model_id: str,
    tag_window: int | None,
    catalog: dict[str, int],
    snapshot_window: int | None,
) -> int | None:
    """按 id 声明 → 网关 tags → models.dev → 快照旧值 取窗口。"""
    for candidate in (
        window_from_id(model_id),
        tag_window,
        lookup_catalog(model_id, catalog),
        snapshot_window,
    ):
        if candidate:
            return candidate
    return None


def lookup_catalog(model_id: str, catalog: dict[str, int]) -> int | None:
    """在 models.dev 派生表里查窗口。

    两级规范化：`.` 当 `-`（models.dev 只收 dash 形式 claude-opus-4-6，而 tclaude
    这类网关用点），再剥变体后缀（网关的 deepseek-v4-flash-external 背后就是
    deepseek-v4-flash）。变体后缀放最后，避免 -official 这类真名被误剥。
    """
    for candidate in (
        model_id,
        model_id.replace(".", "-"),
        VARIANT_SUFFIX.sub("", model_id.replace(".", "-")),
    ):
        if catalog.get(candidate):
            return catalog[candidate]
    return None


def _entry_window(entry: dict) -> int:
    limit = entry.get("limit") or {}
    return limit.get("context") or 0


def _derive_windows(catalog: dict) -> dict[str, int]:
    """models.dev 全量目录 → 裸 id → 众数窗口。"""
    votes: dict[str, Counter] = {}
    for provider in catalog.values():
        for model_id, entry in (provider.get("models") or {}).items():
            window = _entry_window(entry)
            if window:
                votes.setdefault(model_id, Counter())[window] += 1
    windows = {}
    for model_id, counts in votes.items():
        top = max(counts.values())
        windows[model_id] = min(w for w, n in counts.items() if n == top)
    return windows


def _read_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(data: dict):
    tmp = CACHE_FILE.with_suffix(f".{os.getpid()}.tmp")
    try:
        CACHE_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, CACHE_FILE)
    except OSError:
        tmp.unlink(missing_ok=True)


def load_catalog_windows() -> dict[str, int]:
    """取 models.dev 的 id→window 表。

    成功的话 24h 内不再拉；失败的话 5 分钟内不重试（否则每次 `cm` 都白等一次超时），
    期间沿用旧缓存，从来没有成功过就返回空表——调用方据此按「不贴 [1m]」处理。
    """
    cache = _read_cache()
    age = time.time() - cache.get("fetched_at", 0)
    if cache.get("windows") and age < (REFRESH_SECS if cache.get("ok") else RETRY_SECS):
        return cache["windows"]
    latest = {"fetched_at": time.time(), "windows": cache.get("windows") or {}, "ok": False}
    try:
        req = urllib.request.Request(MODELS_DEV_URL, headers={"User-Agent": "switch_model"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            latest["windows"] = _derive_windows(json.load(resp))
            latest["ok"] = True
    except (OSError, ValueError, TypeError, KeyError):
        pass
    _write_cache(latest)
    return latest["windows"]
