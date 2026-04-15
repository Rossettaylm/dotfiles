import subprocess
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

_dir = os.path.dirname(__file__)
preview_script = os.path.join(_dir, "brew_preview.sh")


def brew_uninstall(query=""):
    formula = subprocess.run(["brew", "leaves"], capture_output=True, text=True)
    cask = subprocess.run(["brew", "list", "--cask"], capture_output=True, text=True)
    cask_lines = [f"{c} [cask]" for c in cask.stdout.strip().splitlines() if c]
    combined = (formula.stdout.strip() + "\n" + "\n".join(cask_lines)).strip()
    if not combined:
        shell.log_err("没有已安装的包")
        return

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🗑️  [Brew: Uninstall]",
        use_multi_select=True,
        query=query,
        preview=f"bash {preview_script} {{1}}",
        preview_label="[ 📦 Package Info ]",
        as_str=True,
    )
    out, err = shell.run_shell_cmd(fzf_cmd, input=combined + "\n")
    if out:
        for uins in out:
            pkg = uins.split()[0]
            shell.log_success("正在卸载{}...".format(pkg))
            subprocess.run(["brew", "uninstall", pkg])
    if err:
        shell.log_err(err)


if __name__ == "__main__":
    query = ""
    if len(sys.argv) > 1:
        query = sys.argv[1]
    brew_uninstall(query)
