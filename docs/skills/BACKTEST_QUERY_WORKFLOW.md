# Agent 工作流指南

## 🤖 作为 Agent 如何使用此技能

### 场景识别

当用户询问以下问题时，使用此技能：

#### 1. 策略查询
- "有哪些BTC策略？"
- "查询ETH的回测结果"
- "2024年收益最高的策略"

**→ 使用**: `query.py`

#### 2. 策略推荐（推荐）
- "帮我找个BTC和ETH的组合"
- "推荐一些低风险的策略"
- "我想做多空对冲"

**→ 使用**: `smart_recommend.py` ⭐

#### 3. 策略详情
- "这个策略的回测详情"
- "查看策略12345的净值曲线"

**→ 使用**: `query.py --detail`

---

## 📋 完整工作流

### 工作流 1: 智能推荐（一键完成）

```python
# 用户: "帮我推荐BTC和ETH的策略组合，要保守一点"

# Step 1: 识别意图
- 币种: BTC, ETH
- 风险偏好: 保守（转换为参数: --max-drawdown 15, --min-sharpe 1.8）

# Step 2: 调用智能推荐
exec:
  python /home/ubuntu/work/QuantClaw/skills/backtest-query/smart_recommend.py \
    --token {user_token} \
    --coins "BTC,ETH" \
    --year 2024 \
    --min-sharpe 1.8 \
    --max-drawdown 15 \
    --workspace {user_workspace} \
    --save-memory

# Step 3: 解读结果
- 提取推荐的前3个组合
- 用人类语言解释相关性、风险等指标
- 询问用户是否创建

# Step 4: 创建策略组（如果用户同意）
exec:
  python /home/ubuntu/work/QuantClaw/skills/backtest-query/query.py \
    --token {user_token} \
    --create-group \
    --group-name "BTC+ETH保守组合" \
    --strategy-tokens "st_xxx,st_yyy"
```

### 工作流 2: 分步查询

```python
# 用户: "查询一下BTC做多的策略"

# Step 1: 查询列表
exec:
  python query.py \
    --token {user_token} \
    --coin BTC \
    --direction long \
    --sort 2 \
    --year 2024

# Step 2: 展示结果
- 用表格或列表展示
- 突出显示年化、夏普、回撤

# Step 3: 等待用户进一步操作
- "查看详情" → query.py --detail
- "推荐组合" → smart_recommend.py
```

### 工作流 3: 特定策略类型的最佳策略（多参数尝试）

```python
# 用户: "提供下BTC做多 风霆v4策略的比较好的策略有哪些"

# Step 1: 识别关键信息
- 币种: BTC
- 方向: 做多 (long)
- 策略类型: 风霆v4 → 查找对应的 strategy_type
- 目标: 找"比较好的" → 需要多参数尝试

# Step 2: 获取策略类型列表
exec:
  python query.py --token {user_token} --list-strategies

# Step 3: 找到风霆v4的 strategy_type ID
# 从返回结果中找 "风霆" 相关策略，确认 strategy_type 和 version

# Step 4: 尝试多个参数组合（不确定的参数都要试）
params_to_try = [
  # 不同年份
  {"year": 2024},
  {"year": 2023},
  {"ai_time_id": "latest"},  # 如果有最新时间ID
  
  # 不同排序
  {"sort": 2},  # 收益率
  {"sort": 3},  # 夏普率
  {"sort": 4},  # 回撤率
  
  # 不同筛选条件
  {"status": 3},  # 成功的回测
  {"recommand_type": 1},  # 推荐策略
]

# Step 5: 组合查询（笛卡尔积或优先级）
results = []

# 优先级查询方式（推荐）
for year in [2024, 2023]:
  for sort_type in [2, 3]:  # 先按收益率，再按夏普
    exec:
      python query.py \
        --token {user_token} \
        --coin BTC \
        --strategy-type {风霆v4_id} \
        --version {风霆v4_version} \
        --direction long \
        --year {year} \
        --sort {sort_type} \
        --status 3 \
        --limit 10
    
    # 收集结果
    results.append(...)

# Step 6: 去重和排序
# 根据 strategy_token 去重
# 按综合指标排序（夏普率 + 收益率 - 回撤）

# Step 7: 展示结果
"为您找到 BTC 做多风霆v4 策略的优选结果：

【2024年数据】
1. 策略名称 | 年化收益 XX% | 夏普率 X.X | 最大回撤 X%
2. ...

【2023年数据】
1. ...

综合推荐：基于风险调整后收益（夏普率），推荐前3个策略：
- [策略A]: 高收益高夏普，适合激进型
- [策略B]: 收益稳定回撤小，适合稳健型
- [策略C]: 收益与风险平衡

💡 是否需要查看这些策略的详细回测数据？或者创建组合？"
```

**关键点**：
1. **识别不确定参数**：年份、排序方式、时间ID
2. **多次查询**：尝试不同参数组合
3. **结果合并**：去重、排序、分组展示
4. **人性化展示**：按年份/指标分类，给出推荐理由

---

## 🔍 不确定参数的处理策略

当用户需求中有**不明确的参数**时，需要**尝试多个值**来找到最佳结果。

### 常见不确定参数

| 参数 | 不确定时的尝试策略 |
|-----|------------------|
| 时间范围 | 尝试：2024, 2023, 最新时间ID |
| 排序方式 | 尝试：收益率(2), 夏普率(3), 回撤率(4) |
| 推荐类型 | 尝试：推荐策略(1), 交易中策略(2) |
| search_pct | 尝试：BTC [60,80,100], 其他币种 [80,100,120] |
| 版本 | 查询策略列表获取所有可用版本，逐个尝试 |

### 查询优先级策略

```python
# 优先级 1: 最新数据 + 风险调整收益
year=2024, sort=3 (夏普率)

# 优先级 2: 最新数据 + 绝对收益
year=2024, sort=2 (收益率)

# 优先级 3: 历史数据验证
year=2023, sort=3

# 优先级 4: 低风险筛选
year=2024, sort=4 (回撤率)
```

### 结果合并策略

1. **去重**：根据 `strategy_token` 去重
2. **分组**：按年份、指标分组展示
3. **排序**：综合评分 = `sharpe_rate * 0.4 + year_rate * 0.3 - max_loss * 0.3`
4. **筛选**：只保留状态=3（成功）的回测

### 示例：完整流程

```bash
# 用户: "BTC做多马丁策略比较好的有哪些"

# Step 1: 识别策略类型
- 马丁策略 → 名称含"风霆"

# Step 2: 获取所有马丁策略ID
python query.py --token xxx --list-strategies | grep 风霆
# 假设找到: 1(风霆现货), 2(风霆合约), 11(风霆V4)

# Step 3: 对每个策略ID，多参数查询
for strategy_type in [1, 2, 11]:
  for year in [2024, 2023]:
    for sort in [2, 3]:
      python query.py \
        --token xxx \
        --coin BTC \
        --strategy-type {strategy_type} \
        --year {year} \
        --sort {sort} \
        --direction long \
        --status 3 \
        --limit 5

# Step 4: 合并结果并展示
# 去重、排序、分组展示
```

---

## 🎯 参数转换规则

### 风险偏好 → 参数

| 用户描述 | 参数配置 |
|---------|---------|
| 保守/稳健 | `--max-drawdown 12 --min-sharpe 2.0 --max-correlation 0.4` |
| 平衡 | `--max-drawdown 15 --min-sharpe 1.5 --max-correlation 0.5` |
| 进取/激进 | `--max-drawdown 20 --min-sharpe 1.2 --max-correlation 0.6` |

### 投资策略 → 方向

| 用户描述 | 参数 |
|---------|-----|
| 做多/看涨 | `--direction long` |
| 做空/看跌 | `--direction short` |
| 对冲 | 分别查询 long + short，然后组合 |

### 组合目标 → group-size

| 用户描述 | 参数 |
|---------|-----|
| 分散风险 | `--group-size 4` (4个以上) |
| 对冲组合 | `--group-size 2` (多空各一) |
| 标准组合 | `--group-size 3` |

---

## 💡 交互建议

### 主动询问

当用户需求不明确时：

```
用户: "推荐个策略"
Agent: "好的！请告诉我：
  1. 想投资哪些币种？(如BTC、ETH、SOL)
  2. 风险偏好？(保守/平衡/进取)
  3. 做多还是做空？(或对冲)
  4. 组合几个策略？(建议3个)"
```

### 结果解读

不要直接抛数据，用人话说：

❌ 差：
```
相关性: 0.28
组合夏普: 2.1
回撤重叠: 15%
```

✅ 好：
```
这个组合的策略互相独立性很好（相关性仅0.28），
风险调整后的收益不错（夏普率2.1），
而且回撤时间错开，当一个策略亏损时，
另一个往往在盈利，起到很好的对冲效果。
```

### 风险警示

**必须**在推荐后说明：

```
⚠️ 重要提示：
- 回测结果基于历史数据，不代表未来表现
- 实盘交易需谨慎，建议小仓位测试
- 市场环境变化可能导致策略失效
- 务必设置止损，控制风险
```

---

## 📝 记忆管理

### 自动记录

使用 `--save-memory` 参数后，自动记录到：
```
{workspace}/memory/portfolio_history.md
```

### 记录内容

- 查询时间
- 查询条件（币种、参数）
- 推荐的组合
- 组合分析指标
- 用户反馈（如果有）

### 调用记忆

下次用户询问时，Agent 会自动：
```python
memory_search("策略组合 BTC ETH")
# 找到历史推荐
memory_get("memory/portfolio_history.md", from=X, lines=Y)
```

可以说：
```
"我看到您上次选择了保守型组合，
这次要继续保守策略还是尝试激进一点？"
```

---

## 🔧 调试技巧

### 检查 token

```bash
# 验证 token 是否有效
curl -X POST http://localhost:18789/webhook/quantclaw \
  -H "Content-Type: application/json" \
  -d '{"token":"qc_xxx","message":"__auth_check__"}'
```

### 快速测试

```bash
# 不获取详情，快速查看
python smart_recommend.py \
  --token qc_xxx \
  --coins "BTC" \
  --year 2024 \
  --no-detail \
  --quiet
```

### 查看日志

```bash
# 详细模式
python smart_recommend.py ... (默认verbose=True)

# 静默模式
python smart_recommend.py ... --quiet
```

---

## ✅ 最佳实践

1. **优先使用 `smart_recommend.py`** - 一键完成所有步骤
2. **始终开启 `--save-memory`** - 建立用户画像
3. **解读结果，不要直接抛数据** - 用人话说
4. **风险警示** - 每次推荐必须说明
5. **记忆驱动** - 利用历史记录优化推荐
6. **交互式优化** - 根据用户反馈调整参数
