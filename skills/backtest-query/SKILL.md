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

#### 输出格式
- **JSON 输出**：使用 `--output` 保存完整数据（供 Agent 读取）
- **文本输出**：包含创建命令示例（供调试/手动使用）

**Agent 使用方式**：
从 JSON 的 `combinations[0]['strategies'][*]['strategy_token']` 提取 token 列表，直接构建创建命令。

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

### Agent 决策逻辑
- **用户包含"创建"关键词** → 推荐后直接创建（无需确认）
- **用户仅查询** → 推荐后询问是否创建
- 需要推荐组合 → `smart_group_recommend.py`
- 查询列表 → `query.py --list-xxx`

### 创建意图关键词
`创建`、`建立`、`建个`、`生成`、`并创建`、`然后创建`

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

#### 方式1：智能推荐 + 自动生成命令（推荐）

```bash
# 1. 智能推荐
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC和ETH的优质策略"
```

**输出示例**：
```
--- 组合 #1 ---
评分: 85.5
预期收益: 120.5%
...

🔧 创建命令:
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "智能组合_1_20260428" \
  --strategy-tokens "st_abc123,st_def456,st_xyz789"
```

```bash
# 2. 复制并执行创建命令
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "智能组合_1_20260428" \
  --strategy-tokens "st_abc123,st_def456,st_xyz789"
```

**成功响应**：
```
✅ 策略组创建成功: 智能组合_1_20260428 (ID: 12345)
```

#### 方式2：手动创建

如果已知 `strategy_token`，可以直接创建：

```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "自定义组合名称" \
  --strategy-tokens "token1,token2,token3"
```

---

## 📚 详细文档

需要深入了解时查阅：
- `examples/smart_group_example.md` - 完整示例
- `SORTING_STRATEGY.md` - 排序策略
- `DIMENSIONS.md` - 参数说明
