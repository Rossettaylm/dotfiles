#!/bin/zsh

source $ZSH_HOME/aliases.zsh
CUR_BRANCH="$(curb)"

git checkout master
git pull
git checkout ${CUR_BRANCH}
git merge master

unset CUR_BRANCH
