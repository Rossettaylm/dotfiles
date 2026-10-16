"""跨平台定时同步任务配置。

- macOS: crontab
- Linux: systemd user timer；systemd user manager 不可达（容器 / 纯 SSH）时回退 crontab
"""

import platform
import shutil
import subprocess
from pathlib import Path

SYNC_MARKER = "# config-repo auto sync"
BREW_CACHE_MARKER = "# brew cache"
SKILL_CACHE_MARKER = "# claude skill cache weekly update"


def _ensure_cron_entry(existing: str, marker: str, cron_line: str) -> tuple[str, bool]:
    """确保 crontab 中存在指定条目，返回 (新 crontab 内容, 是否有变更)。"""
    if marker in existing:
        return existing, False
    entry = f"{marker}\n{cron_line}"
    new_crontab = f"{existing.rstrip()}\n{entry}\n" if existing.strip() else f"{entry}\n"
    return new_crontab, True


def _cron_entries(repo_root: Path) -> list[tuple[str, str]]:
    """返回 (marker, cron 行) 列表，macOS 与 Linux 共用。"""
    brew_cache_script = repo_root / "zsh" / "fzf" / "brew" / "update_brew_cache.py"
    skill_cache_script = repo_root / "zsh" / "fzf" / "claude" / "update_skill_cache.py"
    templog = Path.home() / "templog"

    return [
        (SYNC_MARKER,
         f"0 8 * * * cd {repo_root} && ./sync.sh >> {repo_root}/.sync.log 2>&1"),
        (BREW_CACHE_MARKER,
         f"0 6 * * * python3 {brew_cache_script} >> {repo_root}/.brew_cache.log 2>&1"),
        (SKILL_CACHE_MARKER,
         f"0 6 * * 4 python3 {skill_cache_script} >> {templog}/update_skill_cache.log 2>&1"),
    ]


def _setup_crontab(repo_root: Path) -> bool:
    """通过 crontab 设置定时任务，返回是否配置成功。"""
    if not shutil.which("crontab"):
        print("未找到 crontab 命令，无法配置定时任务")
        return False

    # 日志目录不存在时 cron 重定向会失败
    (Path.home() / "templog").mkdir(parents=True, exist_ok=True)

    ret = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    existing = ret.stdout if ret.returncode == 0 else ""

    changed = False
    for marker, cron_line in _cron_entries(repo_root):
        existing, c = _ensure_cron_entry(existing, marker, cron_line)
        changed |= c

    if not changed:
        print("crontab 定时任务已存在，跳过")
        return True

    ret = subprocess.run(["crontab", "-"], input=existing, text=True, check=False)
    if ret.returncode != 0:
        print("设置 crontab 失败，请手动添加")
        return False
    print("已添加 crontab 定时任务")
    return True


def _systemd_user_available() -> bool:
    """探测 systemd user manager 是否可达（无 D-Bus 时不可达，timer 不会运行）。"""
    if not shutil.which("systemctl"):
        return False
    ret = subprocess.run(
        ["systemctl", "--user", "show-environment"],
        capture_output=True,
        check=False,
    )
    return ret.returncode == 0


def _setup_systemd_timer(repo_root: Path, sync_script: Path):
    """Linux: 通过 systemd user timer 设置定时任务"""
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)

    service_name = "config-sync"
    service_file = unit_dir / f"{service_name}.service"
    timer_file = unit_dir / f"{service_name}.timer"

    service_content = f"""\
[Unit]
Description=Sync config repo to GitHub

[Service]
Type=oneshot
WorkingDirectory={repo_root}
ExecStart={sync_script}
StandardOutput=append:{repo_root}/.sync.log
StandardError=append:{repo_root}/.sync.log
"""

    timer_content = """\
[Unit]
Description=Daily config repo sync timer

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    if service_file.exists() and timer_file.exists():
        if service_file.read_text() == service_content and \
                timer_file.read_text() == timer_content:
            print("systemd timer 已存在且配置一致，跳过")
            return

    service_file.write_text(service_content)
    timer_file.write_text(timer_content)
    print(f"已写入 {service_file} 和 {timer_file}")

    subprocess.run(
        ["systemctl", "--user", "enable", f"{service_name}.timer"],
        check=False,
    )
    subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["systemctl", "--user", "start", f"{service_name}.timer"],
        capture_output=True, check=False,
    )
    print("已启用 systemd user timer：每天 08:00 执行 sync.sh")


def setup_sync_timer(repo_root: Path):
    """设置定时同步任务（入口函数）。

    - macOS: crontab
    - Linux: systemd user timer；不可用时回退 crontab
    - 幂等：已存在则跳过
    """
    sync_script = repo_root / "sync.sh"

    if not sync_script.exists():
        print(f"sync.sh 不存在: {sync_script}，跳过定时任务配置")
        return

    if platform.system() == "Darwin":
        _setup_crontab(repo_root)
        return

    if _systemd_user_available():
        _setup_systemd_timer(repo_root, sync_script)
    else:
        print("systemd user manager 不可达，回退到 crontab")
        _setup_crontab(repo_root)
