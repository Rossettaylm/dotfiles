#!/usr/bin/env zsh

# ======== 通用环境变量（所有 OS/设备共享） ========

export GITHUB_ACCOUNT_PREFIX="https://github.com/Rossettaylm"
export SCRIPTS_HOME="$HOME/.config/scripts"

export ZSH_HOME="$HOME/.config/zsh"
export ZSH="$ZSH_HOME/oh-my-zsh"
export SOFTWARES_HOME="$HOME/Softwares"
export FZF_HOME="$HOME/.config/thirdparty/fzf"

export PATH=$SCRIPTS_HOME:$PATH
export PATH=$HOME/.local/bin:$PATH
export PATH=$PATH:$HOME/.cargo/bin
export PATH=$PATH:/home/linuxbrew/.linuxbrew/bin

export EDITOR=nvim
export TERM=xterm-256color

# nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# ======== 按 OS 区分 ========
case $(uname) in
  Darwin)
    # --- macOS 通用 ---
    export PATH=$PATH:/opt/homebrew/bin
    export PATH="/opt/homebrew/opt/node@18/bin:$PATH"
    export XDG_CONFIG_HOME="$HOME/.config"

    # 按设备区分
    case $(hostname -s) in
      LYMANYANG-MC1)
        # Java
        export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/jbr-17.0.14/Contents/Home"
        export PATH=$JAVA_HOME/bin:$PATH

        # Android
        export ANDROID_HOME=$HOME/Library/Android/sdk
        export PATH=$PATH:$ANDROID_HOME/platform-tools

        # NDK
        export PATH=$HOME/Softwares/ndk_toolchaines_arm64/bin:$PATH

        # yazi
        export PATH=$PATH:$HOME/Softwares/yazi-aarch64-apple-darwin/

        # ohpm (HarmonyOS Package Manager)
        export PATH="$PATH:/Applications/DevEco-Studio.app/Contents/tools/ohpm/bin"

        # eigen
        export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:/opt/homebrew/Cellar/eigen/3.4.0.1/include/eigen3
        ;;
      *)
        # 新 macOS 设备在此添加
        ;;
    esac
    ;;
  Linux)
    # --- Linux 通用 ---
    export PATH=$PATH:/usr/local/mariadb/bin

    # 按设备区分
    case $(hostname -s) in
      *)
        # 新 Linux 设备在此添加
        ;;
    esac
    ;;
esac

# ======== 可选配置 ========

# proxy
# export http_proxy="http://127.0.0.1:12639"
# export https_proxy="http://127.0.0.1:12639"
# export no_proxy="*.tencent.com|*.oa.com|localhost"
