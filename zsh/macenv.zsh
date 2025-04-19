export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:/opt/homebrew/Cellar/eigen/3.4.0.1/include/eigen3


#llvm
export PATH=$PATH:/opt/homebrew/opt/llvm/bin

# trash-cli on macos
export PATH=$PATH:/opt/homebrew/Cellar/trash-cli/0.24.5.26/bin

#rust 
export PATH=$PATH:/opt/homebrew/Cellar/rust/1.83.0/bin

# mac
# 禁止合盖休眠
alias dislid='sudo pmset -b sleep 0; sudo pmset -b displaysleep 0; sudo pmset -b disablesleep 1'
# 启动合盖休眠
alias enlid='sudo pmset -b sleep 15; sudo pmset -b displaysleep 10; sudo pmset -b disablesleep 0'
