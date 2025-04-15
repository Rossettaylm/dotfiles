import os
import sys
from pyutils import shell
from time import time as get_now_time

cache_file = os.path.join(
    "{}/fzf".format(os.getenv("ZSH_HOME")), "brew_online_pkg_cache.txt"
)


def check_cache_available():
    if os.path.isfile(cache_file):
        mtime = os.path.getmtime(cache_file)
        nowtime = get_now_time()
        if os.path.getsize(cache_file) == 0 or (nowtime - mtime) / (60 * 60 * 24) >= 7:
            update_cache()
    else:
        update_cache()


def update_cache():
    with open(cache_file, "w+") as cache:
        shell.log_plain("正在更新pkg cache...")
        out, err = shell.run_shell_cmd("brew search ''")
        for line in out:
            cache.write(line + "\n")
        if err:
            shell.log_err(err)
        else:
            shell.log_success("更新成功! pkg数:{}".format(len(out)))


def brew_install(query=""):
    check_cache_available()
    cmd = shell.fzf_command(header="[brew install]", use_multi_select=True, query=query)
    with open(cache_file, "r") as cache:
        out, err = shell.run_shell_cmd(cmd, input=cache.read())
        if out:
            for ins in out:
                shell.log_success("正在安装{}...".format(ins))
                os.system("brew install {}".format(ins))
        if err:
            shell.log_err(err)


if __name__ == "__main__":
    query = ""
    if len(sys.argv) > 1:
        query = sys.argv[1]
    brew_install(query)
