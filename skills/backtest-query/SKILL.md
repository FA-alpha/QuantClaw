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

## 🚨 意图识别与脚本选择

### 意图判断优先级

| 意图类型 | 触发条件 | 处理方式 |
|---------|---------|---------|
| **复合意图（创建+回测）** | "挑选/推荐/创建" + "回测" | 直接创建策略组，提醒回测 |
| **纯创建** | "创建/新建/建/构建" + 无"回测" | 直接创建策略组 |
| **纯推荐** | "推荐/建议/给我看看/挑选" + 无"回测" | 展示结果，询问是否创建 |
| **保存单策略** | "保存"/"收藏" | 收藏到策略库 |
| **查询列表** | "有哪些"/"列出"/"查看" | 展示列表 |

**核心规则**：
- 检测关键词组合（不要只看单个词）
- 看到 "回测" + 任何创建/挑选词 → 直接创建
- 只看到 "推荐/建议"，没有"回测" → 只展示，询问是否创建
- 创建时 `--max-combinations 1` 确保只返回一个最佳组合

### 复合意图识别（重要）

**触发特征**：既提到**挑选/推荐/创建策略**，又提到**回测**相关词汇

**正确处理流程**：
1. 先完成策略组创建（本技能）
2. 提醒转到回测技能（不在本技能处理）

**参数区分**：

| 参数类型 | 属于哪个技能 | 说明 |
|---------|------------|------|
| 币种、策略类型、版本、方向 | backtest-query | 用于创建策略组 |
| **资金配比**、保证金分配 | start-backtest | ❌ 不传给 backtest-query |
| "2025年全年"/"最近30天" | start-backtest | 不是AI时间ID |
| AI时间ID（"震荡行情"/"牛市"） | backtest-query | 用于筛选策略 |
| 策略建仓比例（60/80/100） | backtest-query | coin-pct-map，与资金配比无关 |

**时间参数判断**：

| 用户说法 | 类型 | 处理 |
|---------|-----|-----|
| "震荡行情"/"牛市"/"熊市" | AI时间ID | 查询 --list-ai-times，传给策略推荐 |
| "2025年"/"最近30天" + 有"回测" | 回测时间范围 | 不查询时间ID，留给回测技能 |
| "最近1年数据的策略" | AI时间ID | 查询 --list-ai-times，历史回测数据 |

**详细意图分析规则**：见 `INTENT_ANALYSIS.md`

---

## 执行规范

### 1. 前置确认（强制执行）

**适用范围**：仅调用 `smart_group_recommend.py` 时生效

#### 币种确认（必需）

- **用户已明确币种**（如 BTC、ETH、狗狗币）：
  1. 执行 `query.py --list-coins --agent-id xxx` 验证
  2. 验证通过 → 继续执行；验证失败 → 告知不存在

- **用户未提币种**（包括"加密货币"/"虚拟货币"等模糊词）：
  1. 询问："请问您想查询哪些币种的策略？（如 BTC、ETH、DOGE 等）"
  2. 用户回复"列表" → 执行 `query.py --list-coins --agent-id xxx`
  3. 用户回复具体币种 → 回到验证步骤

#### 策略类型确认（必需）

- **用户已明确策略类型**（风霆、网格、趋势等）：
  1. 执行 `query.py --list-strategies --agent-id xxx` 匹配
  2. 匹配成功 → 继续执行；匹配失败 → 告知不存在

- **用户未提策略类型**（包括"策略"/"回测策略"等模糊词）：
  1. 询问："请问您想查询哪种类型的策略？（如风霆、网格、趋势等）"
  2. 用户回复"列表" → 执行 `query.py --list-strategies --agent-id xxx`
  3. 用户回复具体策略类型 → 回到匹配步骤

### 2. 核心规范

1. **静默执行**：不显示命令，只返回结果
2. **参数铁律**：用户说的才传，没说的不传
3. **动态查询**（币种、策略类型、时间必须先查询列表）：禁止硬编码任何 ID/币种
4. **必须加 `--agent-id`**：所有脚本都需要
5. **使用 `--output` 保存结果**：`/tmp/result_${agent_id}.json`
6. **意图分析必做**：读取 `INTENT_ANALYSIS.md` → 生成 intent JSON → 传 `--intent-json`
7. **数据不足处理**：读取返回的 `error` 和 `suggestions` 字段，引导用户调整（禁止自行修改查询条件）

### 3. 意图 JSON 传递（重要）

**关键**：`--intent-json` 传递 JSON 字符串字面值，不是文件路径

**正确做法**：
```bash
agent_id="qc-xxx"
intent_json='{"strategy_goal":"hedging","constraints":{"coins":["DOGE","BCH"],"directions":["long","short"],"min_strategies":4},"preferences":{"risk_level":"balanced","diversity_priority":"coin"}}'

cd skills/backtest-query && python3 smart_group_recommend.py \
  --agent-id "${agent_id}" \
  --query "用户原话" \
  --coins "DOGE,BCH" \
  --strategy-types "11" \
  --intent-json "${intent_json}" \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result_${agent_id}.json
```

**生成步骤**：
1. 读取 `INTENT_ANALYSIS.md` 意图分析规则
2. 根据用户需求构建 JSON 对象（在内存中，不写文件）
3. 转为单行字符串，外层用单引号包裹

### 4. 参数传递规则

| 用户说了 | 操作 | 传递参数 |
|---------|-----|---------|
| 币种/策略名/时间 | 查询列表 → 匹配/验证 | 传递找到的值 |
| 版本（"V4.3"） | 直接提取 | `--strategy-version-map '{"11": ["4.3"]}'` |
| **明确方向**（"做多""做空"） | 直接提取 | `--strategy-direction-map '{"11": ["long"]}'` |
| **对冲/多空关键词** | 自动推断 | `--strategy-direction-map '{"11": ["long", "short"]}'` |
| 建仓比例（"80%"） | 直接提取 | `--coin-pct-map '{"BTC": ["80"]}'` |
| 数量（如"推荐3个"） | 提取数字 | `--max-combinations "3"` |
| 未说（时间/版本/方向） | 无操作 | 不传参数 |
| 未说数量 | 根据模式 | 创建=1, 推荐=3 |

**⚠️ 方向自动传递规则**：
- 用户说 "对冲""多空""对冲策略" → 自动传递 `["long", "short"]`
- 用户说 "做多" → 传递 `["long"]`
- 用户说 "做空" → 传递 `["short"]`
- 用户未提方向 → 不传参数

### 5. 数量识别规则

| 用户说法 | 识别为数量 | 传递参数 |
|---------|----------|---------|
| "一组"/"1组"/"一个" | 1 | `--max-combinations 1` |
| "两组"/"2组"/"两个" | 2 | `--max-combinations 2` |
| "多个"/"几个"/"一些" | 3 | `--max-combinations 3` |
| 完全未提数量 | 根据模式 | 创建=1, 推荐=3 |

### 6. 总是传递的参数

| 参数 | 取值规则 |
|------|---------|
| `--max-combinations` | 1. 用户说了数量 → 用户的数量<br>2. 创建模式 → `1`<br>3. 推荐模式 → `3` |
| `--top-per-group` | `3`（固定） |

---

## 参数说明

### smart_group_recommend.py

```bash
--agent-id "qc-xxx"                           # 必需
--query "用户原话"                            # 必需
--coins "BTC,ETH"                             # 币种（先验证）
--strategy-types "11,7"                       # 策略类型（11=风霆, 7=网格）
--strategy-version-map '{"11": ["4.3"]}'      # 版本过滤
--strategy-direction-map '{"11": ["long", "short"]}'  # 方向
--coin-pct-map '{"BTC": ["80"]}'              # 策略建仓比例（非资金分配）
--ai-time-ids "16"                            # 时间ID（用户说了才传）
--intent-json '{...}'                         # 意图JSON（必传）
--max-combinations 1                          # 总是传
--top-per-group 3                             # 总是传
--output /tmp/result_${agent_id}.json         # 必需
```

**输出 JSON 格式**：

成功时：
```json
{
  "combinations": [...],        # 推荐的策略组合列表
  "total_fetched": 100,
  "total_selected": 50
}
```

数据不足时：
```json
{
  "error": "候选策略不足",
  "message": "找到 2 个策略，但需要至少 4 个",
  "suggestions": [              # 引导用户的建议列表
    "降低 min_strategies 要求（当前=4，建议≤2）",
    "放宽时间范围"
  ]
}
```

### query.py

```bash
--agent-id "qc-xxx"                           # 用于自动获取 token
--list-coins / --list-strategies / --list-ai-times  # 查询列表
--detail "back_id"                            # 查看回测详情（需要回测记录ID）
--create-group --group-name "xxx" --strategy-tokens "t1,t2,t3"  # 创建组
--add-strategy --strategy-token "xxx"         # 保存单策略（使用 strategy_token）
```

**使用示例**：

**查看回测详情**：
```bash
cd skills/backtest-query && python3 query.py \
  --detail "12345" \
  --agent-id "qc-xxx"
```

**⚠️ 保存单策略注意**：必须使用 `strategy_token` 字段（Base64 格式），禁止使用 `id` 字段

---

## 推荐后用户选择的处理规则

### 核心区分：策略库 vs 策略组

| 类型 | 用途 | 命令 | 场景 |
|------|------|------|------|
| **策略库** | 保存单个策略 | `--add-strategy` | 用户选择了一个策略 |
| **策略组** | 保存多个策略组合 | `--create-group` | 用户要整个组合 |

### 推荐组合后的处理

| 用户回复 | 判断为 | 处理 |
|---------|--------|------|
| 策略名称/序号 | 单个策略 | `--add-strategy` → 询问是否回测 |
| "组合"/"全部"/"这几个" | 整个组合 | `--create-group` → 询问是否回测 |
| "回测"（不明确） | 需确认 | 先询问：单个还是组合？ |

**正确流程**：
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

**禁止的做法**：
- ❌ 用户说了单个策略名 → 自动创建策略组（应该保存到策略库）
- ❌ 用户说"回测" → 不询问就创建策略组（应该先确认单个/组合）
- ❌ 用户选择策略后 → 直接跳到 start-backtest（应该先保存）

---

## 延伸阅读

- **典型案例集**：见 `EXAMPLES.md`
- **高级规则/边界情况**：见 `ADVANCED.md`
- **意图分析详细规则**：见 `INTENT_ANALYSIS.md`
- **回测详情字段说明**：见 `BACKTEST_DETAIL.md`
