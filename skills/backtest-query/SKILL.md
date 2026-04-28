# 回测数据查询与策略组合

查询 AI 回测数据，智能推荐策略组合，创建策略组。

---

## 🎯 主要功能

1. **智能推荐** - 根据需求推荐优质策略组合
2. **创建策略组** - 将策略组合成一个策略组

---

## 📝 使用流程

### 步骤 1：判断用户意图

**创建关键词**：创建、建立、建个、生成

- 包含 → 推荐后**直接创建**
- 不包含 → 推荐后**询问确认**

### 步骤 2：执行推荐

```bash
cd /home/ubuntu/work/QuantClaw
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求描述" \
  --output /tmp/recommend.json
```

**常用参数**：
- `--coins "BTC,ETH"` - 币种
- `--min-total-win-rate 60` - 最小胜率
- `--max-recent-drawdown 15` - 最大回撤

### 步骤 3：读取推荐结果

JSON 文件包含：
- `combinations[0]` - 最优组合
- `combinations[0]['strategies'][*]['strategy_token']` - token 列表
- `combinations[0]['score']` - 评分
- `combinations[0]['expected_return']` - 预期收益

### 步骤 4：创建策略组

从 JSON 提取 token 列表，执行创建：

```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名称" \
  --strategy-tokens "token1,token2,token3"
```

---

## 💡 完整示例

**用户**："帮我找 BTC 优质策略并创建组合"

**执行**：
```bash
# 1. 推荐
cd /home/ubuntu/work/QuantClaw
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC优质策略" \
  --coins "BTC" \
  --output /tmp/rec.json

# 2. 读取 JSON 提取 tokens
# (用 read 或 exec cat + jq)

# 3. 创建
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC优质组合_$(date +%Y%m%d)" \
  --strategy-tokens "提取的tokens"
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
- 马丁策略：名称含"风霆"
- 网格策略：strategy_type=7
- 趋势策略：如"鲲鹏"
