import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

# 可供选择的模型列表，按需增删
MODELS = [
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "deepseek-v4-flash-official",
    "deepseek-v4-pro-official",
]

config_file = os.path.expanduser("~/.claude.json")


def read_current_model():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("env", {}).get("ANTHROPIC_MODEL", "")
    except (OSError, json.JSONDecodeError):
        return ""


def write_model(model):
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("env", {})["ANTHROPIC_MODEL"] = model

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


def switch_model():
    current = read_current_model()
    lines = []
    for m in MODELS:
        if m == current:
            lines.append(f"\033[32m● {m}\033[0m")
        else:
            lines.append(f"  {m}")

    cmd = shell.build_fzf_cmd(
        border_label="🤖 [Claude: Switch Model]",
        header=f"enter: 切换模型 │ 当前: {current or '未设置'}",
        sort=False,
        as_str=True,
    )
    out, err = shell.run_shell_cmd(cmd, input="\n".join(lines))
    if err:
        shell.log_err(err)
    if not out:
        return

    selected = out[0].split()[-1]
    if selected == current:
        shell.log_plain(f"未变更，仍为 {selected}")
        return
    write_model(selected)
    shell.log_success(f"已切换模型: {current or '未设置'} → {selected}")


if __name__ == "__main__":
    switch_model()
