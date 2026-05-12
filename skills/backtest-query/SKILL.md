# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 🚨 脚本选择

| 用户意图 | 使用脚本 | 说明 |
|---------|---------|------|
| 推荐策略组 | `smart_group_recommend.py` | 展示推荐结果 |
| 创建策略组 | `smart_group_recommend.py` → `query.py --create-group` | 先推荐，再创建 |
| 保存单个策略 | `query.py --add-strategy` | 收藏到策略库 |
| 查询列表 | `query.py --list-xxx` | 币种/策略类型/时间 |

**⚠️ 核心规则**：
- 创建策略组 = 推荐 + 创建（两步，因为需要 strategy_tokens）
- 查询列表用 `query.py`，推荐组合用 `smart_group_recommend.py`

---

## 执行规范

1. **静默执行**：不显示命令，只返回结果
2. **参数铁律**：用户说的才传，没说的不传
3. **动态查询**：用户说了时间/策略类型时，先查ID（`--list-ai-times` / `--list-strategies`）
4. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
5. **一次性执行**：推荐时总是加 `--output`，避免二次运行
6. **数据验证优先**：
   - 多币种 → 先 `--list-coins` 验证币种存在
   - 多策略类型 → 先 `--list-strategies` 验证类型存在
   - 无效的参数不要传递，提示用户修改

### 参数传递规则

| 用户说了 | 操作步骤 | 传递参数 |
|---------|---------|---------|
| "最近30天" / "30天" | 1. `query.py --list-ai-times` 查询ID<br>2. 找到对应ID（如 30天=id:16） | `--ai-time-ids "16"` |
| "风霆 V4.3" | 直接传递 | `--strategy-types "11"` + `--strategy-version-map '{"11": ["4.3"]}'` |
| "多空" / "对冲" | 直接传递 | `--strategy-direction-map '{"11": ["long", "short"]}'` |
| "比例80" / "网格比例100" | 直接传递 | `--coin-pct-map '{"BTC": ["80"]}'` |
| 未说时间 | 无需操作 | **不传** `--ai-time-ids` |
| 未说版本 | 无需操作 | **不传** `--strategy-version-map` |
| 未说方向 | 无需操作 | **不传** `--strategy-direction-map` |

### 总是传递的参数

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `--max-combinations` | `1` | 返回几个组合 |
| `--top-per-group` | `3` | 每组取几个策略 |

7. **意图分析流程**（推荐组合时使用）：
   
   ```python
   # A. 数据验证（先查询列表，过滤无效参数）
   if 多币种场景:
       coins_result = exec("query.py --agent-id {aid} --list-coins")
       valid_coins = [验证并过滤用户提到的币种]
       if invalid: 提示用户
   
   if 用户说了时间:
       time_result = exec("query.py --agent-id {aid} --list-ai-times")
       time_id = [根据用户说的"30天"查找对应ID]
   
   if 用户说了策略类型:
       strategies_result = exec("query.py --agent-id {aid} --list-strategies")
       strategy_ids = [查找对应ID，如"风霆"=11]
   
   # B. 读取意图分析规则
   read('skills/backtest-query/INTENT_ANALYSIS.md')
   
   # C. 生成 intent JSON
   intent = {
     "strategy_goal": "hedging",
     "constraints": {"coins": valid_coins, "directions": ["long","short"]},
     "preferences": {"diversity_priority": "direction"}
   }
   
   # D. 调用脚本（只传用户说了的参数）
   exec(f"python3 smart_group_recommend.py \
     --agent-id {aid} \
     --coins '{','.join(valid_coins)}' \
     --ai-time-ids '{time_id}' \  # 用户说了才传
     --intent-json '{json.dumps(intent)}' \
     --output /tmp/result.json")
   ```
   
   **关键点**：
   - 用户说了时间 → 先查 ID，再传参数
   - 用户说了策略类型 → 先查 ID，再传参数
   - 用户未说 → 不传参数，让脚本自动推荐

8. **数据不足处理**：
   - ❌ 禁止自行修改查询条件
   - ✅ 引导用户调整参数
   - 场景：币种不存在、策略类型无数据、无法生成组合

---

---

## 典型案例

### 案例：用户指定时间和版本

**用户**：`"创建风霆 V4.3 BTC 多空，最近 30 天"`

```python
# 步骤1：查询时间ID（因为用户说了"最近30天"）
time_result = exec("query.py --agent-id {aid} --list-ai-times")
# 从结果中找到：30天 → id:16

# 步骤2：推荐
exec(f"smart_group_recommend.py \
  --agent-id {aid} \
  --query '创建风霆 V4.3 BTC 多空，最近 30 天' \
  --coins 'BTC' \
  --strategy-types '11' \
  --strategy-version-map '{{\"11\": [\"4.3\"]}}' \
  --strategy-direction-map '{{\"11\": [\"long\", \"short\"]}}' \
  --ai-time-ids '16' \
  --max-combinations 1 \
  --top-per-group 3 \
  --output /tmp/result.json")

# 步骤3：提取 tokens → 创建策略组
tokens = [从JSON提取]
exec(f"query.py --agent-id {aid} --create-group ...")
```

**关键点**：
- 用户说了 "最近30天" → **必须先查 ID**，然后传 `--ai-time-ids "16"`
- 用户说了 "V4.3" → 传 `--strategy-version-map`
- 用户说了 "多空" → 传 `--strategy-direction-map`

---

## 参数说明

### smart_group_recommend.py 核心参数
```bash
--agent-id "qc-xxx"              # [必需] 用于获取 token
--query "用户原话"               # [必需] 用户需求
--coins "BTC,ETH"                # [条件必需] 币种（先验证）
--strategy-types "11,7"          # [可选] 策略类型（11=风霆, 7=网格，不传=所有）
--strategy-version-map '{"11": ["4.3"]}'  # [可选] 版本过滤（不传=所有版本）
--strategy-direction-map '{"11": ["long", "short"]}'  # [可选] 方向/合约方向
--coin-pct-map '{"BTC": ["80"]}'    # [可选] 比例/网格比例（BTC: 10~120, 其他: 60~140）
--ai-time-ids "16"               # [可选] 时间ID（用户明确说时才传）
--intent-json '{...}'            # [推荐] 意图分析JSON
--max-combinations 1             # [默认=1] 返回几个组合
--top-per-group 3                # [默认=3] 每组取几个策略
--output /tmp/result.json        # [必需] 保存完整结果
```

**参数传递原则**：
1. 用户明确指定的参数（如"风霆 V4.3" → 传 `--strategy-version-map '{"11": ["4.3"]}'`）
2. 总是传递的参数（`--max-combinations 1`, `--top-per-group 3`）
3. 用户未说的参数 → **不传**（如用户未说时间 → 不传 `--ai-time-ids`）

### query.py 常用命令
```bash
# 查询列表
--list-coins                     # 可用币种
--list-strategies                # 策略类型
--list-ai-times                  # 时间范围

# 创建/保存
--create-group --group-name "..." --strategy-tokens "t1,t2,t3"
--add-strategy --strategy-token "xxx"
```
