# -*- coding: utf-8 -*-
import os
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


def fzf_command(header, use_multi_select=False, query=""):
    return "fzf {default_opts} --header='{header}' {multi_select} --query='{query}'".format(
        default_opts=os.getenv("FZF_DEFAULT_OPTS"),
        header=header,
        multi_select="-m" if use_multi_select else "",
        query=query,
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
