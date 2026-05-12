# 用户意图分析规则

**用途**：在调用 `smart_group_recommend.py` 前，AI Agent 读取本文件，分析用户意图，生成 JSON。

---

## 📊 输出格式

```json
{
  "strategy_goal": "...",       // 策略目标
  "constraints": {              // 硬约束（必须满足）
    "coins": [...],
    "directions": [...],
    "min_strategies": 3,
    "max_strategies": 5
  },
  "preferences": {              // 软偏好（优先考虑）
    "risk_level": "...",
    "diversity_priority": "...",
    "correlation_target": "..."
  },
  "user_hints": {               // 用户线索
    "keywords": [...],
    "sentiment": "..."
  }
}
```

---

## 🎯 字段说明

### strategy_goal（策略目标）

| 值 | 含义 | 触发条件 |
|---|------|---------|
| `hedging` | 对冲型：多空配合降低方向风险 | 用户提到"对冲"/"多空平衡" |
| `diversification` | 分散型：同方向多币种，降低单一风险 | 用户提到"分散"/"互补" + 单一方向 |
| `trend` | 趋势型：单一方向，赌趋势 | 明确只要"做多"或"做空"，无分散意图 |
| `hybrid` | 混合型：部分对冲+部分趋势 | 用户指定比例，如"60%做多+40%做空" |
| `unknown` | 不确定：交给算法自动推荐 | 无明确意图，如"推荐BTC策略" |

### directions（方向约束）

| 值 | 含义 | 示例 |
|---|------|------|
| `["long"]` | 只要做多 | "BTC做多策略" |
| `["short"]` | 只要做空 | "做空策略" |
| `["long", "short"]` | 两个方向都要 | "对冲策略"/"多空组合" |
| `null` | 不限制 | "推荐BTC策略"（未说明方向） |

### risk_level（风险偏好）

| 值 | 含义 | 触发关键词 |
|---|------|-----------|
| `aggressive` | 激进：追求高收益 | 激进、高收益、冒险、追牛市 |
| `conservative` | 保守：强调风险控制 | 保守、稳健、低回撤、安全 |
| `balanced` | 平衡（默认） | 其他情况 |

### diversity_priority（多样性优先级）

| 值 | 含义 | 适用场景 |
|---|------|---------|
| `coin` | 优先保证币种分散 | 多币种场景 |
| `direction` | 优先保证多空平衡 | 对冲场景 |
| `strategy_type` | 优先保证策略类型分散 | 单币种场景 |
| `parameter` | 优先保证参数分散 | 同策略不同配置 |

### correlation_target（相关性目标）

| 值 | 含义 |
|---|------|
| `low` | 追求低相关性（默认） |
| `medium` | 中等相关性可接受 |
| `any` | 不关心相关性 |

---

## 🔍 判断逻辑

### 1. 识别 strategy_goal

```python
if "对冲" in query or "多空" in query:
    strategy_goal = "hedging"
    
elif ("分散" in query or "互补" in query) and (单一方向):
    strategy_goal = "diversification"
    
elif 只提到一个方向 and not 分散意图:
    strategy_goal = "trend"
    
elif 指定了比例:
    strategy_goal = "hybrid"
    
else:
    strategy_goal = "unknown"
```

### 2. 识别 directions

```python
if "做多" in query or "看涨" in query or "long" in query:
    if "对冲" in query or "做空" in query:
        directions = ["long", "short"]  # 对冲需要双向
    else:
        directions = ["long"]
        
elif "做空" in query or "看跌" in query or "short" in query:
    if "对冲" in query:
        directions = ["long", "short"]
    else:
        directions = ["short"]
        
elif "对冲" in query or "多空" in query:
    directions = ["long", "short"]
    
else:
    directions = null  # 未限制
```

### 3. 识别 risk_level

```python
keywords = ["激进", "高收益", "冒险", "追", "牛市"]
if any(kw in query for kw in keywords):
    risk_level = "aggressive"
    
keywords = ["保守", "稳健", "低回撤", "安全", "防守"]
if any(kw in query for kw in keywords):
    risk_level = "conservative"
    
else:
    risk_level = "balanced"
```

### 4. 识别 diversity_priority

```python
if len(coins) > 1:
    diversity_priority = "coin"  # 多币种优先保证币种分散
    
elif strategy_goal == "hedging":
    diversity_priority = "direction"  # 对冲优先保证多空平衡
    
elif len(coins) == 1:
    diversity_priority = "strategy_type"  # 单币种优先策略类型分散
    
else:
    diversity_priority = "coin"  # 默认
```

---

## 📚 完整示例

### 示例1：对冲型

**用户输入**：`"帮我建个 BTC 和 SOL 的对冲策略组"`

**分析过程**：
1. 关键词："对冲" → `strategy_goal = "hedging"`
2. 提到 BTC 和 SOL → `coins = ["BTC", "SOL"]`
3. 对冲需要多空 → `directions = ["long", "short"]`
4. 至少2币种×2方向 → `min_strategies = 4`
5. 对冲场景 → `diversity_priority = "direction"`

**输出 JSON**：
```json
{
  "strategy_goal": "hedging",
  "constraints": {
    "coins": ["BTC", "SOL"],
    "directions": ["long", "short"],
    "min_strategies": 4,
    "max_strategies": 6
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "direction",
    "correlation_target": "low"
  },
  "user_hints": {
    "keywords": ["对冲", "策略组"],
    "sentiment": "neutral"
  }
}
```

---

### 示例2：分散型（同方向）

**用户输入**：`"推荐 BTC、ETH、SOL 的做多策略，分散风险"`

**分析过程**：
1. 关键词："分散"+"做多" → `strategy_goal = "diversification"`
2. 明确做多 → `directions = ["long"]`
3. 3个币种 → `coins = ["BTC", "ETH", "SOL"], min_strategies = 3`
4. 多币种 → `diversity_priority = "coin"`

**输出 JSON**：
```json
{
  "strategy_goal": "diversification",
  "constraints": {
    "coins": ["BTC", "ETH", "SOL"],
    "directions": ["long"],
    "min_strategies": 3,
    "max_strategies": 5
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "coin",
    "correlation_target": "low"
  },
  "user_hints": {
    "keywords": ["做多", "分散风险"],
    "sentiment": "bullish"
  }
}
```

---

### 示例3：趋势型（单方向）

**用户输入**：`"给我一个激进的 BTC 做多组合"`

**分析过程**：
1. 单一方向"做多" → `strategy_goal = "trend"`
2. 关键词："激进" → `risk_level = "aggressive"`
3. 只有 BTC → `coins = ["BTC"]`
4. 单币种 → `diversity_priority = "strategy_type"`

**输出 JSON**：
```json
{
  "strategy_goal": "trend",
  "constraints": {
    "coins": ["BTC"],
    "directions": ["long"],
    "min_strategies": 3,
    "max_strategies": 5
  },
  "preferences": {
    "risk_level": "aggressive",
    "diversity_priority": "strategy_type",
    "correlation_target": "medium"
  },
  "user_hints": {
    "keywords": ["激进", "做多"],
    "sentiment": "bullish"
  }
}
```

---

### 示例4：无明确意图

**用户输入**：`"推荐 BTC 策略"`

**分析过程**：
1. 无方向、无对冲、无分散 → `strategy_goal = "unknown"`
2. 未说明方向 → `directions = null`
3. 单币种 → `diversity_priority = "strategy_type"`

**输出 JSON**：
```json
{
  "strategy_goal": "unknown",
  "constraints": {
    "coins": ["BTC"],
    "directions": null,
    "min_strategies": 3,
    "max_strategies": 5
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "strategy_type",
    "correlation_target": "low"
  },
  "user_hints": {
    "keywords": [],
    "sentiment": "neutral"
  }
}
```

---

### 示例5：混合型（指定比例）

**用户输入**：`"BTC 策略组，60% 做多，40% 做空"`

**分析过程**：
1. 指定比例 → `strategy_goal = "hybrid"`
2. 两个方向 → `directions = ["long", "short"]`
3. 计算数量：假设5个策略 → 3个long + 2个short

**输出 JSON**：
```json
{
  "strategy_goal": "hybrid",
  "constraints": {
    "coins": ["BTC"],
    "directions": ["long", "short"],
    "min_strategies": 5,
    "max_strategies": 5
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "direction",
    "correlation_target": "low",
    "balance_ratio": {"long": 0.6, "short": 0.4}
  },
  "user_hints": {
    "keywords": ["60%", "40%"],
    "sentiment": "bullish"
  }
}
```

---

## 🔧 使用方式

### AI Agent 工作流

1. **读取本文件**：`read('skills/backtest-query/INTENT_ANALYSIS.md')`
2. **根据规则分析用户输入**，生成 JSON
3. **调用脚本**：
```python
exec(
    command=f"""
python3 skills/backtest-query/smart_group_recommend.py \
  --agent-id {agent_id} \
  --query "{user_query}" \
  --coins "BTC,SOL" \
  --intent-json '{intent_json}' \
  --max-combinations 3 \
  --output /tmp/combo.json
"""
)
```

---

## ⚠️ 注意事项

1. **JSON 转义**：确保 JSON 中的引号正确转义
2. **降级方案**：如果分析不出来，设置 `strategy_goal = "unknown"`
3. **保守为主**：不确定时，用 `balanced` 和 `null`（不限制）
4. **参数匹配**：`constraints.coins` 应与 `--coins` 参数一致
