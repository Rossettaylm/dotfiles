import subprocess
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell


def brew_uninstall(query=""):
    ret = subprocess.run(["brew", "leaves"], capture_output=True, text=True)
    if not ret.stdout.strip():
        shell.log_err("没有已安装的包")
        return

    fzf_cmd = shell.build_fzf_cmd(border_label="🗑️  [Brew: Uninstall]", use_multi_select=True, query=query, as_str=True)
    out, err = shell.run_shell_cmd(fzf_cmd, input=ret.stdout)
    if out:
        for uins in out:
            shell.log_success("正在卸载{}...".format(uins))
            subprocess.run(["brew", "uninstall", uins])
    if err:
        shell.log_err(err)


if __name__ == "__main__":
    query = ""
    if len(sys.argv) > 1:
        query = sys.argv[1]
    brew_uninstall(query)
