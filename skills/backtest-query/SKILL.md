# 回测数据查询与策略组合

智能推荐策略组合并创建策略组。

---

## 🚨 关键区分

| 用户意图 | 关键词 | 使用技能 | 输出 |
|---------|--------|---------|------|
| 创建策略组 | 创建/建立/生成 + 策略组/回测组 | **本技能** | 策略组ID |
| 启动回测 | 启动/开始/运行 + 回测 | `start-backtest/` | 回测任务ID |

**判断规则**：
1. 包含"创建/建立/生成" → 本技能（创建策略组）
2. 包含"启动/开始/运行" → start-backtest 技能
3. 不确定 → 询问用户

---

## 命令格式（Agent 内部使用）

```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求" \
  --coins "BTC,ETH" \
  --strategy-types "11,7" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --ai-time-ids "3" \
  [其他参数...]
```

**⚠️ 执行规范**：
- 命令由 Agent **静默执行**
- **不要**在回复中显示命令本身
- **只返回**执行结果给用户

---

## Agent 核心规则

### 0. 意图识别（优先判断）

**创建策略组 vs 启动回测**：
```
✅ 创建策略组：
- "创建策略组"、"创建回测组"、"建立组合"、"生成策略组"
- 关键词：创建/建立/生成 + 策略组/回测组/组合

✅ 启动回测：
- "启动回测"、"开始回测"、"运行策略"
- 关键词：启动/开始/运行 + 回测

⚠️ 易混淆场景：
用户："创建一个回测组"
→ 正确理解：创建策略组（组合多个已有回测）
→ 错误理解：启动新的回测任务

判断规则：
1. 包含"创建/建立/生成" → 优先判断为创建策略组
2. 包含"启动/开始/运行" → 判断为启动回测
3. 不确定 → 询问用户："您是要创建策略组，还是启动新的回测？"
```

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

### 3. 动态查询参数（重要）
```bash
# 必须先查询，不要硬编码
python3 skills/backtest-query/query.py --list-coins       # 币种
python3 skills/backtest-query/query.py --list-strategies  # 策略类型（获取ID）
python3 skills/backtest-query/query.py --list-ai-times    # 时间ID
```

**⚠️ 参数传递铁律**：
```
用户明确说的 → 传入参数
用户没说的   → 不传参数（让系统自动查询）

❌ 错误示例：
用户："推荐 BTC 策略"
Agent 自作主张：--ai-time-ids "3"  （用户没说时间！）

✅ 正确示例：
用户："推荐 BTC 策略"
Agent：--coins "BTC" --strategy-types "11"
       （不传 --ai-time-ids，让系统查询所有时间）

用户："推荐 BTC 最近30天的策略"
Agent：执行 --list-ai-times → 找到 id=3
       --coins "BTC" --ai-time-ids "3"
```

**策略类型 ID 映射**（先查询）：
- 风霆V4 → 11
- 网格/星辰 → 7
- 马丁/风霆V1 → 1

**时间 ID 映射**（先查询）：
- 最近7天 → 2
- 最近30天 → 3
- 最近90天 → 1

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
- **用户未指定 → 不传参数**（不要自己决定传 `null` 或其他值）

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

### 案例1：简单推荐（用户未指定时间）
```bash
# 用户："推荐 BTC 策略"
# 只传用户明确说的参数
--query "BTC策略" --coins "BTC"

# ❌ 错误：不要自作主张加 --ai-time-ids
# ✅ 正确：不传时间参数，让系统查询所有时间
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

### 案例3：对冲策略（用户示例）
```bash
# 用户："推荐风霆V4.3策略 关于SOL和BTC的对冲策略组"
# 注意：用户没说时间！

# 步骤1：查询策略类型ID
python3 skills/backtest-query/query.py --list-strategies  # 得到 11

# 步骤2：推荐（不传时间参数）
--query "SOL和BTC对冲策略" \
--coins "SOL,BTC" \
--strategy-types "11" \
--strategy-version-map '{"11": ["4.3"]}' \
--strategy-direction-map '{"11": ["long", "short"]}'

# ⚠️ 注意：
# - 用户没说时间 → 不传 --ai-time-ids
# - 用户说"对冲" → 传 --strategy-direction-map
```

---

## 完整流程：创建策略组

**⚠️ 执行规范（重要）**：
- 所有命令由 Agent **静默执行**，不显示给用户
- 只返回执行结果，不显示命令本身
- 用户看到的应该是："✅ 已创建策略组"，而不是命令行

---

### 步骤1：推荐策略组合（静默执行）
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求" \
  --coins "BTC,ETH" \
  --strategy-types "11" \
  --max-combinations 1
```

### 步骤2：提取策略 tokens（内部处理）
```python
result = json.loads(output)
if "error" in result:
    return f"推荐失败：{result['error']}"

tokens = [s["strategy_token"] for s in result["combinations"][0]["strategies"]]
tokens_str = ",".join(tokens)
```

### 步骤3：创建策略组（静默执行）
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "策略组名称" \
  --strategy-tokens "token1,token2,token3"
```

### 步骤4：返回用户友好的结果
```
❌ 错误回复（显示命令）：
"创建命令：python3 skills/backtest-query/query.py --create-group ..."

✅ 正确回复（只显示结果）：
"✅ 已创建策略组：BTC+DOGE风霆V4.3对冲组合
  - 策略数量：3个
  - 组合ID：12345
  - 包含：2个BTC做多、1个DOGE做空"
```

### 自动创建决策
```
用户说"创建" → 静默执行步骤1-3，只返回结果
用户说"推荐" → 展示策略信息，问"是否创建？"
```

---

## 性能参考

| 查询条件 | 组合数 | 耗时 |
|---------|--------|------|
| 1币 × 1策略 × 1时间 | ~50 | 3-5秒 |
| 3币 × 2策略 × 1时间 | ~300 | 15-30秒 |
| 30币 × 2策略 × 1时间 | ~3000 | 3-5分钟 |
