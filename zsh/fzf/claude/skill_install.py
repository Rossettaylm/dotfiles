#!/usr/bin/env python3
"""通过 fzf 交互式搜索并安装 Claude Code skill。

三个来源：
1. skills.sh (npx skills find)
2. ComposioHQ/awesome-claude-skills (GitHub)
3. hesreallyhim/awesome-claude-code 收录的仓库 (GitHub)

无参数从缓存加载全量列表，传参直接搜索 skills.sh。
"""

import json
import os
import re
import subprocess
import sys
from time import time as get_now_time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pyutils import shell

_SKILLS_DIR = os.path.expanduser("~/.claude/skills")
_DIR = os.path.dirname(__file__)
_CACHE_FILE = os.path.join(_DIR, "skill_cache.txt")
_CACHE_MAX_AGE_DAYS = 3

# ── skills.sh 搜索分类 ──────────────────────────────────────────
_SEARCH_CATEGORIES = [
    "react", "nextjs", "python", "rust", "go", "typescript", "docker",
    "deploy", "git", "test", "review", "security", "database", "api",
    "css", "design", "performance", "debug", "documentation", "mcp",
    "mobile", "swift", "kotlin", "flutter", "ai", "llm", "agent",
    "aws", "azure", "gcp", "kubernetes", "terraform",
]

# ── GitHub 来源 ──────────────────────────────────────────────────
_COMPOSIO_REPO = "ComposioHQ/awesome-claude-skills"
_COMPOSIO_BRANCH = "master"
_COMPOSIO_SKIP = {"template-skill", "skill-share"}

_AWESOME_REPOS = [
    "avifenesh/agentsys",
    "robertguss/claude-skills",
    "akin-ozer/cc-devops-skills",
    "undeadlist/claude-code-agents",
    "fcakyon/claude-codex-settings",
    "K-Dense-AI/claude-scientific-skills",
    "zarazhangrui/codebase-to-course",
    "skills-directory/skill-codex",
    "EveryInc/compound-engineering-plugin",
    "NeoLabHQ/context-engineering-kit",
    "affaan-m/everything-claude-code",
    "jeffallan/claude-skills",
    "jawwadfirdousi/agent-skills",
    "obra/superpowers",
    "trailofbits/skills",
    "glittercowboy/taches-cc-resources",
    "alonw0/web-asset-generator",
]


# ── 缓存格式 ─────────────────────────────────────────────────────
# skill_name \t source(npx|github) \t install_ref \t extra_info
#
# npx:    skill_name \t npx \t owner/repo@skill \t 316.5K installs
# github: skill_name \t github \t owner/repo:path:branch \t repo desc


def _gh_api(endpoint: str):
    """通过 gh CLI 访问 GitHub API（自带认证，不受 rate limit 限制）。"""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return None


# ── skills.sh 来源 ───────────────────────────────────────────────

def _parse_skills_output(raw: str) -> list[str]:
    results = []
    for line in raw.splitlines():
        cleaned = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if "@" in cleaned and "/" in cleaned and not cleaned.startswith("└"):
            parts = cleaned.split()
            if parts:
                pkg = parts[0]
                installs = " ".join(parts[1:]) if len(parts) > 1 else ""
                name = pkg.split("@")[-1] if "@" in pkg else pkg
                results.append(f"{name}\tnpx\t{pkg}\t{installs}")
    return results


def _search_npx(query: str) -> list[str]:
    try:
        result = subprocess.run(
            ["npx", "skills", "find", query],
            capture_output=True, text=True, timeout=60,
        )
        return _parse_skills_output(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ── GitHub 来源 ──────────────────────────────────────────────────

def _fetch_composio_skills() -> list[str]:
    """从 ComposioHQ/awesome-claude-skills 获取 skill 列表。"""
    data = _gh_api(f"repos/{_COMPOSIO_REPO}/contents/?ref={_COMPOSIO_BRANCH}")
    if not data:
        return []
    results = []
    for item in data:
        if item.get("type") != "dir":
            continue
        name = item["name"]
        if name.startswith(".") or name in _COMPOSIO_SKIP:
            continue
        ref = f"{_COMPOSIO_REPO}:{name}:{_COMPOSIO_BRANCH}"
        results.append(f"{name}\tgithub\t{ref}\tComposioHQ")
    return results


def _dir_has_file(repo: str, path: str, filename: str) -> bool:
    """检查 repo 指定路径下是否有某文件。"""
    data = _gh_api(f"repos/{repo}/contents/{path}")
    if not data or not isinstance(data, list):
        return False
    return any(f.get("name") == filename and f.get("type") == "file" for f in data)


def _list_subdirs(repo: str, path: str = "") -> list[str]:
    """列出 repo 指定路径下的子目录名。"""
    endpoint = f"repos/{repo}/contents/{path}" if path else f"repos/{repo}/contents"
    data = _gh_api(endpoint)
    if not data or not isinstance(data, list):
        return []
    return [
        item["name"] for item in data
        if item.get("type") == "dir" and not item["name"].startswith(".")
    ]


def _detect_branch(repo: str) -> str:
    """检测仓库默认分支。"""
    data = _gh_api(f"repos/{repo}")
    if data and isinstance(data, dict):
        return data.get("default_branch", "main")
    return "main"


def _fetch_awesome_repo_skills(repo: str) -> list[str]:
    """扫描一个 awesome-claude-code 收录的仓库，支持多种目录结构：

    结构 A: 根目录有 SKILL.md（单 skill 仓库）
    结构 B: 子目录各有 SKILL.md（如 ComposioHQ、jeffallan/claude-skills）
    结构 C: plugins/<name>/skills/<name>/SKILL.md（如 trailofbits/skills）
    结构 D: 子目录下有 skills/ 子目录含 SKILL.md
    """
    owner = repo.split("/")[0]
    branch = _detect_branch(repo)

    root_data = _gh_api(f"repos/{repo}/contents")
    if not root_data or not isinstance(root_data, list):
        return []

    root_files = {f["name"] for f in root_data if f.get("type") == "file"}
    root_dirs = [d["name"] for d in root_data if d.get("type") == "dir" and not d["name"].startswith(".")]

    results = []

    # 结构 A: 根目录直接有 SKILL.md
    if "SKILL.md" in root_files:
        name = repo.split("/")[-1]
        results.append(f"{name}\tgithub\t{repo}:.:{branch}\t{owner}")

    # 检查 plugins/ 目录（结构 C）
    if "plugins" in root_dirs:
        for plugin in _list_subdirs(repo, "plugins"):
            skill_dirs = _list_subdirs(repo, f"plugins/{plugin}/skills")
            if skill_dirs:
                for sd in skill_dirs:
                    path = f"plugins/{plugin}/skills/{sd}"
                    if _dir_has_file(repo, path, "SKILL.md"):
                        results.append(f"{sd}\tgithub\t{repo}:{path}:{branch}\t{owner}")
            elif _dir_has_file(repo, f"plugins/{plugin}", "SKILL.md"):
                results.append(f"{plugin}\tgithub\t{repo}:plugins/{plugin}:{branch}\t{owner}")

    # 检查根目录下的子目录（结构 B / D）
    skip = {"plugins", "docs", "tests", "test", ".github", "hooks", "commands", "agents"}
    for d in root_dirs:
        if d in skip:
            continue
        # 结构 B: 子目录直接有 SKILL.md
        if _dir_has_file(repo, d, "SKILL.md"):
            results.append(f"{d}\tgithub\t{repo}:{d}:{branch}\t{owner}")
            continue
        # 结构 D: 子目录下有 skills/ 含 SKILL.md
        skill_sub = _list_subdirs(repo, f"{d}/skills")
        for sd in skill_sub:
            path = f"{d}/skills/{sd}"
            if _dir_has_file(repo, path, "SKILL.md"):
                results.append(f"{sd}\tgithub\t{repo}:{path}:{branch}\t{owner}")
        # 结构 E: 子目录下的子目录直接含 SKILL.md（如 scientific-skills/astropy/SKILL.md）
        if not skill_sub:
            grandchildren = _list_subdirs(repo, d)
            if grandchildren and _dir_has_file(repo, f"{d}/{grandchildren[0]}", "SKILL.md"):
                for gc in grandchildren:
                    path = f"{d}/{gc}"
                    results.append(f"{gc}\tgithub\t{repo}:{path}:{branch}\t{owner}")

    return results


def _fetch_all_awesome_skills() -> list[str]:
    """扫描所有 awesome-claude-code 仓库。"""
    results = []
    total = len(_AWESOME_REPOS)
    for i, repo in enumerate(_AWESOME_REPOS, 1):
        sys.stdout.write(f"\r  扫描仓库 [{i}/{total}]: {repo:<45}")
        sys.stdout.flush()
        results.extend(_fetch_awesome_repo_skills(repo))
    return results


# ── 缓存管理 ─────────────────────────────────────────────────────

def _update_cache():
    shell.log_plain("正在更新 skill 缓存（首次较慢）...")
    seen = set()
    all_items = []

    # 1) skills.sh
    shell.log_plain("[1/3] 搜索 skills.sh ...")
    total = len(_SEARCH_CATEGORIES)
    for i, cat in enumerate(_SEARCH_CATEGORIES, 1):
        sys.stdout.write(f"\r  搜索分类 [{i}/{total}]: {cat:<20}")
        sys.stdout.flush()
        for item in _search_npx(cat):
            name = item.split("\t")[0]
            if name not in seen:
                seen.add(name)
                all_items.append(item)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    shell.log_success(f"  skills.sh: {len(all_items)} 个")

    # 2) ComposioHQ
    shell.log_plain("[2/3] 扫描 ComposioHQ/awesome-claude-skills ...")
    count_before = len(all_items)
    for item in _fetch_composio_skills():
        name = item.split("\t")[0]
        if name not in seen:
            seen.add(name)
            all_items.append(item)
    shell.log_success(f"  ComposioHQ: +{len(all_items) - count_before} 个")

    # 3) awesome-claude-code repos
    shell.log_plain("[3/3] 扫描 awesome-claude-code 仓库 ...")
    count_before = len(all_items)
    for item in _fetch_all_awesome_skills():
        name = item.split("\t")[0]
        if name not in seen:
            seen.add(name)
            all_items.append(item)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    shell.log_success(f"  awesome repos: +{len(all_items) - count_before} 个")

    all_items.sort(key=lambda x: x.split("\t")[0])
    with open(_CACHE_FILE, "w") as f:
        f.write("\n".join(all_items))
    shell.log_success(f"缓存已更新，共 {len(all_items)} 个 skill")
    return all_items


def _load_cache() -> list[str]:
    if os.path.isfile(_CACHE_FILE) and os.path.getsize(_CACHE_FILE) > 0:
        age_days = (get_now_time() - os.path.getmtime(_CACHE_FILE)) / 86400
        if age_days < _CACHE_MAX_AGE_DAYS:
            with open(_CACHE_FILE) as f:
                return [l for l in f.read().splitlines() if l.strip()]
    return _update_cache()


# ── 安装逻辑 ─────────────────────────────────────────────────────

def _get_installed_skills() -> set[str]:
    if not os.path.isdir(_SKILLS_DIR):
        return set()
    return {d for d in os.listdir(_SKILLS_DIR) if os.path.isdir(os.path.join(_SKILLS_DIR, d))}


def _install_npx(install_ref: str):
    subprocess.run(["npx", "skills", "add", install_ref, "-g", "-y"])


def _install_github(install_ref: str, skill_name: str):
    """从 GitHub 下载 skill 目录到 ~/.claude/skills/。"""
    parts = install_ref.split(":")
    repo = parts[0]
    path = parts[1] if len(parts) > 1 else "."
    branch = parts[2] if len(parts) > 2 else "main"

    endpoint = f"repos/{repo}/contents/{path}?ref={branch}" if path != "." else f"repos/{repo}/contents?ref={branch}"
    data = _gh_api(endpoint)
    if not data or not isinstance(data, list):
        shell.log_err(f"无法获取 {repo}/{path} 的文件列表")
        return

    target = os.path.join(_SKILLS_DIR, skill_name)
    os.makedirs(target, exist_ok=True)

    for item in data:
        if item.get("type") != "file":
            continue
        dl_url = item.get("download_url")
        fname = item["name"]
        if not dl_url:
            continue
        fpath = os.path.join(target, fname)
        ret = subprocess.run(
            ["curl", "-sL", "-o", fpath, dl_url],
            timeout=30,
        )
        if ret.returncode != 0:
            shell.log_err(f"  下载失败: {fname}")

    shell.log_success(f"已安装到 {target}")


# ── 解析缓存行 ───────────────────────────────────────────────────

def _parse_cache_line(line: str) -> dict:
    parts = line.split("\t")
    return {
        "name": parts[0],
        "source": parts[1] if len(parts) > 1 else "npx",
        "ref": parts[2] if len(parts) > 2 else parts[0],
        "extra": parts[3] if len(parts) > 3 else "",
    }


# ── preview 命令 ─────────────────────────────────────────────────

def _preview_cmd() -> str:
    return (
        f"name=$(echo {{}} | awk '{{print $1}}'); "
        f"line=$(grep -m1 '^'\"$name\"'\\t' '{_CACHE_FILE}' 2>/dev/null); "
        f"if [ -n \"$line\" ]; then "
        f"  src=$(echo \"$line\" | cut -f2); "
        f"  ref=$(echo \"$line\" | cut -f3); "
        f"  extra=$(echo \"$line\" | cut -f4); "
        f"  if [ \"$src\" = 'npx' ]; then "
        f"    echo \"📦 $ref\"; "
        f"    [ -n \"$extra\" ] && echo \"📊 $extra\"; "
        f"    echo ''; echo \"🏪 skills.sh\"; "
        f"  else "
        f"    repo=$(echo \"$ref\" | cut -d: -f1); "
        f"    path=$(echo \"$ref\" | cut -d: -f2); "
        f"    echo \"📦 $repo/$path\"; "
        f"    [ -n \"$extra\" ] && echo \"👤 $extra\"; "
        f"    echo ''; echo \"🔗 https://github.com/$repo\"; "
        f"  fi; "
        f"fi"
    )


# ── 主逻辑 ───────────────────────────────────────────────────────

def _source_tag(source: str) -> str:
    return "[npx]" if source == "npx" else "[gh]"


def skill_install(query: str = ""):
    if query:
        shell.log_plain(f"正在搜索: {query} ...")
        items = _search_npx(query)
        if not items:
            shell.log_err(f"未找到与 '{query}' 相关的 skill")
            return
    else:
        items = _load_cache()
        if not items:
            shell.log_err("skill 列表为空")
            return

    installed = _get_installed_skills()
    entries = [_parse_cache_line(item) for item in items]

    lines = []
    for e in entries:
        marker = "  ✓" if e["name"] in installed else ""
        lines.append(f"{e['name']}{marker}")
    fzf_input = "\n".join(lines)

    entry_map = {}
    for e in entries:
        if e["name"] not in entry_map:
            entry_map[e["name"]] = e

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🧩 [Claude Skill: Install]",
        header="enter: 安装  │  ctrl-r: 刷新缓存  │  ✓ = 已安装",
        use_multi_select=True,
        query=query,
        preview=_preview_cmd(),
        preview_window="right,45%",
        preview_label="[ 📦 Detail ]",
        extra_args=["--expect", "ctrl-r"],
        as_str=True,
    )

    out, err = shell.run_shell_cmd(fzf_cmd, input=fzf_input)
    if not out:
        return

    key_pressed = out[0]
    selections = out[1:]

    if key_pressed == "ctrl-r":
        _update_cache()
        skill_install(query)
        return

    for line in selections:
        name = line.split()[0]
        entry = entry_map.get(name)
        if not entry:
            shell.log_err(f"未找到 {name} 的安装信息")
            continue

        shell.log_success(f"正在安装 {name} ({_source_tag(entry['source'])}) ...")
        if entry["source"] == "npx":
            _install_npx(entry["ref"])
        else:
            _install_github(entry["ref"], name)

    if err:
        shell.log_err(err)


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else ""
    skill_install(q)
