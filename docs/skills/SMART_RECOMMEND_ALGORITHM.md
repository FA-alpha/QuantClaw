# 智能推荐算法详解

**创建时间**: 2024-12-XX  
**版本**: v2.0（支持参数自动补全）

---

## 🎯 核心设计理念

**智能推荐 = 参数自动补全 + 多维评分 + 组合优化**

当用户需求参数不完整时，自动探索并推荐最优策略组合。

---

## 📊 完整流程

```
1. 参数补全  →  2. 数据查询  →  3. 组合生成  →  4. 多维评分  →  5. 排序推荐
```

---

## 1️⃣ 参数补全阶段

### 处理逻辑

| 参数 | 用户传入 | 系统处理 |
|------|---------|---------|
| 币种 | 指定 | 使用用户指定 |
| 币种 | 未指定 | 默认 `BTC, ETH, SOL` |
| 策略类型 | 指定 | 只查该类型 |
| 策略类型 | 未指定 | 查询多种类型 `11, 7, 1`（风霆/网格/鲲鹏） |
| 方向 | 指定 | 使用指定方向 |
| 方向 | 未指定 | 不限方向 |
| 时间 | 指定 `--ai-time-id` | 使用指定时间ID（**推荐**） |
| 时间 | 指定 `--year` | 使用指定年份（优先级低） |
| 时间 | 未指定 | 默认 `ai_time_id=5`（最近1年） |
| 时间 | 同时指定 | **优先使用 `--ai-time-id`** |

### 支持场景

```python
# 场景1：完全开放
python smart_recommend.py --token xxx
# → 查询 BTC/ETH/SOL × 风霆/网格/鲲鹏

# 场景2：指定币种
python smart_recommend.py --token xxx --coins "BTC,ETH"
# → 查询 BTC/ETH × 风霆/网格/鲲鹏

# 场景3：指定策略类型
python smart_recommend.py --token xxx --strategy-type 11
# → 查询 BTC/ETH/SOL × 风霆

# 场景4：完全指定
python smart_recommend.py --token xxx --coins "BTC" --strategy-type 11 --direction long
# → 查询 BTC × 风霆 × 做多
```

---

## 2️⃣ 数据查询阶段

### 查询策略

```python
for coin in coins:
    for strategy_type in strategy_types:
        query_backtest(
            token, coin, strategy_type, sort_type, 
            direction, year, ai_time_id, limit=10
        )
```

### 筛选条件（可选）

- `min_sharpe`: 最小夏普率
- `max_drawdown`: 最大回撤

**示例**：20 个策略筛选后剩余 12 个

---

## 3️⃣ 组合生成阶段

### 组合算法

```python
import itertools

# 生成所有 C(n, k) 组合
all_combinations = itertools.combinations(strategies, group_size)

# 限制计算量（默认1000）
if len(all_combinations) > max_combinations:
    all_combinations = random.sample(all_combinations, max_combinations)
```

**示例**：
- 12 个策略，选 3 个 → C(12,3) = 220 种组合
- 20 个策略，选 3 个 → C(20,3) = 1140 种 → 采样 1000 种

---

## 4️⃣ 多维评分阶段 ⭐核心

### 评分公式（总分100）

```python
总分 = 夏普率得分(40) + 回撤得分(30) + 相关性得分(20) + 回撤错位得分(10)
```

---

### 评分细节

#### **1. 夏普率得分（0-40分）**

```python
sharpe_score = min(sharpe / min_sharpe * 40, 40)

# 默认 min_sharpe = 1.5
```

| 夏普率 | 得分 |
|--------|------|
| ≥ 1.5 | 40（满分） |
| 1.0 | 26.7 |
| 0.75 | 20 |

---

#### **2. 回撤得分（0-30分）**

```python
if drawdown <= max_drawdown:
    drawdown_score = 30 * (1 - drawdown / max_drawdown)
else:
    drawdown_score = 0

# 默认 max_drawdown = 20%
```

| 回撤 | 得分 |
|------|------|
| 0% | 30（理想） |
| 10% | 15 |
| 20% | 0 |
| > 20% | 0（不推荐） |

---

#### **3. 相关性得分（0-20分）**

```python
if avg_corr <= max_correlation:
    corr_score = 20 * (1 - avg_corr / max_correlation)
else:
    corr_score = 0

# 默认 max_correlation = 0.5
```

**相关性计算**：
```python
# 基于 Pearson 相关系数
1. 提取各策略净值收益率序列
2. 计算两两相关性（取交集日期）
3. 构建相关性矩阵
4. 取上三角平均值
```

| 平均相关性 | 得分 |
|------------|------|
| 0 | 20（理想） |
| 0.25 | 10 |
| 0.5 | 0 |
| > 0.5 | 0（同质化） |

---

#### **4. 回撤错位得分（0-10分）**

```python
if overlap_ratio < 50:
    overlap_score = 10 * (1 - overlap_ratio / 50)
else:
    overlap_score = 0
```

**回撤重叠计算**：
```python
1. 识别每个策略的回撤期（开始/结束日期）
2. 构建时间轴，标记每天有多少策略在回撤
3. 计算"同时回撤"的天数占比
```

| 重叠比例 | 得分 |
|----------|------|
| 0% | 10（理想） |
| 25% | 5 |
| 50% | 0 |
| > 50% | 0（同时受损） |

---

### 评分示例

**假设组合**：
- 组合夏普率：2.0
- 组合回撤：12%
- 平均相关性：0.3
- 回撤重叠：20%

**计算**：
```
夏普率得分 = 2.0 / 1.5 × 40 = 40（满分）
回撤得分 = 30 × (1 - 12/20) = 12
相关性得分 = 20 × (1 - 0.3/0.5) = 8
回撤错位得分 = 10 × (1 - 20/50) = 6

总分 = 40 + 12 + 8 + 6 = 66 分
```

**推荐理由**：
- 高夏普率(2.00)
- 低回撤(12.0%)
- 相关性较低(0.30)
- 回撤错位良好(20%重叠)

---

## 5️⃣ 排序推荐阶段

```python
# 按总分降序
results.sort(key=lambda x: x['score'], reverse=True)

# 取前N个（默认5个）
top_recommendations = results[:top_n]
```

### 输出信息

- 📋 策略列表（名称、币种、年化、夏普、回撤）
- 📊 组合分析（相关性、组合夏普、回撤、胜率、回撤重叠）
- 💡 推荐理由（自动生成）
- 🔧 创建命令（一键复制）

---

## 🎛️ 可调整参数

### 用户偏好

```python
preferences = {
    'max_correlation': 0.5,    # 最大相关性
    'max_drawdown': 20.0,      # 最大回撤
    'min_sharpe': 1.5,         # 最小夏普率
}
```

### 风险偏好配置

| 风险偏好 | 参数配置 |
|---------|---------|
| 保守/稳健 | `max_drawdown=12, min_sharpe=2.0, max_correlation=0.4` |
| 平衡 | `max_drawdown=15, min_sharpe=1.5, max_correlation=0.5` |
| 进取/激进 | `max_drawdown=20, min_sharpe=1.2, max_correlation=0.6` |

### 查询参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `group_size` | 3 | 组合大小 |
| `top_n` | 5 | 推荐数量 |
| `max_combinations` | 1000 | 最大尝试组合数 |
| `limit` | 10 | 每币种/策略类型查询数量 |

---

## 🔍 核心数学原理

### Pearson 相关系数

```python
returns_a = diff(net_values_a) / net_values_a[:-1]
returns_b = diff(net_values_b) / net_values_b[:-1]

correlation = corrcoef(returns_a, returns_b)
```

**范围**: [-1, 1]
- -1: 完全负相关（一涨一跌）
- 0: 无相关
- 1: 完全正相关（同涨同跌）

### 组合指标（等权重）

```python
portfolio_metric = Σ(strategy_metric_i × weight_i)
weight_i = 1 / N

# 示例
portfolio_sharpe = (2.0 + 1.8 + 2.2) / 3 = 2.0
```

---

## 📈 算法特点

### ✅ 优势

1. **多维度评估**: 不只看收益，综合考虑风险、相关性、互补性
2. **权重平衡**: 
   - 收益（夏普）: 40%
   - 风险（回撤）: 30%
   - 分散性（相关性）: 20%
   - 互补性（回撤错位）: 10%
3. **参数自动补全**: 支持完全开放式查询
4. **灵活配置**: 用户可调整偏好
5. **可解释性**: 每个推荐都有明确理由

### 📊 性能

**计算复杂度**:
- 相关性矩阵: O(n²)
- 组合生成: C(n, k)
- 评分: O(组合数 × k)

**优化策略**:
- 限制组合数上限（1000）
- 随机采样（避免暴力枚举）
- 可选快速模式（`--no-detail`）

---

## 🚀 使用示例

### 完全开放式推荐

```bash
python smart_recommend.py \
  --token qc_xxx \
  --workspace ~/quantclaw \
  --save-memory

# 自动查询：BTC/ETH/SOL × 风霆/网格/鲲鹏 × 最近1年
```

### 保守型组合

```bash
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC,ETH" \
  --min-sharpe 1.8 \
  --max-drawdown 15 \
  --max-correlation 0.4 \
  --workspace ~/quantclaw \
  --save-memory
```

### 单币种多策略

```bash
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC" \
  --workspace ~/quantclaw \
  --save-memory

# 查询 BTC × 风霆/网格/鲲鹏
```

---

## 📝 版本历史

### v2.0 (2024-12-XX)
- ✨ 支持参数自动补全
- ✨ `coins` 和 `strategy_type` 改为可选
- ✨ 支持完全开放式推荐

### v1.0
- 🎉 初始版本
- 多维评分算法
- 相关性分析
- 回撤错位分析

---

**相关文件**:
- 实现: `/home/ubuntu/work/QuantClaw/skills/backtest-query/smart_recommend.py`
- 文档: `/home/ubuntu/work/QuantClaw/skills/backtest-query/skills/smart_recommend.md`
- 算法库: `/home/ubuntu/work/QuantClaw/skills/backtest-query/analysis/`
