# dotfiles

macOS 开发环境配置仓库，位于 `~/.config`，通过 cron 定时执行 `sync.sh` 自动同步到 GitHub。

## 目录结构

```
~/.config/
├── nvim/              # Neovim（Lua，基于 lazy.nvim）
├── zsh/               # Zsh 模块化配置 + oh-my-zsh
│   └── fzf/           # FZF 交互工具集（Python）
├── ghostty/           # Ghostty 终端模拟器
├── zellij/            # Zellij 终端复用器
├── yazi/              # Yazi 文件管理器
├── aerospace/         # AeroSpace 平铺窗口管理器
├── lazygit/           # LazyGit 配置
├── scripts/           # 实用脚本
├── init_dep/          # 初始化依赖模块
├── git/               # Git 全局配置
├── bottom/            # Bottom 系统监视器
├── neofetch/          # Neofetch
├── gh/                # GitHub CLI
├── thirdparty/        # 第三方子模块（fzf）
├── sync.sh            # 自动同步脚本
├── dep.txt            # Homebrew 依赖清单
└── init_dep.py        # 一键初始化脚本
```

## 快速开始

```bash
# 1. 克隆到 ~/.config
git clone --recursive git@github.com:Rossettaylm/config.git ~/.config

# 2. 一键安装所有依赖
python3 init_dep.py
```

`init_dep.py` 会自动完成：
- 配置 Git remote 和 SSH/HTTPS 认证
- 初始化 FZF 子模块和 oh-my-zsh 插件
- 通过 Homebrew 安装 `dep.txt` 中的所有依赖
- 设置 cron 定时同步任务
- 安装 Yazi 插件

### 手动同步

```bash
./sync.sh
```

## 核心组件

### Neovim

自定义 Lua 配置，使用 **lazy.nvim** 管理插件（非 LazyVim 发行版，已迁移为独立配置）。

| 模块 | 说明 |
|------|------|
| `plugins/lsp.lua` | LSP + Mason 自动安装语言服务器 |
| `plugins/completion.lua` | blink.cmp 补全引擎 + LuaSnip |
| `plugins/fzf.lua` | fzf-lua 模糊查找（文件/grep/buffer） |
| `plugins/git.lua` | gitsigns + diffview + lazygit.nvim |
| `plugins/treesitter.lua` | Tree-sitter 语法高亮（15+ 语言） |
| `plugins/formatting.lua` | conform.nvim 格式化（stylua/ruff/rustfmt/prettier） |
| `plugins/ui.lua` | lualine + bufferline + which-key + indent-blankline + nvim-notify |
| `plugins/tools.lua` | yazi.nvim + toggleterm + flash + surround + todo-comments |
| `plugins/trouble.lua` | 诊断列表 |
| `plugins/dashboard.lua` | 启动页 |
| `plugins/colorscheme.lua` | 主题配色 |
| `plugins/markdown.lua` | Markdown 预览与渲染 |

常用快捷键：

| 快捷键 | 功能 |
|--------|------|
| `jj` | Esc（退出插入模式） |
| `;` | 进入命令模式 |
| `(` / `)` | 行首 / 行尾 |
| `<S-h/j/k/l>` | 快速移动（7 行/列） |
| `<leader>,` | 查找文件 |
| `<leader>sg` | 全局搜索（live grep） |
| `<leader><leader>` | Buffer 搜索 |
| `gd` / `ga` / `gh` | 跳转定义 / 查找引用 / 悬浮文档 |
| `<leader>rn` | LSP 重命名 |
| `<leader>.` | Code Action |
| `<S-R>` | Yazi 文件管理器 |
| `` Ctrl+` `` | 浮动终端 |

### Zsh

入口 `zsh/zshrc`，按模块加载：

| 文件 | 职责 |
|------|------|
| `env.zsh` | 环境变量、PATH |
| `aliases.zsh` | 命令别名（`eza` 替代 ls，`bat` 替代 cat，`btm` 替代 top） |
| `functions.zsh` | 自定义函数（yazi wrapper、cmake helpers） |
| `fzf.zsh` | FZF 配置与快捷键 |
| `mappings.zsh` | 键位映射 |
| `zoxide.zsh` | zoxide 集成（`cd` → `z`） |
| `macenv.zsh` | macOS 专属配置（条件加载） |

oh-my-zsh 插件：git, sudo, web-search, zsh-syntax-highlighting, zsh-autosuggestions, fzf-tab

### FZF 交互工具集

基于 FZF + Python 的交互式命令行工具，位于 `zsh/fzf/`，共享 `pyutils/` 工具库：

| 分类 | 工具 | 说明 |
|------|------|------|
| **Git** | `gco.py` | 交互式切换分支 |
| | `git_log.py` | 交互式查看 git log |
| | `git_remove_branch.py` | 交互式删除分支 |
| | `git_merge_branch.py` | 交互式合并分支 |
| | `git_cherry_pick.py` | 交互式 cherry-pick |
| | `git_stash.py` | 交互式 stash 管理 |
| | `merge_master.py` | 快速合并 master |
| | `git_select_branch.py` | 分支选择器 |
| | `git_show_branches.py` | 分支概览 |
| **Brew** | `brew_install.py` | 交互式安装 Homebrew 包 |
| | `brew_uninstall.py` | 交互式卸载 Homebrew 包 |
| **文件** | `file_preview.py` | 文件预览 |
| | `recent_files.py` | 最近打开的文件 |
| **进程** | `kill_process.py` | 交互式杀进程 |
| | `kill_socket.py` | 交互式关闭 socket |
| **系统** | `app_launcher.py` | 应用启动器 |
| | `env_browser.py` | 环境变量浏览器 |
| | `ssh_connect.py` | SSH 连接管理 |
| | `tldr_browser.py` | TLDR 交互浏览 |
| | `zellij_sessions.py` | Zellij 会话管理 |
| | `adb_device.py` | ADB 设备管理 |

### 终端与窗口管理

| 组件 | 说明 |
|------|------|
| **Ghostty** | 终端模拟器。CommitMono Nerd Font，半透明背景（85% opacity），紫色光标 |
| **Zellij** | 终端复用器。Vim 风格导航，`Alt+h/j/k/l` 切换 pane，`Alt+[/]` 切换 tab |
| **AeroSpace** | 平铺窗口管理器。自动横竖排列，鼠标跟随焦点 |

三者通过精心编排的快捷键体系协同工作，Ghostty 主动 unbind 分屏快捷键以避免与 Zellij 冲突。

### Yazi

终端文件管理器，丰富的预览插件支持：

- Markdown → glow 渲染
- 媒体文件 → mediainfo
- CSV/JSON/Notebook → rich-preview
- 压缩包 → ouch
- 二进制 → hexyl
- 目录级 Git 状态集成

插件通过 `package.toml` 声明式管理版本。

### 实用脚本 (`scripts/`)

| 脚本 | 说明 |
|------|------|
| `gpu` | 推送当前分支到 remote |
| `autocm` | 快速提交（自动生成 commit message） |
| `nvimsh` | Neovim 快速启动 |
| `bilidown.sh` | Bilibili 视频下载 |
| `adb.sh` | ADB 设备辅助 |
| `lazygit_edit.sh` | LazyGit 编辑器集成 |

## Homebrew 依赖

完整列表见 `dep.txt`，核心工具：

| 类别 | 工具 |
|------|------|
| 编辑器 | neovim |
| 终端 | ghostty, zellij |
| 文件管理 | yazi |
| Git | git, git-lfs, lazygit |
| 搜索与替代 | ripgrep, fd, eza, bat, zoxide, tldr |
| 系统监控 | bottom, htop, procs |
| 开发工具 | pyright, cmake, node, tree-sitter-cli |
| 文档与预览 | glow, hexyl, mediainfo, ouch |
| 其他 | neofetch, tree, claude-code |

## Git 管理策略

`.gitignore` 采用**白名单模式**：默认忽略所有文件（`*`），通过 `!dir/` 显式放行需要同步的配置目录。新增配置时需在 `.gitignore` 中添加对应的 `!` 规则。

自动同步通过 cron 每日执行 `sync.sh`，自动 commit + push 到 GitHub，日志记录到 `.sync.log`。

## 关键环境变量

| 变量 | 值 |
|------|-----|
| `$ZSH_HOME` | `~/.config/zsh` |
| `$SCRIPTS_HOME` | `~/.config/scripts` |
| `$FZF_HOME` | `~/.config/thirdparty/fzf` |
| `$EDITOR` | `nvim` |
