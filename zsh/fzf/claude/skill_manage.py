#!/usr/bin/env python3
"""通过 fzf 交互式管理已安装的 Claude Code skill（删除 / 更新）。"""

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pyutils import shell

_SKILLS_DIR = os.path.expanduser("~/.claude/skills")


def _load_skills() -> list[dict]:
    """扫描已安装 skill，读取 _meta.json 获取详情。"""
    if not os.path.isdir(_SKILLS_DIR):
        return []
    skills = []
    for name in sorted(os.listdir(_SKILLS_DIR)):
        skill_dir = os.path.join(_SKILLS_DIR, name)
        if not os.path.isdir(skill_dir):
            continue
        meta_path = os.path.join(skill_dir, "_meta.json")
        info = {"name": name, "dir": skill_dir, "owner": "", "version": ""}
        if os.path.isfile(meta_path):
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                info["owner"] = meta.get("owner", "")
                ver = meta.get("latest", {}).get("version", "")
                info["version"] = ver
            except (json.JSONDecodeError, OSError):
                pass
        skills.append(info)
    return skills


def _build_display_lines(skills: list[dict]) -> str:
    if not skills:
        return ""
    return "\n".join(s["name"] for s in skills)


def _preview_skill(skill_dir: str) -> str:
    return (
        f"name=$(echo {{}} | awk '{{print $1}}'); "
        f"dir='{_SKILLS_DIR}/'\"$name\"; "
        f"meta=\"$dir/_meta.json\"; "
        f"if [ -f \"$meta\" ]; then "
        f"  owner=$(cat \"$meta\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get('owner',''))\" 2>/dev/null); "
        f"  ver=$(cat \"$meta\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get('latest',{{}}).get('version',''))\" 2>/dev/null); "
        f"  [ -n \"$owner\" ] && echo \"👤 $owner\"; "
        f"  [ -n \"$ver\" ] && echo \"📌 v$ver\"; "
        f"  echo ''; "
        f"fi; "
        f"f=\"$dir/SKILL.md\"; "
        f"if [ -f \"$f\" ]; then head -40 \"$f\"; "
        f"else echo '无 SKILL.md'; fi"
    )


def skill_manage():
    skills = _load_skills()
    if not skills:
        shell.log_err("没有已安装的 skill")
        return

    display = _build_display_lines(skills)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🧩 [Claude Skill: Manage]",
        header="enter: 删除  │  ctrl-u: 更新全部",
        use_multi_select=True,
        preview=_preview_skill(_SKILLS_DIR),
        preview_window="right,60%",
        preview_label="[ 📄 SKILL.md ]",
        extra_args=["--expect", "ctrl-u"],
        as_str=True,
    )

    out, err = shell.run_shell_cmd(fzf_cmd, input=display)
    if not out:
        return

    key_pressed = out[0]
    selections = out[1:]

    if key_pressed == "ctrl-u":
        shell.log_success("正在更新所有 skill ...")
        subprocess.run(["npx", "skills", "update"])
        return

    # 默认 enter → 删除选中的 skill
    for line in selections:
        name = line.split()[0]
        skill_dir = os.path.join(_SKILLS_DIR, name)
        if os.path.isdir(skill_dir):
            shell.log_success(f"正在删除 {name} ...")
            shutil.rmtree(skill_dir)
            shell.log_success(f"已删除 {name}")
        else:
            shell.log_err(f"skill 目录不存在: {name}")

    if err:
        shell.log_err(err)


if __name__ == "__main__":
    skill_manage()
