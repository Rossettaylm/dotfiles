import os
import sys

from pyutils import shell


def brew_uninstall(query=""):
    brew_cmd = "brew leaves"
    fzf_cmd = shell.fzf_command("[brew:uninstall]", use_multi_select=True, query=query)
    out, err = shell.run_shell_cmd("{} | {}".format(brew_cmd, fzf_cmd))
    if out:
        for uins in out:
            shell.log_success("正在卸载{}...".format(uins))
            os.system("brew uninstall {}".format(uins))
    if err:
        shell.log_err(err)


if __name__ == "__main__":
    query = ""
    if len(sys.argv) > 1:
        query = sys.argv[1]
    brew_uninstall(query)
