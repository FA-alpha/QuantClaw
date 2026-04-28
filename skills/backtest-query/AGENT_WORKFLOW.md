# Agent 工作流程指南

## 📊 智能推荐 → 创建策略组完整流程

当用户请求策略推荐并创建组合时，按以下步骤操作：

---

## 🔄 标准流程

### 1️⃣ 理解用户需求

**用户可能的表述**：
- "帮我找 BTC 和 ETH 的优质策略，并创建组合"
- "推荐一些低风险策略，然后帮我建个策略组"
- "给我找做多做空各一个，创建对冲组合"

**关键识别点**：
- ✅ 需要推荐策略 → 使用 `smart_group_recommend.py`
- ✅ 需要创建策略组 → 后续使用 `query.py --create-group`

---

### 2️⃣ 执行智能推荐

```bash
cd /home/ubuntu/work/QuantClaw

python3 skills/backtest-query/smart_group_recommend.py \
  --query "<用户需求描述>" \
  [可选参数]
```

**常用可选参数**：
- `--coins "BTC,ETH"` - 指定币种
- `--min-total-win-rate 60` - 最低胜率
- `--max-recent-drawdown 15` - 最大回撤
- `--top-per-group 3` - 每组取几个
- `--max-combinations 5` - 最多推荐几个组合

**输出内容**：
- 推荐的组合列表
- 每个组合的详细信息
- **🔧 自动生成的创建命令**

---

### 3️⃣ 提取创建命令

从智能推荐的输出中找到：

```
🔧 创建命令:
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "智能组合_1_20260428" \
  --strategy-tokens "st_xxx,st_yyy,st_zzz"
```

**关键字段**：
- `--group-name` - 组合名称（自动生成，可修改）
- `--strategy-tokens` - 策略 token 列表（自动提取）

---

### 4️⃣ 询问用户确认

**推荐话术**：

> 📊 我为您找到了 X 个优质策略组合。
> 
> **推荐组合 #1**：
> - 评分: XX.X
> - 预期收益: XX.X%
> - 组合回撤: XX.X%
> - 包含策略: X 个
> 
> 我可以帮您创建这个组合吗？
> 
> 可选操作：
> 1. ✅ 创建组合 #1
> 2. 🔍 查看其他组合
> 3. ✏️ 修改组合名称
> 4. ❌ 取消

---

### 5️⃣ 执行创建命令

**用户确认后**，执行提取的命令：

```bash
cd /home/ubuntu/work/QuantClaw

python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "<用户确认或修改的名称>" \
  --strategy-tokens "<自动提取的 tokens>"
```

**注意**：
- 如果用户要修改名称，替换 `--group-name` 参数
- `--strategy-tokens` 不要修改（从推荐结果自动提取）

---

### 6️⃣ 反馈结果

**成功时**：
```
✅ 策略组创建成功！

组合名称: XXX
策略组 ID: 12345
包含策略: X 个

您可以在平台上查看和管理这个策略组。
```

**失败时**：
```
❌ 创建失败: <错误信息>

可能原因：
- Token 无效或过期
- 策略 token 不存在
- 网络连接问题

建议：<具体建议>
```

---

## ⚠️ 常见问题处理

### 问题 1：推荐结果中没有创建命令

**原因**：策略数据缺少 `strategy_token` 字段

**处理**：
```
⚠️ 部分策略缺少必要信息，无法自动创建组合。

建议：
1. 尝试调整筛选条件重新推荐
2. 或者手动查询策略详情获取 token
```

### 问题 2：用户要求修改组合内容

**场景**：用户说"把第二个策略换成另一个"

**处理**：
1. 重新执行智能推荐（调整参数）
2. 或者让用户提供具体策略的 `strategy_token`
3. 手动组合 token 列表执行创建

### 问题 3：用户要创建多个组合

**处理**：
```bash
# 依次执行多个创建命令
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合1" \
  --strategy-tokens "..."

python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合2" \
  --strategy-tokens "..."
```

---

## 📋 完整对话示例

**用户**："帮我找 BTC 和 ETH 的低风险策略，创建一个对冲组合"

**Agent**：
```
收到！我将为您查找 BTC 和 ETH 的低风险策略。

[执行智能推荐]

📊 推荐结果：

--- 组合 #1 ---
评分: 87.3
预期收益: 95.2%
组合回撤: 11.5%
策略数量: 3

策略列表:
1. BTC / 鲲鹏_BTC_做多 (年化102%, 夏普2.35, 胜率68.5%)
2. ETH / 风霆_ETH_做空 (年化88%, 夏普2.10, 胜率65.2%)
3. BTC / 网格_BTC_震荡 (年化76%, 夏普2.50, 胜率72.1%)

这个组合实现了多空对冲，风险较低。我可以帮您创建吗？
```

**用户**："好的，创建吧"

**Agent**：
```
正在创建策略组...

[执行创建命令]

✅ 策略组创建成功！

组合名称: 智能组合_1_20260428
策略组 ID: 12345
包含策略: 3 个

您可以在平台的"策略组管理"中查看和编辑这个组合。
```

---

## 🎯 最佳实践

1. **始终先推荐，后创建** - 让用户看到详细信息再确认
2. **清晰展示组合信息** - 收益、风险、策略数量
3. **提供选择** - 如果有多个推荐，让用户选择
4. **确认后再执行** - 避免误操作
5. **反馈详细** - 成功/失败都要给出明确信息

---

## 🔧 调试技巧

### 查看推荐原始数据
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "..." \
  --output /tmp/recommend_result.json

cat /tmp/recommend_result.json | jq '.combinations[0]'
```

### 检查策略 token
```python
# 在 Python 中检查
import json
with open('/tmp/recommend_result.json') as f:
    data = json.load(f)
    for combo in data['combinations']:
        tokens = [s.get('strategy_token') for s in combo['strategies']]
        print(f"组合 tokens: {tokens}")
```

### 测试创建命令
```bash
# 先测试推荐
python3 skills/backtest-query/smart_group_recommend.py \
  --query "测试" --quiet

# 手动创建（如果自动生成失败）
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "测试组合" \
  --strategy-tokens "token1,token2"
```

---

**总结**：整个流程已打通，Agent 只需按照标准流程操作，智能推荐会自动生成创建命令，确保 `strategy_token` 正确传递。
