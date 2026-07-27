#!/usr/bin/python3
"""
[K]ill [P]rocess — 交互式选择进程并 kill
Columns: PID  USER  CPU%  MEM%  RSS  PROCESS
ctrl-o : toggle sort order (cpu ↔ mem)
"""
import re
import shlex
import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pyutils.shell as shell

SCRIPT_PATH = os.path.abspath(__file__)
SORT_FILE   = "/tmp/.kp_sort_mode"
SORT_MODES  = ["cpu", "mem"]

R    = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
RED  = "\033[91m"
YEL  = "\033[93m"
CYN  = "\033[96m"
WHT  = "\033[97m"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

SORT_ARROWS = {"cpu": "CPU%↓", "mem": "MEM%↓"}
SORT_KEYS = {
    "cpu": lambda r: -r[2],
    "mem": lambda r: -r[3],
}


# ── sort state ────────────────────────────────────────────────────────────────

def get_sort_mode() -> str:
    try:
        mode = open(SORT_FILE).read().strip()
        if mode in SORT_MODES:
            return mode
    except Exception:
        pass
    return "cpu"


def cycle_sort_mode() -> str:
    cur = get_sort_mode()
    nxt = SORT_MODES[(SORT_MODES.index(cur) + 1) % len(SORT_MODES)]
    try:
        with open(SORT_FILE, "w") as f:
            f.write(nxt)
    except Exception:
        pass
    return nxt


# ── formatting helpers ─────────────────────────────────────────────────────────

def color_pct(val: float, warn: float, crit: float) -> str:
    s = f"{val:5.1f}"
    if val >= crit:
        return f"{RED}{s}{R}"
    if val >= warn:
        return f"{YEL}{s}{R}"
    return s


def fmt_rss(kb: int) -> str:
    if kb >= 1024 * 1024:
        return f"{kb / 1048576:6.1f}G"
    if kb >= 1024:
        return f"{kb / 1024:6.1f}M"
    return f"{kb:6d}K"


def build_title(sort_by: str) -> str:
    arrow = SORT_ARROWS.get(sort_by, sort_by.upper())
    cols = (
        f"{BOLD}{WHT}"
        f"{'PID':>7}  {'USER':<12}  "
        f"{'CPU%':>5}  {'MEM%':>5}  "
        f"{'RSS':>7}  "
        f"PROCESS{R}"
    )
    hint = f"  {YEL}[{arrow}]{R}  {DIM}ctrl-o: toggle sort{R}"
    return cols + hint


# ── data fetch & format ────────────────────────────────────────────────────────

def fetch_and_sort(sort_by: str) -> list[tuple]:
    # comm = executable name only (no path, no args)
    out, _ = shell.run_shell_cmd(
        "ps -c -eo pid,user,%cpu,%mem,rss,comm 2>/dev/null | sed 1d"
    )
    rows: list[tuple] = []
    for line in out:
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        try:
            pid = int(parts[0])
            cpu = float(parts[2])
            mem = float(parts[3])
            rss = int(parts[4])
        except (ValueError, IndexError):
            continue
        rows.append((pid, parts[1], cpu, mem, rss, parts[5]))
    rows.sort(key=SORT_KEYS.get(sort_by, SORT_KEYS["cpu"]))
    return rows


def format_rows(rows: list[tuple]) -> list[str]:
    lines = []
    for pid, user, cpu, mem, rss, comm in rows:
        lines.append(
            f"{CYN}{pid:>7}{R}  "
            f"{user:<12.12}  "
            f"{color_pct(cpu, 20.0, 50.0)}  "
            f"{color_pct(mem, 10.0, 25.0)}  "
            f"{fmt_rss(rss)}  "
            f"{comm}"
        )
    return lines


# ── fzf reload target ──────────────────────────────────────────────────────────

def list_processes(cycle: bool = False) -> None:
    sort_by = cycle_sort_mode() if cycle else get_sort_mode()
    rows    = fetch_and_sort(sort_by)
    print(build_title(sort_by))
    for line in format_rows(rows):
        print(line)


# ── interactive kill loop ──────────────────────────────────────────────────────

def select_and_kill(sig: str = "9") -> bool:
    try:
        with open(SORT_FILE, "w") as f:
            f.write("cpu")
    except Exception:
        pass

    rows = fetch_and_sort("cpu")
    if not rows:
        return False

    title      = build_title("cpu")
    lines      = format_rows(rows)
    input_data = "\n".join([title] + lines)

    script_q   = shlex.quote(SCRIPT_PATH)
    reload_cmd = f"python3 {script_q} --list --cycle"
    preview_cmd = (
        r"echo {} | perl -pe 's/\x1b\[[0-9;]*m//g' | awk '{print $1}' | "
        "xargs -I% ps -p % -o pid,ppid,user,%cpu,%mem,rss,start,time,command 2>/dev/null"
    )

    fzf_cmd = shell.build_fzf_cmd(
        border_label="💀  [Kill Process]",
        header="  Tab 多选  ·  Enter kill  ·  ctrl-o 切换排序  ·  Esc quit",
        prompt="  Process > ",
        use_multi_select=True,
        sort=False,
        preview=preview_cmd,
        preview_window="up,5,border-bottom,wrap",
        preview_label="[ Process Detail ]",
        extra_args=[
            "--header-lines=1",
            "--nth=6..",
            f"--bind=ctrl-o:reload({reload_cmd})",
        ],
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input=input_data)
    if process.returncode != 0 or not stdout.strip():
        return False

    pids: list[str] = []
    for line in stdout.strip().splitlines():
        clean = ANSI_RE.sub("", line).strip()
        if clean:
            pids.append(clean.split()[0])

    for pid in pids:
        shell.run_shell_cmd(f"kill -{sig} {pid} 2>/dev/null")
        shell.log_success(f"killed pid {pid}")
    return True


def main() -> None:
    if "--list" in sys.argv:
        list_processes(cycle="--cycle" in sys.argv)
        return

    non_flags = [a for a in sys.argv[1:] if not a.startswith("--")]
    sig = non_flags[0] if non_flags else "9"
    while select_and_kill(sig):
        pass


if __name__ == "__main__":
    main()
