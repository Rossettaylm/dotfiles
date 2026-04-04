#!/usr/bin/python3
"""交互式展示当前终端环境下可用的自定义命令（alias + function + script）"""
import os
import re
import sys

from pyutils import shell

ZSH_HOME = os.getenv("ZSH_HOME", os.path.expanduser("~/.config/zsh"))
SCRIPTS_HOME = os.getenv("SCRIPTS_HOME", os.path.expanduser("~/.config/scripts"))

# 颜色标签
_C_TYPE = "\033[36m"    # cyan
_C_NAME = "\033[33m"    # yellow
_C_DESC = "\033[0m"     # reset
_C_SECTION = "\033[35m" # magenta


def parse_aliases(path):
    """解析 aliases.zsh，提取 alias 定义及其所属段落标题。"""
    entries = []
    section = ""
    section_re = re.compile(r"^#\s*──\s*(.+?)\s*─")
    alias_re = re.compile(r'^alias\s+([^=]+)=["\'](.+)["\']')

    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                m = section_re.match(line)
                if m:
                    section = m.group(1).strip()
                    continue
                m = alias_re.match(line)
                if m:
                    name = m.group(1)
                    value = m.group(2)
                    desc = f"[{section}] {value}" if section else value
                    entries.append(("alias", name, desc))
    except FileNotFoundError:
        pass
    return entries


def parse_functions(path):
    """解析 functions.zsh，提取函数名及其上方的注释作为描述。"""
    entries = []
    func_re = re.compile(r"^(?:function\s+)?(\w+)\s*\(\)\s*\{")

    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return entries

    for i, line in enumerate(lines):
        m = func_re.match(line.strip())
        if m:
            name = m.group(1)
            # 取函数上方紧邻的注释行作为描述
            desc = ""
            if i > 0:
                prev = lines[i - 1].strip()
                if prev.startswith("#"):
                    desc = prev.lstrip("# ").strip()
            entries.append(("func", name, desc))
    return entries


def parse_scripts(dirpath):
    """扫描 scripts 目录，取可执行文件，用第一行注释作为描述。"""
    entries = []
    if not os.path.isdir(dirpath):
        return entries

    for name in sorted(os.listdir(dirpath)):
        fpath = os.path.join(dirpath, name)
        if not os.path.isfile(fpath) or not os.access(fpath, os.X_OK):
            continue
        # 跳过以 . 或 _ 开头的辅助文件
        if name.startswith((".", "_")):
            continue
        desc = ""
        try:
            with open(fpath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#!"):
                        continue
                    if line == "":
                        continue
                    if line.startswith("#"):
                        desc = line.lstrip("# ").strip()
                    break
        except (OSError, UnicodeDecodeError):
            pass
        entries.append(("script", name, desc))
    return entries


def format_entry(kind, name, desc):
    """格式化为 fzf 显示行：  [type]  name  ── description"""
    tag = {"alias": "alias ", "func": "func  ", "script": "script"}[kind]
    pad_name = name.ljust(16)
    desc_part = f" ── {desc}" if desc else ""
    return f"{_C_TYPE}{tag}{_C_NAME} {pad_name}{_C_DESC}{desc_part}"


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    aliases_path = os.path.join(ZSH_HOME, "aliases.zsh")
    functions_path = os.path.join(ZSH_HOME, "functions.zsh")

    entries = []
    entries.extend(parse_aliases(aliases_path))
    entries.extend(parse_functions(functions_path))
    entries.extend(parse_scripts(SCRIPTS_HOME))

    if not entries:
        shell.log_err("未找到任何命令")
        return

    lines = [format_entry(*e) for e in entries]
    input_text = "\n".join(lines)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="📋 [Commands]",
        query=query,
        preview="",
        preview_window="hidden",
        as_str=True,
    )

    out, err = shell.run_shell_cmd(fzf_cmd, input=input_text)
    if not out:
        return

    # 提取命令名（第二列）
    for selection in out:
        # 去除 ANSI 转义后解析
        clean = re.sub(r"\033\[[0-9;]*m", "", selection).strip()
        parts = clean.split()
        if len(parts) >= 2:
            cmd_name = parts[1].split()[0]
            print(cmd_name)


if __name__ == "__main__":
    main()
