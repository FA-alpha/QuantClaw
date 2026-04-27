#!/usr/bin/env python3
"""
默认参数管理模块

集中管理所有从接口获取的默认参数，便于统一配置和修改。
"""

from typing import List, Optional
from query import get_coin_list, get_ai_time_list, get_ai_strategy_list


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
    COIN_COUNT = 3  # 取前N个币种
    COIN_FALLBACK = ["BTC", "ETH", "SOL"]  # 容错默认值
    
    # 策略类型默认配置
    STRATEGY_COUNT = 3  # 取前N个策略类型
    STRATEGY_FALLBACK = [11, 7, 1]  # 容错默认值（风霆、网格、鲲鹏）
    
    # 时间ID默认配置
    TIME_INDEX = 0  # 取第N个时间ID（0表示第1个）
    TIME_FALLBACK = "5"  # 容错默认值（最近1年）
    
    # 缓存配置
    ENABLE_CACHE = True  # 是否启用缓存
    
    # ============ 实现代码（一般不需要修改） ============
    
    def __init__(self, token: str, verbose: bool = True):
        """
        初始化默认参数管理器
        
        Args:
            token: 用户 token
            verbose: 是否输出日志
        """
        self.token = token
        self.verbose = verbose
        
        # 缓存
        self._coins = None
        self._ai_time_id = None
        self._strategy_types = None
    
    def log(self, msg: str):
        """输出日志"""
        if self.verbose:
            print(msg)
    
    def get_coins(self) -> List[str]:
        """
        获取默认币种列表
        
        Returns:
            List[str]: 币种列表
        """
        # 使用缓存
        if self.ENABLE_CACHE and self._coins is not None:
            return self._coins
        
        try:
            result = get_coin_list(self.token)
            
            if "error" in result:
                self.log(f"⚠️  获取币种列表失败: {result['error']}")
                self._coins = self.COIN_FALLBACK
            else:
                coins_data = result.get("info", [])
                
                # 取前N个币种
                self._coins = [item["coin"] for item in coins_data[:self.COIN_COUNT]]
                
                if not self._coins:
                    self.log("⚠️  接口返回空数据")
                    self._coins = self.COIN_FALLBACK
        
        except Exception as e:
            self.log(f"⚠️  获取币种列表异常: {e}")
            self._coins = self.COIN_FALLBACK
        
        return self._coins
    
    def get_ai_time_id(self) -> str:
        """
        获取默认时间ID
        
        Returns:
            str: 时间ID
        """
        # 使用缓存
        if self.ENABLE_CACHE and self._ai_time_id is not None:
            return self._ai_time_id
        
        try:
            result = get_ai_time_list(self.token)
            
            if "error" in result:
                self.log(f"⚠️  获取时间列表失败: {result['error']}")
                self._ai_time_id = self.TIME_FALLBACK
            else:
                times_data = result.get("info", [])
                
                # 取第N个时间ID
                if len(times_data) > self.TIME_INDEX:
                    self._ai_time_id = str(times_data[self.TIME_INDEX]["id"])
                else:
                    self.log("⚠️  接口返回数据不足")
                    self._ai_time_id = self.TIME_FALLBACK
        
        except Exception as e:
            self.log(f"⚠️  获取时间列表异常: {e}")
            self._ai_time_id = self.TIME_FALLBACK
        
        return self._ai_time_id
    
    def get_strategy_types(self) -> List[int]:
        """
        获取默认策略类型列表
        
        Returns:
            List[int]: 策略类型ID列表
        """
        # 使用缓存
        if self.ENABLE_CACHE and self._strategy_types is not None:
            return self._strategy_types
        
        try:
            result = get_ai_strategy_list(self.token)
            
            if "error" in result:
                self.log(f"⚠️  获取策略列表失败: {result['error']}")
                self._strategy_types = self.STRATEGY_FALLBACK
            else:
                strategies_data = result.get("info", [])
                
                # 取前N个策略类型
                self._strategy_types = [item["id"] for item in strategies_data[:self.STRATEGY_COUNT]]
                
                if not self._strategy_types:
                    self.log("⚠️  接口返回空数据")
                    self._strategy_types = self.STRATEGY_FALLBACK
        
        except Exception as e:
            self.log(f"⚠️  获取策略列表异常: {e}")
            self._strategy_types = self.STRATEGY_FALLBACK
        
        return self._strategy_types
    
    def clear_cache(self):
        """清除所有缓存"""
        self._coins = None
        self._ai_time_id = None
        self._strategy_types = None
    
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

def get_default_coins(token: str, verbose: bool = False) -> List[str]:
    """
    获取默认币种列表（便捷函数）
    
    Args:
        token: 用户 token
        verbose: 是否输出日志
    
    Returns:
        List[str]: 币种列表
    """
    manager = DefaultParams(token, verbose)
    return manager.get_coins()


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


# ============ 配置说明 ============

"""
## 如何修改默认参数？

### 1. 修改选取数量

在 DefaultParams 类的配置区域修改：

```python
COIN_COUNT = 5          # 取前5个币种（原来是3个）
STRATEGY_COUNT = 5      # 取前5个策略类型（原来是3个）
TIME_INDEX = 1          # 取第2个时间ID（原来是第1个）
```

### 2. 修改容错默认值

```python
COIN_FALLBACK = ["BTC", "ETH", "BNB", "SOL"]  # 修改容错币种
STRATEGY_FALLBACK = [11, 8, 7]                # 修改容错策略
TIME_FALLBACK = "16"                          # 修改容错时间ID
```

### 3. 修改缓存策略

```python
ENABLE_CACHE = False  # 禁用缓存，每次都重新获取
```

### 4. 修改选取逻辑（高级）

如果需要按特定条件筛选，可以修改 get_coins() 等方法：

```python
def get_coins(self) -> List[str]:
    result = get_coin_list(self.token)
    coins_data = result.get("info", [])
    
    # 示例：只选择主流币种
    main_coins = ["BTC", "ETH", "SOL", "BNB"]
    self._coins = [c["coin"] for c in coins_data if c["coin"] in main_coins][:self.COIN_COUNT]
    
    return self._coins
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
