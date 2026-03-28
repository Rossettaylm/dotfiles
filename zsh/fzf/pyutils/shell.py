# -*- coding: utf-8 -*-
import os
import shlex
import subprocess
from enum import Enum


DEFAULT_FZF_OPTS = "--no-sort"

_DEFAULT_PROMPT = "  > "
_DEFAULT_POINTER = "▶"


class LogLevel(Enum):
    PLAIN = (1,)
    SUCCESS = (2,)
    FAIL = 3


# 运行一段shell命令
def run_shell_cmd(cmd, input=""):
    process = subprocess.run(
        args=cmd,
        executable="/bin/zsh",
        input=input,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    return (process.stdout.splitlines(), process.stderr.splitlines())


def run_cmd_chain(commands, init_input="", need_raise_error=False):
    """
    执行一系列命令，将前一个命令的输出作为下一个命令的输入。

    :param commands: 命令列表，每个命令是一个字符串列表，例如 [["ls", "-l"], ["grep", "example"]]
    :return: 最后一个命令的输出
    """
    if not commands:
        return ""

    # 初始化第一个命令的输入为None（从标准输入读取）
    previous_output = None if init_input.isspace() else None

    for cmd in commands:
        # 执行当前命令，将前一个命令的输出作为输入
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if previous_output else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 将前一个命令的输出传递给当前命令的输入
        stdout, stderr = process.communicate(input=previous_output)

        if process.returncode != 0:
            if need_raise_error:
                raise subprocess.CalledProcessError(
                    process.returncode, cmd, stdout, stderr
                )
            else:
                return None

        # 当前命令的输出作为下一个命令的输入
        previous_output = stdout

    if previous_output:
        return previous_output.splitlines()
    return None


# 示例用法
if __name__ == "__main__":
    commands = [["echo", "hello world"], ["grep", "hello"]]
    result = run_cmd_chain(commands)
    print(result)  # 输出: hello world


def build_fzf_cmd(
    border_label: str,
    header: str = "",
    use_multi_select: bool = False,
    query: str = "",
    prompt: str = _DEFAULT_PROMPT,
    pointer: str = _DEFAULT_POINTER,
    sort: bool = True,
    preview: str = "",
    preview_window: str = "right,70%",
    preview_label: str = "[ preview ]",
    extra_args: list[str] = [],
    as_str: bool = False,
):
    """统一的 fzf 命令构造函数。

    as_str=True  → 返回字符串（用于 shell pipe：cmd1 | fzf ...）
    as_str=False → 返回列表（用于 subprocess.Popen，避免 shell 转义问题）
    """
    fzf_opts = os.getenv("FZF_DEFAULT_OPTS", "").split()
    args: list[str] = ["fzf", "--ansi"]
    args.extend(fzf_opts)
    args.extend(DEFAULT_FZF_OPTS.split())
    args += ["--sort" if sort else "--no-sort"]
    args += ["--border-label", f" {border_label} "]
    args += ["--border-label-pos", "2"]
    args += ["--prompt", prompt]
    args += ["--pointer", pointer]
    if header:
        args += ["--header", header]
    if query:
        args += ["--query", query]
    if use_multi_select:
        args.append("-m")
    if preview:
        args += ["--preview", preview]
    args += ["--preview-window", preview_window]
    args += ["--preview-label", preview_label]
    if extra_args:
        args.extend(extra_args)

    if as_str:
        # shell 管道模式：手动引用含空格的参数
        parts = []
        i = 0
        while i < len(args):
            parts.append(shlex.quote(args[i]))
            i += 1
        return " ".join(parts)
    return args


# ── 向后兼容 wrapper ───────────────────────────────────────────

def fzf_command(
    header,
    use_multi_select=False,
    query="",
    preview="",
    preview_window="right,70%",
    preview_label="[preview]",
    sort=True,
):
    """已废弃，保留向后兼容。请使用 build_fzf_cmd(as_str=True)。"""
    return build_fzf_cmd(
        border_label=header,
        use_multi_select=use_multi_select,
        query=query,
        preview=preview,
        preview_window=preview_window,
        preview_label=preview_label,
        sort=sort,
        as_str=True,
    )


def fzf_command_list(
    header, use_multi_select=False, query="", delemiter="", preview=""
):
    """已废弃，保留向后兼容。请使用 build_fzf_cmd(as_str=False)。"""
    return build_fzf_cmd(
        border_label=header,
        use_multi_select=use_multi_select,
        query=query,
        preview=preview,
        as_str=False,
    )


_format_table = {
    LogLevel.PLAIN: "{}",
    LogLevel.SUCCESS: "\033[32m{}\033[0m",
    LogLevel.FAIL: "\033[31m{}\033[0m",
}


def _log(text, level=LogLevel.PLAIN):
    if not isinstance(level, LogLevel) or level not in _format_table:
        return
    format_str = _format_table[level]
    if isinstance(text, list):
        for line in text:
            print(format_str.format(line))
    else:
        print(format_str.format(text))


def log_err(text):
    _log(text, LogLevel.FAIL)


def log_success(text):
    _log(text, LogLevel.SUCCESS)


def log_plain(text):
    _log(text)
