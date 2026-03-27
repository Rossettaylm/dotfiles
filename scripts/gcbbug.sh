#!/bin/bash

_git_checkout_branch_with_name() {
  local BRANCH_NAME="personal/lymanyang_bugfix_$1"
  local REFERENCE=$2

  local CMD="git checkout -b $BRANCH_NAME $REFERENCE"
  exec $CMD
}

_git_checkout_branch_with_name "$@"
