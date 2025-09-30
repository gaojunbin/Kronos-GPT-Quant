import os
from typing import List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class TradingConfig:
    """交易配置类"""

    # API配置
    BINANCE_API_KEY: str = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET: str = os.getenv('BINANCE_API_SECRET', '')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')

    # 交易策略配置
    MIN_TRADE_AMOUNT: float = float(os.getenv('MIN_TRADE_AMOUNT', '50.0'))
    MAX_SINGLE_TRADE: float = float(os.getenv('MAX_SINGLE_TRADE', '500.0'))
    MAX_TOTAL_EXPOSURE: float = float(os.getenv('MAX_TOTAL_EXPOSURE', '0.8'))

    # 监控的交易对
    SYMBOLS: List[str] = os.getenv('SYMBOLS', 'BNBUSDT,ETHUSDT,BTCUSDT,SOLUSDT,DOGEUSDT,ADAUSDT').split(',')

    # 风险管理
    STOP_LOSS_PERCENTAGE: float = float(os.getenv('STOP_LOSS_PERCENTAGE', '0.05'))
    MAX_SINGLE_POSITION: float = float(os.getenv('MAX_SINGLE_POSITION', '0.3'))

    # 系统配置
    SIMULATION_MODE: bool = os.getenv('SIMULATION_MODE', 'true').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # 通知配置（可选）
    PUSHPLUS_TOKEN: Optional[str] = os.getenv('PUSHPLUS_TOKEN')
    BOT_TOKEN: Optional[str] = os.getenv('BOT_TOKEN')
    CHAT_ID: Optional[str] = os.getenv('CHAT_ID')

    # Kronos模型配置
    PRED_HORIZON: int = 24  # 预测时间范围（小时）
    N_PREDICTIONS: int = 30  # 预测样本数
    VOL_WINDOW: int = 24  # 波动率计算窗口（小时）

    # ChatGPT配置
    CHATGPT_MODEL: str = "gpt-4"  # 可以改为 gpt-3.5-turbo
    CHATGPT_TEMPERATURE: float = 0.3  # 较低的温度获得更一致的结果
    CHATGPT_MAX_TOKENS: int = 1500

    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否完整"""
        required_fields = [
            'BINANCE_API_KEY',
            'BINANCE_API_SECRET',
            'OPENAI_API_KEY'
        ]

        missing_fields = []
        for field in required_fields:
            value = getattr(cls, field)
            if not value or value == '':
                missing_fields.append(field)

        if missing_fields:
            print(f"缺少必需的配置: {', '.join(missing_fields)}")
            print("请检查.env文件并设置相应的环境变量")
            return False

        return True

    @classmethod
    def print_config(cls):
        """打印当前配置（敏感信息会被隐藏）"""
        print("=== Kronos交易系统配置 ===")
        print(f"模拟模式: {cls.SIMULATION_MODE}")
        print(f"日志级别: {cls.LOG_LEVEL}")
        print(f"监控币种: {cls.SYMBOLS}")
        print(f"最小交易金额: ${cls.MIN_TRADE_AMOUNT}")
        print(f"最大单次交易: ${cls.MAX_SINGLE_TRADE}")
        print(f"最大总仓位: {cls.MAX_TOTAL_EXPOSURE * 100}%")
        print(f"止损比例: {cls.STOP_LOSS_PERCENTAGE * 100}%")
        print(f"最大单币种仓位: {cls.MAX_SINGLE_POSITION * 100}%")

        # 敏感信息隐藏显示
        api_key_masked = cls.BINANCE_API_KEY[:8] + '...' if cls.BINANCE_API_KEY else '未设置'
        openai_key_masked = cls.OPENAI_API_KEY[:8] + '...' if cls.OPENAI_API_KEY else '未设置'

        print(f"币安API密钥: {api_key_masked}")
        print(f"OpenAI API密钥: {openai_key_masked}")

        notification_enabled = bool(cls.PUSHPLUS_TOKEN or cls.BOT_TOKEN)
        print(f"通知功能: {'启用' if notification_enabled else '未启用'}")
        print("========================")


# 全局配置实例
config = TradingConfig()