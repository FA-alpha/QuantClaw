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
