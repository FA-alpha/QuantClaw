# 中英术语对照表

## 必须翻译的常见英文词

### API 响应字段
| 英文 | 中文 |
|------|------|
| status | 状态 |
| success | 成功 |
| failed | 失败 |
| error | 错误 |
| message | 消息 |
| data | 数据 |
| result | 结果 |
| info | 信息 |
| code | 代码/编码 |
| response | 响应 |
| request | 请求 |
| timeout | 超时 |

### 回测相关
| 英文 | 中文 |
|------|------|
| backtest | 回测 |
| strategy | 策略 |
| symbol | 交易对/币种 |
| long | 做多 |
| short | 做空 |
| profit | 盈利 |
| loss | 亏损 |
| balance | 余额 |
| position | 仓位 |
| order | 订单 |
| execute | 执行 |
| pending | 待处理 |
| completed | 已完成 |
| cancelled | 已取消 |

### 技术指标
| 英文 | 中文 |
|------|------|
| return | 收益率 |
| drawdown | 回撤 |
| maxDrawdown | 最大回撤 |
| sharpe ratio | 夏普比率 |
| win rate | 胜率 |
| profit factor | 盈亏比 |
| annual return | 年化收益 |
| volatility | 波动率 |

### 错误类型
| 英文 | 中文 |
|------|------|
| Connection timeout | 连接超时 |
| Invalid parameters | 参数无效 |
| Not found | 未找到 |
| Permission denied | 权限被拒绝 |
| Internal server error | 服务器内部错误 |
| Bad request | 请求错误 |
| Unauthorized | 未授权 |

## 使用场景

**场景1：API 返回原始 JSON**
```json
// ❌ 不要直接输出
{"status": "success", "message": "Order executed"}

// ✅ 应该翻译为
状态：成功
消息：订单已执行
```

**场景2：错误信息**
```
❌ 不要：Error: Connection timeout after 5000ms
✅ 应该：错误：连接超时（5秒后未响应）
```

**场景3：表格展示**
```markdown
❌ 不要：
| strategy | profit | status |
|----------|--------|--------|

✅ 应该：
| 策略名称 | 盈利 | 状态 |
|---------|------|------|
```
