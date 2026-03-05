# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

macOS 开发环境的 dotfiles 配置仓库，位于 `~/.config`，通过 cron 定时执行 `sync.sh` 自动提交并推送到 GitHub。

## 常用命令

```bash
# 手动同步配置到 GitHub
./sync.sh

# 安装全部 Homebrew 依赖（从 dep.txt 读取）
python3 init_dep.py
```

## 仓库架构

### Git 管理策略

`.gitignore` 采用**白名单模式**：默认忽略所有文件，通过 `!dir/` 显式包含需要同步的配置目录。新增配置目录时必须在 `.gitignore` 中添加对应的 `!dirname/` 规则。

### Zsh 配置 (`zsh/`)

入口文件 `zshrc`，按模块化加载：
- `env.zsh` → 环境变量和 PATH（`$ZSH_HOME` = `~/.config/zsh`）
- `aliases.zsh` → 命令别名
- `functions.zsh` → 自定义函数（ranger_cd, yazi wrapper, cmake helpers）
- `fzf.zsh` → FZF 配置和快捷键绑定
- `mappings.zsh` → 键位映射
- `zoxide.zsh` → zoxide 集成（`cd` 被重映射为 `z`）
- `macenv.zsh` → macOS 专属配置（条件加载）

Zsh 插件通过 oh-my-zsh 管理（`zsh/oh-my-zsh/`），启用的插件：git, sudo, web-search, zsh-syntax-highlighting, zsh-autosuggestions, fzf-tab。

### FZF 工具脚本 (`zsh/fzf/`)

一组基于 FZF 的 Python/Shell 脚本，提供交互式 Git 操作：
- `gco.sh` → 交互式 checkout 分支
- `git_log.py` → 交互式查看 git log
- `git_remove_branch.py` / `git_merge_branch.py` → 交互式删分支/合并
- `brew_install.py` / `brew_uninstall.py` → 交互式 brew 包管理

Python 脚本共享 `pyutils/` 模块（`shell.py` 封装命令执行，`git.py` 封装 Git 操作）。

### Neovim (`nvim/`)

基于 **LazyVim** 框架，入口 `init.lua` → `config/lazy.lua`。自定义配置在：
- `lua/config/` → keymaps, options, autocmds
- `lua/plugins/` → 插件配置覆盖（lsp, treesitter, mason, fzf, yazi）
- `lua/self-plugins/` → 自定义插件

### 其他配置目录

- `alacritty/` → 终端模拟器
- `zellij/` → 终端复用器
- `yazi/` → 终端文件管理器（含主题和插件）
- `aerospace/` → 平铺式窗口管理器
- `lazygit/` → Git TUI
- `scripts/` → 实用脚本（`gpu` 推送当前分支, `autocm` 快速提交, `nvimsh` 等）
- `nvim.vim.bak/` → 旧版 VimScript 配置备份

### 关键环境变量

| 变量 | 值 |
|------|-----|
| `$ZSH_HOME` | `~/.config/zsh` |
| `$SCRIPTS_HOME` | `~/.config/scripts` |
| `$FZF_HOME` | `~/.config/thirdparty/fzf` |
| `$EDITOR` | `nvim` |

## 编辑注意事项

- Shell 脚本和 zsh 配置保持 POSIX 兼容 + zsh 扩展风格
- FZF Python 脚本使用 Python 3，依赖 `pyutils/` 包
- Neovim 配置遵循 LazyVim 的覆盖约定（在 `lua/plugins/` 下返回 table）
- `dep.txt` 每行一个 Homebrew 包名
- 别名定义集中在 `aliases.zsh`，函数定义集中在 `functions.zsh`
