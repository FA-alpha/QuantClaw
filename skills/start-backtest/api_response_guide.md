# API 响应格式指南

## 回测列表接口 /Backtrack/lists

### 📋 接口基本信息

- **接口路径**: `/Backtrack/lists`
- **请求方法**: POST
- **base URL**: `https://www.fourieralpha.com/Mobile`
- **完整URL**: `https://www.fourieralpha.com/Mobile/Backtrack/lists`

### 🔧 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `usertoken` | string | ✅ 是 | 用户认证token |
| `back_id` | string | ❌ 否 | 回测ID，不传则查询所有回测记录 |
| `limit` | int | ❌ 否 | 返回条数限制，默认返回所有 |
| `offset` | int | ❌ 否 | 偏移量，用于分页 |

### 📊 响应格式

#### 成功响应示例
```json
{
  "status": 1,
  "info": [
    {
      "back_id": "5745",
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

#### 错误响应示例
```json
{
  "status": 0,
  "info": "Token验证失败"
}
```

### 🏷️ 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `status` | int | 响应状态：1=成功，0=失败 |
| `info` | array/string | 成功时为回测列表数组，失败时为错误信息字符串 |

#### 回测记录字段详解

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `back_id` | string | 回测ID | "5745" |
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

### 📊 状态码对照表

| 状态码 | 状态名称 | 描述 |
|--------|----------|------|
| "1" | 排队中 | 回测任务已提交，等待执行 |
| "2" | 运行中 | 回测正在执行中 |
| "3" | 成功 | 回测已完成，可查看结果 |
| "4" | 失败 | 回测执行失败 |

### 🎯 使用示例

#### 查询单个回测记录
```bash
curl -X POST "https://www.fourieralpha.com/Mobile/Backtrack/lists" \
  -d "usertoken=your_token_here" \
  -d "back_id=5745"
```

#### 查询所有回测记录
```bash
curl -X POST "https://www.fourieralpha.com/Mobile/Backtrack/lists" \
  -d "usertoken=your_token_here"
```

#### 分页查询
```bash
curl -X POST "https://www.fourieralpha.com/Mobile/Backtrack/lists" \
  -d "usertoken=your_token_here" \
  -d "limit=10" \
  -d "offset=0"
```

### ⚠️ 注意事项

1. **Token认证**: 所有请求必须包含有效的usertoken
2. **空结果**: 当查询的back_id不存在时，info字段为空数组 `[]`
3. **运行中状态**: 状态为"1"或"2"时，收益相关字段可能为空字符串
4. **时间格式**: 所有时间字段格式为 "YYYY-MM-DD HH:mm:ss" 或 "YYYY-MM-DD"