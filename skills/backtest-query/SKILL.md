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
3. **动态查询**（关键步骤）：
   - 用户说了时间 → 必须先 `query.py --list-ai-times` 获取完整列表 → 从列表中匹配描述 → 提取 ID
   - 用户说了策略名 → 必须先 `query.py --list-strategies` 获取完整列表 → 从列表中匹配名称 → 提取 ID
   - ⚠️ 禁止猜测或硬编码 ID
4. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
5. **一次性执行**：推荐时总是加 `--output`，避免二次运行
6. **意图分析必做**：每次调用 `smart_group_recommend.py` 前，必须先读取 `INTENT_ANALYSIS.md` 生成 intent JSON
7. **数据验证优先**：
   - 多币种 → 先 `--list-coins` 验证币种存在
   - 多策略类型 → 先 `--list-strategies` 验证类型存在
   - 无效的参数不要传递，提示用户修改

### 参数传递规则

| 用户说了 | 操作步骤 | 传递参数 |
|---------|---------|---------|
| "最近7天/30天/1年" 等时间 | 1. `query.py --list-ai-times` 获取列表<br>2. 从列表中查找匹配的描述<br>3. 提取对应的 ID | `--ai-time-ids "找到的ID"` |
| "风霆" / "网格" 等策略名 | 1. `query.py --list-strategies` 获取列表<br>2. 从列表中匹配策略名<br>3. 提取对应的 ID | `--strategy-types "找到的ID"` |
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

8. **意图分析流程**（必需步骤）：
   - 使用 `smart_group_recommend.py` 时必须传递 `--intent-json`
   - 步骤：读取 `skills/backtest-query/INTENT_ANALYSIS.md` → 分析用户意图 → 生成 JSON → 传递参数
   - 不传会导致推荐结果不准确

---

---

## 典型案例

### 创建策略组（完整流程）
```python
# 1. 读取意图分析规则
read('skills/backtest-query/INTENT_ANALYSIS.md')

# 2. 生成 intent JSON（根据用户需求）
intent = {
  "strategy_goal": "hedging",  # 对冲/分散/趋势/未知
  "constraints": {"coins": ["BTC","SOL"], "directions": ["long","short"]},
  "preferences": {"risk_level": "balanced", "diversity_priority": "direction"}
}

# 3. 推荐（必须传 --intent-json）
exec("smart_group_recommend.py --agent-id {aid} --coins 'BTC,SOL' \
  --intent-json '{json.dumps(intent)}' --output /tmp/result.json")

# 4. 提取 tokens → 创建策略组
tokens = [从JSON提取]
exec("query.py --agent-id {aid} --create-group --group-name '...' --strategy-tokens '{tokens}'")
```

### 指定时间参数（重要）
```python
# 用户说："最近1年"
# 步骤1：获取时间列表
time_result = exec("query.py --agent-id {aid} --list-ai-times")
# 返回示例：[{"id": 1, "description": "最近7天"}, {"id": 5, "description": "最近1年"}, ...]

# 步骤2：从列表中查找匹配 "最近1年" 的项
matched = [找到 description 包含 "1年" 的项]  # {"id": 5, "description": "最近1年"}

# 步骤3：提取 ID 并传递
exec("smart_group_recommend.py --ai-time-ids '5' ...")
```

**⚠️ 常见错误**：不查询列表直接传 ID，导致 ID 不匹配

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
