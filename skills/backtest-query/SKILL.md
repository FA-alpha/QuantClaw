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

### 语义识别（关键词映射）

**触发策略组合推荐的关键词**：
- **组合类**：策略组、回测组、组合、投资组合、策略组合
- **推荐类**：推荐、建议、帮我选、怎么配、配置
- **多策略**：多策略、多个策略、组合策略、配对、对冲

**示例：**
```
用户说                    → Agent 理解
────────────────────────────────────────────
"帮我推荐个回测组"        → 策略组合推荐
"BTC 有什么好的组合？"    → BTC 策略组合推荐
"多策略对冲配置"          → 多策略组合（含多空）
"建议几个策略组"          → 策略组合推荐
"怎么配置投资组合？"      → 策略组合推荐
```

**判断逻辑**：
1. 包含上述关键词 → 使用 `smart_group_recommend.py`
2. 明确说单个策略 → 使用 `query.py --list-strategies` 或 `--query-backtest`
3. 不确定 → 优先推荐组合（更符合量化思维）

---

### 参数识别规则

**时间识别**：
```
"最近30天"  → --ai-time-ids 1
"最近7天"   → --ai-time-ids 2
"最近90天"  → --ai-time-ids 3
"最近180天" → --ai-time-ids 4
```

**版本号处理**：
```
❌ 错误：用户说 "V4.3" → 传 --versions "4.3,4.31,4.32,4.33"
✅ 正确：用户说 "V4.3" → 传 --versions "4.3"

规则：不要自动扩展版本号！用户说什么就传什么。
```

**方向映射使用**：
```
用户说："2个BTC做多, 2个BTC做空, 2个SOL做多"

✅ 正确方案（使用映射）：
--strategy-direction-map '{"11": {"BTC": ["long", "short"], "SOL": ["long"]}}'
--top-per-group 2  （每个方向取2个）

❌ 错误方案（全局方向）：
--directions "long,short"  （无法精确控制每个币种）
```

**数量控制**：
- `--top-per-group N` - 每个"币种+方向"组合取 N 个策略
- `--max-combinations 1` - 只返回1个最优组合

---

### 参数选择

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

# 7. 精确方向+数量控制（用户案例）
# 用户说："创建回测组，风霆V4.3，最近30天收益最高，2个BTC做多+2个BTC做空+2个SOL做多+2个SOL做空+2个ETH做多"
--query "风霆V4.3策略组，最近30天高收益" \
--coins "BTC,SOL,ETH" \
--strategy-types "11" \
--versions "4.3" \
--ai-time-ids "1" \
--strategy-direction-map '{"11": {"BTC": ["long", "short"], "SOL": ["long", "short"], "ETH": ["long"]}}' \
--top-per-group 2 \
--max-combinations 1 \
--api-sort 2

# 说明：
# - versions "4.3" 不扩展（用户说4.3就只查4.3）
# - ai-time-ids "1" = 最近30天
# - strategy-direction-map 明确每个币的方向
# - top-per-group 2 = 每个"币种+方向"取2个
# - api-sort 2 = 按收益排序
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
