# 高级规则与边界情况

本文档包含 backtest-query 技能的高级使用规则和边界情况处理。

---

## 📊 coin-pct-map 参数（策略建仓比例）

### 概念区分

| 概念 | 含义 | 参数 | 所属技能 |
|------|------|------|---------|
| **资金配比** | 总资金如何分配到不同策略 | 回测参数 | start-backtest |
| **建仓比例** | 单个策略的持仓百分比 | `--coin-pct-map` | backtest-query |

### 使用规则

**用户说"资金配比各50%"**：
- ❌ 不传 `--coin-pct-map`
- ✅ 这是回测参数，留给 start-backtest 技能

**用户说"建仓比例80%"**：
- ✅ 传 `--coin-pct-map '{"BTC": ["80"]}'`
- 📌 BTC 可选：10/20/.../120
- 📌 其他币种可选：60/80/.../140

### 示例

```bash
# 用户："推荐 BTC 策略，建仓比例 80%"
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "qc-xxx" \
  --query "推荐 BTC 策略，建仓比例 80%" \
  --coins "BTC" \
  --strategy-types "11" \
  --coin-pct-map '{"BTC": ["80"]}' \
  --intent-json '{...}' \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result_qc-xxx.json
```

---

## 🕐 时间参数判断细则

### 判断流程图

```
用户提到时间
  ↓
是否有"回测"关键词？
  ├─ 是 → 回测时间范围 → 不查询 --list-ai-times → 不传参数
  └─ 否 → 继续判断
        ↓
        是"震荡"/"牛市"/"熊市"等市场状态？
          ├─ 是 → AI时间ID → 查询 --list-ai-times → 传 --ai-time-ids
          └─ 否 → "最近1年"/"2025年数据"等
                  ↓
                  查询 --list-ai-times → 匹配描述 → 传 --ai-time-ids
```

### 详细示例

| 用户说法 | 有"回测"? | 判断为 | 操作 |
|---------|---------|-------|------|
| "震荡行情的策略" | ❌ | AI时间ID | 查询列表 → 传ID |
| "2025年牛市策略" | ❌ | AI时间ID | 查询列表 → 传ID |
| "最近1年数据的策略" | ❌ | AI时间ID | 查询列表 → 传ID |
| "推荐策略，回测2025年" | ✅ | 回测时间范围 | 不查询，不传参数 |
| "挑选策略，分别回测全年" | ✅ | 回测时间范围 | 不查询，不传参数 |
| "最近30天回测" | ✅ | 回测时间范围 | 不查询，不传参数 |

---

## 🎯 多策略类型混合

### 场景

用户要求同时使用多种策略类型（如风霆 + 鲲鹏）

**用户**："推荐 BTC 的风霆和鲲鹏组合"

### 处理

```bash
# 1. 查询策略类型列表
cd skills/backtest-query && python3 query.py --list-strategies --agent-id "qc-xxx"

# 2. 匹配名称
# 风霆 → 11
# 鲲鹏 → 3

# 3. 生成 intent JSON
intent_json='{"strategy_goal":"diversification","constraints":{"coins":["BTC"],"strategy_types":["11","3"],"directions":null,"min_strategies":2},"preferences":{"risk_level":"balanced","diversity_priority":"strategy_type"}}'

# 4. 执行推荐
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "qc-xxx" \
  --query "推荐 BTC 的风霆和鲲鹏组合" \
  --coins "BTC" \
  --strategy-types "11,3" \
  --intent-json "${intent_json}" \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result_qc-xxx.json
```

**关键**：`diversity_priority: "strategy_type"` 确保不同策略类型分散

---

## 🔄 按币种/方向指定数量

### 场景1：按币种指定数量

**用户**："给我生成策略组，风霆V4.3，SOL要2个，BCH要3个"

**intent JSON**：
```json
{
  "strategy_goal": "diversification",
  "constraints": {
    "coins": ["SOL", "BCH"],
    "directions": null,
    "min_strategies": 5,
    "coin_strategies_count": {
      "SOL": 2,
      "BCH": 3
    }
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "coin"
  }
}
```

### 场景2：按方向指定数量（对冲）

**用户**："BTC对冲，做多3个，做空2个"

**intent JSON**：
```json
{
  "strategy_goal": "hedging",
  "constraints": {
    "coins": ["BTC"],
    "directions": ["long", "short"],
    "min_strategies": 5,
    "group_strategies_count": {
      "long_BTC": 3,
      "short_BTC": 2
    }
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "direction"
  }
}
```

### 场景3：对冲自动平衡

**用户**："BTC对冲，要5个策略"（不指定具体多空比例）

**intent JSON**：
```json
{
  "strategy_goal": "hedging",
  "constraints": {
    "coins": ["BTC"],
    "directions": ["long", "short"],
    "min_strategies": 5
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "direction"
  }
}
```

**说明**：不使用 `group_strategies_count`，让对冲算法自动决定多空比例（如3:2或2:3）

### 适用性总结

| 字段 | 适用场景 | 不适用场景 |
|------|---------|-----------|
| `coin_strategies_count` | 多币种分散、跨币种对冲 | 同币种多空对冲 |
| `group_strategies_count` | 精确控制（任何场景） | 自动平衡场景 |

---

## 🚫 禁止的错误操作

### 错误1：自动修改币种

**场景**：用户要求 DOGE 策略，但数据不足

❌ **错误做法**：
```bash
# 自动把 DOGE 换成 BTC
--coins "BTC"  # ❌ 违反用户意图
```

✅ **正确做法**：
```
抱歉，DOGE 的策略数据不足。建议：

1. 增加其他币种（如 BTC、ETH）
2. 放宽时间范围
3. 降低 min_strategies 要求

请问您想调整哪些条件？
```

### 错误2：硬编码 ID

❌ **错误做法**：
```bash
# 直接写死策略类型 ID
--strategy-types "11"  # ❌ 没有查询列表
```

✅ **正确做法**：
```bash
# 1. 查询列表
cd skills/backtest-query && python3 query.py --list-strategies --agent-id "qc-xxx"

# 2. 匹配名称
# 风霆 → 11

# 3. 传递 ID
--strategy-types "11"
```

### 错误3：混淆资金配比和建仓比例

❌ **错误做法**：
```bash
# 用户说"资金配比各50%"
--coin-pct-map '{"BTC": ["50"], "ETH": ["50"]}'  # ❌ 这不是资金配比！
```

✅ **正确做法**：
```bash
# 用户说"资金配比各50%" → 这是回测参数
# 不传 --coin-pct-map
# 创建策略组后，提醒转到回测技能
```

### 错误4：传错误的 strategy_token

❌ **错误做法**：
```bash
# 使用 id 字段
--strategy-token "832548##2##2"  # ❌ 服务器不识别！
```

✅ **正确做法**：
```bash
# 使用 strategy_token 字段（Base64 格式）
--strategy-token "NzAxNzA1IyMyIyMy"  # ✅
```

### 错误5：传文件路径给 --intent-json

❌ **错误做法**：
```bash
# 传文件路径
--intent-json /tmp/intent.json  # ❌ JSON 解析失败
```

✅ **正确做法**：
```bash
# 传 JSON 字符串字面值
--intent-json '{"strategy_goal":"hedging",...}'  # ✅
```

---

## 🔍 数据不足的详细处理

### 输出格式

**成功时**：
```json
{
  "combinations": [...],        # 推荐的策略组合列表
  "total_fetched": 100,
  "total_selected": 50
}
```

**数据不足时**：
```json
{
  "error": "候选策略不足",
  "message": "找到 2 个策略，但需要至少 4 个",
  "suggestions": [
    "降低 min_strategies 要求（当前=4，建议≤2）",
    "放宽时间范围",
    "增加币种选择"
  ],
  "total_fetched": 10,
  "total_selected": 2
}
```

### 检查逻辑

```python
import json

# 读取结果文件
result = json.load(open(f'/tmp/result_{agent_id}.json'))

# 1. 优先检查 error 字段
if 'error' in result:
    error_message = result['message']
    suggestions = result.get('suggestions', [])
    
    # 构建友好回复
    reply = f"抱歉，{error_message}。"
    if suggestions:
        reply += "\n\n建议：\n"
        for i, s in enumerate(suggestions):
            reply += f"{i+1}. {s}\n"
    
    回复(reply)
    return

# 2. 检查 combinations 是否为空
if not result.get('combinations'):
    回复("未找到符合条件的策略组合。建议放宽条件重试。")
    return

# 3. 正常处理组合
combinations = result['combinations']
# ...
```

### 常见错误类型

| error 值 | 含义 | suggestions 示例 |
|---------|------|-----------------|
| `候选策略不足` | 筛选后策略数 < min_strategies | 降低 min_strategies 要求 |
| `无法生成组合` | 策略冲突（如只有做多，无做空） | 放宽方向限制 |
| `币种数据缺失` | 指定币种无回测数据 | 增加其他币种选择 |

---

## 📈 性能优化建议

### 1. 控制组合规模

```bash
# 复杂查询（5币×3策略×2时间 = ~1000+组合）
# 可能耗时 60-90 秒

# 优化方案：
--max-combinations 1          # 只返回最佳组合
--top-per-group 3             # 每组最多3个策略
```

### 2. 分批查询

**场景**：用户要求同时查询多个币种的策略

**优化**：分批查询，避免超时

```bash
# 不推荐：一次查询 10 个币种
--coins "BTC,ETH,SOL,DOGE,BCH,LTC,XRP,ADA,AVAX,DOT"

# 推荐：分 2-3 批查询
# 第1批：BTC,ETH,SOL,DOGE
# 第2批：BCH,LTC,XRP,ADA
# 第3批：AVAX,DOT
```

### 3. 提前告知用户

**复杂查询时**：
```
您的查询涉及 3 个币种 × 2 个策略类型 × 1 个时间范围，
预计需要 15-30 秒，请稍候...

正在查询中...
```

---

## 🔄 边界情况处理

### 情况1：用户只说"策略"

**用户**："推荐策略"

**处理**：
1. 询问币种
2. 询问策略类型
3. 都明确后再执行

### 情况2：用户说了模糊词

**用户**："推荐虚拟货币的策略"

**处理**：
1. 识别"虚拟货币"不是具体币种
2. 询问："请问您想查询哪些币种的策略？（如 BTC、ETH、DOGE 等）"

### 情况3：币种验证失败

**用户**："推荐狗币策略"

**处理**：
1. 查询 `--list-coins`
2. 尝试匹配："狗币" → "DOGE" ✅
3. 如果匹配失败 → "抱歉，未找到币种'狗币'，请确认币种名称。"

### 情况4：策略类型匹配失败

**用户**："推荐 BTC 的追涨策略"

**处理**：
1. 查询 `--list-strategies`
2. 尝试匹配："追涨" → 无匹配结果 ❌
3. 回复："抱歉，未找到策略类型'追涨'。可用策略类型：风霆、网格、趋势、鲲鹏等。"

### 情况5：推荐0个组合

**场景**：脚本返回空组合列表

**处理**：
```
未找到符合条件的策略组合。

可能原因：
1. 筛选条件过于严格
2. 该币种/策略类型数据不足

建议：
1. 放宽版本限制
2. 增加币种选择
3. 调整时间范围

请问您想如何调整？
```

---

## 🎓 进阶技巧

### 1. 利用 intent JSON 精确控制

**精确指定多空比例**：
```json
{
  "strategy_goal": "hedging",
  "constraints": {
    "group_strategies_count": {
      "long_BTC": 3,
      "short_BTC": 2
    }
  }
}
```

**多币种对冲**：
```json
{
  "strategy_goal": "hedging",
  "constraints": {
    "coins": ["BTC", "ETH"],
    "directions": ["long", "short"]
  },
  "preferences": {
    "diversity_priority": "coin"  # 关键：币种优先
  }
}
```

### 2. 风险级别调整

```json
{
  "preferences": {
    "risk_level": "aggressive"    // 激进
    // "risk_level": "balanced"   // 平衡
    // "risk_level": "conservative"  // 保守
  }
}
```

### 3. 多维度分散

```json
{
  "strategy_goal": "diversification",
  "preferences": {
    "diversity_priority": "strategy_type"  // 策略类型分散
    // "diversity_priority": "coin"        // 币种分散
    // "diversity_priority": "direction"   // 方向分散
  }
}
```

---

## 📚 相关文档

- **快速开始**：见 `SKILL.md`
- **典型案例集**：见 `EXAMPLES.md`
- **意图分析详细规则**：见 `INTENT_ANALYSIS.md`

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
