import os
import logging
import asyncio
from typing import Dict, List, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime


class BinanceClient:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 从环境变量获取API密钥
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')

        if not self.api_key or not self.api_secret:
            raise ValueError("请在.env文件中配置BINANCE_API_KEY和BINANCE_API_SECRET")

        # 初始化Binance客户端
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.api_secret,
            tld='com'  # 使用全球站
        )

        self.logger.info("币安客户端初始化完成")

    def get_account_info(self):
        """获取账户信息"""
        try:
            return self.client.get_account()
        except BinanceAPIException as e:
            self.logger.error(f"获取账户信息失败: {e}")
            raise

    def get_balance(self, asset: str) -> float:
        """获取指定资产余额"""
        try:
            account = self.get_account_info()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return float(balance['free'])
            return 0.0
        except Exception as e:
            self.logger.error(f"获取{asset}余额失败: {e}")
            return 0.0

    def get_all_balances(self) -> Dict[str, float]:
        """获取所有非零余额"""
        try:
            account = self.get_account_info()
            balances = {}
            for balance in account['balances']:
                free_balance = float(balance['free'])
                locked_balance = float(balance['locked'])
                total_balance = free_balance + locked_balance
                if total_balance > 0:
                    balances[balance['asset']] = {
                        'free': free_balance,
                        'locked': locked_balance,
                        'total': total_balance
                    }
            return balances
        except Exception as e:
            self.logger.error(f"获取所有余额失败: {e}")
            return {}

    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            self.logger.error(f"获取{symbol}当前价格失败: {e}")
            raise

    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100):
        """获取K线数据"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return klines
        except BinanceAPIException as e:
            self.logger.error(f"获取{symbol} K线数据失败: {e}")
            raise

    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """下市价单"""
        try:
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError("side必须为BUY或SELL")

            order = self.client.order_market(
                symbol=symbol,
                side=side.upper(),
                quantity=quantity
            )

            self.logger.info(f"市价{side}单已下达: {symbol} 数量:{quantity}")
            return order

        except BinanceAPIException as e:
            self.logger.error(f"下{side}单失败: {e}")
            return None

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Optional[Dict]:
        """下限价单"""
        try:
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError("side必须为BUY或SELL")

            order = self.client.order_limit(
                symbol=symbol,
                side=side.upper(),
                quantity=quantity,
                price=str(price)
            )

            self.logger.info(f"限价{side}单已下达: {symbol} 数量:{quantity} 价格:{price}")
            return order

        except BinanceAPIException as e:
            self.logger.error(f"下限价{side}单失败: {e}")
            return None

    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """取消订单"""
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            self.logger.info(f"订单已取消: {symbol} 订单ID:{order_id}")
            return True
        except BinanceAPIException as e:
            self.logger.error(f"取消订单失败: {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取挂单"""
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()
            return orders
        except BinanceAPIException as e:
            self.logger.error(f"获取挂单失败: {e}")
            return []

    def get_order_status(self, symbol: str, order_id: int) -> Optional[Dict]:
        """获取订单状态"""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order
        except BinanceAPIException as e:
            self.logger.error(f"获取订单状态失败: {e}")
            return None