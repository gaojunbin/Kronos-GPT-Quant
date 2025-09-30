import os
import logging
import json
import requests
from typing import Dict, Optional
import time


class ChatGPTClient:
    """
    ChatGPT API客户端
    用于与OpenAI GPT模型交互，分析预测结果并生成交易信号
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 从环境变量获取API密钥
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("请在.env文件中配置OPENAI_API_KEY")

        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4"  # 可以改为 gpt-3.5-turbo 以降低成本
        self.max_retries = 3
        self.retry_delay = 2

        self.logger.info("ChatGPT客户端初始化完成")

    def analyze_trading_signals(self, kronos_predictions: Dict, historical_data: Dict, position_info: Dict, market_data: Dict) -> Dict:
        """
        分析交易信号

        Args:
            kronos_predictions: Kronos模型的原始预测数据
            historical_data: 历史价格和成交量数据
            position_info: 当前持仓信息
            market_data: 市场数据（当前价格等）

        Returns:
            Dict: 包含买卖信号和数量的建议
        """

        # 构建提示词
        prompt = self._build_trading_prompt(kronos_predictions, historical_data, position_info, market_data)

        try:
            response = self._call_api(prompt)

            if response:
                # 解析ChatGPT的响应
                trading_advice = self._parse_trading_response(response)
                return trading_advice
            else:
                return self._get_default_response()

        except Exception as e:
            self.logger.error(f"分析交易信号时发生错误: {e}")
            return self._get_default_response()

    def _build_trading_prompt(self, kronos_predictions: Dict, historical_data: Dict, position_info: Dict, market_data: Dict) -> str:
        """构建发送给ChatGPT的提示词"""

        # 格式化Kronos预测数据
        predictions_summary = self._format_kronos_predictions(kronos_predictions)

        # 格式化历史数据
        historical_summary = self._format_historical_data(historical_data)

        # 格式化持仓信息
        position_summary = self._format_position_info(position_info)

        # 格式化市场数据
        market_summary = self._format_market_data(market_data)

        # 获取可用USDT余额
        usdt_balance = position_info.get('USDT', {}).get('amount', 0)

        prompt = f"""
你是一个专业的加密货币交易分析师。请根据以下信息分析并给出具体的交易建议：

【Kronos模型预测数据】
{predictions_summary}

【历史价格和成交量数据】
{historical_summary}

【当前持仓信息】
{position_summary}

【当前市场数据】
{market_summary}

【可用USDT余额】
${usdt_balance:.2f}

请严格按照以下JSON格式返回交易建议，不要添加任何其他文字说明：

{{
    "trading_actions": [
        {{
            "symbol": "BTCUSDT",
            "action": "BUY|SELL|HOLD",
            "quantity_usdt": 100.0,
            "confidence": 0.75,
            "reason": "基于模型预测上涨概率70%，建议适量做多"
        }}
    ],
    "risk_management": {{
        "total_risk_exposure": 0.3,
        "max_single_position": 500.0,
        "stop_loss_percentage": 0.05
    }},
    "market_outlook": "市场整体情绪乐观，建议适度增加仓位"
}}

交易规则（必须严格遵守）：
1. **重要**：你只有 ${usdt_balance:.2f} USDT可用余额，所有BUY操作的quantity_usdt总和不能超过这个金额
2. **重要**：综合分析所有币种，只选择1-3个最有潜力的币种进行交易，不要对每个币种都建议操作
3. 每次单个交易金额建议在50-500 USDT之间
4. 总仓位不超过可用资金的80%
5. 单个币种仓位不超过总资产的30%
6. 只有当上涨概率>60%时才建议BUY
7. 当上涨概率<40%时建议SELL，否则HOLD
8. 高波动性时适当降低仓位
9. 如果某个币种已经有大量持仓，避免继续加仓
10. 对于不操作的币种，使用HOLD并设置quantity_usdt为0
11. **优先考虑**：上涨概率最高且波动率适中的币种
12. 保留至少30%的USDT作为机动资金
"""

        return prompt

    def _format_kronos_predictions(self, kronos_predictions: Dict) -> str:
        """格式化Kronos预测数据"""
        if not kronos_predictions or 'symbols' not in kronos_predictions:
            return "暂无预测数据"

        lines = []
        lines.append(f"预测时间: {kronos_predictions.get('last_updated', '未知')}")
        lines.append("")

        for symbol, pred_data in kronos_predictions['symbols'].items():
            if 'error' in pred_data:
                lines.append(f"{symbol}: 预测失败 - {pred_data['error']}")
                continue

            lines.append(f"{symbol}:")

            # 添加预测统计数据
            if 'prediction_stats' in pred_data:
                stats = pred_data['prediction_stats']
                lines.append(f"  • 预测均值: {stats.get('mean_prediction', 0):.6f}")
                lines.append(f"  • 预测区间: [{stats.get('min_prediction', 0):.6f}, {stats.get('max_prediction', 0):.6f}]")

            lines.append(f"  • 上涨概率: {pred_data.get('upside_prob', 'N/A')}")
            lines.append(f"  • 高波动概率: {pred_data.get('vol_amp_prob', 'N/A')}")
            lines.append(f"  • 当前价格: {pred_data.get('current_price', 0):.6f}")
            lines.append("")

        return "\n".join(lines)

    def _format_historical_data(self, historical_data: Dict) -> str:
        """格式化历史数据"""
        if not historical_data:
            return "暂无历史数据"

        lines = []
        for symbol, data in historical_data.items():
            if not data:
                continue

            lines.append(f"{symbol} 最近24小时数据:")

            if 'prices' in data and len(data['prices']) > 0:
                prices = data['prices']
                lines.append(f"  • 价格变化: {prices[0]:.6f} → {prices[-1]:.6f}")
                lines.append(f"  • 价格变化率: {((prices[-1] - prices[0]) / prices[0] * 100):.2f}%")
                lines.append(f"  • 最高价: {max(prices):.6f}")
                lines.append(f"  • 最低价: {min(prices):.6f}")

            if 'volumes' in data and len(data['volumes']) > 0:
                volumes = data['volumes']
                avg_volume = sum(volumes) / len(volumes)
                lines.append(f"  • 平均成交量: {avg_volume:.2f}")
                lines.append(f"  • 最新成交量: {volumes[-1]:.2f}")

            lines.append("")

        return "\n".join(lines)

    def _format_position_info(self, position_info: Dict) -> str:
        """格式化持仓信息"""
        if not position_info:
            return "暂无持仓"

        lines = []
        total_value = 0

        for asset, info in position_info.items():
            usd_value = info.get('usd_value', 0)
            total_value += usd_value
            lines.append(f"{asset}: {info.get('amount', 0):.4f} (价值: ${usd_value:.2f})")

        lines.insert(0, f"总资产价值: ${total_value:.2f}")
        return "\n".join(lines)

    def _format_market_data(self, market_data: Dict) -> str:
        """格式化市场数据"""
        if not market_data:
            return "市场数据不可用"

        lines = []
        for symbol, price in market_data.items():
            lines.append(f"{symbol}: ${price:.4f}")

        return "\n".join(lines)

    def _call_api(self, prompt: str) -> Optional[str]:
        """调用ChatGPT API"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的加密货币交易分析师，擅长分析市场数据并给出精确的交易建议。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.3,  # 降低温度以获得更一致的结果
            "top_p": 0.9
        }

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"调用ChatGPT API (尝试 {attempt + 1}/{self.max_retries})")

                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    self.logger.info("ChatGPT API调用成功")
                    return content

                else:
                    self.logger.error(f"API调用失败，状态码: {response.status_code}, 响应: {response.text}")

            except requests.RequestException as e:
                self.logger.error(f"API请求异常: {e}")

            if attempt < self.max_retries - 1:
                self.logger.info(f"等待{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
                self.retry_delay *= 2  # 指数退避

        return None

    def _parse_trading_response(self, response: str) -> Dict:
        """解析ChatGPT的交易建议响应"""
        try:
            # 尝试从响应中提取JSON
            # 有时ChatGPT会在JSON前后添加说明文字
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                trading_advice = json.loads(json_str)

                # 验证响应格式
                if self._validate_trading_response(trading_advice):
                    self.logger.info("成功解析ChatGPT交易建议")
                    return trading_advice
                else:
                    self.logger.warning("ChatGPT响应格式不正确，使用默认建议")

        except json.JSONDecodeError as e:
            self.logger.error(f"解析ChatGPT响应JSON失败: {e}")
        except Exception as e:
            self.logger.error(f"解析ChatGPT响应时发生意外错误: {e}")

        return self._get_default_response()

    def _validate_trading_response(self, response: Dict) -> bool:
        """验证交易响应格式是否正确"""
        try:
            # 检查必需的字段
            if 'trading_actions' not in response:
                return False

            for action in response['trading_actions']:
                required_fields = ['symbol', 'action', 'quantity_usdt', 'confidence']
                if not all(field in action for field in required_fields):
                    return False

                # 验证action的值
                if action['action'] not in ['BUY', 'SELL', 'HOLD']:
                    return False

            return True

        except Exception:
            return False

    def _get_default_response(self) -> Dict:
        """获取默认的交易响应（保守策略）"""
        return {
            "trading_actions": [
                {
                    "symbol": "BTCUSDT",
                    "action": "HOLD",
                    "quantity_usdt": 0.0,
                    "confidence": 0.0,
                    "reason": "ChatGPT分析失败，采用保守策略"
                }
            ],
            "risk_management": {
                "total_risk_exposure": 0.1,
                "max_single_position": 100.0,
                "stop_loss_percentage": 0.03
            },
            "market_outlook": "由于分析系统异常，建议保持观望"
        }