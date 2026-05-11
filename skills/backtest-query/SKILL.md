# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 🚨 脚本选择决策树（必读）

**关键原则**：根据用户意图选择正确的脚本

```
用户输入
    │
    ├─ 包含"推荐"/"建议"/"帮我选" + 策略组相关
    │  → smart_group_recommend.py（智能推荐）
    │  → 展示推荐结果，询问是否创建
    │
    ├─ 包含"创建"/"新建"/"建立" + 策略组相关
    │  → smart_group_recommend.py（先推荐）
    │  → query.py --create-group（再创建）
    │  → 静默执行，只返回结果
    │
    ├─ 包含"保存"/"收藏"/"添加" + 单个策略
    │  → query.py --add-strategy
    │  → 需要 strategy_token 参数
    │
    └─ 其他查询需求（查币种/策略/时间列表等）
       → query.py --list-xxx
```

### ⚠️ 常见错误判断

| 用户说的 | ❌ 错误 | ✅ 正确 |
|---------|--------|--------|
| "帮我建个 DOGE/BCH 对冲策略组" | query.py | smart_group_recommend.py → query.py --create-group |
| "推荐 BTC 策略" | query.py | smart_group_recommend.py |
| "创建策略组：BTC+ETH" | query.py | smart_group_recommend.py → query.py --create-group |
| "保存这个策略" | smart_group_recommend.py | query.py --add-strategy |
| "查看有哪些币种" | smart_group_recommend.py | query.py --list-coins |

---

## 📋 意图识别表

| 用户意图 | 关键词 | 第一步脚本 | 第二步脚本 | 说明 |
|---------|--------|-----------|-----------|------|
| **智能推荐** | 推荐/建议/帮我选 + 策略组 | smart_group_recommend.py | - | 展示结果 |
| **创建策略组** | 创建/新建/建立 + 策略组 | smart_group_recommend.py | query.py --create-group | 静默执行 |
| **保存单策略** | 保存/收藏/添加 + 策略 | query.py --add-strategy | - | 需要 token |
| **查询列表** | 查看/列出/有哪些 | query.py --list-xxx | - | 查币种/策略/时间 |
| 启动回测 | 启动/开始 + 回测 | start-backtest | - | 其他技能 |

**关键判断规则**：
1. 看到"策略组" + "创建/建/推荐" → **必须先用 smart_group_recommend.py**
2. 看到"策略" (单数) + "保存/收藏" → 用 query.py --add-strategy
3. 看到"查询/列出/有哪些" → 用 query.py --list-xxx

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

### 🎯 流程1：智能推荐（仅展示，不创建）

**触发词**：推荐、建议、帮我选、看看

```bash
# 步骤1：调用推荐脚本
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户的完整输入" \
  --coins "BTC,ETH" \
  --strategy-types "11" \
  --ai-time-ids "3"
  # 其他参数按需添加

# 步骤2：解析结果并展示
展示前 3 个推荐组合的：
- 策略列表
- 收益率
- 胜率
- 回撤

# 步骤3：询问用户
"以上是推荐结果，是否创建策略组？"
```

**示例**：
```
用户："推荐 BTC 和 ETH 的对冲策略"
Agent：调用 smart_group_recommend.py → 展示结果 → 等待用户确认
```

---

### 🏗️ 流程2：创建策略组（推荐 + 创建，静默执行）

**触发词**：创建、新建、建立、帮我建

**⚠️ 关键**：必须先推荐，再创建（两步流程）

```bash
# 步骤1：智能推荐（与流程1相同）
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户的完整输入" \
  --coins "DOGE,BCH" \
  --strategy-types "11" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --strategy-direction-map '{"11": ["long", "short"]}' \
  --ai-time-ids "3"

# 步骤2：提取最优组合的 tokens（解析 JSON）
result = json.loads(output)
tokens = [s["strategy_token"] for s in result["combinations"][0]["strategies"]]

# 步骤3：创建策略组
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "DOGE/BCH 风霆V4.3 对冲组合" \
  --strategy-tokens "token1,token2,token3"

# 步骤4：返回结果
"✅ 已创建策略组：DOGE/BCH 风霆V4.3 对冲组合
  - 包含 3 个策略
  - 组合ID：12345
  - 预期年化收益率：45.2%"
```

**示例**：
```
用户："帮我建个 DOGE 和 BCH 的对冲策略组"
Agent：
  1. 调用 smart_group_recommend.py（获取最优组合）
  2. 调用 query.py --create-group（创建）
  3. 返回 "✅ 已创建策略组：xxx"
```

**❌ 错误示例**（避免）：
```
用户："帮我建个 DOGE 和 BCH 的对冲策略组"
Agent：直接调用 query.py --create-group  ← 错误！缺少推荐步骤
```

---

### 💾 流程3：保存单个策略到策略库（静默执行）

**触发词**：保存、收藏、添加 + 策略（单数）

```bash
# 步骤1：保存策略
python3 skills/backtest-query/query.py \
  --add-strategy \
  --strategy-token "xxx"

# 步骤2：返回结果
"✅ 策略保存成功 (ID: 12345)"
```

**使用场景**：
- 用户说："保存这个策略" / "收藏策略" / "添加到策略库"
- 需要 strategy_token（从回测结果或推荐结果中获取）

**⚠️ 注意**：
- 策略库 ≠ 策略组
- 策略库：单个策略收藏
- 策略组：多个策略组合

---

### 📋 流程4：查询元数据（列表查询）

**触发词**：查看、列出、有哪些

```bash
# 查币种列表
python3 skills/backtest-query/query.py --list-coins

# 查策略列表
python3 skills/backtest-query/query.py --list-strategies

# 查时间配置
python3 skills/backtest-query/query.py --list-ai-times
```

**使用场景**：
- 用户说："有哪些币种可以回测？"
- 用户说："查看所有策略类型"
- 用户说："支持哪些时间范围？"

---

## 📚 典型案例（正确 vs 错误对比）

### 案例1：创建对冲策略组 ⭐

**用户输入**：
```
"帮我建个 DOGE 和 BCH 的对冲策略组"
```

**✅ 正确流程**：
```bash
# 步骤1：智能推荐（必须先执行）
python3 skills/backtest-query/smart_group_recommend.py \
  --query "帮我建个 DOGE 和 BCH 的对冲策略组" \
  --coins "DOGE,BCH" \
  --strategy-direction-map '{"11": ["long", "short"]}'
  # 用户未说时间、策略，不传参数

# 步骤2：提取 tokens
tokens = extract_tokens_from_result(result)

# 步骤3：创建策略组
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "DOGE/BCH 对冲策略组" \
  --strategy-tokens "token1,token2,token3"

# 步骤4：返回结果
"✅ 已创建策略组：DOGE/BCH 对冲策略组"
```

**❌ 错误流程（避免）**：
```bash
# 直接调用 query.py 创建（缺少推荐步骤）
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "DOGE/BCH 对冲策略组"
  # ❌ 没有 strategy-tokens，无法创建
```

---

### 案例2：简单推荐（仅展示）

**用户输入**：
```
"推荐 BTC 策略"
```

**✅ 正确流程**：
```bash
# 步骤1：智能推荐
python3 skills/backtest-query/smart_group_recommend.py \
  --query "推荐 BTC 策略" \
  --coins "BTC"
  # ✅ 用户未说时间、策略类型，不传参数

# 步骤2：展示结果（不创建）
展示前 3 个推荐组合

# 步骤3：询问
"以上是推荐结果，是否创建策略组？"
```

**❌ 错误流程**：
```bash
# 使用 query.py 查询数据（不是推荐）
python3 skills/backtest-query/query.py --list-strategies
# ❌ 这只能列出策略类型，无法智能推荐组合
```

---

### 案例3：指定版本+时间创建

**用户输入**：
```
"创建风霆 V4.3 BTC 多空策略组，用最近 30 天数据"
```

**✅ 正确流程**：
```bash
# 步骤1：查时间ID（如果缓存没有）
python3 skills/backtest-query/query.py --list-ai-times
# 得到：最近30天 → id=3

# 步骤2：智能推荐
python3 skills/backtest-query/smart_group_recommend.py \
  --query "创建风霆 V4.3 BTC 多空策略组" \
  --coins "BTC" \
  --strategy-types "11" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --strategy-direction-map '{"11": ["long", "short"]}' \
  --ai-time-ids "3"

# 步骤3：提取 tokens 并创建
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC 风霆 V4.3 多空组合" \
  --strategy-tokens "token1,token2"

# 步骤4：返回
"✅ 已创建策略组：BTC 风霆 V4.3 多空组合"
```

---

### 案例4：对冲策略（未说时间）

**用户输入**：
```
"SOL 和 BTC 的风霆 V4.3 对冲策略组"
```

**✅ 正确流程**：
```bash
# 步骤1：查策略ID（如果需要）
python3 skills/backtest-query/query.py --list-strategies
# 得到：风霆 → 11

# 步骤2：智能推荐
python3 skills/backtest-query/smart_group_recommend.py \
  --query "SOL 和 BTC 的风霆 V4.3 对冲策略组" \
  --coins "SOL,BTC" \
  --strategy-types "11" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --strategy-direction-map '{"11": ["long", "short"]}'
  # ✅ 用户未说时间，不传 --ai-time-ids

# 步骤3-4：创建策略组（同案例1）
```

---

### 案例5：保存单个策略（区别于策略组）

**用户输入**：
```
"保存这个策略"（假设上下文有 strategy_token）
```

**✅ 正确流程**：
```bash
# 直接使用 query.py 保存
python3 skills/backtest-query/query.py \
  --add-strategy \
  --strategy-token "abc123..."

# 返回
"✅ 策略保存成功 (ID: 12345)"
```

**⚠️ 注意**：
- 这是"保存策略"，不是"创建策略组"
- 不需要调用 smart_group_recommend.py

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
