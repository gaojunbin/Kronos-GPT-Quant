"""
Kronos Trader 状态管理器
用于存储和管理交易系统的实时状态数据
"""

import json
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import deque
import requests


class StateManager:
    """
    线程安全的状态管理器
    存储交易系统的所有状态信息
    """

    def __init__(self, max_history: int = 1000, webui_url: str = None):
        """
        初始化状态管理器

        Args:
            max_history: 保存的最大历史记录数
            webui_url: WebUI服务的URL，用于推送状态更新
        """
        self.lock = threading.RLock()
        self.max_history = max_history
        self.webui_url = webui_url or "http://kronos-trader-webui:8000"
        self.logger = logging.getLogger(self.__class__.__name__)

        # 系统运行状态
        self.system_status = {
            "is_running": False,
            "last_update": None,
            "last_strategy_run": None,
            "next_strategy_run": None,
            "simulation_mode": True,
            "error_count": 0,
            "total_runs": 0
        }

        # 当前持仓
        self.positions = {}

        # 最新预测数据
        self.predictions = {}

        # 交易历史
        self.trading_history = deque(maxlen=max_history)

        # 策略日志
        self.strategy_logs = deque(maxlen=max_history)

        # 性能统计
        self.performance_stats = {
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_profit_loss": 0.0,
            "total_volume": 0.0,
            "start_balance": 0.0,
            "current_balance": 0.0
        }

        # 风险指标
        self.risk_metrics = {
            "total_exposure": 0.0,
            "max_single_position": 0.0,
            "position_count": 0,
            "usdt_reserve": 0.0,
            "total_value": 0.0
        }

    def update_state(self, state_data: dict):
        """
        更新系统状态

        Args:
            state_data: 状态数据字典
        """
        with self.lock:
            update_type = state_data.get("type")

            if update_type == "system_status":
                self._update_system_status(state_data.get("data", {}))

            elif update_type == "positions":
                self._update_positions(state_data.get("data", {}))

            elif update_type == "predictions":
                self._update_predictions(state_data.get("data", {}))

            elif update_type == "trade_execution":
                self._record_trade(state_data.get("data", {}))

            elif update_type == "strategy_log":
                self._add_strategy_log(state_data.get("data", {}))

            elif update_type == "performance":
                self._update_performance(state_data.get("data", {}))

            elif update_type == "risk_metrics":
                self._update_risk_metrics(state_data.get("data", {}))

            # 更新最后更新时间
            self.system_status["last_update"] = datetime.now().isoformat()

            # 推送状态到WebUI
            self._push_to_webui(state_data)

    def _update_system_status(self, data: dict):
        """更新系统运行状态"""
        self.system_status.update(data)

    def _update_positions(self, data: dict):
        """更新持仓信息"""
        self.positions = data

        # 同时更新风险指标
        self._calculate_risk_metrics()

    def _update_predictions(self, data: dict):
        """更新预测数据"""
        self.predictions = data

    def _record_trade(self, trade_data: dict):
        """记录交易"""
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            **trade_data
        }
        self.trading_history.append(trade_record)

        # 更新性能统计
        self.performance_stats["total_trades"] += 1
        if trade_data.get("status") == "success":
            self.performance_stats["successful_trades"] += 1
        else:
            self.performance_stats["failed_trades"] += 1

        if "volume_usdt" in trade_data:
            self.performance_stats["total_volume"] += trade_data["volume_usdt"]

    def _add_strategy_log(self, log_data: dict):
        """添加策略日志"""
        log_record = {
            "timestamp": datetime.now().isoformat(),
            **log_data
        }
        self.strategy_logs.append(log_record)

    def _update_performance(self, data: dict):
        """更新性能统计"""
        self.performance_stats.update(data)

    def _update_risk_metrics(self, data: dict):
        """更新风险指标"""
        self.risk_metrics.update(data)

    def _calculate_risk_metrics(self):
        """根据当前持仓计算风险指标"""
        if not self.positions:
            return

        total_value = 0.0
        max_position = 0.0
        position_count = 0
        usdt_reserve = 0.0

        for asset, info in self.positions.items():
            usd_value = info.get("usd_value", 0.0)
            total_value += usd_value

            if asset == "USDT":
                usdt_reserve = usd_value
            else:
                position_count += 1
                max_position = max(max_position, usd_value)

        # 计算总敞口（非USDT资产占比）
        total_exposure = (total_value - usdt_reserve) / total_value if total_value > 0 else 0.0

        self.risk_metrics.update({
            "total_exposure": total_exposure,
            "max_single_position": max_position,
            "position_count": position_count,
            "usdt_reserve": usdt_reserve,
            "total_value": total_value
        })

    def _push_to_webui(self, state_data: dict):
        """
        推送状态更新到WebUI服务

        Args:
            state_data: 状态数据字典
        """
        try:
            response = requests.post(
                f"{self.webui_url}/api/update-state",
                json=state_data,
                timeout=5
            )
            if response.status_code != 200:
                self.logger.warning(f"推送状态到WebUI失败: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"无法连接到WebUI服务: {e}")

    def get_system_status(self) -> dict:
        """获取系统运行状态"""
        with self.lock:
            return self.system_status.copy()

    def get_positions(self) -> dict:
        """获取当前持仓"""
        with self.lock:
            return self.positions.copy()

    def get_predictions(self) -> dict:
        """获取最新预测"""
        with self.lock:
            return self.predictions.copy()

    def get_trading_history(self, limit: int = 50) -> List[dict]:
        """获取交易历史"""
        with self.lock:
            history = list(self.trading_history)
            return history[-limit:] if limit else history

    def get_strategy_logs(self, limit: int = 100) -> List[dict]:
        """获取策略日志"""
        with self.lock:
            logs = list(self.strategy_logs)
            return logs[-limit:] if limit else logs

    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        with self.lock:
            return self.performance_stats.copy()

    def get_risk_metrics(self) -> dict:
        """获取风险指标"""
        with self.lock:
            return self.risk_metrics.copy()

    def save_state(self, file_path: Path):
        """
        保存状态到文件

        Args:
            file_path: 保存路径
        """
        with self.lock:
            state_data = {
                "system_status": self.system_status,
                "positions": self.positions,
                "predictions": self.predictions,
                "trading_history": list(self.trading_history),
                "strategy_logs": list(self.strategy_logs),
                "performance_stats": self.performance_stats,
                "risk_metrics": self.risk_metrics,
                "saved_at": datetime.now().isoformat()
            }

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

    def load_state(self, file_path: Path):
        """
        从文件加载状态

        Args:
            file_path: 加载路径
        """
        if not file_path.exists():
            return

        with self.lock:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            self.system_status = state_data.get("system_status", self.system_status)
            self.positions = state_data.get("positions", {})
            self.predictions = state_data.get("predictions", {})
            self.performance_stats = state_data.get("performance_stats", self.performance_stats)
            self.risk_metrics = state_data.get("risk_metrics", self.risk_metrics)

            # 恢复历史记录
            trading_history = state_data.get("trading_history", [])
            self.trading_history = deque(trading_history, maxlen=self.max_history)

            strategy_logs = state_data.get("strategy_logs", [])
            self.strategy_logs = deque(strategy_logs, maxlen=self.max_history)


# 全局状态管理器实例
_global_state_manager = None


def get_state_manager() -> StateManager:
    """获取全局状态管理器实例"""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager()
    return _global_state_manager