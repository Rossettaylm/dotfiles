# -*- coding: utf-8 -*-
import os
import shlex
import subprocess
from enum import Enum


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


def fzf_command(
    header,
    use_multi_select=False,
    query="",
    preview="",
    preview_window="right,70%",
    preview_label="[preview]",
):
    cmd = "fzf --ansi {default_opts} --header='{header}' {multi_select} --preview-window='{preview_window}' --preview-label='{preview_label}' --query='{query}'".format(
        default_opts=os.getenv("FZF_DEFAULT_OPTS"),
        header=header,
        multi_select="-m" if use_multi_select else "",
        preview_window=preview_window,
        query=query,
        preview_label=preview_label,
    )
    if preview:
        cmd = cmd + " " + preview
    return cmd


# fg+ 字体颜色
def fzf_command_list(
    header, use_multi_select=False, query="", delemiter="", preview=""
):
    fzf_opts = os.getenv("FZF_DEFAULT_OPTS", "").split(sep=" ")
    cmd = ["fzf"]
    if fzf_opts:
        cmd.extend(fzf_opts)
    cmd.append(
        f"--header={header}",
    )
    if query:
        cmd.append("--query")
        cmd.append(query)
    if use_multi_select:
        cmd.append("-m")
    if delemiter:
        cmd.append("--delemiter")
        cmd.append(delemiter)
    if preview:
        cmd.append("--preview")
        cmd.append(preview)
    return cmd


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
