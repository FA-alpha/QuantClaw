# 回测数据查询与策略组合

推荐并创建策略组合。

---

## 🚨 脚本选择（意图识别）

| 用户意图 | 触发关键词 | 使用脚本 | 执行方式 |
|---------|----------|---------|---------|
| **推荐策略组** | "推荐"/"建议"/"给我看看" | `smart_group_recommend.py` | 展示结果，**询问是否创建** |
| **创建策略组** | "创建"/"新建"/"建"/"构建"/"帮我建" | `smart_group_recommend.py` → `query.py --create-group` | **静默执行，直接创建** |
| 保存单个策略 | "保存"/"收藏" | `query.py --add-strategy` | 收藏到策略库 |
| 查询列表 | "有哪些"/"列出"/"查看" | `query.py --list-xxx` | 展示列表 |

**⚠️ 核心规则**：
1. 看到 "创建/建/构建" → **必须执行完整的两步流程**（推荐 + 创建），不要只推荐
2. 看到 "推荐/建议" → 只展示结果，询问用户是否创建
3. 创建时 `--max-combinations 1` 确保只返回一个最佳组合

---

## 执行规范

1. **静默执行**：不显示命令，只返回结果
2. **参数铁律**：用户说的才传，没说的不传
3. **动态查询**（三类数据必须先查询列表）：
   - **币种**：`--list-coins` → 验证存在 → 传递
   - **策略类型**：`--list-strategies` → 匹配名称/验证ID → 传递
   - **时间**：`--list-ai-times` → 匹配描述（含隐含时间如"2025年"） → 传递
   - **禁止**硬编码任何 ID/币种

4. **必须加 `--agent-id`**：所有脚本都需要（用于自动获取 token）
5. **一次性执行**：推荐时总是加 `--output`，避免二次运行
6. **意图分析必做**：每次调用 `smart_group_recommend.py` 前，必须先读取 `INTENT_ANALYSIS.md` 生成 intent JSON

### 参数传递规则

| 用户说了 | 操作 | 传递参数 |
|---------|-----|---------|
| 币种/策略名/时间 | 查询列表 → 匹配/验证 | 传递找到的值 |
| 版本/方向/比例 | 直接提取 | 直接传递 |
| 数量（如"推荐3个"） | 提取数字 | `--max-combinations "3"` |
| 未说（时间/版本/方向） | 无操作 | 不传参数 |
| 未说数量 | 根据模式 | 创建=1, 推荐=3 |

### 总是传递的参数

| 参数 | 取值规则（优先级从高到低） |
|------|--------------------------|
| `--max-combinations` | 1. 用户说了数量 → 用户的数量<br>2. 创建模式 → `1`<br>3. 推荐模式 → `3` |
| `--top-per-group` | `3`（固定） |

7. **意图分析**（必需）：读取 `INTENT_ANALYSIS.md` → 生成 intent JSON → 传 `--intent-json`

---

---

## 典型案例

### 案例：创建策略组（完整流程）

用户："帮我构建 DOGE 与 BCH 对冲策略组"
```python
# 1. 查币种 → 验证
# 2. 读 INTENT_ANALYSIS.md → 生成 intent JSON
# 3. 推荐（max-combinations=1，因为创建模式）
# 4. 提取 tokens
# 5. 创建策略组（自动执行）
# 6. 返回："✅ 已创建"
```
⚠️ 关键：看到"创建/建/构建" → 必须执行第5步

### 区分推荐与创建
- 推荐："推荐BTC策略" → 展示结果，询问是否创建
- 创建："建个策略组" → 直接创建，不询问
- 指定数量："推荐5个" → 传 max-combinations=5

### 动态查询示例

```python
# 币种："BTC和狗狗币" → 查列表 → 验证 → 传 "BTC,DOGE"
# 策略："风霆" → 查列表 → 匹配名称 → 传 id:11
# 时间："最近1年" → 查列表 → 匹配描述 → 传 id:5
# 隐含时间："2025年震荡" → 查列表 → 根据列表和需求选择合适ID
```
⚠️ 禁止硬编码，必须查询列表

### 保存单策略
`query.py --add-strategy --strategy-token "xxx"`（策略库 ≠ 策略组）

---

## 参数说明

### smart_group_recommend.py
```bash
--agent-id "qc-xxx"              # 必需
--query "用户原话"               # 必需
--coins "BTC,ETH"                # 币种（先验证）
--strategy-types "11,7"          # 策略类型（11=风霆, 7=网格）
--strategy-version-map '{"11": ["4.3"]}'  # 版本过滤
--strategy-direction-map '{"11": ["long", "short"]}'  # 方向
--coin-pct-map '{"BTC": ["80"]}'    # 比例（BTC: 10~120, 其他: 60~140）
--ai-time-ids "16"               # 时间ID（用户说了才传）
--intent-json '{...}'            # 意图JSON（必传，从 INTENT_ANALYSIS.md 生成）
--max-combinations 1             # 总是传
--top-per-group 3                # 总是传
--output /tmp/result.json        # 必需
```

### query.py
```bash
--list-coins / --list-strategies / --list-ai-times  # 查询列表
--create-group --group-name "xxx" --strategy-tokens "t1,t2,t3"  # 创建组
--add-strategy --strategy-token "xxx"  # 保存单策略
```

### 参数规则
- 版本：用户说 "V4.3" → `{"11": ["4.3"]}`；未说 → 不传
- 方向：`{"11": ["long", "short"]}`（所有币种统一）
- 时间：用户说了才查ID再传，未说不传

### 性能参考
1币×1策略×1时间 ~50组合 3-5秒 | 3币×2策略×1时间 ~300组合 15-30秒
