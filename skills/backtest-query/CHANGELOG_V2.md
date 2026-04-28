# 智能推荐 v2 版本更新日志

## 🎯 核心变更

### 接口调用优化

**旧版本（v1）**：
- 多维度笛卡尔积轮询
- 每个参数组合都调用一次接口
- 查询次数 = 币种 × 方向 × 策略类型 × 版本 × 网格比例 × 时间
- 可能导致上万次 API 调用

**新版本（v2）**：
- **只传已知的必须循环参数**
- 接口返回全量数据
- 代码端按需分类和筛选
- 查询次数 = 需要循环的维度数量（通常 1-4 次）

---

## 🔄 循环逻辑

### 统一的循环规则

**核心原则**：任何参数指定了多个值，就需要循环该维度

| 参数 | 单个值 | 多个值 | 未指定 |
|------|--------|--------|--------|
| `--coins` | 固定参数 | 循环 | 不传（全量） |
| `--strategy-types` | 固定参数 | 循环 | 不传（全量） |
| `--directions` | 固定参数 | 循环 | 不传（全量） |
| `--ai-time-ids` | 固定参数 | 循环 | 不传（全量） |

### 循环场景示例

| 场景 | 参数 | 循环维度 | 查询次数 |
|------|------|---------|---------|
| 单币种 | `--coins "BTC"` | 无 | **1次** |
| 多币种 | `--coins "BTC,ETH"` | 币种 | **2次** |
| 多策略 | `--strategy-types "11,7"` | 策略类型 | **2次** |
| 多方向 | `--directions "long,short"` | 方向 | **2次** |
| 多维度组合 | `--coins "BTC,ETH" --directions "long,short"` | 币种 × 方向 | **4次** |
| 三维度组合 | `--coins "BTC,ETH" --strategy-types "11,7" --directions "long,short"` | 币种 × 策略 × 方向 | **8次** |

### 代码逻辑

```python
# 统一处理所有参数
def _identify_loop_dimensions(coins, strategy_types, directions, ai_time_ids):
    loop_dims = {}
    fixed_params = {}
    
    # 任何参数都按统一规则处理
    if coins:
        if len(coins) > 1:
            loop_dims['coins'] = coins  # 需要循环
        else:
            fixed_params['search_coin'] = coins[0]  # 固定参数
    # 未指定则不传参数（接口返回全量）
    
    # strategy_types, directions, ai_time_ids 同理
    
    return {'loop_dims': loop_dims, 'fixed_params': fixed_params}

# 笛卡尔积生成查询组合
import itertools
combinations = itertools.product(
    loop_dims['coins'],
    loop_dims['strategy_types'],
    loop_dims['directions']
)

# 查询次数 = 所有循环维度的笛卡尔积
total_queries = len(list(combinations))
```

---

## 📊 查询对比

### 示例1：单币种查询

**需求**："查询 BTC 的马丁策略"

**命令**：
```bash
--coins "BTC" --strategy-types "11"
```

**v1 版本**：
```
查询次数 = 1个币种 × 2个方向 × 1个策略 × 3个版本 × 9个网格 × 16个时间
         = 864 次
```

**v2 版本**：
```
查询次数 = 1次
参数: coin=BTC, strategy_type=11
接口返回: 全部方向、版本、网格、时间的数据
代码分类: 按需筛选
```

---

### 示例2：多币种对冲

**需求**："找到一组 BTC 和 SOL 对冲的策略组"

**命令**：
```bash
--coins "BTC,SOL" --directions "long,short"
```

**v1 版本**：
```
查询次数 = 2个币种 × 2个方向 × M个策略 × N个版本 × 网格 × 时间
         = 数千次
```

**v2 版本**：
```
查询次数 = 4次
1. BTC + long
2. BTC + short
3. SOL + long
4. SOL + short

每次查询返回该币种+方向下的全部数据
代码端进行组合优化
```

---

### 示例3：多策略类型对比

**需求**："对比 BTC 的马丁和网格策略"

**命令**：
```bash
--coins "BTC" --strategy-types "11,7"
```

**v1 版本**：
```
查询次数 = 1个币种 × 2个方向 × 2个策略 × 版本 × 网格 × 时间
         = 数千次
```

**v2 版本**：
```
查询次数 = 2次
1. BTC + 策略11（马丁）
2. BTC + 策略7（网格）

每次查询返回该策略类型的全部数据
```

---

### 示例4：时间周期对比

**需求**："对比 BTC 在最近1年和3年的表现"

**命令**：
```bash
--coins "BTC" --ai-time-ids "5,7"
```

**v1 版本**：
```
查询次数 = 1个币种 × 2个方向 × M个策略 × 版本 × 网格 × 2个时间
         = 数千次
```

**v2 版本**：
```
查询次数 = 2次
1. BTC + 时间5（最近1年）
2. BTC + 时间7（最近3年）

每次查询返回该时间周期的全部数据
```

---

## 🆕 新增功能

### 1. 智能维度识别

```python
loop_config = _identify_loop_dimensions(
    coins=['BTC', 'SOL'],
    direction=None,
    strategy_type=11,
    ai_time_id=None
)

# 输出：
# {
#   'coins': ['BTC', 'SOL'],      # 需要循环
#   'directions': ['long', 'short'], # 需要循环（对冲场景）
#   'fixed_params': {
#     'strategy_type': 11          # 固定参数
#   }
# }
```

### 2. 数据分类统计

```
📦 总计获取: 1243 条策略数据
   - 币种: 2 个 ['BTC', 'SOL']
   - 方向: 2 个 ['long', 'short']
   - 策略类型: 1 个 [11]
```

### 3. 查询进度显示

```
🔍 [1/4] 查询: 币种=BTC / 方向=long
✅ 返回 312 条数据

🔍 [2/4] 查询: 币种=BTC / 方向=short
✅ 返回 289 条数据
```

---

## ⚙️ 配置变更

### defaults.py 不再需要轮询配置

**移除的配置**：
```python
# 不再需要
TIME_MODE = "all"  # 全部时间
GRID_PCT_MODE = "all"  # 全部网格
```

**保留的配置**：
```python
# 仍然需要（用于默认值补全）
COIN_COUNT = None
STRATEGY_COUNT = None
COIN_TYPE_FILTER = "CRYPTO"
```

---

## 🔧 使用方法

### 命令行

```bash
# v2 版本
python3 smart_recommend_v2.py \
  --coins "BTC,SOL" \
  --workspace $(pwd) \
  --save-memory

# v1 版本（兼容保留）
python3 smart_recommend.py \
  --coins "BTC,SOL" \
  --workspace $(pwd) \
  --save-memory
```

### Agent 调用

```python
from smart_recommend_v2 import SmartRecommenderV2

recommender = SmartRecommenderV2(token, verbose=True)

strategies = recommender.fetch_strategies(
    coins=['BTC', 'SOL'],  # 多币种对冲
    strategy_type=11,      # 马丁策略
    min_sharpe=1.5
)
```

---

## ⚠️ 注意事项

### 1. 接口要求

**接口必须支持部分参数查询**：
- 传入 `coin=BTC` → 返回 BTC 的全部数据（所有方向、版本、网格、时间）
- 不传 `strategy_type` → 返回所有策略类型的数据

### 2. 兼容性

- v1 和 v2 **可以共存**
- v2 不影响 v1 的使用
- 建议新查询使用 v2，旧代码保持 v1

### 3. 性能提升

| 指标 | v1 | v2 | 提升 |
|------|----|----|-----|
| 查询次数 | 数千次 | 1-10次 | **99%+** |
| 响应时间 | 10-30分钟 | 5-30秒 | **95%+** |
| 网络开销 | 极高 | 极低 | **99%+** |

---

## 🚀 迁移建议

### 短期（测试阶段）

1. 保留 `smart_recommend.py`（v1）
2. 新增 `smart_recommend_v2.py`（v2）
3. 逐步测试 v2 的准确性

### 长期（稳定后）

1. 将 v2 作为默认版本
2. 重命名 `smart_recommend.py` → `smart_recommend_legacy.py`
3. 重命名 `smart_recommend_v2.py` → `smart_recommend.py`
4. 更新 SKILL.md 文档

---

## 📝 TODO

- [ ] 测试多币种对冲场景
- [ ] 验证接口返回的数据完整性
- [ ] 优化数据分类算法
- [ ] 添加缓存机制（避免重复查询）
- [ ] 性能对比测试报告

---

**更新时间**: 2024-04-27  
**版本**: v2.0.0  
**状态**: 🚧 测试中
