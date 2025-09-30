"""
Kronos Trader WebUI 后端服务
提供实时交易状态的 REST API
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from trader.state_manager import StateManager

# 初始化日志
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Kronos Trader WebUI",
    description="Kronos智能交易系统实时监控面板",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 状态管理器
state_manager = StateManager()

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")

manager = ConnectionManager()

# 挂载静态文件目录
webui_dir = Path(__file__).parent / 'webui'
if webui_dir.exists():
    app.mount("/static", StaticFiles(directory=str(webui_dir)), name="static")

# 挂载 charts 目录以提供预测图表
charts_dir = project_root / 'charts'
if charts_dir.exists():
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")


@app.get("/")
async def root():
    """根路径 - 返回 WebUI 页面"""
    index_file = webui_dir / 'index.html'
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Kronos Trader WebUI API", "status": "running"}


@app.get("/api/status")
async def get_status():
    """获取系统运行状态"""
    return JSONResponse(content=state_manager.get_system_status())


@app.get("/api/positions")
async def get_positions():
    """获取当前持仓信息"""
    return JSONResponse(content=state_manager.get_positions())


@app.get("/api/predictions")
async def get_predictions():
    """获取最新预测数据"""
    return JSONResponse(content=state_manager.get_predictions())


@app.get("/api/trading-history")
async def get_trading_history(limit: int = 50):
    """获取交易历史"""
    return JSONResponse(content=state_manager.get_trading_history(limit))


@app.get("/api/strategy-logs")
async def get_strategy_logs(limit: int = 100):
    """获取策略执行日志"""
    return JSONResponse(content=state_manager.get_strategy_logs(limit))


@app.get("/api/performance")
async def get_performance():
    """获取性能统计"""
    return JSONResponse(content=state_manager.get_performance_stats())


@app.get("/api/risk-metrics")
async def get_risk_metrics():
    """获取风险指标"""
    return JSONResponse(content=state_manager.get_risk_metrics())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点，用于实时数据推送"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（心跳）
            data = await websocket.receive_text()

            # 发送最新状态
            status = state_manager.get_system_status()
            await websocket.send_json(status)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)


@app.post("/api/update-state")
async def update_state(state_data: dict):
    """
    更新系统状态（由交易策略调用）
    """
    try:
        state_manager.update_state(state_data)

        # 广播更新到所有 WebSocket 连接
        await manager.broadcast({
            "type": "state_update",
            "data": state_data,
            "timestamp": datetime.now().isoformat()
        })

        return {"status": "success", "message": "状态已更新"}
    except Exception as e:
        logger.error(f"更新状态失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """启动 WebUI 服务器"""
    logger.info(f"启动 Kronos Trader WebUI 服务器: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 启动服务器
    run_server()