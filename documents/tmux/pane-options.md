# tmux pane 级 user option

Agent Radar 用 pane option `@agent_seen_ts` 存「已读水位」。选它而不是全局 option 或状态文件，原因是生命周期自动跟随 pane。以下是实测行为。

## 基本读写

```bash
tmux set -p -t %3 @agent_seen_ts 1757900000.123   # 写入
tmux show -pv -t %3 @agent_seen_ts                # 读取
tmux set -pu -t %3 @agent_seen_ts                 # 清除
```

- `set -p` 可以创建**从未声明过**的新 option，不需要预先 `set -g`。
- `set -pu` 清除一个不存在的 option 也返回 0，不报错。

## 读取不存在时：rc=1 + stderr

```
$ tmux show -pv -t %3 @agent_seen_ts
rc=1
stdout=(空)
stderr=invalid option: @agent_seen_ts
```

`agent_lib.tmux()` 在 `returncode != 0` 时返回空串，所以这种情况下自然得到 `""`，`_parse_ts("")` 返回 `0.0`。**不要**为了读一个可能不存在的 option 去写 `|| echo 0` 之类的兜底 —— 直接把 stderr 丢给 `/dev/null` 交给 `tmux()` 处理即可。

## 作用域不回落

pane 层设置了值之后，全局查询**不会**看到它：

```
tmux set -p -t %1 @agent_seen_ts 123.456
tmux show -pv -t %1 @agent_seen_ts   →  123.456
tmux show -gqv    @agent_seen_ts     →  (空)
```

反过来，全局层有值也不会被 pane 层读到（pane 层无值时 `show -pv` 返回空）。两层完全独立，读哪个必须显式指定。Agent Radar 只用 pane 层，`@agent_unread_*` 那些汇总信息才用全局层。

## 可以在 format 里展开

```
$ tmux list-panes -aF '#{pane_id} seen=[#{@agent_seen_ts}]'
%0 seen=[1757900000]
%1 seen=[]
```

未设置时展开成空串，**不报错**，且制表符分隔的列位不会错乱：

```
$ tmux list-panes -aF '#{pane_id}\t#{@agent_seen_ts}\t#{@agent_other}'
%1\t\t0
```

空字段两侧的 `\t` 都保留。这是 `agent_lib.PANE_FIELDS` 敢把 `#{@agent_seen_ts}` 直接追加成第 8 列、并继续用 `len(parts) != len(PANE_FIELDS)` 做完整性校验的前提。

一次性取全量的写法（`seen_ts_map()`）：

```bash
tmux list-panes -aF '#D\t#{@agent_seen_ts}'
```

比逐 pane `show -pv` 少 N 次 fork。

## pane 销毁自动回收

```
新建 pane 后:  %0:   %1:999
kill %1 后:    %0:
```

pane 消失，它的 option 一并消失，不会泄漏到全局层（`show -gqv @agent_seen_ts` 始终为空）。**不需要写 GC。**

这也是不用全局 option + 手动清理的原因 —— 后者要自己处理「pane 没了但 option 还在」，属于必须维护的额外状态。

## 写入要保证单调不减

`mark_seen()` 只前进不后退：

```python
if _parse_ts(tmux("show", "-pv", "-t", pane_id, "@agent_seen_ts").strip()) >= ts:
    return
tmux("set", "-p", "-t", pane_id, "@agent_seen_ts", f"{ts:.3f}")
```

因为 daemon 每轮都可能调用它，且 `ts` 默认取 `time.time()`，重复调用必须是幂等的。同时避免时钟回拨或并发调用把水位改小。

## 精度必须是 .3f

写入用 `.3f`，`to_tsv()` 序列化 `since_ts` 也必须用 `.3f`。两者精度不一致会导致 unread 误判 —— 详见 [agent-radar.md](agent-radar.md#时间戳精度必须一致)。

`.3f` 毫秒精度足够：浮点往返稳定。

```
float(f"{t:.3f}") -> f"{...:.3f}"  稳定
写入 option 再读回，与原值差 0.0003 以内
```

注意 `.3f` 会对第 4 位小数四舍五入（`1789549733.9999` → `1789549734.0`）。对本用途无影响（判定只关心两次调用的先后），但别拿它当精确存储。
