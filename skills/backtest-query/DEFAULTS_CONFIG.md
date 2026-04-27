# 默认参数配置指南

## 📁 统一配置文件

**文件位置**: `skills/backtest-query/defaults.py`

所有从接口获取的默认参数都在这个文件中统一管理，方便修改和维护。

---

## 🎯 可配置项

### 1. 币种默认配置

```python
# defaults.py 第 17-18 行

COIN_COUNT = 3  # 取前N个币种
COIN_FALLBACK = ["BTC", "ETH", "SOL"]  # 容错默认值
```

**修改示例**：
```python
# 取前5个币种
COIN_COUNT = 5

# 修改容错币种
COIN_FALLBACK = ["BTC", "ETH", "BNB", "SOL", "XRP"]
```

---

### 2. 策略类型默认配置

```python
# defaults.py 第 20-21 行

STRATEGY_COUNT = 3  # 取前N个策略类型
STRATEGY_FALLBACK = [11, 7, 1]  # 容错默认值（风霆、网格、鲲鹏）
```

**修改示例**：
```python
# 取前5个策略类型
STRATEGY_COUNT = 5

# 修改容错策略类型
STRATEGY_FALLBACK = [11, 8, 7, 1, 3]
```

---

### 3. 时间ID默认配置

```python
# defaults.py 第 23-24 行

TIME_INDEX = 0  # 取第N个时间ID（0表示第1个）
TIME_FALLBACK = "5"  # 容错默认值（最近1年）
```

**修改示例**：
```python
# 改为取第2个时间ID
TIME_INDEX = 1

# 修改容错时间ID（改为最近90天）
TIME_FALLBACK = "1"
```

---

### 4. 缓存配置

```python
# defaults.py 第 26 行

ENABLE_CACHE = True  # 是否启用缓存
```

**修改示例**：
```python
# 禁用缓存，每次都重新获取
ENABLE_CACHE = False
```

---

## 📊 配置效果对比

### 示例：修改币种数量

**修改前**：
```python
COIN_COUNT = 3
```
输出：
```
ℹ️  未指定币种，使用默认币种（接口前3个）: DOGE, BCH, HYPE
```

**修改后**：
```python
COIN_COUNT = 5
```
输出：
```
ℹ️  未指定币种，使用默认币种（接口前5个）: DOGE, BCH, HYPE, SOL, XRP
```

---

### 示例：修改时间ID选取

**修改前**：
```python
TIME_INDEX = 0  # 第1个
```
输出：
```
ℹ️  未指定时间范围，使用默认（接口第1个）: ai_time_id=16
```

**修改后**：
```python
TIME_INDEX = 1  # 第2个
```
输出：
```
ℹ️  未指定时间范围，使用默认（接口第2个）: ai_time_id=5
```

---

## 🔧 高级配置

### 1. 自定义筛选逻辑

如果需要按特定条件筛选（而不是简单地取前N个），可以修改 `defaults.py` 中的方法：

**示例：只选择主流币种**

```python
# defaults.py 第 58-80 行：get_coins() 方法

def get_coins(self) -> List[str]:
    # ... 省略前面的代码 ...
    
    coins_data = result.get("info", [])
    
    # 【修改这里】只选择主流币种
    main_coins = ["BTC", "ETH", "SOL", "BNB", "XRP"]
    self._coins = [
        c["coin"] for c in coins_data 
        if c["coin"] in main_coins
    ][:self.COIN_COUNT]
    
    if not self._coins:
        self._coins = self.COIN_FALLBACK
    
    return self._coins
```

---

### 2. 自定义排序逻辑

**示例：按市值排序（假设接口有 market_cap 字段）**

```python
def get_coins(self) -> List[str]:
    # ... 省略前面的代码 ...
    
    coins_data = result.get("info", [])
    
    # 【修改这里】按市值排序
    sorted_coins = sorted(
        coins_data, 
        key=lambda x: x.get("market_cap", 0), 
        reverse=True
    )
    
    self._coins = [c["coin"] for c in sorted_coins[:self.COIN_COUNT]]
    
    return self._coins
```

---

### 3. 条件判断逻辑

**示例：根据市场情况动态选择时间范围**

```python
def get_ai_time_id(self) -> str:
    # ... 省略前面的代码 ...
    
    times_data = result.get("info", [])
    
    # 【修改这里】根据市场情况选择
    # 示例：如果是牛市，选择"牛市"时间段
    for time_item in times_data:
        if "牛市" in time_item.get("name", ""):
            self._ai_time_id = str(time_item["id"])
            break
    else:
        # 没找到就用第1个
        self._ai_time_id = str(times_data[self.TIME_INDEX]["id"])
    
    return self._ai_time_id
```

---

## 📝 使用示例

### 方式1：不需要修改任何代码

修改 `defaults.py` 中的配置后，所有脚本会自动使用新配置：

```bash
# 修改 COIN_COUNT = 5
vim skills/backtest-query/defaults.py

# 直接运行，会使用新配置
python3 smart_recommend.py --token xxx
```

---

### 方式2：临时覆盖配置（不推荐）

```python
from defaults import DefaultParams

# 临时修改
DefaultParams.COIN_COUNT = 5
DefaultParams.TIME_INDEX = 1

# 使用修改后的配置
manager = DefaultParams(token)
coins = manager.get_coins()  # 取前5个
```

---

## 🧪 测试配置

修改配置后，建议运行测试验证：

```bash
cd /home/ubuntu/work/QuantClaw/skills/backtest-query

# 测试币种配置
python3 -c "
from defaults import DefaultParams
manager = DefaultParams('YOUR_TOKEN', verbose=True)
print('Coins:', manager.get_coins())
print('Time ID:', manager.get_ai_time_id())
print('Strategy Types:', manager.get_strategy_types())
"

# 测试完整流程
python3 smart_recommend.py \
  --token YOUR_TOKEN \
  --group-size 2 \
  --top-n 1 \
  --no-detail
```

---

## ⚠️ 注意事项

1. **修改后无需重启**
   - Python 脚本每次执行都会重新加载模块
   - 修改配置后直接运行即可生效

2. **容错默认值很重要**
   - 确保 `FALLBACK` 值始终有效
   - 建议使用稳定的主流币种/策略

3. **缓存的影响**
   - 如果启用缓存，同一次运行中多次调用会返回相同结果
   - 禁用缓存会增加 API 调用次数

4. **接口数据格式**
   - 确保接口返回的数据格式与代码期望一致
   - 如果接口变更，可能需要同步修改代码

---

## 📖 相关文档

- **算法详解**: `docs/skills/SMART_RECOMMEND_ALGORITHM.md`
- **使用指南**: `skills/backtest-query/skills/smart_recommend.md`
- **测试指南**: `skills/backtest-query/TEST.md`

---

## 🎯 常见配置场景

### 场景1：只使用主流币种

```python
COIN_COUNT = 3
COIN_FALLBACK = ["BTC", "ETH", "SOL"]

# 并在 get_coins() 中添加过滤
main_coins = ["BTC", "ETH", "SOL", "BNB", "XRP"]
self._coins = [c["coin"] for c in coins_data if c["coin"] in main_coins][:3]
```

### 场景2：保守策略配置

```python
# 只使用成熟策略
STRATEGY_COUNT = 2
STRATEGY_FALLBACK = [11, 7]  # 只用风霆和网格

# 时间范围更长
TIME_INDEX = 2  # 选择更长的时间范围
TIME_FALLBACK = "6"  # 最近2年
```

### 场景3：激进策略配置

```python
# 使用更多策略类型
STRATEGY_COUNT = 5
STRATEGY_FALLBACK = [11, 8, 7, 1, 3]

# 时间范围更短（更关注近期表现）
TIME_INDEX = 0  # 第1个（通常是最新的）
TIME_FALLBACK = "2"  # 最近7天
```

---

**修改配置后记得测试！** 🧪
