# API 排序说明

## 🔄 API sort_type 参数

接口查询时的 `sort_type` 参数控制 API 返回数据的排序方式：

| sort_type | 说明 | 影响 |
|-----------|------|------|
| 1 | 按最新时间 | 返回最近创建的策略 |
| 2 | 按收益率 | 返回高收益策略 |
| 3 | 按夏普率 | 返回高夏普策略 |
| 4 | 按回撤率 | 返回低回撤策略 |
| None | 不指定 | 接口默认排序 |

---

## ⚠️ 重要变更

### 之前（v1-v3）
```python
fetch_params = {
    'sort_type': 2,  # 硬编码按收益率
}
```

**问题**：
- API 只返回高收益策略
- 限制了数据多样性
- 可能错过低收益但高夏普、低回撤的策略

### 现在（v4）
```python
fetch_params = {
    # 不设置 sort_type
}
```

**改进**：
- ✅ API 返回更多样化的数据
- ✅ 由客户端的多维度排序筛选
- ✅ 避免 API 层面的偏见
- ✅ 可选指定 `--api-sort` 参数

---

## 🎯 使用建议

### 默认方式（推荐）
```bash
python3 smart_group_recommend.py \
  --query "BTC策略" \
  --coins "BTC" \
  --sort-methods "sharpe,return,drawdown"
```

**优势**：
- 不指定 API 排序
- 获取更全面的数据
- 客户端多维度筛选

---

### 指定 API 排序
```bash
python3 smart_group_recommend.py \
  --query "BTC策略" \
  --coins "BTC" \
  --api-sort 2 \
  --sort-methods "sharpe,return"
```

**场景**：
- 明确只要高收益策略
- 减少客户端排序计算
- 数据量过大时预筛选

---

## 📊 对比分析

### 场景：BTC 策略池（假设 1000 个）

#### 1. API排序：收益率（sort_type=2）
```
API 返回：Top 1000 按收益排序
  → [收益180%, 收益175%, ..., 收益5%]
  
客户端筛选：
  - 按夏普排序 → 只能从这 1000 个中选
  - 按回撤排序 → 只能从这 1000 个中选
  
问题：可能错过收益中等但夏普高的策略
```

#### 2. API不排序（sort_type=None）
```
API 返回：1000 个（默认排序或随机）
  → [夏普2.5收益120%, 回撤5%收益80%, 收益180%夏普1.2, ...]
  
客户端筛选：
  - 按夏普排序 → 从全量数据中选
  - 按回撤排序 → 从全量数据中选
  - 按收益排序 → 从全量数据中选
  
优势：数据更全面，筛选更灵活
```

---

## 🔬 实验对比

### 实验1：只按收益率API排序
```bash
--api-sort 2 --sort-methods "sharpe"
```

**结果**：
- API 返回 Top 100 高收益策略
- 客户端按夏普排序
- 可能错过：中等收益但高夏普的策略

### 实验2：不指定API排序
```bash
--sort-methods "sharpe,return"
```

**结果**：
- API 返回多样化数据
- 客户端同时按夏普和收益排序
- 覆盖更全面

---

## ⚙️ 配置建议

### 小数据集（< 100 个策略）
```bash
# 不指定 API 排序
--sort-methods "sharpe,return,drawdown"
```

### 大数据集（> 1000 个策略）
```bash
# 可选指定 API 排序预筛选
--api-sort 2 \
--sort-methods "sharpe,return,drawdown"
```

### 明确需求（只要高收益）
```bash
# API 层面就筛选高收益
--api-sort 2 \
--sort-methods "sharpe"
```

---

## 📝 命令行参数

### --api-sort
```bash
--api-sort 1  # API 按最新排序
--api-sort 2  # API 按收益率排序
--api-sort 3  # API 按夏普率排序
--api-sort 4  # API 按回撤率排序
```

### 不指定（默认，推荐）
```bash
# 不加 --api-sort 参数
# API 返回默认排序的数据
```

---

## 🎯 最佳实践

### 1. 探索阶段
```bash
# 不指定 API 排序，获取多样化数据
--sort-methods "sharpe,return,drawdown,score"
```

### 2. 明确目标
```bash
# 如果只要高收益，API 预筛选
--api-sort 2 --sort-methods "sharpe,stability"
```

### 3. 全面分析
```bash
# 不指定 API 排序，客户端深度筛选
--sort-methods "score,sharpe,return,drawdown,win_rate,stability" \
--min-total-win-rate 60 \
--max-recent-drawdown 15
```

---

## ⚠️ 注意事项

### 1. API 返回数量限制
- 即使 `limit=-1`，API 可能有最大返回数量
- 不指定排序可能获得更随机/全面的数据

### 2. 性能考虑
- 不指定排序：客户端需要更多计算
- 指定排序：API 层面预筛选，减少数据量

### 3. 数据偏差
- 指定排序：可能产生"幸存者偏差"
- 不指定排序：更接近真实分布

---

## 🔄 版本迁移

### 从 v3 迁移到 v4

#### 之前
```python
# 硬编码 sort_type=2
fetch_params = {'sort_type': 2}
```

#### 现在
```python
# 默认不设置
fetch_params = {}

# 或可选指定
if api_sort_type:
    fetch_params['sort_type'] = api_sort_type
```

#### 用户使用
```bash
# 默认行为（推荐）
python3 smart_group_recommend.py --query "xxx"

# 如果需要 API 排序
python3 smart_group_recommend.py --query "xxx" --api-sort 2
```

---

## 📊 实际测试建议

### 测试1：对比数据质量
```bash
# 不指定 API 排序
python3 smart_group_recommend.py \
  --query "BTC策略" --coins "BTC" \
  --sort-methods "sharpe,return,drawdown" \
  --output result_no_api_sort.json

# 指定 API 排序
python3 smart_group_recommend.py \
  --query "BTC策略" --coins "BTC" \
  --api-sort 2 \
  --sort-methods "sharpe,return,drawdown" \
  --output result_api_sort.json

# 对比两个结果的多样性
```

---

**推荐配置**：
```bash
# 默认不指定 API 排序，让多维度排序发挥最大作用
--sort-methods "score,sharpe,return,drawdown"
```

**原因**：
- API 返回更全面的数据
- 客户端多维度排序能覆盖各种需求
- 避免 API 层面的选择偏差
