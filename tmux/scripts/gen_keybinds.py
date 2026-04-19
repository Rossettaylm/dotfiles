#!/usr/bin/env python3
"""Generate tmux bind -T keybindings from which-key-config.yaml.

Usage: python3 gen_keybinds.py
Reads:  ~/.config/tmux/which-key-config.yaml
Writes: ~/.config/tmux/keybinds_generated.conf
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip3 install pyyaml")

CONFIG_DIR = Path(__file__).resolve().parent.parent
YAML_PATH = CONFIG_DIR / "which-key-config.yaml"
OUTPUT_PATH = CONFIG_DIR / "keybinds_generated.conf"


def mode_name(display_name: str) -> str:
    """'+Pane' -> 'pane_mode', '+Tab' -> 'tab_mode', etc."""
    return re.sub(r"^\+", "", display_name).lower() + "_mode"


def expand_macro(macro_name: str, macros: list[dict]) -> str:
    for m in macros:
        if m["name"] == macro_name:
            return " \\; ".join(m["commands"])
    return ""


def quote_format_vars(cmd: str) -> str:
    """Ensure #{...} variables in tmux commands are properly quoted.

    Wraps bare #{...} tokens (those not already inside quotes) with double quotes.
    e.g. 'split-window -v -c #{pane_current_path}' ->
         'split-window -v -c "#{pane_current_path}"'

    Leaves #{...} inside quoted strings untouched.
    """
    if "#{" not in cmd:
        return cmd

    result = []
    i = 0
    in_double = False
    in_single = False
    while i < len(cmd):
        ch = cmd[i]
        if ch == '"' and not in_single:
            in_double = not in_double
            result.append(ch)
            i += 1
        elif ch == "'" and not in_double:
            in_single = not in_single
            result.append(ch)
            i += 1
        elif cmd[i:i+2] == '#{' and not in_double and not in_single:
            # Find closing }
            end = cmd.find('}', i)
            if end == -1:
                result.append(ch)
                i += 1
            else:
                token = cmd[i:end+1]
                result.append(f'"{token}"')
                i = end + 1
        else:
            result.append(ch)
            i += 1
    return "".join(result)


def generate(config: dict) -> list[str]:
    lines: list[str] = []
    lines.append("# Auto-generated from which-key-config.yaml")
    lines.append("# Do not edit — run: python3 ~/.config/tmux/scripts/gen_keybinds.py")
    lines.append("")

    macros = config.get("macros", [])
    items = config.get("items", [])

    prefix_binds: list[str] = []
    mode_sections: list[str] = []

    for item in items:
        if "separator" in item:
            continue

        key = item.get("key")
        name = item.get("name", "")
        menu = item.get("menu")
        command = item.get("command")
        macro = item.get("macro")

        if menu:
            # Sub-mode: generate switch-client and bind -T entries
            table = mode_name(name)
            prefix_binds.append(f"bind {key} switch-client -T {table}")

            section_lines = [f"# ─── {name.lstrip('+')} mode (prefix + {key}) ───"]
            for entry in menu:
                if "separator" in entry:
                    continue
                ekey = entry.get("key")
                ecmd = entry.get("command", "")
                emacro = entry.get("macro")
                transient = entry.get("transient", False)

                if emacro:
                    ecmd = expand_macro(emacro, macros)

                ecmd = quote_format_vars(ecmd)

                repeat = "-r " if transient else ""
                section_lines.append(
                    f"bind -T {table} {repeat}{ekey} {ecmd}"
                )
            mode_sections.append("\n".join(section_lines))

        elif command:
            prefix_binds.append(f"bind {key} {quote_format_vars(command)}")

        elif macro:
            expanded = expand_macro(macro, macros)
            if expanded:
                prefix_binds.append(f"bind {key} {expanded}")

    lines.append("# Prefix bindings (enter sub-modes or direct commands)")
    lines.extend(prefix_binds)
    lines.append("")

    for section in mode_sections:
        lines.append(section)
        lines.append("")

    return lines


def main():
    if not YAML_PATH.exists():
        sys.exit(f"Config not found: {YAML_PATH}")

    with open(YAML_PATH) as f:
        config = yaml.safe_load(f)

    output = generate(config)
    OUTPUT_PATH.write_text("\n".join(output) + "\n")
    print(f"Generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
