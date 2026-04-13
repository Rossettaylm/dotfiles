import os
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell
from time import time as get_now_time
from update_brew_cache import update_cache

_dir = os.path.dirname(__file__)
cache_file = os.path.join(_dir, "brew_online_pkg_cache.txt")
preview_script = os.path.join(_dir, "brew_preview.sh")


def check_cache_available():
    if os.path.isfile(cache_file):
        mtime = os.path.getmtime(cache_file)
        nowtime = get_now_time()
        if os.path.getsize(cache_file) == 0 or (nowtime - mtime) / (60 * 60 * 24) >= 7:
            update_cache()
    else:
        update_cache()


def brew_install(query=""):
    check_cache_available()
    cmd = shell.build_fzf_cmd(
        border_label="🍺 [Brew: Install]",
        header="enter: brew install │ ctrl-k: brew install --cask",
        use_multi_select=True,
        query=query,
        preview=f"bash {preview_script} {{}}",
        preview_label="[ 📦 Package Info ]",
        extra_args=["--expect", "ctrl-k"],
        as_str=True,
    )
    with open(cache_file, "r") as cache:
        out, err = shell.run_shell_cmd(cmd, input=cache.read())
        if out:
            key_pressed = out[0]
            packages = out[1:]
            use_cask = key_pressed == "ctrl-k"
            for ins in packages:
                if use_cask:
                    shell.log_success("正在安装(cask) {}...".format(ins))
                    subprocess.run(["brew", "install", "--cask", ins])
                else:
                    shell.log_success("正在安装{}...".format(ins))
                    subprocess.run(["brew", "install", ins])
        if err:
            shell.log_err(err)


if __name__ == "__main__":
    query = ""
    if len(sys.argv) > 1:
        query = sys.argv[1]
    brew_install(query)
