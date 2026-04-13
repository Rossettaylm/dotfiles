#!/usr/bin/python3
import json
import os
import shutil
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import shell

_dir = os.path.dirname(__file__)
cache_file = os.path.join(_dir, "brew_online_pkg_cache.txt")
desc_cache_file = os.path.join(_dir, "brew_desc_cache.json")
installed_cache_file = os.path.join(_dir, "brew_installed_cache.json")

_brew_bin = shutil.which("brew") or "/opt/homebrew/bin/brew"


def update_pkg_list():
    shell.log_plain("正在更新pkg列表...")
    out, err = shell.run_shell_cmd(f"{_brew_bin} search ''")
    if err:
        shell.log_err(err)
        return
    if out:
        with open(cache_file, "w") as f:
            f.write("\n".join(out) + "\n")
        shell.log_success("pkg列表更新成功! 数量:{}".format(len(out)))


def update_desc_cache():
    shell.log_plain("正在更新pkg描述缓存...")
    out, err = shell.run_shell_cmd(f"{_brew_bin} desc -s ''")
    if not out:
        shell.log_err(err or "没有获取到描述数据")
        return
    desc_map = {}
    for line in out:
        if line.startswith("==>"):
            continue
        parts = line.split(": ", 1)
        if len(parts) == 2:
            desc_map[parts[0].strip()] = parts[1].strip()
    with open(desc_cache_file, "w") as f:
        json.dump(desc_map, f, ensure_ascii=False)
    shell.log_success("描述缓存更新成功! 数量:{}".format(len(desc_map)))


def update_installed_cache():
    shell.log_plain("正在更新已安装包信息缓存...")
    out, err = shell.run_shell_cmd(f"{_brew_bin} info --json=v2 --installed")
    if err:
        shell.log_err(err)
        return
    raw = "\n".join(out)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        shell.log_err(f"JSON解析失败: {e}")
        return
    info_map = {}
    for f in data.get("formulae", []):
        info_map[f["name"]] = {
            "desc": f.get("desc", ""),
            "homepage": f.get("homepage", ""),
            "version": f.get("versions", {}).get("stable", ""),
            "license": f.get("license", ""),
            "deps": [d.get("name", d) if isinstance(d, dict) else d for d in f.get("dependencies", [])],
        }
    for c in data.get("casks", []):
        info_map[c["token"]] = {
            "desc": c.get("desc", ""),
            "homepage": c.get("homepage", ""),
            "version": c.get("version", ""),
            "license": "",
            "deps": [],
        }
    with open(installed_cache_file, "w") as f:
        json.dump(info_map, f, ensure_ascii=False)
    shell.log_success("已安装包缓存更新成功! 数量:{}".format(len(info_map)))


def update_cache():
    update_pkg_list()
    update_desc_cache()
    update_installed_cache()


def main():
    update_cache()


if __name__ == "__main__":
    main()
