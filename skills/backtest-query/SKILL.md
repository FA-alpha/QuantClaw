# 回测数据查询与策略组合

智能推荐策略组合并创建策略组。

---

## 使用流程

### 1. 推荐策略

```bash
cd /home/ubuntu/work/QuantClaw
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

| 参数 | 说明 | 示例 |
|------|------|------|
| `--coins` | 币种（逗号分隔） | `"BTC,ETH,SOL"` |
| `--strategy-types` | 策略类型ID（逗号分隔） | `"1,11"` |
| `--directions` | 方向 | `"long,short"` |
| `--search-pcts` | 网格比例（逗号分隔） | `"80,100,120"` |
| `--ai-time-ids` | 时间ID（逗号分隔） | `"5,6"` |
| `--versions` | 版本号（逗号分隔） | `"4.2,4.3"` |
| `--version-configs` | 版本配置对象数组（JSON） | 见下方说明 |
| `--search-recommand-type` | 推荐类型 | `1`（推荐）/ `2`（交易中） |

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
cd /home/ubuntu/work/QuantClaw/skills/backtest-query

# 查看可用币种
python3 query.py --list-coins

# 查看策略类型
python3 query.py --list-strategies

# 查看时间ID
python3 query.py --list-ai-times
```

### 根据用户需求筛选

**示例1：用户说"马丁策略"**
1. 查询策略列表 → 找到包含"风霆"的策略
2. 提取策略类型ID（如 `1, 11`）
3. 构建参数：`--strategy-types "1,11"`

**示例2：用户说"所有虚拟货币"**
1. 查询币种列表 → 筛选 `type="CRYPTO"` 的币种
2. 提取币种代码（如 `BTC,ETH,SOL,...`）
3. 构建参数：`--coins "BTC,ETH,SOL,..."`

**示例3：用户说"主流币"**
- 根据常识筛选：`BTC,ETH,SOL,BNB`

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
python3 smart_group_recommend.py \
  --query "BTC 风霆v4.3" \
  --coins "BTC" \
  --strategy-types "11" \
  --version-configs '[{"version":4.3,"leverage":3,"search_extend":"3w"},{"version":4.3,"leverage":1.5,"search_extend":"3w"}]'
```

**说明**：
- `version-configs` 优先于 `--versions` 参数
- 每个配置对象包含：`version`（版本号）、`leverage`（杠杆）、`search_extend`（扩展参数）
- 系统会对每个配置进行轮询查询并去重合并

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
# 1. 对冲组合（多空）
--coins "BTC" --directions "long,short"

# 2. 币种分散
--coins "BTC,ETH,SOL" --directions "long"

# 3. 马丁策略
--strategy-types "1,11"

# 4. 高质量策略
--min-total-win-rate 65 --max-recent-drawdown 10 --min-trade-count 100
```
