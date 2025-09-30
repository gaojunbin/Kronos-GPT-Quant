import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple


class PredictionAnalyzer:
    """
    预测结果分析器
    处理当前持仓信息
    """

    def __init__(self):
        self.symbols = ['BNBUSDT', 'ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT']


    def get_current_market_positions(self, binance_client) -> Dict:
        """获取当前市场仓位信息"""
        positions = {}
        balances = binance_client.get_all_balances()

        for asset, balance_info in balances.items():
            if balance_info['total'] > 0:
                # 获取对应USDT的价格
                try:
                    if asset != 'USDT':
                        symbol = f"{asset}USDT"
                        current_price = binance_client.get_current_price(symbol)
                        usd_value = balance_info['total'] * current_price
                        positions[asset] = {
                            'amount': balance_info['total'],
                            'current_price': current_price,
                            'usd_value': usd_value,
                            'free': balance_info['free'],
                            'locked': balance_info['locked']
                        }
                    else:
                        positions[asset] = {
                            'amount': balance_info['total'],
                            'current_price': 1.0,
                            'usd_value': balance_info['total'],
                            'free': balance_info['free'],
                            'locked': balance_info['locked']
                        }
                except Exception:
                    continue

        return positions