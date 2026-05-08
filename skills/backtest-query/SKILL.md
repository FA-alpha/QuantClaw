# 回测数据查询与策略组合

智能推荐策略组合。

---

## 命令

```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求" \
  --coins "BTC,ETH" \
  --strategy-types "11,7" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --ai-time-ids "3" \
  [其他参数...]
```

---

## Agent 核心规则

### 1. 触发关键词
策略组、回测组、组合、推荐、对冲

### 2. 查询优化（重要）
**轮询机制**：coins × strategy_types × versions × directions × time_ids = 组合数

**条件不足时引导**：
```
用户："推荐策略"（无条件）

Agent："请提供：
 1. 币种？（BTC/ETH/SOL，最多3-5个）
 2. 策略类型？（风霆/网格/马丁）
 3. 时间范围？（最近30天/90天）"
```

**优化优先级**：币种（影响最大）> 时间 > 策略类型

### 3. 动态查询参数
```bash
# 必须先查询，不要硬编码
python3 skills/backtest-query/query.py --list-coins       # 币种
python3 skills/backtest-query/query.py --list-strategies  # 策略类型（获取ID）
python3 skills/backtest-query/query.py --list-ai-times    # 时间ID
```

**策略类型 ID 映射**：
- 风霆V4 → 11
- 网格/星辰 → 7
- 马丁/风霆V1 → 1
- 鲲鹏V4 → 8

**时间 ID 映射**：
- 最近7天 → 2
- 最近30天 → 3
- 最近90天 → 1
- 最近180天 → 4

### 4. 版本控制
**统一用 `--strategy-version-map`，不用 `--versions`**

```json
{
  "11": ["4.3"],     // 简化格式：查该版本所有配置（推荐）
  "7": null,         // 查所有版本
  "1": [完整对象]     // 完整格式：不要手动构造
}
```

**规则**：
- 用户说 "V4.3" → `["4.3"]`（不扩展为 4.31、4.32）
- 用户说 "V4.3 3倍杠杆" → `["4.3"]`（简化格式，系统自动过滤）
- 用户未指定 → `null`

### 5. 方向控制
```json
// 格式（所有币种统一方向）
{"11": ["long", "short"]}

// 不支持按币种细分：
{"11": {"BTC": ["long"], "ETH": ["short"]}}  // ❌
```

### 6. 常用参数
- `--top-per-group N` - 每组取几个
- `--max-combinations 1` - 只返回1个最优组合
- `--min-total-win-rate` - 最小胜率（%）
- `--max-recent-drawdown` - 最大回撤（%）

---

## 典型案例

### 案例1：简单推荐
```bash
--query "BTC策略" --coins "BTC"
```

### 案例2：指定版本+时间
```bash
# 用户："风霆V4.3，最近30天，2个BTC多空"

# 步骤1：查时间ID
python3 skills/backtest-query/query.py --list-ai-times  # 得到 id=3

# 步骤2：推荐
--query "风霆V4.3，最近30天" \
--coins "BTC" \
--strategy-types "11" \
--strategy-version-map '{"11": ["4.3"]}' \
--ai-time-ids "3" \
--strategy-direction-map '{"11": ["long", "short"]}' \
--top-per-group 2 \
--max-combinations 1
```

### 案例3：多币种多策略
```bash
--query "BTC风霆 + ETH网格" \
--coins "BTC,ETH" \
--strategy-types "11,7" \
--strategy-version-map '{"11": ["4.3"], "7": null}'
```

---

## 结果处理

**提取 tokens**：
```python
tokens = [s["strategy_token"] for s in result["combinations"][0]["strategies"]]
```

**创建策略组**：
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名" \
  --strategy-tokens "token1,token2,token3"
```

---

## 性能参考

| 查询条件 | 组合数 | 耗时 |
|---------|--------|------|
| 1币 × 1策略 × 1时间 | ~50 | 3-5秒 |
| 3币 × 2策略 × 1时间 | ~300 | 15-30秒 |
| 30币 × 2策略 × 1时间 | ~3000 | 3-5分钟 |
