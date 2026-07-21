# dotfiles

Personal macOS / Linux development environment configuration, managed as a Git repository at `~/.config`.

![Platform](https://img.shields.io/badge/platform-macOS%20%2B%20Linux-lightgrey)
![Shell](https://img.shields.io/badge/shell-zsh-blue)
![Editor](https://img.shields.io/badge/editor-neovim-green)
![Prompt](https://img.shields.io/badge/prompt-starship-ff69b4)
![License](https://img.shields.io/badge/license-MIT-orange)

## Overview

A modular, self-bootstrapping dotfiles setup covering the full terminal development workflow:

| Component | Tool |
|-----------|------|
| Editor | Neovim (lazy.nvim, custom Lua config) |
| Shell | Zsh (submodule-managed plugins, no oh-my-zsh) |
| Prompt | Starship |
| Shell history | Atuin (Ctrl-H panel) |
| Multiplexer | Tmux (Zellij-style keybinds) + Zellij |
| File manager | Yazi |
| Terminal | Ghostty |
| Fuzzy finder | FZF + custom Python tools |
| Git TUI | LazyGit |
| Window manager | *(AeroSpace config has been removed)* |

> [!NOTE]
> The repo is cross-platform: setup, sync timer and env vars all branch on `uname`. macOS is the primary target; Linux (systemd user timer, Homebrew on Linux) is supported as a secondary target.

## Prerequisites

- macOS (Apple Silicon or Intel) **or** Linux
- Python 3.11+
- macOS: Xcode Command Line Tools: `xcode-select --install`

## Installation

```bash
# 1. Clone to ~/.config (with submodules)
git clone --recursive git@github.com:Rossettaylm/config.git ~/.config

# 2. Bootstrap everything
python3 ~/.config/setup.py
```

`setup.py` runs the following steps in order:

1. Git / GitHub remote (SSH or HTTPS with PAT fallback) + submodule update
2. FZF install / link
3. Zsh plugins (submodule init: zsh-defer, fzf-tab, zsh-autosuggestions, zsh-syntax-highlighting)
4. Homebrew dependencies from `dep.txt`
5. Shell (`~/.zshrc`) + Git global config
6. Auto-sync timer (macOS crontab / Linux systemd user timer)
7. Claude Code config
8. AI notification hooks
9. Yazi plugins (`ya pkg install`)
10. Tmux plugins via TPM
11. Zellij plugins (`zjstatus.wasm`)

> [!NOTE]
> Pass `--pat TOKEN` (or set `GITHUB_PAT` / `GITHUB_TOKEN`) if SSH is unavailable. The Git step falls back to HTTPS + PAT.

## Core Components

### Neovim

Custom Lua config using **lazy.nvim** (not a LazyVim distribution). Entry point: `nvim/init.lua` → `lua/config/lazy.lua`. VSCode shares keymaps via `lua/config/vscode.lua`.

| Plugin module | Description |
|---------------|-------------|
| `lsp.lua` | lspconfig + Mason + fidget + SchemaStore (lua_ls, pyright, rust_analyzer, ts_ls, bashls, jsonls, html, cssls, lemminx) |
| `completion.lua` | blink.cmp + LuaSnip (Tab/S-Tab select, Enter confirm) |
| `fzf.lua` | fzf-lua (files, grep, buffers, registers, diagnostics, LSP, zoxide) |
| `git.lua` | gitsigns (current-line blame) + diffview + lazygit.nvim |
| `treesitter.lua` | nvim-treesitter (main branch, 20+ parsers, auto-install on FileType) |
| `treesitter_textobjects.lua` | treesitter text objects |
| `aerial.lua` | aerial.nvim code outline (treesitter / LSP / markdown backends) |
| `formatting.lua` | conform.nvim (stylua / ruff / rustfmt / shfmt / prettierd) |
| `markdown.lua` | render-markdown.nvim (in-buffer render) + markdown-preview.nvim (browser) |
| `trouble.lua` | trouble.nvim diagnostics panel |
| `dashboard.lua` | dashboard-nvim startup page (hyper theme, project/MRU) |
| `ui.lua` | which-key + lualine + bufferline + nvim-notify + indent-blankline + neoscroll |
| `tools.lua` | yazi + toggleterm + flash + nvim-surround + todo-comments + mini.ai + grug-far + nvim-autopairs |
| `colorscheme.lua` | catppuccin (mocha), transparent background |

`lua/config/` modules: `keymaps`, `options`, `autocmds`, `lazy`, `nav_mode` (full/text navigation mode logic, shown in lualine), `smart_open` (smart file-open dispatcher for fzf-lua/yazi), `vscode`.

Key bindings (selection):

| Key | Action |
|-----|--------|
| `jj` / `jk` | Exit insert mode / jump to line tail |
| `;` | Command mode |
| `(`/`)` | Line head / line tail |
| `<S-j/k/h/l>` | Move 7 lines at a time |
| `<C-h/j/k/l>` | Window navigation |
| `<leader>,` | Find files (project root) |
| `<leader><leader>` | Switch buffers |
| `<leader>pt` | Live grep (project root) |
| `<leader>sw` | Grep current word |
| `<leader>sb` | Grep in current buffer |
| `<leader>sr` | Resume last fzf search |
| `<leader>s.` | Recent files |
| `<leader>sc` | Find nvim config files |
| `<leader>o` | Symbols / outline (aerial via nav_mode) |
| `<leader>?` | Show all keymaps (which-key) |
| `gd` / `ga` / `gh` | Definition / references / hover |
| `gi` / `gs` | Implementation / type definition |
| `ge` / `gE` | Next / previous diagnostic |
| `<leader>rn` | LSP rename |
| `<leader>.` | Code action |
| `<leader>th` | Toggle inlay hints |
| `<leader>gb` | Toggle git blame |
| `<leader>gd` / `gh` / `gH` / `gc` | Diffview open / file history / branch history / close |
| `gl` | LazyGit |
| `<leader>rr` / `rw` / `rf` | Grug-far search & replace (open / current word / current file) |
| `<S-r>` | Yazi file manager |
| `<C-\`` | Floating terminal (toggleterm) |
| `s` / `S` | Flash jump / treesitter jump |
| `<leader>t` | Trouble diagnostics panel |
| `<leader>mp` | Markdown browser preview |

### Zsh

Entry: `zsh/zshrc`. Module loading order:

| File | Responsibility |
|------|----------------|
| `env.zsh` | Environment variables and PATH. Branches on `uname` (Darwin / Linux) and on `hostname` (e.g. `LYMANYANG-MC0` / `LYMANYANG-MC1`) for device-specific Java/Android/NDK/yazi/ohpm paths. |
| `plugins.zsh` | Submodule plugin loading (see below) + inlined helpers: `sudo` (double-Esc toggle), `extract`, `cd` multi-dot up-navigation (`cd ...` → up 2 levels), `google`/`baidu`/`github` web-search. |
| `mappings.zsh` | Key bindings (must load before starship to avoid zle recursion). |
| `prompt.zsh` | Starship prompt init (falls back to builtin prompt if starship missing). |
| `fzf.zsh` | FZF config and keybindings (loads eagerly for Ctrl-T / Alt-C). |
| `atuin.zsh` | Atuin history: Ctrl-H opens search panel, ↑ uses `atuin-up-search`; disables the `?` AI mode. |
| `aliases.zsh` | Aliases (`eza` → ls, `bat`-less, `btm` → top, `tldr` → man, `dust` → du, `nvim` → vi/vim). |
| `functions.zsh` | Custom functions (yazi wrapper, cmake helpers, etc.). |
| `zoxide.zsh` | zoxide integration (`cd` → `z`). |

**Plugin management**: oh-my-zsh is **no longer used**. Plugins are tracked as git submodules under `zsh/plugins/` (gitignored) and loaded by `plugins.zsh`:

- `zsh-defer` — lazy-loading enabler
- `fzf-tab` — Tab completion powered by fzf (loaded after `compinit`)
- `zsh-autosuggestions` — deferred
- `zsh-syntax-highlighting` — deferred

### FZF Tool Suite

Interactive CLI tools in `zsh/fzf/`, built on FZF + Python 3. Shared utilities in `pyutils/` (`shell.py` command runner, `git.py` git helpers). The suite is organized into subdirectories, each exposed via aliases in `aliases.zsh`.

| Category | Tools |
|----------|-------|
| **`git/`** | `gco.py` (checkout), `git_log.py`, `git_remove_branch.py`, `git_merge_branch.py`, `git_cherry_pick.py`, `git_stash.py`, `git_select_branch.py`, `git_show_branches.py`, `git_checkout_from_origin.py`, `get_cur_branch.py`, `merge_master.py` |
| **`brew/`** | `brew_install.py`, `brew_uninstall.py`, `brew_preview.sh`, `update_brew_cache.py` (+ cached JSON / online package list) |
| **`claude/`** | `skill_install.py`, `skill_manage.py`, `switch_model.py`, `update_skill_cache.py` (+ skill cache) |
| **`file/`** | `file_preview.py`, `recent_files.py` |
| **`process/`** | `kill_process.py`, `kill_socket.py` |
| **`system/`** | `app_launcher.py`, `env_browser.py`, `ssh_connect.py`, `tldr_browser.py`, `adb_device.py`, `cmd_browser.py`, `tmux_sessions.py`, `tmux_delete_session.py`, `zellij_sessions.py`, `zellij_delete_session.py` |

### Tmux

Config: `tmux/tmux.conf`. Keybind philosophy mirrors Zellij's modal model. Prefix is `Ctrl-\`. Global keys live on the Alt table (no prefix needed); sub-modes are declared in `tmux/which-key-config.yaml` and compiled to `keybinds_generated.conf` by `scripts/gen_keybinds.py` (run `prefix + R` to reload).

| Mode | Trigger | Scope |
|------|---------|-------|
| Global Alt keys | `Alt+h/j/k/l`, `Alt+1-6`, `Alt+9/0`, `Alt+e`, `Alt+w`, `Alt+f`, `Alt+a`, … | Pane nav, window switch, fzf pane/session switcher, floating popup, agent-tracker popup |
| Prefix | `Ctrl-\` | Enter command mode (which-key popup) |
| `pane_mode` | `prefix + p` | Split, resize layout, zoom, popup, rename, kill pane |
| `tab_mode` | `prefix + t` | Window management, sync panes, jump to window 1-9 |
| `resize_mode` | `prefix + r` | Interactive resize (transient, repeatable) |
| `move_mode` | `prefix + m` | Swap panes |
| `copy_mode` | `prefix + s` | Enter copy/scroll mode (vi bindings: `v` select, `y` yank to pbcopy) |
| `session_mode` | `prefix + o` | Detach / session tree |

Plugins (via TPM, in `tmux/plugins/`): `tmux-which-key`, `catppuccin/tmux` (mocha), `tmux-resurrect`, `tmux-continuum` (auto-save every 15 min, auto-restore), `tmux-cpu`.

Helper scripts in `tmux/scripts/`:

| Script | Description |
|--------|-------------|
| `fzf_agents.tmux` | MRU pane switcher (fed by `pane-focus-in` hook) |
| `fzf_sessions.tmux` | fzf session switcher with live preview |
| `fzf_utils.sh` | Shared fzf helpers |
| `gen_keybinds.py` | Compiles `which-key-config.yaml` → `keybinds_generated.conf` |
| `join_pane_to_window.sh` | Move pane to a (possibly new) window (`Alt+Shift+1-6`) |
| `layout_builder.sh` | Toggle / right / left / up / down layouts; swap panes |
| `watch_pane.sh` | Watch a command output in a pane |

> [!TIP]
> Ghostty explicitly unbinds its own split shortcuts so they don't conflict with Tmux Alt bindings.

### Zellij

Config: `zellij/config.kdl`, with layouts in `zellij/layouts/` and themes in `zellij/themes/` (rose-pine). The status-bar plugin `zjstatus.wasm` lives in `zellij/plugins/` and is installed during setup. Aliases: `zj` (zellij), `za` (attach -c), `zr` (run), `zs`/`zd` (fzf session switch/delete).

### Yazi

Terminal file manager with rich preview support via plugins declared in `yazi/package.toml` and config in `yazi/yazi.toml` / `keymap.toml` / `theme.toml`:

- Markdown → `piper` + `glow` (dark, wrapped), plus `rich-preview`
- Media → `mediainfo` (audio/subtitle/postscript), built-in video/image
- Archives → `ouch`
- CSV / JSON / Notebook / xlsx → `rich-preview`
- Binary → `hexyl` (fallback)
- Directory Git status via `git` fetcher
- Bookmarks → `yamb`
- Quick enter / lazygit / system-clipboard / chmod / diff / mount plugins

Flavors: `everforest-medium`, `kanagawa`. Openers include `edit`, `open`, `reveal`, `extract` (ouch), `open_with` (fzf picker via `scripts/open_with.sh`), `play` (mpv). WeChat mini-program files (`*.wxml` / `*.wxss`) are previewed as HTML/CSS-like code.

### Terminal & Git TUI

| Tool | Notes |
|------|-------|
| **Ghostty** | CommitMono Nerd Font, 85% opacity, purple cursor; unbinds split shortcuts to avoid Tmux conflicts |
| **LazyGit** | `lazygit/config.yml`; Neovim ↔ LazyGit bridge via `scripts/lazygit_edit.sh` |

## Scripts (`scripts/`)

| Script | Description |
|--------|-------------|
| `gpu` | Push current branch to remote |
| `cm` | Quick commit with auto-generated message |
| `nvimsh` | Fast Neovim launcher |
| `bilidown.sh` | Bilibili video downloader |
| `adb.sh` | ADB device helpers |
| `lazygit_edit.sh` | LazyGit → Neovim editor bridge |
| `open_with.sh` | fzf "open with" picker (used by Yazi) |
| `theme` | Theme switcher (catppuccin-mocha / kanagawa for tmux) |
| `ai_notify.sh` | AI agent completion notification hook |
| `skill-install.sh` | Claude skill installer wrapper |
| `rmnvimswap` | Clean up Neovim swap files |
| `rm_install_file.sh` | Clean up installer artifacts |
| `_bash_header.sh` | Shared bash header sourced by other scripts |

## Homebrew Dependencies

All packages are declared in `dep.txt`. Core tools by category:

| Category | Packages |
|----------|----------|
| Editor | `neovim` |
| Terminal | `ghostty` |
| Shell | `starship` (prompt) — *zsh is system default, atuin installed separately* |
| Multiplexer | `tmux` |
| Shell utilities | `ripgrep` `fd` `eza` `bat` `zoxide` `tldr` `dust` `tree` |
| Git | `git` `git-lfs` `git-delta` `lazygit` |
| File manager | `yazi` `chafa` `ffmpegthumbnailer` `imagemagick` `poppler` |
| Preview | `glow` `hexyl` `mediainfo` `ouch` |
| System monitoring | `bottom` `btop` `procs` |
| Fonts | `font-commit-mono-nerd-font` |
| Dev tooling | `node` `cmake` `pyright` `tree-sitter-cli` `stylua` |
| Misc | `neofetch` `clipboard` |
| AI | `claude-code` |

## Auto-sync

`sync.sh` is registered as a scheduled job during setup. On each run it:

1. Updates the `thirdparty/fzf` submodule to latest master
2. Stages all changes
3. Commits with a timestamp message
4. Pushes to the current branch on GitHub

Logs are written to `.sync.log`.

```bash
# Run manually
./sync.sh
```

The setup registers **three** scheduled jobs (idempotent):

| Job | Schedule | Platform | Target |
|-----|----------|----------|--------|
| dotfiles sync | daily 08:00 | macOS crontab | `sync.sh` |
| dotfiles sync | daily 08:00 (persistent) | Linux systemd user timer (`config-sync.timer`) | `sync.sh` |
| brew cache update | weekly Mon 06:00 | macOS crontab | `zsh/fzf/brew/update_brew_cache.py` |
| claude skill cache update | weekly Thu 06:00 | macOS crontab | `zsh/fzf/claude/update_skill_cache.py` |

## Repository Structure

`.gitignore` uses a **whitelist strategy**: all files are ignored by default (`*`), and directories are explicitly included with `!dirname/` rules. Add a new `!` rule when tracking a new config directory.

Tracked top-level directories: `zsh/`, `nvim/`, `tmux/`, `zellij/`, `yazi/`, `ghostty/`, `lazygit/`, `scripts/`, `themes/`, `bat/`, `neofetch/`, `bottom/`, `git/`, `gh/`, `starship/`, `thirdparty/` (fzf + tpm submodules), `setup_dep/`, plus root files `setup.py`, `sync.sh`, `dep.txt`, `README.md`, `CLAUDE.md`.

The whitelist is per-directory, so a few entries are narrower than they first appear — the table below mirrors the actual `.gitignore` rules:

| Path | Whitelist rule | What is actually tracked |
|------|----------------|-------------------------|
| `zsh/` | `!zsh/**` (then `zsh/plugins/`) | All of `zsh/` **except** `zsh/plugins/`; the 4 plugin submodules are still registered via `.gitmodules` and tracked as gitlinks, not as regular files |
| `nvim/` | `!nvim/init.lua`, `!nvim/lazy-lock.json`, `!nvim/lua/**` | Only `init.lua`, `lazy-lock.json`, and `lua/**` — not the rest of `nvim/` |
| `yazi/` | explicit file allowlist | Only `init.lua`, `package.toml`, `yazi.toml`, `keymap.toml`, `theme.toml` — not `yazi/**` |
| `tmux/` | `!tmux/**` (then `tmux/plugins/`) | All of `tmux/` except `tmux/plugins/` (gitignored) |
| `zellij/` | `!zellij/**` (then `zellij/plugins/`) | All of `zellij/` except `zellij/plugins/` (gitignored) |

> [!NOTE]
> A few `.gitignore` whitelist rules target directories that no longer exist in the working tree: `aerospace/`, `nvim.vim.bak/` (VimScript backup), `alacritty/`, and `thirdparty/agent-tracker/` (the latter is also **not** registered in `.gitmodules`, so it is not a submodule). Their `!` rules are inert leftovers rather than active tracking. Other local-only config dirs (e.g. `atuin/`, `nushell/`, `kitty/`, `htop/`, `iterm2/`, `raycast/`, `opencode/`) are present on disk but **not** tracked.

## Environment Variables

| Variable | Value |
|----------|-------|
| `$ZSH_HOME` | `~/.config/zsh` |
| `$ZSH_PLUGINS` | `$ZSH_HOME/plugins` |
| `$SCRIPTS_HOME` | `~/.config/scripts` |
| `$FZF_HOME` | `~/.config/thirdparty/fzf` |
| `$SOFTWARES_HOME` | `~/Softwares` |
| `$STARSHIP_CONFIG` | `~/.config/starship/starship.toml` |
| `$GITHUB_ACCOUNT_PREFIX` | `https://github.com/Rossettaylm` |
| `$EDITOR` | `nvim` |
