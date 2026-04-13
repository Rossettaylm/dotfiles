#!/bin/bash
# fzf preview script for brew packages
# 优先从本地缓存读取，未命中时 fallback 到 brew info
PKG="$1"
DIR="$(cd "$(dirname "$0")" && pwd)"
DESC_CACHE="$DIR/brew_desc_cache.json"
INSTALLED_CACHE="$DIR/brew_installed_cache.json"

# 已安装包：从 installed_cache 读取详细信息
if [[ -f "$INSTALLED_CACHE" ]]; then
    info=$(python3 -c "
import json,sys
pkg = sys.argv[1]
with open(sys.argv[2]) as f:
    data = json.load(f)
if pkg in data:
    d = data[pkg]
    print(f'📦 {pkg}')
    print(f'   Version:  {d[\"version\"]}')
    print(f'   Desc:     {d[\"desc\"]}')
    print(f'   Homepage: {d[\"homepage\"]}')
    if d.get('license'):
        print(f'   License:  {d[\"license\"]}')
    if d.get('deps'):
        print(f'   Deps:     {\", \".join(d[\"deps\"])}')
    print()
    print('✅ Installed')
" "$PKG" "$INSTALLED_CACHE" 2>/dev/null)
    if [[ -n "$info" ]]; then
        echo "$info"
        exit 0
    fi
fi

# 未安装包：从 desc_cache 读取描述
if [[ -f "$DESC_CACHE" ]]; then
    desc=$(python3 -c "
import json,sys
pkg = sys.argv[1]
with open(sys.argv[2]) as f:
    data = json.load(f)
if pkg in data:
    print(data[pkg])
" "$PKG" "$DESC_CACHE" 2>/dev/null)
    if [[ -n "$desc" ]]; then
        echo "📦 $PKG"
        echo "   Desc: $desc"
        echo ""
        echo "⚪ Not installed"
        exit 0
    fi
fi

# Fallback: 直接调用 brew info
brew info "$PKG" 2>/dev/null
