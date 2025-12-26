import os
import sys

from pyutils import shell
from update_brew_cache import cache_file


def brew_install(query=""):
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
