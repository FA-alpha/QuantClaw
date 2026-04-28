# 两层排序策略说明

## 📊 设计理念

### 两层筛选机制

```
API 层（粗筛）
    ↓ 决定数据类型
客户端层（精选）
    ↓ 多维度筛选
最终结果
```

---

## 🎯 第一层：API 排序（粗筛）

### 作用
决定返回什么**类型**的数据

### 排序选项

| sort_type | 说明 | 返回数据特征 | 适用场景 |
|-----------|------|-------------|---------|
| 1 | 最新 | 最近创建的策略 | 追踪最新算法 |
| **2** | **收益率（默认）** | **高收益策略** | **收益优先** |
| 3 | 夏普率 | 高性价比策略 | 稳健投资 |
| 4 | 回撤率 | 低风险策略 | 风险控制 |

### 默认选择：收益率（sort_type=2）

**理由**：
- ✅ 符合大多数用户需求
- ✅ 收益率是首要关注指标
- ✅ 客户端可进一步筛选其他维度

---

## 🔍 第二层：客户端排序（精选）

### 作用
从 API 返回的数据中，按**多个维度**精选优质策略

### 排序方式（7种）

| 排序 | 说明 | 优先级 |
|-----|------|-------|
| `score` | 综合评分 | ⭐⭐⭐ |
| `sharpe` | 夏普率 | ⭐⭐⭐ |
| `return` | 年化收益率 | ⭐⭐⭐ |
| `drawdown` | 最小回撤 | ⭐⭐⭐ |
| `win_rate` | 总胜率 | ⭐⭐ |
| `stability` | 稳定性 | ⭐⭐ |
| `custom:xxx` | 自定义字段 | ⭐ |

### 默认组合
```bash
--sort-methods "sharpe,return,drawdown"
```

---

## 💡 配合策略

### 场景1：收益优先（默认推荐）

```bash
# API: 按收益率（默认）
# 客户端: 按夏普+收益+回撤
--sort-methods "sharpe,return,drawdown"
```

**逻辑**：
1. API 返回高收益策略（收益 100%-200%）
2. 客户端从中选：
   - 高夏普的（风险收益比好）
   - 高收益的（强化收益）
   - 低回撤的（控制风险）

**结果**：高收益 + 多维度优化

---

### 场景2：稳健投资

```bash
# API: 按夏普率
--api-sort 3 \
--sort-methods "return,drawdown,score"
```

**逻辑**：
1. API 返回高夏普策略（夏普 1.5-3.0）
2. 客户端从中选：
   - 高收益的（提升收益）
   - 低回撤的（加强风险控制）
   - 高评分的（综合优质）

**结果**：稳健 + 收益兼顾

---

### 场景3：风险控制

```bash
# API: 按回撤率
--api-sort 4 \
--sort-methods "sharpe,return,score"
```

**逻辑**：
1. API 返回低回撤策略（回撤 5%-15%）
2. 客户端从中选：
   - 高夏普的（性价比好）
   - 高收益的（保证收益）
   - 高评分的（综合考虑）

**结果**：低风险 + 合理收益

---

### 场景4：最新算法

```bash
# API: 按最新
--api-sort 1 \
--sort-methods "score,sharpe,return"
```

**逻辑**：
1. API 返回最新策略
2. 客户端从中选：
   - 高评分的（平台推荐）
   - 高夏普的（稳健）
   - 高收益的（收益）

**结果**：最新 + 优质

---

## 📈 效果对比

### 示例：BTC 策略（假设1000个）

#### 单层排序（只用API）
```
API 按收益率 → 返回 Top 100 高收益
问题: 可能都是激进策略，风险大
```

#### 单层排序（只用客户端）
```
获取全部 1000 个 → 客户端按夏普排序
问题: 数据杂乱，计算量大
```

#### 两层排序（API + 客户端）
```
API 按收益率 → 返回 Top 100 高收益策略
    ↓
客户端多维度排序:
  - 按夏普 Top 5 → [A, B, C, D, E]
  - 按收益 Top 5 → [B, F, G, D, H]
  - 按回撤 Top 5 → [I, J, A, K, L]
    ↓
去重合并 → [A, B, C, D, E, F, G, H, I, J, K, L]
    ↓
获取详情 → 深度筛选 → 组合优化
```

**优势**：
- ✅ API 粗筛：减少数据量，定向高收益
- ✅ 客户端精选：多维度保证质量
- ✅ 去重合并：覆盖面广
- ✅ 详情筛选：最终保障

---

## 🎨 典型配置

### 激进型投资者
```bash
# API: 收益率（默认）
# 客户端: 收益+稳定性+评分
--sort-methods "return,stability,score" \
--min-recent-profit-rate 20
```

### 平衡型投资者（推荐）
```bash
# API: 收益率（默认）
# 客户端: 评分+夏普+收益+回撤
--sort-methods "score,sharpe,return,drawdown" \
--min-total-win-rate 60
```

### 保守型投资者
```bash
# API: 回撤率
--api-sort 4 \
# 客户端: 夏普+评分+收益
--sort-methods "sharpe,score,return" \
--max-recent-drawdown 10 \
--min-total-win-rate 70
```

---

## 🔧 参数说明

### --api-sort（API排序）
```bash
--api-sort 1  # 最新
--api-sort 2  # 收益率（默认）
--api-sort 3  # 夏普率
--api-sort 4  # 回撤率
```

**不指定**：默认使用 2（收益率）

### --sort-methods（客户端排序）
```bash
--sort-methods "sharpe,return,drawdown"
```

**支持**：
- 基础：sharpe, return, drawdown
- 详情：win_rate, stability
- 评分：score
- 自定义：custom:字段名

### --top-per-group（每种排序取几个）
```bash
--top-per-group 5  # 默认
```

**说明**：
- 每种排序方式取 Top N
- 去重后总数 ≈ 排序数 × N × 0.6
- 例如：3种排序 × 5个 ≈ 9个（去重后）

---

## ⚠️ 注意事项

### 1. API 排序的影响
- **决定性作用**：决定返回数据的大类型
- 收益型策略 vs 稳健型策略 vs 保守型策略
- 选择要与投资风格匹配

### 2. 客户端排序的作用
- **精细筛选**：在 API 返回的数据中优中选优
- 多维度保证质量
- 不能突破 API 返回的数据范围

### 3. 两者关系
```
API 定方向（大类） → 客户端选细节（优质）
```

---

## 📊 选择建议

### 不知道选什么？
```bash
# 使用默认配置
python3 smart_group_recommend.py --query "xxx"
```
- API: 收益率（默认）
- 客户端: sharpe, return, drawdown（默认）

### 明确投资风格？

#### 激进
```bash
--api-sort 2 --sort-methods "return,score,stability"
```

#### 平衡
```bash
--api-sort 2 --sort-methods "score,sharpe,return,drawdown"
```

#### 保守
```bash
--api-sort 4 --sort-methods "sharpe,score,return"
```

---

## 🚀 进阶用法

### 混合策略
```bash
# 第一次：高收益策略
--api-sort 2 --sort-methods "sharpe,return" \
--output result_return.json

# 第二次：低回撤策略
--api-sort 4 --sort-methods "sharpe,return" \
--output result_drawdown.json

# 手动合并两组结果，形成收益+稳健混合组合
```

### 动态调整
```bash
# 牛市：收益优先
--api-sort 2 --sort-methods "return,stability,score"

# 熊市：风险控制
--api-sort 4 --sort-methods "sharpe,score,return"

# 震荡：稳健
--api-sort 3 --sort-methods "return,drawdown,score"
```

---

## 📝 总结

### 核心思想
**两层筛选，先定方向，再选细节**

### 第一层（API）
- 定方向：收益型 / 稳健型 / 保守型
- 默认：收益型（符合大多数需求）
- 可选：根据投资风格自定义

### 第二层（客户端）
- 选细节：多维度筛选优质策略
- 去重合并：覆盖面广
- 详情筛选：最终保障

### 配合使用
- API + 客户端排序 = 最优效果
- 根据场景灵活调整
- 默认配置已经很好

---

**推荐配置**：
```bash
# 大多数场景
--sort-methods "score,sharpe,return,drawdown"

# 保守场景
--api-sort 4 --sort-methods "sharpe,score,return"
```
