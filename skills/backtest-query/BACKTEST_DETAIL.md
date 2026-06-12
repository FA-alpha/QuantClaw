# 回测详情字段说明

AI 回测记录的返回字段详细说明。

---

### 顶层字段

| 字段 | 说明 |
|------|------|
| `status` | 回测状态（1-待回测 2-回测中 3-回测成功 4-回测失败）|
| `bgn_date` | 开始时间 |
| `end_date` | 结束时间 |
| `data_type` | 数据来源 |
| `trade_detail_url` | 交易明细下载表（可能为 null）|
| `statement_url` | 交易收益下载表（可能为 null）|
| `strategy` | 策略信息数组 |
| `total_stat` | 回测统计（总览）|
| `margin_mode_config` | 保证金模式配置 |

---

### strategy（策略信息）

#### 基本信息

| 字段 | 说明 |
|------|------|
| `id` | 策略ID |
| `name` | 策略名称 |
| `desc` | 策略描述 |
| `direction` | 方向（long-做多 / short-做空）|
| `coin` | 币种 |
| `ai_time_id` | AI时间ID |
| `ai_time_name` | AI时间名称 |
| `multiple_num` | 倍数（合约马丁有）|

#### total_stat（统计数据）

| 字段 | 说明 | 显示规则 |
|------|------|---------|
| `total_amt` | 投资金额 | 始终显示 |
| `last_amt` | 净值 | 始终显示 |
| `profit_rate` | 收益率 | 始终显示 |
| `total_profit` | 净利润 | 始终显示 |
| `year_rate` | 年化收益 | 始终显示 |
| `max_loss` | 最大回撤 | 始终显示 |
| `sharp_rate` | 夏普率 | 始终显示 |
| `buy_num` | 买入次数 | 始终显示 |
| `sell_num` | 卖出次数 | 始终显示 |
| `win_rate` | 胜率 | 始终显示 |
| `odds` | 赔率（显示：1/xxx）| **可选字段，没有则不显示** |
| `max_recovery_time` | 最大修复时间 | **可选字段，没有则不显示** |
| `drawdown_over_10pct_count` | 回撤超过10%的次数 | 始终显示 |

#### net_value（净值信息）

| 字段 | 说明 |
|------|------|
| `max` | 净值最大值 |
| `min` | 净值最小值 |
| `lists` | 净值列表（数组）|

**lists 元素结构**：
```json
{"date": "2025-01-15", "net": 1.0523}
```

#### trade_lists（交易记录）

| 字段 | 说明 |
|------|------|
| `date` | 日期 |
| `time` | 时间 |
| `symbol` | 币种 |
| `action` | 操作（buy/sell）|
| `price` | 价格 |
| `quantity` | 数量 |
| `revenue` | 金额 |
| `amount` | 可用余额 |
| `position` | 仓位 |
| `avg_price` | 持仓均价 |
| `grids` | 仓位数量 |
| `profit` | 利润 |
| `reason` | 操作原因 |
| `is_stop_loss` | 是否止损（True-止损 / False-没止损）|
| `fee_amt` | 手续费 |

---

### total_stat（总览统计）

与 strategy.total_stat 结构相同，额外包含：

| 字段 | 说明 |
|------|------|
| `take_profit_rate` | 止盈点卖出比例 |

**trade_lists 额外字段**：

| 字段 | 说明 |
|------|------|
| `liquidation_price` | 预估强评价 |
| `profit_ratio` | 盈利比例 |

---

### margin_mode_config（保证金配置）

| 字段 | 说明 |
|------|------|
| `is_shared_margin` | 是否共享保证金模式 |
| `global_margin_limit` | 共享保证金上限 |
| `strategy_margin_limit` | 策略保证金上限映射 |

**strategy_margin_limit 示例**：
```json
{
  "strategy_id_1 -> 3000": "策略保证金上限",
  "strategy_id_2 -> 8000": "策略保证金上限"
}
```

---

## 展示建议

### 基础信息

```
✅ 回测详情（ID: 12345）

📊 基本信息：
• 状态：回测成功
• 时间范围：2025-01-01 至 2025-12-31
• 数据来源：历史数据
```

### 统计数据

```
📈 回测统计：
• 投资金额：10,000
• 当前净值：14,523
• 收益率：+45.23%
• 年化收益：+45.23%
• 最大回撤：-12.5%
• 夏普率：1.85
• 胜率：68.5%
• 买入/卖出：120/115 次
```

### 注意事项

1. **可选字段**：`odds` 和 `max_recovery_time` 不一定存在，显示前需检查
2. **交易记录**：数量可能很大，建议只展示最近 10-20 笔
3. **下载链接**：如果 `trade_detail_url` 或 `statement_url` 存在，提供下载提示
