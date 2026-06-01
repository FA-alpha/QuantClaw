#!/usr/bin/env python3
"""
日志查看工具 - 兼容 Wrapper

⚠️ 此文件已迁移到 scripts/logging/view_logs.py
   
为了向后兼容，这里保留一个 wrapper。
新代码应该使用：
    ./scripts/view-logs [选项]

旧代码可以继续使用：
    python3 skills/backtest-query/view_logs.py [选项]
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 从统一模块导入
from scripts.logging.view_logs import main

if __name__ == "__main__":
    main()
