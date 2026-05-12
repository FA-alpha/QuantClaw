# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 🚨 脚本选择（意图识别）

| 用户意图 | 触发关键词 | 使用脚本 | 执行方式 |
|---------|----------|---------|---------|
| **推荐策略组** | "推荐"/"建议"/"给我看看" | `smart_group_recommend.py` | 展示结果，**询问是否创建** |
| **创建策略组** | "创建"/"新建"/"建"/"构建"/"帮我建" | `smart_group_recommend.py` → `query.py --create-group` | **静默执行，直接创建** |
| 保存单个策略 | "保存"/"收藏" | `query.py --add-strategy` | 收藏到策略库 |
| 查询列表 | "有哪些"/"列出"/"查看" | `query.py --list-xxx` | 展示列表 |

**⚠️ 核心规则**：
1. 看到 "创建/建/构建" → **必须执行完整的两步流程**（推荐 + 创建），不要只推荐
2. 看到 "推荐/建议" → 只展示结果，询问用户是否创建
3. 创建时 `--max-combinations 1` 确保只返回一个最佳组合

---

## 执行规范

1. **静默执行**：不显示命令，只返回结果
2. **参数铁律**：用户说的才传，没说的不传
3. **动态查询**（关键步骤，三类数据都必须查询）：
   
   **币种**：
   - 用户提到币种 → `query.py --list-coins` 获取列表 → 验证币种是否存在 → 传递有效币种
   - 无效币种 → 提示用户，不要自行替换
   
   **策略类型**：
   - 用户说了策略名（如"风霆"/"网格"）→ `query.py --list-strategies` 获取列表 → 匹配名称 → 提取 ID
   - 用户说了策略ID（如"11"/"7"）→ 仍需查询列表验证ID有效
   
   **时间范围**（包括隐含时间需求）：
   - 明确时间：用户说"最近1年"/"30天" → `query.py --list-ai-times` → 匹配描述 → 提取 ID
   - 隐含时间：用户说"2025年行情"/"当前震荡" → 查询列表 → 根据列表描述和用户上下文选择最合适的 ID
   - 未说时间：完全未提及时间概念 → 不传参数
   
   **⚠️ 禁止猜测或硬编码任何 ID/币种**

4. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
5. **一次性执行**：推荐时总是加 `--output`，避免二次运行
6. **意图分析必做**：每次调用 `smart_group_recommend.py` 前，必须先读取 `INTENT_ANALYSIS.md` 生成 intent JSON

### 参数传递规则（所有涉及列表的都必须先查询）

| 用户说了 | 操作步骤 | 传递参数 |
|---------|---------|---------|
| **币种**（如"BTC"/"狗狗币"） | 1. `query.py --list-coins` 获取列表<br>2. 验证币种在列表中<br>3. 提取有效币种 | `--coins "BTC,ETH"` |
| **时间**（明确/隐含） | 1. `query.py --list-ai-times` 获取列表<br>2. 明确时间（如"最近1年"）→匹配描述<br>3. 隐含时间（如"2025年"）→根据列表和用户需求选择 | `--ai-time-ids "找到的ID"` |
| **策略名**（如"风霆"） | 1. `query.py --list-strategies` 获取列表<br>2. 匹配名称<br>3. 提取 ID | `--strategy-types "11"` |
| **策略版本**（如"V4.3"） | 直接传递（需要配合策略类型） | `--strategy-version-map '{"11": ["4.3"]}'` |
| **方向**（如"多空"） | 直接传递 | `--strategy-direction-map '{"11": ["long", "short"]}'` |
| **比例**（如"比例80"） | 直接传递 | `--coin-pct-map '{"BTC": ["80"]}'` |
| 未说时间 | 无需操作 | **不传** `--ai-time-ids` |
| 未说版本 | 无需操作 | **不传** `--strategy-version-map` |
| 未说方向 | 无需操作 | **不传** `--strategy-direction-map` |

### 总是传递的参数

| 参数 | 默认值 | 说明 | 重要性 |
|------|-------|------|-------|
| `--max-combinations` | `1` | 返回几个组合 | **创建时必须=1，只返回最佳组合** |
| `--top-per-group` | `3` | 每组取几个策略 | 每个币种/方向取几个策略 |

**⚠️ 特别注意**：
- 用户说 "创建/建/构建" → `--max-combinations 1`（只要最佳组合）
- 用户说 "推荐/对比" → `--max-combinations 3`（可以返回多个供选择）

8. **意图分析流程**（必需步骤）：
   - 使用 `smart_group_recommend.py` 时必须传递 `--intent-json`
   - 步骤：读取 `skills/backtest-query/INTENT_ANALYSIS.md` → 分析用户意图 → 生成 JSON → 传递参数
   - 不传会导致推荐结果不准确

---

---

## 典型案例

### 案例A：创建策略组（用户说"创建/建/构建"）

**用户说**："帮我构建一个 DOGE 与 BCH 对冲策略组"

```python
# 识别意图：包含"构建" → 创建模式（必须执行完整流程）

# 1. 查询币种（验证存在）
coins_result = exec("query.py --agent-id {aid} --list-coins")
valid_coins = ["DOGE", "BCH"]  # 验证通过

# 2. 读取意图规则 → 生成 intent JSON
read('skills/backtest-query/INTENT_ANALYSIS.md')
intent = {
  "strategy_goal": "hedging",
  "constraints": {"coins": ["DOGE","BCH"], "directions": ["long","short"]},
  "preferences": {"diversity_priority": "direction"}
}

# 3. 推荐（--max-combinations 1 确保只返回一个最佳组合）
result = exec("smart_group_recommend.py --agent-id {aid} \
  --coins 'DOGE,BCH' \
  --strategy-direction-map '{\"11\": [\"long\", \"short\"]}' \
  --max-combinations 1 \
  --top-per-group 3 \
  --intent-json '{json.dumps(intent)}' \
  --output /tmp/result.json")

# 4. 提取 tokens（从唯一的组合中）
tokens = result["combinations"][0]["strategies"] 提取所有 strategy_token

# 5. 创建策略组（自动执行，不询问）
exec("query.py --agent-id {aid} --create-group \
  --group-name 'DOGE与BCH对冲策略组' \
  --strategy-tokens '{','.join(tokens)}'")

# 6. 返回："✅ 已创建策略组：DOGE与BCH对冲策略组"
```

**⚠️ 关键**：看到 "创建/建/构建" → 必须执行第5步，不要只展示推荐结果

---

### 案例B：推荐策略组（用户说"推荐/建议"）

**用户说**："推荐 BTC 策略"

```python
# 识别意图：包含"推荐" → 推荐模式（只展示，不自动创建）

# 1-4 步骤同上（查询、生成intent、推荐）

# 5. 展示推荐结果，询问用户
回复："为您推荐以下策略组合：[展示结果]。是否创建策略组？"

# 如果用户确认 → 再执行 query.py --create-group
```

### 动态查询示例

#### 1. 币种查询（必做）
```python
# 用户说："推荐 BTC 和狗狗币策略"
coins_result = exec("query.py --agent-id {aid} --list-coins")
# 返回：["BTC", "ETH", "DOGE", "SOL", ...]

# 验证：BTC ✓, "狗狗币" → 匹配到 "DOGE" ✓
valid_coins = ["BTC", "DOGE"]
exec("smart_group_recommend.py --coins 'BTC,DOGE' ...")
```

#### 2. 策略类型查询
```python
# 用户说："推荐风霆策略"
strategies_result = exec("query.py --agent-id {aid} --list-strategies")
# 返回：[{"id": 11, "name": "风霆"}, {"id": 7, "name": "网格"}, ...]

# 匹配 "风霆" → id: 11
exec("smart_group_recommend.py --strategy-types '11' ...")
```

#### 3. 时间范围查询

**场景A：明确时间**
```python
# 用户说："最近1年"
time_result = exec("query.py --agent-id {aid} --list-ai-times")
# 返回：[{"id": 1, "description": "最近7天"}, {"id": 16, "description": "最近30天"}, {"id": 5, "description": "最近1年"}, ...]

# 匹配 "1年" → id: 5
exec("smart_group_recommend.py --ai-time-ids '5' ...")
```

**场景B：隐含时间（重要）**
```python
# 用户说："适用于 2025年震荡行情 的策略"
# 分析：提到"2025年"暗示需要最近数据

# 步骤1：获取时间列表
time_result = exec("query.py --agent-id {aid} --list-ai-times")
# 返回：[{"id": 1, "description": "最近7天"}, {"id": 16, "description": "最近30天"}, ...]

# 步骤2：分析
# "2025年震荡" → 需要最近的数据来分析当前行情
# 查看列表 → 选择"最近30天"较为合适（覆盖足够周期）

# 步骤3：传递选定的ID
exec("smart_group_recommend.py --ai-time-ids '16' ...")
```

**判断规则**：
- 提到年份/市场状态 → **算隐含时间，必须查询列表并根据列表内容选择**
- 完全未提及时间 → 不传参数

**⚠️ 常见错误**：不查询列表直接硬编码，导致参数不匹配

### 保存单策略
`query.py --add-strategy --strategy-token "xxx"`（策略库 ≠ 策略组）

---

## 参数说明

### smart_group_recommend.py
```bash
--agent-id "qc-xxx"              # 必需
--query "用户原话"               # 必需
--coins "BTC,ETH"                # 币种（先验证）
--strategy-types "11,7"          # 策略类型（11=风霆, 7=网格）
--strategy-version-map '{"11": ["4.3"]}'  # 版本过滤
--strategy-direction-map '{"11": ["long", "short"]}'  # 方向
--coin-pct-map '{"BTC": ["80"]}'    # 比例（BTC: 10~120, 其他: 60~140）
--ai-time-ids "16"               # 时间ID（用户说了才传）
--intent-json '{...}'            # 意图JSON（必传，从 INTENT_ANALYSIS.md 生成）
--max-combinations 1             # 总是传
--top-per-group 3                # 总是传
--output /tmp/result.json        # 必需
```

### query.py
```bash
--list-coins / --list-strategies / --list-ai-times  # 查询列表
--create-group --group-name "xxx" --strategy-tokens "t1,t2,t3"  # 创建组
--add-strategy --strategy-token "xxx"  # 保存单策略
```

### 参数规则
- 版本：用户说 "V4.3" → `{"11": ["4.3"]}`；未说 → 不传
- 方向：`{"11": ["long", "short"]}`（所有币种统一）
- 时间：用户说了才查ID再传，未说不传

### 性能参考
1币×1策略×1时间 ~50组合 3-5秒 | 3币×2策略×1时间 ~300组合 15-30秒
