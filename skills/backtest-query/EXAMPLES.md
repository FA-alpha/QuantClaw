# 典型案例集

本文档提供 backtest-query 技能的详细使用案例。

---

## 案例1：创建策略组（完整流程）

**用户**："帮我构建 DOGE 与 BCH 对冲策略组"

### 执行步骤

```bash
# 1. 查币种验证
cd skills/backtest-query && python3 query.py --list-coins --agent-id "qc-xxx"

# 2. 根据 INTENT_ANALYSIS.md 生成 intent JSON（在内存中）
# 对冲策略 → hedging, 多币种 → diversity_priority: coin
agent_id="qc-xxx"
intent_json='{"strategy_goal":"hedging","constraints":{"coins":["DOGE","BCH"],"directions":["long","short"],"min_strategies":4},"preferences":{"risk_level":"balanced","diversity_priority":"coin"}}'

# 3. 执行推荐（保存到临时文件）
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "${agent_id}" \
  --query "帮我构建 DOGE 与 BCH 对冲策略组" \
  --coins "DOGE,BCH" \
  --strategy-types "11" \
  --strategy-direction-map '{"11": ["long", "short"]}' \
  --intent-json "${intent_json}" \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result_${agent_id}.json

# 4. 读取结果文件并检查
```

### Python 结果检查逻辑

```python
import json
agent_id = "qc-xxx"  # 从环境获取
result = json.load(open(f'/tmp/result_{agent_id}.json'))

# 检查是否有错误
if 'error' in result:
    # 数据不足：显示建议，引导用户调整
    suggestions = result.get('suggestions', [])
    回复：f"抱歉，{result['message']}。建议：\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
    return

# 检查是否有组合
if not result.get('combinations'):
    回复："未找到符合条件的策略组合。建议放宽条件重试。"
    return

# 5. 提取 tokens → 创建策略组
tokens = [s['strategy_token'] for s in result['combinations'][0]['strategies']]
cd skills/backtest-query && python3 query.py \
  --create-group \
  --group-name "DOGE+BCH对冲策略组" \
  --strategy-tokens "${tokens}" \
  --agent-id "${agent_id}"

# 6. 返回："✅ 已创建"
```

⚠️ **关键**：检查 error 字段，引导用户而不是自动修改参数

---

## 案例2：动态查询示例

### 币种查询
**用户**："BTC和狗狗币"

```bash
# 1. 查询列表
cd skills/backtest-query && python3 query.py --list-coins --agent-id "qc-xxx"

# 2. 验证币种存在（输出示例）
# BTC ✅
# DOGE ✅（匹配"狗狗币"）

# 3. 传递参数
--coins "BTC,DOGE"
```

### 策略类型查询
**用户**："风霆"

```bash
# 1. 查询列表
cd skills/backtest-query && python3 query.py --list-strategies --agent-id "qc-xxx"

# 2. 匹配名称（输出示例）
# 风霆 → id: 11

# 3. 传递参数
--strategy-types "11"
```

### 时间查询（AI时间ID）
**用户**："最近1年"

```bash
# 1. 查询列表
cd skills/backtest-query && python3 query.py --list-ai-times --agent-id "qc-xxx"

# 2. 匹配描述（输出示例）
# id: 5, name: "最近1年数据"

# 3. 传递参数
--ai-time-ids "5"
```

### 隐含时间示例
**用户**："2025年震荡行情"

```bash
# 1. 查询列表
cd skills/backtest-query && python3 query.py --list-ai-times --agent-id "qc-xxx"

# 2. 根据列表和需求选择合适ID（输出示例）
# id: 8, name: "2025震荡行情"

# 3. 传递参数
--ai-time-ids "8"
```

⚠️ **禁止硬编码**，必须查询列表

---

## 案例3：保存单个策略

**用户**："保存 SOL-星辰-做多/5x/40/等差"

### 步骤

```bash
# 1. 从推荐结果中提取 strategy_token（必须是 Base64 格式）
# 示例 JSON:
# {
#   "id": "832548##2##2",           // ❌ 不要用这个！
#   "strategy_token": "NzAxNzA1IyMyIyMy",  // ✅ 必须用这个！
#   "strategy_name": "SOL-星辰-做多/5x/40/等差"
# }

# 2. 保存到策略库
cd skills/backtest-query && python3 query.py \
  --add-strategy \
  --strategy-token "NzAxNzA1IyMyIyMy" \
  --agent-id "qc-xxx"

# 3. 回复
```
✅ 已保存到策略库

策略：SOL-星辰-做多/5x/40/等差

需要回测吗？请告诉我回测参数。
```
```

⚠️ **关键**：必须使用 `strategy_token` 字段（Base64 格式），禁止使用 `id` 字段！

---

## 案例4：推荐后用户选择单个策略

**场景**：Agent 推荐了一个包含 7 个策略的组合，用户只要其中一个

**用户回复**："SOL-星辰-做多/5x/40/等差" 或 "第3个策略" 或 "1号"

### 处理

```bash
# 1. 提取该策略的 strategy_token
# 2. 保存到策略库（单个）
cd skills/backtest-query && python3 query.py \
  --add-strategy \
  --strategy-token "NzAxNzA1IyMyIyMy" \
  --agent-id "qc-xxx"

# 3. 简短回复
```
✅ 已保存到策略库

策略：SOL-星辰-做多/5x/40/等差

需要回测吗？请告诉我回测参数。
```
```

---

## 案例5：推荐后用户要整个组合

**场景**：Agent 推荐了一个组合，用户要全部策略

**用户回复**："创建策略组" 或 "这个组合我要" 或 "保存这几个策略"

### 处理

```bash
# 1. 提取所有策略的 strategy_tokens
tokens="token1,token2,token3,token4,token5,token6,token7"

# 2. 创建策略组
cd skills/backtest-query && python3 query.py \
  --create-group \
  --group-name "DOGE+HYPE 7策略组合" \
  --strategy-tokens "${tokens}" \
  --agent-id "qc-xxx"

# 3. 回复
```
✅ 已创建策略组 (ID: xxx, Token: yyy)

包含 7 个策略

需要回测吗？
```
```

---

## 案例6：推荐后用户说"回测"（不明确）

**场景**：Agent 推荐了组合，用户直接说"回测"，没说单个还是组合

**用户回复**："回测" 或 "测一下" 或 "开始回测"

### 处理：先询问清楚

```
检测到您需要回测。请问：

1️⃣ 回测单个策略 - 请告诉我具体哪个策略
2️⃣ 回测整个组合 - 我会创建策略组后回测全部 7 个策略

请选择回测方式。
```

**用户明确后再执行对应操作**（参考案例4或案例5）

---

## 案例7：复合意图（创建+回测）

**用户**："挑选doge的策略，分别回测2025年"

### 正确处理流程

```bash
# 1. 识别到"回测"关键词 → 这是复合意图
# 2. 先询问策略类型（因为未明确）
```
请问您想查询哪种类型的策略？（如风霆、网格、趋势等）
```

# 3. 用户回复"风霆"
# 4. 创建策略组（不传"2025年"参数，这是回测时间范围）
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "qc-xxx" \
  --query "挑选doge的策略" \
  --coins "DOGE" \
  --strategy-types "11" \
  --intent-json '{...}' \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result_qc-xxx.json

# 5. 创建完成后，提醒转到回测技能
```
✅ 策略组已创建！

📋 策略组信息：
• 策略组ID: xxx
• 币种: DOGE
• 策略数: N个

💡 检测到您还需要执行回测。回测参数：
• 时间范围: 2025年全年

请问现在开始回测吗？
```
```

⚠️ **关键规则**：
- "2025年全年"是回测时间范围，不传给 `smart_group_recommend.py`
- "资金配比"/"保证金分配" 也是回测参数，不传给本技能
- 只有 AI时间ID（"震荡行情"/"牛市"）才传给策略推荐

---

## 案例8：数据不足的处理

**场景**：用户要求的策略组合无法满足（如只找到2个策略，但需要至少4个）

### 输出 JSON 示例

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

### 正确处理

```
抱歉，找到 2 个策略，但需要至少 4 个。建议：

1. 降低 min_strategies 要求（当前=4，建议≤2）
2. 放宽时间范围
3. 增加币种选择

请问您想调整哪些条件？
```

⚠️ **禁止的做法**：
- ❌ 自动修改币种（如把 DOGE 换成 BTC）
- ❌ 自动降低 min_strategies
- ✅ 显示 `suggestions`，引导用户调整

---

## 案例9：版本和方向的传递

**用户**："推荐 BTC 风霆 V4.3 做多策略"

### 参数提取

```bash
# 版本：用户说了 "V4.3"
--strategy-version-map '{"11": ["4.3"]}'

# 方向：用户说了 "做多"
--strategy-direction-map '{"11": ["long"]}'

# 完整命令
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "qc-xxx" \
  --query "推荐 BTC 风霆 V4.3 做多策略" \
  --coins "BTC" \
  --strategy-types "11" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --strategy-direction-map '{"11": ["long"]}' \
  --intent-json '{...}' \
  --max-combinations 3 \
  --top-per-group 3 \
  --output /tmp/result_qc-xxx.json
```

### 如果用户未提版本/方向

```bash
# 版本：未说 → 不传
# 方向：未说 → 不传

# 完整命令（精简版）
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "qc-xxx" \
  --query "推荐 BTC 风霆策略" \
  --coins "BTC" \
  --strategy-types "11" \
  --intent-json '{...}' \
  --max-combinations 3 \
  --top-per-group 3 \
  --output /tmp/result_qc-xxx.json
```

---

## 案例10：数量识别

### 明确数量

**用户**："帮我挑选**一组**DOGE策略"

```bash
# 识别："一组" → 1
--max-combinations 1
```

**用户**："推荐**3个**BTC策略组合"

```bash
# 识别："3个" → 3
--max-combinations 3
```

### 隐含数量

**用户**："创建策略组"（未说数量）

```bash
# 创建模式 → 默认 1
--max-combinations 1
```

**用户**："推荐策略"（未说数量）

```bash
# 推荐模式 → 默认 3
--max-combinations 3
```

---

## 性能参考

| 查询规模 | 组合数 | 耗时 |
|---------|-------|------|
| 1币×1策略×1时间 | ~50 | 3-5秒 |
| 3币×2策略×1时间 | ~300 | 15-30秒 |
| 5币×3策略×2时间 | ~1000+ | 60-90秒 |

⚠️ **建议**：
- 复杂查询（>500组合）提前告知用户需要等待
- 使用 `--max-combinations` 和 `--top-per-group` 控制输出规模
