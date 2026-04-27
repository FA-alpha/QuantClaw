#!/usr/bin/env python3
"""
默认参数管理模块

集中管理所有从接口获取的默认参数，便于统一配置和修改。

注意：币种、策略类型、时间ID等数据是全局公共的，不是用户特定的。
因此使用全局缓存，所有用户共享同一份数据。
"""

from typing import List, Optional
import threading
from query import get_coin_list, get_ai_time_list, get_ai_strategy_list


# ============ 全局缓存（所有用户共享） ============
_global_cache = {
    'coins': None,
    'ai_time_id': None,
    'strategy_types': None,
}
_cache_lock = threading.Lock()


class DefaultParams:
    """
    默认参数管理器
    
    所有默认参数的获取逻辑集中在这里，方便统一修改：
    - 修改选取数量（如前3个改为前5个）
    - 修改选取逻辑（如按特定条件筛选）
    - 修改容错默认值
    """
    
    # ============ 配置区域（可修改） ============
    
    # 币种默认配置
    COIN_COUNT = None  # None表示获取全部，数字表示取前N个
    COIN_TYPE_FILTER = "CRYPTO"  # None=全部, "CRYPTO"=只要虚拟币, "US"=只要美股
    COIN_FALLBACK = ["BTC", "ETH", "SOL"]  # 容错默认值
    
    # 策略类型默认配置
    STRATEGY_COUNT = None  # None=获取全部, 数字=取前N个
    STRATEGY_FALLBACK = [11, 7, 1]  # 容错默认值（风霆、网格、鲲鹏）
    
    # 时间ID默认配置
    TIME_MODE = "all"  # "single"=只用第1个, "all"=全部16个, "top_n"=前N个
    TIME_COUNT = 3  # TIME_MODE="top_n"时使用，取前N个
    TIME_INDEX = 0  # TIME_MODE="single"时使用，取第N个
    TIME_FALLBACK = ["5"]  # 容错默认值（最近1年）
    
    # 方向默认配置
    DIRECTION_MODE = "all"  # "none"=不限, "all"=轮询long和short, "long_only"=只做多, "short_only"=只做空
    DIRECTION_FALLBACK = ["long", "short"]  # 容错默认值
    
    # 网格比例默认配置（仅对网格策略有效）
    GRID_PCT_MODE = "all"  # "none"=不限, "all"=轮询所有比例, "common"=只用常用比例
    GRID_PCT_BTC = ['10', '20', '30', '40', '50', '60', '80', '100', '120']  # BTC可选
    GRID_PCT_OTHER = ['60', '80', '100', '120', '140']  # 其他币种可选
    GRID_PCT_COMMON = ['80', '100', '120']  # 常用比例
    
    # 缓存配置
    ENABLE_CACHE = True  # 是否启用缓存
    
    # ============ 实现代码（一般不需要修改） ============
    
    def __init__(self, token: str, verbose: bool = True):
        """
        初始化默认参数管理器
        
        Args:
            token: 用户 token（仅用于首次获取数据，数据是全局共享的）
            verbose: 是否输出日志
        """
        self.token = token
        self.verbose = verbose
    
    def log(self, msg: str):
        """输出日志"""
        if self.verbose:
            print(msg)
    
    def get_coins(self, coin_type: Optional[str] = None) -> List[str]:
        """
        获取默认币种列表（全局共享）
        
        Args:
            coin_type: 币种类型过滤，None=全部, "CRYPTO"=虚拟币, "US"=美股
        
        Returns:
            List[str]: 币种列表
        """
        global _global_cache
        
        # 使用全局缓存
        if self.ENABLE_CACHE and _global_cache['coins'] is not None:
            coins_data = _global_cache['coins']
        else:
            with _cache_lock:
                # 双重检查
                if self.ENABLE_CACHE and _global_cache['coins'] is not None:
                    coins_data = _global_cache['coins']
                else:
                    try:
                        result = get_coin_list(self.token)
                        
                        if "error" in result:
                            self.log(f"⚠️  获取币种列表失败: {result['error']}")
                            _global_cache['coins'] = self.COIN_FALLBACK
                            return self.COIN_FALLBACK
                        
                        coins_data = result.get("info", [])
                        
                        if not coins_data:
                            self.log("⚠️  接口返回空数据")
                            _global_cache['coins'] = self.COIN_FALLBACK
                            return self.COIN_FALLBACK
                        
                        # 缓存完整的币种数据（包含type字段）
                        _global_cache['coins'] = coins_data
                    
                    except Exception as e:
                        self.log(f"⚠️  获取币种列表异常: {e}")
                        _global_cache['coins'] = self.COIN_FALLBACK
                        return self.COIN_FALLBACK
        
        # 根据配置和参数过滤
        filter_type = coin_type or self.COIN_TYPE_FILTER
        
        if filter_type:
            # 按类型过滤
            filtered = [c["coin"] for c in coins_data if isinstance(c, dict) and c.get("type") == filter_type]
            if not filtered:
                self.log(f"⚠️  没有找到类型为 {filter_type} 的币种")
                return self.COIN_FALLBACK
            coins = filtered
        else:
            # 不过滤，获取全部
            coins = [c["coin"] if isinstance(c, dict) else c for c in coins_data]
        
        # 如果配置了数量限制
        if self.COIN_COUNT is not None:
            coins = coins[:self.COIN_COUNT]
        
        return coins
    
    def get_ai_time_ids(self) -> List[str]:
        """
        获取时间ID列表（全局共享）
        
        根据 TIME_MODE 配置返回：
        - "single": 返回第1个
        - "all": 返回全部
        - "top_n": 返回前N个
        
        Returns:
            List[str]: 时间ID列表
        """
        global _global_cache
        
        # 先获取完整数据（会缓存）
        if self.ENABLE_CACHE and _global_cache.get('ai_time_list') is not None:
            times_data = _global_cache['ai_time_list']
        else:
            with _cache_lock:
                if self.ENABLE_CACHE and _global_cache.get('ai_time_list') is not None:
                    times_data = _global_cache['ai_time_list']
                else:
                    try:
                        result = get_ai_time_list(self.token)
                        if "error" in result:
                            _global_cache['ai_time_list'] = []
                            return [self.TIME_FALLBACK[0]]
                        times_data = result.get("info", [])
                        _global_cache['ai_time_list'] = times_data
                    except:
                        _global_cache['ai_time_list'] = []
                        return [self.TIME_FALLBACK[0]]
        
        if not times_data:
            return [self.TIME_FALLBACK[0]]
        
        # 根据模式返回
        if self.TIME_MODE == "single":
            if len(times_data) > self.TIME_INDEX:
                return [str(times_data[self.TIME_INDEX]["id"])]
            return [self.TIME_FALLBACK[0]]
        elif self.TIME_MODE == "all":
            return [str(t["id"]) for t in times_data]
        elif self.TIME_MODE == "top_n":
            return [str(t["id"]) for t in times_data[:self.TIME_COUNT]]
        else:
            return [str(times_data[0]["id"])]
    
    def get_ai_time_id(self) -> str:
        """
        获取默认时间ID（全局共享）
        
        Returns:
            str: 时间ID
        """
        global _global_cache
        
        # 使用全局缓存
        if self.ENABLE_CACHE and _global_cache['ai_time_id'] is not None:
            return _global_cache['ai_time_id']
        
        with _cache_lock:
            # 双重检查
            if self.ENABLE_CACHE and _global_cache['ai_time_id'] is not None:
                return _global_cache['ai_time_id']
            
            try:
                result = get_ai_time_list(self.token)
                
                if "error" in result:
                    self.log(f"⚠️  获取时间列表失败: {result['error']}")
                    _global_cache['ai_time_id'] = self.TIME_FALLBACK
                else:
                    times_data = result.get("info", [])
                    
                    # 取第N个时间ID
                    if len(times_data) > self.TIME_INDEX:
                        _global_cache['ai_time_id'] = str(times_data[self.TIME_INDEX]["id"])
                    else:
                        self.log("⚠️  接口返回数据不足")
                        _global_cache['ai_time_id'] = self.TIME_FALLBACK
            
            except Exception as e:
                self.log(f"⚠️  获取时间列表异常: {e}")
                _global_cache['ai_time_id'] = self.TIME_FALLBACK
        
        return _global_cache['ai_time_id']
    
    def get_strategy_types(self) -> List[int]:
        """
        获取默认策略类型列表（全局共享）
        
        Returns:
            List[int]: 策略类型ID列表
        """
        global _global_cache
        
        # 使用全局缓存
        if self.ENABLE_CACHE and _global_cache['strategy_types'] is not None:
            return _global_cache['strategy_types']
        
        with _cache_lock:
            # 双重检查
            if self.ENABLE_CACHE and _global_cache['strategy_types'] is not None:
                return _global_cache['strategy_types']
            
            try:
                result = get_ai_strategy_list(self.token)
                
                if "error" in result:
                    self.log(f"⚠️  获取策略列表失败: {result['error']}")
                    _global_cache['strategy_types'] = self.STRATEGY_FALLBACK
                else:
                    strategies_data = result.get("info", [])
                    
                    # 取前N个或全部策略类型
                    if self.STRATEGY_COUNT is None:
                        # 获取全部
                        _global_cache['strategy_types'] = [item["id"] for item in strategies_data]
                    else:
                        # 取前N个
                        _global_cache['strategy_types'] = [item["id"] for item in strategies_data[:self.STRATEGY_COUNT]]
                    
                    if not _global_cache['strategy_types']:
                        self.log("⚠️  接口返回空数据")
                        _global_cache['strategy_types'] = self.STRATEGY_FALLBACK
            
            except Exception as e:
                self.log(f"⚠️  获取策略列表异常: {e}")
                _global_cache['strategy_types'] = self.STRATEGY_FALLBACK
        
        return _global_cache['strategy_types']
    
    def get_directions(self) -> List[Optional[str]]:
        """
        获取方向列表
        
        根据 DIRECTION_MODE 配置返回：
        - "none": 返回 [None]（不限方向）
        - "all": 返回 ["long", "short"]
        - "long_only": 返回 ["long"]
        - "short_only": 返回 ["short"]
        
        Returns:
            List[Optional[str]]: 方向列表
        """
        if self.DIRECTION_MODE == "none":
            return [None]
        elif self.DIRECTION_MODE == "all":
            return ["long", "short"]
        elif self.DIRECTION_MODE == "long_only":
            return ["long"]
        elif self.DIRECTION_MODE == "short_only":
            return ["short"]
        else:
            return [None]
    
    def get_grid_pcts(self, coin: str = None) -> List[Optional[str]]:
        """
        获取网格比例列表
        
        Args:
            coin: 币种（BTC有特殊比例）
        
        根据 GRID_PCT_MODE 配置返回：
        - "none": 返回 [None]（不限比例）
        - "all": 返回所有可选比例
        - "common": 返回常用比例
        
        Returns:
            List[Optional[str]]: 比例列表
        """
        if self.GRID_PCT_MODE == "none":
            return [None]
        
        # 判断是否BTC
        is_btc = coin and 'BTC' in coin.upper()
        
        if self.GRID_PCT_MODE == "all":
            return self.GRID_PCT_BTC if is_btc else self.GRID_PCT_OTHER
        elif self.GRID_PCT_MODE == "common":
            return self.GRID_PCT_COMMON
        else:
            return [None]
    
    def get_coins_by_type(self) -> dict:
        """
        获取按类型分组的币种
        
        Returns:
            dict: {
                'CRYPTO': ['BTC', 'ETH', ...],
                'US': ['AAPL', 'TSLA', ...],
                'all': ['BTC', 'ETH', 'AAPL', ...]
            }
        """
        # 先获取全部币种数据（会触发缓存）
        self.get_coins()
        
        global _global_cache
        coins_data = _global_cache['coins']
        
        if not isinstance(coins_data, list) or not coins_data:
            return {
                'CRYPTO': self.COIN_FALLBACK,
                'US': [],
                'all': self.COIN_FALLBACK
            }
        
        crypto = [c["coin"] for c in coins_data if isinstance(c, dict) and c.get("type") == "CRYPTO"]
        us = [c["coin"] for c in coins_data if isinstance(c, dict) and c.get("type") == "US"]
        all_coins = [c["coin"] if isinstance(c, dict) else c for c in coins_data]
        
        return {
            'CRYPTO': crypto,
            'US': us,
            'all': all_coins
        }
    
    @staticmethod
    def clear_cache():
        """
        清除所有全局缓存
        
        注意：只清除，不重新获取。下次查询时才会重新获取。
        如果需要立即刷新，请使用 refresh_cache()
        """
        global _global_cache
        with _cache_lock:
            _global_cache['coins'] = None
            _global_cache['ai_time_id'] = None
            _global_cache['ai_time_list'] = None
            _global_cache['strategy_types'] = None
    
    @staticmethod
    def refresh_cache(token: str, verbose: bool = False):
        """
        刷新全局缓存（清除后立即重新获取）
        
        Args:
            token: 用户 token（用于重新获取数据）
            verbose: 是否输出日志
        """
        # 清除缓存
        DefaultParams.clear_cache()
        
        # 立即重新获取
        manager = DefaultParams(token, verbose)
        manager.get_coins()
        manager.get_ai_time_ids()
        manager.get_strategy_types()
        
        if verbose:
            print("✅ 全局缓存已刷新（重新获取了最新数据）")
    
    @staticmethod
    def get_cache_status() -> dict:
        """
        获取缓存状态
        
        Returns:
            dict: {
                'coins': bool,  # 是否已缓存
                'ai_time_id': bool,
                'strategy_types': bool
            }
        """
        global _global_cache
        return {
            'coins': _global_cache['coins'] is not None,
            'ai_time_id': _global_cache['ai_time_id'] is not None,
            'strategy_types': _global_cache['strategy_types'] is not None,
        }
    
    def get_all(self) -> dict:
        """
        一次性获取所有默认参数
        
        Returns:
            dict: {
                'coins': List[str],
                'ai_time_id': str,
                'strategy_types': List[int]
            }
        """
        return {
            'coins': self.get_coins(),
            'ai_time_id': self.get_ai_time_id(),
            'strategy_types': self.get_strategy_types()
        }


# ============ 便捷函数（向后兼容） ============

def get_default_coins(token: str, verbose: bool = False, coin_type: Optional[str] = None) -> List[str]:
    """
    获取默认币种列表（便捷函数）
    
    Args:
        token: 用户 token
        verbose: 是否输出日志
        coin_type: 币种类型过滤，None=全部, "CRYPTO"=虚拟币, "US"=美股
    
    Returns:
        List[str]: 币种列表
    """
    manager = DefaultParams(token, verbose)
    return manager.get_coins(coin_type=coin_type)


def get_default_ai_time_id(token: str, verbose: bool = False) -> str:
    """
    获取默认时间ID（便捷函数）
    
    Args:
        token: 用户 token
        verbose: 是否输出日志
    
    Returns:
        str: 时间ID
    """
    manager = DefaultParams(token, verbose)
    return manager.get_ai_time_id()


def get_default_strategy_types(token: str, verbose: bool = False) -> List[int]:
    """
    获取默认策略类型列表（便捷函数）
    
    Args:
        token: 用户 token
        verbose: 是否输出日志
    
    Returns:
        List[int]: 策略类型ID列表
    """
    manager = DefaultParams(token, verbose)
    return manager.get_strategy_types()


# ============ 全局缓存说明 ============

"""
## 重要：全局缓存机制

币种列表、策略类型列表、时间ID列表是**全局公共数据**，不是用户特定的。
因此使用全局缓存，所有用户共享同一份数据。

### 优势：
1. 节省 API 调用 - 只在第一次调用时获取数据
2. 提高性能 - 后续用户直接使用缓存
3. 数据一致性 - 所有用户看到相同的默认参数

### 缓存管理：
```python
# 查看缓存状态
status = DefaultParams.get_cache_status()
print(status)  # {'coins': True, 'ai_time_id': True, 'strategy_types': True}

# 清除缓存（强制重新获取）
DefaultParams.clear_cache()
```

### 线程安全：
使用 threading.Lock 保证多线程环境下的数据安全。
"""

# ============ 配置说明 ============

"""
## 如何修改默认参数？

### 1. 修改币种选取

在 DefaultParams 类的配置区域修改：

```python
# 币种配置
COIN_COUNT = None       # None=获取全部, 数字=取前N个
COIN_TYPE_FILTER = None # None=全部, "CRYPTO"=只要虚拟币, "US"=只要美股

# 示例：只要前5个币种
COIN_COUNT = 5

# 示例：只要虚拟币
COIN_TYPE_FILTER = "CRYPTO"

# 示例：只要美股
COIN_TYPE_FILTER = "US"

# 示例：只要前3个虚拟币
COIN_COUNT = 3
COIN_TYPE_FILTER = "CRYPTO"
```

### 2. 修改策略和时间选取

```python
STRATEGY_COUNT = 5      # 取前5个策略类型（原来是3个）
TIME_INDEX = 1          # 取第2个时间ID（原来是第1个）
```

### 3. 修改容错默认值

```python
COIN_FALLBACK = ["BTC", "ETH", "BNB", "SOL"]  # 修改容错币种
STRATEGY_FALLBACK = [11, 8, 7]                # 修改容错策略
TIME_FALLBACK = "16"                          # 修改容错时间ID
```

### 4. 修改缓存策略

```python
ENABLE_CACHE = False  # 禁用缓存，每次都重新获取
```

### 5. 按类型获取币种（新功能）

```python
from defaults import DefaultParams

manager = DefaultParams(token)

# 方法1：获取特定类型
crypto_coins = manager.get_coins(coin_type="CRYPTO")  # 只要虚拟币
us_coins = manager.get_coins(coin_type="US")          # 只要美股
all_coins = manager.get_coins()                       # 全部

# 方法2：获取分组结果
by_type = manager.get_coins_by_type()
print(by_type['CRYPTO'])  # ['BTC', 'ETH', 'SOL', ...]
print(by_type['US'])      # ['AAPL', 'TSLA', 'NVDA', ...]
print(by_type['all'])     # 全部币种
```

## 使用示例

### 方式1：使用便捷函数（推荐）

```python
from defaults import get_default_coins, get_default_ai_time_id

coins = get_default_coins(token)
ai_time_id = get_default_ai_time_id(token)
```

### 方式2：使用管理器（推荐用于批量获取）

```python
from defaults import DefaultParams

manager = DefaultParams(token, verbose=True)
all_defaults = manager.get_all()

coins = all_defaults['coins']
ai_time_id = all_defaults['ai_time_id']
strategy_types = all_defaults['strategy_types']
```

### 方式3：自定义配置

```python
from defaults import DefaultParams

# 临时修改配置
DefaultParams.COIN_COUNT = 5
DefaultParams.TIME_INDEX = 1

manager = DefaultParams(token)
coins = manager.get_coins()  # 取前5个
```
"""
