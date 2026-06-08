---
name: trade-bot
description: "Manage fourieralpha trading bots — list, inspect, stop, scale, margin, edit, and monitor."
---

# Trade-Bot — 交易机器人管理

管理 fourieralpha 平台的交易机器人。所有脚本位于 `skills/trade-bot/scripts/`，入口为 `trade_bot.py`。

---

## 🔒 安全机制（必读）

**所有写操作默认预览，不加 `--confirm` 不会调用 API。**

| 危险等级 | 操作 | 触发方式 |
|---------|------|---------|
| 🟢 只读 | list, detail, leverage, exchange-list, realtime | 无需确认 |
| 🔴 写操作 | stop, batch, scale, margin | 预览后加 `--confirm` |
| 🔴 编辑 | edit | 三步流程：预览→差异→确认 |

**Agent 规则**：任何写操作，必须先预览展示结果，用户确认后再加 `--confirm` 重新运行。不得跳过预览直接执行。

---

## 📁 脚本路径

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py <subcommand> ...
```

---

## 🟢 只读操作

### 1. list — 查询机器人列表

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py list \
  --agent-id "qc-xxx" \
  [--status running|sim|stopped|deleted|all] \
  [--exchange-ids "1,2"] \
  [--amt-type spot|futures|all] \
  [--strategy-type 7] \
  [--account-id 123] \
  [--direction long|short|all] \
  [--search "关键词"] \
  [--coin "SOL"] \
  [--sort latest|profit|runtime|capital|nav|stop-time] \
  [--order desc|asc] \
  [--page 1] \
  [--limit 10]
```

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `--agent-id` | (必填) | 用于自动获取 token |
| `--status` | running | running/sim/stopped/deleted/all |
| `--limit` | 10 | -1=全部 |
| `--sort` | latest | 排序字段 |
| `--order` | desc | 排序方向 |

**返回**的 `symbol_stat` 附带 `symbol_stat_help` 字段映射，Agent 展示实盘汇总时必须参照帮助将英文字段名替换为中文标签。

### 2. detail — 机器人详情

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py detail \
  --agent-id "qc-xxx" \
  --bot-id "2039"
```

**返回关键字段**：
- `detail.bot_id` / `detail.name` — 标识
- `detail.status` / `detail.status_label` — 运行状态
- `detail.strategy_type` — 策略类型（决定 edit 流程）
- `detail.is_edit` — 是否可编辑（1=可 0=不可）
- `detail.add_pause_status` — 加仓暂停状态（0=正常 1=已暂停）
- `detail.buttons` — 可用操作按钮
- `detail.strategy_rule` — 策略参数
- `detail.trade_info` — 盈亏/胜率等
- `detail.grids` — 网格数据

**缓存**：查询详情会自动缓存到 `/tmp/quantclaw/bot_details/{bot_id}.json`，供 edit/realtime 复用。

### 3. leverage — 杠杆率统计

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py leverage \
  --agent-id "qc-xxx" \
  [--status running] \
  [--exchange-ids "1,2"] \
  [--coin "BTC"]
```

筛选参数与 `list` 一致，但只统计运行中的机器人。

**返回**包含 `section_help`（分组标签）和 `field_help`（字段标签），Agent 展示时必须参照帮助信息将英文字段名替换为中文标签，按分组逐字段解释，不得跳过任何有值的字段。

### 4. exchange-list — 交易所账户列表

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py exchange-list \
  --agent-id "qc-xxx" \
  [--page 1] [--limit -1]
```

返回用户绑定的交易所账户（exchange_id、名称、类型等）。

### 5. realtime — 实时数据

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py realtime \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  [--show-type "1,2"]
```

| show_type | 含义 |
|-----------|------|
| 1 | 最新币价 |
| 2 | 可用余额 |
| 3 | 可减少保证金 |

**用途**：加仓/调保证金前查询实时行情和可用余额。

---

## 🔴 写操作（预览→确认→执行）

### ⚠️ Agent 展示约束

所有写操作的返回都包含 `agent_display` 字段，Agent 必须遵守：

| status | blocked | confirm_required | Agent 行为 |
|--------|---------|-----------------|-----------|
| `blocked` | true | false | **必须停止**，展示原因，等用户处理。不得绕过 |
| `prompt` | true | false | **必须等待用户输入**，不得编造数据 |
| `preview` | false | true | 展示预览，等用户确认后原样重跑 |
| `ok` | false | false | 展示成功结果 |
| `error` | true | false | 展示错误，不得自行处理 |

**关键规则**：
- `blocked`=true 时 → 展示 `agent_display.title` + `agent_display.lines`，显示 `agent_display.user_prompt`，**不做任何操作**
- `preview` 时 → 展示 `agent_display.title` + `agent_display.lines`，**不加 `--confirm`**。用户确认后，**原样重跑相同命令加 `--confirm`**
- `prompt` 时 → 展示引导语，等用户给数据
- **禁止裸返回**：返回中没有 `agent_display` 时应视为异常

### 6. stop — 单个机器人操作

```bash
# 预览（默认）
cd skills/trade-bot/scripts && python3 trade_bot.py stop \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --save-type "4"

# 用户确认后执行
cd skills/trade-bot/scripts && python3 trade_bot.py stop \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --save-type "4" \
  --confirm
```

| save_type | 操作 | 前置条件 |
|-----------|------|---------|
| 4 | 停止 | status=1/2（运行中） |
| 5 | 停止当周期 | status=1/2 |
| 6 | 预约停止 | status=1/2 且 reserve=0 |
| 7 | 取消预约终止 | status=1/2 且 reserve=1/2 |
| 8 | 暂停加仓 | status=1/2 且 add_pause=0 |
| 9 | 取消暂停加仓 | status=1/2 且 add_pause=1 |

**工作流**：
1. 先查 `detail` 确认状态
2. 运行 stop 预览 → 展示 `agent_display`
3. 确认 `can_execute` 为 true
4. 用户确认 → 加 `--confirm` 重新运行

### 7. batch — 批量操作

```bash
# 预览
cd skills/trade-bot/scripts && python3 trade_bot.py batch \
  --agent-id "qc-xxx" \
  --bot-ids "2039,2523,3012" \
  --save-type "8"

# 用户确认后执行
cd skills/trade-bot/scripts && python3 trade_bot.py batch \
  --agent-id "qc-xxx" \
  --bot-ids "2039,2523,3012" \
  --save-type "8" \
  --confirm
```

| save_type | 操作 |
|-----------|------|
| 4 | 批量停止 |
| 6 | 批量预约停止 |
| 7 | 批量取消预约终止 |
| 8 | 批量暂停加仓 |
| 9 | 批量取消暂停加仓 |

**返回**：`executable_count` / `blocked_count`，每个 bot 的 `can_execute` + `reason`。Agent 必须展示哪些会被执行、哪些被阻止及原因。

### 8. scale — 手动加仓/取消加仓

```bash
# 加仓预览（需 price + amt）
cd skills/trade-bot/scripts && python3 trade_bot.py scale \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --save-type "8" \
  --price 78.00 \
  --amt 100

# 取消加仓预览（需 order_id）
cd skills/trade-bot/scripts && python3 trade_bot.py scale \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --save-type "9" \
  --order-id "abc123"

# 确认执行加 --confirm
```

| save_type | 操作 | 必要参数 |
|-----------|------|---------|
| 8 | 手动加仓 | `--price` + `--amt` |
| 9 | 取消加仓 | `--order-id` |

**⚠️ 加仓前必须**：
1. 先跑 `realtime --show-type "1,2"` 获取当前币价和可用余额
2. 展示实时数据给用户
3. 由用户指定 price 和 amt，**不得由 Agent 自行决定**

### 9. margin — 调整保证金

```bash
# 预览（不传 amt 则自动查询最大可用额度）
cd skills/trade-bot/scripts && python3 trade_bot.py margin \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --save-type "6" \
  [--amt 100]

# 确认执行加 --confirm
```

| save_type | 操作 | 说明 |
|-----------|------|------|
| 6 | 增加保证金 | 不传 `--amt` 自动查最大可用余额 |
| 7 | 减少保证金 | 不传 `--amt` 自动查最大可减少额度 |

**工作流**：
1. 先跑 `margin`（不传 `--amt`）→ 查看最大可用额度
2. 展示可用额度给用户
3. 用户指定金额 → 带 `--amt` 预览
4. 用户确认 → 加 `--confirm` 执行

---

## 🟡 edit — 策略参数编辑（三步流程）

**三步流程：预览 → 差异对比 → 确认执行**

### 第①步：预览可编辑参数

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py edit \
  --agent-id "qc-xxx" \
  --bot-id "2039"
```

**返回**：
- `strategy_type=2` → `fields`（扁平字段列表，含 type/options/hidden）
- `strategy_type≠2` → `field_groups`（按分组，含 `editable` 标志）
- 多维数组字段 → `_kind: "multiples_row"`，只读不可编辑
- `editable_check.editable` → false 表示不可编辑

### 第②步：差异对比

用户告诉你要改什么后：

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py edit \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --rule '{"multiple_num":3,"max_grid_size":10}'
```

**返回**：
- `diff.changed` — 变更明细（old → new）
- `diff.unchanged` — 未变字段
- `diff.unknown` — 未识别的 key
- `merged_rule` — 合并后的完整参数（第③步直接用）

**Agent 规则**：
- 展示 `diff.changed` 给用户确认
- 如有 `diff.unknown`，提醒用户这些 key 不存在
- **禁止自行修改** `merged_rule` 中的值

### 第③步：确认执行

用户确认后：

```bash
cd skills/trade-bot/scripts && python3 trade_bot.py edit \
  --agent-id "qc-xxx" \
  --bot-id "2039" \
  --merged-rule '{"multiple_num":3,"max_grid_size":10,...}' \
  [--update-type 1|2]
```

| update_type | 含义 |
|-------------|------|
| 1（默认） | 永久更新 |
| 2 | 仅当前周期 |

**⚠️** `--merged-rule` 必须用第②步返回的完整值，不要自己拼。

---

## 🔄 常见工作流

### 批量暂停机器人加仓

```
1. list → 找到运行中的机器人 ID
2. batch --bot-ids "..." --save-type "8" → 预览
3. 展示 agent_display，列出可执行/被阻止的
4. 用户确认 → batch --confirm --bot-ids "..." --save-type "8"
```

### 手动加仓

```
1. detail --bot-id "2039" → 确认状态（运行中、add_pause=0）
2. realtime --bot-id "2039" --show-type "1,2" → 获取币价+余额
3. 展示币价/余额给用户，等用户指定价格和金额
4. scale --bot-id "2039" --save-type "8" --price 78 --amt 100 → 预览
5. 展示 agent_display，用户确认
6. scale --confirm --bot-id "2039" --save-type "8" --price 78 --amt 100
```

### 编辑策略参数

```
1. detail --bot-id "2039" → 确认 is_edit=1
2. edit --bot-id "2039" → 第①步预览所有可编辑字段
3. 展示字段列表给用户，用户指定要改的
4. edit --bot-id "2039" --rule '{"key":"value"}' → 第②步差异
5. 展示 diff.changed，用户确认
6. edit --bot-id "2039" --merged-rule '...' → 第③步执行
```

### 为机器人增加保证金

```
1. detail --bot-id "2039" → 确认状态
2. margin --bot-id "2039" --save-type "6" → 自动查最大可用余额
3. 展示可用额度给用户
4. 用户指定金额 → margin --bot-id "2039" --save-type "6" --amt 200 → 预览
5. 展示 agent_display，用户确认
6. margin --confirm --bot-id "2039" --save-type "6" --amt 200
```

---

## ⚠️ 易错点

| 错误 | 正确做法 |
|------|---------|
| 写操作不加预览直接执行 | **必须先预览**，展示 `agent_display`，用户确认后加 `--confirm` |
| Agent 自行决定加仓价格/金额 | 必须先查 `realtime`，展示数据，**等用户指定** |
| `blocked` 后 Agent 自行调整参数重试 | **必须停止**，展示 `user_prompt`，等用户处理 |
| `preview` 返回后直接加 `--confirm` | **必须先展示给用户**，用户说"确认"后再加 `--confirm` |
| edit 第③步自己拼 `merged_rule` | **必须用第②步返回的** `merged_rule` |
| batch 不展示哪些被阻止 | 必须展示 `executable_count` + `blocked_count` + 每个被阻止的 `reason` |

---

## 📦 数据缓存

| 缓存 | 路径 | TTL |
|------|------|-----|
| 机器人详情 | `/tmp/quantclaw/bot_details/{bot_id}.json` | 无过期（每次 detail 刷新） |
| 平台数据（币种/策略/时间） | `~/.quantclaw/cache/{key}.json` | 24h |
| API 日志 | `~/.quantclaw/logs/{agent_id}/{date}.log` | 7天自动清理 |
| 确认 nonce | `/tmp/quantclaw/nonces/` | 5分钟 |
