# 回测数据查询与组合优化

查询 AI 回测数据，支持多条件筛选，智能分析策略组合，自动推荐最优投资组合。

## 🎯 核心能力

1. **数据查询** - 多维度筛选回测策略
2. **智能分析** - 相关性分析、回撤错位检测、风险评估
3. **组合优化** - 自动推荐低相关性、风险互补的策略组合
4. **策略组创建** - 一键创建策略组合

## 使用场景

- 查询回测结果
- 按条件筛选策略
- **⭐ 智能推荐组合（一键完成）**
- **⭐ 创建策略组合（核心功能）**
- 获取策略列表用于组合
- 查看 AI 回测时间列表
- 查看 AI 回测策略类型

## ⭐ 智能推荐（推荐使用）

一键完成：查询 → 分析 → 推荐 → 记忆

```bash
python skills/backtest-query/smart_recommend.py \
  --token <用户token> \
  --coins "BTC,ETH,SOL" \
  --year 2024 \
  --workspace <工作区路径> \
  --save-memory
```

### 常用参数

| 参数 | 说明 | 默认值 |
|-----|-----|-------|
| `--token` | 用户 token（必填） | - |
| `--coins` | 币种列表，逗号分隔（必填） | - |
| `--workspace` | 工作区路径（保存记忆用） | - |
| `--year` | 年份（与 --ai-time-id 二选一） | - |
| `--ai-time-id` | 时间ID | - |
| `--group-size` | 组合大小 | 3 |
| `--top-n` | 返回推荐数量 | 5 |
| `--min-sharpe` | 最小夏普率（筛选） | - |
| `--max-drawdown` | 最大回撤（筛选） | - |
| `--max-correlation` | 最大相关性 | 0.5 |
| `--save-memory` | 保存到记忆 | false |
| `--format` | 输出格式 json/text | text |
| `--no-detail` | 快速模式（不获取详情）| false |

### 使用示例

#### 保守型组合
```bash
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC,ETH" \
  --year 2024 \
  --min-sharpe 1.8 \
  --max-drawdown 15 \
  --max-correlation 0.4 \
  --workspace ~/clawd-qc-xxx \
  --save-memory
```

#### 进取型组合
```bash
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC,SOL,BNB" \
  --year 2024 \
  --group-size 3 \
  --top-n 3 \
  --workspace ~/clawd-qc-xxx \
  --save-memory
```

#### 快速查看（不获取详情）
```bash
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC" \
  --year 2024 \
  --no-detail \
  --format json
```

### 输出说明

智能推荐会显示：
- 📋 策略列表（币种、年化、夏普、回撤）
- 📊 组合分析（相关性、组合夏普、回撤重叠）
- 💡 推荐理由
- 🔧 创建命令（一键复制）

并自动保存到 `workspace/memory/portfolio_history.md`

## 查询脚本

```bash
python skills/backtest-query/query.py --token <用户token> [选项]
```

## 参数说明

| 参数 | 说明 | 示例 |
|-----|-----|-----|
| `--token` | 用户 token（必填） | `--token qc_xxx` |
| `--coin` | 币种（必填），多选逗号分割 | `--coin BTC` |
| `--amt-type` | 类型（必填）：1现货 2合约 | `--amt-type 2` |
| `--sort` | 排序（必填）：1最新 2收益率 3夏普 4回撤 | `--sort 2` |
| `--strategy-type` | 策略类型（必填） | `--strategy-type 11` |
| `--year` | 按年份查询（与 --ai-time-id 二选一必传） | `--year 2024` |
| `--ai-time-id` | 按时间ID查询（与 --year 二选一必传） | `--ai-time-id xxx` |
| `--status` | 状态（默认3-成功）：-1删除 2回测中 3成功 4失败 | `--status 3` |
| `--direction` | 方向（策略类型1,7,11必填）：long/short | `--direction long` |
| `--page` | 页码（默认1） | `--page 1` |
| `--limit` | 每页数量（默认10），-1获取全部 | `--limit 20` |
| `--name` | 策略名称 | `--name "BTC网格"` |
| `--start-date` | 开始日期 | `--start-date 2024-01-01` |
| `--end-date` | 结束日期 | `--end-date 2024-12-31` |
| `--pct` | 比例选择 | `--pct 60` |
| `--recommand-type` | 推荐类型：1推荐 2交易中策略 | `--recommand-type 1` |
| `--version` | 策略版本 | `--version 1.0` |
| `--format` | 输出格式：json/table/summary | `--format json` |

## 使用示例

### 查询 AI 推荐的 BTC 做多策略，按收益率排序

```bash
python skills/backtest-query/query.py \
  --token qc_xxx \
  --type 2 \
  --coin BTC \
  --direction long \
  --sort 2 \
  --status 3
```

### 查询合约策略，获取全部结果

```bash
python skills/backtest-query/query.py \
  --token qc_xxx \
  --amt-type 2 \
  --limit -1 \
  --format json
```

### 查询 2024 年夏普率最高的策略

```bash
python skills/backtest-query/query.py \
  --token qc_xxx \
  --year 2024 \
  --sort 3 \
  --limit 10
```

## 返回字段说明

| 字段 | 说明 |
|-----|-----|
| `id` | 回测记录 ID |
| `name` | 策略名称 |
| `bgn_date` | 开始日期 |
| `end_date` | 结束日期 |
| `year_rate` | 年化收益率 |
| `sharp_rate` | 夏普比率 |
| `max_loss` | 最大回撤 |
| `amt_type` | 类型：1现货 2合约 |
| `win_rate` | 胜率 |
| `score` | 策略评分 |
| `trade_num` | 交易次数 |
| `status` | 状态：1排队 2回测中 3成功 4失败 |
| `strategy_token` | 策略 token |
| `strategy_id` | 策略 ID |
| `version` | 策略版本 |

## ⭐ 创建策略组合（核心功能）

**重要性**：将多个优选策略组合成一个策略组，用于分散风险、对冲或构建投资组合。

**API**: `Strategy/group_adds_do`

**命令**：
```bash
python skills/backtest-query/query.py \
  --token <token> \
  --create-group \
  --group-name "策略组名称" \
  --strategy-tokens "token1,token2,token3"
```

**参数说明**：
- `--token` 用户 token（必填）
- `--create-group` 创建策略组标志
- `--group-name` 策略组名称（必填）
- `--strategy-tokens` 策略 token 列表，逗号分隔（必填）

**返回值**：
- 策略组 ID - 保存后可用于其他功能

**完整工作流程**：

### 步骤 1：查询并筛选策略

根据条件查询回测，获取 `strategy_token`：

```bash
# 查询 BTC 做多策略，按收益率排序
python query.py --token xxx \
  --coin BTC \
  --direction long \
  --sort 2 \
  --limit 10 \
  --format json
```

从返回结果中记录优选策略的 `strategy_token`。

### 步骤 2：创建策略组

将选中的策略组合：

```bash
python query.py --token xxx \
  --create-group \
  --group-name "BTC多空对冲组合" \
  --strategy-tokens "st_abc123,st_def456,st_xyz789"
```

**成功响应**：
```
✅ 策略组创建成功: BTC多空对冲组合 (ID: 12345)
```

### 步骤 3：使用策略组

策略组 ID 可用于：
- 统一跟踪多个策略的表现
- 执行组合回测
- 实盘交易时批量操作

**典型应用场景**：
- **对冲组合**：同时持有做多和做空策略
- **币种分散**：多个币种的策略组合
- **策略类型组合**：网格 + 趋势 + DCA 混合
- **风险分级**：高中低风险策略配比

## 查看回测详情

```bash
python skills/backtest-query/query.py --token <token> --detail <回测ID>
```

返回完整的回测统计信息，包括：
- 策略信息（币种、方向、参数等）
- 回测统计（收益率、夏普、回撤、胜率等）
- 净值曲线
- 交易明细
- 保证金配置（如有）

## AI 回测时间列表

```bash
# 列出 AI 回测时间（使用缓存，24小时有效）
python skills/backtest-query/query.py --token <token> --list-ai-times

# 强制刷新时间缓存
python skills/backtest-query/query.py --token <token> --list-ai-times --refresh-cache
```

**返回字段**：
- `id` - 时间 ID（用于 --ai-time-id 参数）
- `name` - 时间名称

**使用场景**：
- 查看可用的回测时间段
- 获取 `ai_time_id` 用于精确查询

**示例输出**：
```
AI 回测时间:
  1 - 2024年第一季度
  2 - 2024年第二季度
  3 - 2024年第三季度
```

缓存文件：`~/.quantclaw/cache/ai_times.json`

## AI 回测策略列表

```bash
# 列出 AI 回测策略类型（使用缓存，24小时有效）
python skills/backtest-query/query.py --token <token> --list-strategies

# 强制刷新策略缓存
python skills/backtest-query/query.py --token <token> --list-strategies --refresh-cache
```

**使用场景**：
- 查看可用的策略类型
- 获取 `strategy_type` 用于查询

缓存文件：`~/.quantclaw/cache/ai_strategies.json`

## 币种管理

```bash
# 列出可用币种（使用缓存，24小时有效）
python skills/backtest-query/query.py --token <token> --list-coins

# 强制刷新币种缓存
python skills/backtest-query/query.py --token <token> --list-coins --refresh-cache
```

缓存文件：`~/.quantclaw/cache/coins.json`

## 📊 智能分析模块（Phase 1 完成）

位于 `analysis/` 目录，提供以下功能：

### 1. 相关性分析 (`correlation.py`)
```python
from analysis import calculate_correlation, build_correlation_matrix

# 计算两策略相关性
corr = calculate_correlation(net_values_a, net_values_b)

# 构建相关性矩阵
matrix, names = build_correlation_matrix(strategies)
```

### 2. 风险分析 (`risk_analyzer.py`)
```python
from analysis import analyze_drawdown_overlap, calculate_portfolio_risk

# 分析回撤重叠
overlap = analyze_drawdown_overlap(strategies, [0, 1, 2])

# 计算组合风险
risk = calculate_portfolio_risk(strategies, [0, 1, 2])
```

### 3. 组合优化 (`portfolio_optimizer.py`)
```python
from analysis import recommend_combinations, filter_by_criteria

# 智能推荐组合
recommendations = recommend_combinations(
    strategies,
    group_size=3,      # 3策略组合
    top_n=5,           # 推荐前5
    preferences={
        'max_correlation': 0.5,
        'max_drawdown': 20.0,
        'min_sharpe': 1.5
    }
)

# 条件筛选
filtered = filter_by_criteria(
    strategies,
    min_sharpe=1.8,
    max_drawdown=15.0,
    coins=['BTC', 'ETH']
)
```

## 🔍 用户需求模糊时的查询策略

**原则**：当用户需求包含模糊描述（"比较好"、"最佳"、"优秀"等）时，**不确定的参数都要尝试**，从多个维度评估。

### 参数探索策略

**常见模糊需求**：
- "比较好的策略" → 什么是"好"？收益？夏普？回撤？
- "最佳组合" → 最佳针对什么目标？
- "表现优秀" → 哪个时间段？哪个指标？

**应对方法**：多维度查询，让数据说话

| 不确定维度 | 探索策略 |
|-----------|---------|
| 时间范围 | 尝试多个年份（2024、2023）或时间ID，验证稳定性 |
| 评价标准 | 尝试多种排序（收益率、夏普率、回撤率），覆盖不同偏好 |
| 策略版本 | 如有多版本，都查询比较 |
| 参数配置 | 如 search_pct，尝试常用值 |

### 查询数量建议

- 单次查询：`--limit 5~10`（避免过多）
- 查询轮数：2~4 轮（时间×排序的组合）
- 总结果数：20~30 条，去重后 10~15 条

### 结果评估方法

**综合打分公式**（参考）：
```
综合分 = 夏普率 × 0.4 + 年化收益 × 0.3 - 最大回撤 × 0.3
```

**分组展示建议**：
- 按年份分组（验证稳定性）
- 按指标突出（高收益 vs 低风险）
- 按风险分级（激进/平衡/保守）

### 灵活示例

```bash
# 场景：用户问"BTC马丁策略比较好的有哪些"
# 策略：先查策略列表找所有马丁策略，然后多维度查询

# 1. 获取马丁策略列表（名称含"风霆"）
python query.py --token xxx --list-strategies

# 2. 对每个马丁策略，尝试多个参数
for each 马丁策略:
  # 2024年按夏普
  query --year 2024 --sort 3
  # 2024年按收益
  query --year 2024 --sort 2
  # 可选：2023年验证
  query --year 2023 --sort 3

# 3. 合并结果，按综合评分排序，分组展示
```

**关键**：根据用户问题灵活调整查询参数，不是固定流程

---

## 🎯 特定策略类型的组合场景

**识别特征**：用户明确指定了策略类型，但要求"组合"

**示例**：
- "BTC做多风霆v4的组合"
- "ETH网格策略的组合"
- "给我几个鲲鹏策略组合起来"

### 参数识别原则

**用户明确的**：直接来自用户描述的参数
**API 才能确定的**：需要查询接口才知道的参数（strategy_type、version 等）
**完全不确定的**：未指定且有多种可能的参数（年份、排序等）

| 示例 | 用户明确的 | API确定的 | 完全不确定的 |
|------|-----------|----------|-------------|
| BTC做多风霆v4的组合 | 币种=BTC<br>方向=做多<br>策略名称=风霆v4 | strategy_type=?<br>version=? | 年份<br>排序方式<br>search_pct |
| ETH网格策略组合 | 币种=ETH<br>策略类型=网格 | strategy_type=7<br>（已知） | 年份<br>排序方式 |

**关键点**：`--list-strategies` 后可能发现该策略有多个版本，此时 version 也需要作为不确定参数尝试！

### 处理流程

```bash
# 1. 查询策略列表
python query.py --token xxx --list-strategies

# 假设返回：
# [11] 风霆V4 (id: 11)
#      - 风霆V4 v4.0 (版本: 4.0, 杠杆: 1)
#      - 风霆V4 v4.1 (版本: 4.1, 杠杆: 3)
#      - 风霆V4 v4.2 (版本: 4.2, 杠杆: 5)

# 发现有 3 个版本！version 也是不确定参数

# 2. 灵活决策
选项 A：每个版本都查（全面）
选项 B：只查最新版本（快速）
选项 C：查最新 + 一个旧版本（平衡）

# 3. 多维度查询（示例选择选项C）
for version in [4.2, 4.0]:  # 最新 + 较早版本
  for year in [2024, 2023]:
    for sort in [2, 3]:  # 收益率、夏普率
      python query.py --token xxx \
        --coin BTC --strategy-type 11 --version {version} \
        --direction long --year {year} --sort {sort} --limit 5

# 4. 合并去重 → 综合评分 → 选出 3-5 个

# 5. 创建组合
python query.py --token xxx \
  --create-group \
  --group-name "BTC做多风霆v4组合" \
  --strategy-tokens "st_xxx,st_yyy,st_zzz"
```

**原则**：先查询接口了解实际情况，再决定哪些参数需要尝试

### 与智能推荐的区别

| 场景 | 使用工具 | 说明 |
|------|---------|------|
| 用户指定了策略类型 | `query.py` 多次查询 + `create-group` | 在该策略类型内选优 |
| 用户未指定策略类型 | `smart_recommend.py` | 跨策略类型智能推荐 |

**判断标准**：用户是否明确提到策略名称（风霆/鲲鹏/星辰/网格/马丁/趋势）

---

**关键**：根据用户问题灵活调整查询参数，不是固定流程

---

## 注意事项

- Token 从用户认证获取
- 查询成功状态的回测使用 `--status 3`
- 获取全部数据用 `--limit -1`
- 币种列表缓存 24 小时，如需更新用 `--refresh-cache`
- **方向参数限制**：只有策略类型 1、7、11 支持 `--direction` 参数，其他策略类型不传方向
- **版本参数**：如果策略类型有版本列表，需要同时传 `--strategy-type` 和 `--version`
- **时间参数**：`--year` 按年份查询，`--ai-time-id` 按具体时间ID查询，二选一使用
- **search_pct 规则**：
  - 当 strategy_type=3 且 recommand_type=2 时不需要传
  - BTC 可选：10, 20, 30, 40, 50, 60, 80, 100, 120
  - 其他币种可选：60, 80, 100, 120, 140
- **特定策略查询**：当用户要求"比较好的"策略时，需要尝试多个参数组合（年份×排序方式）来全面评估

## 依赖安装

```bash
pip install -r requirements.txt
```
