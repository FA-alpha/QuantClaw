# Trade-Bot 技能设计文档

## 📋 概述

"用户操作交易机器人"技能，允许 Agent 通过 API 管理 fourieralpha 平台的交易机器人。

---

## 🔒 安全确认机制（核心设计）

### 设计原则

> **所有涉及交易机器人的写操作（创建/停止/调整/加仓/编辑），代码层强制要求确认。**

### 实现方案：默认预览 + `--confirm` 两步模式

每个写操作默认只预览不执行，加 `--confirm` 才真正调用 API。

| 模式 | 触发方式 | 行为 |
|------|---------|------|
| 预览（默认） | 不加 `--confirm` | 输出 JSON `{"status":"preview",...}`，不调用 API |
| 执行 | 加 `--confirm` | 调用 API 并返回结果 |

> **为什么不是 `--dry-run`**：写操作 "不加 flag = 安全" 更可靠。Agent 必须**显式加 `--confirm`** 才能执行。漏加 = 安全，不加 = 无害。

### 策略编辑采用三步流程（`edit` 子命令）

```
用户："编辑机器人 2039"
  → ① 预览: edit --bot-id 2039
  → 返回可编辑字段列表 + 状态检查

用户："杠杆改3x，止损改限价"
  → ② 差异: edit --bot-id 2039 --rule '{"multiple_num":3,...}'
  → 返回变更明细 diff (changed/unchanged/unknown)

用户："确认"
  → ③ 执行: edit --bot-id 2039 --merged-rule '{...}'
  → 调用对应 API 真正修改
```

### 操作危险等级

| 等级 | 操作 | 确认要求 |
|------|------|---------|
| 🟢 只读 | list, detail, leverage, exchange-list | 无需确认 |
| 🟡 可逆写 | 手动加仓、取消加仓、暂停加仓、取消暂停 | 需确认 |
| 🔴 危险写 | 停止、批量停止、调整保证金、策略编辑 | **强制确认** |

---

## 📁 文件结构

```
skills/trade-bot/
├── DESIGN.md                    ← 设计文档（本文件）
├── SKILL.md                     ← Agent 使用指南
└── scripts/                     ← 所有脚本（自包含，无外部依赖）
    │
    ├── trade_bot.py             ← 🔑 入口（argparse CLI，路由 + token 解析）
    │
    ├── list_bots.py             ← 机器人列表查询（/Trade/lists）
    ├── detail_bot.py            ← 机器人详情（/Trade/info）+ 缓存写入
    ├── leverage_bot.py          ← 杠杆率统计（/TradeStat/leverage_ratio）
    ├── exchange_list.py         ← 交易所账户列表（/User/exchange_lists）
    │
    ├── stop_bot.py              ← 单个机器人操作（/Trade/status_do）
    ├── batch_bot.py             ← 批量机器人操作（/Trade/batch_do）
    ├── scale_bot.py             ← 手动加仓/取消加仓（/Trade/scale_do）
    ├── margin_bot.py            ← 调整保证金（/Trade/margin_do）
    ├── edit_bot.py              ← 策略参数编辑（/Trade/strategy_update_do 或 /Strategy/trade_update_do）
    │
    ├── bot_check.py             ← 🔧 状态预检（/Trade/batch_check_status，供 stop/batch/scale/margin 复用）
    ├── agent_display.py         ← 🔧 Agent 展示约束（统一返回格式，防止 Agent 自由发挥）
    ├── api_client.py            ← 🔧 通用 HTTP 请求封装
    ├── platform_data.py         ← 🔧 平台参考数据（币种/策略/时间，24h 缓存）
    └── qc_log/                  ← 🔧 统一日志模块
        ├── __init__.py
        └── api_logger.py
```

---

## 🎯 子命令与 API 映射

### 🟢 只读操作（无需 `--confirm`）

| 子命令 | 脚本 | API | 说明 |
|--------|------|-----|------|
| `list` | `list_bots.py` | `/Trade/lists` | 按状态/交易所/类型/排序查询 |
| `detail` | `detail_bot.py` | `/Trade/info` | 运行数据、策略参数、权限按钮、**is_edit、add_pause_status** |
| `leverage` | `leverage_bot.py` | `/TradeStat/leverage_ratio` | 杠杆率统计 |
| `exchange-list` | `exchange_list.py` | `/User/exchange_lists` | 用户绑定的交易所账户列表 |

### 🔴 写操作（默认预览，需 `--confirm` 才执行）

| 子命令 | 脚本 | API | save_type | 说明 |
|--------|------|-----|-----------|------|
| `stop` | `stop_bot.py` | `/Trade/status_do` | 4/5/6/7/8/9 | 停止/重启/预约停止/取消预约/暂停加仓/取消暂停 |
| `batch` | `batch_bot.py` | `/Trade/batch_do` | 4/6/7/8/9 | 批量停止/预约停止/取消预约/暂停加仓/取消暂停 |
| `scale` | `scale_bot.py` | `/Trade/scale_do` | 8/9 | 手动加仓/取消加仓 |
| `margin` | `margin_bot.py` | `/Trade/margin_do` | 6/7 | 增加/减少保证金 |
| `edit` | `edit_bot.py` | 见下方 | — | 策略参数编辑（三步流程） |

### `stop` / `batch` 的 save_type 说明

| save_type | 操作 | 状态条件 | 附加条件 |
|-----------|------|---------|---------|
| 4 | 停止 | 运行中(1,2) | — |
| 5 | 停止当周期 | 运行中(1,2) | — |
| 6 | 预约停止 | 运行中(1,2) | 未预约(reserve=0) |
| 7 | 取消预约终止 | 运行中(1,2) | 已预约(reserve=1,2) |
| 8 | 暂停加仓 | 运行中(1,2) | 未暂停(add_pause=0) |
| 9 | 取消暂停加仓 | 运行中(1,2) | 已暂停(add_pause=1) |

### `edit` 的 API 路由（按 strategy_type 区分）

| strategy_type | API | 关键参数 |
|--------------|-----|---------|
| `"2"` | `/Trade/strategy_update_do` | `update_type=1`, `strategy_type`, `rule` |
| 其他 | `/Strategy/trade_update_do` | `save_type=2`, `strategy_id`, `robot_id`, `rule` |

---

## 📤 各脚本返回格式

### `detail_bot.py` — 机器人详情

```json
{
  "status": "ok",
  "detail": {
    "bot_id": "2039",
    "name": "SOL-星辰-做多",
    "strategy_id": "4154",
    "strategy_type": "7",
    "exchange_name": "OKX",
    "status": "1",
    "status_label": "实盘运行中",
    "amt_type": "2",
    "amt_type_label": "合约",
    "unit": "USDT",
    "run_time": 10915576,
    "run_time_label": "126天7小时12分钟",
    "reserve_status": "0",
    "is_edit": 0,
    "add_pause_status": "0",
    "buttons": {
      "margin": true,
      "manual": true,
      "reserve_stop": false,
      "add_pause": true
    },
    "strategy_rule": {
      "coin": "SOL", "leverage": 1, "max_grid_size": 20,
      "grid_type": 1, "direction": "long", "price_high": 140, "price_low": 120,
      "enable_grid_shift": false, "is_add_amt": 1, ...
    },
    "trade_info": { "coin": "SOL/USDT-永续", "float_profit": "0.04%", "win_rate": 66.67, ... },
    "grids": { "long": {...}, "short": {...}, "grids_token": "..." },
    "profit_chart": { "max": 0.02, "min": -7.02, "points": [...] },
    "fund_fee_total": 0.0191
  }
}
```

> 查询详情时自动将原始 `info` 缓存到 `/tmp/quantclaw/bot_details/{bot_id}.json`，供 `edit_bot.py` 复用。

### `edit_bot.py` — 策略编辑

#### 第①步：预览 (`status: "preview"`)

**strategy_type=2 返回 `fields`（扁平列表）**：
```json
{
  "status": "preview",
  "bot_id": "8888",
  "name": "TEST-ST2-BOT",
  "amt_type": "2",
  "editable_check": { "editable": true, "is_edit": 1, "status": "1", "strategy_type": "2" },
  "strategy_type": "2",
  "strategy_type_label": "策略类型2",
  "fields": [
    { "key": "max_grid_size", "label": "最大加仓次数", "type": "number", "value": 10, "hint": "整数" },
    { "key": "max_loss_type", "label": "最大止损类型", "type": "select", "value": "1",
      "options": { "1": "市价", "2": "限价" } },
    { "key": "rsi_signal", "label": "RSI信号", "type": "switch", "value": "0",
      "options": { "0": "关闭", "1": "开启" } },
    { "key": "rsi_time_grain", "label": "RSI时间颗粒度", "type": "select",
      "options": { "1min": "1分钟", "5min": "5分钟", ... },
      "hidden": true, "hidden_reason": "RSI未开启" },
    ...
  ],
  "strategy_rule": { "max_grid_size": 10, ... },
  "raw_rule": { ... }
}
```

**strategy_type≠2 返回 `field_groups`（按分组，来自 `/Strategy/trade_field_info`）**：
```json
{
  "status": "preview",
  "field_groups": [
    {
      "group": "基础设置",
      "fields": [
        { "key": "multiple_num", "label": "杠杆倍数", "type": "number", "value": 3, "editable": true },
        { "key": "direction", "label": "方向", "type": "select", "value": "long",
          "options": { "long": "做多", "short": "做空" }, "editable": true },
        { "key": "coin", "label": "币种", "type": "fixed", "value": "SOL", "editable": false }
      ]
    }
  ],
  ...
}
```

**多维数组（multiples）字段**：
```json
{
  "_kind": "multiples_row",
  "array_key": "tiered_take_profit",
  "row_index": 0,
  "label": "分层止盈[1]",
  "fields": [
    { "key": "layer", "label": "层", "type": "number", "value": 1, "editable": true },
    { "key": "position_ratio", "label": "仓位比例%", "type": "number", "value": 20, "editable": true },
    { "key": "profit_ratio", "label": "盈利比例%", "type": "number", "value": 20, "editable": true }
  ]
}
```

#### 第②步：差异对比 (`status: "diff"`)

```json
{
  "status": "diff",
  "bot_id": "9999",
  "name": "TEST-BOT-SOL",
  "strategy_type": "7",
  "diff": {
    "changed": [
      { "key": "multiple_num", "label": "杠杆倍数", "old": 1, "new": 3 },
      { "key": "max_grid_size", "label": "最大网格数", "old": 20, "new": 10 }
    ],
    "unchanged": [],
    "unknown": []
  },
  "merged_rule": { "multiple_num": 3, "max_grid_size": 10, ... }
}
```

#### 第③步：执行 (`status: "ok"`)

```json
{
  "status": "ok",
  "data": { "status": 1, "info": "...", "url": "" }
}
```

### `stop_bot.py` — 单个机器人操作

**预览**：
```json
{
  "status": "preview",
  "action": "暂停加仓",
  "danger_level": "red",
  "bot": {
    "id": "2039", "status": "1", "status_label": "实盘运行中",
    "reserve_status": "0", "add_pause_status": "0",
    "can_execute": true, "reason": null
  },
  "can_execute": true,
  "summary": { "机器人 ID": "2039", "操作": "暂停加仓", "save_type": "8" },
  "warning": "⚠️ 即将对机器人 2039 执行「暂停加仓」"
}
```

**执行成功**：
```json
{
  "status": "ok",
  "action": "暂停加仓",
  "bot": {
    "id": "2039", "status": "1", "status_label": "实盘运行中",
    "before": { "status": "1", "status_label": "实盘运行中" }
  }
}
```

### `batch_bot.py` — 批量操作

**预览**：
```json
{
  "status": "preview",
  "action": "批量暂停加仓",
  "danger_level": "red",
  "bots": [
    { "id": "2039", "status": "1", "status_label": "实盘运行中",
      "add_pause_status": "0", "can_execute": true, "reason": null },
    { "id": "2523", "status": "1", "status_label": "实盘运行中",
      "add_pause_status": "1", "can_execute": false, "reason": "加仓暂停状态为「已暂停」，不支持此操作" }
  ],
  "executable_count": 1,
  "blocked_count": 1,
  "summary": { "操作类型": "暂停加仓 (save_type=8)", "总数": 2, "可执行": 1, "被阻止": 1 },
  "warning": "⚠️ 即将对 1 个机器人执行「暂停加仓」"
}
```

**执行成功**：
```json
{
  "status": "ok",
  "action": "批量暂停加仓",
  "executed": 1,
  "skipped": 1,
  "bot_ids": ["2039"]
}
```

---

## 🔧 内部模块

### `bot_check.py` — 状态预检

供 `stop_bot` / `batch_bot` / `scale_bot` / `margin_bot` 复用的状态检查模块。

```python
def check_bots(
    token, bot_ids, allowed_statuses,
    allowed_reserve=None,           # 预约状态限制
    allowed_add_pause_status=None,  # 暂停加仓状态限制
    agent_id=None,
) -> dict:
    """
    返回: {
        "bots": [{id, status, status_label, reserve_status, add_pause_status,
                  can_execute, reason}, ...],
        "executable_count": int,
        "blocked_count": int,
    }
    """

def filter_executable(bot_states) -> List[str]:
    """提取可执行 bot_id 列表"""
```

### `api_client.py` — 通用 HTTP 请求封装

- `api_post(path, params, agent_id)` — 统一 POST 请求，内置日志 + 网络异常兜底
- `check_auth(data)` — 检查 API 鉴权状态，返回 `(ok, message)`
- `check_status(data)` — 检查业务状态（status == 1）

### `platform_data.py` — 平台级参考数据（带 24h 磁盘缓存）

- `get_coin_list(token)` → `/Strategy/coin_lists`
- `get_ai_time_list(token)` → `/Extend/ai_time_lists`
- `get_ai_strategy_list(token)` → `/Extend/ai_strategy_lists`
- `get_exchange_list(token, page, limit)` → `/User/exchange_lists`（不缓存）
- 缓存目录：`~/.quantclaw/cache/{key}.json`，TTL 24h

### `qc_log/` — API 请求日志 & 错误日志

- 目录名 `qc_log` 避免遮蔽 Python 标准库 `logging`
- 日志写入 `~/.quantclaw/logs/{agent_id}/{date}.log`
- 自动清理 7 天前的旧日志

---

## 🏗️ 架构约定

- `trade_bot.py` 是唯一入口，用 `argparse` 子命令路由
- 每个功能脚本导出 `def run(...)`，由入口 import 调用
- Token 解析统一在入口 `get_user_token_by_agent_id()` 完成
- 详情缓存（临时数据）写入 `/tmp/quantclaw/bot_details/{bot_id}.json`
- 平台数据缓存（持久化）写入 `~/.quantclaw/cache/{key}.json`
- 所有 import 均为本地引用，skill 完全自包含

---

## 🔗 与其他技能的关系

| 职责 | 归属 Skill |
|------|-----------|
| 策略推荐/创建策略组 | backtest-query |
| 回测 | start-backtest |
| 创建机器人 | backtest-query（调用 `apply_bot.run()`） |
| 管理/监控/控制机器人 | **trade-bot** ✅ |

---

## ✅ 已实现

- [x] 确认机制：默认预览，显式 `--confirm` 执行
- [x] 策略编辑三步流程：预览 → 差异对比 → 确认执行
- [x] `strategy_type=2` 硬编码字段 Schema（switch/select/number/条件隐藏）
- [x] `strategy_type≠2` 动态字段（调 `/Strategy/trade_field_info` 获取）
- [x] 多维数组（multiples）只读现有数据，不支持增删行
- [x] 暂停加仓/取消暂停加仓（save_type=8/9）
- [x] 单个操作 + 批量操作（stop/batch）
- [x] 状态预检模块 `bot_check.py`，检查 status + reserve + add_pause_status
- [x] 详情缓存到 `/tmp/quantclaw/bot_details/`
- [x] `is_edit` / `is_add_pause_btn` / `add_pause_status` 字段
---

## 🔒 Agent 展示约束（防自由发挥）

### 问题

Agent 在遇到报错（超额/状态不符/网络错误）时可能自由发挥：自行调整金额、跳过校验、编造数据。

### 解决方案：`agent_display` 通用模块

所有写操作脚本返回时**必须**附带 `agent_display` 字段，明确告诉 Agent 该展示什么、不该做什么。

### 模块：`agent_display.py`

```python
from agent_display import blocked_result, prompt_result, preview_result, ok_result, error_result
```

**5 种标准返回类型**：

| 函数 | status | blocked | confirm_required | 用途 |
|------|--------|---------|------------------|------|
| `blocked_result(title, reason)` | `"blocked"` | `true` | `false` | 操作被阻止，Agent 不得绕过 |
| `prompt_result(title, prompt_text)` | `"prompt"` | `true` | `false` | 需要用户输入，Agent 不得代为决定 |
| `preview_result(title, detail_lines)` | `"preview"` | `false` | `true` | 展示操作详情，确认后原样重跑 |
| `ok_result(title, detail_lines)` | `"ok"` | `false` | `false` | 操作成功 |
| `error_result(title, message)` | `"error"` | `true` | `false` | 错误，Agent 不得自行处理 |

### 返回格式

所有类型都返回统一结构：
```json
{
  "status": "preview",
  "agent_display": {
    "title": "⚠️ 手动加仓 - 待确认",
    "lines": ["SOL 当前价: 75.56", "加仓价格: 78.00", "加仓金额: 100U"],
    "blocked": false,
    "confirm_required": true,
    "rule": "等待用户确认后，以相同参数重新运行此命令即可执行",
    "user_prompt": "确认执行？回复「确认」后将原样重跑相同命令"
  },
  "action": "手动加仓",
  "summary": {...}
}
```

### `agent_display` 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 展示标题（Agent 可直接用） |
| `lines` | list | 展示内容行（Agent 逐行渲染即可） |
| `blocked` | bool | `true`=Agent 被阻止继续，必须等待用户 |
| `confirm_required` | bool | `true`=待用户确认，确认后以相同参数重新运行即可执行 |
| `rule` | string | 行为约束规则 |
| `user_prompt` | string | 给用户的引导语（Agent 可直接复制发送） |

### 使用示例

```python
# 超额
return blocked_result(
    title="⚠️ 金额超额",
    reason=f"请求 999U 超出可用余额 500U",
    rule="必须等待用户重新输入，不得自行调小金额",
    user_prompt="请输入不超过 500 的金额",
    max_available=500,
    requested=999,
)

# 引导输入
return prompt_result(
    title="📝 请输入加仓参数",
    prompt_text="当前 SOL=75.56, 可用余额=500U\n请输入加仓价格和金额，如「78, 100U」",
    rule="必须等待用户输入价格和金额，不得编造",
    realtime={...},
)

# 预览
return preview_result(
    title="⚠️ 增加保证金 - 待确认",
    detail_lines=["机器人: 2039 SOL-星辰", "金额: 100U", "可用余额: 500U"],
    rule="等待用户确认后，原样重跑相同命令即可执行",
    user_prompt="确认增加 100U 保证金？回复「确认」",
    bot_id="2039",
    amt=100,
)

# 成功
return ok_result(
    title="✅ 保证金已增加",
    detail_lines=["机器人: 2039", "金额: +100U"],
    bot_id="2039",
    amt=100,
)
```

### 脚本编写检查清单

新增或修改写操作脚本时，确认以下项：

- [ ] 所有 `return` 都用了 `agent_display` 的 5 个函数之一
- [ ] `blocked` 状态时 `rule` 明确写了"不得..."的约束
- [ ] `prompt` 状态时 `user_prompt` 包含引导用户输入的示例格式
- [ ] `preview` 状态时 `confirm_required=true` 且 `blocked=false`，`rule` 明确「确认后原样重跑」
- [ ] `preview` 状态时 `detail_lines` 列出了所有关键参数（金额/币种/操作类型）
- [ ] 超额/状态不符等异常场景不是泛泛的 error，而是具体的 `blocked_result` + 明确原因
- [ ] 没有裸 `return {"status":"error", "message":"..."}` 没带 `agent_display`
