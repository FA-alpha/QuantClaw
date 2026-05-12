# 用户意图分析规则

**用途**：分析用户策略组合需求，生成结构化 JSON，传递给 `smart_group_recommend.py`。

---

## 📊 输出格式

```json
{
  "strategy_goal": "hedging",        // 策略目标
  "constraints": {                   // 硬约束
    "coins": ["BTC", "SOL"],
    "directions": ["long", "short"], // null=不限制
    "min_strategies": 4
  },
  "preferences": {                   // 软偏好
    "risk_level": "balanced",        // aggressive | balanced | conservative
    "diversity_priority": "coin"     // coin | direction | strategy_type
  }
}
```

---

## 🎯 策略目标判断

| strategy_goal | 触发条件 | 说明 |
|--------------|---------|------|
| `hedging` | 包含"对冲"/"多空" | 多空配合降低风险 |
| `diversification` | 包含"分散"/"互补" + 单一方向/多币种/多策略类型 | 同类分散降低单一风险 |
| `trend` | 只提到一个方向，无分散意图 | 单一方向 |
| `unknown` | 无明确意图 | 交给算法自动推荐 |

**diversity_priority 细分**：
- `coin`: 多币种分散（相同策略类型，不同币种）
- `direction`: 多空平衡（同币种，不同方向） - 通常用于 hedging
- `strategy_type`: 多策略类型分散（相同币种，不同策略算法）

---

## 🔍 方向识别

- **只要做多**：`directions: ["long"]`
- **只要做空**：`directions: ["short"]`
- **对冲/多空**：`directions: ["long", "short"]`
- **未限制**：`directions: null`

---

## 📚 示例

### 对冲型
**输入**：`"BTC和SOL的对冲策略组"`
```json
{
  "strategy_goal": "hedging",
  "constraints": {
    "coins": ["BTC", "SOL"],
    "directions": ["long", "short"],
    "min_strategies": 4
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "direction"
  }
}
```

### 分散型
**输入**：`"推荐BTC、ETH、SOL的做多策略，分散风险"`
```json
{
  "strategy_goal": "diversification",
  "constraints": {
    "coins": ["BTC", "ETH", "SOL"],
    "directions": ["long"],
    "min_strategies": 3
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "coin"
  }
}
```

### 无明确意图
**输入**：`"推荐BTC策略"`
```json
{
  "strategy_goal": "unknown",
  "constraints": {
    "coins": ["BTC"],
    "directions": null,
    "min_strategies": 3
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "strategy_type"
  }
}
```

### 策略类型分散
**输入**：`"推荐BTC的风霆和鲲鹏组合"`
```json
{
  "strategy_goal": "diversification",
  "constraints": {
    "coins": ["BTC"],
    "strategy_types": ["11", "3"],
    "directions": null,
    "min_strategies": 2
  },
  "preferences": {
    "risk_level": "balanced",
    "diversity_priority": "strategy_type"
  }
}
```
