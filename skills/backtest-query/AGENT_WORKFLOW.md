# Agent 工作流程指南

## 📊 智能推荐 → 创建策略组完整流程

当用户请求策略推荐并创建组合时，按以下步骤操作。

---

## 🚦 快速决策流程

```
用户查询
    ↓
包含"创建"/"建立"关键词？
    ↓
YES → 执行推荐 → 直接创建 → 反馈结果 ✅
    ↓
NO  → 执行推荐 → 展示结果 → 询问是否创建 → 等待确认 → 创建 ✅
```

**关键原则**：
- 🟢 **用户已明确要创建** → 不询问，直接执行
- 🟡 **用户仅查询** → 展示后询问是否创建

---

## 🚀 快速使用（推荐）

使用 `agent_helper.py` 辅助库简化操作：

```python
from skills.backtest_query.agent_helper import StrategyRecommendHelper

helper = StrategyRecommendHelper()

# 检测用户意图
has_create_intent = helper.detect_create_intent(user_query)

if has_create_intent:
    # 直接推荐并创建
    success, message, combo = helper.recommend_and_create(
        query=user_query,
        coins=["BTC", "ETH"],
        max_drawdown=15
    )
    if success:
        print(f"✅ 创建成功: {message}")
        print(f"评分: {combo['score']:.2f}")
    else:
        print(f"❌ 失败: {message}")
else:
    # 仅推荐，等待确认
    success, result = helper.recommend(
        query=user_query,
        coins=["BTC"]
    )
    # 展示结果...
    # 用户确认后：
    # tokens = helper.extract_tokens(result['combinations'][0])
    # helper.create_group(tokens, "组合名称")
```

---

## 🔄 标准流程（手动操作）

### 1️⃣ 理解用户需求

#### 场景A：明确创建意图（直接执行，无需确认）

**关键词识别**：
- "创建策略组"
- "建立/建个组合"
- "帮我创建"
- "生成一个策略组"
- "并创建" / "然后创建"

**示例**：
- ✅ "帮我找 BTC 和 ETH 的优质策略，并创建组合"
- ✅ "推荐低风险策略，然后帮我建个策略组"
- ✅ "给我找做多做空各一个，创建对冲组合"

**处理方式**：推荐 → **直接创建** → 反馈结果（不询问确认）

---

#### 场景B：仅查询意图（需要确认）

**关键词识别**：
- "帮我找"
- "推荐"
- "查询"
- "有哪些"
- 没有"创建"关键词

**示例**：
- "帮我找 BTC 的优质策略"
- "推荐一些低风险策略"
- "看看有哪些好的策略"

**处理方式**：推荐 → **询问是否创建** → 用户确认 → 创建

---

**决策逻辑（伪代码）**：
```python
def detect_create_intent(user_query: str) -> bool:
    """检测用户是否有明确创建意图"""
    create_keywords = [
        "创建", "建立", "建个", "生成",
        "并创建", "然后创建", "帮我创建",
        "create", "make", "build"
    ]
    return any(kw in user_query.lower() for kw in create_keywords)

# 使用示例
if detect_create_intent(user_query):
    # 场景A：直接执行
    execute_recommend_and_create()
else:
    # 场景B：需要确认
    execute_recommend_and_ask()
```

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

### 3️⃣ 从推荐结果提取数据

**方式A：从 JSON 文件读取（推荐）**

```bash
# 保存推荐结果到文件
python3 skills/backtest-query/smart_group_recommend.py \
  --query "..." \
  --output /tmp/recommend.json
```

```python
# Agent 读取并提取数据
import json

with open('/tmp/recommend.json') as f:
    result = json.load(f)

# 获取第一个推荐组合
best_combo = result['combinations'][0]

# 提取 strategy_token 列表
tokens = [s['strategy_token'] for s in best_combo['strategies']]
tokens_str = ','.join(tokens)

# 提取组合信息
score = best_combo['score']
expected_return = best_combo['expected_return']
max_drawdown = best_combo['portfolio_risk']['max_drawdown']

print(f"策略 tokens: {tokens_str}")
print(f"评分: {score}, 收益: {expected_return}%, 回撤: {max_drawdown}%")
```

**方式B：解析标准输出（不推荐）**

可以从脚本的文本输出中提取"🔧 创建命令"部分，但不如直接读取 JSON 可靠。

**关键数据路径**：
- `result['combinations'][0]['strategies'][*]['strategy_token']` - 策略 token 列表
- `result['combinations'][0]['score']` - 评分
- `result['combinations'][0]['expected_return']` - 预期收益
- `result['combinations'][0]['portfolio_risk']['max_drawdown']` - 组合回撤

---

### 4️⃣ 根据场景决定是否确认

#### 场景A：直接创建（用户已明确要求）

**跳过确认，直接执行创建命令**，并展示结果：

> 📊 找到 1 个符合要求的组合，正在为您创建...
>
> [执行创建命令]
>
> ✅ 策略组创建成功！
> 
> **组合详情**：
> - 名称: 智能组合_1_20260428
> - 策略组 ID: 12345
> - 包含策略: 3 个
> - 预期收益: 120.5%
> - 组合回撤: 12.3%

---

#### 场景B：询问确认（用户仅查询）

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

### 5️⃣ 执行创建

**从提取的数据构建并执行创建命令**：

```python
# 构建组合名称
from datetime import datetime
combo_name = f"智能组合_{datetime.now().strftime('%Y%m%d_%H%M')}"

# 如果用户指定了名称，使用用户的
if user_provided_name:
    combo_name = user_provided_name

# 构建命令
import subprocess

cmd = [
    'python3', 'skills/backtest-query/query.py',
    '--create-group',
    '--group-name', combo_name,
    '--strategy-tokens', tokens_str
]

# 执行
result = subprocess.run(
    cmd,
    cwd='/home/ubuntu/work/QuantClaw',
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print(f"✅ 策略组创建成功: {combo_name}")
    # 解析输出获取策略组 ID
else:
    print(f"❌ 创建失败: {result.stderr}")
```

**注意**：
- 直接使用提取的 `tokens_str`，不要手动修改
- 组合名称可以由用户指定或自动生成
- 需要在正确的工作目录执行

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

### 示例1：明确创建意图（直接执行）

**用户**："帮我找 BTC 和 ETH 的低风险策略，创建一个对冲组合"

**Agent 内部流程**：
```python
# 1. 检测创建意图
has_create_intent = True  # "创建" in query

# 2. 执行智能推荐，保存到临时文件
exec("""
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC和ETH的低风险策略" \
  --coins "BTC,ETH" \
  --max-recent-drawdown 15 \
  --output /tmp/recommend.json
""")

# 3. 读取推荐结果
with open('/tmp/recommend.json') as f:
    result = json.load(f)

best_combo = result['combinations'][0]
tokens = [s['strategy_token'] for s in best_combo['strategies']]
tokens_str = ','.join(tokens)

# 4. 直接创建（不询问确认）
exec(f"""
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC+ETH对冲组合_20260428" \
  --strategy-tokens "{tokens_str}"
""")
```

**Agent 回复用户**：
```
收到！我将为您查找 BTC 和 ETH 的低风险策略并创建组合。

📊 找到 1 个符合要求的组合，正在为您创建...

✅ 策略组创建成功！

组合详情:
- 名称: BTC+ETH对冲组合_20260428
- 策略组 ID: 12345
- 包含策略: 3 个
- 预期收益: 95.2%
- 组合回撤: 11.5%

策略列表:
1. BTC / 鲲鹏_BTC_做多 (年化102%, 夏普2.35, 胜率68.5%)
2. ETH / 风霆_ETH_做空 (年化88%, 夏普2.10, 胜率65.2%)
3. BTC / 网格_BTC_震荡 (年化76%, 夏普2.50, 胜率72.1%)

您可以在平台的"策略组管理"中查看和编辑这个组合。
```

---

### 示例2：仅查询（需要确认）

**用户**："帮我看看 BTC 有哪些好的策略"

**Agent 内部流程**：
```python
# 1. 检测创建意图
has_create_intent = False  # 无"创建"关键词

# 2. 执行智能推荐
exec("""
python3 skills/backtest-query/smart_group_recommend.py \
  --query "BTC的优质策略" \
  --coins "BTC" \
  --output /tmp/recommend.json
""")

# 3. 读取结果并展示
with open('/tmp/recommend.json') as f:
    result = json.load(f)

best_combo = result['combinations'][0]

# 4. 暂存数据，等待用户确认
# 将 tokens 保存到会话上下文中
session_context['pending_combo'] = best_combo
```

**Agent 回复用户**：
```
收到！我将为您查找 BTC 的优质策略。

📊 推荐结果：

组合 #1:
- 评分: 87.3
- 预期收益: 95.2%
- 组合回撤: 11.5%
- 包含策略: 3 个

策略列表:
1. BTC / 鲲鹏_BTC_做多 (年化102%, 夏普2.35, 胜率68.5%)
2. BTC / 风霆_BTC_做空 (年化88%, 夏普2.10, 胜率65.2%)
3. BTC / 网格_BTC_震荡 (年化76%, 夏普2.50, 胜率72.1%)

这个组合实现了多空对冲，风险较低。我可以帮您创建策略组吗？
```

---

**用户**："好的，创建吧"

**Agent 内部流程**：
```python
# 5. 从会话上下文读取之前保存的数据
combo = session_context['pending_combo']
tokens = [s['strategy_token'] for s in combo['strategies']]
tokens_str = ','.join(tokens)

# 6. 执行创建
exec(f"""
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "BTC智能组合_20260428" \
  --strategy-tokens "{tokens_str}"
""")
```

**Agent 回复用户**：
```
正在创建策略组...

✅ 策略组创建成功！

组合名称: BTC智能组合_20260428
策略组 ID: 12345
包含策略: 3 个

您可以在平台的"策略组管理"中查看和编辑这个组合。
```

---

## 🎯 最佳实践

1. **识别用户意图** - 区分"查询"和"创建"，决定是否需要确认
2. **明确创建意图时直接执行** - 包含"创建"/"建立"关键词时，推荐后直接创建
3. **仅查询时询问确认** - 没有创建意图时，展示结果并询问是否创建
4. **清晰展示组合信息** - 收益、风险、策略数量、评分
5. **反馈详细** - 成功/失败都要给出明确信息和后续操作建议

---

## 🔧 调试技巧

### 完整流程测试脚本

```python
#!/usr/bin/env python3
"""测试完整的推荐→创建流程"""

import json
import subprocess
from datetime import datetime

# 1. 执行推荐
print("📊 执行智能推荐...")
recommend_result = subprocess.run([
    'python3', 'skills/backtest-query/smart_group_recommend.py',
    '--query', 'BTC优质策略',
    '--coins', 'BTC',
    '--output', '/tmp/test_recommend.json'
], cwd='/home/ubuntu/work/QuantClaw', capture_output=True, text=True)

if recommend_result.returncode != 0:
    print(f"❌ 推荐失败: {recommend_result.stderr}")
    exit(1)

# 2. 读取推荐结果
with open('/tmp/test_recommend.json') as f:
    result = json.load(f)

if not result.get('combinations'):
    print("⚠️ 没有推荐组合")
    exit(1)

# 3. 提取第一个组合的数据
best_combo = result['combinations'][0]
print(f"\n📋 推荐组合:")
print(f"  评分: {best_combo['score']:.2f}")
print(f"  预期收益: {best_combo['expected_return']:.2f}%")
print(f"  回撤: {best_combo['portfolio_risk']['max_drawdown']:.2f}%")

# 4. 提取 strategy_token
tokens = [s['strategy_token'] for s in best_combo['strategies'] if s.get('strategy_token')]
if not tokens:
    print("❌ 没有有效的 strategy_token")
    exit(1)

tokens_str = ','.join(tokens)
print(f"\n🔑 策略 tokens: {tokens_str}")

# 5. 构建组合名称
combo_name = f"测试组合_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"\n📝 组合名称: {combo_name}")

# 6. 执行创建
print("\n🔧 执行创建...")
create_result = subprocess.run([
    'python3', 'skills/backtest-query/query.py',
    '--create-group',
    '--group-name', combo_name,
    '--strategy-tokens', tokens_str
], cwd='/home/ubuntu/work/QuantClaw', capture_output=True, text=True)

print(create_result.stdout)
if create_result.returncode != 0:
    print(f"❌ 创建失败: {create_result.stderr}")
    exit(1)

print("\n✅ 测试完成")
```

### 检查 JSON 数据结构

```bash
# 查看完整结构
python3 skills/backtest-query/smart_group_recommend.py \
  --query "测试" \
  --output /tmp/test.json

# 提取关键字段
cat /tmp/test.json | jq '{
  total_selected: .total_selected,
  combinations: [.combinations[] | {
    score,
    expected_return,
    tokens: [.strategies[].strategy_token]
  }]
}'
```

### 单独测试创建

```bash
# 直接测试创建功能（使用已知 token）
python3 skills/backtest-query/query.py \
  --create-group \
  --group-name "测试组合_$(date +%Y%m%d_%H%M%S)" \
  --strategy-tokens "已知token1,已知token2"
```

---

**总结**：整个流程已打通，Agent 只需按照标准流程操作，智能推荐会自动生成创建命令，确保 `strategy_token` 正确传递。
