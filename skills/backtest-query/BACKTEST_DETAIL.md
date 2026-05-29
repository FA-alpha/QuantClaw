# 回测详情字段说明

查看回测记录的详细统计信息、交易记录、净值曲线等。

---

## 📊 回测详情字段说明

### API 信息

- **URI**: `/Backtrack/stat_info`
- **参数**: `usertoken`, `back_id`

### 响应结构

#### 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | int | 回测状态（1-待回测 2-回测中 3-回测成功 4-回测失败）|
| `bgn_date` | string | 开始时间 |
| `end_date` | string | 结束时间 |
| `data_type` | string | 数据来源 |
| `trade_detail_url` | string/null | 交易明细下载表 |
| `statement_url` | string/null | 交易收益下载表 |
| `strategy` | array | 策略信息列表 |
| `total_stat` | object | 回测统计（总览）|
| `margin_mode_config` | object | 保证金模式配置 |

---

### strategy（策略信息）

#### 策略基本信息

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 策略ID |
| `name` | string | 策略名称 |
| `desc` | string | 策略描述 |
| `direction` | string | 方向（long-做多 / short-做空）|
| `coin` | string | 币种 |
| `ai_time_id` | string | AI时间ID |
| `ai_time_name` | string | AI时间名称 |
| `multiple_num` | int | 倍数（合约马丁有）|

#### strategy.total_stat（单策略统计）

| 字段 | 类型 | 说明 | 展示规则 |
|------|------|------|---------|
| `total_amt` | float | 投资金额 | 始终展示 |
| `last_amt` | float | 净值 | 始终展示 |
| `profit_rate` | float | 收益率 | 始终展示 |
| `total_profit` | float | 净利润 | 始终展示 |
| `year_rate` | float | 年化收益 | 始终展示 |
| `max_loss` | float | 最大回撤 | 始终展示 |
| `sharp_rate` | float | 夏普率 | 始终展示 |
| `buy_num` | int | 买入次数 | 始终展示 |
| `sell_num` | int | 卖出次数 | 始终展示 |
| `win_rate` | float | 胜率 | 始终展示 |
| `odds` | float | 赔率（显示：1/xxx）| **若无此字段则不显示** |
| `max_recovery_time` | string | 最大修复时间 | **若无此字段则不显示** |
| `drawdown_over_10pct_count` | int | 回撤超过10%的次数 | 始终展示 |

#### strategy.total_stat.net_value（净值信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `max` | float | 净值最大值 |
| `min` | float | 净值最小值 |
| `lists` | array | 净值列表 |

**lists 元素结构**：
```json
{
  "date": "2025-01-15",
  "net": 1.0523
}
```

#### strategy.trade_lists（交易信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 日期 |
| `time` | string | 时间 |
| `symbol` | string | 币种 |
| `action` | string | 操作（buy/sell）|
| `price` | float | 价格 |
| `quantity` | float | 数量 |
| `revenue` | float | 金额 |
| `amount` | float | 可用余额 |
| `position` | float | 仓位 |
| `avg_price` | float | 持仓均价 |
| `grids` | int | 仓位数量 |
| `profit` | float | 利润 |
| `reason` | string | 操作原因 |
| `is_stop_loss` | bool | 是否止损（True-止损 / False-没止损）|
| `fee_amt` | float | 手续费 |

---

### total_stat（回测统计总览）

**结构与 strategy.total_stat 基本相同**，但额外包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `take_profit_rate` | float | 止盈点卖出比例 |

#### total_stat.trade_lists（总览交易信息）

**包含 strategy.trade_lists 的所有字段，额外增加**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `liquidation_price` | float | 预估强评价 |
| `profit_ratio` | float | 盈利比例 |

---

### margin_mode_config（保证金模式配置）

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_shared_margin` | bool | 是否是共享保证金模式 |
| `global_margin_limit` | float | 共享保证金上限 |
| `strategy_margin_limit` | object | 策略保证金上限映射 |

**strategy_margin_limit 结构示例**：
```json
{
  "strategy_id_1 -> 3000": "策略保证金上限",
  "strategy_id_2 -> 8000": "策略保证金上限"
}
```

---

## 🎨 回测详情展示模板

### 基础信息展示

```
✅ 回测详情（ID: {back_id}）

📊 基本信息：
• 状态：{status_text}  (1-待回测 2-回测中 3-回测成功 4-回测失败)
• 时间范围：{bgn_date} 至 {end_date}
• 数据来源：{data_type}
```

### 策略信息展示

```
📋 策略信息：
• 策略名称：{name}
• 币种：{coin}
• 方向：{direction_text}  (long-做多 / short-做空)
• AI时间：{ai_time_name}
```

### 统计数据展示

```
📈 回测统计：
• 投资金额：{total_amt}
• 当前净值：{last_amt}
• 收益率：{profit_rate}%
• 净利润：{total_profit}
• 年化收益：{year_rate}%
• 最大回撤：{max_loss}%
• 夏普率：{sharp_rate}
• 胜率：{win_rate}%
• 买入次数：{buy_num}
• 卖出次数：{sell_num}
• 回撤超10%次数：{drawdown_over_10pct_count}
```

**可选字段（存在才展示）**：
```
• 赔率：1/{odds}
• 最大修复时间：{max_recovery_time}
```

### 净值信息展示

```
📊 净值曲线：
• 最大净值：{net_value.max}
• 最小净值：{net_value.min}
• 数据点数：{len(net_value.lists)}
```

### 交易记录展示（精简版）

```
💰 交易记录（最近10笔）：
1. {date} {time} | {action_text} {quantity} {symbol} @ {price} | 利润: {profit} | {reason}
2. ...
```

**action_text**：
- `buy` → 买入
- `sell` → 卖出

### 保证金配置展示

```
💵 保证金配置：
• 共享保证金模式：{is_shared_margin_text}  (是/否)
• 全局上限：{global_margin_limit}
• 策略上限：
  - 策略1: {strategy_margin_limit_1}
  - 策略2: {strategy_margin_limit_2}
```

---

## ⚠️ 展示注意事项

1. **状态判断**：
   - status=3（回测成功）→ 展示完整统计数据
   - status=1/2（待回测/回测中）→ 只展示基本信息
   - status=4（回测失败）→ 提示失败原因

2. **可选字段**：
   - `odds` 和 `max_recovery_time` 不一定存在，展示前需检查

3. **交易记录**：
   - 数量可能很大，建议只展示最近10-20笔
   - 提供"查看完整交易记录"的选项（如果有 trade_detail_url）

4. **下载链接**：
   - 如果 `trade_detail_url` 或 `statement_url` 存在，提供下载提示

5. **数值格式化**：
   - 收益率/年化收益：显示百分号
   - 金额：保留2位小数
   - 夏普率：保留2位小数
   - 胜率：显示百分号

---

## 📝 回测详情完整示例

### 输入

```bash
cd skills/backtest-query && python3 query.py \
  --detail "12345" \
  --agent-id "qc-xxx"
```

### 输出 JSON（结构示例）

```json
{
  "status": 1,
  "info": {
    "status": 3,
    "bgn_date": "2025-01-01",
    "end_date": "2025-12-31",
    "data_type": "历史数据",
    "trade_detail_url": "https://example.com/trade_detail.xlsx",
    "statement_url": "https://example.com/statement.xlsx",
    "strategy": [
      {
        "id": "strategy_1",
        "name": "风霆V4.3-BTC-做多",
        "desc": "BTC做多策略",
        "direction": "long",
        "coin": "BTC",
        "ai_time_id": "5",
        "ai_time_name": "2025全年",
        "multiple_num": 5,
        "total_stat": {
          "total_amt": 10000,
          "last_amt": 14523,
          "profit_rate": 45.23,
          "total_profit": 4523,
          "year_rate": 45.23,
          "max_loss": -12.5,
          "sharp_rate": 1.85,
          "buy_num": 120,
          "sell_num": 115,
          "win_rate": 68.5,
          "odds": 2.3,
          "max_recovery_time": "15天",
          "drawdown_over_10pct_count": 2,
          "net_value": {
            "max": 1.6523,
            "min": 0.8750,
            "lists": [
              {"date": "2025-01-01", "net": 1.0000},
              {"date": "2025-01-02", "net": 1.0123}
            ]
          }
        },
        "trade_lists": [
          {
            "date": "2025-01-15",
            "time": "10:30:00",
            "symbol": "BTC",
            "action": "buy",
            "price": 42000,
            "quantity": 0.1,
            "revenue": 4200,
            "amount": 5800,
            "position": 0.1,
            "avg_price": 42000,
            "grids": 1,
            "profit": 0,
            "reason": "突破入场",
            "is_stop_loss": false,
            "fee_amt": 4.2
          }
        ]
      }
    ],
    "total_stat": {
      "total_amt": 10000,
      "last_amt": 14523,
      "profit_rate": 45.23,
      "total_profit": 4523,
      "year_rate": 45.23,
      "max_loss": -12.5,
      "sharp_rate": 1.85,
      "buy_num": 120,
      "sell_num": 115,
      "win_rate": 68.5,
      "odds": 2.3,
      "max_recovery_time": "15天",
      "take_profit_rate": 75.5,
      "net_value": {
        "max": 1.6523,
        "min": 0.8750,
        "lists": [...]
      },
      "trade_lists": [...]
    },
    "margin_mode_config": {
      "is_shared_margin": true,
      "global_margin_limit": 50000,
      "strategy_margin_limit": {
        "strategy_1 -> 3000": "策略保证金上限",
        "strategy_2 -> 8000": "策略保证金上限"
      }
    }
  }
}
```

### 回复格式化示例

```
✅ 回测详情（ID: 12345）

📊 基本信息：
• 状态：回测成功
• 时间范围：2025-01-01 至 2025-12-31
• 数据来源：历史数据

📋 策略信息：
• 策略名称：风霆V4.3-BTC-做多
• 币种：BTC
• 方向：做多
• AI时间：2025全年
• 杠杆倍数：5x

📈 回测统计：
• 投资金额：10,000
• 当前净值：14,523
• 收益率：+45.23%
• 净利润：+4,523
• 年化收益：+45.23%
• 最大回撤：-12.5%
• 夏普率：1.85
• 胜率：68.5%
• 买入次数：120
• 卖出次数：115
• 回撤超10%次数：2
• 赔率：1/2.3
• 最大修复时间：15天

📊 净值曲线：
• 最大净值：1.6523
• 最小净值：0.8750
• 数据点数：365

💰 交易记录（最近1笔）：
1. 2025-01-15 10:30:00 | 买入 0.1 BTC @ 42,000 | 利润: 0 | 突破入场

💵 保证金配置：
• 共享保证金模式：是
• 全局上限：50,000
• 策略上限：
  - strategy_1: 3,000
  - strategy_2: 8,000

📥 下载链接：
• 交易明细：https://example.com/trade_detail.xlsx
• 交易收益：https://example.com/statement.xlsx

需要更详细的净值曲线或完整交易记录吗？
```
