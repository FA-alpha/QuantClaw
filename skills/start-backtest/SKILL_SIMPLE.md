# 回测执行规则 - 严格执行版

## 🚨 强制执行规则（不允许违反）

### 规则1：回测成功后禁止询问
- ❌ 绝对不要问"需要我等回测完成后帮你查看结果吗？"
- ❌ 绝对不要问任何关于等待或监控的问题
- ✅ 回测提交成功后直接结束对话

### 规则2：每次都必须询问时间范围
- ❌ 绝对不要使用历史对话中的时间信息
- ✅ 每次回测都必须问用户要什么时间范围

### 规则3：智能处理保证金分配
- ✅ **参数完整时直接执行**：不要反复询问"是否确认"
- ✅ **参数不明确时主动询问**：提供已理解参数作为默认值
- ✅ **理解自然语言**：将用户描述转换为具体参数
- ❌ **不要制造参数**：只传递用户明确指定的参数

---

## 📋 回测类型判断（简单版）

### A. 单个策略回测
**什么时候是单个策略：**
- 用户只提到1个策略
- 用户说"回测策略4300"

**怎么做：**
1. 询问时间范围
2. 直接执行回测（不问保证金模式）

### B. 多个策略回测
**什么时候是多个策略：**
- 用户提到2个或更多策略
- 用户说"一起回测"、"同时回测"

**怎么做：**
1. 询问保证金模式（独占还是共享）
2. 如果选共享，询问保证金分配
3. 询问时间范围
4. 执行回测

---

## 🔢 共享保证金分配处理（最新规则）

### 新的共享模式处理流程：

**步骤1：理解用户自然语言**
- 用户："BTC占60%，其他币种各20%"
- 用户："DOGE多一点，SOL少一点" ← 需要询问具体数值
- 用户："震荡做多70%，做空30%"

**步骤2：判断参数完整性**
- ✅ **参数完整**：直接调用calc_margin接口计算分配
- ❌ **参数不明确**：询问具体数值（已理解的参数作为默认值）

**步骤3：调用calc_margin接口**
```bash
python skills/start-backtest/start.py \
  --calc-margin \
  --strategy-ids 4920,50722,50723 \
  --coin-long-allocation '{"DOGE": 60, "SOL": 20, "XRP": 20}' \
  --coin-short-allocation '{"DOGE": 60, "SOL": 20, "XRP": 20}' \
  --ai-time-long-allocation '{"2025年震荡": 70}' \
  --ai-time-short-allocation '{"2025年震荡": 30}' \
  --total-balance 10000
```

**步骤4：显示分配结果并执行回测**
- ✅ 显示每个策略的具体保证金金额
- ✅ 直接执行apply_backtest（不再询问"是否确认"）

---

## 🛠️ 执行命令格式

### 单策略回测：
```bash
python skills/start-backtest/start.py \
  --apply \
  --strategy-id <策略ID> \
  --bgn-date 2024-01-01 \
  --end-date 2024-12-31 \
  --leverage 10
```

### 多策略回测（独占）：
```bash
python skills/start-backtest/start.py \
  --apply \
  --strategy-ids id1,id2,id3 \
  --margin-mode exclusive \
  --bgn-date 2024-01-01 \
  --end-date 2024-12-31 \
  --leverage 10
```

### 多策略回测（共享，新流程）：

**第1步：计算保证金分配**
```bash
python skills/start-backtest/start.py \
  --calc-margin \
  --strategy-ids id1,id2,id3 \
  --coin-long-allocation '{"BTC": 60, "ETH": 40}' \
  --ai-time-long-allocation '{"2025年震荡": 70}' \
  --ai-time-short-allocation '{"2025年震荡": 30}' \
  --total-balance 10000
```

**第2步：执行回测**
```bash
python skills/start-backtest/start.py \
  --apply \
  --strategy-ids id1,id2,id3 \
  --margin-mode shared \
  --bgn-date 2024-01-01 \
  --end-date 2024-12-31 \
  --leverage 10 \
  --coin-long-allocation '{"BTC": 60, "ETH": 40}' \
  --ai-time-long-allocation '{"2025年震荡": 70}' \
  --total-balance 10000
```

---

## ⏰ 时间范围处理

### 用户可能的输入：
- "最近30天" → 转换为具体日期
- "最近3个月" → 转换为具体日期
- "2024-01-01 到 2024-12-31" → 直接使用

### 转换方法：
- 最近30天 = 当前日期往前推30天
- 最近3个月 = 当前日期往前推3个月

---

## 📝 对话模板（照抄执行）

### 模板1：单策略回测
```
用户："回测策略4300"

回复：
请问回测的时间范围是？
支持格式：
• 最近30天、最近3个月
• 2024-01-01 到 2024-12-31

等用户回复后 → 直接执行回测
```

### 模板2：多策略回测
```
用户："一起回测策略4300和4679"

回复：
请选择保证金模式：
1️⃣ 独占模式 - 每个策略独立使用保证金
2️⃣ 共享模式 - 策略共享保证金池
请回复1或2

如果用户选2 → 继续问分配比例
如果用户选1 → 跳过分配，直接问时间范围
```

### 模板3：智能保证金分配

**情况1：用户提供完整参数**
```
用户："策略组114，DOGE占60%，其他10%，震荡做多70%做空30%，2025年全年"

处理：
1. ✅ 立即调用calc_margin接口
2. ✅ 显示分配结果
3. ✅ 直接执行回测（不询问确认）
```

**情况2：用户参数不明确**
```
用户："共享模式，BTC多一点，其他少一点"

回复：
已理解的参数：
- 策略组：最新策略组114
- 保证金模式：共享模式

需要明确的参数：
- BTC具体占比？（建议：40%, 50%, 60%）
- 其他币种具体占比？
- 市场行情分配？（震荡做多：？%, 震荡做空：？%）
- 回测时间范围？

等用户补充完整参数后 → 直接执行
```

---

## 🔍 新增接口使用

### 查询策略组列表：
```bash
python skills/start-backtest/backtest_monitor.py --list-groups --token <token>
```

### 查询策略列表：
```bash
# 查询所有策略
python skills/start-backtest/backtest_monitor.py --list-strategies --token <token>

# 按币种筛选
python skills/start-backtest/backtest_monitor.py --list-strategies --coin BTC --token <token>

# 按名称搜索
python skills/start-backtest/backtest_monitor.py --list-strategies --name "做多" --token <token>
```

## ❌ 绝对禁止的行为

1. ❌ 说"总和必须为100%"
2. ❌ 说"请确认是否开始回测？"（参数完整时）
3. ❌ 问"需要我等回测完成吗？"
4. ❌ 使用历史对话中的时间范围
5. ❌ 额外制造用户未提及的参数
6. ❌ 在回测成功后继续询问任何问题

## ✅ 必须执行的行为

1. ✅ 每次都询问时间范围
2. ✅ 多策略必须询问保证金模式
3. ✅ **参数完整立即执行**，不过度询问
4. ✅ **参数不明确主动询问**，提供已理解参数
5. ✅ 共享模式先调用calc_margin计算分配
6. ✅ 回测成功后立即结束对话
7. ✅ 使用strategy-id参数（不是strategy-token）
8. ✅ 只传递用户明确指定的参数