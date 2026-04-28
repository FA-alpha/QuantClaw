# 排序方式快速参考

## 📊 所有支持的排序方式

| 排序方式 | 说明 | 数据来源 | 排序方向 | 推荐场景 |
|---------|------|---------|---------|---------|
| `sharpe` | 夏普率 | 列表数据 | ⬆️ 降序 | 综合评估，收益/风险平衡 |
| `return` | 年化收益率 | 列表数据 | ⬆️ 降序 | 追求高收益 |
| `drawdown` | 最大回撤 | 列表数据 | ⬇️ 升序 | 风险控制，保守投资 |
| `win_rate` | 总胜率 | 详情数据 | ⬆️ 降序 | 稳定盈利，交易频繁策略 |
| `stability` | 稳定性 | 详情数据 | ⬆️ 降序 | 近期表现好，趋势向上 |
| `score` | 综合评分 | 列表数据 | ⬆️ 降序 | 信任平台算法，快速筛选 |
| `custom:字段名` | 自定义字段 | 取决于字段 | ⬆️ 降序 | 特殊需求，灵活扩展 |

---

## 🎯 使用建议

### 默认组合（推荐）
```bash
--sort-methods "sharpe,return,drawdown"
```
**适用**: 大多数场景，平衡收益和风险

### 有综合评分时
```bash
--sort-methods "score,sharpe,return,drawdown"
```
**适用**: 信任平台算法，全面筛选

### 保守型
```bash
--sort-methods "drawdown,sharpe,score"
```
**适用**: 熊市、风险厌恶型投资者

### 激进型
```bash
--sort-methods "return,score,stability"
```
**适用**: 牛市、追求高收益

### 深度分析（需详情）
```bash
--sort-methods "score,sharpe,return,drawdown,win_rate,stability"
```
**适用**: 重点策略深度评估

---

## 💡 排序方式详解

### sharpe - 夏普率
```python
夏普率 = (年化收益率 - 无风险利率) / 年化波动率
```
- **值越大越好**
- 综合考虑收益和风险
- 夏普率 > 2 通常认为优秀
- **推荐**: 作为主要排序依据

### return - 年化收益率
```python
年化收益率 = (期末净值 - 期初净值) / 期初净值 × 100%
```
- **值越大越好**
- 只看收益，不考虑风险
- 需配合回撤等指标
- **适用**: 追求高收益

### drawdown - 最大回撤
```python
最大回撤 = (峰值 - 谷值) / 峰值 × 100%
```
- **值越小越好**（升序排序）
- 最大损失幅度
- 回撤 < 15% 通常认为优秀
- **适用**: 风险控制优先

### win_rate - 总胜率
```python
总胜率 = 盈利交易次数 / 总交易次数 × 100%
```
- **需要详情数据**
- 值越大越好
- 胜率 > 60% 通常认为优秀
- **适用**: 稳定盈利策略

### stability - 稳定性
```python
稳定性 = 近期收益率 / 总体收益率
```
- **需要详情数据**
- 接近 1 表示稳定
- \> 1 表示近期表现更好（上升趋势）
- < 1 表示近期表现下滑
- **适用**: 判断趋势

### score - 综合评分
```python
# 平台算法计算，通常考虑:
综合评分 = f(收益率, 夏普率, 回撤, 胜率, 稳定性, ...)
```
- **值越大越好**
- 单一数字总结多维度
- 平台优化算法
- **适用**: 快速筛选

### custom:字段名 - 自定义字段
```bash
--sort-methods "custom:my_field"
```
- 灵活扩展任意字段
- 自动从数据中提取
- 降序排序
- **适用**: 特殊评分字段

---

## 📈 组合示例

### 场景1: 快速筛选（3种）
```bash
sharpe,return,drawdown
```
- 取 3×3 = 9 个候选
- 去重后约 5-9 个
- 速度快

### 场景2: 平衡筛选（4种）
```bash
score,sharpe,return,drawdown
```
- 取 4×5 = 20 个候选
- 去重后约 12-18 个
- 推荐使用

### 场景3: 深度筛选（6种）
```bash
score,sharpe,return,drawdown,win_rate,stability
```
- 取 6×5 = 30 个候选
- 去重后约 18-28 个
- 需要详情数据（慢）

---

## ⚠️ 注意事项

### 1. 详情数据排序
`win_rate` 和 `stability` 需要先获取详情：
- 小数据集（<30个）：可以用
- 大数据集（>100个）：避免或先用其他方式筛选

### 2. 综合评分字段
`score` 排序自动检测以下字段：
```python
score, total_score, recommend_score, rating
```
如果都不存在，该排序无效

### 3. 自定义字段
使用前确认字段存在：
```bash
# 查看数据结构
python3 query.py --token xxx --limit 1 --format json
```

### 4. 去重数量
如果多种排序结果重叠度高：
- 去重后数量 < 预期
- 增加 `--top-per-group` 值

---

## 🎨 场景速查

| 需求 | 推荐组合 |
|-----|---------|
| 快速筛选 | `sharpe,return,drawdown` |
| 平衡收益风险 | `score,sharpe,return,drawdown` |
| 追求高收益 | `return,score,stability` |
| 控制风险 | `drawdown,sharpe,score` |
| 稳定盈利 | `score,sharpe,win_rate` |
| 深度分析 | `score,sharpe,return,drawdown,win_rate,stability` |

---

## 🔧 调试技巧

### 查看排序过程
运行时会输出每种排序的结果：
```
--- BTC (128 个策略) ---
   🔹 按 sharpe 排序取 Top 3
      ✅ BTC / 策略A (sharpe)
      ✅ BTC / 策略B (sharpe)
   🔹 按 return 排序取 Top 3
      ✅ BTC / 策略C (return)
   🔹 按 score 排序取 Top 3
      ✅ BTC / 策略D (score)
📊 去重后选择 4 个策略
```

### 验证字段存在
```bash
python3 query.py --token xxx --coin BTC --limit 1 --format json | jq '.info[0] | keys'
```

---

**推荐阅读**:
- [多维度排序详细演示](examples/multi_sort_demo.md)
- [架构文档](ARCHITECTURE.md)
- [使用示例](examples/smart_group_example.md)
