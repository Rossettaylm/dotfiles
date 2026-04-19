"""AI 通知 Hooks 注入：将统一通知 hook 写入 Claude / CodeBuddy 配置。"""

import json
from pathlib import Path

HOOK_SCRIPT = Path.home() / ".config" / "scripts" / "ai_notify.sh"

HOOKS_CONFIG = {
    "Stop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"bash {HOOK_SCRIPT} stop",
                    "async": True,
                }
            ]
        }
    ],
    "Notification": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"bash {HOOK_SCRIPT} notification",
                    "async": True,
                }
            ]
        }
    ],
}

TARGETS = [
    Path.home() / ".claude" / "settings.json",
    Path.home() / ".claude-internal" / "settings.json",
    Path.home() / ".codebuddy" / "settings.json",
]


def inject_ai_hooks():
    """向目标 settings.json 注入 Stop / Notification hooks（幂等）。

    - 保留文件中已有的其他字段和其他 hook 事件
    - 仅覆盖 Stop 和 Notification 两个事件
    - 文件或目录不存在时自动创建
    """
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            try:
                settings = json.loads(target.read_text())
            except (json.JSONDecodeError, ValueError):
                settings = {}
        else:
            settings = {}

        hooks = settings.setdefault("hooks", {})
        hooks["Stop"] = HOOKS_CONFIG["Stop"]
        hooks["Notification"] = HOOKS_CONFIG["Notification"]

        target.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
        print(f"  已注入 hooks → {target}")
