# tmux format 字符串

`#{}` 不是全局替换，展开与否取决于它出现在哪个上下文。本文只写实测确认过的规则。

## 确认会展开

| 位置 | 说明 |
|------|------|
| `display-message -p '#D'` | 按调用时的当前 pane 求值 |
| `list-panes -F` / `list-windows -F` | 逐 pane / 逐 window 求值 |
| `if-shell -F` 的 condition | `-F` 即声明 condition 是 format |
| 状态栏 / `window_text` / `pane-border-format` | 逐对象求值 |
| `#{E:@option}` | 见下 |
| 从 shell 直接执行 `tmux run-shell 'echo #{pane_id}'` | 展开后交给 shell |
| hook body 里的 `#{...}` | 会展开，但有前提，见下文 |

## 确认不展开

| 位置 | 说明 |
|------|------|
| `#{@option}` 直接引用 | 原样取出字符串内容 |
| shell 脚本文件里的字面量 | shell 拿到什么就是什么 |

## `#{E:@opt}` 二次求值

`#{@opt}` 只取值；`#{E:@opt}` 会把取到的内容**再当 format 求值一次**。这是「把动态内容塞进格式串」的正规做法。

```
set -g @probe 'inner=#{pane_id}'
display-message -p '#{@probe}'    →  inner=#{pane_id}
display-message -p '#{E:@probe}'  →  inner=%0
```

`status-right` 用 `#{E:@agent_summary}` 就是这个原因：daemon 往 option 里写的是含 `#[fg=...]` 的格式串，必须二次求值才生效。

## `#` 是转义引导符，字面量要双写

user option 的值会被当 format 解析，字面量 `#` 必须写成 `##`：

```python
def esc(text: str) -> str:
    return text.replace("#", "##")
```

`agentd.py` 里所有写进 option 的文本（agent 名、路径、任务名）都过这个函数。漏一处，路径里一个 `#` 就能让状态栏整段渲染错乱。

## 常用写法

### 嵌套 `#{?}` 做优先级

```
#{?cond_a, A, #{?cond_b, B, }}
```

tab 角标用它实现 blocked 优先于 unread。实测两者同时满足时只显示 A。

### `#{&&:...}` 逻辑与

```
#{&&:#{pane_active},#{&&:#{window_active},#{session_attached}}}
```

返回 `1` / `0`，可用于条件。详见 [agent-radar.md](agent-radar.md#焦点判定)。

### `m:` 通配匹配

daemon 把 window 列表写成 `|@1|@7|`，用两侧 `|` 包裹避免 `@1` 误匹配 `@12`：

```
#{?#{m:*|#{window_id}|*,#{@agent_blocked_windows}}, ⚠,}
```

## 坑：`#{...}` 在 hook body 里能展开，但别依赖

```
set-hook -g pane-focus-in "run-shell 'echo #{pane_id} >> log'"
```

`#{pane_id}` 在 hook body 里**是会展开的**，展开值也正确（等于触发时的当前 pane）。真正的坑不在这里，而在下面这条。

### 前提：`focus-events on` 才会每次切换都触发

`pane-focus-in` 依赖 tmux 的焦点事件。`focus-events` 默认 `off` 时，这个 hook **只在 attach 时触发一次**，之后切换 pane 完全不触发。

实测（`tmux -L <name> -f /dev/null` 起的隔离 server，默认即 `focus-events off`）：

| `focus-events` | 切换 3 次 pane 触发次数 |
|----------------|------------------------|
| `off`（默认） | 0 |
| `on` | 3 |

真实配置里 `tmux.conf` 有 `set -g focus-events on`，所以正常环境是好的。但**用 `-f /dev/null` 起的测试 server 不会加载它**，于是切换 pane 时 hook 完全不触发 —— 症状和「format 不展开」一模一样，很容易误判。

排查顺序：先查 `focus-events`，再怀疑 `#{}`。

```bash
tmux -L <name> show -gv focus-events
```

### 展开结果正确，但不要依赖

虽然实测能正确展开，仍不建议在 hook body 里写 `#{}`：

- 只在 `focus-events on` 时才有效，隔离环境验证时极易误判成「展开坏了」。
- body 会依次经过 `hook 定义 → run-shell → shell`，多层引号里 `$`、`"`、`\` 都要按层数转义，出错时同样伪装成「format 不展开」。

需要当前 pane 就在命令内部显式取：

```bash
set-hook -g pane-focus-in "run -b 'pane=$(tmux display-message -p \"#D\"); ...'"
```

`display-message -p` 在所有场景下都稳定。更好的做法是把逻辑写进脚本文件，hook 只负责调用 —— 仓库里 `fzf_agents.tmux update_mru_pane_ids` 就是这种形式：

```bash
set-hook -g pane-focus-in "run -b 'bash ~/.config/tmux/scripts/xxx.sh'"
```

## 相关文件

| 文件 | 用到的写法 |
|------|-----------|
| `tmux/tmux.conf` | `#{E:}` 状态栏、嵌套 `#{?}` tab 角标 |
| `tmux/scripts/agentd.py` | `esc()` 的 `##` 转义 |
| `tmux/scripts/agent_lib.py` | `FOCUS_FIELDS` 的 `#{&&:}`、`list-panes -F` 多字段 TSV |
