#!/usr/bin/env python3
"""
Kronos智能交易系统启动脚本

用法:
  python run_trader.py            # 运行完整策略（预测+交易）
  python run_trader.py --once     # 只运行一次策略
  python run_trader.py --config   # 检查配置
  python run_trader.py --test     # 测试模式（只预测，不交易）
"""

import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from trader.config import config
from trader.main_strategy import KronosMainStrategy


def setup_logging():
    """设置日志配置"""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    # 创建日志目录
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 配置日志
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'kronos_trader.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # 设置第三方库日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def check_config():
    """检查配置"""
    print("正在检查Kronos交易系统配置...")
    config.print_config()

    if not config.validate_config():
        print("\n❌ 配置验证失败！")
        print("请检查.env文件并设置所有必需的环境变量。")
        return False

    print("\n✅ 配置验证通过！")
    return True


def run_once():
    """运行一次策略"""
    try:
        setup_logging()
        logger = logging.getLogger('RunOnce')

        if not check_config():
            return False

        logger.info("开始运行单次策略...")
        strategy = KronosMainStrategy()
        strategy.run_hourly_strategy()
        logger.info("单次策略执行完成")
        return True

    except Exception as e:
        logging.error(f"运行单次策略时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_continuous():
    """持续运行策略"""
    try:
        setup_logging()
        logger = logging.getLogger('RunContinuous')

        if not check_config():
            return False

        logger.info("开始持续运行策略...")
        strategy = KronosMainStrategy()

        # 首次立即执行
        strategy.run_hourly_strategy()

        # 进入持续模式
        strategy.run_continuous_strategy()

    except KeyboardInterrupt:
        logging.info("接收到停止信号，正在退出...")
    except Exception as e:
        logging.error(f"持续运行策略时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_test_mode():
    """测试模式 - 只进行预测分析，不执行交易"""
    try:
        setup_logging()
        logger = logging.getLogger('TestMode')

        logger.info("⚠️  运行在测试模式 - 将不会执行实际交易")

        if not check_config():
            return False

        # 临时设置为模拟模式
        original_simulation = config.SIMULATION_MODE
        config.SIMULATION_MODE = True

        strategy = KronosMainStrategy()
        strategy.run_hourly_strategy()

        # 恢复原始设置
        config.SIMULATION_MODE = original_simulation

        logger.info("测试模式执行完成")
        return True

    except Exception as e:
        logging.error(f"测试模式运行时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Kronos智能交易系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_trader.py              # 持续运行策略
  python run_trader.py --once       # 运行一次策略
  python run_trader.py --config     # 检查配置
  python run_trader.py --test       # 测试模式运行

注意事项:
- 首次使用前请确保已正确配置.env文件
- 建议先使用--test模式验证策略逻辑
- 实盘交易前请确保有足够的风险控制措施
        """
    )

    parser.add_argument('--once', action='store_true',
                        help='只运行一次策略')
    parser.add_argument('--config', action='store_true',
                        help='检查并显示配置信息')
    parser.add_argument('--test', action='store_true',
                        help='测试模式（只预测，不交易）')

    args = parser.parse_args()

    print("🚀 Kronos智能交易系统")
    print("=" * 50)

    try:
        if args.config:
            check_config()
        elif args.test:
            success = run_test_mode()
            sys.exit(0 if success else 1)
        elif args.once:
            success = run_once()
            sys.exit(0 if success else 1)
        else:
            # 默认持续运行
            run_continuous()

    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()