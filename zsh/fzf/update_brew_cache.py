#!/usr/bin/python3
import os

from pyutils import shell

cache_file = os.path.join(
    "{}/.config/zsh/fzf".format(os.getenv("HOME")), "brew_online_pkg_cache.txt"
)

# 通过crontab执行只有最小环境变量，这里使用绝对路径
brew_search_cmd = "/opt/homebrew/bin/brew search ''"


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
