#!/usr/bin/env python3
"""
db_connector.py - 数据库连接管理模块

功能:
1. 管理 backtest_optimizer 和 quantify 数据库连接
2. 提供统一的查询/更新接口
3. 自动处理连接池和异常
"""

import pymysql
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path


class DBConnector:
    """数据库连接管理器"""
    
    def __init__(self, config_path: str = None):
        """初始化数据库连接
        
        Args:
            config_path: 配置文件路径（绝对路径或相对路径）
                        如果为 None，按以下优先级查找：
                        1. ~/.config/okx_1m_add_config.yaml
                        2. 同目录下的 config.yaml
        """
        # 加载配置
        if config_path is None:
            # 默认优先级查找
            fallback_config = Path(__file__).parent / "config.yaml"
            
            config_file = fallback_config
        else:
            # 支持绝对路径和相对路径
            config_file = Path(config_path)
            if not config_file.is_absolute():
                # 相对路径：相对于当前文件所在目录
                config_file = Path(__file__).parent / config_path
            
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 检查配置格式
        if 'databases' not in self.config:
            raise ValueError(f"配置文件缺少 'databases' 字段: {config_file}")
        
        self.db_configs = self.config['databases']
        
        print(f"✅ DBConnector 已加载配置: {config_file}")
    
    def get_connection(self, db_name: str):
        """获取数据库连接
        
        Args:
            db_name: 数据库名称（backtest_optimizer 或 quantify）
        
        Returns:
            pymysql.Connection
        """
        if db_name not in self.db_configs:
            raise ValueError(f"未知的数据库名称: {db_name}")
        
        config = self.db_configs[db_name]
        return pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            port=config['port'],
            database=config['database'],
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def execute_query(self, db_name: str, query: str, params: tuple = None) -> List[Dict]:
        """执行查询（SELECT）
        
        Args:
            db_name: 数据库名称
            query: SQL 查询语句
            params: 参数元组
        
        Returns:
            查询结果列表
        """
        conn = self.get_connection(db_name)
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            conn.close()
    
    def execute_update(self, db_name: str, query: str, params: tuple = None) -> int:
        """执行更新（INSERT/UPDATE/DELETE）
        
        Args:
            db_name: 数据库名称
            query: SQL 语句
            params: 参数元组
        
        Returns:
            影响的行数
        """
        conn = self.get_connection(db_name)
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()
    
    def execute_many(self, db_name: str, query: str, data: List[tuple]) -> int:
        """批量执行（INSERT）
        
        Args:
            db_name: 数据库名称
            query: SQL 语句
            data: 数据列表
        
        Returns:
            影响的行数
        """
        conn = self.get_connection(db_name)
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, data)
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()
    
    # ============================================================
    # 业务方法：backtest_optimizer 数据库
    # ============================================================
    
    def get_max_back_id(self) -> int:
        """获取最大的 back_id（从2个表中取最大值）
        
        查询以下2个表：
        1. ml_backtest_record_v2_ai - 当前 AI 回测记录
        2. ml_backtest_record_ai_configs - 回测配置表（取 back_end_id）
        
        Returns:
            最大 back_id，如果所有表为空则返回 0
        """
        # 查询 ml_backtest_record_v2_ai
        query1 = "SELECT COALESCE(MAX(back_id), 0) as max_id FROM ml_backtest_record_v2_ai"
        result1 = self.execute_query('backtest_optimizer', query1)
        max_id_1 = result1[0]['max_id'] if result1 else 0
        
        # 查询 ml_backtest_record_ai_configs（取 end_back_id）这是看是否已经有预占位的
        query2 = "SELECT COALESCE(MAX(end_back_id), 0) as max_id FROM ml_backtest_record_ai_configs"
        result2 = self.execute_query('backtest_optimizer', query2)
        max_id_2 = result2[0]['max_id'] if result2 else 0
        
        # 返回三者中的最大值
        return max(max_id_1, max_id_2)
    
    def insert_backtest_placeholders(self, back_ids: List[int], coin: str, 
                                     bgn_date: str, end_date: str, name: str) -> int:
        """批量插入回测占位记录到 ml_backtest_record_v2_ai
        
        Args:
            back_ids: back_id 列表
            coin: 币种
            bgn_date: 开始日期 "YYYY-MM-DD"
            end_date: 结束日期 "YYYY-MM-DD"
            name: 时间段名称（如 "熊市"）
        
        Returns:
            插入的行数
        """
        query = """
        INSERT INTO ml_backtest_record_v2_ai 
        (back_id, coin, bgn_date, end_date, name)
        VALUES (%s, %s, %s, %s, %s)
        """
        data = [(bid, coin, bgn_date, end_date, name) for bid in back_ids]
        return self.execute_many('backtest_optimizer', query, data)
    
    def create_configs_table_if_not_exists(self):
        """创建 ml_backtest_record_ai_configs 表（如果不存在）
        
        注意：表已存在，字段名为 bgn_back_id, end_back_id, finish_count
        """
        query = """
        CREATE TABLE IF NOT EXISTS `ml_backtest_record_ai_configs` (
          `id` BIGINT NOT NULL AUTO_INCREMENT,
          `bgn_back_id` INT UNSIGNED NULL DEFAULT 0,
          `end_back_id` INT UNSIGNED NULL DEFAULT 0,
          `finish_count` INT UNSIGNED NULL DEFAULT 0,
          `create_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`)
        ) ENGINE = InnoDB CHARACTER SET = utf8mb3;
        """
        self.execute_update('backtest_optimizer', query)
    
    def insert_backtest_config(self, back_start_id: int, back_end_id: int, max_evals: int, market_count: int, agent_id: str = None) -> int:
        """插入回测配置到 ml_backtest_record_ai_configs
        
        Args:
            back_start_id: 开始 back_id
            back_end_id: 结束 back_id
            max_evals: 单次回测数量
            market_count: 市场行情数量
            agent_id: 任务来源标识（可选）
        
        Returns:
            插入的配置 ID
        """
        # 确保表存在
        self.create_configs_table_if_not_exists()
        
        # finish_count 初始值 = back_start_id - 1（表示还未开始）
        finish_count = back_start_id - 1
        
        # 如果提供了 agent_id，则插入到 agent_id 字段
        if agent_id:
            query = """
            INSERT INTO ml_backtest_record_ai_configs 
            (bgn_back_id, end_back_id, finish_count, agent_id)
            VALUES (%s, %s, %s, %s)
            """
            self.execute_update('backtest_optimizer', query, (back_start_id, back_end_id, finish_count, agent_id))
        else:
            query = """
            INSERT INTO ml_backtest_record_ai_configs 
            (bgn_back_id, end_back_id, finish_count)
            VALUES (%s, %s, %s)
            """
            self.execute_update('backtest_optimizer', query, (back_start_id, back_end_id, finish_count))
        
        # 获取刚插入的 ID
        result = self.execute_query('backtest_optimizer', "SELECT LAST_INSERT_ID() as id")
        return result[0]['id']
    
    def update_backtest_progress(self, config_id: int = None):
        """更新回测进度（finish_count + 1）
        
        Args:
            config_id: 配置 ID，如果为 None 则更新最新的一条
        """
        if config_id:
            query = """
            UPDATE ml_backtest_record_ai_configs 
            SET finish_count = finish_count + 1
            WHERE id = %s
            """
            self.execute_update('backtest_optimizer', query, (config_id,))
        else:
            # 更新最新的一条记录
            query = """
            UPDATE ml_backtest_record_ai_configs 
            SET finish_count = finish_count + 1
            WHERE id = (SELECT id FROM (SELECT id FROM ml_backtest_record_ai_configs ORDER BY id DESC LIMIT 1) as tmp)
            """
            self.execute_update('backtest_optimizer', query)
    
    def get_backtest_progress(self, config_id: int = None) -> Optional[Dict]:
        """获取回测进度
        
        Args:
            config_id: 配置 ID，如果为 None 则获取最新的一条
        
        Returns:
            进度信息字典，包含 bgn_back_id, end_back_id, finish_count
        """
        if config_id:
            query = """
            SELECT * FROM ml_backtest_record_ai_configs 
            WHERE id = %s
            """
            result = self.execute_query('backtest_optimizer', query, (config_id,))
        else:
            query = """
            SELECT * FROM ml_backtest_record_ai_configs 
            ORDER BY id DESC LIMIT 1
            """
            result = self.execute_query('backtest_optimizer', query)
        
        return result[0] if result else None
    
    def is_backtest_completed(self, config_id: int = None) -> bool:
        """检查回测是否完成
        
        Args:
            config_id: 配置 ID，如果为 None 则检查最新的一条
        
        Returns:
            True 如果完成，False 未完成
        """
        progress = self.get_backtest_progress(config_id)
        if not progress:
            return False
        
        # 当 finish_count == end_back_id 时，表示回测完成
        return progress['finish_count'] == progress['end_back_id']
    
    # ============================================================
    # 业务方法：quantify 数据库
    # ============================================================
    
    def check_coin_data_exists(self, coin: str, type_: str = "swap", year: int = None) -> bool:
        """检查币种数据是否存在（K线表）
        
        Args:
            coin: 币种名称（如 "BTC"）
            type_: "swap"（合约）或 "spot"（现货）
            year: 年份，如果为 None 则检查任意年份
        
        Returns:
            True 如果存在，False 不存在
        """
        coin_lower = coin.lower()
        type_suffix = "_swap" if type_ == "swap" else ""
        
        if year:
            pattern = f"ml_{coin_lower}{type_suffix}_history_1m_{year}"
        else:
            pattern = f"ml_{coin_lower}{type_suffix}_history_1m_%"
        
        query = "SHOW TABLES LIKE %s"
        result = self.execute_query('quantify', query, (pattern,))
        return len(result) > 0
    
    def get_price_at_date(self, coin: str, date: str, type_: str = "swap") -> Optional[float]:
        """获取指定日期 00:00 的开盘价格
        
        Args:
            coin: 币种名称
            date: 日期 "YYYY-MM-DD"
            type_: "swap" 或 "spot"
        
        Returns:
            开盘价格（float），如果不存在则返回 None
        """
        from datetime import datetime
        
        coin_lower = coin.lower()
        type_suffix = "_swap" if type_ == "swap" else ""
        year = datetime.strptime(date, "%Y-%m-%d").year
        table_name = f"ml_{coin_lower}{type_suffix}_history_1m_{year}"
        
        # 转换日期为时间戳（00:00）
        dt = datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")
        timestamp = int(dt.timestamp())
        
        query = f"""
        SELECT `open` FROM {table_name}
        WHERE time = %s
        LIMIT 1
        """
        
        try:
            result = self.execute_query('quantify', query, (timestamp,))
            if result:
                return float(result[0]['open'])
        except:
            pass
        
        return None
    
    def get_latest_table_update_time(self, coin: str, type_: str = "swap") -> Optional[int]:
        """获取币种 K 线表的最新更新时间（时间戳）
        
        Args:
            coin: 币种名称
            type_: "swap" 或 "spot"
        
        Returns:
            最新的时间戳，如果表不存在则返回 None
        """
        from datetime import datetime
        
        coin_lower = coin.lower()
        type_suffix = "_swap" if type_ == "swap" else ""
        current_year = datetime.now().year
        table_name = f"ml_{coin_lower}{type_suffix}_history_1m_{current_year}"
        
        query = f"""
        SELECT MAX(time) as max_time FROM {table_name}
        """
        
        try:
            result = self.execute_query('quantify', query)
            if result and result[0]['max_time']:
                return int(result[0]['max_time'])
        except:
            pass
        
        return None


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    db = DBConnector()
    
    print("🔍 测试数据库连接...")
    
    # 测试获取最大 back_id
    max_id = db.get_max_back_id()
    print(f"✅ 最大 back_id: {max_id}")
    
    # 测试检查币种数据
    btc_exists = db.check_coin_data_exists("BTC", "swap")
    print(f"✅ BTC 数据存在: {btc_exists}")
    
    # 测试获取价格
    price = db.get_price_at_date("BTC", "2025-01-01", "swap")
    print(f"✅ BTC 2025-01-01 价格: {price}")
    
    print("\n✅ 数据库连接模块测试完成！")
