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
| `--directions` | 方向 | 类型1,7,11自动轮询long/short |
| `--search-pcts` | 比例（逗号分隔） | BTC:10-120, 其他:60-140 |

### 映射参数（🔥 多策略不同配置时使用）

| 参数 | 格式 | 说明 |
|------|------|------|
| `--strategy-version-map` | JSON 对象 | 按策略类型指定版本 |
| `--strategy-direction-map` | JSON 对象 | 按策略类型指定方向 |
| `--coin-pct-map` | JSON 对象 | 按币种指定比例 |

**映射格式**：
```json
// strategy-version-map: 策略类型 → 版本列表
{
  "11": ["4.3", "4.4"],                          // 简化格式：版本号数组
  "7": [{"version": "3.2", "leverage": 10}],     // 完整格式：包含杠杆
  "1": null                                       // null：自动查询所有版本
}

// strategy-direction-map: 策略类型 → 方向列表
{
  "11": ["long", "short"],  // 风霆多空都要
  "7": ["long"],            // 网格只要做多
  "1": null                 // 马丁自动判断
}

// coin-pct-map: 币种 → 比例列表
{
  "BTC": ["80", "100"],
  "ETH": null  // 自动选择
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

**时间识别（动态查询）**：
```bash
# ⚠️ 不要硬编码！先查询可用的时间ID
python3 skills/backtest-query/query.py --list-ai-times

# 常见映射（仅供参考，以实际查询为准）：
"最近7天"   → id=2
"最近30天"  → id=3
"最近90天"  → id=1
"最近180天" → id=4
"最近1年"   → id=5
"最近2年"   → id=6

# Agent 流程：
1. 用户提到时间范围 → 先执行 --list-ai-times
2. 从返回结果中匹配对应的 id
3. 传入 --ai-time-ids "id"
```

**版本号处理**：
```
❌ 错误：用户说 "V4.3" → 传 --versions "4.3,4.31,4.32,4.33"
✅ 正确：用户说 "V4.3" → 传 --versions "4.3"

规则：不要自动扩展版本号！用户说什么就传什么。
```

**方向控制限制**：
```
⚠️ strategy-direction-map 格式限制：
  格式：{"strategy_type": ["long", "short"]}
  不支持：{"strategy_type": {"coin": ["long"]}}  # ❌ 不支持按币种细分

用户说："2个BTC做多, 2个BTC做空, 2个SOL做多"

❌ 无法一次实现（不支持按币种指定方向）
✅ 解决方案：
  1. 如果所有币种方向相同 → 一次调用
     --strategy-direction-map '{"11": ["long", "short"]}'
  
  2. 如果不同币种不同方向 → 告知用户当前限制
     "系统暂不支持不同币种指定不同方向，建议统一方向或分批查询"
```

**数量控制**：
- `--top-per-group N` - 每个"币种+方向"组合取 N 个策略
- `--max-combinations 1` - 只返回1个最优组合

---

### 参数选择

**版本控制（统一使用 strategy-version-map）**：

⚠️ **不要使用全局 `--versions` 参数！** 统一用 `--strategy-version-map`

```bash
# ✅ 正确：用映射控制版本
--strategy-version-map '{"11": ["4.3"], "7": ["3.2"]}'

# ❌ 错误：不要用全局 versions
--versions "4.3,4.4"  # 容易误扩展版本号
```

**格式选择**：
- 只指定版本号 → 简化格式 `["4.3"]`（自动获取所有配置）
- 需要指定 leverage → 完整格式 `[{"version": "4.3", "leverage": 3}]`
- 不指定版本 → 传 `null`（自动查询所有版本）

**传参原则**：
- 用户明确说的 → 精确传入
- 用户没说的 → 传 `null`（自动查询）
- **版本号不扩展**：用户说 "V4.3" 就传 `["4.3"]`，不要自动加 4.31、4.32

**示例**：
```json
{
  "11": ["4.3"],              // 风霆只查 4.3 版本
  "7": null,                  // 网格查所有版本
  "1": [{"version": "2.1", "leverage": 5}]  // 马丁 2.1 版本 5 倍杠杆
}
```

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
--query "BTC风霆v4.3 3倍杠杆" \
--coins "BTC" \
--strategy-types "11" \
--strategy-version-map '{"11": [{"version":"4.3","leverage":3}]}'

# 6. 大规模查询（不限版本）
--query "主流币马丁" \
--coins "BTC,ETH,SOL,BNB" \
--strategy-types "1,11" \
--strategy-version-map '{"1": null, "11": null}' \
--max-workers 20 --max-qps 50

# 7. 精确方向+数量控制（用户案例）
# 用户说："创建回测组，风霆V4.3，最近30天收益最高，2个BTC做多+2个BTC做空+2个SOL做多+2个SOL做空+2个ETH做多"

# 步骤1: 查询时间ID
python3 skills/backtest-query/query.py --list-ai-times
# 找到 "3 - 最近30天"

# 步骤2: 执行推荐
--query "风霆V4.3策略组，最近30天高收益" \
--coins "BTC,SOL,ETH" \
--strategy-types "11" \
--strategy-version-map '{"11": ["4.3"]}' \
--ai-time-ids "3" \
--strategy-direction-map '{"11": ["long", "short"]}' \
--top-per-group 2 \
--max-combinations 1 \
--api-sort 2

# 说明：
# - strategy-version-map '{"11": ["4.3"]}' 不扩展（用户说4.3就只传4.3）
# - ai-time-ids "3" = 最近30天（从 --list-ai-times 查询得到）
# - strategy-direction-map '{"11": ["long", "short"]}' 所有币种都做多做空
# - top-per-group 2 = 每个"币种+方向"取2个
# - api-sort 2 = 按收益排序
# 
# ⚠️ 注意：strategy-direction-map 不支持按币种细分方向！
#    所有币种会使用相同的方向设置
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

**⚠️ 重要：涉及以下参数时必须先查询，不要硬编码！**

```bash
# 1. 币种列表
python3 skills/backtest-query/query.py --list-coins

# 2. 策略类型（返回 id, name, versions）
python3 skills/backtest-query/query.py --list-strategies

# 3. 时间ID（AI 回测时间范围）
python3 skills/backtest-query/query.py --list-ai-times
```

**Agent 工作流：**
```
用户提到 "最近30天"
    ↓
1. 执行 --list-ai-times
2. 找到 "3 - 最近30天"
3. 传参 --ai-time-ids "3"

❌ 不要直接硬编码 --ai-time-ids "3"
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
