# 回测数据查询与组合优化

查询 AI 回测数据，支持多条件筛选，智能分析策略组合，自动推荐最优投资组合。

---

## ⚡ 重要提示

**所有 Python 脚本已内置自动获取 token 功能！**

- ❌ **不要使用** `--token` 参数
- ✅ **直接运行**脚本，token 会自动从 `~/.quantclaw/users.json` 获取

**示例**：
```bash
# 正确 ✅
python3 skills/backtest-query/smart_recommend.py --coins "BTC,ETH" --year 2024

# 错误 ❌ 
python3 skills/backtest-query/smart_recommend.py --token xxx --coins "BTC,ETH"
```

---

## 🚀 快速开始

### 智能分组推荐（推荐使用）

```bash
# 最简单：直接描述需求
python3 skills/backtest-query/smart_group_recommend.py \
  --query "帮我找BTC和ETH的最优策略组合"

# 指定币种和排序方式
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC高收益低风险策略" \
  --coins "BTC" \
  --sort-methods "score,sharpe,return,drawdown" \
  --top-per-group 5

# 详情深度筛选
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC稳健策略组合" \
  --coins "BTC" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15 \
  --output result.json
```

**特性**：
- ✅ 自动推断分组策略
- ✅ 多维度排序筛选（夏普/收益/回撤/评分等）
- ✅ 详情深度分析（胜率/稳定性）
- ✅ 自动生成最优组合

### 基础查询

```bash
# 列出可用币种
python3 skills/backtest-query/query.py --list-coins

# 列出策略类型
python3 skills/backtest-query/query.py --list-strategies

# 查询回测数据
python3 skills/backtest-query/query.py \
  --coin BTC \
  --strategy-type 11 \
  --sort 2
```

---

## 🎯 使用场景

### 何时使用智能分组推荐 (`smart_group_recommend.py`) ⭐推荐

- ✅ 需要智能推荐最优策略组合
- ✅ 跨币种、跨方向、跨策略类型组合
- ✅ "帮我找BTC的最优策略"
- ✅ "BTC和ETH的多空策略组合"
- ✅ "高收益低风险的策略"
- ✅ 需要详情深度分析（胜率、稳定性）

→ **详见**：`examples/smart_group_example.md`、`SORTING_STRATEGY.md`

### 何时使用智能推荐 v1/v2 (`smart_recommend.py`, `smart_recommend_v2.py`)

- ✅ 简单的组合推荐
- ✅ 不需要详情深度分析
- ✅ 快速查询和组合

→ **详见**：`skills/smart_recommend.md`

### 何时使用基础查询 (`query.py`)

- ✅ 查询策略列表
- ✅ 获取可用币种/策略类型
- ✅ 简单查询和浏览
- ✅ "查询BTC做多的策略"
- ✅ "2024年夏普率最高的策略"

→ **详见**：`skills/query_basic.md`、`skills/query_advanced.md`

---

## 🔑 关键概念

### 策略类型

- **马丁策略**：名称含"风霆"
- **网格策略**：strategy_type=7
- **趋势策略**：其他策略（如鲲鹏系列）

详见：`memory/strategy_types.md`

### 工具选择

| 需求 | 推荐使用 | 备选 |
|------|---------|------|
| 智能推荐组合 | `smart_group_recommend.py` ⭐ | `smart_recommend_v2.py` |
| 简单查询列表 | `query.py` | - |
| 创建策略组 | `query.py --create-group` | - |

**推荐优先级**：
1. 智能分组推荐（`smart_group_recommend.py`）- 功能最全
2. 智能推荐 v2（`smart_recommend_v2.py`）- 快速查询
3. 智能推荐 v1（`smart_recommend.py`）- 基础推荐
4. 基础查询（`query.py`）- 简单查询

---

## ⚠️ 注意事项

### 智能分组推荐（smart_group_recommend.py）

1. **最简单用法**：只需 `--query "需求描述"` 即可
2. **自动推断**：自动识别分组维度（币种/方向/策略类型）
3. **多维度排序**：支持 7 种排序方式组合
4. **详情筛选**：支持胜率、稳定性、回撤等深度指标
5. **API 排序**：默认按收益率，可通过 `--api-sort` 自定义

### 基础查询（query.py）

1. **参数必填**：`--coin`、`--sort`、`--strategy-type`
2. **方向参数**：只有部分策略类型支持 `--direction`
3. **时间参数**：`--ai-time-id` 优先级高于 `--year`

---

## 📚 决策流程

```
用户提问
    ↓
需要智能推荐？
    ├─ 是 → smart_group_recommend.py ⭐ （推荐）
    │        - 自动分组
    │        - 多维度筛选
    │        - 详情深度分析
    │
    ├─ 快速查询 → smart_recommend_v2.py
    │        - 简单推荐
    │        - 快速组合
    │
    └─ 简单查询 → query.py
             - 列表查询
             - 基础筛选
```

**推荐使用 smart_group_recommend.py 的场景**：
- ✅ "帮我找最优策略"
- ✅ "推荐一个组合"
- ✅ "高收益低风险的策略"
- ✅ 需要详细分析和筛选

---

## 📖 详细文档

### 核心文档
- `examples/smart_group_example.md` - 智能分组推荐完整示例
- `SORTING_STRATEGY.md` - 两层排序策略说明
- `SORT_METHODS.md` - 7种排序方式详解
- `API_SORT.md` - API排序配置说明

### 参考文档
- `DIMENSIONS.md` - 8个查询维度说明
- `ARCHITECTURE.md` - 系统架构
- `memory/strategy_types.md` - 策略类型详细分类

---

根据用户具体问题，优先使用 `smart_group_recommend.py` 进行智能推荐。
