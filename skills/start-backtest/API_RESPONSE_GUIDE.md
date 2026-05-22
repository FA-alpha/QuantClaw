# API 返回数据说明文档

本文档详细说明 start-backtest 中所有 Python 脚本调用接口后返回的数据结构和参数含义，供 Agent 快速理解和处理。

---

## 📋 接口列表概览

| 函数名 | 接口地址 | 功能 |
|--------|----------|------|
| `get_coin_list` | `/Strategy/coin_lists` | 获取可用币种列表 |
| `get_group_lists` | `/Strategy/group_lists` | 获取策略组列表 |
| `get_strategy_lists` | `/Strategy/lists` | 获取策略列表 |
| `get_backtest_detail` | `/Backtrack/stat_info` | 获取回测详细统计信息 |
| `get_backtest_list` | `/Backtrack/lists` | 获取回测列表/历史记录 |
| `calc_margin_allocation` | `/Strategy/calc_margin` | 计算保证金分配方案 |
| `apply_backtest` | `/Backtrack/apply_do` | 启动回测任务 |

---

## 🪙 get_coin_list - 币种列表

**接口**: `POST /Strategy/coin_lists`

### 返回数据结构
```json
{
  "status": 1,
  "msg": "success",
  "info": [
    {
      "coin": "BTC",
      "name": "比特币"
    },
    {
      "coin": "ETH", 
      "name": "以太坊"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态（1=成功, 0=失败） | 1 |
| `msg` | string | 状态消息 | "success" |
| `info` | array | 币种列表数组 | [...] |
| `info[].coin` | string | 币种代码 | "BTC" |
| `info[].name` | string | 币种中文名称 | "比特币" |

### Agent 使用示例
```python
result = get_coin_list(token)
if result.get("status") == 1:
    coins = result.get("info", [])
    for coin_info in coins:
        coin_code = coin_info.get("coin")      # BTC, ETH, SOL...
        coin_name = coin_info.get("name")      # 比特币, 以太坊...
```

---

## 📁 get_group_lists - 策略组列表

**接口**: `POST /Strategy/group_lists`

### 返回数据结构
```json
{
  "status": 1,
  "msg": "success", 
  "info": [
    {
      "id": 12333,
      "name": "BTC/ETH/SOL 风霆V4.2 多空组合",
      "strategy_count": 6,
      "created_at": "2026-05-09 15:30:22",
      "strategies": [
        {
          "id": 4300,
          "name": "BTC-风霆V4.2-做多",
          "coin": "BTC",
          "direction": "做多"
        }
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态 | 1 |
| `msg` | string | 状态消息 | "success" |
| `info` | array | 策略组列表 | [...] |
| `info[].id` | int | 策略组ID | 12333 |
| `info[].name` | string | 策略组名称 | "BTC/ETH/SOL 风霆V4.2 多空组合" |
| `info[].strategy_count` | int | 包含的策略数量 | 6 |
| `info[].created_at` | string | 创建时间 | "2026-05-09 15:30:22" |
| `info[].strategies` | array | 策略组内的策略详情 | [...] |
| `strategies[].id` | int | 策略ID | 4300 |
| `strategies[].name` | string | 策略名称 | "BTC-风霆V4.2-做多" |
| `strategies[].coin` | string | 币种 | "BTC" |
| `strategies[].direction` | string | 方向 | "做多" |

### Agent 使用示例
```python
result = get_group_lists(token)
if result.get("status") == 1:
    groups = result.get("info", [])
    for group in groups:
        group_id = group.get("id")                    # 策略组ID
        group_name = group.get("name")                # 策略组名称
        strategy_count = group.get("strategy_count")  # 策略数量
        strategies = group.get("strategies", [])      # 策略详情列表
```

---

## 📈 get_strategy_lists - 策略列表

**接口**: `POST /Strategy/lists`

### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `usertoken` | string | ✅ 是 | - | 用户认证token |
| `page` | int | ❌ 否 | 1 | 页码，从1开始 |
| `limit` | int | ❌ 否 | 10 | 每页返回条数 |
| `search_val` | string | ❌ 否 | - | 搜索关键词（策略名称模糊搜索） |
| `data_grade` | int | ❌ 否 | 1 | 排序方式：1=按创建时间排序 |
| `show_type` | int | ❌ 否 | 1 | 显示类型：1=标准显示 |
| `app_v` | string | ❌ 否 | "2.0.0" | API版本 |
| `lang` | int | ❌ 否 | 1 | 语言：1=中文 |

### 💡 **标准请求参数（推荐）**
```json
{
  "usertoken": "MTEjI2JpYXplQGZvdXJpZXJhbHBoYS5jb20jIzE3Nzg2NjU0NzAjI3BsYW50X3YyIyMwIyMxIyN1c2Vy",
  "page": 1,
  "limit": 10,
  "data_grade": 1,
  "show_type": 1,
  "app_v": "2.0.0",
  "lang": 1
}
```

### 🔍 **搜索模式参数**
当需要搜索特定策略时，额外添加：
```json
{
  "search_val": "风霆V4.3"  // 根据用户需求设置搜索关键词
}
```

### 返回数据结构
```json
{
  "status": 1,
  "msg": "success",
  "info": [
    {
      "id": 4300,
      "strategy_token": "abc123def456",
      "name": "BTC-风霆V4.2-做多",
      "coin": "BTC",
      "amt_type": 2,
      "direction": "做多",
      "leverage": 10,
      "created_at": "2026-05-09 15:30:22",
      "status": 1
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态 | 1 |
| `msg` | string | 状态消息 | "success" |
| `info` | array | 策略列表 | [...] |
| `info[].id` | int | **策略ID**（用于回测） | 4300 |
| `info[].strategy_token` | string | 策略Token（查询用） | "abc123def456" |
| `info[].name` | string | 策略名称 | "BTC-风霆V4.2-做多" |
| `info[].coin` | string | 币种 | "BTC" |
| `info[].amt_type` | int | 类型（1=现货, 2=合约） | 2 |
| `info[].direction` | string | 方向 | "做多" |
| `info[].leverage` | int | 杠杆倍数 | 10 |
| `info[].created_at` | string | 创建时间 | "2026-05-09 15:30:22" |
| `info[].status` | int | 策略状态（1=正常） | 1 |

### ⚠️ 重要提醒
- **回测使用 `id` 字段**，不是 `strategy_token`
- **amt_type**: 1=现货, 2=合约
- **杠杆**: 合约策略必填参数

### Agent 使用示例
```python
result = get_strategy_lists(token, coin="BTC")
if result.get("status") == 1:
    strategies = result.get("info", [])
    for strategy in strategies:
        strategy_id = strategy.get("id")              # 用于回测的ID
        strategy_name = strategy.get("name")          # 策略名称
        coin = strategy.get("coin")                   # 币种
        direction = strategy.get("direction")         # 做多/做空
        amt_type = strategy.get("amt_type")           # 1现货2合约
        leverage = strategy.get("leverage")           # 杠杆倍数
```

---

## 📊 get_backtest_detail - 回测详细统计

**接口**: `POST /Backtrack/stat_info`

### 返回数据结构
```json
{
  "status": 1,
  "msg": "success",
  "info": {
    "back_id": 5906,
    "name": "BTC-风霆V4.2-做多",
    "year_rate": "25.30",
    "sharp_rate": "1.85",
    "max_loss": "8.45",
    "win_rate": "68.5",
    "trade_num": 156,
    "total_stat": {
      // net_value 参数已被自动删除，节省上下文
      "profit_rate": "25.30",
      "max_drawdown": "8.45"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态 | 1 |
| `msg` | string | 状态消息 | "success" |
| `info` | object | 回测详细信息 | {...} |
| `info.back_id` | int | 回测ID | 5906 |
| `info.name` | string | 策略名称 | "BTC-风霆V4.2-做多" |
| `info.year_rate` | string | 年化收益率 | "25.30" |
| `info.sharp_rate` | string | 夏普比率 | "1.85" |
| `info.max_loss` | string | 最大回撤 | "8.45" |
| `info.win_rate` | string | 胜率 | "68.5" |
| `info.trade_num` | int | 交易次数 | 156 |
| `info.total_stat` | object | 统计数据（已清理net_value） | {...} |

### ⚠️ 自动数据清理
- **net_value参数已被自动删除** - 节省上下文窗口
- **daily_stat已被删除** - 避免大数据传输
- **trade_details已被删除** - 移除详细交易记录

### Agent 使用示例
```python
result = get_backtest_detail(token, back_id=5906)
if result.get("status") == 1:
    info = result.get("info", {})
    year_rate = info.get("year_rate")      # 年化收益率
    sharp_rate = info.get("sharp_rate")    # 夏普比率
    max_loss = info.get("max_loss")        # 最大回撤
    # total_stat 中的 net_value 已被自动清理
```

---

## 📋 get_backtest_list - 回测列表

**接口**: `POST /Backtrack/lists`

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `usertoken` | string | ✅ 是 | 用户认证token |
| `back_id` | string | ❌ 否 | 回测ID，不传则查询所有回测记录 |
| `page` | int | ❌ 否 | 页码，从1开始，默认1 |
| `limit` | int | ❌ 否 | 每页返回条数，默认10 |
| `app_v` | string | ❌ 否 | API版本，建议使用"2.0.0" |
| `lang` | int | ❌ 否 | 语言设置，1=中文 |
| `type` | int | ❌ 否 | 查询类型，1=标准查询 |
| `sort_type` | int | ❌ 否 | 排序字段，1=按回测时间排序 |
| `sort_direction` | string | ❌ 否 | 排序方向，"desc"=降序，"asc"=升序 |
| `search_val` | string | ❌ 否 | 搜索关键词，为空则不筛选 |
| `search_bgn_date` | string | ❌ 否 | 搜索开始日期，格式YYYY-MM-DD |
| `search_end_date` | string | ❌ 否 | 搜索结束日期，格式YYYY-MM-DD |

### 🔧 参数作用详解

#### 📊 排序参数
- **sort_type=1**: 按回测开始时间(back_time)排序，确保最新回测在前
- **sort_direction="desc"**: 降序排列，最新的在最前面
- **组合使用**: `sort_type=1` + `sort_direction="desc"` 实现按时间倒序

#### 🎯 分页参数  
- **page**: 页码从1开始，替代offset参数
- **limit**: 每页条数，建议10-50之间
- **计算**: `page = (offset / limit) + 1`

#### 🔍 搜索参数
- **search_val**: 按策略名称模糊搜索
- **search_bgn_date/search_end_date**: 按回测时间范围筛选
- **type=1**: 标准查询模式，包含完整回测信息

#### 🌐 环境参数
- **app_v="2.0.0"**: Agent专用API版本，不同于网页版1.0.1
- **lang=1**: 中文界面，影响返回的错误信息语言

### 💡 推荐配置
```json
{
  "usertoken": "xxx",
  "app_v": "2.0.0",
  "lang": 1,
  "type": 1,
  "sort_type": 1,
  "sort_direction": "desc",
  "page": 1,
  "limit": 10
}
```

### 返回数据结构

#### 成功响应（多条记录）
```json
{
  "status": 1,
  "info": [
    {
      "id": "5745",
      "status": "3",
      "name": "BTC/ETH/SOL 风霆V4.4-做多",
      "year_rate": "125.67",
      "sharp_rate": "1.85",
      "max_loss": "15.23",
      "win_rate": "68.5",
      "trade_num": "156",
      "strategy_num": "3",
      "bgn_date": "2025-01-01",
      "end_date": "2025-12-31",
      "create_time": "2026-05-19 10:30:15",
      "update_time": "2026-05-19 12:45:32"
    },
    {
      "back_id": "5746",
      "status": "2",
      "name": "SOL震荡策略组合",
      "year_rate": "",
      "sharp_rate": "",
      "max_loss": "",
      "win_rate": "",
      "trade_num": "",
      "strategy_num": "5",
      "bgn_date": "2024-06-01",
      "end_date": "2024-12-31",
      "create_time": "2026-05-19 15:20:10",
      "update_time": "2026-05-19 15:20:10"
    }
  ]
}
```

#### 错误响应
```json
{
  "status": 0,
  "info": "Token验证失败"
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 响应状态：1=成功，0=失败 | 1 |
| `info` | array/string | 成功时为回测列表数组，失败时为错误信息字符串 | [...] |

#### 回测记录字段详解

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `id` | string | 回测ID | "5745" |
| `status` | string | 回测状态 | "1"=排队, "2"=运行中, "3"=成功, "4"=失败 |
| `name` | string | 回测名称 | "BTC/ETH/SOL 风霆V4.4-做多" |
| `year_rate` | string | 年化收益率(%) | "125.67" |
| `sharp_rate` | string | 夏普比率 | "1.85" |
| `max_loss` | string | 最大回撤(%) | "15.23" |
| `win_rate` | string | 胜率(%) | "68.5" |
| `trade_num` | string | 交易次数 | "156" |
| `strategy_num` | string | 策略数量 | "3" |
| `bgn_date` | string | 开始日期 | "2025-01-01" |
| `end_date` | string | 结束日期 | "2025-12-31" |
| `create_time` | string | 创建时间 | "2026-05-19 10:30:15" |
| `update_time` | string | 更新时间 | "2026-05-19 12:45:32" |

### 状态码对照表

| 状态码 | 状态名称 | 描述 | Emoji |
|--------|----------|------|-------|
| "1" | 排队中 | 回测任务已提交，等待执行 | ⏳ |
| "2" | 运行中 | 回测正在执行中 | 🏃 |
| "3" | 成功 | 回测已完成，可查看结果 | ✅ |
| "4" | 失败 | 回测执行失败 | ❌ |

### Agent 使用示例
```bash
# 查询所有回测记录（建议加过滤避免上下文爆炸）
python skills/start-backtest/backtest_monitor.py \
  --list-backtests \
  --token "$TOKEN" \
  --limit 10

# 按策略名筛选（避免大量无关数据）
python skills/start-backtest/backtest_monitor.py \
  --list-backtests \
  --token "$TOKEN" \
  --filter-name "风霆" \
  --limit 5

# 查询最近7天的回测记录
python skills/start-backtest/backtest_monitor.py \
  --list-backtests \
  --token "$TOKEN" \
  --filter-days 7

# 查询已完成的回测记录
python skills/start-backtest/backtest_monitor.py \
  --list-backtests \
  --token "$TOKEN" \
  --filter-status "3" \
  --limit 10

# 查询指定回测记录详细信息
python skills/start-backtest/backtest_monitor.py \
  --get-backtest-detail "5745" \
  --token "$TOKEN"
```

### ⚠️ 重要提醒
1. **Token认证**: 所有请求必须包含有效的usertoken
2. **空结果**: 当查询的back_id不存在时，info字段为空数组 `[]`
3. **运行中状态**: 状态为"1"或"2"时，收益相关字段可能为空字符串
4. **时间格式**: 时间字段格式为 "YYYY-MM-DD HH:mm:ss" 或 "YYYY-MM-DD"

### 用户触发场景
- "查看我的回测记录"、"回测历史"、"过去的回测"
- "回测ID 5745 的结果"、"回测 5745 怎么样"
- "最近的回测记录"、"所有回测列表"

---

## 📊 get_backtest_detail - 回测详细信息

**接口**: `POST /Backtrack/stat_info`

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `usertoken` | string | ✅ 是 | 用户认证token |
| `back_id` | string | ✅ 是 | 回测ID |

### 返回数据结构

#### 成功响应
```json
{
  "status": 1,
  "info": {
    "back_id": "5745",
    "status": "3",
    "name": "BTC/ETH/SOL 风霆V4.4-做多",
    "year_rate": "125.67",
    "sharp_rate": "1.85",
    "max_loss": "15.23",
    "win_rate": "68.5",
    "trade_num": "156",
    "total_return": "1256.78",
    "max_drawdown_days": "5",
    "avg_trade_return": "8.05",
    "profit_trades": "107",
    "loss_trades": "49",
    "avg_profit": "15.32",
    "avg_loss": "-8.45",
    "profit_loss_ratio": "1.81",
    "kelly_criterion": "0.234",
    "volatility": "18.45",
    "sortino_ratio": "2.15",
    "calmar_ratio": "8.25",
    "create_time": "2026-05-19 10:30:15",
    "update_time": "2026-05-19 12:45:32",
    "strategy": [
      {
        "id": 4300,
        "name": "BTC-风霆V4.2-做多",
        "coin": "BTC",
        "direction": "做多",
        "ai_time_id": "123",
        "ai_time_name": "2025年震荡"
      },
      {
        "id": 4301,
        "name": "ETH-风霆V4.2-做多", 
        "coin": "ETH",
        "direction": "做多",
        "ai_time_id": "123",
        "ai_time_name": "2025年震荡"
      }
    ]
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态 | 1 |
| `info` | object | 回测详细信息 | {...} |
| `info.back_id` | string | 回测ID | "5745" |
| `info.status` | string | 回测状态 | "3" |
| `info.name` | string | 策略名称 | "BTC/ETH/SOL 风霆V4.4-做多" |
| `info.year_rate` | string | 年化收益率 | "125.67" |
| `info.sharp_rate` | string | 夏普比率 | "1.85" |
| `info.max_loss` | string | 最大回撤 | "15.23" |
| `info.win_rate` | string | 胜率 | "68.5" |
| `info.trade_num` | string | 交易次数 | "156" |
| `info.strategy` | array | **策略详情数组**（重要） | [...] |
| `strategy[].id` | int | 策略ID | 4300 |
| `strategy[].name` | string | 策略名称 | "BTC-风霆V4.2-做多" |
| `strategy[].coin` | string | 币种 | "BTC" |
| `strategy[].direction` | string | 方向 | "做多" |
| `strategy[].ai_time_id` | string | **AI时间ID**（策略组特有） | "123" |
| `strategy[].ai_time_name` | string | **AI时间名称**（策略组特有） | "2025年震荡" |

### ⚠️ 重要 - 策略组vs单策略判断

**策略组回测特征:**
- `strategy` 数组中包含 `ai_time_id` 参数（关键判断标准）
- 通常也包含 `ai_time_name` 参数

**多策略回测特征:**  
- `strategy` 数组中**没有** `ai_time_id` 参数
- 可能包含一个或多个策略，没有 `ai_time_id` 就是多策略回测

### 🔧 保证金模式与参数需求

**独占保证金模式:**
- 适用于任何回测类型（单个策略、多策略、策略组）
- 每个策略独立分配保证金，**无需**任何分配参数
- 系统自动分配，用户无需干预

**共享保证金模式:**
- ⚠️ **仅适用于多个策略或策略组的回测** 
- 单个策略回测时，无共享保证金模式选项
- **策略组回测**: 需要币种分配参数 + AI时间分配参数  
- **多策略回测**: 只需要币种分配参数（无需AI时间参数）

**Agent检查逻辑:**
```python
def is_strategy_group_backtest(strategy_info):
    """检查是否为策略组回测"""
    if not strategy_info.get("strategy"):
        return False
    
    for strategy in strategy_info["strategy"]:
        ai_time_id = strategy.get("ai_time_id")
        
        # 关键判断：有ai_time_id参数就是策略组回测
        if ai_time_id:
            return True
    
    return False

def is_shared_mode_applicable(strategy_info):
    """检查是否可以使用共享保证金模式"""
    strategies = strategy_info.get("strategy", [])
    
    # 共享模式仅适用于多个策略或策略组
    if len(strategies) <= 1:
        return False  # 单个策略不支持共享模式
    
    return True  # 多策略或策略组支持共享模式

def needs_ai_time_params(strategy_info, margin_mode):
    """检查是否需要AI时间参数"""
    if margin_mode == "exclusive":
        return False  # 独占模式不需要任何分配参数
    
    if margin_mode == "shared":
        if not is_shared_mode_applicable(strategy_info):
            return False  # 单个策略不支持共享模式
        return is_strategy_group_backtest(strategy_info)  # 共享模式下策略组才需要AI时间参数
    
    return False
```

### 重要说明

| 字段 | 说明 | 备注 |
|------|------|------|
| `net_value` | 净值曲线数据 | **已过滤**，避免上下文爆炸 |
| `strategy` | 策略详情数组 | **新增重要字段**，包含AI时间参数 |
| `ai_time_id/ai_time_name` | AI时间参数 | **策略组标识**，用于再次回测时的参数检查 |
| 其他字段 | 回测统计指标 | 完整返回给Agent |

### Agent 调用方式
```bash
# 获取回测详细信息（不含净值曲线）
python skills/start-backtest/backtest_monitor.py \
  --get-backtest-detail "5745" \
  --token "$TOKEN"

# 分析回测策略参数需求（用于再次回测）
python skills/start-backtest/backtest_monitor.py \
  --analyze-backtest-strategies "5745" \
  --token "$TOKEN"
```

### 使用场景
- Agent确认要查看具体回测后，调用此接口获取详细统计数据
- 先用 `--list-backtests` 过滤筛选，再用此接口查看详情
- **用这个回测的策略再次回测时**，使用 `--analyze-backtest-strategies` 分析参数需求
- 避免直接查询大量回测数据导致上下文溢出

### 🔄 再次回测工作流程

当用户想使用某个回测的策略再次进行回测时：

#### 1️⃣ 分析回测策略参数
```bash
python skills/start-backtest/backtest_monitor.py \
  --analyze-backtest-strategies "5745" \
  --token "$TOKEN"
```

#### 2️⃣ 检查参数完整性（如果是共享保证金模式）
```bash
python skills/start-backtest/backtest_monitor.py \
  --check-allocation \
  --token "$TOKEN" \
  --strategy-ids "4300,4301,4302" \
  --coin-long-allocation '{"BTC": 40, "ETH": 30, "SOL": 30}' \
  --ai-time-long-allocation '{"2025年震荡": 70, "最近1年": 30}'
```

#### 3️⃣ 启动新回测
```bash
python skills/start-backtest/start.py \
  --apply \
  --token "$TOKEN" \
  --strategy-ids "4300,4301,4302" \
  --bgn-date "2024-01-01" \
  --end-date "2024-12-31" \
  # 其他参数...
```

**关键判断逻辑：**
1. **策略类型判断**: 有 `ai_time_id` = 策略组，无 `ai_time_id` = 单策略
2. **保证金模式**: 独占模式无需参数，共享模式需要分配参数  
3. **参数需求**: 策略组+共享模式需要AI时间参数，多策略+共享模式不需要

**实际输出示例：**

```json
// 策略组回测分析结果
{
  "back_id": "5745",
  "backtest_name": "BTC/ETH/SOL 风霆V4.2 多空组合",
  "strategy_count": 3,
  "is_strategy_group_backtest": true,
  "requirement": {
    "coin_long_pairs": ["BTC", "ETH"],
    "coin_short_pairs": ["SOL"],
    "ai_time_long_types": ["2025年震荡"],
    "ai_time_short_types": ["最近1年"],
    "ai_time_id_mapping": {
      "2025年震荡": "123",
      "最近1年": "124"
    },
    "has_ai_time": true
  },
  "usage_guide": {
    "exclusive_mode": "独占保证金模式：无需任何分配参数",
    "shared_mode": "共享保证金模式：需要币种分配参数 + AI时间分配参数"
  }
}

// 多策略回测分析结果  
{
  "back_id": "5746",
  "backtest_name": "BTC/ETH/SOL-多策略组合",
  "strategy_count": 3,
  "is_strategy_group_backtest": false,
  "requirement": {
    "coin_long_pairs": ["BTC", "ETH"],
    "coin_short_pairs": ["SOL"],
    "ai_time_long_types": [],
    "ai_time_short_types": [],
    "ai_time_id_mapping": {},
    "has_ai_time": false
  },
  "usage_guide": {
    "exclusive_mode": "独占保证金模式：无需任何分配参数", 
    "shared_mode": "共享保证金模式：只需要币种分配参数（无需AI时间参数）"
  }
}
```

---

## 💰 calc_margin_allocation - 保证金分配计算

**接口**: `POST /Strategy/calc_margin`

### 默认参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `app_v` | "2.0.0" | API版本 |
| `leverage` | "1.5" | 杠杆倍数 |
| `long_pct` | "90" | 做多保证金占比 |
| `short_pct` | "20" | 做空保证金占比 |

### 返回数据结构
```json
{
  "status": 1,
  "msg": "success",
  "info": {
    "total_balance": 10000,
    "allocations": {
      "4300": {
        "name": "BTC-风霆V4.2-做多",
        "coin": "BTC", 
        "direction": "做多",
        "percentage": "30",
        "amount": "3000"
      },
      "4679": {
        "name": "ETH-风霆V4.2-做多",
        "coin": "ETH",
        "direction": "做多", 
        "percentage": "25",
        "amount": "2500"
      }
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态 | 1 |
| `msg` | string | 状态消息 | "success" |
| `info` | object | 分配方案信息 | {...} |
| `info.total_balance` | int | 总保证金 | 10000 |
| `info.allocations` | object | 策略分配详情 | {...} |
| `allocations.<id>` | object | 具体策略的分配信息 | {...} |
| `allocations.<id>.name` | string | 策略名称 | "BTC-风霆V4.2-做多" |
| `allocations.<id>.coin` | string | 币种 | "BTC" |
| `allocations.<id>.direction` | string | 方向 | "做多" |
| `allocations.<id>.percentage` | string | 分配比例 | "30" |
| `allocations.<id>.amount` | string | 保证金金额 | "3000" |

### Agent 使用示例
```python
# 按币种分配：BTC 60%, ETH 40%
allocation_rules = {
    "coin_allocation": {"BTC": 60, "ETH": 40}
}

result = calc_margin_allocation(
    token=token, 
    strategy_ids="4300,4679,4680", 
    allocation_rules=allocation_rules,
    total_balance=10000
)

if result.get("status") == 1:
    allocations = result.get("info", {}).get("allocations", {})
    for strategy_id, allocation in allocations.items():
        amount = allocation.get("amount")         # 分配的保证金金额
        percentage = allocation.get("percentage") # 分配的比例
        print(f"策略{strategy_id}: {percentage}% = {amount}保证金")
```

### 支持的分配规则

#### 1. 按币种做多分配
```python
allocation_rules = {
    "coin_long_allocation": {"BTC": 40, "ETH": 30, "SOL": 30}
}
```

#### 2. 按币种做空分配
```python
allocation_rules = {
    "coin_short_allocation": {"BTC": 50, "ETH": 50}
}
```

#### 3. 按方向分配
```python
allocation_rules = {
    "direction_allocation": {"做多": 70, "做空": 30}
}
```

#### 4. 按AI回测时间类型分配（市场行情）
```python
allocation_rules = {
    "ai_time_allocation": {"震荡行情": 60, "趋势行情": 40}
}
```

#### 5. 按策略类型分配
```python
allocation_rules = {
    "strategy_type_allocation": {"风霆": 80, "网格": 20}
}
```

#### 6. 按细分组分配（方向+市场行情组合）
```python
allocation_rules = {
    "sub_group_allocation": {
        "2025年震荡做多": 40,
        "2025年震荡做空": 30, 
        "2024年趋势做多": 20,
        "2024年趋势做空": 10
    }
}
```

#### 7. 复合规则（同时满足多个约束）
```python
allocation_rules = {
    "coin_long_allocation": {"BTC": 40, "ETH": 30, "SOL": 30},
    "coin_short_allocation": {"BTC": 60, "ETH": 40},
    "direction_allocation": {"做多": 70, "做空": 30},
    "ai_time_allocation": {"震荡行情": 60, "趋势行情": 40},
    "sub_group_allocation": {"2025年震荡做多": 35, "2025年震荡做空": 25}
}
```

---

## 🚀 apply_backtest - 启动回测

**接口**: `POST /Backtrack/apply_do`

### 返回数据结构

#### 成功响应
```json
{
  "status": 1,
  "msg": "回测任务已提交",
  "info": {
    "back_id": 5906,
    "id": 5906,
    "status": 1,
    "message": "回测任务排队中"
  }
}
```

#### 错误响应
```json
{
  "status": 0,
  "msg": "参数错误：策略ID不存在",
  "info": null
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 请求状态（1=成功, 0=失败） | 1 |
| `msg` | string | 状态消息 | "回测任务已提交" |
| `info` | object | 回测任务信息 | {...} |
| `info.back_id` | int | **回测任务ID**（主要ID） | 5906 |
| `info.id` | int | 任务ID（同back_id） | 5906 |
| `info.status` | int | 任务状态（1=排队,2=运行中,3=完成,4=失败） | 1 |
| `info.message` | string | 任务状态描述 | "回测任务排队中" |

### ⚠️ 重要提醒
- **back_id** 是最重要的字段，用于后续查询回测结果
- **status=1** 表示成功提交，不是完成
- **实际回测需要时间执行**

### Agent 使用示例
```python
result = apply_backtest(token, strategy_id="4300", ...)
if result.get("status") == 1:
    back_id = result.get("info", {}).get("back_id")  # 回测ID
    message = result.get("info", {}).get("message")  # 状态信息
    print(f"✅ 回测已提交，任务ID: {back_id}")
else:
    error = result.get("msg", "未知错误")
    print(f"❌ 回测失败: {error}")
```

---

## 📊 通用响应格式

### 标准成功响应
```json
{
  "status": 1,
  "msg": "success",
  "info": {...}  // 具体数据
}
```

### 标准错误响应
```json
{
  "status": 0,
  "msg": "错误描述",
  "info": null
}
```

### 网络错误响应
```json
{
  "error": "网络连接失败"
}
```

---

## 🎯 Agent 处理建议

### 1. 统一错误检查
```python
def check_response(result):
    if "error" in result:
        return False, result["error"]
    if result.get("status") != 1:
        return False, result.get("msg", "未知错误")
    return True, result.get("info")
```

### 2. 数据提取模式
```python
# 检查响应
ok, data = check_response(result)
if not ok:
    print(f"错误: {data}")
    return

# 安全获取数据
items = data.get("info", []) if isinstance(data, dict) else data
```

### 3. 显示用户友好信息
- 使用 `name` 字段显示给用户
- 使用 `id` 字段进行API调用
- 错误时显示 `msg` 内容

---

## 📝 快速参考

### 常用字段映射

| 业务概念 | API字段 | 用途 |
|----------|---------|------|
| 策略ID | `id` | 回测时使用 |
| 策略名称 | `name` | 显示给用户 |
| 币种 | `coin` | 筛选和分类 |
| 回测ID | `back_id` | 查询回测结果 |
| 策略组ID | `id` | 识别策略组 |

### 状态码含义

| 状态码 | 含义 | 处理方式 |
|--------|------|----------|
| `1` | 成功 | 继续处理数据 |
| `0` | 失败 | 显示错误信息 |
| `"error"` | 网络错误 | 显示连接问题 |

---

## ⚠️ 数据处理优化建议

### 忽略大数据参数
为了节省大模型的上下文窗口，Agent在处理回测结果时应该：

**❌ 应该忽略的参数：**
- `total_stat.net_value` - 数据量大且通常不需要
- `daily_stat` - 详细的每日数据（如果存在）
- `trade_details` - 具体交易记录（如果存在）

**✅ 关注核心指标：**
- `year_rate` - 年化收益率
- `sharp_rate` - 夏普比率  
- `max_loss` - 最大回撤
- `win_rate` - 胜率
- `trade_num` - 交易次数

### Agent 处理建议
```python
# 在处理回测详情时，删除不必要的大数据字段
def clean_backtest_data(data):
    if isinstance(data, dict):
        # 删除total_stat中的net_value
        if 'total_stat' in data and isinstance(data['total_stat'], dict):
            data['total_stat'].pop('net_value', None)
        
        # 删除其他大数据字段
        data.pop('daily_stat', None)
        data.pop('trade_details', None)
    
    return data
```

---

*本文档供 Agent 快速理解 API 返回数据，避免重复查询接口文档*