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
3. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
4. **一次性执行**：推荐时总是加 `--output`，避免二次运行
5. **数据验证优先**：
   - 多币种 → 先 `--list-coins` 验证币种存在
   - 多策略类型 → 先 `--list-strategies` 验证类型存在
   - 无效的参数不要传递，提示用户修改
7. **意图分析流程**（推荐组合时使用）：
   
   ```python
   # A. 数据验证（先查询列表，过滤无效参数）
   if 多币种场景:
       coins_result = exec("query.py --agent-id {aid} --list-coins")
       valid_coins = [验证并过滤用户提到的币种]
       if invalid: 提示用户
   
   if 多策略类型场景:
       strategies_result = exec("query.py --agent-id {aid} --list-strategies")
       valid_types = [验证并过滤]
       if invalid: 提示用户
   
   # B. 读取意图分析规则
   read('skills/backtest-query/INTENT_ANALYSIS.md')
   
   # C. 生成 intent JSON
   intent = {
     "strategy_goal": "hedging",  # 根据规则判断
     "constraints": {"coins": valid_coins, "directions": ["long","short"]},
     "preferences": {"diversity_priority": "direction"}
   }
   
   # D. 调用脚本（传递验证后的参数 + intent）
   exec(f"python3 smart_group_recommend.py \
     --agent-id {aid} \
     --coins '{','.join(valid_coins)}' \
     --intent-json '{json.dumps(intent)}' \
     --output /tmp/result.json")
   ```
   
   **关键点**：
   - 先验证数据存在，再生成 intent
   - intent 中的 coins/strategy_types 应该是验证后的有效值
   - 无效参数提示用户，不要自行替换

8. **数据不足处理**：
   - ❌ 禁止自行修改查询条件
   - ✅ 引导用户调整参数
   - 场景：币种不存在、策略类型无数据、无法生成组合

---

## 典型案例

### 案例1：创建对冲策略组

**用户**：`"建个 BTC 和 SOL 对冲策略组"`

```python
# 1. 验证币种
coins_data = exec("query.py --agent-id {aid} --list-coins")
valid_coins = ["BTC", "SOL"]  # 验证通过

# 2. 读取意图规则 → 生成 intent
read('INTENT_ANALYSIS.md')
intent = {"strategy_goal": "hedging", "constraints": {"coins": ["BTC","SOL"], "directions": ["long","short"]}}

# 3. 推荐（必须带 --output）
exec(f"smart_group_recommend.py --agent-id {aid} \
  --query '...' --coins 'BTC,SOL' \
  --strategy-direction-map '{{\"11\": [\"long\", \"short\"]}}' \
  --intent-json '{json.dumps(intent)}' \
  --output /tmp/combo.json")

# 4. 提取 tokens → 创建
tokens = [从 JSON 提取]
exec(f"query.py --agent-id {aid} --create-group --group-name '...' --strategy-tokens '{tokens}'")
```

---

### 案例2：币种无效时

**用户**：`"推荐 BTC 和 XYZ 策略"`

```python
# 1. 验证币种
coins_data = exec("query.py --agent-id {aid} --list-coins")
available = ["BTC", "ETH", "SOL", ...]  # XYZ 不在列表

# 2. 过滤 + 提示
valid_coins = ["BTC"]
回复："XYZ 币种暂无数据，为您推荐 BTC 策略。可选币种：BTC, ETH, SOL..."
# 然后用 valid_coins 继续
```

---

### 案例3：查询列表

**用户**：`"有哪些币种可以查"`

```bash
exec("query.py --agent-id {aid} --list-coins")
# 直接展示结果

---

## 参数说明

### smart_group_recommend.py 核心参数
```bash
--agent-id "qc-xxx"              # 必需，用于获取 token
--query "用户原话"               # 必需，用户需求
--coins "BTC,ETH"                # 币种（先验证）
--strategy-types "11,7"          # 策略类型（11=风霆, 7=网格）
--strategy-direction-map '{"11": ["long", "short"]}'  # 方向/合约方向
--coin-pct-map '{"BTC": ["80"]}'    # 比例/网格比例（BTC: 10~120, 其他: 60~140）
--ai-time-ids "16"               # 时间ID
--intent-json '{...}'            # 意图分析JSON（可选）
--max-combinations 3             # 返回几个组合
--output /tmp/result.json        # 必需，保存完整结果
```

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
