# Kronos Trader WebUI 使用说明

## 概述

Kronos Trader WebUI 是一个实时交易监控面板，用于可视化展示交易系统的运行状态、持仓、预测数据和交易历史。

## 功能特性

### 1. 实时监控面板
- **系统概览**: 显示总资产价值、运行次数、成功交易数、总交易量
- **风险指标**: 展示总敞口、USDT储备、持仓数量、最大单仓位
- **运行状态**: 实时显示系统运行状态和下次执行时间

### 2. 持仓管理
- 显示所有币种的当前持仓
- 实时更新价格和持仓价值
- 区分可用余额和锁定余额

### 3. 价格预测
- 展示各币种的上涨概率
- 显示高波动概率
- 预测价格区间

### 4. 交易历史
- 记录所有买卖操作
- 显示交易状态（成功/失败）
- 包含交易理由和置信度

### 5. 策略日志
- 实时显示策略执行日志
- 不同级别日志颜色区分（info/success/error/warning）
- 自动滚动到最新日志

## 快速开始

### 方式1: 使用 Docker Compose（推荐）

```bash
# 启动完整的 Trader 系统（包括 WebUI）
docker-compose -f docker-compose.trader.yml up -d

# 查看日志
docker-compose -f docker-compose.trader.yml logs -f kronos-trader-webui

# 停止服务
docker-compose -f docker-compose.trader.yml down
```

访问地址: http://localhost:8000

### 方式2: 独立运行 WebUI

```bash
# 安装依赖
pip install -r trader_requirements.txt

# 启动 WebUI 服务
python trader/run_webui.py

# 或使用模块方式
python -m trader.webui_server
```

访问地址: http://localhost:8000

## 架构说明

### 后端 (FastAPI)
- **webui_server.py**: FastAPI 服务器，提供 REST API 和 WebSocket
- **state_manager.py**: 线程安全的状态管理器，存储所有运行时数据
- **main_strategy.py**: 交易策略主逻辑，集成了状态更新功能

### 前端 (HTML/CSS/JS)
- **index.html**: WebUI 主页面结构
- **style.css**: 响应式深色主题样式
- **app.js**: 前端应用逻辑，处理数据获取和展示

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | WebUI 主页面 |
| `/api/status` | GET | 获取系统运行状态 |
| `/api/positions` | GET | 获取当前持仓信息 |
| `/api/predictions` | GET | 获取最新预测数据 |
| `/api/trading-history` | GET | 获取交易历史 |
| `/api/strategy-logs` | GET | 获取策略执行日志 |
| `/api/performance` | GET | 获取性能统计 |
| `/api/risk-metrics` | GET | 获取风险指标 |
| `/ws` | WebSocket | WebSocket 连接，实时数据推送 |

## 配置说明

WebUI 服务默认配置:
- 端口: 8000
- 主机: 0.0.0.0 (接受所有来源)
- 更新间隔: 10秒
- WebSocket 心跳: 30秒

可以在 `trader/webui_server.py` 中修改配置:

```python
def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="info")
```

## Docker Compose 配置

新增的 WebUI 服务配置:

```yaml
kronos-trader-webui:
  build:
    context: .
    dockerfile: Dockerfile.trader
  container_name: kronos-trader-webui
  restart: unless-stopped
  command: python -m trader.webui_server
  ports:
    - "8000:8000"
  volumes:
    - .:/app
  environment:
    - TZ=Asia/Singapore
  env_file:
    - .env
  networks:
    - kronos-network
  depends_on:
    - kronos-trader
```

## 状态数据流

```
KronosMainStrategy (交易策略)
        ↓
StateManager (状态管理器)
        ↓
WebUI Server (API服务)
        ↓
Browser (Web界面)
```

交易策略在执行过程中会自动更新状态:
- 系统运行状态
- 持仓变化
- 预测结果
- 交易执行
- 策略日志

WebUI 通过定期轮询和 WebSocket 实时获取最新数据。

## 开发说明

### 添加新的数据类型

1. 在 `state_manager.py` 中添加存储字段
2. 在 `main_strategy.py` 中调用更新方法
3. 在 `webui_server.py` 中添加 API 端点
4. 在前端 `app.js` 中添加数据获取和展示逻辑

### 自定义样式

修改 `trader/webui/style.css` 中的 CSS 变量:

```css
:root {
    --primary-color: #3b82f6;
    --success-color: #10b981;
    --danger-color: #ef4444;
    --warning-color: #f59e0b;
    /* ... */
}
```

## 故障排查

### WebUI 无法访问

1. 检查服务是否正在运行:
```bash
docker ps | grep webui
# 或
ps aux | grep webui_server
```

2. 检查端口是否被占用:
```bash
lsof -i :8000
```

3. 查看服务日志:
```bash
docker logs kronos-trader-webui
```

### 数据不更新

1. 确认交易策略服务正在运行
2. 检查 StateManager 是否正常工作
3. 打开浏览器开发者工具查看网络请求
4. 检查 WebSocket 连接状态

### WebSocket 连接失败

1. 确认浏览器支持 WebSocket
2. 检查防火墙设置
3. 查看浏览器控制台错误信息
4. 尝试使用 HTTP 轮询（已作为备用方案）

## 安全建议

1. **生产环境部署**:
   - 使用 Nginx/Caddy 作为反向代理
   - 启用 HTTPS
   - 设置访问认证

2. **网络安全**:
   - 限制 WebUI 端口仅内网访问
   - 使用 VPN 或 SSH 隧道远程访问
   - 定期更新依赖包

3. **API 密钥保护**:
   - 不要在 WebUI 中暴露 API 密钥
   - 使用环境变量管理敏感信息

## 性能优化

1. **减少轮询频率**: 如果数据量大，可以增加更新间隔
2. **限制历史记录**: StateManager 中设置合理的 `max_history`
3. **启用缓存**: 为静态资源配置浏览器缓存
4. **数据分页**: 对大量历史数据实现分页加载

## 未来改进

- [ ] 添加用户认证和权限管理
- [ ] 支持多种图表展示（K线图、收益曲线）
- [ ] 添加邮件/Telegram 通知集成
- [ ] 支持策略参数实时调整
- [ ] 添加回测功能可视化
- [ ] 支持多语言界面

## 相关文件

```
trader/
├── webui_server.py       # FastAPI 服务器
├── state_manager.py      # 状态管理器
├── main_strategy.py      # 交易策略（已集成状态更新）
├── run_webui.py          # WebUI 独立启动脚本
└── webui/                # 前端文件
    ├── index.html        # 主页面
    ├── style.css         # 样式文件
    └── app.js            # JavaScript 应用逻辑
```

## 技术栈

- **后端**: FastAPI, Uvicorn, WebSocket
- **前端**: 原生 HTML/CSS/JavaScript
- **数据存储**: 内存（线程安全的 deque）
- **容器化**: Docker, Docker Compose

## 许可

与 Kronos 项目保持一致。