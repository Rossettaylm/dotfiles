# 在隔离 tmux server 上做验证

改 tmux 脚本/配置时不要拿正在用的 server 试 —— 会污染 `@mru_pane_ids`、pane option、hook。`-L <name>` 起独立 server，互不干扰。

## 基本骨架

```bash
S="tmux -L probe"
$S kill-server 2>/dev/null
$S -f /dev/null new-session -d -s t -x 100 -y 24
$S split-window -d
```

`-f /dev/null` 跳过配置文件加载，避免 source 真实 `tmux.conf`。

**注意 `-t` 的目标写法**：`-f /dev/null` 下 `base-index` 是默认的 0，`t:0` 有效；
不带 `-f` 时会加载真实配置，`base-index 1` + `pane-base-index 1`，此时 `t:0` 报 `can't find window: 0`，要用 `t:1`。

`respawn-pane` **没有 `-f` 这个 flag**（加了会报 `unknown flag -f`），别照搬 `new-session -f /dev/null` 的写法。

收尾统一 `$S kill-server`。

## 让 python 脚本连到隔离 server

`agent_lib.tmux()` 走子进程调 tmux，用 `TMUX` 环境变量重定向即可，不用改代码：

```python
os.environ["TMUX"] = "/tmp/tmux-%d/probe,0,0" % os.getuid()
sys.path.insert(0, "/Users/lyman/.config/tmux/scripts")
import agent_lib as lib
lib.scan(); lib.focused_pane_id()
```

socket 路径是 `/tmp/tmux-<uid>/<name>`（macOS 上 `/tmp` 是 `/private/tmp` 的软链，两个路径都能连）。

## 影子 agent pane

`agent_lib` 靠 `pane_current_command` + OSC title 认 agent，所以影子 pane 要造得让它认。

### 造假 claude：不可行

把任意二进制复制/改名成 `claude` 没用 —— tmux 读的是进程真实的 command 名（`ps` 的 comm），不是文件名。复制 `/bin/sleep` 过去，`pane_current_command` 依然报 `sleep`。

要测 claude 分支就用真实的 claude pane，或直接对 `parse_claude_title()` 单独喂 title 字符串做单元测试。

### 造假 pi：可行

`pi` 分支要求 `pane_current_command == node`，然后扫进程子树匹配 `pi-coding-agent`。所以只要用 node 起一个文件名含该串的脚本：

```bash
printf 'setTimeout(function(){},600000);\n' > /tmp/fb/pi-coding-agent.js
$S respawn-pane -k -t t:agents.0 "node /tmp/fb/pi-coding-agent.js"
```

实测 `scan()` 输出 `('pi', 'working')`。

### 驱动状态

`scan()` 每次重新解析 title，所以直接改 title 就能切状态：

```bash
$S select-pane -t %0 -T "π done"      # π 开头 -> idle
$S select-pane -t %0 -T "working..."  # 其他   -> working
```

比让影子进程真的吐 OSC 序列简单得多。

## 焦点判定要真的 attach

`focused_pane_id()` 依赖 `session_attached`，纯 `new-session -d`（detached）永远返回空串 —— **测焦点必须挂一个真 client**。用 `pty.fork()` 起一个 attach 的进程：

```python
import os, pty, time, subprocess
pid, fd = pty.fork()
if pid == 0:
    os.execvp("tmux", S + ["attach", "-t", "t"])
time.sleep(1.5)                     # 等 attach 完成，用 2s 更稳
# ... 做验证 ...
os.write(fd, b"\x02d")              # prefix + d 退出
```

窗口尺寸要显式给（`-x 100 -y 24`），否则 pty 尺寸为 0 时布局行为与真实环境不一致。

测「视线在别处」就多开一个 window 再 `select-window` 切过去。

### 按键驱动要注意 prefix

`-f /dev/null` 起的 server 用默认 prefix `C-b`，`\x02o`（切换 pane）有效。
**不带 `-f /dev/null` 时会加载真实 `tmux.conf`，prefix 已被改成 `C-\`**（`0x1c`），此时发 `\x02o` 不会触发任何绑定，测试静默失效。

两种驱动方式都能触发 `pane-focus-in`，也都能让 `display-message -p '#D'` 返回正确值：

```bash
$S select-pane -t %1     # 命令式，可控、可重复
os.write(fd, b"\x1co")   # 按键式（C-\ + o），贴近真实操作
```

## 坑：`-f /dev/null` 下没有 `focus-events`，hook 不触发

这是本仓库验证时最大的一个坑。

`pane-focus-in` 依赖焦点事件，而 `focus-events` 默认 `off`。真实 `tmux.conf` 里有 `set -g focus-events on`，但 **`-f /dev/null` 起的隔离 server 不加载它**，于是切换 pane 时 hook 完全不触发 —— 看起来像被测代码有 bug，实际是测试环境缺了一行配置。

```
focus-events=off（-f /dev/null 的默认）: 切换 3 次 pane，hook 触发 0 次
focus-events=on                        : 切换 3 次 pane，hook 触发 3 次
```

所以隔离 server 上要测任何跟 `pane-focus-in` 有关的逻辑，必须补上：

```bash
$S set -g focus-events on
```

排查 hook 不触发时，第一件事就是查这个值：

```bash
tmux -L <name> show -gv focus-events
```

### 其它写测试脚本的注意点

- 落盘断言**不要在中间删文件**——会和 hook 的异步写盘竞争，记录时有时无（这个也误导过判断，误以为 hook 时好时坏）。
- 用 `echo`/`touch` 这类无歧义副作用判断 hook 是否触发。
- 要断言的逻辑（`focused_pane_id()`、`apply_unread()`）**绕开 hook 直接调函数** —— 那部分是确定性的，也是真正需要覆盖的。
- 「hook 没触发」先怀疑测试装置（`focus-events`、prefix、引号转义），再怀疑被测代码。


## 清理

```bash
for s in probe probe2 ...; do tmux -L $s kill-server 2>/dev/null; done
```

真实 server 上留下的是：`@agent_seen_ts` 之类的 pane option（pane 关掉就没了）、daemon 发布的 `@agent_*` 全局 option。中途用 `python3 agentd.py --once` 试过的话，它会写一遍缓存和 option，正式收尾时记得重启常驻 daemon。

**不要拿真实 server 验证「用户的 MRU 顺序」这类有状态的东西** —— `@mru_pane_ids` 会被测试写坏，之后 M-e 的排序就不对了。

## 隔离 server 上误跑 agentd 会串台（已修，但别依赖）

缓存/日志现在按 `server_tag()` 分目录（见 [[agent-radar]]），所以 `-L probe` 上的 daemon 只写自己的 `<tag>/state.tsv`。但**别在隔离 server 上留常驻 daemon**：`ensure_daemon()` 看的是 `@agent_radar_pid`，隔离 server 上那个是空的，任何 `agent_nav.py` / `agent_lib.py dump` 调用都会 spawn 一个 —— 它不会随 `kill-server` 退出（`server_alive()` 只在循环里检查，`--once` 之后就不管了）。

清理时把 daemon 一起收掉：

```bash
pgrep -f agentd.py | xargs -r ps -o pid,command -p   # 先看清哪个挂在哪个 server
kill <pid>
```

daemon 的 log 文件里 `agent_radar.<tag>.log` 的 tag 直接告诉你是哪个 server 起的。
