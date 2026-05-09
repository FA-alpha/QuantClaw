# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 🚨 意图识别

| 用户意图 | 关键词 | 使用技能 |
|---------|--------|---------|
| 创建策略组 | 创建/建立 + 策略组/回测组 | **本技能** |
| 启动回测 | 启动/开始 + 回测 | start-backtest |

**易混淆**："创建一个回测组" → 创建策略组（不是启动回测）

---

## Agent 核心规则

### 1. 执行规范（重要）
- 命令**静默执行**，不显示给用户
- 只返回结果："✅ 已创建策略组：xxx"
- 不暴露命令行或 token

### 2. 参数铁律
```
用户说的   → 传参数
用户没说的 → 不传参数（系统自动查询）

❌ 错误：用户没说时间，Agent 加 --ai-time-ids "3"
✅ 正确：用户没说时间，不传参数
```

### 3. 查询优化
**轮询机制**：coins × types × versions × directions × time_ids

**条件不足 → 引导用户**：
```
"请提供：
 1. 币种（BTC/ETH/SOL，3-5个）
 2. 策略类型（风霆/网格/马丁）
 3. 时间范围（最近30天/90天）"
```

**优化优先级**：币种 > 时间 > 策略类型

### 4. 动态查询参数（必须）
```bash
python3 skills/backtest-query/query.py --list-coins       # 币种
python3 skills/backtest-query/query.py --list-strategies  # 策略ID
python3 skills/backtest-query/query.py --list-ai-times    # 时间ID
```

**常用映射**（先查询确认）：
- 策略：风霆V4→11, 网格→7, 马丁→1
- 时间：最近7天→2, 30天→3, 90天→1

### 5. 版本控制
用 `--strategy-version-map`，不用 `--versions`

```json
{
  "11": ["4.3"],     // 查4.3所有配置
  "7": null          // 查所有版本（用户未说）
}
```

**规则**：
- 用户说"V4.3" → `["4.3"]`（不扩展）
- 用户说"V4.3 3倍杠杆" → `["4.3"]`（系统过滤）
- 用户未说 → 不传参数

### 6. 方向控制
```json
{"11": ["long", "short"]}  // 所有币种统一
```

**限制**：不支持按币种细分（如BTC做多、SOL做空）

---

## 完整流程

### 创建策略组（静默执行）
```bash
# 步骤1：推荐
python3 smart_group_recommend.py --query "..." --coins "BTC,ETH"

# 步骤2：提取 tokens
tokens = [s["strategy_token"] for s in result["combinations"][0]["strategies"]]

# 步骤3：创建
python3 query.py --create-group --group-name "..." --strategy-tokens "..."

# 步骤4：返回结果
"✅ 已创建策略组：xxx
  - 包含3个策略
  - 组合ID：12345"
```

**决策**：
- 用户说"创建" → 自动执行完整流程
- 用户说"推荐" → 展示结果，问是否创建

---

## 典型案例

### 案例1：简单推荐
```bash
# 用户："推荐BTC策略"（未说时间）
--query "BTC策略" --coins "BTC"
# ✅ 不传 --ai-time-ids
```

### 案例2：指定版本+时间
```bash
# 用户："风霆V4.3，最近30天，2个BTC多空"

# 1. 查时间ID
python3 query.py --list-ai-times  # 得到 id=3

# 2. 推荐
--query "风霆V4.3，最近30天" \
--coins "BTC" \
--strategy-types "11" \
--strategy-version-map '{"11": ["4.3"]}' \
--ai-time-ids "3" \
--strategy-direction-map '{"11": ["long", "short"]}' \
--top-per-group 2 \
--max-combinations 1
```

### 案例3：对冲策略
```bash
# 用户："SOL和BTC的风霆V4.3对冲策略组"（未说时间）

# 1. 查策略ID
python3 query.py --list-strategies  # 得到 11

# 2. 推荐
--query "SOL和BTC对冲" \
--coins "SOL,BTC" \
--strategy-types "11" \
--strategy-version-map '{"11": ["4.3"]}' \
--strategy-direction-map '{"11": ["long", "short"]}'
# ✅ 不传 --ai-time-ids（用户没说）
```

---

## 常用参数

- `--top-per-group N` - 每组取几个
- `--max-combinations 1` - 只返回1个最优组合
- `--min-total-win-rate` - 最小胜率（%）
- `--max-recent-drawdown` - 最大回撤（%）

---

## 性能参考

| 条件 | 组合数 | 耗时 |
|------|--------|------|
| 1币×1策略×1时间 | ~50 | 3-5秒 |
| 3币×2策略×1时间 | ~300 | 15-30秒 |
| 30币×2策略×1时间 | ~3000 | 3-5分钟 |
