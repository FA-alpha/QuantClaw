# 快速参考卡片

## 🎯 Agent 行为决策树

```
用户输入
    ↓
检测关键词
    ↓
包含"创建"/"建立"？
    ↓                ↓
   YES              NO
    ↓                ↓
推荐 → 创建      推荐 → 询问
    ↓                ↓
展示结果        等待确认 → 创建
```

---

## 📝 创建意图关键词

### 中文
- ✅ 创建
- ✅ 建立
- ✅ 建个
- ✅ 生成
- ✅ 并创建
- ✅ 然后创建
- ✅ 帮我创建

### 英文
- ✅ create
- ✅ make
- ✅ build
- ✅ generate

---

## 🔄 两种流程对比

### 流程A：直接创建（用户明确意图）

**触发**：用户说"创建"/"建立"

**步骤**：
1. 执行 `smart_group_recommend.py`
2. 提取第一个推荐组合
3. 自动执行 `query.py --create-group`
4. 反馈创建结果

**话术**：
> 找到 1 个符合要求的组合，正在为您创建...
> 
> ✅ 策略组创建成功！
> - 名称: XXX
> - ID: XXX
> - 包含策略: X 个

---

### 流程B：询问确认（用户仅查询）

**触发**：用户说"找"/"推荐"/"查询"（无"创建"）

**步骤**：
1. 执行 `smart_group_recommend.py`
2. 展示推荐结果
3. 询问是否创建
4. 等待用户确认
5. 执行创建

**话术**：
> 📊 找到 X 个优质组合：
> 
> **组合 #1**:
> - 评分: XX.X
> - 预期收益: XX.X%
> ...
> 
> 我可以帮您创建这个组合吗？

---

## 🛠️ 命令速查

### 智能推荐
```bash
python3 skills/backtest-query/smart_group_recommend.py \
  --query "用户需求" \
  --coins "BTC,ETH" \
  --min-total-win-rate 60 \
  --max-recent-drawdown 15
```

### 创建策略组
```bash
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "组合名称" \
  --strategy-tokens "token1,token2,token3"
```

### Agent 完整流程
```python
# 1. 推荐并保存到 JSON
subprocess.run([
    'python3', 'skills/backtest-query/smart_group_recommend.py',
    '--query', '用户需求',
    '--output', '/tmp/rec.json'
])

# 2. 读取 JSON 提取数据
with open('/tmp/rec.json') as f:
    result = json.load(f)
tokens = [s['strategy_token'] for s in result['combinations'][0]['strategies']]
tokens_str = ','.join(tokens)

# 3. 执行创建
subprocess.run([
    'python3', 'skills/backtest-query/query.py',
    '--create-group',
    '--group-name', '组合名称',
    '--strategy-tokens', tokens_str
])
```

---

## 🎨 话术模板

### 场景1：明确创建
```
收到！我将为您查找 {币种} 的 {条件} 策略并创建组合。

[推荐中...]

✅ 找到 1 个符合要求的组合，正在为您创建...

[创建中...]

✅ 策略组创建成功！

组合详情:
- 名称: {name}
- 策略组 ID: {id}
- 包含策略: {count} 个
- 预期收益: {return}%
- 组合回撤: {drawdown}%

策略列表:
{strategy_list}

您可以在平台的"策略组管理"中查看和编辑。
```

### 场景2：仅查询
```
收到！我将为您查找 {币种} 的 {条件} 策略。

[推荐中...]

📊 找到 {count} 个优质组合：

**组合 #1**:
- 评分: {score}
- 预期收益: {return}%
- 组合回撤: {drawdown}%
- 包含策略: {count} 个

{strategy_list}

这个组合实现了 {特点}。我可以帮您创建策略组吗？
```

### 场景3：创建失败
```
❌ 创建策略组失败: {error}

可能原因：
- Token 无效或过期
- 策略 token 不存在
- 网络连接问题

建议：
{建议内容}
```

---

## ⚠️ 常见问题

### Q1: 如何判断用户意图？
检查用户输入是否包含创建关键词（创建/建立/建个/生成）

### Q2: 如果推荐结果有多个组合，创建哪个？
默认创建评分最高的第一个组合。如果用户有特殊要求，询问选择。

### Q3: 用户要修改组合名称怎么办？
提取用户指定的名称，替换 `--group-name` 参数。

### Q4: 如果缺少 strategy_token 怎么办？
提示无法创建，建议调整筛选条件重新推荐。

---

## 📚 详细文档

- **完整流程**: `AGENT_WORKFLOW.md`
- **用户手册**: `SKILL.md`
- **API 文档**: `query.py` 中的 docstring
