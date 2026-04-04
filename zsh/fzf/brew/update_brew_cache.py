#!/usr/bin/python3
import os
import shutil
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

cache_file = os.path.join(os.path.dirname(__file__), "brew_online_pkg_cache.txt")

# 通过crontab执行只有最小环境变量，优先使用 PATH 中的 brew，回退到常见绝对路径
_brew_bin = shutil.which("brew") or "/opt/homebrew/bin/brew"
brew_search_cmd = f"{_brew_bin} search ''"


def update_cache():
    with open(cache_file, "w+") as cache:
        shell.log_plain("正在更新pkg cache...")
        out, err = shell.run_shell_cmd(brew_search_cmd)
        if out:
            for line in out:
                cache.write(line + "\n")
        if err:
            shell.log_err(err)
        else:
            shell.log_success("更新成功! pkg数:{}".format(len(out)))


def main():
    update_cache()


if __name__ == "__main__":
    main()
