# 回测数据查询与策略组合

智能推荐策略组合并创建策略组。

---

## 使用流程

### 1. 推荐策略

```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  --coins "BTC,ETH" \
  --directions "long,short" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15 \
  --output /tmp/rec_$(date +%s).json
```

**判断是否直接创建**：
- 用户说"创建"/"建立"/"生成" → 推荐后直接创建
- 否则 → 推荐后询问确认

### 2. 提取并创建

```bash
# 提取 tokens
TOKENS=$(python3 -c "
import json
with open('/tmp/rec_*.json') as f:
    data = json.load(f)
if 'error' in data:
    print('ERROR:' + data['error'])
    exit(1)
tokens = [s['strategy_token'] for s in data['combinations'][0]['strategies']]
print(','.join(tokens))
")

# 创建策略组
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名_$(date +%Y%m%d)" \
  --strategy-tokens "$TOKENS"
```

---

## 参数说明

### 查询范围

| 参数 | 说明 | 示例 | 依赖关系 | 未传时行为 |
|------|------|------|---------|-----------|
| `--coins` | 币种（逗号分隔） | `"BTC,ETH,SOL"` | 独立 | 查询所有可用币种 |
| `--strategy-types` | 策略类型ID（逗号分隔） | `"1,11"` | 独立 | 查询所有策略类型 |
| `--ai-time-ids` | 时间ID（逗号分隔） | `"5,6"` | 独立 | 查询所有时间ID |
| `--versions` | 版本号（逗号分隔） | `"4.2,4.3"` | **依赖 strategy-types** | 自动提取该策略的所有版本 |
| `--directions` | 方向 | `"long,short"` | **依赖 strategy-types** | 类型 1,7,11 轮询 long/short，其他不传 |
| `--search-pcts` | 网格比例（逗号分隔） | `"80,100,120"` | **依赖 coins** | BTC: 10~120，其他: 60~140 |
| `--version-configs` | 版本配置对象数组（JSON） | 见下方说明 | 优先级最高 | - |
| `--search-recommand-type` | 推荐类型 | `1`（推荐）/ `2`（交易中） | 独立 | 默认 1 |

#### 重要：参数依赖关系

参数之间存在依赖关系，系统会智能处理：

**1. versions 依赖 strategy-types**
- 每个策略类型有不同的版本列表
- 未传 `--versions` 时，自动从 `get_ai_strategy_list` 中提取该策略的所有版本
- 如果策略没有 `versions` 字段，则不传 version 参数

**2. directions 依赖 strategy-types**
- 仅策略类型 **1, 7, 11** 需要传方向
- 未传 `--directions` 时：
  - 类型 1,7,11 → 自动轮询 `["long", "short"]`
  - 其他类型 → 不传 direction 参数
- 已传 `--directions` 时：使用指定值

**3. search-pcts 依赖 coins**
- BTC 有特殊比例配置：`['10', '20', '30', '40', '50', '60', '80', '100', '120']`
- 其他币种通用比例：`['60', '80', '100', '120', '140']`
- 未传 `--search-pcts` 时自动根据币种选择

### 筛选条件

| 参数 | 说明 | 示例 |
|------|------|------|
| `--min-total-win-rate` | 最小总胜率（%） | `60` |
| `--min-recent-profit-rate` | 最小近期收益率（%） | `10` |
| `--max-recent-drawdown` | 最大近期回撤（%） | `15` |
| `--min-trade-count` | 最小交易次数 | `50` |
| `--min-stability` | 最小稳定性 | `0.8` |

### 排序和组合

| 参数 | 说明 | 示例 |
|------|------|------|
| `--top-per-group` | 每种排序取几个 | `5` |
| `--sort-methods` | 排序方式（逗号分隔） | `"sharpe,return,drawdown"` |
| `--api-sort` | API排序类型 | `2`（收益）/ `3`（夏普）/ `4`（回撤） |
| `--max-combinations` | 最多推荐几个组合 | `10` |
| `--quiet` | 静默模式 | 不输出详细过程 |

---

## 查询可用参数

在构建查询前，先获取最新的可用参数：

```bash
# 查看可用币种
python3 skills/backtest-query/query.py --list-coins

# 查看策略类型
python3 skills/backtest-query/query.py --list-strategies

# 查看时间ID
python3 skills/backtest-query/query.py --list-ai-times
```

### 根据用户需求筛选

**示例1：用户说"马丁策略"**
1. 查询策略列表 → 找到包含"风霆"的策略
2. 提取策略类型ID（如 `1, 11`）
3. 构建参数：`--strategy-types "1,11"`
4. ✅ **无需传 `--versions`**，系统会自动提取所有版本
5. ✅ **无需传 `--directions`**，系统会自动轮询 long/short

**示例2：用户说"所有虚拟货币"**
1. 查询币种列表 → 筛选 `type="CRYPTO"` 的币种
2. 提取币种代码（如 `BTC,ETH,SOL,...`）
3. 构建参数：`--coins "BTC,ETH,SOL,..."`
4. ✅ **无需传 `--search-pcts`**，系统会根据币种自动选择比例

**示例3：用户说"主流币"**
- 根据常识筛选：`BTC,ETH,SOL,BNB`
- 或者直接**不传 `--coins`**，系统会查询所有币种

**示例4：用户说"BTC 做多"**
- 只需传：`--coins "BTC" --directions "long"`
- ✅ **无需传 `--strategy-types`**，系统会查询所有策略类型
- ✅ **无需传 `--versions`**，系统会自动提取所有版本

### 🎯 推荐实践：只传用户明确指定的参数

由于系统会自动处理参数依赖关系，建议：
- **只传用户明确指定的参数**
- 其他参数留空，让系统自动查询和组合
- 这样可以获得更全面的推荐结果

### 版本配置对象（version-configs）

当用户指定特定版本时（如"风霆v4.3"），需要传入版本配置对象数组。

**工作流程**：
```python
# 1. 查询策略类型的版本列表
from query import get_ai_strategy_list
result = get_ai_strategy_list(token)
strategies = result['info']

# 2. 找到目标策略（如风霆V4，strategy_type=11）
feng_ting_v4 = [s for s in strategies if s['id'] == 11][0]

# 3. 筛选匹配的版本（如 version=4.3）
v43_configs = [v for v in feng_ting_v4['versions'] if v['version'] == 4.3]
# 结果: [
#   {"version": 4.3, "leverage": 3, "search_extend": "3w"},
#   {"version": 4.3, "leverage": 1.5, "search_extend": "3w"}
# ]

# 4. 转为 JSON 并传入参数
import json
configs_json = json.dumps(v43_configs)
```

**命令示例**：
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC 风霆v4.3" \
  --coins "BTC" \
  --strategy-types "11" \
  --version-configs '[{"version":4.3,"leverage":3,"search_extend":"3w"},{"version":4.3,"leverage":1.5,"search_extend":"3w"}]'
```

**说明**：
- `version-configs` 优先于 `--versions` 参数
- 配置对象结构**动态根据 API 返回**（直接使用 `versions` 数组中的对象）
- 系统会提取对象中的所有字段作为查询参数（version、leverage、search_extend 等）
- 对每个配置进行轮询查询并去重合并

---

## JSON 结构

```json
{
  "error": "错误信息（如有）",
  "combinations": [
    {
      "score": 85.5,
      "expected_return": 95.2,
      "portfolio_risk": {"max_drawdown": 11.5},
      "strategies": [
        {
          "strategy_token": "token123",
          "coin": "BTC",
          "name": "风霆_做多",
          "year_rate": 102,
          "sharp_rate": 2.35
        }
      ]
    }
  ]
}
```

**提取路径**：
- 检查错误：`error` 字段
- 最优组合：`combinations[0]`
- 策略 tokens：`combinations[0].strategies[].strategy_token`

---

## 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `无法自动获取 token` | 不在用户 workspace | 确保在正确路径执行 |
| `未查询到任何策略` | 筛选条件太严格 | 放宽条件或扩大范围 |
| `策略数量不足` | 少于2个策略 | 降低筛选标准 |
| `API 请求失败` | 网络问题 | 检查网络或稍后重试 |
| 创建失败 | token 格式/策略不存在 | 重新推荐获取最新 tokens |

---

## 快速参考

### 典型场景

```bash
# 1. 对冲组合（BTC 多空）
# ✅ 只传币种和方向，其他参数自动查询
--query "BTC 对冲组合" \
--coins "BTC" \
--directions "long,short"

# 2. 币种分散（只做多）
# ✅ 只传币种和方向
--query "多币种分散做多" \
--coins "BTC,ETH,SOL" \
--directions "long"

# 3. 马丁策略（所有币种）
# ✅ 只传策略类型，coins/versions/directions 自动处理
--query "马丁策略推荐" \
--strategy-types "1,11"

# 4. 高质量策略（不限类型、不限币种）
# ✅ 完全依赖自动查询，只设置筛选条件
--query "高质量低回撤策略" \
--min-total-win-rate 65 \
--max-recent-drawdown 10 \
--min-trade-count 100

# 5. 特定策略版本（风霆 v4.3）
# ✅ 指定策略类型和版本，其他自动
--query "BTC 风霆 v4.3 做多" \
--coins "BTC" \
--strategy-types "11" \
--versions "4.3" \
--directions "long"
```

### ⚠️ 避免过度指定参数

**❌ 不推荐**：全部手动指定
```bash
# 容易遗漏版本、设置错误的方向等
--coins "BTC" \
--strategy-types "11" \
--versions "4.2,4.3,4.4" \
--directions "long,short" \
--search-pcts "80,100,120" \
--ai-time-ids "5,6,7,8"
```

**✅ 推荐**：只传用户明确指定的
```bash
# 系统会自动处理依赖关系
--coins "BTC" \
--strategy-types "11"
# versions/directions/pcts/time_ids 自动查询
```
