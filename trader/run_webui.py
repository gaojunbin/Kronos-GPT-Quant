#!/usr/bin/env python3
"""
Kronos Trader WebUI 独立启动脚本
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from trader.webui_server import run_server


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🚀 启动 Kronos Trader WebUI")
    print("=" * 50)
    print("访问地址: http://localhost:8000")
    print("=" * 50)

    # 启动服务器
    run_server(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()