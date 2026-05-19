# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 📁 脚本路径规范

**重要**：本 skill 的脚本位于 `skills/backtest-query/` 目录内。

执行方式（从 Agent 工作区）：
```bash
cd skills/backtest-query && python3 query.py --list-coins --agent-id xxx
cd skills/backtest-query && python3 smart_group_recommend.py --agent-id xxx --query "..."
```

---

## 🚨 脚本选择（意图识别）

### 意图判断优先级（从上到下）

**优先级1️⃣：复合意图（创建+回测）**
- **触发**：同时出现 "挑选/推荐/创建/建" + "回测"
- **示例**：
  - "挑选doge的策略，分别回测2025年"
  - "推荐sol策略搭配，资金配比各50%，回测全年"
- **处理**：**直接创建策略组**（不询问，不只推荐）
- **理由**：用户明确要回测，说明需要立即使用策略组

**优先级2️⃣：纯创建意图**
- **触发**："创建"/"新建"/"建"/"构建"/"帮我建"（无"回测"）
- **示例**：
  - "创建一个BTC和ETH的对冲策略组"
  - "帮我建个多币种策略组"
- **处理**：**直接创建策略组**

**优先级3️⃣：纯推荐意图**
- **触发**："推荐"/"建议"/"给我看看"/"挑选"（无"回测"）
- **示例**：
  - "推荐一些BTC策略"
  - "给我看看sol的策略搭配"
- **处理**：展示结果，**询问是否创建**

**优先级4️⃣：其他操作**
- 保存单个策略："保存"/"收藏"
- 查询列表："有哪些"/"列出"/"查看"

### 意图识别表格

| 用户意图 | 触发条件 | 执行方式 |
|---------|---------|---------|
| **复合意图（创建+回测）** | 有"挑选/推荐/创建/建" + 有"回测" | **直接创建**，然后提醒回测 |
| **纯创建** | 有"创建/新建/建/构建" + 无"回测" | **直接创建** |
| **纯推荐** | 有"推荐/建议/给我看看/挑选" + 无"回测" | 展示结果，**询问是否创建** |
| **保存单策略** | "保存"/"收藏" | 收藏到策略库 |
| **查询列表** | "有哪些"/"列出"/"查看" | 展示列表 |

**⚠️ 核心规则**：
1. **检测关键词组合**，不要只看单个词
2. 看到 "回测" + 任何创建/挑选词 → **直接创建**
3. 只看到 "推荐/建议"，没有"回测" → 只展示，询问是否创建
4. 创建时 `--max-combinations 1` 确保只返回一个最佳组合

---

## 🔗 复合意图识别（重要）

### 识别"策略组创建 + 回测"的复合需求

**触发特征**：
- 用户既提到了**挑选/推荐/创建策略**
- 又提到了**回测**相关词汇（"回测"/"分别回测"/"资金配比"）

**典型案例**：
```
用户："挑选doge，bch的策略搭配，资金配比各50%，分别回测2025年全年和2026年至今"
```

**正确处理流程**：

1️⃣ **先完成策略组创建**（本技能）
   - 提取策略组创建参数：币种（doge, bch）
   - **询问策略类型**（因为未明确）
   - **忽略回测相关参数**（资金配比、时间范围）
   - 创建策略组，记录 group_token

2️⃣ **提醒转到回测技能**（不在本技能处理）
   - 回复：
     ```
     ✅ 策略组已创建！
     
     📋 策略组信息：
     • 策略组ID: xxx
     • 币种: DOGE, BCH
     • 策略数: N个
     
     💡 检测到您还需要执行回测。回测参数：
     • 保证金分配: 各50%（共享模式）
     • 时间范围: 2025年全年 + 2026年至今
     
     请问现在开始回测吗？
     ```

**⚠️ 关键规则**：

| 参数类型 | 属于哪个技能 | 处理方式 |
|---------|------------|---------|
| 币种、策略类型、版本、方向 | backtest-query | 用于创建策略组 |
| **资金配比**、保证金分配 | start-backtest | **❌ 不传给 backtest-query！这是回测参数** |
| "2025年全年"/"最近30天"等 | start-backtest | **不是AI时间ID** |
| AI时间ID（"震荡行情"/"牛市"） | backtest-query | 用于筛选策略 |
| 策略建仓比例（60/80/100） | backtest-query | coin-pct-map，**与资金配比无关** |

**易混淆示例**：

❌ **错误处理**：
```
用户："挑选sol的策略，分别回测2025年全年"
Agent错误操作：
  1. 查询 --list-ai-times
  2. 匹配"2025年" → 传递时间ID给策略推荐脚本 ❌
```

✅ **正确处理**：
```
用户："挑选sol的策略，分别回测2025年全年"
Agent正确操作：
  1. 识别到"回测"关键词 → 这是复合意图
  2. 先询问策略类型，创建策略组
  3. "2025年全年"是回测时间范围，不传给策略推荐脚本
  4. 创建完成后，提醒转到回测技能
```

**时间参数判断规则**：

| 用户说法 | 类型 | 处理 |
|---------|-----|-----|
| "震荡行情"/"牛市"/"熊市" | AI时间ID | 查询 --list-ai-times，传给策略推荐 |
| "2025年"/"最近30天"/"全年" + **有"回测"关键词** | 回测时间范围 | **不查询时间ID，留给回测技能处理** |
| "最近1年数据的策略" | AI时间ID | 查询 --list-ai-times，有可能是指历史回测数据 |

---

## 执行规范

### 0. **前置确认**（强制执行，仅推荐/查询场景）

⚠️ **适用范围**：仅在调用 `smart_group_recommend.py`（推荐策略组）时生效
- ✅ 适用："推荐策略"/"给我看看策略"/"挑选策略"
- ❌ 不适用："创建策略组"/"添加策略"/"列出xxx"（已有明确tokens或操作）

⚠️ **强制规则**：在执行 `smart_group_recommend.py` 前，**必须先确认币种和策略类型**，否则脚本会报错。

#### 币种确认（必需）

**判断标准**：用户是否明确说了具体币种名称（如 BTC、ETH、狗狗币等）

- **用户已明确币种**：
  1. 先执行 `query.py --list-coins --agent-id xxx` 验证币种存在
  2. 如果验证通过 → 继续执行
  3. 如果验证失败 → 告知用户币种不存在

- **用户未提币种**（包括只说"加密货币"/"虚拟货币"/"ai回测策略"等模糊词）：
  1. **必须先询问**，不要直接执行脚本
  2. 询问话术：
     ```
     请问您想查询哪些币种的策略？（如 BTC、ETH、DOGE 等）
     如果不确定有哪些币种，可以输入"列表"查看所有可用币种。
     ```
  3. 用户回复"列表" → 执行 `query.py --list-coins --agent-id xxx`
  4. 用户回复具体币种 → 回到步骤1验证

#### 策略类型确认（必需）

**判断标准**：用户是否明确说了策略类型名称（风霆、网格、趋势、鲲鹏等）

- **用户已明确策略类型**：
  1. 先执行 `query.py --list-strategies --agent-id xxx` 匹配策略名称
  2. 如果匹配成功 → 继续执行
  3. 如果匹配失败 → 告知用户策略类型不存在

- **用户未提策略类型**（包括只说"策略"/"回测策略"/"ai回测"等模糊词）：
  1. **必须先询问**，不要直接执行脚本
  2. 询问话术：
     ```
     请问您想查询哪种类型的策略？（如风霆、网格、趋势等）
     如果不确定有哪些策略类型，可以输入"列表"查看所有策略类型。
     ```
  3. 用户回复"列表" → 执行 `query.py --list-strategies --agent-id xxx`
  4. 用户回复具体策略类型 → 回到步骤1匹配

#### ❌ 错误示例（不要这样做）

用户："帮我挑选 doge、bch 的 ai回测策略"
- ❌ 直接执行脚本（"ai回测策略"不是具体的策略类型名称）
- ✅ 应该先询问："请问您想查询哪种类型的策略？（如风霆、网格、趋势等）"

---

1. **静默执行**：不显示命令，只返回结果
2. **参数铁律**：用户说的才传，没说的不传
3. **动态查询**（三类数据必须先查询列表，时间必查）：
   - **币种**：`--list-coins` → 验证存在 → 传递
   - **策略类型**：`--list-strategies` → 匹配名称/验证ID → 传递
   - **时间**（强制步骤）：
     - **明确时间**（如"最近1年"）：查列表 → 匹配描述 → 传ID
     - **隐含时间**（如"2025年震荡"/"当前行情"）：查列表 → 找最匹配的 → 传ID
     - **完全未提时间**：不查列表，不传参数
     - ⚠️ **关键**：只要提到年份/市场状态，就算隐含时间，必须查列表并传ID
   - **禁止**硬编码任何 ID/币种

4. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
5. **使用 `--output` 保存结果**：使用 agent-id 命名临时文件避免冲突 → `/tmp/result_${agent_id}.json`
6. **意图分析必做**：每次调用 `smart_group_recommend.py` 前，必须先读取 `INTENT_ANALYSIS.md` 生成 intent JSON

### 🔑 意图 JSON 传递规范（重要）

**⚠️ 关键**：`--intent-json` 参数需要传递 **JSON 字符串字面值**，不是文件路径！

**正确做法**：
```bash
# 使用 --output 保存到临时文件
agent_id="qc-xxx"
cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "${agent_id}" \
  --query "用户原话" \
  --coins "DOGE,BCH" \
  --strategy-types "11" \
  --intent-json '{"strategy_goal":"hedging","constraints":{"coins":["DOGE","BCH"],"directions":["long","short"],"min_strategies":4},"preferences":{"risk_level":"balanced","diversity_priority":"coin"}}' \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result_${agent_id}.json
```

**❌ 错误做法**：
```bash
# 不要传文件路径！
--intent-json /tmp/intent.json  # ❌ 会导致 JSON 解析失败
```

**生成 intent JSON 的步骤**：

1. **读取意图分析规则**：
   ```bash
   cd skills/backtest-query && cat INTENT_ANALYSIS.md
   ```

2. **根据用户需求生成 JSON 对象**（在内存中构建，不写文件）：
   ```python
   # 示例：用户说 "DOGE和BCH对冲策略"
   intent_json = {
       "strategy_goal": "hedging",
       "constraints": {
           "coins": ["DOGE", "BCH"],
           "directions": ["long", "short"],
           "min_strategies": 4
       },
       "preferences": {
           "risk_level": "balanced",
           "diversity_priority": "coin"
       }
   }
   ```

3. **将 JSON 对象转为单行字符串**（用于命令行传递）：
   ```bash
   # 单行紧凑格式，外层用单引号包裹
   --intent-json '{"strategy_goal":"hedging","constraints":{"coins":["DOGE","BCH"],"directions":["long","short"],"min_strategies":4},"preferences":{"risk_level":"balanced","diversity_priority":"coin"}}'
   ```

**⚠️ 注意事项**：
- JSON 字符串外层必须用**单引号** `'...'` 包裹（避免 shell 解析问题）
- JSON 内部的字符串用**双引号** `"..."`
- 不要有换行符（保持单行）
- 不要使用文件路径

### 参数传递规则

| 用户说了 | 操作 | 传递参数 |
|---------|-----|---------|
| 币种/策略名/时间 | 查询列表 → 匹配/验证 | 传递找到的值 |
| 版本/方向/比例 | 直接提取 | 直接传递 |
| 数量（如"推荐3个"） | 提取数字 | `--max-combinations "3"` |
| 未说（时间/版本/方向） | 无操作 | 不传参数 |
| 未说数量 | 根据模式 | 创建=1, 推荐=3 |

### 数量识别规则（重要）

**明确数量关键词**：

| 用户说法 | 识别为数量 | 传递参数 |
|---------|----------|---------|
| "一组" / "1组" / "一个" | 1 | `--max-combinations 1` |
| "两组" / "2组" / "两个" | 2 | `--max-combinations 2` |
| "三组" / "3组" / "三个" | 3 | `--max-combinations 3` |
| "多个" / "几个" / "一些" | 3 | `--max-combinations 3`（默认） |
| 完全未提数量 | 根据模式 | 创建=1, 推荐=3 |

**示例**：
- ✅ "帮我**挑选一组**DOGE策略" → `--max-combinations 1`
- ✅ "推荐**3个**BTC策略组合" → `--max-combinations 3`
- ✅ "创建策略组"（未说数量） → `--max-combinations 1`（创建模式）
- ✅ "推荐策略"（未说数量） → `--max-combinations 3`（推荐模式）

**优先级**：
1. **数字优先**：用户明确说了数字（1、2、3等）
2. **量词识别**：一组、两个等
3. **模式默认**：创建模式=1, 推荐模式=3

### 总是传递的参数

| 参数 | 取值规则（优先级从高到低） |
|------|--------------------------|
| `--max-combinations` | 1. 用户说了数量 → 用户的数量<br>2. 创建模式 → `1`<br>3. 推荐模式 → `3` |
| `--top-per-group` | `3`（固定） |

7. **意图分析**（必需）：读取 `INTENT_ANALYSIS.md` → 生成 intent JSON → 传 `--intent-json`
8. **数据不足处理**：
   - ❌ 禁止自行修改查询条件（如自动替换币种）
   - ✅ 读取返回的 `error` 和 `suggestions` 字段，引导用户调整
   - 场景：
     - 币种无数据
     - 候选策略 < min_strategies
     - 无法生成组合

---

---

## 典型案例

### 案例：创建策略组（完整流程）

用户："帮我构建 DOGE 与 BCH 对冲策略组"

**完整执行步骤**：

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

# 4. 读取结果文件
```

**Python 伪代码检查逻辑**：
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
exec("query.py --create-group --strategy-tokens '{','.join(tokens)}'")

# 6. 返回："✅ 已创建"
```
⚠️ 关键：检查 error 字段，引导用户而不是自动修改参数

### 区分推荐与创建
- 推荐："推荐BTC策略" → 展示结果，询问是否创建
- 创建："建个策略组" → 直接创建，不询问
- 指定数量："推荐5个" → 传 max-combinations=5

### 动态查询示例

```python
# 币种："BTC和狗狗币" → 查列表 → 验证 → 传 "BTC,DOGE"
# 策略："风霆" → 查列表 → 匹配名称 → 传 id:11
# 时间："最近1年" → 查列表 → 匹配描述 → 传 id:5
# 隐含时间："2025年震荡" → 查列表 → 根据列表和需求选择合适ID
```
⚠️ 禁止硬编码，必须查询列表

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
--coin-pct-map '{"BTC": ["80"]}'    # ⚠️ 策略的建仓比例（非资金分配！）
                                    # BTC: 10/20/.../120, 其他: 60/80/.../140
                                    # 用户说"资金配比"时不传此参数！
--ai-time-ids "16"               # 时间ID（用户说了才传）
--intent-json '{...}'            # 意图JSON（必传，从 INTENT_ANALYSIS.md 生成）
--max-combinations 1             # 总是传
--top-per-group 3                # 总是传
--output /tmp/result_${agent_id}.json  # 必需，使用 agent_id 避免冲突
```

**输出 JSON 格式**（保存到 --output 文件中）：

成功时：
```json
{
  "combinations": [...],        # 推荐的策略组合列表（核心数据）
  "total_fetched": 100,
  "total_selected": 50,
  "selected_strategies": [...]
}
```

数据不足时：
```json
{
  "error": "候选策略不足",
  "message": "找到 2 个策略，但需要至少 4 个",
  "suggestions": [              # 引导用户的建议列表
    "降低 min_strategies 要求（当前=4，建议≤2）",
    "放宽时间范围",
    "增加币种选择"
  ],
  "total_fetched": 10,
  "total_selected": 2
}
```
⚠️ 必须检查 `error` 字段，有错误时显示 `suggestions` 引导用户

### query.py
```bash
--agent-id "qc-xxx"              # 用于自动获取 token
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

---


---

## 🚨 推荐后用户选择的处理规则

### 核心区分：策略库 vs 策略组

| 类型 | 用途 | 命令 | 场景 |
|------|------|------|------|
| **策略库** | 保存单个策略 | `--add-strategy` | 用户选择了一个策略 |
| **策略组** | 保存多个策略组合 | `--create-group` | 用户要整个组合 |

---

### 情况1：推荐的是组合（多个策略）

#### A. 用户选择单个策略

**触发词**：直接回复策略名称，不带"组合"/"全部"等词
```
用户："SOL-星辰-做多/5x/40/等差"
用户："第3个策略"
用户："1号"
```

**处理**：
```bash
# 1. 提取该策略的 token
# 2. 保存到策略库（单个）
cd skills/backtest-query && python3 query.py \
  --add-strategy \
  --strategy-token "NzAxNzA1IyMyIyMy"

# 3. 简短回复
```
✅ 已保存到策略库

策略：SOL-星辰-做多/5x/40/等差

需要回测吗？请告诉我回测参数。
```

#### B. 用户要整个组合

**触发词**："组合"/"全部"/"这几个"/"创建策略组"
```
用户："创建策略组"
用户："这个组合我要"
用户："保存这几个策略"
```

**处理**：
```bash
# 1. 提取所有策略的 tokens
# 2. 创建策略组
cd skills/backtest-query && python3 query.py \
  --create-group \
  --group-name "DOGE+HYPE 7策略组合" \
  --strategy-tokens "token1,token2,..."

# 3. 回复
```
✅ 已创建策略组 (ID: xxx, Token: yyy)

包含 7 个策略

需要回测吗？
```

#### C. 用户说"回测"（未明确单个/组合）

**触发词**："回测"/"测一下"/"开始回测"
```
用户："回测"
用户："帮我测一下"
```

**处理**：先询问清楚
```
检测到您需要回测。请问：

1️⃣ 回测单个策略 - 请告诉我具体哪个策略
2️⃣ 回测整个组合 - 我会创建策略组后回测全部 7 个策略

请选择回测方式。
```

**用户明确后再执行对应操作**

---

### 情况2：推荐的是单个策略

用户："保存" / "收藏" / "回测这个"

**处理**：直接保存到策略库
```bash
cd skills/backtest-query && python3 query.py \
  --add-strategy \
  --strategy-token "xxx"
```

---

### 🚫 禁止的做法

❌ 用户说了单个策略名 → 自动创建策略组（应该保存到策略库）
❌ 用户说"回测" → 不询问就创建策略组（应该先确认单个/组合）
❌ 用户选择策略后 → 直接跳到 start-backtest（应该先保存到策略库/策略组）

---

### ✅ 正确流程总结

```
推荐组合后
  ↓
用户回复
  ↓
判断意图：
  ├─ 单个策略名 → 保存到策略库 → 询问是否回测
  ├─ "组合"/"全部" → 创建策略组 → 询问是否回测
  └─ "回测"（不明确） → 先询问：单个还是组合？
```

