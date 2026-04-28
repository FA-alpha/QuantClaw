# 回测查询系统架构文档

## 📁 文件结构

```
skills/backtest-query/
├── query.py                    # 基础查询模块（API 封装）
├── defaults.py                 # 默认参数管理
├── smart_recommend.py          # 智能推荐 v1
├── smart_recommend_v2.py       # 智能推荐 v2（接口优化版）
├── smart_group_recommend.py   # 智能分组推荐系统（NEW）
├── analysis/                   # 分析模块
│   ├── __init__.py
│   ├── correlation.py          # 相关性分析
│   ├── risk_analyzer.py        # 风险分析
│   └── portfolio_optimizer.py  # 组合优化
├── examples/                   # 使用示例
│   └── smart_group_example.md
└── test_smart_group.sh        # 测试脚本
```

---

## 🔄 版本演进

### v1: smart_recommend.py
**特点**：
- 手动指定查询参数
- 每个币种循环查询
- 固定 `limit=10`
- 详情获取限制 `max_fetch=20`

**适用场景**：
- 明确知道要查询什么
- 单一维度筛选

### v2: smart_recommend_v2.py
**特点**：
- 接口优化，`limit=-1` 获取全部
- 减少 API 调用次数
- 支持多维度循环查询
- 定义了分组函数但未使用

**适用场景**：
- 需要全量数据
- 减少网络请求

### v3: smart_group_recommend.py（推荐）
**特点**：
- ✅ 智能推断分组策略
- ✅ 自动分组 + Top-N 筛选
- ✅ 详情深度分析
- ✅ 二次筛选优化
- ✅ 稳定性指标

**适用场景**：
- 需要智能推荐
- 深度策略分析
- 组合优化

---

## 🧠 智能分组推荐系统架构

### 核心流程

```
用户需求
   ↓
推断分组策略 (infer_grouping_strategy)
   ↓
查询全量数据 (query_backtest)
   ↓
按维度分组 (classify_strategies)
   ↓
每组多维度排序 Top-N (get_top_by_multiple_sorts)
   ├─ 按夏普率排序 → Top N
   ├─ 按收益率排序 → Top N
   ├─ 按回撤排序 → Top N
   └─ 去重合并
   ↓
批量获取详情 (fetch_detail_data)
   ↓
详情指标分析 (analyze_detail_metrics)
   ↓
二次筛选 (filter_by_detail_criteria)
   ↓
组合优化 (recommend_combinations)
   ↓
返回推荐结果
```

### 关键模块

#### 1. 智能分组推断
```python
def infer_grouping_strategy(self, query_text: str) -> List[str]:
    """
    关键词匹配：
    - '币种' / 'coin' → ['coin']
    - '多空' / 'direction' → ['direction']
    - '策略类型' / 'strategy' → ['strategy_type']
    - '周期' / 'time' → ['ai_time_id']
    """
```

#### 2. 多维度排序 Top-N（NEW）
```python
def get_top_by_multiple_sorts(
    self,
    strategies: List[Dict],
    top_n: int = 5,
    sort_methods: Optional[List[str]] = None
) -> List[Dict]:
    """
    支持排序方式：
    - sharpe: 夏普率（默认）
    - return: 年化收益率
    - drawdown: 最小回撤
    - win_rate: 胜率（需详情）
    - stability: 稳定性（需详情）
    
    每种方式取 Top N，去重后返回
    """
```

#### 3. 详情指标提取
```python
def analyze_detail_metrics(self, strategy: Dict) -> Dict[str, float]:
    """
    提取指标：
    - total_stat: 总体统计（收益率、胜率、回撤、交易次数）
    - recent_stat: 近期统计
    - 稳定性 = 近期收益 / 总体收益
    """
```

#### 4. 详情二次筛选
```python
def filter_by_detail_criteria(self, strategies: List[Dict], criteria: Dict):
    """
    支持条件：
    - min_total_win_rate: 最小总胜率
    - min_recent_profit_rate: 最小近期收益
    - max_recent_drawdown: 最大近期回撤
    - min_trade_count: 最小交易次数
    - min_stability: 最小稳定性
    """
```

---

## 📊 数据流

### 列表数据（query_backtest）
```json
{
  "back_id": 178011,
  "coin": "BTC",
  "name": "网格策略v2",
  "year_rate": 120.5,
  "sharp_rate": 2.5,
  "max_loss": 15.2,
  "direction": "long",
  "strategy_type": 11
}
```

### 详情数据（get_backtest_detail）
```json
{
  "total_stat": {
    "profit_rate": 125.3,
    "win_rate": 65.5,
    "trade_count": 150,
    "max_loss": 15.2
  },
  "recent_stat": {
    "profit_rate": 18.5,
    "win_rate": 68.0,
    "trade_count": 30,
    "max_loss": 8.5
  },
  "coin_fee_list": [...],
  "time_line_list": [...]
}
```

### 分析指标（analyze_detail_metrics）
```json
{
  "year_rate": 120.5,
  "sharp_rate": 2.5,
  "max_loss": 15.2,
  "total_profit_rate": 125.3,
  "total_win_rate": 65.5,
  "total_trade_count": 150,
  "total_max_drawdown": 15.2,
  "recent_profit_rate": 18.5,
  "recent_win_rate": 68.0,
  "recent_trade_count": 30,
  "recent_max_drawdown": 8.5,
  "recent_stability": 0.92
}
```

---

## 🎯 使用场景对比

| 场景 | 推荐版本 | 原因 |
|-----|---------|------|
| 快速查询单个币种 | v1 | 简单直接 |
| 查询全量数据 | v2 | 减少请求 |
| 智能推荐组合 | v3 | 自动分组 + 深度分析 |
| 多维度对比 | v3 | 灵活分组 |
| 保守型投资 | v3 | 详情筛选 |
| 激进型投资 | v3 | 可调参数 |

---

## 🔧 扩展点

### 1. 新增分组维度
在 `infer_grouping_strategy()` 中添加：
```python
if 'xxx' in query_lower:
    dimensions.append('new_dimension')
```

### 2. 新增详情指标
在 `analyze_detail_metrics()` 中计算：
```python
metrics['new_metric'] = calculate_something(detail)
```

### 3. 新增筛选条件
在 `filter_by_detail_criteria()` 中添加：
```python
if 'new_criteria' in criteria:
    if metrics['new_metric'] < criteria['new_criteria']:
        passed = False
```

### 4. 自定义组合优化
修改 `analysis/portfolio_optimizer.py` 中的评分逻辑

---

## ⚠️ 注意事项

### API 调用限制
- 详情获取受 `top_per_group` 限制
- 建议每组不超过 10 个
- 总请求 = 组数 × top_per_group

### 数据质量
- 稳定性指标需要 `total_profit_rate > 0`
- 近期数据可能样本不足
- 建议配合 `min_trade_count` 使用

### 分组推断准确性
- 基于关键词匹配，可能不准确
- 建议在查询中明确说明意图
- 或手动指定参数覆盖推断

---

## 🚀 性能优化

### 已优化
- ✅ v2 版本减少循环查询
- ✅ 详情批量获取带进度显示
- ✅ 缓存机制（币种列表等）

### 待优化
- ⏳ 详情并发获取（线程池）
- ⏳ 分组结果缓存
- ⏳ 增量更新机制

---

## 📚 相关文档

- [使用示例](examples/smart_group_example.md)
- [API 文档](../../docs/api.md)（如有）
- [分析模块说明](analysis/README.md)（如有）

---

**最后更新**: 2025-01-24  
**版本**: v3.0  
**维护者**: QuantClaw Team
