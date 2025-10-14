# 🎨 Lyman's .config 配置文件集合

> 🌟 **一站式 macOS 开发环境配置仓库**  
> 📅 **最后更新**: 2025-10-14  
> 🌿 **当前分支**: macos

---

## 📋 目录

- [✨ 项目简介](#-项目简介)
- [🛠️ 核心工具配置](#️-核心工具配置)
- [📂 目录结构](#-目录结构)
- [🔧 自动化脚本](#-自动化脚本)
- [📦 安装指南](#-安装指南)
- [🚀 快速上手](#-快速上手)
- [📝 更新日志](#-更新日志)

---

## ✨ 项目简介

这是我的 macOS 开发环境配置文件集合，包含了终端、编辑器、窗口管理等各类开发工具的精心配置。所有配置都经过实际使用优化，专注于提升开发效率和使用体验。

### 🎯 特色亮点

- 🎨 **美观实用** - 精心调配的主题配色和界面布局
- ⚡ **高效快捷** - 丰富的快捷键绑定和自动化脚本
- 🔄 **自动同步** - 内置 Git 自动同步脚本，配置永不丢失
- 🧩 **模块化** - 清晰的目录结构，方便按需使用
- 📱 **跨平台** - 部分配置支持多平台使用

---

## 🛠️ 核心工具配置

### 🖥️ **终端相关**
- **🐚 Zsh** - 强大的 shell 配置，包含别名、函数、环境变量
- **🎨 Alacritty** - GPU 加速终端模拟器配置
- **📊 Zellij** - 现代化终端复用器配置
- **🔍 Neofetch** - 系统信息展示工具

### 📝 **编辑器配置**
- **⚡ Neovim** - 现代化 Vim 配置 (LazyVim)
- **🗂️ Yazi** - 终端文件管理器，包含丰富插件
- **🎯 LazyGit** - Git 图形界面工具配置

### 🪟 **窗口管理**
- **🚀 AeroSpace** - 平铺式窗口管理器

---

## 📂 目录结构

```
.config/
├── 🚀 aerospace/          # AeroSpace 窗口管理器配置
├── 🎨 alacritty/          # Alacritty 终端配置
├── 📊 zellij/             # Zellij 终端复用器配置
├── ⚡ nvim/               # Neovim 主配置
├── 🗂️ yazi/               # Yazi 文件管理器配置
├── 🐚 zsh/                # Zsh Shell 配置
├── 🎯 lazygit/            # LazyGit 配置
├── 🛠️ scripts/            # 实用脚本集合
├── 📦 thirdparty/         # 第三方工具
├── 🔧 sync.sh             # 自动同步脚本
└── 📋 其他配置文件...
```

### 📁 详细说明

#### 🐚 **zsh/** - Shell 配置核心
- `aliases.zsh` - 常用命令别名
- `functions.zsh` - 自定义函数
- `env.zsh` - 环境变量配置
- `fzf.zsh` - 模糊查找配置
- `zoxide.zsh` - 智能目录跳转

#### ⚡ **nvim/** - 编辑器配置
- 基于 **LazyVim** 框架
- 丰富的插件配置
- 优化的按键映射
- 支持多种编程语言

#### 🗂️ **yazi/** - 文件管理器
- 自定义按键映射
- 精美主题配置
- 实用插件集成
- 文件预览优化

#### 🛠️ **scripts/** - 工具脚本
- `autocm` - 自动提交脚本
- `gpu` - GPU 状态监控
- `nvimsh` - Neovim 快速启动
- `dpui` - Docker 管理界面

---

## 🔧 自动化脚本

### 📜 **sync.sh** - 智能同步脚本

这个脚本提供了完整的配置文件自动同步功能：

**✨ 主要功能:**
- 🔍 **智能检测** - 自动检测文件变更
- 📝 **详细日志** - 记录每次同步的具体文件变更
- 🌿 **分支感知** - 自动推送到对应的远程分支
- ⏰ **定时执行** - 通过 cron 定时自动同步
- 🛡️ **错误处理** - 完善的错误处理和日志记录

**⏰ 定时任务:**
```bash
# 每天上午 9:00 自动执行同步
0 9 * * * cd /Users/lyman/.config && /Users/lyman/.config/sync.sh
```

---

## 📦 安装指南

### 🚀 快速安装

1. **克隆仓库**
   ```bash
   git clone <repository-url> ~/.config
   cd ~/.config
   ```

2. **安装依赖**
   ```bash
   python3 init_dep.py  # 安装 Python 依赖
   ```

3. **设置权限**
   ```bash
   chmod +x sync.sh
   chmod +x scripts/*
   ```

4. **启用自动同步**
   ```bash
   # 添加 cron 任务（可选）
   crontab -e
   # 添加: 0 9 * * * cd ~/.config && ~/.config/sync.sh >> ~/.config/cron.log 2>&1
   ```

---

## 🚀 快速上手

### 🎯 **推荐工作流**

1. **🔧 安装核心工具**
   ```bash
   # 安装 Homebrew（如果还没安装）
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # 安装核心工具
   brew install zsh alacritty neovim yazi lazygit zellij
   ```

2. **⚡ 启用配置**
   ```bash
   # 使用 Zsh 配置
   source ~/.config/zsh/zshrc
   
   # 启动 Neovim（会自动安装插件）
   nvim
   ```

3. **🎨 个性化定制**
   - 修改 `zsh/aliases.zsh` 添加个人别名
   - 调整 `alacritty/alacritty.toml` 终端外观
   - 在 `nvim/` 中添加个人插件配置

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

- 🐛 **报告问题** - 发现 bug 请创建 Issue
- ✨ **功能建议** - 有好想法欢迎讨论
- 🔧 **配置分享** - 分享你的配置优化

---

## 📄 许可证

本项目遵循个人使用许可，请根据需要进行引用和修改。

---

<div align="center">

**🌟 如果这些配置对你有帮助，请给个 Star！**

*Built with ❤️ by Lyman*

</div>
