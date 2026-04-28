# 回测数据查询与策略组合

查询 AI 回测数据，智能推荐策略组合，创建策略组。

---

## 🎯 主要功能

1. **智能推荐** - 根据需求推荐优质策略组合
2. **创建策略组** - 将策略组合成一个策略组

---

## 📝 使用流程

### 步骤 0：准备工作

**Token 自动获取**：
- `smart_group_recommend.py` 会自动从当前 workspace 匹配用户获取 token
- 无需手动传入 `--token` 参数
- 确保在正确的 workspace 路径下执行

### 步骤 1：判断用户意图

**创建关键词**：创建、建立、建个、生成

- 包含 → 推荐后**直接创建**
- 不包含 → 推荐后**询问确认**

### 步骤 2：执行推荐

```bash
cd /home/ubuntu/work/QuantClaw
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  --output /tmp/quantclaw_recommend_$(date +%s).json
```

**注意**：
- 输出文件使用时间戳避免覆盖
- 脚本会输出推荐摘要到终端
- JSON 文件包含完整的推荐详情

**常用参数**：

**查询范围参数**：
- `--coins "BTC,ETH,SOL"` - 币种列表（逗号分隔）
- `--strategy-types "1,7,11"` - 策略类型（1=风霆 7=网格 11=鲲鹏）
- `--directions "long,short"` - 方向（long=做多 short=做空）
- `--search-pcts "80,100,120"` - 网格比例（仅网格策略）
- `--ai-time-ids "5,6"` - AI回测时间ID
- `--versions "v1,v2"` - 策略版本
- `--search-recommand-type 1` - 推荐类型（1=推荐 2=交易中）

**筛选条件参数**：
- `--min-total-win-rate 60` - 最小总胜率（%）
- `--min-recent-profit-rate 10` - 最小近期收益率（%）
- `--max-recent-drawdown 15` - 最大近期回撤（%）
- `--min-trade-count 50` - 最小交易次数
- `--min-stability 0.8` - 最小稳定性（近期/总体）

**排序和组合参数**：
- `--top-per-group 5` - 每种排序方式取几个策略（默认5）
- `--sort-methods "sharpe,return,drawdown"` - 排序方式（可选：sharpe,return,drawdown,win_rate,stability,score）
- `--api-sort 2` - API排序（1=最新 2=收益 3=夏普 4=回撤，默认2）
- `--max-combinations 10` - 最多推荐几个组合（默认10）

### 步骤 3：读取推荐结果

**检查推荐是否成功**：
```bash
# 使用 read 工具读取 JSON 文件
# 检查是否包含 "error" 字段
```

**JSON 结构**：
- `error` - 如果存在说明推荐失败
- `combinations` - 推荐的策略组合列表（按评分排序）
- `combinations[0]` - 最优组合（第一个）
  - `score` - 组合评分
  - `expected_return` - 预期收益率（%）
  - `portfolio_risk.max_drawdown` - 组合最大回撤（%）
  - `strategies` - 策略列表
    - `strategy_token` - 策略 token（创建时需要）
    - `coin` - 币种
    - `name` - 策略名称
    - `year_rate` - 年化收益率
    - `sharp_rate` - 夏普率

### 步骤 4：提取策略 Token

**方法 1：使用 Python**（推荐）
```python
import json

with open('/tmp/quantclaw_recommend_*.json') as f:
    data = json.load(f)

# 检查错误
if 'error' in data:
    print(f"推荐失败: {data['error']}")
    exit(1)

# 提取第一个组合的 tokens
best_combo = data['combinations'][0]
tokens = [s['strategy_token'] for s in best_combo['strategies']]
tokens_str = ','.join(tokens)

print(f"策略数量: {len(tokens)}")
print(f"Tokens: {tokens_str}")
```

**方法 2：使用 jq**
```bash
# 提取第一个组合的所有 strategy_token
jq -r '.combinations[0].strategies[].strategy_token' /tmp/quantclaw_recommend_*.json | paste -sd ','
```

### 步骤 5：创建策略组

```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名称_$(date +%Y%m%d)" \
  --strategy-tokens "提取的tokens字符串"
```

**检查创建结果**：
- 成功：返回策略组 ID
- 失败：返回错误信息

---

## 💡 完整示例

**用户**："帮我找 BTC 和 ETH 的多空策略并创建组合"

**执行**：
```bash
# 1. 推荐（轮询查询 2×2 = 4 次并去重）
cd /home/ubuntu/work/QuantClaw
OUTPUT_FILE="/tmp/quantclaw_rec_$(date +%s).json"

python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC和ETH的多空策略" \
  --coins "BTC,ETH" \
  --directions "long,short" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15 \
  --output "$OUTPUT_FILE"

# 2. 读取 JSON 并提取 tokens
TOKENS=$(python3 -c "
import json
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
if 'error' in data:
    print('ERROR:' + data['error'])
    exit(1)
tokens = [s['strategy_token'] for s in data['combinations'][0]['strategies']]
print(','.join(tokens))
")

# 检查是否成功
if [[ "$TOKENS" == ERROR:* ]]; then
    echo "推荐失败: ${TOKENS#ERROR:}"
    exit 1
fi

echo "提取到 tokens: $TOKENS"

# 3. 创建策略组
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC_ETH多空组合_$(date +%Y%m%d)" \
  --strategy-tokens "$TOKENS"
```

**回复用户**：
```
✅ 策略组创建成功！

组合名称: BTC优质组合_20260428
策略组 ID: 12345
包含策略: 3 个
预期收益: 95.2%
组合回撤: 11.5%

策略列表:
1. BTC / 鲲鹏_做多 (年化102%, 夏普2.35)
2. BTC / 风霆_做空 (年化88%, 夏普2.10)
3. BTC / 网格_震荡 (年化76%, 夏普2.50)
```

---

## 🔑 关键信息

### 典型场景
- **对冲组合** - 做多 + 做空
- **币种分散** - BTC + ETH + SOL
- **策略混合** - 网格 + 趋势

### 策略类型
- `1`: 风霆（马丁策略）
- `7`: 网格策略
- `11`: 鲲鹏（趋势策略）
- 更多类型可通过 `DefaultParams.get_strategy_types()` 获取

### 参数取值范围获取

在 Python 脚本中可以获取可用参数：

```python
from defaults import DefaultParams

manager = DefaultParams(token)

# 获取可用币种
coins = manager.get_coins()  # 所有币种
crypto_coins = manager.get_coins(coin_type="CRYPTO")  # 仅虚拟币

# 获取策略类型
strategy_types = manager.get_strategy_types()  # [1, 7, 11, ...]

# 获取时间ID
time_ids = manager.get_ai_time_ids()  # ["5", "6", ...]

# 获取网格比例
btc_pcts = manager.get_grid_pcts("BTC")  # ['10', '20', ..., '120']
eth_pcts = manager.get_grid_pcts("ETH")  # ['60', '80', ..., '140']
```

### 轮询查询机制

当传入多个参数值时，系统会轮询查询所有组合并去重合并：

**计算公式**：
```
查询次数 = coins数量 × strategy_types数量 × directions数量 × search_pcts数量 × ai_time_ids数量 × versions数量
```

**示例 1**：
```bash
--coins "BTC,ETH" --directions "long,short"
# 2×2×1×1×1×1 = 4 次查询
```

**示例 2**：
```bash
--coins "BTC,ETH,SOL" --directions "long,short" --search-pcts "80,100,120"
# 3×1×2×3×1×1 = 18 次查询
```

**注意**：
- 去重基于 `back_id`，避免重复策略
- 查询失败时跳过，不影响其他查询
- 最终合并所有成功查询的结果

---

## ⚠️ 错误处理

### 推荐失败常见原因

1. **Token 无效**
   - 错误信息：`无法自动获取 token`
   - 解决方案：确保在正确的用户 workspace 下执行

2. **未查询到策略**
   - 错误信息：`未查询到任何策略`
   - 解决方案：
     - 放宽筛选条件（降低胜率要求、提高回撤限制）
     - 扩大查询范围（增加币种、取消方向限制）

3. **策略数量不足**
   - 错误信息：`策略数量不足，无法形成组合`
   - 解决方案：至少需要 2 个策略才能形成组合

4. **API 请求失败**
   - 错误信息：API 相关错误
   - 解决方案：检查网络连接，稍后重试

### 创建失败常见原因

1. **Token 格式错误**
   - 检查提取的 token 是否正确
   - 确保 token 用逗号分隔

2. **策略不存在**
   - 策略可能已被删除
   - 重新推荐获取最新策略

---

## 💡 使用技巧

### 1. 快速推荐（使用默认参数）
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "优质策略组合" \
  --output /tmp/rec.json
# 不指定参数时会使用合理的默认值
```

### 2. 精细控制（指定多个条件）
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "高胜率低回撤的BTC策略" \
  --coins "BTC" \
  --directions "long,short" \
  --min-total-win-rate 65 \
  --max-recent-drawdown 10 \
  --min-trade-count 100 \
  --top-per-group 3 \
  --output /tmp/rec.json
```

### 3. 静默模式（减少输出）
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "..." \
  --quiet \
  --output /tmp/rec.json
# 只输出关键信息，不显示详细过程
```

### 4. 直接在 Python 中使用
```python
from smart_group_recommend import SmartGroupRecommender

recommender = SmartGroupRecommender(token, verbose=True)
result = recommender.smart_recommend(
    query_text="BTC优质策略",
    strategies=None,  # 或传入预查询的策略列表
    top_per_group=5,
    max_combinations=10
)

if 'error' not in result:
    print(f"推荐了 {len(result['combinations'])} 个组合")
```
