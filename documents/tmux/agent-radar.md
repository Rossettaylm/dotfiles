# Agent Radar

tmux 里的 AI agent 状态监控。本文只记录从代码读不出来的设计约束。

## 架构

```
agentd.py (常驻, 2s 一轮)          ← 唯一写 @agent_* option 的地方
   ├── focused_pane_id()  当前 client 盯着的 pane
   ├── mark_seen()        推进已读水位
   └── agent_lib.scan()   tmux list-panes → 解析状态
         ↓ 写缓存 ~/.cache/tmux-agent-radar/<server_tag>/state.tsv
   ↓ 发布 tmux 全局 option
@agent_summary / @agent_toast / @agent_blocked_{windows,panes} / @agent_unread_{windows,panes}
   ↓ 消费方
状态栏 (status-right) · tab 角标 (catppuccin_window_text) · M-n 跳转 · M-a 菜单 · M-e fzf 列表
```

`agent_lib.py` 是 agentd / agent_nav / fzf_agents 共用的唯一数据源，避免三处各自实现状态解析后漂移。

## 状态机

四个状态，由 OSC title / 屏幕内容 / claude session 文件解析：

| 状态 | 含义 | 判定来源 |
|------|------|----------|
| `blocked` | 等用户授权 | claude：session 文件 `waiting`，或 `busy` 时 capture-pane 匹配提示串 |
| `working` | 在干活 | claude：session 文件 `busy`；其他：title 前缀 |
| `unread` | **跑完但没看过** | 派生，见下 |
| `idle` | 闲着呢（含跑完且已看过） | claude：session 文件 `idle`；其他：title 前缀 |
| `unknown` | 解析不出 | 兜底 |

**claude 不能再靠 title**：2.1.2xx 起在 tmux/screen/zellij 下 title 前缀恒为 `✳`（远端 flag `tengu_static_title_under_mux`）。改读 `~/.claude/sessions/<pid>.json` 的 `status`（`busy`/`waiting`/`idle`），按 `tmux` 字段（`<session>:@<win>.%<pane>`）末尾的 pane id 关联；pid 已死的残留文件跳过。文件缺失或无 `status` 时才退回 title 前缀。

排序 `STATE_RANK = (blocked, unread, working, idle, unknown)`，`sort_key`、`pick_target`、fzf 分组三处都依赖这个顺序，改顺序要同步改三处。

### unread 是派生态，不是新状态机

不引入新的状态转换，纯派生：`idle 且 since_ts > seen_ts`。

- `since_ts` = 本轮状态开始时刻，由 agentd 的 `self.prev` 维护（状态变化时置为 now）。所以 idle 的 `since_ts` 就是「跑完的时刻」。
- `seen_ts` = 已读水位，存 tmux pane option `@agent_seen_ts`。

**关键约束：`since_ts` 不在 `PANE_FIELDS` 里。** 它由 daemon 持有，`scan()` 刚返回时恒为 0。因此：

- `apply_unread()` **不能**在 `scan()` 里调用 —— 那时所有 pane 的 `since_ts` 都是 0，`0 > seen_ts` 恒为假，unread 永远派生不出来。
- agentd 的 tick 分两趟：第一趟定 `since_ts`，第二趟才 `apply_unread()`。
- `agent_lib.load()` 走缓存路径（fzf / M-n 用），缓存的 TSV 里带 `since_ts`，所以在那条路径上派生是安全的。

`apply_unread()` 是**双向**派生，不是单向闩锁：`seen_ts >= since_ts` 时会把 `unread` 纠正回 `idle`。因为 daemon 会把自己派生的 unread 写进缓存，没有反向纠正就会永久卡住。

### idle ↔ unread 互转不算状态变化

`agentd._settled()` 把两者视为同一底层状态。若按普通状态变化处理，`since_ts` 会被重置成「用户查看的时刻」，M-a 菜单里的等待时长就废了。

### 时间戳精度必须一致

`to_tsv()` 写 `since_ts` 用 `.3f`，`mark_seen()` 写 pane option 也用 `.3f`。

曾用 `.0f`：`since=...733.697` 存进 TSV 进位成 `...734.0`，于是 `734.0 > 733.697` 成立，把「刚跑完正好被标记已读」的 pane 全部误判成 unread。真实 server 上表现为角标常亮。（TSV 是纯内部格式，改精度不影响 `len(parts) != 8` 校验和 `fzf_agents.tmux` 的 `IFS read`。）

### 冷启动约定

daemon 首次见到的 pane 一律 `mark_seen(pane_id, now)` 标记为已读。因为此时 `since_ts` 只能伪造成 `now`，据此派生 unread 是纯误报。代价：daemon 重启期间跑完的 agent 不亮铃铛 —— 宁可漏报，不要误报。跟「首次见到的 pane 不补报 toast」是同一套约定。

## 焦点判定

`unread` 要排除「正盯着的 pane」（光标停着不动、agent 自己在后台跑完，结果就滚在眼前）。

```
#{&&:#{pane_active},#{&&:#{window_active},#{session_attached}}}
```

三层缺一不可，实测依据：

- `session_attached`：detached session 的当前 pane 依然是 `window_active=1 pane_active=1`，只有 `session_attached=0` 能排除它。缺这层，后台 session 的 agent 会被永久判为已读。
- `window_active`：排除同 session 其他 window 的焦点 pane。
- `pane_active`：排除同 window 的非焦点 pane。

client detach 后 `focused_pane_id()` 立即返回空串，焦点状态不会滞留。

## agent 类型识别

`pane_current_command` 为 `claude` / `omp` 直接认；`cursor-agent` 和 `pi` 都跑在 `node` 下，需要第二信号：

1. pi 空闲时 OSC title 以 `π` 开头（零 fork 快路径）
2. 否则扫 pane 进程子树按命令行匹配，结果 memo 到 `(pane_id, pane_pid)`

快路径必须配子树兜底：pi 工作时图标是 spinner 而非 `π`，只靠 title 会漏掉正在干活的 pi 面板。

### omp（oh-my-pi）的 title

omp 是 Bun 编译的单文件二进制，`pane_current_command` 就是 `omp`。title 格式 `π <标记> <任务>`（源码 `title-generator.ts` / `run-status.ts`）：

| 标记 | omp 内部状态 | 雷达状态 |
|------|------|------|
| `>` | idle / error | `idle` |
| `!` | blocked | `blocked` |
| spinner 帧（braille / pulse / dots / line），无动画终端为 `:` | working | `working` |

它同样以 `π` 开头，**不能**套 pi 的「`π` 开头即 idle」。关掉 title 状态显示后退化成 `π` / `π: <任务>`，判为 `unknown`。这是内部实现而非公开协议，omp 升级后若状态全变 `unknown`，先看 title 格式是否变了。

## 降级行为

daemon 没跑时（`agent_lib.load()` 读不到缓存）走 `scan()` 兜底：状态照常解析，但拿不到 `since_ts`，因此**没有等待时长，也不派生 unread**。跟状态栏「daemon 挂了整段消失」是同一类降级。

`ensure_daemon()` 在每个交互入口（M-n / M-a / M-e）兜一次底，覆盖「已 attach 状态下 daemon 崩溃」——`client-attached` hook 只在 attach 那一刻触发。

## 缓存路径要按 tmux server 分命名空间

缓存和日志都在 `server_tag()` 下：`~/.cache/tmux-agent-radar/<tag>/state.tsv`、`~/templog/agent_radar.<tag>.log`。tag 取 `TMUX` 环境变量里 socket 路径的 basename（`<socket_path>,<pid>,<session>`，tmux CLI 正是按它选 server），无 `TMUX` 时是 `default`。

两个坑决定了这个设计：

**不隔离会串台。** `-L probe` 起的验证 server 上如果误跑 `agentd.py`，它读的是**自己**那个 server 的 pane 列表（空），却把结果写进共享的 state.tsv。真实 server 的 daemon 下一轮再覆盖回来，两边互相踩。实测过一次：zletest server 的 `agentd.py` 残留后台跑了一小时，真实 server 的 `M-e` 列表就开始间歇性为空。

**取 basename 而非全路径。** macOS 上 `/tmp` 是 `/private/tmp` 的软链，`#{socket_path}` 报 `/private/tmp/...` 而 `TMUX` 里可能是 `/tmp/...` —— 同一个 socket 两种写法，按全路径分会裂成两个缓存目录，等于没隔离。

### 空缓存必须回退 scan()

`read_cache()` 把「解析出 0 条」也当 None 返回，`load()` 于是落到 `scan()` 兜底。

`write_cache()` 已经是 tmp + `os.replace` 的原子写，所以**读不到半截文件**。要被挡的是另一件事：0 个 agent 是合法状态，空文件因此与「陈旧」不可区分 —— 缓存刚被写空的那一瞬间，`M-e` 读到的就是「没有 agent」。宁可让真无 agent 时多扫一次实时，也不要让写缓存的那一瞬被当成数据。

这条同时是个错配兜底：`read_cache` 的年龄门槛是 3s，agentd 的 tick 间隔是 2s；daemon 卡顿一次就会让缓存短暂过期。过期走 `scan()` 拿到的 pane 列表照样是对的，只少 `since_ts`。

