# 启动回测

## 🔥 关键警告：Mobile/Strategy/calc_margin接口参数检查

**Agent在共享保证金模式下必须先调用参数完整性检查：**
```bash
python skills/start-backtest/backtest_monitor.py --check-allocation --strategy-ids "ID列表" --token <token>
```
**只有返回 `is_complete: true` 才能继续调用calc_margin接口！**
**禁止臆造、修改、补充用户未提供的分配比例！**

## 🚨 强制执行规则

1. **回测成功后绝对不要询问用户是否需要等待或查看结果**
2. **每次回测必须询问时间范围，不使用历史对话信息**
3. **调用Python脚本前必须获取并传递token参数**
4. **🔥 共享保证金模式必须先调用--check-allocation，禁止臆造分配比例**
5. **🔥 calc_margin接口调用前必须确保参数完整，否则会报错**
6. **🔥 严格按照用户提供的分配比例，不能自行修改或补充**

## 🔄 回测类型识别

### 单策略回测
- 用户明确指定一个策略
- 直接询问时间范围 → 执行回测
- 不需要保证金模式选择

### 多策略/策略组回测
- "一起回测"、"同时回测"、"策略组回测"
- 必须询问保证金模式：独占 或 共享

## 🔧 共享保证金模式处理（重要）

### 🚨 强制流程：必须先调用参数完整性检查（不可跳过）

**⚠️ 重要：Mobile/Strategy/calc_margin接口对参数要求严格，缺失任何必要参数都会报错**
**⚠️ Agent必须先用--check-allocation确认参数完整，才能调用calc_margin接口**

**步骤1：获取策略ID列表**
```bash
# 查询策略组或筛选策略
python skills/start-backtest/backtest_monitor.py --list-groups --token <token>
python skills/start-backtest/backtest_monitor.py --list-strategies --coin BTC --token <token>
```

**步骤2：调用参数完整性检查（必须）**
```bash
python skills/start-backtest/backtest_monitor.py \
  --check-allocation \
  --strategy-ids "4637,50722,50723" \
  --coin-long-allocation '{"DOGE": 60}' \
  --coin-short-allocation '{"DOGE": 50}' \
  --ai-time-allocation '{"2025年震荡": 70}' \
  --token <token>
```

**步骤3：根据检查结果处理**
- `is_complete: true` → 直接执行calc_margin + 回测
- `is_complete: false` → 显示缺失参数，要求用户补充

### ❌ 绝对禁止的行为（会导致回测失败）

1. **🔥 跳过--check-allocation直接调用calc_margin** - 接口会报错
2. **🔥 臆造任何分配比例** - 如设为50%、平均分配、自动补0等
3. **🔥 修改用户提供的分配比例** - 必须严格按用户需求
4. **🔥 参数不完整时继续执行** - 会导致接口调用失败
5. **🔥 忽略--check-allocation的返回结果** - 必须根据is_complete决定后续操作

### ✅ 正确的共享模式处理

```
用户："策略组114共享模式，DOGE占60%"

Agent处理：
1. 获取策略组114的策略ID
2. 调用--check-allocation检查参数完整性
3. 如果缺失参数，显示具体缺失项：
   "检测到缺失参数：
   📊 SOL做空占比：？%  
   📊 AI时间分配：2025年震荡？%
   
   请提供这些参数才能计算保证金分配。"
4. 用户补充完整后，再执行回测
```

## 📊 保证金分配接口参数

### Mobile/Strategy/calc_margin 接口需求：

**必须参数：**
- `strategy_ids` - 策略ID列表
- `total_balance` - 总保证金（默认10000）

**条件必须参数（由策略决定）：**
- `coin_long_allocation` - 币种做多分配（如策略包含BTC/DOGE做多）
- `coin_short_allocation` - 币种做空分配（如策略包含BTC/DOGE做空）
- `ai_time_allocation` - AI时间分配（如策略包含ai_time_id参数）

### 参数检查方法智能识别：

```python
# analyze_strategies_for_allocation() 会分析：
# 1. 策略包含哪些币种的做多/做空
# 2. 策略是否包含ai_time_id/ai_time_name参数
# 3. 生成完整的参数需求清单

# check_allocation_completeness() 会检查：
# 1. 用户提供的参数是否覆盖所有需求
# 2. 返回具体的缺失参数列表
# 3. 确保不会遗漏任何必要参数
```

## 🎯 Agent使用模板

### 共享模式标准流程：

```
1. 用户："策略组XX共享模式，[分配描述]"

2. Agent处理：
   - 获取策略组内策略ID
   - 解析用户分配需求为JSON格式
   - 调用--check-allocation检查完整性
   
3. 如果参数不完整：
   - 显示具体缺失的参数
   - 等待用户补充
   - 重新检查直到完整
   
4. 参数完整后：
   - 调用calc_margin计算分配
   - 执行apply_backtest回测
   - 不再询问"是否确认"
```

## 🔑 Token获取

```bash
TOKEN=$(cat ~/.quantclaw/users.json | jq -r --arg agent_id "当前机器人agentID" '.users[] | select(.agentId == $agent_id) | .token')
```

## 📋 常用命令

```bash
# 查询策略组
python skills/start-backtest/backtest_monitor.py --list-groups --token <token>

# 查询策略（支持筛选）
python skills/start-backtest/backtest_monitor.py --list-strategies --coin DOGE --token <token>

# 检查保证金参数完整性
python skills/start-backtest/backtest_monitor.py --check-allocation --strategy-ids "ID列表" --coin-long-allocation '{}' --token <token>

# 计算保证金分配
python skills/start-backtest/start.py --calc-margin --strategy-ids "ID列表" --coin-long-allocation '{}' --token <token>

# 执行回测
python skills/start-backtest/start.py --apply --strategy-ids "ID列表" --margin-mode shared --bgn-date YYYY-MM-DD --end-date YYYY-MM-DD --token <token>
```

---

**关键原则：共享模式下，参数检查是强制步骤，防止无效API调用和错误处理**