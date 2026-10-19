r"""交互式切换 Claude Code 的 provider 与模型组。

provider 定义网关地址、token 来源环境变量与附加请求头：

- llmtoken → https://REDACTED     token 取自 LLMTOKEN_API_KEY
- tclaude  → https://REDACTED  token 取自 TCLAUDE_AUTH_TOKEN
             附加 User-Agent: REDACTED/0.1.5

模型组由上游模型列表自动派生，不再手工维护：

- Claude Code 发送请求前会剥掉模型名末尾的 [1m]（二进制内的
  `replace(/(\[1m\])+$/i, "")`），因此贴 [1m] 只影响 Claude Code 认定的窗口，
  不影响上游收到的 wire id。窗口由 model_windows 按「模型 id 自带声明 → 网关 tags →
  models.dev → 快照旧值」判定，只有 ≥1M 才贴；查不到一律不贴（宁可让 Claude Code
  提前 compact，也不要让它以为有 1M 而永不 compact）。
- tclaude 的 wire id 形如 claude-opus-5-1m，其 `-1m` 后缀即窗口声明，同样按上面
  的规则贴 [1m]——Claude Code 剥掉后缀后发出的仍是不带方括号的原 id。
- tclaude 的权威模型清单内嵌在其原生二进制里（每条含 wire id 与显示名），
  无需启动 daemon 即可读取；`/v1/models` 端点返回的是显示名方言，直连会 404。

切换时更新 ~/.claude.json 的 env 段：ANTHROPIC_BASE_URL、ANTHROPIC_AUTH_TOKEN、
ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL、CLAUDE_CODE_MAX_CONTEXT_TOKENS，以及
ANTHROPIC_CUSTOM_HEADERS（切回无附加头的 provider 时清除）。窗口 env 只对不贴 [1m]
的模型有意义（贴了的话 Claude Code 直接短路成 1M），取各槽位窗口的最小值——一个值
服务所有模型，取最小的那个才不会被撑爆；全部贴了 [1m] 或窗口未知时不写。

主模型写在 ~/.claude/settings.json 的 model，而不是 ANTHROPIC_MODEL：启动时 env 优先级
高于 settings，若写 env，/model 里按 Enter「设为默认」会在下次启动时被覆盖。同时把当前
provider 的模型组写进 settings 的 modelPicker，使 /model 候选即为这些模型组（用户级
settings 会热加载，会话中重新打开 /model 即生效；跨 provider 仍需重启，base URL 只在
启动时读取）。`--sync-picker` 只刷新候选，不切换。

token 只从环境变量读取，本脚本不硬编码任何凭证。
"""

import json
import os
import platform
import re
import shlex
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell
from llm_balance import short_balance
from model_windows import load_catalog_windows, pick_window, windows_from_tags

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_CONFIG = os.path.expanduser("~/.claude.json")
CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")
SNAPSHOT_PATH = os.path.join(SCRIPT_DIR, "model_snapshots.json")
TCLAUDE_CACHE = os.path.expanduser("~/.tclaude/cache/gateway-models.json")
CONTEXT_STASH_KEY = "context_env"

HTTP_TIMEOUT = 15
ONE_M = 1_000_000
CONTEXT_KEY = "CLAUDE_CODE_MAX_CONTEXT_TOKENS"

PROVIDERS = {
    "llmtoken": {
        "base_url": "https://REDACTED",
        "token_env": "LLMTOKEN_API_KEY",
        "headers": {},
    },
    "tclaude": {
        "base_url": "https://REDACTED",
        "token_env": "TCLAUDE_AUTH_TOKEN",
        "headers": {"User-Agent": "REDACTED/0.1.5"},
    },
}

ENV_KEYS = {
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}
HEADERS_KEY = "ANTHROPIC_CUSTOM_HEADERS"
MODEL_KEY = "ANTHROPIC_MODEL"

# Claude Code 不认识的模型须借用一个已知模型的客户端行为，否则 modelPicker 不展示该行
BEHAVES_AS = "claude-sonnet-5"
SYNC_PICKER_FLAG = "--sync-picker"

MIN_OPUS_VERSION = (4, 7)

# ── 模型列表过滤规则 ───────────────────────────────────────
NON_CHAT = re.compile(
    r"embedding|image|vision|seedream|whisper|tts"
    r"|^codex-auto-review$|^nano-jev$|^laya$"
    r"|-mini$|-lite$|^gemma-|^qwen3\.5-35b|^qwen3\.8-27b",
    re.I,
)
DATE_SUFFIX = re.compile(r"-\d{8}$")
VARIANT_SUFFIX = re.compile(r"-(external|official|aws|overseas|ptu|demo)$")
VARIANT_PRIORITY = {"": 0, "-external": 1, "-official": 2}
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
SUFFIX_1M_RE = re.compile(r"(\[1m\])+$", re.I)
CREDITS_RE = re.compile(r"x([\d.]+)")
FAMILY_VARIANT_RE = re.compile(r"-(external|official|aws|overseas|ptu|demo|ioa)$")
VERSION_RE = re.compile(r"\d+(?:\.\d+)*")

# new-api 约定：model_ratio = 1 对应 $2 / 1M 输入 token
USD_PER_RATIO = 2
PRICE_KEYS = ("price", "rank")

SORT_KEY = "ctrl-s"
BORDER_LABEL = "🤖 [Claude: Switch Provider / Model Group]"
PRICE_SORT_MARK = "· 费率降序"


# ── 通用工具 ───────────────────────────────────────────────


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write(path: str, content: str):
    """原子写入文本文件（先写临时文件再 rename）。"""
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise


def write_json(path: str, data: dict):
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ── 模型列表获取 ───────────────────────────────────────────


def llmtoken_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{PROVIDERS['llmtoken']['base_url']}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.load(resp)


def fetch_llmtoken_pricing(token: str) -> dict[str, dict]:
    """从 new-api 的 /api/pricing 取按 token 计费模型的 输入/输出 单价（$/1M）与窗口。"""
    prices = {}
    for m in llmtoken_get("/api/pricing", token)["data"]:
        if m.get("quota_type") != 0 or not m.get("model_ratio"):
            continue
        cost_in = m["model_ratio"] * USD_PER_RATIO
        cost_out = cost_in * m.get("completion_ratio", 1)
        prices[m["model_name"]] = {
            "price": f"${cost_in:.3g}/${cost_out:.3g}",
            "rank": cost_in,
            "window": windows_from_tags(m.get("tags")),
        }
    return prices


def fetch_llmtoken_models(token: str) -> list[dict]:
    """从 llmtoken 网关拉取模型列表，费率拉取失败时沿用快照中的旧值。"""
    data = llmtoken_get("/v1/models", token)
    models = [{"id": m["id"], "name": m["id"]} for m in data["data"]]
    try:
        prices = fetch_llmtoken_pricing(token)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        shell.log_err(f"获取 llmtoken 费率失败: {exc}")
        prices = {
            m["id"]: {k: m[k] for k in PRICE_KEYS if k in m}
            for m in read_snapshot("llmtoken")
        }
    for model in models:
        model.update(prices.get(model["id"], {}))
    return models


def find_tclaude_binary() -> str | None:
    """定位 tclaude 原生二进制（bin/tclaude.js 只是平台分发 wrapper）。"""
    pkg_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath("/opt/homebrew/bin/tclaude"))),
        "node_modules",
        "@tencent",
    )
    if not os.path.isdir(pkg_root):
        return None
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    pkg = f"tclaude-{platform.system().lower()}-{arch}"
    candidate = os.path.join(pkg_root, pkg, "tclaude")
    return candidate if os.path.isfile(candidate) else None


def extract_embedded_models(binary: str) -> list[dict]:
    """从 tclaude 二进制中提取内嵌的模型清单（唯一的 wire id 权威来源）。"""
    with open(binary, "rb") as f:
        blob = f.read()
    match = re.search(rb"\[\s*\{\s*\"credits\"", blob)
    if not match:
        return []
    start = match.start()
    depth = 0
    for i in range(start, len(blob)):
        byte = blob[i : i + 1]
        if byte == b"[":
            depth += 1
        elif byte == b"]":
            depth -= 1
            if depth == 0:
                raw = blob[start : i + 1].decode("utf-8", "replace")
                models = json.loads(raw)
                return [
                    {"id": m["id"], "name": m.get("name", m["id"]), **parse_credits(m.get("credits"))}
                    for m in models
                    if not m.get("disabled") and m.get("id")
                ]
    return []


def parse_credits(credits: str | None) -> dict:
    """"x3.33 credits" → {"price": "x3.33", "rank": 3.33}。"""
    match = CREDITS_RE.search(credits or "")
    if not match:
        return {}
    return {"price": f"x{match.group(1)}", "rank": float(match.group(1))}


def fetch_tclaude_models() -> list[dict]:
    binary = find_tclaude_binary()
    if binary:
        models = extract_embedded_models(binary)
        if models:
            return models
    raise OSError("未找到 tclaude 二进制或其中未内嵌模型清单")


def read_snapshot(provider: str) -> list[dict]:
    return read_json(SNAPSHOT_PATH).get(provider, {}).get("models", [])


def fill_windows(provider: str, models: list[dict]) -> list[dict]:
    """给每个模型补 window 字段：id 自带声明 → 网关 tags → models.dev → 快照旧值。

    快照旧值只用来兜底同一个 id 上次算出来的窗口，所以先在旧快照里建索引。
    """
    previous = {m["id"]: m.get("window") for m in read_snapshot(provider)}
    catalog = load_catalog_windows()
    for model in models:
        model["window"] = pick_window(
            model["id"], model.get("window"), catalog, previous.get(model["id"])
        )
    return models


def fetch_tclaude_cache_models(snapshot_models: list[dict]) -> list[dict]:
    """兜底：读 tclaude 的 gateway-models.json。

    该文件存的是显示名方言（claude-opus-5[1m]），需要用上一次成功抓取时记下的
    name → wire id 映射还原成可用的 wire id；映射不到的（本轮新上线的模型）原样保留，
    至少让它在候选里出现。
    """
    by_name = {m["name"]: m for m in snapshot_models}
    cached = read_json(TCLAUDE_CACHE).get("models", [])
    return [by_name.get(m["id"], {"id": m["id"], "name": m["id"]}) for m in cached]


def save_snapshot(provider: str, models: list[dict]):
    """把成功抓到的模型列表存为脚本目录下的最后兜底。"""
    data = read_json(SNAPSHOT_PATH)
    data[provider] = {"models": models}
    write_json(SNAPSHOT_PATH, data)


def load_models(provider: str, token: str) -> tuple[list[dict], str]:
    """按 上游 → 缓存 → 本地快照 的顺序取模型列表，返回 (models, 来源)。"""
    try:
        if provider == "llmtoken":
            models = fetch_llmtoken_models(token)
            origin = "上游接口"
        else:
            models = fetch_tclaude_models()
            origin = "tclaude 二进制"
        models = fill_windows(provider, models)
        save_snapshot(provider, models)
        return models, origin
    except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
        shell.log_err(f"获取 {provider} 模型列表失败: {exc}")

    snapshot = read_snapshot(provider)
    if provider == "tclaude":
        try:
            cached = fetch_tclaude_cache_models(snapshot)
            if cached:
                return cached, "tclaude 缓存"
        except (OSError, ValueError, KeyError):
            pass
    if snapshot:
        return snapshot, "本地快照"
    return [], ""


# ── 模型组派生 ─────────────────────────────────────────────


def normalize_id(model_id: str) -> str:
    """剥掉 [1m] 后缀、tclaude 的 -1m 后缀与快照日期后缀。"""
    core = SUFFIX_1M_RE.sub("", model_id)
    core = re.sub(r"-1m$", "", core)
    return DATE_SUFFIX.sub("", core)


def parse_version(text: str) -> tuple[int, int] | None:
    m = re.match(r"^(\d+)(?:[.-](\d+))?", text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2) or 0)


def finalize_id(model_id: str, windows: dict[str, int | None]) -> str:
    """窗口 ≥1M 才贴 [1m]；Claude Code 发送前会剥掉，故不影响上游 wire id。

    窗口未知时一律不贴：贴错的代价是 Claude Code 认定 1M 而永不 compact，
    不贴的代价只是它按 200K 提前 compact——后者安全得多。
    """
    if model_id.endswith("[1m]"):
        return model_id
    window = windows.get(model_id)
    return model_id + "[1m]" if window and window >= ONE_M else model_id


def slot_window(model_id: str, windows: dict[str, int | None]) -> int | None:
    """一个槽位对 Claude Code 有意义的窗口：贴了 [1m] 的它自己就知道是 1M。"""
    if model_id.endswith("[1m]"):
        return None
    return windows.get(model_id)


def group_window(models: dict[str, str], windows: dict[str, int | None]) -> int | None:
    """写进 CLAUDE_CODE_MAX_CONTEXT_TOKENS 的值。

    Claude Code 只认一个值服务所有模型，所以取各槽位里最小的那个，免得被窗口小的
    槽位撑爆。全部贴了 [1m]（各自自带 1M）或窗口未知时返回 None，调用方据此清掉该键。
    """
    known = [w for slot in models.values() if (w := slot_window(slot, windows))]
    return min(known) if known else None


def split_claude_family(models: list[dict]) -> tuple[dict, list[dict]]:
    family: dict[str, list[tuple[tuple[int, int], str, str]]] = {
        "opus": [],
        "sonnet": [],
        "haiku": [],
    }
    others = []
    for model in models:
        mid, name = model["id"], model.get("name", model["id"])
        parsed = re.match(r"^claude-(opus|sonnet|haiku)-(.+)$", normalize_id(name))
        version = parse_version(parsed.group(2)) if parsed else None
        if parsed and version:
            family[parsed.group(1)].append((version, mid, name))
        else:
            others.append(model)

    deduped = {}
    for slot, entries in family.items():
        best: dict[tuple[int, int], tuple[str, str]] = {}
        for version, mid, name in entries:
            if version not in best or len(mid) < len(best[version][0]):
                best[version] = (mid, name)
        deduped[slot] = sorted((v, *best[v]) for v in best)
    return deduped, others


def pick_others(models: list[dict]) -> list[dict]:
    """非 Claude 家族：丢弃非对话模型，同名变体按 裸名 > -external > -official 取一个。"""
    best: dict[str, tuple[int, dict]] = {}
    for model in models:
        mid = normalize_id(model["id"])
        if NON_CHAT.search(mid):
            continue
        match = VARIANT_SUFFIX.search(mid)
        suffix = match.group(0) if match else ""
        if suffix not in VARIANT_PRIORITY:
            continue
        base = mid[: match.start()] if match else mid
        priority = VARIANT_PRIORITY[suffix]
        if base not in best or priority < best[base][0]:
            best[base] = (priority, model)
    return [entry for _, (_, entry) in sorted(best.items())]


def derive_groups(provider: str, models: list[dict]) -> dict[str, dict]:
    """把扁平模型列表派生成 opus/sonnet/haiku 三元组。

    Claude 家族：每个 opus 版本一组，sonnet 取「版本不高于该 opus 的最新一个」，
    haiku 取最新一个；每个 sonnet 版本再单独成组（三槽位同填该 sonnet，
    可直接把主模型切到 sonnet）；非 Claude 模型各自成组，三个槽位填同一个模型。
    """
    windows = {m["id"]: m.get("window") for m in models}
    family, others = split_claude_family(models)
    ops = [(v, mid, name) for v, mid, name in family["opus"] if v >= MIN_OPUS_VERSION]
    sons = family["sonnet"]
    haikus = family["haiku"]
    haiku = haikus[-1] if haikus else None

    groups: dict[str, dict] = {}
    for version, opus_id, _ in ops:
        if sons:
            eligible = [s for s in sons if s[0] <= version]
            sonnet_id = (eligible[-1] if eligible else sons[0])[1]
        else:
            sonnet_id = opus_id
        values = {
            "opus": finalize_id(opus_id, windows),
            "sonnet": finalize_id(sonnet_id, windows),
            "haiku": finalize_id(haiku[1] if haiku else opus_id, windows),
        }
        groups[f"opus{version[0]}.{version[1]}"] = values

    for version, sonnet_id, _ in sons:
        model_id = finalize_id(sonnet_id, windows)
        groups[f"sonnet{version[0]}.{version[1]}"] = {
            "opus": model_id,
            "sonnet": model_id,
            "haiku": model_id,
        }

    for model in pick_others(others):
        model_id = finalize_id(model["id"], windows)
        groups[model_id] = {"opus": model_id, "sonnet": model_id, "haiku": model_id}
    return groups


# ── 配置读取与检测 ─────────────────────────────────────────


def provider_of(env: dict) -> str | None:
    return next(
        (
            name
            for name, cfg in PROVIDERS.items()
            if env.get("ANTHROPIC_BASE_URL") == cfg["base_url"]
        ),
        None,
    )


def detect_current(
    env: dict, model: str | None, all_groups: dict[str, dict[str, dict]]
) -> tuple[str, str] | None:
    """按 ANTHROPIC_BASE_URL 反查 provider，再按主模型匹配模型组（主模型可能已在 /model
    中改过），匹配不到时退回比对三个槽位 env。"""
    provider = provider_of(env)
    if provider is None:
        return None
    groups = all_groups.get(provider, {})
    for group, models in groups.items():
        if models["opus"] == model:
            return provider, group
    for group, models in groups.items():
        if all(env.get(ENV_KEYS[slot]) == value for slot, value in models.items()):
            return provider, group
    return None


def parse_selection(line: str, all_groups: dict[str, dict[str, dict]]) -> tuple[str, str] | None:
    """从 fzf 输出行中解析出 `provider:group` 标记。"""
    for token in ANSI_RE.sub("", line).split():
        if ":" not in token:
            continue
        provider, _, group = token.partition(":")
        if group in all_groups.get(provider, {}):
            return provider, group
    return None


def resolve_token(provider: str) -> str | None:
    return os.environ.get(PROVIDERS[provider]["token_env"])


# ── Claude Code 配置写入 ───────────────────────────────────


def update_claude_env(
    provider: str, models: dict[str, str], token: str, window: int | None
):
    """更新 ~/.claude.json 中的环境变量。"""
    cfg = PROVIDERS[provider]
    data = read_json(CLAUDE_CONFIG)
    env = data.setdefault("env", {})
    env["ANTHROPIC_BASE_URL"] = cfg["base_url"]
    env["ANTHROPIC_AUTH_TOKEN"] = token
    for slot, key in ENV_KEYS.items():
        env[key] = models[slot]
    env.pop(MODEL_KEY, None)
    apply_context_window(env, window)

    if cfg["headers"]:
        env[HEADERS_KEY] = "\n".join(f"{k}: {v}" for k, v in cfg["headers"].items())
    else:
        env.pop(HEADERS_KEY, None)

    write_json(CLAUDE_CONFIG, data)


def apply_context_window(env: dict, window: int | None) -> bool:
    """在 env 里改 CLAUDE_CODE_MAX_CONTEXT_TOKENS，不覆盖用户自己设的值。

    按「当前值 == 上次我们写的值」判定归属：是用户写的就原样保留，是空的或我们上次
    写的才改写。返回是否真的动过——动了才需要把新值记进快照，否则别把用户的值
    当成"我们写的"记下来。
    """
    previous = read_json(SNAPSHOT_PATH).get(CONTEXT_STASH_KEY)
    current = env.get(CONTEXT_KEY)
    if current is not None and current != previous:
        return False
    value = str(window) if window else None
    if value:
        env[CONTEXT_KEY] = value
    else:
        env.pop(CONTEXT_KEY, None)
    stash_context_window(value)
    return True


def stash_context_window(value: str | None):
    data = read_json(SNAPSHOT_PATH)
    if value is None:
        data.pop(CONTEXT_STASH_KEY, None)
    else:
        data[CONTEXT_STASH_KEY] = value
    write_json(SNAPSHOT_PATH, data)


def read_settings() -> dict:
    """settings.json 解析失败时直接抛出，避免把用户配置覆盖成只剩脚本写入的字段。"""
    try:
        with open(CLAUDE_SETTINGS, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def picker_rows(entries: list[dict]) -> list[dict]:
    """模型组 → /model 候选行：选中即把主模型设为该组的 opus 槽位。"""
    rows = []
    for e in entries:
        model = e["models"]["opus"]
        row = {"model": model, "label": SUFFIX_1M_RE.sub("", e["label"])}
        if e["price"] != "-":
            row["description"] = f"{e['price']} · {model}"
        if not model.startswith("claude-"):
            row["behavesAs"] = BEHAVES_AS
        rows.append(row)
    return rows


def update_claude_settings(rows: list[dict], model: str | None = None):
    data = read_settings()
    if model:
        data["model"] = model
    data["modelPicker"] = {"replaceBuiltInOptions": True, "options": rows}
    write_json(CLAUDE_SETTINGS, data)


# ── UI ─────────────────────────────────────────────────────


def group_price(prices: dict[str, dict], models: dict[str, str]) -> dict:
    """模型组费率取 opus 槽位（主模型即 opus，主要消耗在它）。"""
    return prices.get(SUFFIX_1M_RE.sub("", models["opus"]), {})


def format_group_line(
    label: str, models: dict, price: str, is_current: bool, widths: tuple[int, int]
) -> str:
    label_w, price_w = widths
    detail = f"{models['opus']} / {models['sonnet']} / {models['haiku']}"
    price_col = f"\033[33m{price:>{price_w}}\033[0m"
    if is_current:
        return f"\033[32m● {label:<{label_w}}\033[0m  {price_col}  {detail}"
    return f"  {label:<{label_w}}  {price_col}  {detail}"


def natural_key(text: str) -> list:
    """数字段按数值比较，使 opus5.0 > opus4.10 > opus4.8。"""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


def model_name(entry: dict) -> str:
    return SUFFIX_1M_RE.sub("", entry["label"].partition(":")[2])


def model_family(entry: dict) -> str:
    """去掉变体后缀和版本号：gpt-6-sol / gpt-5.6-sol → gpt-*-sol。"""
    return VERSION_RE.sub("*", FAMILY_VARIANT_RE.sub("", model_name(entry)))


def sort_by_price(entries: list[dict]) -> list[dict]:
    """provider 分块保持原序；块内同一模型的各版本聚成一组，组间按组内最高费率降序，
    组内按版本降序；无费率的组排在末尾。"""
    order = {p: i for i, p in enumerate(dict.fromkeys(e["provider"] for e in entries))}
    family_rank: dict[tuple[str, str], float] = {}
    for e in entries:
        rank: float | None = e["rank"]
        if rank is not None:
            key = (e["provider"], model_family(e))
            family_rank[key] = max(family_rank.get(key, rank), rank)

    def group_key(e: dict) -> tuple:
        family = model_family(e)
        rank = family_rank.get((e["provider"], family))
        return order[e["provider"]], rank is None, -(rank or 0), family

    by_version = sorted(entries, key=lambda e: natural_key(model_name(e)), reverse=True)
    return sorted(by_version, key=group_key)


def build_toggle_bind(default_file: str, price_file: str) -> str:
    """ctrl-s 在 默认顺序 ⇄ 费率降序 间切换，以 border label 记录当前状态。"""
    to_price = f"reload(cat {shlex.quote(price_file)})+change-border-label( {BORDER_LABEL} {PRICE_SORT_MARK} )"
    to_default = f"reload(cat {shlex.quote(default_file)})+change-border-label( {BORDER_LABEL} )"
    script = (
        f'case "$FZF_BORDER_LABEL" in *"{PRICE_SORT_MARK}"*) echo {shlex.quote(to_default)} ;; '
        f"*) echo {shlex.quote(to_price)} ;; esac"
    )
    return f"{SORT_KEY}:transform:{script}"


# ── 主逻辑 ─────────────────────────────────────────────────


def load_all_groups(
    tokens: dict[str, str],
) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict[str, int | None]]]:
    all_groups: dict[str, dict[str, dict]] = {}
    prices: dict[str, dict[str, dict]] = {}
    windows: dict[str, dict[str, int | None]] = {}
    for provider, token in tokens.items():
        models, source = load_models(provider, token)
        if models:
            windows[provider] = {m["id"]: m.get("window") for m in models}
            all_groups[provider] = derive_groups(provider, models)
            prices[provider] = {m["id"]: m for m in models if "price" in m}
            shell.log_plain(f"{provider}: {len(models)} 个模型（来源: {source}）")
    return all_groups, prices, windows


def build_entries(
    all_groups: dict[str, dict], prices: dict[str, dict], current: tuple[str, str] | None
) -> list[dict]:
    entries = []
    for provider, groups in all_groups.items():
        for group, models in groups.items():
            price = group_price(prices[provider], models)
            entries.append(
                {
                    "provider": provider,
                    "label": f"{provider}:{group}",
                    "models": models,
                    "price": price.get("price", "-"),
                    "rank": price.get("rank"),
                    "is_current": (provider, group) == current,
                }
            )
    return entries


def sync_picker():
    """按当前 provider 刷新 /model 候选，不改动模型选择。"""
    provider = provider_of(read_json(CLAUDE_CONFIG).get("env", {}))
    if provider is None:
        shell.log_err("~/.claude.json 的 ANTHROPIC_BASE_URL 未匹配任何 provider，已中止")
        return
    token = resolve_token(provider)
    if not token:
        shell.log_err(f"未设置 {PROVIDERS[provider]['token_env']}，已中止")
        return
    all_groups, prices, windows = load_all_groups({provider: token})
    if not all_groups:
        shell.log_err(f"未能获取 {provider} 的模型列表，已中止")
        return
    rows = picker_rows(build_entries(all_groups, prices, None))
    update_claude_settings(rows)
    shell.log_success(f"/model 候选已刷新: {provider} 共 {len(rows)} 项")


def switch_model():
    tokens = {p: token for p in PROVIDERS if (token := resolve_token(p))}
    all_groups, prices, windows = load_all_groups(tokens)
    if not all_groups:
        shell.log_err("未能获取任何 provider 的模型列表，已中止")
        return

    env = read_json(CLAUDE_CONFIG).get("env", {})
    current = detect_current(env, read_settings().get("model"), all_groups)
    entries = build_entries(all_groups, prices, current)
    widths = (
        max(len(e["label"]) for e in entries),
        max(len(e["price"]) for e in entries),
    )

    def render(items: list[dict]) -> str:
        return "\n".join(
            format_group_line(e["label"], e["models"], e["price"], e["is_current"], widths)
            for e in items
        )

    current_label = f"{current[0]}:{current[1]}" if current else "未匹配"
    balance = f" │ llmtoken 余额: {short_balance() or '-'}" if "llmtoken" in tokens else ""
    with tempfile.TemporaryDirectory(prefix="switch_model.") as tmp_dir:
        default_file = os.path.join(tmp_dir, "default")
        price_file = os.path.join(tmp_dir, "price")
        with open(default_file, "w", encoding="utf-8") as f:
            f.write(render(entries))
        with open(price_file, "w", encoding="utf-8") as f:
            f.write(render(sort_by_price(entries)))

        cmd = shell.build_fzf_cmd(
            border_label=BORDER_LABEL,
            header=f"enter: 切换 │ {SORT_KEY}: 费率排序 │ 当前: {current_label}{balance} │ 费率取 opus 槽位",
            sort=False,
            extra_args=["--bind", build_toggle_bind(default_file, price_file)],
            as_str=True,
        )
        out, err = shell.run_shell_cmd(cmd, input=render(entries))
    if err:
        shell.log_err(err)
    if not out:
        return

    selection = parse_selection(out[0], all_groups)
    if not selection:
        shell.log_err("无法解析选择")
        return

    provider, group = selection
    rows = picker_rows([e for e in entries if e["provider"] == provider])
    models = all_groups[provider][group]
    window = group_window(models, windows.get(provider, {}))
    if selection == current:
        data = read_json(CLAUDE_CONFIG)
        if apply_context_window(data.setdefault("env", {}), window):
            write_json(CLAUDE_CONFIG, data)
        update_claude_settings(rows)
        shell.log_plain(f"未变更，仍为 {provider}:{group}（/model 候选已刷新）")
        return

    update_claude_env(provider, models, tokens[provider], window)
    update_claude_settings(rows, models["opus"])

    shell.log_success(
        f"已切换: {current_label} → {provider}:{group}\n"
        f"  baseUrl = {PROVIDERS[provider]['base_url']}\n"
        f"  opus    = {models['opus']}\n"
        f"  sonnet  = {models['sonnet']}\n"
        f"  haiku   = {models['haiku']}\n"
        f"  context = {window if window else '由 [1m] 或 Claude Code 默认决定'}"
    )


if __name__ == "__main__":
    if SYNC_PICKER_FLAG in sys.argv[1:]:
        sync_picker()
    else:
        switch_model()
