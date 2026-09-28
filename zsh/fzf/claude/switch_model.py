r"""交互式切换 Claude Code 的 provider 与模型组。

provider 定义网关地址、token 来源环境变量与附加请求头：

- llmtoken → https://qproxy.gtimg.com     token 取自 LLMTOKEN_API_KEY
- tclaude  → https://copilot.tencent.com  token 取自 TCLAUDE_AUTH_TOKEN
             附加 User-Agent: TClaude-code/0.1.5

模型组由上游模型列表自动派生，不再手工维护：

- Claude Code 发送请求前会剥掉模型名末尾的 [1m]（二进制内的
  `replace(/(\[1m\])+$/i, "")`），因此 llmtoken 的 [1m] 后缀纯属显示，请求实际
  发出的是裸 id；而 tclaude 的 wire id 形如 claude-opus-5-1m（没有方括号），
  不会被剥掉，必须原样使用。所以只有 llmtoken 追加 [1m] 后缀。
- tclaude 的权威模型清单内嵌在其原生二进制里（每条含 wire id 与显示名），
  无需启动 daemon 即可读取；`/v1/models` 端点返回的是显示名方言，直连会 404。

切换时更新 ~/.claude.json 的 env 段：ANTHROPIC_BASE_URL、ANTHROPIC_AUTH_TOKEN、
ANTHROPIC_MODEL、ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL，以及
ANTHROPIC_CUSTOM_HEADERS（切回无附加头的 provider 时清除）。

token 只从环境变量读取，本脚本不硬编码任何凭证。
"""

import json
import os
import platform
import re
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_CONFIG = os.path.expanduser("~/.claude.json")
SNAPSHOT_PATH = os.path.join(SCRIPT_DIR, "model_snapshots.json")
TCLAUDE_CACHE = os.path.expanduser("~/.tclaude/cache/gateway-models.json")

HTTP_TIMEOUT = 15

PROVIDERS = {
    "llmtoken": {
        "base_url": "https://qproxy.gtimg.com",
        "token_env": "LLMTOKEN_API_KEY",
        "headers": {},
        "suffix_1m": True,
    },
    "tclaude": {
        "base_url": "https://copilot.tencent.com",
        "token_env": "TCLAUDE_AUTH_TOKEN",
        "headers": {"User-Agent": "TClaude-code/0.1.5"},
        "suffix_1m": False,
    },
}

ENV_KEYS = {
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}
HEADERS_KEY = "ANTHROPIC_CUSTOM_HEADERS"

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


def fetch_llmtoken_models(token: str) -> list[dict]:
    """从 llmtoken 网关拉取模型列表。"""
    req = urllib.request.Request(
        f"{PROVIDERS['llmtoken']['base_url']}/v1/models",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        data = json.load(resp)
    return [{"id": m["id"], "name": m["id"]} for m in data["data"]]


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
                    {"id": m["id"], "name": m.get("name", m["id"])}
                    for m in models
                    if not m.get("disabled") and m.get("id")
                ]
    return []


def fetch_tclaude_models() -> list[dict]:
    binary = find_tclaude_binary()
    if binary:
        models = extract_embedded_models(binary)
        if models:
            return models
    raise OSError("未找到 tclaude 二进制或其中未内嵌模型清单")


def read_snapshot(provider: str) -> list[dict]:
    return read_json(SNAPSHOT_PATH).get(provider, {}).get("models", [])


def fetch_tclaude_cache_models(snapshot_models: list[dict]) -> list[dict]:
    """兜底：读 tclaude 的 gateway-models.json。

    该文件存的是显示名方言（claude-opus-5[1m]），需要用上一次成功抓取时记下的
    name → wire id 映射还原成可用的 wire id。
    """
    name_to_id = {m["name"]: m["id"] for m in snapshot_models}
    cached = read_json(TCLAUDE_CACHE).get("models", [])
    resolved = []
    for m in cached:
        mid = name_to_id.get(m.get("id", ""))
        if mid:
            resolved.append({"id": mid, "name": m["id"]})
    return resolved


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


def finalize_id(provider: str, model_id: str) -> str:
    """llmtoken 的 [1m] 仅作显示，Claude Code 发送前会剥掉；haiku 不加。"""
    if PROVIDERS[provider]["suffix_1m"] and "haiku" not in model_id:
        return model_id + "[1m]"
    return model_id


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
    haiku 取最新一个；非 Claude 模型各自成组，三个槽位填同一个模型。
    """
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
            "opus": finalize_id(provider, opus_id),
            "sonnet": finalize_id(provider, sonnet_id),
            "haiku": finalize_id(provider, haiku[1]) if haiku else finalize_id(provider, opus_id),
        }
        groups[f"opus{version[0]}.{version[1]}"] = values

    for model in pick_others(others):
        model_id = finalize_id(provider, model["id"])
        groups[model_id] = {"opus": model_id, "sonnet": model_id, "haiku": model_id}
    return groups


# ── 配置读取与检测 ─────────────────────────────────────────


def detect_current(env: dict, all_groups: dict[str, dict[str, dict]]) -> tuple[str, str] | None:
    """按 ANTHROPIC_BASE_URL 反查 provider，再比对三个槽位 env 匹配模型组。"""
    provider = next(
        (
            name
            for name, cfg in PROVIDERS.items()
            if env.get("ANTHROPIC_BASE_URL") == cfg["base_url"]
        ),
        None,
    )
    if provider is None:
        return None
    for group, models in all_groups.get(provider, {}).items():
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


def update_claude_env(provider: str, models: dict[str, str], token: str):
    """更新 ~/.claude.json 中的环境变量。"""
    cfg = PROVIDERS[provider]
    data = read_json(CLAUDE_CONFIG)
    env = data.setdefault("env", {})
    env["ANTHROPIC_BASE_URL"] = cfg["base_url"]
    env["ANTHROPIC_AUTH_TOKEN"] = token
    for slot, key in ENV_KEYS.items():
        env[key] = models[slot]
    env["ANTHROPIC_MODEL"] = models["opus"]

    if cfg["headers"]:
        env[HEADERS_KEY] = "\n".join(f"{k}: {v}" for k, v in cfg["headers"].items())
    else:
        env.pop(HEADERS_KEY, None)

    write_json(CLAUDE_CONFIG, data)


# ── UI ─────────────────────────────────────────────────────


def format_group_line(provider: str, group: str, models: dict, is_current: bool) -> str:
    label = f"{provider}:{group}"
    detail = f"{models['opus']} / {models['sonnet']} / {models['haiku']}"
    if is_current:
        return f"\033[32m● {label}\033[0m  {detail}"
    return f"  {label}  {detail}"


# ── 主逻辑 ─────────────────────────────────────────────────


def switch_model():
    tokens = {p: token for p in PROVIDERS if (token := resolve_token(p))}
    all_groups: dict[str, dict[str, dict]] = {}
    for provider, token in tokens.items():
        models, source = load_models(provider, token)
        if models:
            all_groups[provider] = derive_groups(provider, models)
            shell.log_plain(f"{provider}: {len(models)} 个模型（来源: {source}）")

    if not all_groups:
        shell.log_err("未能获取任何 provider 的模型列表，已中止")
        return

    env = read_json(CLAUDE_CONFIG).get("env", {})
    current = detect_current(env, all_groups)

    lines = [
        format_group_line(provider, group, models, (provider, group) == current)
        for provider, groups in all_groups.items()
        for group, models in groups.items()
    ]

    current_label = f"{current[0]}:{current[1]}" if current else "未匹配"
    cmd = shell.build_fzf_cmd(
        border_label="🤖 [Claude: Switch Provider / Model Group]",
        header=f"enter: 切换 │ 当前: {current_label} │ 格式 provider:group",
        sort=False,
        as_str=True,
    )
    out, err = shell.run_shell_cmd(cmd, input="\n".join(lines))
    if err:
        shell.log_err(err)
    if not out:
        return

    selection = parse_selection(out[0], all_groups)
    if not selection:
        shell.log_err("无法解析选择")
        return

    provider, group = selection
    if selection == current:
        shell.log_plain(f"未变更，仍为 {provider}:{group}")
        return

    models = all_groups[provider][group]
    update_claude_env(provider, models, tokens[provider])

    shell.log_success(
        f"已切换: {current_label} → {provider}:{group}\n"
        f"  baseUrl = {PROVIDERS[provider]['base_url']}\n"
        f"  opus    = {models['opus']}\n"
        f"  sonnet  = {models['sonnet']}\n"
        f"  haiku   = {models['haiku']}"
    )


if __name__ == "__main__":
    switch_model()
