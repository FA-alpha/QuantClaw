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
