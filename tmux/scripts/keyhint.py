#!/usr/bin/env python3
"""Alt+? key-hint popup — an fzf-searchable cheat sheet of tmux bindings.

Two sources, because tmux only records notes where a note was written:

  root table   -> `tmux list-keys -1N -T root`, i.e. the `bind -N "..."` notes
                  in tmux.conf. Read live, so it is never stale.
  prefix table -> ~/.cache/tmux/keyhint.tsv, emitted by gen_keybinds.py from
                  which-key-config.yaml. Notes are the YAML entry names.

Every row is checked against the running tmux, so the sheet never advertises a
binding that no longer exists.
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
SPEED_CACHE = CACHE_DIR / "tmux" / "keyhint.tsv"


def tmux(*args: str) -> str:
    try:
        proc = subprocess.run(["tmux", *args], capture_output=True,
                              text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout


def describe_key(key: str) -> str:
    out = re.sub(r"^M-S-", "Alt-Shift-", key)
    out = re.sub(r"^M-", "Alt-", out)
    out = re.sub(r"^C-", "Ctrl-", out)
    return out


def parse_notes(text: str) -> list[tuple[str, str]]:
    """Parse `list-keys -1N` output: '<key>  <note>', column-padded."""
    rows = []
    for line in text.splitlines():
        match = re.match(r"^(\S+)\s+(.*\S)\s*$", line)
        if match:
            rows.append((match.group(1), match.group(2)))
    return rows


def parse_live(text: str, table: str) -> dict[str, str]:
    """Map key -> command for one table, from `list-keys -T <table>`."""
    pattern = re.compile(
        r'^bind-key\s+(?:-r\s+)?-T\s+%s\s+(?:"(?P<qkey>[^"]+)"|(?P<key>\S+))\s+(?P<cmd>.*)$'
        % re.escape(table)
    )
    live: dict[str, str] = {}
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            key = match.group("qkey") or match.group("key")
            live.setdefault(key, match.group("cmd"))
    return live


def canonical_key(key: str, live_keys: dict[str, str]) -> str:
    """Collapse a CSI-u twin onto the shortcut the user actually presses.

    With `extended-keys always` a Shift combination arrives as a kitty/CSI-u
    sequence that tmux canonicalises to `M-S-*`, so a `bind -n M-S-H` in
    tmux.conf exists only as the CSI-u twin of `bind -n M-H`. Without this the
    sheet would list Alt+Shift+H three times (M-H, M-S-h, M-S-H).

    Punctuation and digits keep their unshifted twin (`M-S-?` -> `M-?`,
    `M-S-1` -> `M-1`); named keys such as `M-S-Left` are their own binding and
    are left alone.
    """
    match = re.match(r"^M-S-(\S)$", key)
    if not match:
        return key
    char = match.group(1)
    candidate = "M-" + (char.upper() if char.isalpha() else char)
    return candidate if candidate in live_keys else key


# Commands that must not fire from inside the popup. The popup holds the
# client's input queue, so anything that wants the client (detach, a nested
# popup/menu, an interactive confirm prompt) would either hang or tear down the
# popup mid-flight.
BLOCKED = (
    "detach-client", "switch-client", "display-popup", "popup",
    "display-menu", "confirm-before", "kill-server", "kill-session",
    "suspend-client", "send-prefix", "choose-tree", "choose-client",
    "choose-buffer", "copy-mode", "customize-mode",
)

# Scripts that would recurse into the popup rather than run a binding. Matched as
# a path segment because they appear inside a run-shell string.
BLOCKED_SCRIPTS = ("keyhint.py",)


def runnable(command: str) -> tuple[bool, str]:
    """Can this binding's command safely run from the popup?"""
    if not command:
        return False, "没有可执行的命令"
    for blocked in BLOCKED:
        if re.search(r"(^|[\s;])" + re.escape(blocked) + r"(\s|$)", command):
            return False, f"{blocked} 不能在弹窗内执行"
    for script in BLOCKED_SCRIPTS:
        if re.search(r"[\s;/]" + re.escape(script) + r"(\s|[\"']|$)", command):
            return False, f"{script} 不能从弹窗里再开弹窗"
    return True, ""


def run_command(command: str) -> int:
    """Execute one binding's command as if its key had been pressed.

    The stored command is a tmux command line, so it is re-split with shell
    quoting rules and handed back to tmux as argv -- that keeps quoted formats
    such as `-c "#{pane_current_path}"` in one piece.
    """
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        notify(f"命令解析失败: {exc}")
        return 1
    # A trailing empty argv entry (e.g. the `''` else-branch of if-shell) would
    # be read as a surplus argument and rejected.
    while argv and argv[-1] == "":
        argv.pop()
    if not argv:
        return 1
    proc = subprocess.run(["tmux", *argv], capture_output=True, text=True)
    if proc.returncode != 0:
        notify((proc.stderr or proc.stdout).strip() or "命令执行失败")
    return proc.returncode


def notify(message: str) -> None:
    """Show a one-line message; usable before or after the popup closes."""
    subprocess.run(["tmux", "display-message", "-d", "2000", message],
                   capture_output=True)


def live_tables() -> dict[str, dict[str, str]]:
    tables: dict[str, dict[str, str]] = {}
    for name in ("root", "prefix", "pane_mode", "tab_mode", "resize_mode",
                 "move_mode", "session_mode"):
        tables[name] = parse_live(tmux("list-keys", "-T", name), name)
    return tables


def sort_key(label: str) -> tuple[int, int, str]:
    """'Alt-?', 'Ctrl-\\ p h' -> (is_prefix, -len(label), label).

    Within each group the widest label first, so 'Ctrl-\\ p h' sorts after the
    bare 'Ctrl-\\ p' entry that introduces the sub-mode.
    """
    rank = 1 if label.startswith("Ctrl-") else 0
    return (rank, -len(label), label)


def collect() -> list[tuple[str, str, str, str, bool]]:
    """Rows of (keys, note, command, group, runnable), checked against tmux."""
    live = live_tables()
    rows: list[tuple[str, str, str, str, bool]] = []

    for key, note in parse_notes(tmux("list-keys", "-N", "-T", "root")):
        shown = canonical_key(key, live["root"])
        command = live["root"].get(shown, "")
        rows.append((describe_key(shown), note, command, "alt",
                     runnable(command)[0]))

    if SPEED_CACHE.exists():
        for line in SPEED_CACHE.read_text().splitlines():
            parts = line.split("\t")
            if len(parts) != 5:
                continue
            table, key, keys, note, command = parts
            table_live = live.get(table, {})
            if key in table_live:
                command = table_live[key]
                rows.append((keys, note, command, "prefix", runnable(command)[0]))

    # Drop the CSI-u twins that only exist to mirror a legacy Alt+Shift binding,
    # so the sheet lists each shortcut once.
    best: dict[str, tuple[str, str, str, str, bool]] = {}
    for row in rows:
        best.setdefault(row[0], row)
    rows = list(best.values())

    rows.sort(key=lambda row: sort_key(row[0]))
    return rows


def main() -> int:
    rows = collect()
    if not rows:
        return 1

    width = max(len(keys) for keys, *_ in rows)
    lines = []
    for keys, note, command, group, ok in rows:
        # Column 4 holds a shell-quoted copy of the command so the preview's
        # `{4}` expands to exactly one word; an unquoted `{3}` would be split on
        # spaces and the preview would show only the first token.
        # Column 6 marks whether the command may run from the popup.
        # fzf displays columns 1-2 only, but prints the whole line back.
        lines.append("\t".join([keys.ljust(width), note, command,
                                shlex.quote(command), group,
                                "1" if ok else "0"]))

    header = ("alt 表 = tmux 实时   prefix 表 = which-key 配置   "
              "Enter = 执行   Esc = 关闭")
    proc = subprocess.run(
        [
            "fzf",
            "--popup", "center,90%,80%",
            "--border-label", " Keybindings ",
            "--delimiter", "\t",
            "--with-nth", "1,2",
            "--nth", "1,2,3",
            "--reverse",
            "--info", "inline",
            "--header", header,
            "--preview", 'printf "\\033[2m%s\\033[0m\\n" {4}',
            "--preview-window", "down,3,border-top,wrap",
        ],
        input="\n".join(lines),
        text=True,
        capture_output=True,
    )
    # Escape leaves rc=130; anything else non-zero means fzf itself failed.
    if proc.returncode in (130,) or not proc.stdout.strip():
        return 0

    fields = proc.stdout.rstrip("\n").split("\t")
    if len(fields) < 6:
        return 0
    command, allowed = fields[2], fields[5]
    if allowed != "1":
        notify("速查表不能执行: " + (runnable(command)[1] or "不可用"))
        return 0
    return run_command(command)


if __name__ == "__main__":
    sys.exit(main())
