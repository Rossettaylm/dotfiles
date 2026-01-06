#!/usr/bin/env zsh

# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH
#
export GITHUB_ACCOUNT_PREFIX="https://github.com/Rossettaylm"
export SCRIPTS_HOME="$HOME/.config/scripts"

# Path to your oh-my-zsh installation.
export ZSH_HOME="$HOME/.config/zsh"
export ZSH="$ZSH_HOME/oh-my-zsh"
export SOFTWARES_HOME="$HOME/Softwares"
export FZF_HOME="$HOME/.config/thirdparty/fzf"

export PATH=$SCRIPTS_HOME:$PATH
export PATH=$HOME/.local/bin:$PATH
export PATH=$PATH:/usr/local/mariadb/bin
export PATH=$PATH:/opt/homebrew/bin/

export EDITOR=nvim
export TERM=xterm-256color

export PATH="/opt/homebrew/opt/node@18/bin:$PATH"

# java home
export JAVA_HOME="$SOFTWARES_HOME/TencentJDK17/Contents/Home"
export PATH=$JAVA_HOME/bin:$PATH

# Android home
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools

#NDK
export PATH=$HOME/Softwares/ndk_toolchaines_arm64/bin:$PATH

# cargo
export PATH=$PATH:$HOME/.cargo/bin

# yazi
export PATH=$PATH:$HOME/Softwares/yazi-aarch64-apple-darwin/

# nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# ohpm (HarmonyOS Package Manager)
export PATH="$PATH:/Applications/DevEco-Studio.app/Contents/tools/ohpm/bin"




#zlib ark
# export LDFLAGS="-L/opt/homebrew/opt/zlib/lib"
# export CPPFLAGS="-I/opt/homebrew/opt/zlib/include"

# proxy
# export http_proxy="http://127.0.0.1:12639"
# export https_proxy="http://127.0.0.1:12639"
# export no_proxy="*.tencent.com|*.oa.com|localhost"
