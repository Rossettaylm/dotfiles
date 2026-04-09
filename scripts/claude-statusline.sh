#!/usr/bin/env bash
# Claude Code statusline — Catppuccin Mocha palette
# Receives JSON on stdin: { model, workspace, cost, context_window }

read -r INPUT

MODEL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model',''))" 2>/dev/null)
COST=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cost',''))" 2>/dev/null)
CTX=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('context_window',{}); used=d.get('used',0); total=d.get('total',1); pct=int(used/total*100); print(f'{pct}%')" 2>/dev/null)

# Catppuccin Mocha ANSI 256-approx colors
MAROON='\033[38;2;235;160;172m'   # #eba0ac
GREEN='\033[38;2;166;227;161m'    # #a6e3a1
LAVENDER='\033[38;2;180;190;254m' # #b4befe
PEACH='\033[38;2;250;179;135m'    # #fab387
SUBTEXT='\033[38;2;166;173;200m'  # #a6adc8
RESET='\033[0m'

echo -e "${MAROON}♥${RESET} ${LAVENDER}${MODEL}${RESET} ${SUBTEXT}│${RESET} ${PEACH}\$${COST}${RESET} ${SUBTEXT}│${RESET} ${GREEN}ctx ${CTX}${RESET}"
