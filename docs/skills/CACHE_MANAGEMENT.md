# 全局缓存管理

## 📊 全局缓存说明

币种列表、策略类型列表、时间ID列表是**全局公共数据**，所有用户共享同一份缓存。

### 缓存的数据

- **币种列表** (32个: 13 CRYPTO + 19 US)
- **策略类型列表** (7个)
- **时间ID列表** (16个)

### 缓存生命周期

- **初始化**: 第一个用户查询时从接口获取
- **共享**: 所有用户使用同一份数据
- **持续**: 进程生命周期内一直有效
- **刷新**: 手动强制刷新

---

## 🔄 强制刷新缓存

### 使用场景

1. **接口数据更新** - 新增币种、策略、时间段
2. **数据不准确** - 怀疑缓存数据有问题
3. **定期刷新** - 每天/每周刷新一次
4. **调试测试** - 验证最新数据

---

## 🛠️ 刷新方法

### 方法1: 使用 smart_recommend.py

```bash
python3 smart_recommend.py \
  --token YOUR_TOKEN \
  --force-refresh \
  --coins "BTC,ETH"

# 输出：
# 🔄 强制刷新全局缓存...
# ✅ 缓存已清除，将重新获取最新数据
# 
# ℹ️  未指定时间范围，使用默认（接口第1个）: ai_time_id=16
# ...
```

---

### 方法2: 使用 query.py

```bash
python3 query.py \
  --token YOUR_TOKEN \
  --list-coins \
  --refresh-cache

# 输出：
# 🔄 已清除全局缓存（币种、策略、时间数据）
# 可用币种:
#   DOGE - DOGE/USDT
#   ...
```

---

### 方法3: 在代码中调用

```python
from defaults import DefaultParams

# 清除全局缓存
DefaultParams.clear_cache()

# 下次查询会重新获取
manager = DefaultParams(token)
coins = manager.get_coins()  # 重新从接口获取
```

---

## 📊 缓存状态查询

### 查看缓存状态

```python
from defaults import DefaultParams

status = DefaultParams.get_cache_status()
print(status)
# {'coins': True, 'ai_time_id': True, 'strategy_types': True}
```

### 命令行查询

```bash
python3 -c "
from defaults import DefaultParams
status = DefaultParams.get_cache_status()
print('缓存状态:')
for key, cached in status.items():
    print(f'  {key}: {\"已缓存\" if cached else \"未缓存\"}')
"

# 输出：
# 缓存状态:
#   coins: 已缓存
#   ai_time_id: 已缓存
#   strategy_types: 已缓存
```

---

## 🎯 刷新效果

### 刷新前

```bash
$ python3 smart_recommend.py --token xxx --coins "BTC"

ℹ️  未指定时间范围，使用默认（接口第1个）: ai_time_id=16
# 使用缓存的时间ID（可能是旧数据）
```

---

### 刷新后

```bash
$ python3 smart_recommend.py --token xxx --force-refresh --coins "BTC"

🔄 强制刷新全局缓存...
✅ 缓存已清除，将重新获取最新数据

ℹ️  未指定时间范围，使用默认（接口第1个）: ai_time_id=17
# 如果接口数据更新了，会获取到新的时间ID
```

---

## ⚠️ 注意事项

### 1. 全局影响

**刷新缓存会影响所有用户**：
- 用户A刷新缓存
- 用户B的下次查询也会使用新数据

这是**预期行为**，因为数据本身就是全局共享的。

---

### 2. 并发安全

使用线程锁保证并发安全：
- 多个用户同时刷新不会冲突
- 数据一致性得到保证

---

### 3. 刷新时机

**建议**：
- 每天定时刷新一次
- 或发现数据不准确时手动刷新

**不建议**：
- 每次查询都刷新（浪费API调用）

---

## 📝 实现细节

### 清除缓存

```python
@staticmethod
def clear_cache():
    """清除所有全局缓存"""
    global _global_cache
    with _cache_lock:
        _global_cache['coins'] = None
        _global_cache['ai_time_id'] = None
        _global_cache['ai_time_list'] = None
        _global_cache['strategy_types'] = None
```

### 线程安全

- 使用 `threading.Lock` 保护
- 静态方法，可直接调用
- 不需要创建实例

---

## 🎯 使用示例

### 示例1: 定期刷新

```bash
#!/bin/bash
# 每天刷新一次缓存

# 清除缓存
python3 query.py --token $TOKEN --list-coins --refresh-cache > /dev/null

echo "缓存已刷新: $(date)"
```

---

### 示例2: 发现数据问题时

```bash
# 用户反馈：怎么没有新币种 XXX？

# 1. 刷新缓存
python3 smart_recommend.py --token $TOKEN --force-refresh --coins "BTC"

# 2. 验证是否有新币种
python3 query.py --token $TOKEN --list-coins
```

---

### 示例3: 脚本中使用

```python
from defaults import DefaultParams

# 执行前先刷新缓存
DefaultParams.clear_cache()

# 然后执行查询
from smart_recommend import SmartRecommender
recommender = SmartRecommender(token)
results = recommender.fetch_strategies(...)
```

---

## 📖 相关命令

### 查询命令

```bash
# 查看币种（使用缓存）
python3 query.py --token xxx --list-coins

# 查看币种（刷新缓存）
python3 query.py --token xxx --list-coins --refresh-cache

# 查看策略（使用缓存）
python3 query.py --token xxx --list-strategies

# 查看策略（刷新缓存）
python3 query.py --token xxx --list-strategies --refresh-cache
```

### 智能推荐

```bash
# 使用缓存
python3 smart_recommend.py --token xxx --coins "BTC"

# 强制刷新缓存
python3 smart_recommend.py --token xxx --force-refresh --coins "BTC"
```

---

## 🎉 总结

**全局缓存刷新功能**：

- ✅ 任何用户都可以强制刷新
- ✅ 刷新后所有用户看到新数据
- ✅ 线程安全
- ✅ 简单易用

**参数**：
- `smart_recommend.py --force-refresh`
- `query.py --refresh-cache`

**效果**：清除全局缓存，重新获取最新数据
