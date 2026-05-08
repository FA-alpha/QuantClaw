# 多维度排序 Top-N 演示

## 💡 为什么需要多维度排序？

### 问题
单一排序方式有局限性：

#### ❌ 只按夏普率
```
Top 5: 都是高夏普策略
问题: 可能忽略高收益但夏普率略低的策略
```

#### ❌ 只按收益率
```
Top 5: 都是高收益策略
问题: 可能风险过高（回撤大）
```

#### ❌ 只按回撤
```
Top 5: 都是低回撤策略
问题: 收益可能不够理想
```

### 解决方案：多维度 Top-N

✅ **每种排序方式取 Top-N，去重合并**

```
按夏普率 Top 3: [A, B, C]
按收益率 Top 3: [B, D, E]
按回撤   Top 3: [C, F, G]
                 ↓ 去重合并
结果: [A, B, C, D, E, F, G]  ← 7个优质策略
```

**优势**：
- ✅ 兼顾收益、风险、稳定性
- ✅ 避免单一视角局限
- ✅ 筛选更全面

---

## 📊 支持的排序方式

| 排序方式 | 说明 | 适用场景 | 是否需要详情 |
|---------|------|---------|-------------|
| `sharpe` | 夏普率（收益/风险比） | 综合评估 | ❌ |
| `return` | 年化收益率 | 追求高收益 | ❌ |
| `drawdown` | 最小回撤 | 保守型/风险控制 | ❌ |
| `win_rate` | 总胜率 | 稳定盈利 | ✅ |
| `stability` | 稳定性（近期/总体） | 趋势判断 | ✅ |
| `score` | 综合评分 | 平台推荐/全面评估 | ❌ |
| `custom:字段名` | 自定义字段 | 灵活扩展 | ⚠️ 视字段而定 |

**综合评分说明**：
- 自动检测多种字段名：`score`, `total_score`, `recommend_score`, `rating`
- 如果数据中存在这些字段，可以用 `score` 排序
- 通常由平台计算的综合指标（收益+风险+稳定性）

---

## 🎯 使用示例

### 示例 1：默认多排序（推荐）

```bash
python3 smart_group_recommend.py \
  --query "帮我找BTC的最优策略" \
  --coins "BTC" \
  --top-per-group 3
```

**默认行为**：
- 自动使用 3 种排序：`sharpe`, `return`, `drawdown`
- 每种取 Top 3
- 去重后约 5-9 个策略

**输出示例**：
```
--- BTC (128 个策略) ---
   🔹 按 sharpe 排序取 Top 3
      ✅ BTC / 网格v2 (sharpe)
      ✅ BTC / 趋势跟踪 (sharpe)
      ✅ BTC / 均线突破 (sharpe)
   🔹 按 return 排序取 Top 3
      ✅ BTC / 激进网格 (return)
      ✅ BTC / 趋势跟踪 (return)  ← 重复，跳过
      ✅ BTC / 高频交易 (return)
   🔹 按 drawdown 排序取 Top 3
      ✅ BTC / 保守网格 (drawdown)
      ✅ BTC / 防守型 (drawdown)
      ✅ BTC / 网格v2 (drawdown)  ← 重复，跳过
📊 去重后选择 7 个策略
```

---

### 示例 2：自定义排序组合

```bash
python3 smart_group_recommend.py \
  --query "收益优先但控制回撤" \
  --coins "BTC,ETH" \
  --top-per-group 5 \
  --sort-methods "return,drawdown" \
  --max-recent-drawdown 15
```

**策略**：
- 收益排序 Top 5：激进策略
- 回撤排序 Top 5：稳健策略
- 去重后约 8-10 个
- 再用详情筛选：近期回撤 ≤15%

**适用场景**：平衡收益与风险

---

### 示例 3：平台推荐+综合评分

```bash
python3 smart_group_recommend.py \
  --query "平台推荐的优质策略" \
  --coins "BTC,ETH" \
  --top-per-group 5 \
  --sort-methods "score,sharpe,return" \
  --min-total-win-rate 60
```

**说明**：
- 优先按综合评分排序（平台算法）
- 兼顾夏普率和收益率
- 去重后约 10-15 个策略

**适用场景**：信任平台算法，快速筛选

---

### 示例 4：全方位筛选（需详情数据）

```bash
python3 smart_group_recommend.py \
  --query "全方位评估" \
  --coins "BTC" \
  --top-per-group 4 \
  --sort-methods "score,sharpe,return,drawdown,win_rate,stability" \
  --min-total-win-rate 60 \
  --min-stability 0.8
```

**说明**：
- 6 种排序方式各取 Top 4
- 去重后约 15-24 个策略
- ⚠️ `win_rate` 和 `stability` 需要详情数据
- 会先获取详情再排序（稍慢）

**适用场景**：深度分析、高要求筛选

---

### 示例 5：保守型组合

```bash
python3 smart_group_recommend.py \
  --query "稳健策略" \
  --coins "BTC,ETH,SOL" \
  --top-per-group 3 \
  --sort-methods "drawdown,sharpe,score" \
  --max-recent-drawdown 10 \
  --min-total-win-rate 70
```

**策略**：
- 优先低回撤
- 兼顾夏普率和综合评分
- 严格详情筛选

**适用场景**：保守投资者、熊市

---

### 示例 6：激进型组合

```bash
python3 smart_group_recommend.py \
  --query "高收益策略" \
  --coins "BTC,ETH" \
  --top-per-group 5 \
  --sort-methods "return,stability,score" \
  --min-recent-profit-rate 20 \
  --min-stability 0.9
```

**策略**：
- 优先高收益
- 必须稳定（近期表现好）
- 参考综合评分
- 近期收益 ≥20%

**适用场景**：激进投资者、牛市

---

### 示例 7：自定义字段排序

```bash
python3 smart_group_recommend.py \
  --query "自定义排序" \
  --coins "BTC" \
  --top-per-group 5 \
  --sort-methods "custom:my_score,sharpe,return"
```

**说明**：
- 按自定义字段 `my_score` 排序
- 如果数据中有该字段，会自动提取
- 适用于有特殊评分字段的场景

---

## 🔬 工作原理

### 去重逻辑
```python
selected = {}  # 用 back_id 去重

for method in sort_methods:
    sorted_list = sort_by(strategies, method)
    for strategy in sorted_list[:top_n]:
        back_id = strategy.get('back_id')
        if back_id not in selected:
            selected[back_id] = strategy  # 首次出现才添加
            
return list(selected.values())
```

### 时间复杂度
- 单次排序：O(n log n)
- k 种排序：O(k × n log n)
- 总体：O(k × n log n + k × top_n)

**实际性能**：
- 100 个策略，3 种排序 → 瞬间完成
- 1000 个策略，5 种排序 → <1 秒

---

## 📈 效果对比

### 场景：BTC 策略池（100 个）

#### 单一排序（按夏普率）
```
Top 5:
1. 网格v2    (夏普2.5, 收益120%, 回撤15%)
2. 趋势跟踪  (夏普2.3, 收益110%, 回撤12%)
3. 均线突破  (夏普2.2, 收益105%, 回撤14%)
4. 防守型    (夏普2.1, 收益 80%, 回撤 8%)
5. 稳健网格  (夏普2.0, 收益 85%, 回撤 9%)

问题: 缺少高收益策略（>150%）
```

#### 多维度排序（夏普+收益+回撤）
```
Top 7 (去重后):
1. 网格v2    (夏普2.5, 收益120%, 回撤15%) ← sharpe
2. 趋势跟踪  (夏普2.3, 收益110%, 回撤12%) ← sharpe
3. 激进网格  (夏普1.8, 收益180%, 回撤25%) ← return ✨
4. 高频交易  (夏普1.9, 收益160%, 回撤22%) ← return ✨
5. 防守型    (夏普2.1, 收益 80%, 回撤 8%) ← drawdown
6. 保守网格  (夏普1.7, 收益 75%, 回撤 7%) ← drawdown ✨
7. 稳健网格  (夏普2.0, 收益 85%, 回撤 9%) ← drawdown

优势: 高收益、稳健型策略都有，可组合优化
```

---

## ⚙️ 配置建议

### 快速筛选（默认）
```bash
--sort-methods "sharpe,return,drawdown"
--top-per-group 3
```
- 3 种排序，去重后 5-9 个
- 速度快，覆盖面广

### 平台推荐优先
```bash
--sort-methods "score,sharpe,return"
--top-per-group 5
```
- 综合评分 + 夏普率 + 收益率
- 去重后约 10-15 个
- 信任平台算法

### 精细筛选
```bash
--sort-methods "score,sharpe,return,drawdown,win_rate"
--top-per-group 5
```
- 5 种排序，去重后 15-25 个
- 需要详情数据，稍慢

### 极致筛选
```bash
--sort-methods "score,sharpe,return,drawdown,win_rate,stability"
--top-per-group 5
```
- 6 种排序，去重后 20-30 个
- 全方位评估，推荐用于重点分析

---

## 🎓 最佳实践

### 1. 根据市场环境选择
- **牛市**：`score, return, stability`（追收益+评分）
- **熊市**：`drawdown, sharpe, score`（控风险+评分）
- **震荡**：`score, sharpe, win_rate`（稳定盈利+评分）

### 2. 根据投资风格
- **保守型**：`drawdown, score, sharpe, win_rate`
- **平衡型**：`score, sharpe, return, drawdown`（推荐）
- **激进型**：`return, score, stability`

### 3. 配合详情筛选
```bash
--sort-methods "score,sharpe,return,drawdown" \
--min-total-win-rate 60 \
--max-recent-drawdown 15
```
多排序扩大候选池，详情筛选确保质量

### 4. 信任平台算法
```bash
--sort-methods "score" \
--top-per-group 10
```
只用综合评分，取更多候选

---

## ⚠️ 注意事项

### win_rate 和 stability 排序
这两种需要详情数据，会先批量获取详情再排序：
```
流程: 
1. 查询策略列表（无详情）
2. 批量获取全部详情（慢）
3. 按 win_rate/stability 排序
4. 取 Top-N
```

**建议**：
- 小数据集（<30个）：可以用
- 大数据集（>100个）：避免使用，或先用其他方式筛选

### 去重可能导致数量不足
如果多种排序结果高度重叠：
```
sharpe Top 3: [A, B, C]
return Top 3: [A, B, C]  ← 完全重复
                ↓
去重后只有 3 个，而非预期的 6 个
```

**解决**：增加 `top_per_group` 值

---

## 🚀 未来优化

- [ ] 并行排序（多线程）
- [ ] 智能权重（不同排序的重要性）
- [ ] 缓存排序结果
- [ ] 排序方式自动推荐

---

**推荐配置**：
```bash
# 有综合评分时
--sort-methods "score,sharpe,return,drawdown"
--top-per-group 5

# 无综合评分时
--sort-methods "sharpe,return,drawdown"
--top-per-group 5
```

平衡速度和质量，适合大多数场景！

---

## 💡 综合评分说明

### 什么是综合评分？

综合评分通常是平台根据多个指标计算出的单一分数，综合考虑：
- 收益率（年化收益）
- 风险控制（回撤、波动）
- 稳定性（胜率、交易频率）
- 夏普率（收益/风险比）

### 优势
- ✅ 一个数字总结多个维度
- ✅ 平台算法优化（可能考虑了更多因素）
- ✅ 方便快速排序

### 何时使用
- 信任平台算法
- 快速筛选
- 作为多排序的一种维度

### 字段名兼容
系统自动检测以下字段：
```python
score
total_score
recommend_score
rating
```

如果数据中使用其他字段名，可以用：
```bash
--sort-methods "custom:your_field_name"
```
