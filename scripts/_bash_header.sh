#!/bin/bash

# -x 执行命令之前打印展开后的命令
# -e 遇到命令失败(返回非0),立即退出,如需要这个返回值,可以使用cmd | RET="$?"
# -u 试图使用未定义的变量就立即退出,如果确实需要可
# -o pipefail 只要管道中某一个子命令失败,则管道命令失败
# -eo pipefail 只要管道中子命令失败则退出脚本
set -xeou pipefail
# 意外退出时杀掉所有子进程
trap 'trap - SIGTERM && kill -- -$$' SIGINT SIGTERM EXIT
