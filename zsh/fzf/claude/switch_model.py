"""交互式切换 Claude Code / Codex / pi 模型组。

模型组定义了 opus / sonnet / haiku 三个槽位的模型，切换时同步更新：
- ~/.claude.json              → Claude Code 环境变量
- ~/.codex/config.toml        → Codex model 字段
- ~/.config/pi/settings.json  → pi defaultProvider/defaultModel/enabledModels（不含 [1m] 后缀）
- ~/.config/pi/models.json    → pi llmtoken provider 的模型列表（不含 [1m] 后缀）
- ~/.config/pi/auth.json      → pi llmtoken 的 API key 凭证

pi 不支持模型 ID 里的 [1m] 上下文后缀，且不读取 ANTHROPIC_AUTH_TOKEN 这类仅由
Claude Code 注入的环境变量，因此需要把去后缀的模型 ID 和 token 分别写入
models.json / auth.json，供 pi 通过网关直连调用。
"""

import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

# ── 模型组定义 ──────────────────────────────────────────────
MODEL_GROUPS = {
    "deepseekv4-flash": {
        "opus": "deepseek-v4-flash-official[1m]",
        "sonnet": "deepseek-v4-flash-official[1m]",
        "haiku": "deepseek-v4-flash-official[1m]",
    },
    "kimi3": {
        "opus": "kimi-k3-external[1m]",
        "sonnet": "claude-sonnet-4-6[1m]",
        "haiku": "claude-haiku-4-5",
    },
    "sonnet5": {
        "opus": "claude-sonnet-5[1m]",
        "sonnet": "claude-sonnet-4-6[1m]",
        "haiku": "claude-haiku-4-5",
    },
    "opus4.8": {
        "opus": "claude-opus-4-8[1m]",
        "sonnet": "claude-sonnet-4-6[1m]",
        "haiku": "claude-haiku-4-5",
    },
    "opus4.6": {
        "opus": "claude-opus-4-6[1m]",
        "sonnet": "claude-sonnet-4-6[1m]",
        "haiku": "claude-haiku-4-5",
    },
    "sonnet4.6": {
        "opus": "claude-sonnet-4-6[1m]",
        "sonnet": "claude-sonnet-4-6[1m]",
        "haiku": "claude-haiku-4-5",
    },
    "deepseekv4": {
        "opus": "deepseek-v4-pro-official[1m]",
        "sonnet": "deepseek-v4-pro-official[1m]",
        "haiku": "deepseek-v4-flash-official",
    },
    "glm-5.2": {
        "opus": "glm-5.2-external[1m]",
        "sonnet": "glm-5.2-external[1m]",
        "haiku": "deepseek-v4-flash-official",
    },
}

# ── 目标配置文件 ───────────────────────────────────────────
CLAUDE_CONFIG = os.path.expanduser("~/.claude.json")
PI_CONFIG = os.path.expanduser("~/.config/pi/settings.json")
PI_MODELS_CONFIG = os.path.expanduser("~/.config/pi/models.json")
PI_AUTH_CONFIG = os.path.expanduser("~/.config/pi/auth.json")

PI_GATEWAY_PROVIDER = "llmtoken"
PI_GATEWAY_BASE_URL = "https://qproxy.gtimg.com"

# pi 通过网关调用部分模型时，需要覆写 pi-ai 内置的 compat/thinkingLevelMap
# 字段才能正确请求（已逐一实测）。未列出的模型使用默认字段。
MODEL_COMPAT_OVERRIDES: dict[str, dict] = {
    "claude-sonnet-4-6": {
        "contextWindow": 1000000,
        "maxTokens": 128000,
        "input": ["text", "image"],
        "thinkingLevelMap": {"max": "max"},
        "compat": {"forceAdaptiveThinking": True},
    },
    "claude-sonnet-5": {
        "contextWindow": 1000000,
        "maxTokens": 128000,
        "input": ["text", "image"],
        "thinkingLevelMap": {"xhigh": "xhigh", "max": "max"},
        "compat": {"forceAdaptiveThinking": True, "supportsTemperature": False},
    },
    "claude-haiku-4-5": {
        "contextWindow": 200000,
        "maxTokens": 64000,
        "input": ["text", "image"],
        "compat": {"supportsEagerToolInputStreaming": False},
    },
    "claude-opus-4-8": {
        "contextWindow": 1000000,
        "maxTokens": 128000,
        "input": ["text", "image"],
        "thinkingLevelMap": {"xhigh": "xhigh", "max": "max"},
        "compat": {"forceAdaptiveThinking": True, "supportsTemperature": False},
    },
    "claude-opus-4-6": {
        "contextWindow": 1000000,
        "maxTokens": 128000,
        "input": ["text", "image"],
        "thinkingLevelMap": {"max": "max"},
        "compat": {"forceAdaptiveThinking": True},
    },
    "deepseek-v4-flash-official": {
        "contextWindow": 1000000,
        "maxTokens": 384000,
        "input": ["text"],
    },
    "deepseek-v4-pro-official": {
        "contextWindow": 1000000,
        "maxTokens": 384000,
        "input": ["text"],
    },
}

MODEL_DEFAULTS = {
    "reasoning": True,
    "contextWindow": 1000000,
    "maxTokens": 128000,
    "input": ["text"],
}

ENV_KEYS = {
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}

# ── 工具函数 ───────────────────────────────────────────────


def strip_context_suffix(model_id: str) -> str:
    """去掉模型名中的上下文窗口后缀，如 [1m] → ''。"""
    return re.sub(r"\[\d+m\]$", "", model_id)


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write(path: str, content: str):
    """原子写入文本文件（先写临时文件再 rename）。"""
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise


def write_json(path: str, data: dict):
    """原子写入 JSON 文件。"""
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ── 配置读取与检测 ─────────────────────────────────────────


def detect_current_group(env: dict) -> str | None:
    for name, models in MODEL_GROUPS.items():
        if all(env.get(ENV_KEYS[slot]) == model for slot, model in models.items()):
            return name
    return None


# ── Claude Code ────────────────────────────────────────────


def update_claude_env(models: dict[str, str]):
    """更新 ~/.claude.json 中的环境变量。"""
    data = read_json(CLAUDE_CONFIG)
    data.setdefault("env", {})
    for slot, key in ENV_KEYS.items():
        data["env"][key] = models[slot]
    data["env"]["ANTHROPIC_MODEL"] = models["opus"]
    write_json(CLAUDE_CONFIG, data)


# ── pi ─────────────────────────────────────────────────────


def all_pi_model_ids() -> list[str]:
    """收集 MODEL_GROUPS 中出现过的全部模型 ID（去重、去 [1m] 后缀）。"""
    seen: dict[str, None] = {}
    for models in MODEL_GROUPS.values():
        for model_id in models.values():
            seen.setdefault(strip_context_suffix(model_id), None)
    return list(seen)


def build_pi_model_entry(model_id: str) -> dict:
    """构造 pi models.json 中单个模型条目，应用已验证的 compat 覆写。"""
    override = MODEL_COMPAT_OVERRIDES.get(model_id)
    entry = {"id": model_id, **MODEL_DEFAULTS}
    if override:
        entry.update(override)
    return entry


def sync_pi_models_json():
    """全量重写 pi models.json 中 llmtoken 的 models 数组。"""
    data = read_json(PI_MODELS_CONFIG)
    providers = data.setdefault("providers", {})
    gateway = providers.setdefault(
        PI_GATEWAY_PROVIDER,
        {
            "baseUrl": PI_GATEWAY_BASE_URL,
            "api": "anthropic-messages",
            "authHeader": True,
            "compat": {"supportsStore": False},
        },
    )
    gateway["models"] = [build_pi_model_entry(mid) for mid in all_pi_model_ids()]
    write_json(PI_MODELS_CONFIG, data)


def sync_pi_auth(auth_token: str | None):
    """把 ANTHROPIC_AUTH_TOKEN 写入 pi 的 auth.json，供 llmtoken 鉴权。"""
    if not auth_token:
        return
    data = read_json(PI_AUTH_CONFIG)
    data[PI_GATEWAY_PROVIDER] = {"type": "api_key", "key": auth_token}
    write_json(PI_AUTH_CONFIG, data)


def update_pi_model(models: dict[str, str]):
    """更新 ~/.config/pi/settings.json 的 defaultProvider/defaultModel/enabledModels。"""
    pi_models = [strip_context_suffix(m) for m in models.values()]
    enabled_models = list(dict.fromkeys(pi_models))
    data = read_json(PI_CONFIG)
    data["defaultProvider"] = PI_GATEWAY_PROVIDER
    data["defaultModel"] = strip_context_suffix(models["opus"])
    data["enabledModels"] = enabled_models
    write_json(PI_CONFIG, data)


# ── UI ─────────────────────────────────────────────────────


def format_group_line(name: str, models: dict, is_current: bool) -> str:
    detail = f"{models['opus']} / {models['sonnet']} / {models['haiku']}"
    if is_current:
        return f"\033[32m● {name}\033[0m  {detail}"
    return f"  {name}  {detail}"


# ── 主逻辑 ─────────────────────────────────────────────────


def switch_model():
    data = read_json(CLAUDE_CONFIG)
    env = data.get("env", {})
    current_group = detect_current_group(env)

    lines = [
        format_group_line(name, models, name == current_group)
        for name, models in MODEL_GROUPS.items()
    ]

    cmd = shell.build_fzf_cmd(
        border_label="🤖 [Claude: Switch Model Group]",
        header=f"enter: 切换模型组 │ 当前: {current_group or '未匹配'}│ opus / sonnet / haiku",
        sort=False,
        as_str=True,
    )
    out, err = shell.run_shell_cmd(cmd, input="\n".join(lines))
    if err:
        shell.log_err(err)
    if not out:
        return

    tokens = out[0].split()
    selected = next((t for t in tokens if t in MODEL_GROUPS), None)
    if not selected:
        shell.log_err("无法解析选择")
        return

    if selected == current_group:
        shell.log_plain(f"未变更，仍为 {selected}")
        return

    models = MODEL_GROUPS[selected]

    # 同步 Claude Code + pi 配置
    update_claude_env(models)
    sync_pi_models_json()
    sync_pi_auth(env.get("ANTHROPIC_AUTH_TOKEN"))
    update_pi_model(models)

    shell.log_success(
        f"已切换模型组: {current_group or '未设置'} → {selected}\n"
        f"  opus   = {models['opus']}\n"
        f"  sonnet = {models['sonnet']}\n"
        f"  haiku  = {models['haiku']}"
    )


if __name__ == "__main__":
    switch_model()
