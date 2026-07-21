"""交互式切换 Claude Code / Codex / pi 模型组。

模型组定义了 opus / sonnet / haiku 三个槽位的模型，切换时同步更新：
- ~/.claude.json           → Claude Code 环境变量
- ~/.codex/config.toml     → Codex model 字段
- ~/.pi/agent/settings.json → pi defaultModel（不含 [1m] 后缀）
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
CODEX_CONFIG = os.path.expanduser("~/.codex/config.toml")
PI_CONFIG = os.path.expanduser("~/.pi/agent/settings.json")

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


# ── Codex ──────────────────────────────────────────────────


def update_codex_model(model_id: str):
    """更新 ~/.codex/config.toml 中的 model 字段。"""
    try:
        with open(CODEX_CONFIG, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        shell.log_err(f"无法读取 codex config: {CODEX_CONFIG}")
        return

    new_content = re.sub(
        r'^model\s*=\s*"[^"]*"',
        f'model = "{model_id}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    atomic_write(CODEX_CONFIG, new_content)


# ── pi ─────────────────────────────────────────────────────


def update_pi_model(model_id: str):
    """更新 ~/.pi/agent/settings.json 中的 defaultModel（不含 [1m] 后缀）。"""
    pi_model = strip_context_suffix(model_id)
    data = read_json(PI_CONFIG)
    data["defaultModel"] = pi_model
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

    # 同步三个配置
    update_claude_env(models)
    update_codex_model(models["opus"])
    update_pi_model(models["opus"])

    shell.log_success(
        f"已切换模型组: {current_group or '未设置'} → {selected}\n"
        f"  opus   = {models['opus']}\n"
        f"  sonnet = {models['sonnet']}\n"
        f"  haiku  = {models['haiku']}"
    )


if __name__ == "__main__":
    switch_model()
