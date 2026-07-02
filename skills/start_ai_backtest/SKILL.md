# SKILL.md - Backtest Optimizer

## 项目简介

自动化加密货币交易策略回测优化系统，通过 **sender.py** 调用回测服务进行批量测试。

**核心组件**：
- `sender.py` - 回测调度模块（唯一调用入口）

---

## 🔑 重要：agentID使用方法

### agentID 获取规则
1. 获取当前机器人的 agentID
2. 调用 sender.py 时，必须传递 `--agent_id` 参数，数据类型为 string
3. 所有接口请求会自动记录日志到 `~/.quantclaw/logs/{agent_id}/yyyy-mm-dd.log`

### 日志记录
- **开启状态**：默认开启接口请求日志
- **日志路径**：`~/.quantclaw/logs/{agent_id}/yyyy-mm-dd.log`
- **日志内容**：包含请求参数、返回参数、时间戳

---

## 🤖 Agent 工作流程

### 步骤 1: 解析用户输入
```
用户："回测 BTC 做多，测试熊市和震荡，每种行情各 200 次"

解析结果：
- coin: BTC
- direction: long
- periods: ["熊市", "震荡"]
- max_evals: 200
```

### 步骤 2: 选择时间段（三种情况）

#### 情况A：用户时间段范围仅选择了"过去一年"
```
所有币种（除 HYPE）统一使用 2025-02-07 ~ 2026-02-07
HYPE 使用 2025-02-22 ~ 2026-02-22
```

#### 情况B：预定义币种（8个）
```
如果 coin 在 [BTC, ETH, SOL, ZEC, NEAR, XLM, HYPE, DOGE] 中：
    → 查下方映射表
    → 直接调用 sender.py run 命令
```

#### 情况C：非预定义币种
```
1. 检查 quantify 数据库中是否有该币种数据
   → 调用: db.check_coin_data_exists(coin, "swap")

2. 如果数据存在：
   → 使用 web_search 搜索时间段
   → 调用 sender.py validate 验证价格
   → 验证通过 → 手动构建 time_periods，调用 AI 回测去将搜索到的对应币种的时间段和市场行情传入
   → 验证失败 → 重试（最多5次）→ Lark 告警

3. 如果数据不存在：
   → 使用 web_search 搜索时间段
   → 调用 sender.py 的回测方法,手动构建 time_periods，调用 AI 回测,去将搜索到的对应币种的时间段和市场行情传入
```

### 步骤 3: 调用命令

**⚠️ 重要**：所有命令必须传递 `--agent_id` 参数！

#### 命令1：预定义币种（run）
```bash
python sender.py \
  --agent_id {当前机器人agentID} \
  run \
  --coin BTC \
  --direction long \
  --max_evals 200
```

**自动回测时间段**：
- long → 震荡市、熊市、过去一年
- short → 震荡市、牛市、过去一年

**总记录数** = max_evals的数量:200 × 回测时间段的数量:3 = 600 条

#### 命令2：验证价格（validate）
```bash
python sender.py \
  --agent_id {当前机器人agentID} \
  validate \
  --coin XRP \
  --start_date 2024-03-01 \
  --end_date 2024-08-15 \
  --market_type 熊市
```

**返回**：通过 / 未通过

#### 命令3：触发OKX获取数据（trigger_okx）
```bash
python sender.py \
  --agent_id {当前机器人agentID} \
  trigger_okx \
  --coin XRP \
  --start_date 2024-03-01 \
  --end_date 2024-08-15 \
  --market_type 熊市 \
  --direction long \
  --max_evals 200
```

**后续流程**：
- OKX 服务获取 K 线数据（每2秒更新）
- 完成后自动验证价格
- 满足规则 → 自动调用 AI 回测
- 不满足规则 → Lark 告警

---

## 📅 预定义时间段映射表

### 预定义币种（8 个）
```
BTC, ETH, SOL, ZEC, NEAR, XLM, HYPE, DOGE
```

### Long 方向

| 时间段 | BTC/ETH/SOL/DOGE | ZEC | NEAR | XLM | HYPE |
|-------|-----------------|-----|------|-----|------|
| **熊市** | 2025-10-01 ~ 2026-02-08 | 2026-01-01 ~ 2026-03-01 | 2024-12-06 ~ 2025-04-09 | 2025-07-22 ~ 2026-05-22 | 2025-11-01 ~ 2025-12-31 |
| **牛市** | 2025-04-10 ~ 2025-08-14 | 2025-04-10 ~ 2025-08-14 | 2025-04-10 ~ 2025-08-14 | 2025-04-10 ~ 2025-08-14 | 2025-04-10 ~ 2025-08-14 |
| **震荡** | 2024-12-01 ~ 2025-12-31 | 2024-11-01 ~ 2025-08-01 | 2025-04-10 ~ 2026-01-14 | 2024-02-07 ~ 2024-11-03 | 2024-02-07 ~ 2024-11-03 |
| **过去一年** | **2025-02-07 ~ 2026-02-07** | 2025-02-07 ~ 2026-02-07 | 2025-02-07 ~ 2026-02-07 | 2025-02-07 ~ 2026-02-07 | **2025-02-22 ~ 2026-02-22** |

### Short 方向

| 时间段 | 所有币种（除 HYPE） | HYPE |
|-------|------------------|------|
| **熊市** | 2025-10-01 ~ 2026-02-08 | 2025-10-01 ~ 2026-02-08 |
| **牛市** | 2025-04-10 ~ 2025-08-14 | 2025-04-10 ~ 2025-08-14 |
| **震荡** | 2024-12-01 ~ 2025-12-31 | 2025-02-22 ~ 2026-02-22 |
| **过去一年** | **2025-02-07 ~ 2026-02-07** | **2025-02-22 ~ 2026-02-22** |

**📌 "过去一年"统一规则**：
- **7个币种**（BTC/ETH/SOL/ZEC/NEAR/XLM/DOGE）：统一使用 **2025-02-07 ~ 2026-02-07**
- **HYPE**：特殊规则，使用 **2025-02-22 ~ 2026-02-22**
- 无论 Long 还是 Short 方向，都遵循此规则

---

## 🔍 Web Search 规则（非预定义币种）

### 搜索条件

| 时间段 | 时长要求 | 价格变化要求 |
|-------|---------|-------------|
| **熊市** | > 3个月 | 起始价格比结束价格高 > 50% |
| **牛市** | > 3个月 | 结束价格比起始价格高 > 50% |
| **震荡** | > 6个月 | 起始与结束价格差距 < 20% |
| **过去一年** | 固定 365 天 | **固定时间段：2025-02-07 ~ 2026-02-07** |

**⚠️ 注意**：非预定义币种选择"过去一年"时，**不需要**用 web_search，直接使用固定时间段 `2025-02-07 ~ 2026-02-07`

### 搜索查询模板
```
熊市: "{coin} bear market 2024 2025 price drop 50% historical data"
牛市: "{coin} bull market 2025 price rally 50% historical data"
震荡: "{coin} range bound sideways market 2024 2025 historical data"
```

### 验证步骤
1. 调用 `web_search` 获取历史数据
2. 提取时间段起止日期和价格
3. 计算时长和价格变化百分比
4. 验证是否满足上述条件
5. 返回 `{"start_date": "...", "end_date": "...", "name": "..."}`

---

## 📖 使用示例

### 示例 1: 预定义币种（BTC 多头）
```bash
# 用户输入
"回测 BTC 做多，测试 200 次"

# Agent 调用
python sender.py --agent_id {当前机器人agentID} run \
  --coin BTC \
  --direction long \
  --max_evals 200

# 自动回测时间段：震荡、熊市、过去一年
# 总记录数：600 条 (200 × 3)
```

### 示例 2: 非预定义币种（XRP）
```bash
# 用户输入
"回测 XRP 做多，测试熊市，150 次"

# Agent 处理
# 1. XRP 不是预定义币种 → 调用 web_search
# 2. 搜索: "XRP bear market 2024 2025 price drop 50%"
# 3. 找到: 2024-03-01 ~ 2024-08-15 (下跌 57%, 167天) ✅

python sender.py \
  --max_evals 150 \
  --coin XRP \
  --direction long \
  --max_go_pct 12 \
  --min_rate 18 \
  --time_periods '[
    {"start_date":"2024-03-01","end_date":"2024-08-15","name":"XRP 熊市"}
  ]'

# 总记录数：150 条
```

### 示例 3: 过去一年（非预定义币种）
```bash
# 用户输入
"回测 XRP 多头，测试过去一年，180 次"

# Agent 处理
# 1. 识别到"过去一年"
# 2. 直接使用固定时间段：2025-02-07 ~ 2026-02-07
# 3. 不需要调用 web_search ✅

python projects/backtest-optimizer/sender.py \
  --max_evals 180 \
  --coin XRP \
  --direction long \
  --max_go_pct 10 \
  --min_rate 20 \
  --time_periods '[
    {"start_date":"2025-02-07","end_date":"2026-02-07","name":"过去一年"}
  ]'

# 总记录数：180 条
```

### 示例 4: ZEC 特殊时间段
```bash
# 用户输入
"回测 ZEC 空头，测试震荡，120 次"

# Agent 调用（ZEC 震荡期有特殊定义）
python projects/backtest-optimizer/sender.py \
  --max_evals 120 \
  --coin ZEC \
  --direction short \
  --max_go_pct 12 \
  --min_rate 18 \
  --time_periods '[
    {"start_date":"2024-11-01","end_date":"2025-08-01","name":"震荡"}
  ]'

# 总记录数：120 条
```

---

## 🔧 sender.py 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--max_evals` | 单个时间段的测试次数 | `200` |
| `--coin` | 币种 | `BTC`, `ETH`, `XRP` |
| `--direction` | 交易方向 | `long` / `short` |
| `--max_go_pct` | 最大网格比例 | `10` |
| `--min_rate` | 最小年化收益率 | `20` |
| `--time_periods` | 时间段 JSON 数组 | `'[{"start_date":"...","end_date":"...","name":"..."}]'` |

---

## 🔴 关键 Gotcha

### 🔴 G1: max_evals 是单个时间段测试次数
- ✅ 正确：`--max_evals 200` → 每个时间段 200 次
- ❌ 错误：`--max_evals 200,200,200`
- **总记录数** = `max_evals × len(time_periods)`

### 🔴 G2: 预定义币种不要用 web_search
- **优先级**：预定义币种直接查映射表
- **预定义列表**：`BTC, ETH, SOL, ZEC, NEAR, XLM, HYPE, DOGE`
- 其他币种（如 XRP, ADA）才用 web_search

### 🔴 G3: "过去一年"时间段是固定的
- ✅ 正确：所有币种（除 HYPE）统一使用 `2025-02-07 ~ 2026-02-07`
- ✅ HYPE 特殊：使用 `2025-02-22 ~ 2026-02-22`
- ❌ 错误：用 web_search 查询"过去一年"的时间段
- ❌ 错误：用非预定义币种时动态计算时间

### 🔴 G4: Web Search 结果必须严格验证
- 熊市：时长 > 90 天 && 价格下跌 > 50%
- 牛市：时长 > 90 天 && 价格上涨 > 50%
- 震荡：时长 > 180 天 && 价格变化 < 20%
- **"过去一年"不需要验证**（固定时间段）

### 🔴 G5: 数据库配置已固定在 sender.py
- ✅ BI 数据库配置已内置，无需外部 config 文件
- ✅ 只能操作 `fourieralpha_bi` 数据库
- ❌ 不要修改数据库配置（host/user/password/database）
- ❌ 不要尝试连接其他数据库

---

## 📁 相关文件

- `sender.py` - 核心调度模块（本目录）
- `QUICKREF.md` - 快速参考
- `backtrack_fengting_v4_ai_7025.py` - 回测服务（不可修改）

---

*最后更新: 2026-06-23*
