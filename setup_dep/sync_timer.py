"""跨平台定时同步任务配置。

- macOS: crontab
- Linux: systemd user timer
"""

import platform
import subprocess
from pathlib import Path


def _ensure_cron_entry(existing: str, marker: str, cron_line: str, description: str) -> tuple[str, bool]:
    """确保 crontab 中存在指定条目，返回 (新 crontab 内容, 是否有变更)。"""
    if marker in existing:
        return existing, False
    entry = f"{marker}\n{cron_line}"
    new_crontab = existing.rstrip("\n") + "\n" + entry + "\n"
    return new_crontab, True


def _setup_cron_macos(repo_root: Path, sync_script: Path):
    """macOS: 通过 crontab 设置定时任务"""
    ret = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
        check=False,
    )
    existing = ret.stdout if ret.returncode == 0 else ""
    changed = False

    # 1) dotfiles sync — 每天 08:00
    existing, c = _ensure_cron_entry(
        existing,
        marker="# config-repo auto sync",
        cron_line=f"0 8 * * * cd {repo_root} && {sync_script} >> {repo_root}/.sync.log 2>&1",
        description="每天 08:00 执行 sync.sh",
    )
    changed |= c

    # 2) brew cache 更新 — 每周一 06:00
    brew_cache_script = repo_root / "zsh" / "fzf" / "brew" / "update_brew_cache.py"
    brew_cache_log = repo_root / ".brew_cache.log"
    existing, c = _ensure_cron_entry(
        existing,
        marker="# brew cache weekly update",
        cron_line=f"0 6 * * 1 python3 {brew_cache_script} >> {brew_cache_log} 2>&1",
        description="每周一 06:00 更新 brew cache",
    )
    changed |= c

    # 3) claude skill cache 更新 — 每周四 06:00
    skill_cache_script = repo_root / "zsh" / "fzf" / "claude" / "update_skill_cache.py"
    skill_cache_log = Path.home() / "templog" / "update_skill_cache.log"
    existing, c = _ensure_cron_entry(
        existing,
        marker="# claude skill cache weekly update",
        cron_line=f"0 6 * * 4 python3 {skill_cache_script} >> {skill_cache_log} 2>&1",
        description="每周四 06:00 更新 claude skill cache",
    )
    changed |= c

    if not changed:
        print("crontab 定时任务已存在，跳过")
        return

    ret = subprocess.run(
        ["crontab", "-"],
        input=existing,
        text=True,
        check=False,
    )
    if ret.returncode != 0:
        print("设置 crontab 失败，请手动添加")
        return
    print("已添加 crontab 定时任务")


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

    # enable 只创建符号链接，不需要 D-Bus；daemon-reload 和 start 需要
    subprocess.run(
        ["systemctl", "--user", "enable", f"{service_name}.timer"],
        check=False,
    )

    # daemon-reload + start 在无 D-Bus user session（容器/SSH）时会失败，属正常情况
    reload_ret = subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True, check=False,
    )
    start_ret = subprocess.run(
        ["systemctl", "--user", "start", f"{service_name}.timer"],
        capture_output=True, check=False,
    )

    if reload_ret.returncode != 0 or start_ret.returncode != 0:
        print("systemd timer 已 enable，但当前无法启动（无 D-Bus user session）。"
              "下次登录桌面/图形会话后将自动生效")
    else:
        print("已启用 systemd user timer：每天 08:00 执行 sync.sh")


def setup_sync_timer(repo_root: Path):
    """设置定时同步任务（入口函数）。

    - macOS: crontab
    - Linux: systemd user timer
    - 幂等：已存在则跳过
    """
    sync_script = repo_root / "sync.sh"

    if not sync_script.exists():
        print(f"sync.sh 不存在: {sync_script}，跳过定时任务配置")
        return

    if platform.system() == "Darwin":
        _setup_cron_macos(repo_root, sync_script)
    else:
        _setup_systemd_timer(repo_root, sync_script)
