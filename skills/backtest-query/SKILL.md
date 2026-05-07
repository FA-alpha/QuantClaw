# 回测数据查询与策略组合

智能推荐策略组合并创建策略组。

---

## 快速开始

### 命令格式

```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  [参数选项...]
```

 **创建判断（3条铁律）**：                                                                                                                                                    
                                                                                                                                                                                
   1. **明确说"创建/建立/生成"** → 推荐后自动创建                                                                                                                               
   2. **只说"推荐/查询/看看"** → 展示结果 + 问"是否创建？"                                                                                                                      
   3. **不确定** → 展示结果 + 问用户                                                                                                                                            
                                                                                                                                                                                
   **默认原则**：有疑问就问，别自己猜。   

---

## 参数速查

### 基础参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--query` | 用户需求描述 | **必填** |
| `--coins` | 币种（逗号分隔） | 查询所有 |
| `--strategy-types` | 策略类型ID（逗号分隔） | 查询所有 |
| `--ai-time-ids` | 时间ID（逗号分隔） | 查询所有 |
| `--versions` | 版本号（逗号分隔） | 查询所有 |
| `--directions` | 方向 | 类型1,7,11自动轮询long/short |
| `--search-pcts` | 比例（逗号分隔） | BTC:10-120, 其他:60-140 |

### 映射参数（🔥 多策略不同配置时使用）

| 参数 | 格式 | 说明 |
|------|------|------|
| `--strategy-version-map` | JSON 对象 | 按策略指定版本 |
| `--strategy-direction-map` | JSON 对象 | 按策略指定方向 |
| `--coin-pct-map` | JSON 对象 | 按币种指定比例 |

**映射格式**：
```json
{
  "11": ["4.3", "4.4"],                          // 简化格式：版本号
  "7": [{"version": "3.2", "leverage": 10}],     // 完整格式：包含杠杆
  "1": null                                       // null：自动查询
}
```

### 筛选参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--min-total-win-rate` | 最小总胜率（%） | `60` |
| `--min-recent-profit-rate` | 最小近期收益率（%） | `10` |
| `--max-recent-drawdown` | 最大近期回撤（%） | `15` |
| `--min-trade-count` | 最小交易次数 | `50` |
| `--top-per-group` | 每种排序取几个 | `5` |
| `--max-combinations` | 最多推荐几个组合 | `10` |

### 并行查询参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-workers` | 10 | 并发线程数（5-20） |
| `--max-qps` | 20 | 每秒最大查询数 |
| `--retry-times` | 3 | 失败重试次数 |
| `--quiet` | False | 静默模式 |

**性能**：并行查询提速 **4-10 倍**（300 组合：60s → 15s）

---

## Agent 决策

**参数选择**：
- 不同策略不同参数 → 用 `--strategy-version-map`
- 需要指定 leverage → 用完整格式 `{"version": "4.3", "leverage": 3}`
- 只指定版本号 → 用简化格式 `["4.3", "4.4"]`（自动获取所有配置）
- 所有策略相同参数 → 用全局参数 `--versions`

**传参原则**：
- 用户明确说的 → 传入
- 用户没说的 → 不传（自动查询）

**优先级**：映射参数 > 全局参数 > 自动查询

---

## 典型场景

```bash
# 1. 简单需求
--query "推荐 BTC 策略" --coins "BTC"

# 2. 多空对冲
--query "BTC 对冲" --coins "BTC" --directions "long,short"

# 3. 高质量筛选
--query "高质量策略" --min-total-win-rate 65 --max-recent-drawdown 10

# 4. 多策略不同版本
--query "BTC风霆v4.3/4.4, ETH网格v3.2" \
--coins "BTC,ETH" --strategy-types "11,7" \
--strategy-version-map '{"11": ["4.3","4.4"], "7": ["3.2"]}'

# 5. 精确控制杠杆
--query "BTC风霆v4.3 3倍杠杆" --coins "BTC" --strategy-types "11" \
--strategy-version-map '{"11": [{"version":"4.3","leverage":3}]}'

# 6. 大规模查询
--query "主流币马丁" --coins "BTC,ETH,SOL,BNB" --strategy-types "1,11" \
--max-workers 20 --max-qps 50
```

---

## 返回结果

```json
{
  "error": "错误信息（如有）",
  "combinations": [
    {
      "score": 85.5,
      "expected_return": 95.2,
      "portfolio_risk": {"max_drawdown": 11.5},
      "strategies": [
        {"strategy_token": "token123", "coin": "BTC", "name": "风霆_做多"}
      ]
    }
  ]
}
```

**提取策略 tokens**：
```python
if "error" in result:
    return result["error"]

tokens = [s["strategy_token"] for s in result["combinations"][0]["strategies"]]
```

**创建策略组**：
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名" \
  --strategy-tokens "token1,token2,token3"
```

---

## 查询可用参数

```bash
python3 skills/backtest-query/query.py --list-coins       # 币种
python3 skills/backtest-query/query.py --list-strategies  # 策略类型（返回 id, name, versions）
python3 skills/backtest-query/query.py --list-ai-times    # 时间ID
```

---

## 常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| `无法自动获取 token` | 不在用户 workspace | 检查执行路径 |
| `未查询到任何策略` | 筛选条件太严格 | 放宽条件 |
| `重试N次失败: timeout` | API 超时 | 增加 `--retry-times` 或降低 `--max-qps` |
| 大量查询失败 | 触发 API 限流 | 降低 `--max-qps` (如改为 10) |
| `策略 X 没有版本 Y` | 版本不存在 | 先查询可用版本 |

---

## 注意事项

- **参数依赖**: versions依赖strategy-types，directions仅1/7/11需要，search-pcts依赖coins
- **并行查询**: 默认配置适合大多数场景，遇限流降低 `--max-qps`
- **只传明确参数**: 用户说的传入，没说的不传（自动查询）
