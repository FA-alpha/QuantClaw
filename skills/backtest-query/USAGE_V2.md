# 智能推荐 v2 使用指南

## 🎯 核心理念

**任何参数指定了多个值，就需要循环该维度**

---

## 📝 命令行使用

### 基础用法

```bash
python3 smart_recommend_v2.py [参数]
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--coins` | 币种列表（逗号分隔） | `"BTC,ETH,SOL"` |
| `--strategy-types` | 策略类型列表 | `"11,7,1"` |
| `--directions` | 方向列表 | `"long,short"` |
| `--ai-time-ids` | 时间ID列表 | `"5,6,7"` |
| `--versions` | 版本列表 | `"1,2,3"` |
| `--leverages` | 杠杆列表 | `"3,5,10"` |
| `--grid-pcts` | 网格比例列表 | `"80,100,120"` |
| `--search-extends` | 扩展参数列表 | （具体值） |
| `--year` | 年份（单个） | `2024` |
| `--min-sharpe` | 最小夏普率 | `1.5` |
| `--max-drawdown` | 最大回撤 | `0.3` |
| `--save-memory` | 保存到 memory | （开关） |
| `--quiet` | 静默模式 | （开关） |

---

## 💡 典型场景

### 场景1：单币种全量查询

**需求**："查询 BTC 的所有策略"

```bash
python3 smart_recommend_v2.py --coins "BTC"
```

**查询次数**：1次  
**接口返回**：BTC 的所有策略类型、方向、版本、网格、时间周期的数据

---

### 场景2：多币种对冲

**需求**："BTC 和 SOL 对冲策略组"

```bash
python3 smart_recommend_v2.py \
  --coins "BTC,SOL" \
  --directions "long,short"
```

**查询次数**：4次
- BTC + long
- BTC + short
- SOL + long
- SOL + short

---

### 场景3：多策略类型对比

**需求**："对比 BTC 的马丁和网格策略"

```bash
python3 smart_recommend_v2.py \
  --coins "BTC" \
  --strategy-types "11,7"
```

**查询次数**：2次
- BTC + 策略11（马丁）
- BTC + 策略7（网格）

---

### 场景4：时间周期分析

**需求**："对比 BTC 在不同时间周期的表现"

```bash
python3 smart_recommend_v2.py \
  --coins "BTC" \
  --ai-time-ids "5,6,7"
```

**查询次数**：3次
- BTC + 最近1年
- BTC + 最近2年
- BTC + 最近3年

---

### 场景5：全维度组合

**需求**："BTC和ETH，做多和做空，马丁和网格"

```bash
python3 smart_recommend_v2.py \
  --coins "BTC,ETH" \
  --strategy-types "11,7" \
  --directions "long,short"
```

**查询次数**：8次（2×2×2）
- BTC + 策略11 + long
- BTC + 策略11 + short
- BTC + 策略7 + long
- BTC + 策略7 + short
- ETH + 策略11 + long
- ETH + 策略11 + short
- ETH + 策略7 + long
- ETH + 策略7 + short

---

### 场景6：指定筛选条件

**需求**："BTC 做多，夏普率>1.5，最大回撤<30%"

```bash
python3 smart_recommend_v2.py \
  --coins "BTC" \
  --directions "long" \
  --min-sharpe 1.5 \
  --max-drawdown 0.3
```

**查询次数**：1次  
**筛选**：代码端按夏普率和回撤筛选

---

## 🔢 查询次数计算

**查询次数 = 所有循环维度的笛卡尔积**

### 公式

```
总查询次数 = len(coins) × len(strategy_types) × len(directions) × len(ai_time_ids) 
            × len(versions) × len(leverages) × len(grid_pcts) × len(search_extends)
```

**注意**：未指定的维度不参与计算（等于1）

### 示例

| 参数 | 查询次数 |
|------|---------|
| `--coins "BTC"` | 1 |
| `--coins "BTC,ETH"` | 2 |
| `--coins "BTC" --strategy-types "11,7"` | 1×2 = 2 |
| `--coins "BTC,ETH" --directions "long,short"` | 2×2 = 4 |
| `--coins "BTC,ETH" --strategy-types "11,7" --directions "long,short"` | 2×2×2 = 8 |
| `--coins "BTC,ETH,SOL" --strategy-types "11,7,1" --directions "long,short" --ai-time-ids "5,6"` | 3×3×2×2 = 36 |

---

## 🐍 Python 调用

### 导入

```python
from smart_recommend_v2 import SmartRecommenderV2

recommender = SmartRecommenderV2(token, verbose=True)
```

### 场景示例

```python
# 1. 多币种对冲
strategies = recommender.fetch_strategies(
    coins=['BTC', 'SOL'],
    directions=['long', 'short']
)

# 2. 多策略对比
strategies = recommender.fetch_strategies(
    coins=['BTC'],
    strategy_types=[11, 7],
    min_sharpe=1.5
)

# 3. 时间周期分析
strategies = recommender.fetch_strategies(
    coins=['BTC'],
    ai_time_ids=['5', '6', '7']
)

# 4. 全维度组合
strategies = recommender.fetch_strategies(
    coins=['BTC', 'ETH'],
    strategy_types=[11, 7],
    directions=['long', 'short'],
    ai_time_ids=['5', '6']
)
```

---

## ⚙️ 参数规则

### 单个值 vs 多个值

| 参数类型 | 行为 | 示例 |
|---------|------|------|
| **单个值** | 固定参数，传给接口 | `coins=['BTC']` → `search_coin=BTC` |
| **多个值** | 循环维度，逐个查询 | `coins=['BTC', 'ETH']` → 查询2次 |
| **未指定** | 不传参数，接口返回全量 | `coins=None` → 接口返回所有币种 |

### 固定参数 vs 循环参数

```python
# 示例1：coins 固定，strategy_types 循环
fetch_strategies(
    coins=['BTC'],           # 固定参数 → search_coin=BTC
    strategy_types=[11, 7]   # 循环维度 → 查询2次
)

# 示例2：coins 和 directions 都循环
fetch_strategies(
    coins=['BTC', 'ETH'],       # 循环维度
    directions=['long', 'short'] # 循环维度
)
# 查询次数 = 2×2 = 4次
```

---

## 📊 输出示例

```
🚀 智能推荐 v2 - 接口优化版
============================================================
🔄 币种循环: ['BTC', 'SOL']
🔄 方向循环: ['long', 'short']

📊 预计查询次数: 4
   - coins: 2 个
   - directions: 2 个

🔍 [1/4] 查询: 币种=BTC / 方向=long
✅ 返回 312 条数据

🔍 [2/4] 查询: 币种=BTC / 方向=short
✅ 返回 289 条数据

🔍 [3/4] 查询: 币种=SOL / 方向=long
✅ 返回 156 条数据

🔍 [4/4] 查询: 币种=SOL / 方向=short
✅ 返回 142 条数据

📦 总计获取: 899 条策略数据
   - 币种: 2 个 ['BTC', 'SOL']
   - 方向: 2 个 ['long', 'short']
   - 策略类型: 5 个 [1, 7, 11, 12, 15]

🎯 智能推荐组合
============================================================
...
```

---

## ⚠️ 注意事项

1. **查询次数控制**：避免过多维度组合导致查询爆炸
2. **接口限制**：接口必须支持部分参数查询
3. **性能优化**：v2 相比 v1 性能提升 95%+

---

**更新时间**: 2024-04-27  
**版本**: v2.0.0
