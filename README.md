# dotfiles

Personal macOS development environment configuration, managed as a Git repository at `~/.config`.

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Shell](https://img.shields.io/badge/shell-zsh-blue)
![Editor](https://img.shields.io/badge/editor-neovim-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Overview

A modular, self-bootstrapping dotfiles setup covering the full terminal development workflow:

| Component | Tool |
|-----------|------|
| Editor | Neovim (lazy.nvim, custom Lua config) |
| Shell | Zsh + oh-my-zsh |
| Multiplexer | Tmux (Zellij-style keybinds) |
| File manager | Yazi |
| Terminal | Ghostty |
| Window manager | AeroSpace |
| Fuzzy finder | FZF + custom Python tools |
| Git TUI | LazyGit |

## Prerequisites

- macOS (Apple Silicon or Intel)
- Python 3.11+
- Xcode Command Line Tools: `xcode-select --install`

## Installation

```bash
# 1. Clone to ~/.config (with submodules)
git clone --recursive git@github.com:Rossettaylm/config.git ~/.config

# 2. Bootstrap everything
python3 ~/.config/setup.py
```

`setup.py` runs the following steps in order:

1. Configure Git remote (SSH or HTTPS with PAT fallback)
2. Update submodules (fzf, oh-my-zsh)
3. Initialize Zsh plugins (syntax-highlighting, autosuggestions, fzf-tab)
4. Install all Homebrew dependencies from `dep.txt`
5. Apply shell and Git global config
6. Register the cron-based auto-sync job
7. Install Claude Code and AI notification hooks
8. Install Yazi plugins (`ya pkg install`)
9. Install Tmux plugins via TPM
10. Install Zellij plugins

> [!NOTE]
> Pass `--pat TOKEN` (or set `GITHUB_PAT` / `GITHUB_TOKEN`) if SSH is unavailable.

## Core Components

### Neovim

Custom Lua config using **lazy.nvim** (not a LazyVim distribution). Entry point: `nvim/init.lua`.

| Plugin module | Description |
|---------------|-------------|
| `lsp.lua` | LSP + Mason auto-installer |
| `completion.lua` | blink.cmp + LuaSnip |
| `fzf.lua` | fzf-lua (files, grep, buffers) |
| `git.lua` | gitsigns + diffview + lazygit.nvim |
| `treesitter.lua` | Syntax highlighting (15+ languages) |
| `formatting.lua` | conform.nvim (stylua / ruff / rustfmt / prettier) |
| `ui.lua` | lualine + bufferline + which-key + indent-blankline |
| `tools.lua` | yazi.nvim + toggleterm + flash + surround |
| `colorscheme.lua` | kanagawa-wave, transparent background |

Key bindings (selection):

| Key | Action |
|-----|--------|
| `jj` | Exit insert mode |
| `;` | Command mode |
| `<leader>,` | Find files |
| `<leader>sg` | Live grep |
| `<leader><leader>` | Buffer search |
| `gd` / `ga` / `gh` | Definition / references / hover |
| `<leader>rn` | LSP rename |
| `<leader>.` | Code action |
| `<S-R>` | Yazi file manager |
| `Ctrl+\`` | Floating terminal |

### Zsh

Entry: `zsh/zshrc`. Modular layout:

| File | Responsibility |
|------|----------------|
| `env.zsh` | Environment variables and PATH |
| `aliases.zsh` | Aliases (`eza` → ls, `bat` → cat, `btm` → top) |
| `functions.zsh` | Custom functions (yazi wrapper, cmake helpers) |
| `fzf.zsh` | FZF config and keybindings |
| `mappings.zsh` | Key mappings |
| `zoxide.zsh` | zoxide integration (`cd` → `z`) |
| `macenv.zsh` | macOS-specific config (conditionally loaded) |

oh-my-zsh plugins: `git sudo web-search zsh-syntax-highlighting zsh-autosuggestions fzf-tab`

### Tmux

Config: `tmux/tmux.conf`. Keybind philosophy mirrors Zellij's modal model:

| Mode | Trigger | Scope |
|------|---------|-------|
| Global Alt keys | `Alt+h/j/k/l`, `Alt+[/]` | Pane navigation, window switch |
| Prefix | `Ctrl+\` | Enter command mode |
| `pane_mode` | `prefix + p` | Split, resize, kill panes |
| `tab_mode` | `prefix + t` | Window management |
| `resize_mode` | `prefix + r` | Interactive resize |
| `session_mode` | `prefix + o` | Session switching |

FZF-powered pane/session switchers (`tmux/scripts/`) provide MRU-ordered navigation with live preview.

### FZF Tool Suite

Interactive CLI tools in `zsh/fzf/`, built on FZF + Python 3. Shared utilities in `pyutils/`.

| Category | Tools |
|----------|-------|
| **Git** | `gco.py` (checkout), `git_log.py`, `git_remove_branch.py`, `git_merge_branch.py`, `git_cherry_pick.py`, `git_stash.py` |
| **Homebrew** | `brew_install.py`, `brew_uninstall.py` |
| **Files** | `file_preview.py`, `recent_files.py` |
| **Process** | `kill_process.py`, `kill_socket.py` |
| **System** | `app_launcher.py`, `env_browser.py`, `ssh_connect.py`, `tldr_browser.py`, `adb_device.py` |

### Yazi

Terminal file manager with rich preview support via plugins (`yazi/plugins/`):

- Markdown → glow
- Media → mediainfo + ffmpegthumbnailer
- CSV / JSON / Notebook → rich-preview
- Archives → ouch
- Binary → hexyl
- Directory Git status integration

Plugin versions are declared in `yazi/package.toml`.

### Terminal & Window Management

| Tool | Notes |
|------|-------|
| **Ghostty** | CommitMono Nerd Font, 85% opacity, purple cursor |
| **AeroSpace** | Tiling WM, auto horizontal/vertical layout, mouse-follows-focus |
| **LazyGit** | Neovim editor integration via `scripts/lazygit_edit.sh` |

> [!TIP]
> Ghostty explicitly unbinds its own split shortcuts so they don't conflict with Tmux bindings.

## Scripts (`scripts/`)

| Script | Description |
|--------|-------------|
| `gpu` | Push current branch to remote |
| `autocm` | Quick commit with auto-generated message |
| `nvimsh` | Fast Neovim launcher |
| `bilidown.sh` | Bilibili video downloader |
| `adb.sh` | ADB device helpers |
| `lazygit_edit.sh` | LazyGit → Neovim editor bridge |

## Homebrew Dependencies

All packages are declared in `dep.txt`. Core tools by category:

| Category | Packages |
|----------|----------|
| Editor | `neovim` |
| Terminal | `ghostty` |
| Shell utilities | `ripgrep` `fd` `eza` `bat` `zoxide` `tldr` `dust` |
| Git | `git` `git-lfs` `git-delta` `lazygit` |
| File manager | `yazi` `chafa` `ffmpegthumbnailer` `imagemagick` `poppler` |
| Preview | `glow` `hexyl` `mediainfo` `ouch` |
| System monitoring | `bottom` `btop` `procs` |
| Dev tooling | `node` `cmake` `pyright` `tree-sitter-cli` `stylua` |
| AI | `claude-code` |

## Auto-sync

`sync.sh` is registered as a cron job during setup. On each run it:

1. Updates `thirdparty/fzf` and `zsh/oh-my-zsh` submodules to latest
2. Stages all changes
3. Commits with timestamp message
4. Pushes to the current branch on GitHub

Logs are written to `.sync.log`.

```bash
# Run manually
./sync.sh
```

## Repository Structure

`.gitignore` uses a **whitelist strategy**: all files are ignored by default (`*`), and directories are explicitly included with `!dirname/` rules. Add a new `!` rule when tracking a new config directory.

## Environment Variables

| Variable | Value |
|----------|-------|
| `$ZSH_HOME` | `~/.config/zsh` |
| `$SCRIPTS_HOME` | `~/.config/scripts` |
| `$FZF_HOME` | `~/.config/thirdparty/fzf` |
| `$EDITOR` | `nvim` |
