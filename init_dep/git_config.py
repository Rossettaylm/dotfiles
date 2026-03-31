"""Git 全局配置初始化。"""

import subprocess

# gitconfig 模板：仅保留通用、跨平台内容
# 去除：[user]（隐私）、[credential]（平台相关）、公司内网 LFS 端点、
#       BeyondCompare mergetool/difftool（macOS 路径硬编码）、
#       [protocol] version=1（旧版内网兼容）、[http] postBuffer（内网大仓库专用）
GITCONFIG_TEMPLATE = """\
[core]
    quotepath = false
    longpaths = true
    autocrlf = false
    trustctime = false
    excludesfile = ~/.gitignore_global
    attributesfile = ~/.attributes_global
    ignorecase = true
    untrackedcache = true
    safecrlf = false
    eol = lf
[filter "lfs"]
    clean = git-lfs clean -- %f
    smudge = git-lfs smudge -- %f
    process = git-lfs filter-process
    required = true
[diff "text"]
    textconv = cat
[mergetool]
    keepBackup = false
    writeToTemp = true
[lfs]
    concurrenttransfers = 32
    fetchrecentrefsdays = 0
    pruneoffsetdays = 0
    dialtimeout = 3
    tlstimeout = 3
[lfs "transfer"]
    maxretries = 1
    maxretrydelay = 2
[rebase]
    backend = merge
[pull]
    rebase = false
[safe]
    directory = *
[init]
    defaultBranch = master
[gui]
    encoding = utf-8
[alias]
    st = status
    co = checkout
    ci = commit
    br = branch
"""


def setup_gitconfig():
    """将通用 gitconfig 写入 ~/.gitconfig。

    采用 git config 逐条写入而非直接覆盖文件，
    以便与用户已有的 [user] 等配置安全共存。
    已存在相同 key 时直接覆盖，不会产生重复项。
    """
    import configparser
    import re

    print("正在配置 ~/.gitconfig ...")
    parser = configparser.RawConfigParser()
    parser.read_string(GITCONFIG_TEMPLATE)

    for section in parser.sections():
        # 处理带子节的 section，如 filter "lfs" -> filter.lfs
        m = re.fullmatch(r'(\S+)\s+"([^"]+)"', section)
        if m:
            git_section = f"{m.group(1)}.{m.group(2)}"
        else:
            git_section = section

        for key, value in parser.items(section):
            ret = subprocess.run(
                ["git", "config", "--global", f"{git_section}.{key}", value],
                check=False,
            )
            if ret.returncode != 0:
                print(f"  警告: 设置 [{section}] {key} 失败，跳过")
    print("~/.gitconfig 配置完成")
