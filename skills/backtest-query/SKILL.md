# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 🚨 脚本选择（核心规则）

```
用户输入
    │
    ├─ "推荐/建议" + 策略组
    │  → smart_group_recommend.py（展示结果）
    │
    ├─ "创建/新建/建" + 策略组
    │  → smart_group_recommend.py → query.py --create-group（静默执行）
    │
    ├─ "保存/收藏" + 单个策略
    │  → query.py --add-strategy
    │
    └─ "查看/列出"
       → query.py --list-xxx
```

**⚠️ 关键**：
- 看到"策略组"+"创建/建" → **必须先推荐**（两步流程）
- 直接用 query.py 创建会失败（缺少 tokens）

---

## 执行规范

1. **静默执行**：不显示命令，只返回结果
2. **参数铁律**：用户说的才传，没说的不传
3. **动态查询**：先查ID（`--list-coins/strategies/ai-times`）
4. **Agent ID 传递**：使用 `--agent-id` 参数显式指定（避免路径依赖）

### Agent ID 获取方式

```python
# 从运行时上下文获取当前 agent_id
agent_id = os.environ.get("CLAWDBOT_AGENT_ID")  # 如果 Gateway 提供
# 或从配置读取当前 session 的 agent_id

# 调用时传递
exec(command=f"python3 skills/backtest-query/query.py --agent-id {agent_id} --list-coins")
```

**为什么需要？**
- 脚本通过 agent_id 从 `~/.quantclaw/users.json` 匹配用户 token
- 避免依赖 PWD 路径识别（软链接导致的路径歧义）
- 更明确、更可靠

---

## 典型案例

### ✅ 案例1：创建策略组

**用户**："帮我建个 DOGE/BCH 对冲策略组"

```bash
# 步骤1：推荐
python3 smart_group_recommend.py \
  --query "帮我建个 DOGE/BCH 对冲策略组" \
  --coins "DOGE,BCH" \
  --strategy-direction-map '{"11": ["long", "short"]}'

# 步骤2：提取 tokens（解析 JSON）
tokens = [s["strategy_token"] for s in result["combinations"][0]["strategies"]]

# 步骤3：创建
python3 query.py --create-group \
  --group-name "DOGE/BCH 对冲策略组" \
  --strategy-tokens "token1,token2,token3"

# 步骤4：返回
"✅ 已创建策略组：DOGE/BCH 对冲策略组"
```

**❌ 错误**：直接用 `query.py --create-group`（没有 tokens）

---

### ✅ 案例2：推荐

**用户**："推荐 BTC 策略"

```bash
# 只推荐，不创建
python3 smart_group_recommend.py \
  --query "推荐 BTC 策略" \
  --coins "BTC"

# 展示结果，询问："是否创建策略组？"
```

---

### ✅ 案例3：指定参数

**用户**："创建风霆 V4.3 BTC 多空，最近 30 天"

```bash
# 步骤1：查时间ID
python3 query.py --list-ai-times  # → 30天=id:3

# 步骤2：推荐
python3 smart_group_recommend.py \
  --query "风霆 V4.3 BTC 多空" \
  --coins "BTC" \
  --strategy-types "11" \
  --strategy-version-map '{"11": ["4.3"]}' \
  --strategy-direction-map '{"11": ["long", "short"]}' \
  --ai-time-ids "3"

# 步骤3-4：创建（同案例1）
```

---

### ✅ 案例4：保存单策略

**用户**："保存这个策略"

```bash
python3 query.py --add-strategy --strategy-token "xxx"
# 返回："✅ 策略保存成功"
```

**⚠️ 注意**：策略库 ≠ 策略组

---

## 常用参数

### smart_group_recommend.py
```bash
--query "用户完整输入"
--coins "BTC,ETH,SOL"
--strategy-types "11,7"           # 策略ID（11=风霆，7=网格）
--strategy-version-map '{"11": ["4.3"]}'  # 版本控制
--strategy-direction-map '{"11": ["long", "short"]}'  # 方向
--coin-pct-map '{"BTC": ["80", "100"]}'   # 比例/网格比例（策略网格密度）
                                           # BTC: 10,20,30,40,50,60,80,100,120
                                           # 其他: 60,80,100,120,140
--ai-time-ids "1,3"              # 时间ID
--top-per-group 3                # 每组取几个
--max-combinations 1             # 返回几个组合
--min-total-win-rate 60          # 最小胜率(%)
--max-recent-drawdown 20         # 最大回撤(%)
```

### query.py
```bash
# 查询
--list-coins           # 币种列表
--list-strategies      # 策略ID映射
--list-ai-times        # 时间配置

# 创建
--create-group --group-name "xxx" --strategy-tokens "t1,t2,t3"

# 保存
--add-strategy --strategy-token "xxx"
```

---

## 参数规则

### 版本控制
```json
{
  "11": ["4.3"],   // 只查 4.3
  "11": null       // 查所有版本（用户未说）
}
```

**规则**：
- 用户说 "V4.3" → `["4.3"]`
- 用户说 "V4.3 3倍杠杆" → `["4.3"]`（系统过滤）
- 用户未说 → 不传参数

### 方向控制
```json
{"11": ["long", "short"]}  // 所有币种统一
```

**限制**：不支持按币种细分

---

## 性能参考

| 条件 | 组合数 | 耗时 |
|------|--------|------|
| 1币×1策略×1时间 | ~50 | 3-5秒 |
| 3币×2策略×1时间 | ~300 | 15-30秒 |
| 30币×2策略×1时间 | ~3000 | 3-5分钟 |

---

## 快速对比

| 用户说的 | ❌ 错误 | ✅ 正确 |
|---------|--------|--------|
| 建DOGE/BCH对冲策略组 | query.py | smart→query |
| 推荐BTC策略 | query.py | smart_group_recommend.py |
| 保存策略 | smart | query.py --add-strategy |
| 查币种 | smart | query.py --list-coins |
