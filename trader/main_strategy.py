import os
import sys
import logging
import time
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytz
import numpy as np
import pandas as pd

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from model import KronosPredictor, KronosTokenizer, Kronos
from update_predictions import load_model, main_task, fetch_binance_data, make_prediction, calculate_metrics
from trader.binance_client import BinanceClient
from trader.prediction_analyzer import PredictionAnalyzer
from trader.chatgpt_client import ChatGPTClient
from trader.state_manager import get_state_manager


def convert_to_json_serializable(obj):
    """递归转换对象为JSON可序列化的格式"""
    if isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_to_json_serializable(obj.tolist())
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    else:
        return obj


class KronosMainStrategy:
    """
    Kronos主交易策略
    每小时运行一次，基于价格预测和ChatGPT分析执行交易
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 初始化所有组件
        try:
            self.kronos_predictor = load_model()
            self.binance_client = BinanceClient()
            self.prediction_analyzer = PredictionAnalyzer()
            self.chatgpt_client = ChatGPTClient()
            self.state_manager = get_state_manager()
        except Exception as e:
            self.logger.error(f"初始化组件失败: {e}")
            raise

        # 配置参数
        self.symbols = ['BNBUSDT', 'ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT']
        self.min_trade_amount = 50.0  # 最小交易金额 USDT
        self.max_single_trade = 500.0  # 单次最大交易金额 USDT
        self.max_total_exposure = 0.8  # 最大总仓位比例

        # 更新系统状态
        self._update_system_status(is_running=True)

        self.logger.info("Kronos主策略初始化完成")

    def run_hourly_strategy(self):
        """执行每小时策略"""
        try:
            singapore_time = datetime.now(pytz.timezone('Asia/Singapore'))
            self.logger.info(f"开始执行每小时策略 - {singapore_time.strftime('%Y-%m-%d %H:%M:%S SGT')}")

            # 更新系统状态
            self._update_system_status(
                last_strategy_run=singapore_time.isoformat()
            )
            self._add_log("开始执行策略周期", "info")

            # 1. 运行价格预测
            self.logger.info("步骤1: 运行价格预测...")
            self._add_log("运行价格预测", "info")
            predictions_data = self._run_predictions()
            self._update_predictions(predictions_data)

            # 2. 获取历史数据
            self.logger.info("步骤2: 获取历史数据...")
            historical_data = self._get_historical_data()

            # 3. 获取当前持仓和市场数据
            self.logger.info("步骤3: 获取市场数据和持仓信息...")
            self._add_log("获取市场数据和持仓信息", "info")
            position_info = self.prediction_analyzer.get_current_market_positions(self.binance_client)
            self._update_positions(position_info)
            market_data = self._get_current_market_data()

            # 4. 使用ChatGPT分析交易信号
            self.logger.info("步骤4: 使用ChatGPT分析交易信号...")
            self._add_log("使用ChatGPT分析交易信号", "info")
            trading_advice = self.chatgpt_client.analyze_trading_signals(
                predictions_data, historical_data, position_info, market_data
            )

            # 5. 执行交易决策
            self.logger.info("步骤5: 执行交易决策...")
            self._add_log("执行交易决策", "info")
            self._execute_trading_decisions(trading_advice)

            # 6. 记录策略执行结果
            self._log_strategy_results(predictions_data, historical_data, trading_advice)

            # 更新系统状态
            self._update_system_status(total_runs=self.state_manager.system_status.get("total_runs", 0) + 1)
            self._add_log("策略执行周期完成", "success")

            self.logger.info("每小时策略执行完成")

        except Exception as e:
            self.logger.error(f"执行每小时策略时发生错误: {e}")
            self._add_log(f"策略执行错误: {str(e)}", "error")
            self._update_system_status(
                error_count=self.state_manager.system_status.get("error_count", 0) + 1
            )
            import traceback
            traceback.print_exc()

    def _run_predictions(self) -> dict:
        """运行价格预测，返回预测数据"""
        try:
            # 使用现有的main_task函数进行预测
            # 由于main_task会更新HTML，我们需要提取其核心逻辑
            predictions_data = {
                "last_updated": datetime.now(pytz.timezone('Asia/Singapore')).strftime('%Y-%m-%d %H:%M:%S'),
                "symbols": {}
            }

            # 对每个币种进行预测
            for symbol in self.symbols:
                try:
                    self.logger.info(f"预测币种: {symbol}")

                    # 获取数据
                    df_full = fetch_binance_data(symbol)
                    df_for_model = df_full.iloc[:-1]

                    # 执行预测
                    close_preds, volume_preds, v_close_preds = make_prediction(
                        df_for_model, self.kronos_predictor
                    )

                    # 计算指标
                    hist_df_for_metrics = df_for_model.tail(24)  # 使用24小时数据
                    upside_prob, vol_amp_prob = calculate_metrics(
                        hist_df_for_metrics, close_preds, v_close_preds
                    )

                    # 保存预测结果
                    predictions_data["symbols"][symbol] = {
                        "upside_prob": f"{upside_prob:.1%}",
                        "vol_amp_prob": f"{vol_amp_prob:.1%}",
                        "current_price": float(df_full['close'].iloc[-1]),
                        "prediction_stats": {
                            "mean_prediction": float(close_preds.mean(axis=1).iloc[-1]),
                            "min_prediction": float(close_preds.min(axis=1).iloc[-1]),
                            "max_prediction": float(close_preds.max(axis=1).iloc[-1])
                        }
                    }

                    self.logger.info(f"{symbol} 预测完成: 上涨概率 {upside_prob:.1%}")

                except Exception as e:
                    self.logger.error(f"预测 {symbol} 时发生错误: {e}")
                    predictions_data["symbols"][symbol] = {
                        "upside_prob": "N/A",
                        "vol_amp_prob": "N/A",
                        "error": str(e)
                    }

            return predictions_data

        except Exception as e:
            self.logger.error(f"运行价格预测时发生错误: {e}")
            raise

    def _get_current_market_data(self) -> dict:
        """获取当前市场数据"""
        market_data = {}
        for symbol in self.symbols:
            try:
                price = self.binance_client.get_current_price(symbol)
                market_data[symbol] = price
            except Exception as e:
                self.logger.error(f"获取{symbol}价格失败: {e}")
                market_data[symbol] = 0.0
        return market_data

    def _get_historical_data(self) -> dict:
        """获取历史数据（价格和成交量）"""
        historical_data = {}
        for symbol in self.symbols:
            try:
                self.logger.info(f"获取{symbol}历史数据...")

                # 获取最近24小时的数据
                df_full = fetch_binance_data(symbol)

                # 获取最近24小时的数据
                recent_data = df_full.tail(24)

                historical_data[symbol] = {
                    'prices': recent_data['close'].tolist(),
                    'volumes': recent_data['volume'].tolist(),
                    'timestamps': recent_data['timestamps'].tolist(),
                    'high': recent_data['high'].tolist(),
                    'low': recent_data['low'].tolist(),
                    'open': recent_data['open'].tolist()
                }

            except Exception as e:
                self.logger.error(f"获取{symbol}历史数据失败: {e}")
                historical_data[symbol] = {
                    'prices': [],
                    'volumes': [],
                    'timestamps': [],
                    'high': [],
                    'low': [],
                    'open': []
                }

        return historical_data

    def _execute_trading_decisions(self, trading_advice: dict):
        """执行交易决策"""
        if not trading_advice.get('trading_actions'):
            self.logger.info("没有交易建议，保持当前持仓")
            return

        # 获取当前USDT余额
        usdt_balance = self.binance_client.get_balance('USDT')
        self.logger.info(f"当前USDT余额: ${usdt_balance:.2f}")

        # 计算总买入金额
        total_buy_amount = sum(
            action['quantity_usdt']
            for action in trading_advice['trading_actions']
            if action['action'] == 'BUY' and action['quantity_usdt'] > 0
        )

        if total_buy_amount > usdt_balance:
            self.logger.warning(f"总买入金额 ${total_buy_amount:.2f} 超过可用余额 ${usdt_balance:.2f}，将按比例调整")
            scale_factor = usdt_balance / total_buy_amount * 0.95  # 保留5%缓冲
        else:
            scale_factor = 1.0

        for action in trading_advice['trading_actions']:
            try:
                symbol = action['symbol']
                action_type = action['action']
                quantity_usdt = action['quantity_usdt']
                confidence = action['confidence']
                reason = action.get('reason', '无具体原因')

                self.logger.info(f"处理交易信号: {symbol} {action_type} ${quantity_usdt:.2f} (置信度: {confidence})")
                self.logger.info(f"交易理由: {reason}")

                if action_type == 'HOLD' or quantity_usdt == 0:
                    self.logger.info(f"{symbol}: 保持持仓")
                    continue

                # 检查交易金额是否在合理范围内
                if quantity_usdt < self.min_trade_amount:
                    self.logger.info(f"{symbol}: 交易金额 ${quantity_usdt:.2f} 低于最小金额，跳过")
                    continue

                # 对于BUY操作应用缩放因子
                if action_type == 'BUY':
                    quantity_usdt = quantity_usdt * scale_factor

                if quantity_usdt > self.max_single_trade:
                    self.logger.warning(f"{symbol}: 交易金额 ${quantity_usdt:.2f} 超过单次最大金额，调整为 ${self.max_single_trade}")
                    quantity_usdt = self.max_single_trade

                # 执行具体交易
                if action_type == 'BUY':
                    self._execute_buy_order(symbol, quantity_usdt, confidence, reason)
                elif action_type == 'SELL':
                    self._execute_sell_order(symbol, quantity_usdt, confidence, reason)

            except Exception as e:
                self.logger.error(f"执行交易 {symbol} {action_type} 时发生错误: {e}")

    def _execute_buy_order(self, symbol: str, usdt_amount: float, confidence: float, reason: str):
        """执行买入订单"""
        try:
            # 检查USDT余额是否足够
            usdt_balance = self.binance_client.get_balance('USDT')
            if usdt_balance < usdt_amount:
                self.logger.warning(f"USDT余额不足: 需要 ${usdt_amount}, 可用 ${usdt_balance}")
                return

            # 获取当前价格
            current_price = self.binance_client.get_current_price(symbol)

            # 计算购买数量
            quantity = usdt_amount / current_price

            # 获取交易对信息以确定精度
            # 这里简化处理，实际应该获取交易对的精度设置
            quantity = round(quantity, 6)  # 保留6位小数

            self.logger.info(f"执行买入: {symbol} 数量: {quantity} 金额: ${usdt_amount} 价格: ${current_price}")
            self.logger.info(f"买入理由: {reason} (置信度: {confidence})")

            # 下市价买单
            order = self.binance_client.place_market_order(symbol, 'BUY', quantity)

            if order:
                self.logger.info(f"买入订单成功: {symbol} 订单ID: {order.get('orderId', 'N/A')}")
                self._record_trade({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": quantity,
                    "price": current_price,
                    "volume_usdt": usdt_amount,
                    "confidence": confidence,
                    "reason": reason,
                    "status": "success",
                    "order_id": order.get('orderId', 'N/A')
                })
            else:
                self.logger.error(f"买入订单失败: {symbol}")
                self._record_trade({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": quantity,
                    "price": current_price,
                    "volume_usdt": usdt_amount,
                    "confidence": confidence,
                    "reason": reason,
                    "status": "failed"
                })

        except Exception as e:
            self.logger.error(f"执行买入订单时发生错误: {e}")
            self._add_log(f"买入订单错误 {symbol}: {str(e)}", "error")

    def _execute_sell_order(self, symbol: str, usdt_amount: float, confidence: float, reason: str):
        """执行卖出订单"""
        try:
            # 获取币种名称（去掉USDT后缀）
            base_asset = symbol.replace('USDT', '')

            # 获取当前持仓
            balance = self.binance_client.get_balance(base_asset)
            if balance <= 0:
                self.logger.info(f"没有{base_asset}持仓，无法卖出")
                return

            # 获取当前价格
            current_price = self.binance_client.get_current_price(symbol)

            # 计算要卖出的数量
            max_sell_quantity = balance
            target_sell_quantity = usdt_amount / current_price
            sell_quantity = min(max_sell_quantity, target_sell_quantity)

            # 精度处理
            sell_quantity = round(sell_quantity, 6)

            if sell_quantity <= 0:
                self.logger.info(f"卖出数量为0，跳过 {symbol}")
                return

            self.logger.info(f"执行卖出: {symbol} 数量: {sell_quantity} 预估金额: ${sell_quantity * current_price} 价格: ${current_price}")
            self.logger.info(f"卖出理由: {reason} (置信度: {confidence})")

            # 下市价卖单
            order = self.binance_client.place_market_order(symbol, 'SELL', sell_quantity)

            if order:
                self.logger.info(f"卖出订单成功: {symbol} 订单ID: {order.get('orderId', 'N/A')}")
                self._record_trade({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": sell_quantity,
                    "price": current_price,
                    "volume_usdt": sell_quantity * current_price,
                    "confidence": confidence,
                    "reason": reason,
                    "status": "success",
                    "order_id": order.get('orderId', 'N/A')
                })
            else:
                self.logger.error(f"卖出订单失败: {symbol}")
                self._record_trade({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": sell_quantity,
                    "price": current_price,
                    "volume_usdt": sell_quantity * current_price,
                    "confidence": confidence,
                    "reason": reason,
                    "status": "failed"
                })

        except Exception as e:
            self.logger.error(f"执行卖出订单时发生错误: {e}")
            self._add_log(f"卖出订单错误 {symbol}: {str(e)}", "error")

    def _log_strategy_results(self, predictions_data: dict, historical_data: dict, trading_advice: dict):
        """记录策略执行结果"""
        try:
            # 创建日志目录
            log_dir = Path(__file__).parent.parent / 'data' / 'strategy_logs'
            log_dir.mkdir(parents=True, exist_ok=True)

            # 生成日志文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f'strategy_{timestamp}.json'

            # 准备日志数据，转换为JSON可序列化格式
            log_data = convert_to_json_serializable({
                'timestamp': timestamp,
                'predictions': predictions_data,
                'historical_data': historical_data,
                'trading_advice': trading_advice,
                'execution_status': 'completed'
            })

            # 保存日志
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"策略执行日志已保存: {log_file}")

        except Exception as e:
            self.logger.error(f"保存策略日志时发生错误: {e}")

    def run_continuous_strategy(self):
        """持续运行策略（每小时执行一次）"""
        self.logger.info("开始持续策略执行模式")

        while True:
            try:
                # 计算下次运行时间（每小时的第5分钟）
                now = datetime.now(timezone.utc)
                next_run = (now + timedelta(hours=1)).replace(minute=5, second=0, microsecond=0)

                # 计算等待时间
                wait_seconds = (next_run - now).total_seconds()

                if wait_seconds > 0:
                    singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
                    next_singapore_time = next_run.astimezone(pytz.timezone('Asia/Singapore'))

                    self.logger.info(f"当前时间: {singapore_time.strftime('%Y-%m-%d %H:%M:%S SGT')}")
                    self.logger.info(f"下次执行时间: {next_singapore_time.strftime('%Y-%m-%d %H:%M:%S SGT')}")
                    self.logger.info(f"等待 {wait_seconds:.0f} 秒...")

                    # 更新下次运行时间
                    self._update_system_status(next_strategy_run=next_singapore_time.isoformat())

                    time.sleep(wait_seconds)

                # 执行策略
                self.run_hourly_strategy()

            except KeyboardInterrupt:
                self.logger.info("接收到停止信号，退出策略")
                self._update_system_status(is_running=False)
                break
            except Exception as e:
                self.logger.error(f"策略执行过程中发生错误: {e}")
                self._add_log(f"持续策略错误: {str(e)}", "error")
                self.logger.info("5分钟后重试...")
                time.sleep(300)  # 等待5分钟后重试

    def _update_system_status(self, **kwargs):
        """更新系统状态"""
        self.state_manager.update_state({
            "type": "system_status",
            "data": kwargs
        })

    def _update_positions(self, positions: dict):
        """更新持仓信息"""
        self.state_manager.update_state({
            "type": "positions",
            "data": positions
        })

    def _update_predictions(self, predictions: dict):
        """更新预测数据"""
        self.state_manager.update_state({
            "type": "predictions",
            "data": predictions
        })

    def _record_trade(self, trade_data: dict):
        """记录交易"""
        self.state_manager.update_state({
            "type": "trade_execution",
            "data": trade_data
        })
        self._add_log(
            f"交易执行: {trade_data['action']} {trade_data['symbol']} "
            f"{trade_data['quantity']} @ ${trade_data['price']:.4f}",
            "success" if trade_data['status'] == 'success' else "error"
        )

    def _add_log(self, message: str, level: str = "info"):
        """添加日志"""
        self.state_manager.update_state({
            "type": "strategy_log",
            "data": {
                "message": message,
                "level": level
            }
        })


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('kronos_strategy.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    try:
        # 创建并运行策略
        strategy = KronosMainStrategy()

        # 首次立即执行
        strategy.run_hourly_strategy()

        # 然后进入持续模式
        strategy.run_continuous_strategy()

    except Exception as e:
        logging.error(f"主函数执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()