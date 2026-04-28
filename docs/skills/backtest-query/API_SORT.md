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

## ⚠️ 配置说明

### 默认行为
```python
# 默认按收益率排序
fetch_params = {
    'sort_type': 2,  # 按收益率
}
```

**理由**：
- ✅ 收益率是最重要的指标
- ✅ 用户通常关注高收益策略
- ✅ 客户端多维度排序可以进一步筛选

### 自定义排序
```python
# 通过参数指定
if api_sort_type is not None:
    fetch_params['sort_type'] = api_sort_type
else:
    fetch_params['sort_type'] = 2  # 默认收益率
```

**灵活性**：
- ✅ 可通过 `--api-sort` 参数自定义
- ✅ 支持按最新、夏普率、回撤率排序
- ✅ 默认值符合大多数场景

---

## 🎯 使用建议

### 默认方式（推荐）
```bash
python3 smart_group_recommend.py \
  --query "BTC策略" \
  --coins "BTC" \
  --sort-methods "sharpe,return,drawdown"
```

**行为**：
- API 按收益率排序（默认）
- 获取高收益策略
- 客户端多维度筛选（夏普、收益、回撤）

---

### 自定义 API 排序
```bash
# 按夏普率排序
python3 smart_group_recommend.py \
  --query "BTC高夏普策略" \
  --coins "BTC" \
  --api-sort 3 \
  --sort-methods "return,drawdown"

# 按回撤率排序
python3 smart_group_recommend.py \
  --query "BTC低风险策略" \
  --coins "BTC" \
  --api-sort 4 \
  --sort-methods "sharpe,return"
```

**场景**：
- 明确需要特定类型策略
- API 预筛选，客户端再精选
- 根据需求灵活调整

---

## 📊 对比分析

### 场景：BTC 策略池（假设 1000 个）

#### 1. 默认：API按收益率排序（sort_type=2）
```
API 返回：Top 1000 按收益排序
  → [收益180%, 收益175%, ..., 收益5%]
  
客户端筛选：
  - 按夏普排序 → 从这 1000 个高收益中选高夏普
  - 按回撤排序 → 从这 1000 个高收益中选低回撤
  
优势：收益优先，再考虑其他指标
```

#### 2. 自定义：API按夏普率排序（sort_type=3）
```
API 返回：Top 1000 按夏普排序
  → [夏普2.8收益80%, 夏普2.5收益120%, ...]
  
客户端筛选：
  - 按收益排序 → 从这 1000 个高夏普中选高收益
  - 按回撤排序 → 从这 1000 个高夏普中选低回撤
  
优势：稳健优先，再考虑收益
```

#### 3. 自定义：API按回撤率排序（sort_type=4）
```
API 返回：Top 1000 按回撤排序
  → [回撤5%收益60%, 回撤7%收益80%, ...]
  
客户端筛选：
  - 按夏普排序 → 从这 1000 个低回撤中选高夏普
  - 按收益排序 → 从这 1000 个低回撤中选高收益
  
优势：风控优先，再考虑收益
```

---

## 🔬 实验对比

### 实验1：默认（API按收益率）
```bash
# 默认 --api-sort=2（可不写）
--sort-methods "sharpe,return,drawdown"
```

**结果**：
- API 返回高收益策略
- 客户端从中选高夏普、低回撤
- 适合：追求收益，兼顾风险

### 实验2：API按夏普率
```bash
--api-sort 3 --sort-methods "return,drawdown"
```

**结果**：
- API 返回高夏普策略
- 客户端从中选高收益、低回撤
- 适合：稳健优先，追求性价比

### 实验3：API按回撤率
```bash
--api-sort 4 --sort-methods "sharpe,return"
```

**结果**：
- API 返回低回撤策略
- 客户端从中选高夏普、高收益
- 适合：保守投资，控制风险

---

## ⚙️ 配置建议

### 追求收益（默认）
```bash
# 默认 API 按收益率
--sort-methods "sharpe,return,drawdown"
```

### 稳健投资
```bash
# API 按夏普率
--api-sort 3 \
--sort-methods "return,drawdown,score"
```

### 风险控制
```bash
# API 按回撤率
--api-sort 4 \
--sort-methods "sharpe,return,score"
```

### 最新策略
```bash
# API 按最新
--api-sort 1 \
--sort-methods "score,sharpe,return"
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

### 1. 收益优先（默认推荐）
```bash
# API 按收益率（默认）
--sort-methods "sharpe,return,drawdown,score"
```

### 2. 风险优先
```bash
# API 按回撤率
--api-sort 4 \
--sort-methods "sharpe,return,score"
```

### 3. 全面分析
```bash
# API 按收益率（默认）+ 客户端深度筛选
--sort-methods "score,sharpe,return,drawdown,win_rate,stability" \
--min-total-win-rate 60 \
--max-recent-drawdown 15
```

---

## ⚠️ 注意事项

### 1. 默认收益率排序
- 符合大多数用户需求（追求收益）
- 客户端多维度排序可以进一步筛选
- 如需其他优先级，使用 `--api-sort`

### 2. API 排序的影响
- API 排序决定返回数据的初始偏向
- 客户端排序从 API 返回的数据中精选
- 两者配合，先粗筛再精选

### 3. 灵活配置
- 默认值适合大多数场景
- 特殊需求可自定义
- 建议根据投资风格选择

---

## 🔄 版本迁移

### v4 配置方式

#### 代码实现
```python
# 默认按收益率
if api_sort_type is not None:
    fetch_params['sort_type'] = api_sort_type
else:
    fetch_params['sort_type'] = 2  # 默认收益率
```

#### 用户使用
```bash
# 默认按收益率（推荐）
python3 smart_group_recommend.py --query "BTC策略"

# 按夏普率
python3 smart_group_recommend.py --query "BTC策略" --api-sort 3

# 按回撤率
python3 smart_group_recommend.py --query "BTC策略" --api-sort 4
```

#### 向后兼容
- ✅ 默认行为与 v1-v3 一致（按收益率）
- ✅ 新增参数灵活自定义
- ✅ 无需修改现有使用方式

---

## 📊 实际测试建议

### 测试：不同 API 排序对比
```bash
# 按收益率（默认）
python3 smart_group_recommend.py \
  --query "BTC策略" --coins "BTC" \
  --sort-methods "sharpe,return,drawdown" \
  --output result_return.json

# 按夏普率
python3 smart_group_recommend.py \
  --query "BTC策略" --coins "BTC" \
  --api-sort 3 \
  --sort-methods "return,drawdown,score" \
  --output result_sharpe.json

# 按回撤率
python3 smart_group_recommend.py \
  --query "BTC策略" --coins "BTC" \
  --api-sort 4 \
  --sort-methods "sharpe,return,score" \
  --output result_drawdown.json

# 对比三个结果的策略类型分布
```

---

**推荐配置**：

### 收益优先（默认）
```bash
# 默认 API 按收益率
--sort-methods "score,sharpe,return,drawdown"
```

### 稳健优先
```bash
--api-sort 3 \
--sort-methods "return,drawdown,score"
```

### 风险控制
```bash
--api-sort 4 \
--sort-methods "sharpe,return,score"
```

**原则**：
- API 排序做粗筛（决定数据类型）
- 客户端排序做精选（多维度筛选）
- 根据投资风格选择 API 排序
