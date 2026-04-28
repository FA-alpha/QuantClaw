# 智能分组推荐系统使用示例

## 功能特性

### 🧠 智能分组
根据用户需求自动推断分组维度：
- 币种维度
- 方向维度（多/空）
- 策略类型维度
- 时间周期维度
- 杠杆维度

### 📊 详情深度分析
基于回测详情数据的高级筛选：
- 总胜率 / 近期胜率
- 总收益率 / 近期收益率
- 总回撤 / 近期回撤
- 交易次数
- 稳定性指标（近期表现 vs 总体表现）

### 🎯 工作流程
1. **智能分组**：根据需求自动分组
2. **多维度筛选**：每组按多种排序方式取 Top N（夏普率/收益率/回撤等）
3. **去重合并**：合并不同排序方式的结果
4. **详情获取**：批量获取策略详情
5. **深度筛选**：基于详情指标二次筛选
6. **组合优化**：形成最优策略组合

---

## 使用示例

### 示例 1：按币种分组推荐（默认多排序）

```bash
python3 smart_group_recommend.py \
  --query "帮我找BTC、ETH、SOL的最优策略" \
  --coins "BTC,ETH,SOL" \
  --top-per-group 3 \
  --min-total-win-rate 60 \
  --min-recent-profit-rate 10
```

**执行流程**：
1. 识别分组维度：`coin`
2. 分成 3 组：BTC / ETH / SOL
3. 每组按 3 种方式排序（夏普率、收益率、回撤），各取 Top 3
4. 去重后每组约 5-9 个策略
5. 获取详情并筛选：总胜率 ≥60%，近期收益 ≥10%
6. 生成最优组合

---

### 示例 1.1：指定排序方式

```bash
python3 smart_group_recommend.py \
  --query "帮我找BTC的最优策略" \
  --coins "BTC" \
  --top-per-group 5 \
  --sort-methods "sharpe,return,drawdown,win_rate" \
  --min-total-win-rate 60
```

**排序方式说明**：
- `sharpe`: 夏普率（收益/风险比）
- `return`: 年化收益率
- `drawdown`: 最小回撤
- `win_rate`: 胜率（需详情数据）
- `stability`: 稳定性（需详情数据）

**结果**：每组按 4 种方式各取 Top 5，去重后约 10-20 个策略

---

### 示例 2：按币种+方向分组（多排序）

```bash
python3 smart_group_recommend.py \
  --query "不同币种的多空策略组合" \
  --coins "BTC,ETH" \
  --directions "long,short" \
  --top-per-group 2 \
  --sort-methods "sharpe,return" \
  --min-stability 0.8 \
  --max-recent-drawdown 15
```

**执行流程**：
1. 识别分组维度：`coin` + `direction`
2. 分成 4 组：BTC多 / BTC空 / ETH多 / ETH空
3. 每组按 2 种方式各取 Top 2（去重后 2-4 个）
4. 获取详情并筛选：稳定性 ≥0.8，近期回撤 ≤15%
5. 生成平衡组合

---

### 示例 3：按策略类型分组

```bash
python3 smart_group_recommend.py \
  --query "网格和趋势策略的组合" \
  --strategy-types "11,7" \
  --top-per-group 5 \
  --min-trade-count 50 \
  --min-total-win-rate 55
```

**执行流程**：
1. 识别分组维度：`strategy_type`
2. 分成 2 组：网格策略 / 趋势策略
3. 每组取 Top 5
4. 筛选：交易次数 ≥50，总胜率 ≥55%
5. 形成多样化组合

---

### 示例 4：自动推断分组

```bash
python3 smart_group_recommend.py \
  --query "帮我找稳定的策略组合" \
  --top-per-group 8 \
  --min-total-win-rate 65 \
  --min-stability 0.9 \
  --max-combinations 5
```

**执行流程**：
1. 无明确分组需求 → 默认按币种分组
2. 查询全部币种
3. 每组取 Top 8
4. 严格筛选：胜率 ≥65%，稳定性 ≥0.9
5. 推荐 5 个最优组合

---

## 详情筛选条件说明

### `--min-total-win-rate`
最小总胜率（%），例如 60 表示 60%

### `--min-recent-profit-rate`
最小近期收益率（%），确保近期表现良好

### `--max-recent-drawdown`
最大近期回撤（%），控制风险

### `--min-trade-count`
最小交易次数，确保样本充足

### `--min-stability`
最小稳定性（0-1之间），计算公式：
```
稳定性 = 近期收益率 / 总收益率
```
- 接近 1：表现稳定
- 大于 1：近期表现更好
- 小于 1：近期表现下滑

---

## 输出结果

### 控制台输出
```
======================================================================
🧠 智能分组推荐系统
======================================================================

📝 用户需求: 帮我找BTC、ETH的最优策略
🎯 分组策略: coin

🔍 查询策略数据...
✅ 获取 245 条策略

📦 分组结果: 2 组
   - coin=BTC: 128 个策略
   - coin=ETH: 117 个策略

🎯 每组筛选 Top 5 策略并获取详情...

--- BTC ---
📊 选择前 5 个策略
📊 获取详情数据（最多 5 个）...
✅ 成功获取 5 个策略详情

🔬 应用详情筛选条件...
   筛选后剩余: 4/5

--- ETH ---
📊 选择前 5 个策略
📊 获取详情数据（最多 5 个）...
✅ 成功获取 5 个策略详情

🔬 应用详情筛选条件...
   筛选后剩余: 5/5

✅ 总计选出 9 个优质策略

🎲 生成策略组合（最多 10 个）...

======================================================================
📊 推荐结果摘要
======================================================================

🎯 分组维度: coin
📦 分组数量: 2 组
📊 总共获取: 245 条策略
✅ 筛选出: 9 条优质策略

🌟 推荐组合: 10 个

--- 组合 #1 ---
评分: 85.50
预期收益: 125.30%
组合回撤: 12.50%
策略数量: 3
策略列表:
  1. BTC / 网格策略v2 (年化120%, 夏普2.50, 总胜率65.0%, 近期收益15.5%)
  2. ETH / 趋势跟踪 (年化105%, 夏普2.20, 总胜率62.0%, 近期收益12.3%)
  3. BTC / 均线突破 (年化98%, 夏普2.10, 总胜率60.0%, 近期收益11.8%)

...
```

### JSON 输出（--output 参数）
```json
{
  "query": "帮我找BTC、ETH的最优策略",
  "group_by": ["coin"],
  "groups": {
    "('BTC',)": 128,
    "('ETH',)": 117
  },
  "total_fetched": 245,
  "total_selected": 9,
  "selected_strategies": [...],
  "combinations": [...],
  "criteria": {
    "min_total_win_rate": 60,
    "min_recent_profit_rate": 10
  }
}
```

---

## 高级用法

### 组合多个筛选条件

```bash
python3 smart_group_recommend.py \
  --query "高胜率稳定策略" \
  --top-per-group 10 \
  --min-total-win-rate 65 \
  --min-recent-profit-rate 15 \
  --max-recent-drawdown 10 \
  --min-trade-count 100 \
  --min-stability 0.9 \
  --output result.json
```

### 快速测试（静默模式）

```bash
python3 smart_group_recommend.py \
  --query "测试" \
  --coins "BTC" \
  --top-per-group 3 \
  --max-combinations 3 \
  --quiet
```

---

## 注意事项

1. **详情获取限制**：每组最多获取 `top_per_group` 个策略详情，避免 API 调用过多
2. **稳定性指标**：需要总收益率 > 0 才计算，否则为 0
3. **分组推断**：可能不准确，建议在查询中明确说明分组意图
4. **数据时效**：详情数据实时获取，确保最新

---

## 与其他版本对比

| 特性 | v1 | v2 | smart_group |
|-----|----|----|-------------|
| 自动分组 | ❌ | ❌ | ✅ |
| 详情筛选 | ❌ | ❌ | ✅ |
| 分组推荐 | ❌ | ❌ | ✅ |
| 稳定性分析 | ❌ | ❌ | ✅ |
| 智能推断 | ❌ | ❌ | ✅ |

---

## 典型场景

### 场景1：保守型投资者
```bash
--min-total-win-rate 70 \
--max-recent-drawdown 10 \
--min-stability 0.95
```

### 场景2：激进型投资者
```bash
--min-recent-profit-rate 20 \
--max-recent-drawdown 25 \
--min-trade-count 30
```

### 场景3：多样化组合
```bash
--query "不同币种不同方向的策略" \
--coins "BTC,ETH,SOL" \
--directions "long,short" \
--top-per-group 3
```

---

✅ 推荐使用此版本进行深度策略分析和组合优化！
