#!/usr/bin/python3
from sys import argv
import pyutils.shell as shell
import os


def show_zellij_sessions_in_fzf() -> str:
    fzf_cmd = shell.fzf_command_list(header="[ZELLIJ SESSIONS]", use_multi_select=False)
    # zellij ls 默认最旧在前，reverse layout 下 FZF 会倒置显示
    # 用 tac 翻转使 FZF 中最旧在顶部、最新在底部（光标默认位置）
    result = shell.run_cmd_chain(commands=[["zellij", "list-sessions"], ["tail", "-r"], fzf_cmd])
    if result is None:
        return ""
    if len(result) <= 0:
        return ""
    session_list = result[0].split(" ")
    if len(session_list) > 0:
        return session_list[0]
    else:
        return ""


def main():
    if len(argv) > 1:
        session = argv[1]  # 自定输入session,直接进入
        attach_session(session)
        exit(0)

    session = show_zellij_sessions_in_fzf()
    if len(session) <= 0:
        shell.log_err("获取session错误!")
        exit(-1)
    attach_session(session)


def attach_session(session: str):
    shell.log_success("正在进入session:{}".format(session))
    os.system("zellij attach -c {}".format(session))


if __name__ == "__main__":
    main()
