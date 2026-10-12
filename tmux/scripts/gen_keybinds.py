#!/usr/bin/env python3
"""Generate tmux bind -T keybindings and the Alt+? key-hint sheet.

Usage: python3 gen_keybinds.py
Reads:  ~/.config/tmux/which-key-config.yaml
Writes: ~/.config/tmux/keybinds_generated.conf
        ~/.cache/tmux/keyhint.tsv  (tab-separated sheet; keyhint.py reads it back)
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip3 install pyyaml")

CONFIG_DIR = Path(__file__).resolve().parent.parent
YAML_PATH = CONFIG_DIR / "which-key-config.yaml"
OUTPUT_PATH = CONFIG_DIR / "keybinds_generated.conf"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
SPEED_CACHE = CACHE_DIR / "tmux" / "keyhint.tsv"


@dataclass
class SpeedEntry:
    """One row of the Alt+? cheat sheet.

    table/livekey let keyhint.py verify the binding still exists in the running
    tmux before showing it, so the sheet never advertises a dead key.
    """

    table: str
    livekey: str
    keys: str
    note: str
    command: str


def mode_name(display_name: str) -> str:
    """'+Pane' -> 'pane_mode', '+Tab' -> 'tab_mode', etc."""
    return re.sub(r"^\+", "", display_name).lower() + "_mode"


def describe_key(tmux_key: str) -> str:
    """'M-S-Left' -> 'Alt-Shift-Left', 'C-\\\\' -> 'Ctrl-\\\\' for display."""
    out = re.sub(r"^M-S-", "Alt-Shift-", tmux_key)
    out = re.sub(r"^M-", "Alt-", out)
    out = re.sub(r"^C-", "Ctrl-", out)
    return out


def prefix_label() -> str:
    """Read the live prefix key from tmux so the sheet tracks tmux.conf."""
    try:
        out = subprocess.run(
            ["tmux", "show-options", "-g", "prefix"],
            capture_output=True, text=True, timeout=2,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "prefix"
    m = re.search(r"^prefix\s+(\S+)", out, re.M)
    return describe_key(m.group(1)) if m else "prefix"


def note_flag(note: str) -> str:
    """tmux bind -N takes the note as one quoted argument."""
    if not note:
        return ""
    escaped = note.replace("\\", "\\\\").replace('"', '\\"')
    return f'-N "{escaped}" '


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


def generate(config: dict) -> tuple[list[str], list[SpeedEntry]]:
    lines: list[str] = []
    lines.append("# Auto-generated from which-key-config.yaml")
    lines.append("# Do not edit — run: python3 ~/.config/tmux/scripts/gen_keybinds.py")
    lines.append("")

    macros = config.get("macros", [])
    items = config.get("items", [])

    pfx = prefix_label()
    prefix_binds: list[str] = []
    mode_sections: list[str] = []
    speed: list[SpeedEntry] = []

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
            note = item.get("note", "")
            prefix_binds.append(f"bind {note_flag(note)}{key} switch-client -T {table}")

            section_lines = [f"# ─── {name.lstrip('+')} mode (prefix + {key}) ───"]
            for entry in menu:
                if "separator" in entry:
                    continue
                ekey = entry.get("key")
                ecmd = entry.get("command", "")
                emacro = entry.get("macro")
                transient = entry.get("transient", False)
                enote = entry.get("note", entry.get("name", ""))

                if emacro:
                    ecmd = expand_macro(emacro, macros)

                ecmd = quote_format_vars(ecmd)

                repeat = "-r " if transient else ""
                section_lines.append(
                    f"bind {note_flag(enote)}-T {table} {repeat}{ekey} {ecmd}"
                )
                speed.append(SpeedEntry(
                    table=table,
                    livekey=ekey,
                    keys=f"{pfx} {key} {ekey}",
                    note=enote,
                    command=ecmd,
                ))
            mode_sections.append("\n".join(section_lines))
            speed.append(SpeedEntry(
                table="prefix",
                livekey=key,
                keys=f"{pfx} {key}",
                note=note or f"{name.lstrip('+')} 子模式",
                command=f"switch-client -T {table}",
            ))

        elif command:
            note = item.get("note", name)
            prefix_binds.append(
                f"bind {note_flag(note)}{key} {quote_format_vars(command)}"
            )
            speed.append(SpeedEntry(
                table="prefix",
                livekey=key,
                keys=f"{pfx} {key}",
                note=note,
                command=quote_format_vars(command),
            ))

        elif macro:
            expanded = expand_macro(macro, macros)
            if expanded:
                note = item.get("note", name)
                prefix_binds.append(f"bind {note_flag(note)}{key} {expanded}")
                speed.append(SpeedEntry(
                    table="prefix",
                    livekey=key,
                    keys=f"{pfx} {key}",
                    note=note,
                    command=expanded,
                ))

    lines.append("# Prefix bindings (enter sub-modes or direct commands)")
    lines.extend(prefix_binds)
    lines.append("")

    for section in mode_sections:
        lines.append(section)
        lines.append("")

    return lines, speed


def write_speed_cache(speed: list[SpeedEntry]) -> None:
    """Hand the sheet to keyhint.py; also usable straight from the shell:

        column -t -s $'\\t' ~/.cache/tmux/keyhint.tsv
    """
    SPEED_CACHE.parent.mkdir(parents=True, exist_ok=True)
    rows = ["\t".join([e.table, e.livekey, e.keys, e.note, e.command])
            for e in speed]
    SPEED_CACHE.write_text("\n".join(rows) + "\n")


def main():
    if not YAML_PATH.exists():
        sys.exit(f"Config not found: {YAML_PATH}")

    with open(YAML_PATH) as f:
        config = yaml.safe_load(f)

    lines, speed = generate(config)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n")
    write_speed_cache(speed)
    print(f"Generated: {OUTPUT_PATH}")
    print(f"Generated: {SPEED_CACHE}")


if __name__ == "__main__":
    main()
