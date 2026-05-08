# 演示指南

## 🎬 快速演示

### 前置条件

1. 确保有有效的 user token
2. 确保服务正常运行

### 演示流程

#### 场景 1: 用户询问策略推荐

**用户输入**:
> "帮我推荐一些BTC和ETH的策略组合，要稳健一点"

**Agent 处理流程**:

```bash
# 1. 识别意图
#    - 币种: BTC, ETH
#    - 风险偏好: 稳健 → max-drawdown=15, min-sharpe=1.8
#    - 需要: 组合推荐

# 2. 调用智能推荐
python /home/ubuntu/work/QuantClaw/skills/backtest-query/smart_recommend.py \
  --token {user_token} \
  --coins "BTC,ETH" \
  --year 2024 \
  --min-sharpe 1.8 \
  --max-drawdown 15 \
  --group-size 3 \
  --top-n 3 \
  --workspace {user_workspace} \
  --save-memory

# 3. 解读结果并回复
```

**Agent 回复示例**:

```
我为您分析了BTC和ETH的策略，找到了3个稳健的组合方案：

🏆 推荐组合 #1 (评分: 85.3/100)

📋 策略列表:
   1. BTC风霆做多v2
      币种: BTC | 年化: 32.5% | 夏普: 2.1 | 回撤: 11.2%
   
   2. ETH鲲鹏震荡v3
      币种: ETH | 年化: 26.8% | 夏普: 1.9 | 回撤: 9.5%
   
   3. BTC网格策略v1
      币种: BTC | 年化: 18.3% | 夏普: 2.3 | 回撤: 7.8%

📊 组合分析:
   相关性: 0.31 (低相关性✅，策略之间互相独立)
   组合夏普: 2.08 (风险调整后收益良好)
   组合回撤: 9.5% (风险可控)
   回撤重叠: 18% (回撤时间错开，对冲效果好)

💡 推荐理由: 相关性极低(0.31)、高夏普率(2.08)、回撤错位良好(18.0%重叠)

这个组合的特点是：
- 三个策略相互独立，不会同时亏损
- 风险调整后的收益表现优秀
- 回撤时间错开，整体风险较低

⚠️ 风险提示：
回测数据基于历史，实盘需谨慎，建议小仓位测试。

要创建这个策略组吗？
```

**用户确认**: "好的，创建吧"

**Agent 执行**:

```bash
python /home/ubuntu/work/QuantClaw/skills/backtest-query/query.py \
  --token {user_token} \
  --create-group \
  --group-name "BTC+ETH稳健组合" \
  --strategy-tokens "st_abc123,st_def456,st_xyz789"
```

**Agent 回复**:

```
✅ 策略组创建成功！

组合名称: BTC+ETH稳健组合
组合ID: 12345

已保存到您的记忆中，下次可以直接查询历史记录。
```

---

#### 场景 2: 用户想看历史推荐

**用户输入**:
> "我之前推荐过什么组合？"

**Agent 处理**:

```python
# 1. 搜索记忆
memory_search("策略组合 推荐")

# 2. 读取记忆
memory_get("memory/portfolio_history.md", from=最近记录)

# 3. 回复
```

**Agent 回复**:

```
根据记忆记录，您之前创建过：

2024-04-23 - BTC+ETH稳健组合
- BTC风霆做多v2 (年化32.5%, 夏普2.1)
- ETH鲲鹏震荡v3 (年化26.8%, 夏普1.9)
- BTC网格策略v1 (年化18.3%, 夏普2.3)

组合特点：
- 相关性: 0.31 (低相关)
- 组合夏普: 2.08
- 回撤重叠: 18%

您想查看详细信息还是创建新的组合？
```

---

#### 场景 3: 用户想要更激进的策略

**用户输入**:
> "有没有收益更高的？可以承受20%回撤"

**Agent 处理**:

```bash
# 调整参数
python smart_recommend.py \
  --token {user_token} \
  --coins "BTC,SOL,BNB" \  # 增加高波动币种
  --year 2024 \
  --max-drawdown 20 \       # 放宽回撤
  --min-sharpe 1.5 \        # 降低夏普要求
  --sort 2 \                # 按收益率排序
  --workspace {user_workspace} \
  --save-memory
```

---

## 🧪 测试命令

### 测试基础查询

```bash
# 列出币种
python query.py --token YOUR_TOKEN --list-coins

# 列出时间段
python query.py --token YOUR_TOKEN --list-ai-times

# 查询BTC策略
python query.py \
  --token YOUR_TOKEN \
  --coin BTC \
  --amt-type 2 \
  --sort 2 \
  --strategy-type 11 \
  --year 2024 \
  --direction long
```

### 测试智能推荐（快速模式）

```bash
# 不获取详情，快速查看
python smart_recommend.py \
  --token YOUR_TOKEN \
  --coins "BTC" \
  --year 2024 \
  --no-detail \
  --format json
```

### 测试完整流程

```bash
# 完整推荐并保存记忆
python smart_recommend.py \
  --token YOUR_TOKEN \
  --coins "BTC,ETH" \
  --year 2024 \
  --group-size 2 \
  --top-n 3 \
  --workspace /path/to/workspace \
  --save-memory
```

---

## 📝 常见问题

### Q: 如何获取 token？

A: Token 由 auth 插件在用户首次访问时自动生成。

### Q: workspace 路径是什么？

A: 用户的工作区路径，例如: `~/clawd-qc-abc123`

### Q: 推荐失败怎么办？

A: 检查：
1. Token 是否有效
2. 年份或 ai_time_id 是否正确
3. 策略数量是否足够（至少需要 group_size 个）
4. 是否有网络问题

### Q: 如何调试？

A: 使用 `--format json` 查看原始数据，不使用 `--quiet` 查看详细日志。
