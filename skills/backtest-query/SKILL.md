# 回测数据查询与组合优化

查询 AI 回测数据，智能推荐最优策略组合。

---

## 🎯 核心工具

### 智能推荐（主要使用）
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述"
```

**用途**：智能推荐策略组合、多维度筛选、详情分析

### 基础查询
```bash
python3 skills/backtest-query/query.py \
  --list-coins          # 列出币种
  --list-strategies     # 列出策略类型
```

**用途**：查询列表、获取可用参数

---

## 📝 使用指南

### 智能推荐参数

#### 必填
- `--query` - 用户需求描述

#### 常用可选
- `--coins` - 币种（如 "BTC,ETH"）
- `--sort-methods` - 排序方式（如 "score,sharpe,return"）
- `--top-per-group` - 每组取几个（默认5）
- `--min-total-win-rate` - 最小胜率
- `--max-recent-drawdown` - 最大回撤
- `--output` - 输出文件

**示例**：
```bash
# 简单推荐
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC最优策略"

# 详细筛选
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC高收益低风险" \
  --coins "BTC" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15
```

---

## 🔑 关键信息

### 策略类型识别
- 马丁策略：名称含"风霆"
- 网格策略：strategy_type=7
- 趋势策略：其他（如鲲鹏）

### 决策逻辑
- 需要推荐组合 → `smart_group_recommend.py`
- 查询列表 → `query.py --list-xxx`

---

---

## 🔧 创建策略组合

**用途**：将多个优选策略组合成一个策略组，用于分散风险、对冲或构建投资组合。

### 命令
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "策略组名称" \
  --strategy-tokens "token1,token2,token3"
```

### 参数说明
- `--create-group` - 创建策略组标志
- `--group-name` - 策略组名称（必填）
- `--strategy-tokens` - 策略 token 列表，逗号分隔（必填）

### 典型应用场景
- **对冲组合**：同时持有做多和做空策略
- **币种分散**：多个币种的策略组合
- **策略类型组合**：网格 + 趋势混合
- **风险分级**：高中低风险策略配比

### 工作流程

#### 1. 查询并筛选策略
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC和ETH的优质策略" \
  --output result.json
```

从结果中记录优选策略的 `strategy_token`。

#### 2. 创建策略组
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC+ETH多空对冲组合" \
  --strategy-tokens "st_abc123,st_def456,st_xyz789"
```

**成功响应**：
```
✅ 策略组创建成功: BTC+ETH多空对冲组合 (ID: 12345)
```

---

## 📚 详细文档

需要深入了解时查阅：
- `examples/smart_group_example.md` - 完整示例
- `SORTING_STRATEGY.md` - 排序策略
- `DIMENSIONS.md` - 参数说明
