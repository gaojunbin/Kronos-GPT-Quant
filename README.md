# Kronos 智能交易系统

基于Kronos价格预测模型和ChatGPT智能分析的加密货币自动交易系统。

## 🌟 功能特性

### 价格预测仪表板
- **实时价格预测**: 对BTC、ETH、BNB、SOL、DOGE、ADA提供24小时概率预测
- **交互式仪表板**: 基于Web的实时数据可视化界面
- **多币种支持**: 可切换查看不同加密货币对
- **概率指标**:
  - 上涨概率（价格上涨的可能性）
  - 波动性放大（预测波动性vs历史波动性）

### 智能交易系统 🤖
- **AI价格预测**: 使用Kronos深度学习模型预测6个主流币种的价格走势
- **智能决策**: 集成ChatGPT API，将预测结果转换为具体的交易信号
- **风险控制**: 内置多层风险管理机制，包括仓位控制、止损等
- **自动执行**: 每小时自动运行策略，无需人工干预
- **完整日志**: 详细记录所有交易决策和执行过程

## 🚀 快速开始

### 预测仪表板

#### 使用Docker（推荐）

```bash
docker-compose up -d
```

#### 手动设置

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 运行预测更新器:
```bash
python update_predictions.py
```

3. 启动仪表板:
```bash
python -m http.server 8000
```

访问 `http://localhost:8000` 查看仪表板。

### 智能交易系统

#### 1. 安装交易系统依赖

```bash
pip install -r trader_requirements.txt
```

#### 2. 配置环境变量

复制环境变量模板并填入你的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下必需项：

```bash
# 币安API (需要现货交易权限)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# 可选：启用模拟模式进行测试
SIMULATION_MODE=true
```

#### 3. 验证配置

运行配置检查：

```bash
python run_trader.py --config
```

#### 4. 开始交易

**测试模式（推荐首次使用）**
```bash
python run_trader.py --test
```

**持续运行（生产模式）**
```bash
python run_trader.py
```

## 📊 支持的交易对

- BNB/USDT (币安币)
- ETH/USDT (以太坊)
- BTC/USDT (比特币)
- SOL/USDT (Solana)
- DOGE/USDT (狗狗币)
- ADA/USDT (Cardano)

## 🔧 系统架构

```
trader/
├── __init__.py              # 模块初始化
├── binance_client.py        # 币安API客户端
├── chatgpt_client.py        # ChatGPT API客户端
├── prediction_analyzer.py   # 预测结果分析器
├── main_strategy.py         # 主策略逻辑
└── config.py               # 配置管理

run_trader.py               # 启动脚本
.env.example               # 环境变量模板
trader_requirements.txt    # 交易系统依赖
```

## 📈 交易策略流程

1. **价格预测**: 使用Kronos模型预测各币种24小时价格走势
2. **数据分析**: 计算上涨概率、波动性等关键指标
3. **自然语言转换**: 将预测结果转换为结构化的分析报告
4. **智能决策**: ChatGPT分析报告和当前持仓，生成交易建议
5. **风险评估**: 检查交易建议是否符合风险管理要求
6. **执行交易**: 自动执行买入/卖出/持有操作
7. **记录日志**: 保存完整的决策和执行记录

## ⚡ 风险管理

- **最小交易金额**: 默认50 USDT
- **最大单次交易**: 默认500 USDT
- **最大总仓位**: 80%的可用资金
- **单币种限制**: 不超过总资产的30%
- **止损机制**: 5%止损保护
- **智能分析**: ChatGPT评估市场风险和机会

## 📋 日志和监控

系统会在以下位置生成日志：

- `logs/kronos_trader.log` - 系统运行日志
- `data/strategy_logs/` - 策略执行详细记录

每次策略执行都会记录：
- 预测结果和分析
- ChatGPT交易建议
- 实际执行的交易操作
- 风险控制决策

## ⚠️  重要提醒

1. **测试先行**: 首次使用请启用`SIMULATION_MODE=true`进行测试
2. **资金安全**: 请只投入你能承受损失的资金
3. **API安全**: 币安API密钥仅需现货交易权限，不要开启其他权限
4. **网络稳定**: 确保服务器网络稳定，避免因网络问题影响交易
5. **定期检查**: 建议定期检查系统运行状态和交易结果

## 🔍 故障排除

### 常见问题

1. **API连接失败**: 检查网络连接和API密钥是否正确
2. **余额不足**: 确保有足够的USDT用于交易
3. **预测失败**: 检查Kronos模型文件是否正确下载
4. **ChatGPT超时**: OpenAI API偶尔会超时，系统会自动重试

### 查看日志

```bash
tail -f logs/kronos_trader.log
```

## 📊 数据来源

- **交易所**: 币安
- **更新间隔**: 每小时
- **预测周期**: 24小时
- **历史数据**: 360个数据点（15天）

## 📝 开发说明

本项目包含两个主要组件：

1. **Kronos预测仪表板**: 基于Kronos深度学习模型的价格预测可视化系统
2. **智能交易系统**: 基于预测结果和ChatGPT分析的自动交易系统

核心交易逻辑参考了成熟的量化交易框架，但专门针对AI预测信号进行了优化。

### 核心特性
- 模块化设计，易于扩展
- 完整的错误处理和重试机制
- 详细的日志记录
- 灵活的配置管理

## 📄 许可证

MIT License