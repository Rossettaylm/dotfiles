"""Claude Code 配置初始化。"""

from pathlib import Path

CLAUDE_MD_CONTENT = """\
## Operating principles

- Prefer small, reviewable diffs. Avoid sweeping refactors unless explicitly requested.
- Before editing, identify the file(s) to change and state the plan in 3-6 bullets.
- Never invent APIs, configs, or file paths. If unsure, search the repo first.
- Keep changes consistent with existing style and architecture.

## Safety and secrets

- Never paste secrets, tokens, private keys, .env values, or credentials into code or logs.
- If a task requires secrets, ask me to provide them via environment variables.
- Do not add analytics, telemetry, or network calls unless I ask.

## Code quality bar

- Add or update tests for behavior changes when the project has tests.
- Prefer type safety and explicit error handling.
- Add comments only when the intent is non-obvious.

## Build and run etiquette

- If you need to run commands, propose the exact command and why.
- When you make changes that may break build, run the fastest relevant check first.

## Output formatting

- For code changes: include a short summary + list of files changed.
- For debugging: include hypotheses, experiments run, and the minimal fix.

## My preferences

- I like concise explanations, concrete steps, and copy-pastable commands.
- Default language for explanations: Chinese.
"""


def init_claude_code():
    """写入 ~/.claude/CLAUDE.md（claude-code 本体由 brew 统一安装）。

    - 创建 ~/.claude/ 目录（若不存在）
    - 写入 CLAUDE.md（已存在则覆盖）
    """
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text(CLAUDE_MD_CONTENT)
    print(f"已写入 {claude_md}")
