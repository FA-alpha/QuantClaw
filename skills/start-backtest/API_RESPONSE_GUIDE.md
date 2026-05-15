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