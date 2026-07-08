import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

# 模型组：每组对应 opus / sonnet / haiku 三个槽位
MODEL_GROUPS = {
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

ENV_KEYS = {
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}

config_file = os.path.expanduser("~/.claude.json")
codex_config_file = os.path.expanduser("~/.codex/config.toml")


def read_config():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def detect_current_group(env):
    for name, models in MODEL_GROUPS.items():
        if all(env.get(ENV_KEYS[slot]) == model for slot, model in models.items()):
            return name
    return None


def write_config(data):
    dir_name = os.path.dirname(config_file)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
        os.replace(tmp_path, config_file)
    except BaseException:
        os.unlink(tmp_path)
        raise


def update_codex_model(model_id):
    try:
        with open(codex_config_file, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(
            r'^model\s*=\s*"[^"]*"',
            f'model = "{model_id}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        dir_name = os.path.dirname(codex_config_file)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                tmp.write(new_content)
            os.replace(tmp_path, codex_config_file)
        except BaseException:
            os.unlink(tmp_path)
            raise
    except OSError as e:
        shell.log_err(f"更新 codex config 失败: {e}")


def format_group_line(name, models, is_current):
    detail = f"{models['opus']} / {models['sonnet']} / {models['haiku']}"
    if is_current:
        return f"\033[32m● {name}\033[0m  {detail}"
    return f"  {name}  {detail}"


def switch_model():
    data = read_config()
    env = data.get("env", {})
    current_group = detect_current_group(env)

    lines = []
    for name, models in MODEL_GROUPS.items():
        lines.append(format_group_line(name, models, name == current_group))

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

    # 提取组名（第一个非空 token，跳过可能的 "●"）
    tokens = out[0].split()
    selected = next((t for t in tokens if t in MODEL_GROUPS), None)
    if not selected:
        shell.log_err("无法解析选择")
        return

    if selected == current_group:
        shell.log_plain(f"未变更，仍为 {selected}")
        return

    models = MODEL_GROUPS[selected]
    data.setdefault("env", {})
    for slot, key in ENV_KEYS.items():
        data["env"][key] = models[slot]

    data["env"]["ANTHROPIC_MODEL"] = models["opus"]

    write_config(data)
    update_codex_model(models["opus"])
    shell.log_success(
        f"已切换模型组: {current_group or '未设置'} → {selected}\n"
        f"  opus   = {models['opus']}\n"
        f"  sonnet = {models['sonnet']}\n"
        f"  haiku  = {models['haiku']}"
    )


if __name__ == "__main__":
    switch_model()
