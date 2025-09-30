// Kronos Trader WebUI - 前端应用逻辑

class KronosUI {
    constructor() {
        this.apiBase = '';  // 使用相对路径
        this.wsUrl = `ws://${window.location.host}/ws`;
        this.ws = null;
        this.reconnectInterval = 5000;
        this.updateInterval = 10000; // 10秒更新一次
        this.updateTimer = null;

        this.init();
    }

    init() {
        this.connectWebSocket();
        this.startPolling();
        this.loadInitialData();
    }

    // WebSocket 连接
    connectWebSocket() {
        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket 连接成功');
                this.updateSystemStatus('connected', '系统运行中');

                // 发送心跳
                setInterval(() => {
                    if (this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send('ping');
                    }
                }, 30000);
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                this.updateSystemStatus('error', '连接错误');
            };

            this.ws.onclose = () => {
                console.log('WebSocket 连接断开，尝试重连...');
                this.updateSystemStatus('disconnected', '连接断开');
                setTimeout(() => this.connectWebSocket(), this.reconnectInterval);
            };

        } catch (error) {
            console.error('WebSocket 连接失败:', error);
            this.updateSystemStatus('error', '连接失败');
        }
    }

    // 处理 WebSocket 消息
    handleWebSocketMessage(data) {
        if (data.type === 'state_update') {
            this.updateUI(data.data);
        }
    }

    // 轮询更新
    startPolling() {
        this.updateTimer = setInterval(() => {
            this.loadAllData();
        }, this.updateInterval);
    }

    // 加载初始数据
    async loadInitialData() {
        await this.loadAllData();
    }

    // 加载所有数据
    async loadAllData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadPositions(),
                this.loadPredictions(),
                this.loadTradingHistory(),
                this.loadStrategyLogs(),
                this.loadPerformance(),
                this.loadRiskMetrics()
            ]);
        } catch (error) {
            console.error('加载数据失败:', error);
        }
    }

    // API 请求方法
    async fetchAPI(endpoint) {
        try {
            const response = await fetch(`${this.apiBase}${endpoint}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API 请求失败 ${endpoint}:`, error);
            return null;
        }
    }

    // 加载系统状态
    async loadSystemStatus() {
        const data = await this.fetchAPI('/api/status');
        if (data) {
            this.updateSystemStatusInfo(data);
        }
    }

    // 加载持仓
    async loadPositions() {
        const data = await this.fetchAPI('/api/positions');
        if (data) {
            this.updatePositionsTable(data);
        }
    }

    // 加载预测
    async loadPredictions() {
        const data = await this.fetchAPI('/api/predictions');
        if (data) {
            this.updatePredictionsTable(data);
        }
    }

    // 加载交易历史
    async loadTradingHistory() {
        const data = await this.fetchAPI('/api/trading-history?limit=20');
        if (data) {
            this.updateTradingHistoryTable(data);
        }
    }

    // 加载策略日志
    async loadStrategyLogs() {
        const data = await this.fetchAPI('/api/strategy-logs?limit=50');
        if (data) {
            this.updateLogsContainer(data);
        }
    }

    // 加载性能统计
    async loadPerformance() {
        const data = await this.fetchAPI('/api/performance');
        if (data) {
            this.updatePerformanceStats(data);
        }
    }

    // 加载风险指标
    async loadRiskMetrics() {
        const data = await this.fetchAPI('/api/risk-metrics');
        if (data) {
            this.updateRiskMetrics(data);
        }
    }

    // 更新系统状态
    updateSystemStatus(status, text) {
        const badge = document.getElementById('systemStatus');
        const statusText = document.getElementById('statusText');

        badge.className = 'status-badge ' + status;
        statusText.textContent = text;
    }

    // 更新系统状态信息
    updateSystemStatusInfo(data) {
        const lastRun = document.getElementById('lastRun');
        const nextRun = document.getElementById('nextRun');
        const totalRuns = document.getElementById('totalRuns');

        if (data.last_strategy_run) {
            lastRun.textContent = this.formatDateTime(data.last_strategy_run);
        }

        if (data.next_strategy_run) {
            nextRun.textContent = this.formatDateTime(data.next_strategy_run);
        }

        if (data.total_runs !== undefined) {
            totalRuns.textContent = data.total_runs;
        }

        if (data.is_running) {
            this.updateSystemStatus('connected', '系统运行中');
        }
    }

    // 更新性能统计
    updatePerformanceStats(data) {
        const successTrades = document.getElementById('successTrades');
        const totalVolume = document.getElementById('totalVolume');

        if (data.successful_trades !== undefined) {
            successTrades.textContent = data.successful_trades;
        }

        if (data.total_volume !== undefined) {
            totalVolume.textContent = this.formatCurrency(data.total_volume);
        }
    }

    // 更新风险指标
    updateRiskMetrics(data) {
        const exposureBar = document.getElementById('exposureBar');
        const exposureValue = document.getElementById('exposureValue');
        const usdtReserve = document.getElementById('usdtReserve');
        const positionCount = document.getElementById('positionCount');
        const maxPosition = document.getElementById('maxPosition');
        const totalValue = document.getElementById('totalValue');

        if (data.total_exposure !== undefined) {
            const exposurePct = (data.total_exposure * 100).toFixed(1);
            exposureBar.style.width = exposurePct + '%';
            exposureValue.textContent = exposurePct + '%';

            // 根据敞口设置颜色
            if (data.total_exposure > 0.7) {
                exposureBar.classList.add('warning');
            } else {
                exposureBar.classList.remove('warning');
            }
        }

        if (data.usdt_reserve !== undefined) {
            usdtReserve.textContent = this.formatCurrency(data.usdt_reserve);
        }

        if (data.position_count !== undefined) {
            positionCount.textContent = data.position_count;
        }

        if (data.max_single_position !== undefined) {
            maxPosition.textContent = this.formatCurrency(data.max_single_position);
        }

        if (data.total_value !== undefined) {
            totalValue.textContent = this.formatCurrency(data.total_value);
        }
    }

    // 更新持仓表格
    updatePositionsTable(data) {
        const tbody = document.getElementById('positionsTable');

        if (!data || Object.keys(data).length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">暂无持仓数据</td></tr>';
            return;
        }

        let html = '';
        for (const [asset, info] of Object.entries(data)) {
            html += `
                <tr>
                    <td><strong>${asset}</strong></td>
                    <td>${this.formatNumber(info.amount, 6)}</td>
                    <td>$${this.formatNumber(info.current_price, 4)}</td>
                    <td>$${this.formatNumber(info.usd_value, 2)}</td>
                    <td>${this.formatNumber(info.free, 6)} / ${this.formatNumber(info.locked, 6)}</td>
                </tr>
            `;
        }
        tbody.innerHTML = html;
    }

    // 更新预测表格
    updatePredictionsTable(data) {
        const tbody = document.getElementById('predictionsTable');

        if (!data || !data.symbols || Object.keys(data.symbols).length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">暂无预测数据</td></tr>';
            return;
        }

        let html = '';
        for (const [symbol, pred] of Object.entries(data.symbols)) {
            if (pred.error) continue;

            const upsideProb = this.parsePercentage(pred.upside_prob);
            const volProb = this.parsePercentage(pred.vol_amp_prob);
            const probClass = this.getProbabilityClass(upsideProb);

            let predRange = 'N/A';
            if (pred.prediction_stats) {
                predRange = `${this.formatNumber(pred.prediction_stats.min_prediction, 6)} - ${this.formatNumber(pred.prediction_stats.max_prediction, 6)}`;
            }

            // 安全获取当前价格，如果不存在则显示 N/A
            const currentPrice = pred.current_price ? `$${this.formatNumber(pred.current_price, 6)}` : 'N/A';

            html += `
                <tr>
                    <td><strong>${symbol}</strong></td>
                    <td>${currentPrice}</td>
                    <td><span class="${probClass}">${pred.upside_prob || 'N/A'}</span></td>
                    <td>${pred.vol_amp_prob || 'N/A'}</td>
                    <td>${predRange}</td>
                </tr>
            `;
        }
        tbody.innerHTML = html || '<tr><td colspan="5" class="no-data">暂无预测数据</td></tr>';
    }

    // 更新交易历史表格
    updateTradingHistoryTable(data) {
        const tbody = document.getElementById('tradesTable');

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">暂无交易记录</td></tr>';
            return;
        }

        let html = '';
        for (const trade of data.slice().reverse()) {
            const actionClass = trade.action.toLowerCase();
            const statusClass = trade.status === 'success' ? 'success' : 'failed';

            html += `
                <tr>
                    <td>${this.formatDateTime(trade.timestamp)}</td>
                    <td><strong>${trade.symbol}</strong></td>
                    <td><span class="action-badge ${actionClass}">${trade.action}</span></td>
                    <td>${this.formatNumber(trade.quantity, 6)}</td>
                    <td>$${this.formatNumber(trade.price, 6)}</td>
                    <td>$${this.formatNumber(trade.volume_usdt, 2)}</td>
                    <td><span class="status-badge-small ${statusClass}">${trade.status}</span></td>
                </tr>
            `;
        }
        tbody.innerHTML = html;
    }

    // 更新日志容器
    updateLogsContainer(data) {
        const container = document.getElementById('logsContainer');

        if (!data || data.length === 0) {
            container.innerHTML = '<div class="no-data">暂无日志</div>';
            return;
        }

        let html = '';
        for (const log of data.slice().reverse()) {
            const level = log.level || 'info';
            html += `
                <div class="log-entry ${level}">
                    <div class="log-timestamp">${this.formatDateTime(log.timestamp)}</div>
                    <div class="log-message">${this.escapeHtml(log.message)}</div>
                </div>
            `;
        }
        container.innerHTML = html;

        // 滚动到底部
        container.scrollTop = container.scrollHeight;
    }

    // 工具方法
    formatDateTime(dateStr) {
        if (!dateStr) return 'N/A';
        try {
            const date = new Date(dateStr);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (e) {
            return dateStr;
        }
    }

    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined || num === '' || isNaN(num)) return '0';
        const parsed = parseFloat(num);
        if (isNaN(parsed)) return '0';
        return parsed.toFixed(decimals);
    }

    formatCurrency(num) {
        if (num === null || num === undefined || num === '' || isNaN(num)) return '$0.00';
        const parsed = parseFloat(num);
        if (isNaN(parsed)) return '$0.00';
        return '$' + parsed.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    parsePercentage(str) {
        if (!str || str === 'N/A') return 0;
        return parseFloat(str.replace('%', ''));
    }

    getProbabilityClass(prob) {
        if (prob >= 60) return 'prob-high';
        if (prob >= 40) return 'prob-medium';
        return 'prob-low';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.kronosUI = new KronosUI();
});