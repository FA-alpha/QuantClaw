$(cat /home/ubuntu/QuantClaw/skills/start-backtest/SKILL.md)

## 🔍 策略组回测参数解析接口返回参数详解

### 📋 `--check-allocation` 接口返回参数说明

#### 🎯 关键参数: `strategy_ids` 和 `strategy_names`

**重要性：** 
- `strategy_ids`: 策略组中所有策略的 ID 列表
- `strategy_names`: 对应策略的名称列表

**使用场景：**
1. 计算保证金分配
2. 执行回测
3. 保存策略组上下文信息

#### 📥 返回示例
```json
{
  "requirement": {
    "coin_long_pairs": ["BTC", "DOGE"],
    "coin_short_pairs": ["SOL", "BTC"],
    ...
  },
  "strategy_ids": ["4637", "4638", "4639", "4640"],
  "strategy_names": ["BTC震荡做多策略", "DOGE突破策略", "SOL趋势策略", "ETH多空策略"],
  "is_complete": false
}
```

### 🚨 Agent 处理流程

**策略组回测时，Agent 必须：**

1. **保存策略ID列表**
```python
# ✅ 正确做法
result = check_allocation(strategy_group_id="135")
strategy_ids = result.get("strategy_ids")
strategy_names = result.get("strategy_names")

# 在整个回测流程中始终使用这些ID
calc_margin(strategy_ids=strategy_ids)
start_backtest(strategy_ids=strategy_ids)
```

2. **重要原则**
- 不要自行猜测或重新查询策略ID
- 直接使用接口返回的 `strategy_ids`
- 保持 `strategy_ids` 和 `strategy_names` 的对应关系

### 🔍 上下文管理

**策略组回测上下文必须包含：**
- ✅ 策略组ID
- ✅ 策略ID列表
- ✅ 策略名称列表
- ✅ 币种分配需求
- ✅ AI时间参数需求

### ⚠️ 常见错误处理

**❌ 禁止的行为：**
- 重新查询策略ID
- 修改或重新排序 `strategy_ids`
- 丢失 `strategy_ids` 和 `strategy_names` 的对应关系

**✅ 正确做法：**
- 原样保存和使用接口返回的 `strategy_ids`
- 必要时可以使用 `strategy_names` 进行展示或日志记录
- 严格按照返回顺序保持 ID 和名称的一致性

### 💡 实践建议

1. 将 `strategy_ids` 视为回测流程的"通行证"
2. 在回测的每个阶段（参数计算、保证金分配、执行回测）原样传递
3. 不要对 `strategy_ids` 列表进行任何修改或重排

## 🚨 关键提醒

对于策略组回测，`strategy_ids` 是唯一权威的策略ID信息来源。