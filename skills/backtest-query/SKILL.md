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
2. **参数规则**：
   - **用户明确说的**：严格按用户输入传递（币种、策略类型、版本、方向等）
   - **用户未说但必需的**：传递合理默认值（见下方默认值表）
   - **用户未说且可选的**：不传参数
3. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
4. **一次性执行**：推荐时总是加 `--output`，避免二次运行
5. **数据验证优先**：
   - 多币种 → 先 `--list-coins` 验证币种存在
   - 多策略类型 → 先 `--list-strategies` 验证类型存在
   - 无效的参数不要传递，提示用户修改

### 默认值规则

| 参数 | 默认值 | 触发条件 |
|------|-------|---------|
| `--ai-time-ids` | `"16"` | 用户未指定时间范围时（16 = 最近 30 天） |
| `--strategy-types` | `"11"` | 用户未指定策略类型时（11 = 风霆 V4.3） |
| `--max-combinations` | `1` | 总是传递（控制返回组合数） |
| `--top-per-group` | `3` | 总是传递（每组取几个策略） |

**时间 ID 映射**（通过 `query.py --list-ai-times` 查询）：
- 7天=id:13，14天=id:14，30天=id:16，60天=id:17

6. **意图分析流程**（推荐组合时使用）：
   
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

---

## 参数说明

### smart_group_recommend.py 核心参数
```bash
--agent-id "qc-xxx"              # [必需] 用于获取 token
--query "用户原话"               # [必需] 用户需求
--coins "BTC,ETH"                # [条件必需] 币种（先验证）
--strategy-types "11,7"          # [默认=11] 策略类型（11=风霆, 7=网格）
--strategy-version-map '{"11": ["4.3"]}'  # [可选] 版本过滤（不传=所有版本）
--strategy-direction-map '{"11": ["long", "short"]}'  # [可选] 方向/合约方向
--coin-pct-map '{"BTC": ["80"]}'    # [可选] 比例/网格比例（BTC: 10~120, 其他: 60~140）
--ai-time-ids "16"               # [默认=16] 时间ID（16=30天）
--intent-json '{...}'            # [推荐] 意图分析JSON
--max-combinations 1             # [默认=1] 返回几个组合
--top-per-group 3                # [默认=3] 每组取几个策略
--output /tmp/result.json        # [必需] 保存完整结果
```

**参数优先级**：
1. 用户明确指定的参数（如"风霆 V4.3" → `--strategy-version-map '{"11": ["4.3"]}'`）
2. 默认值（如用户未说时间 → `--ai-time-ids "16"`）
3. 不传（如用户未说方向 → 不传 `--strategy-direction-map`）

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
