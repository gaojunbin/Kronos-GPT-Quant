# Kronos Intelligent Trading System

An automated cryptocurrency trading system powered by Kronos price prediction model and ChatGPT intelligent analysis.

## 🌟 Features

### Price Prediction Dashboard
- **Real-time Price Forecasting**: 24-hour probabilistic predictions for BTC, ETH, BNB, SOL, DOGE, and ADA
- **Interactive Dashboard**: Web-based real-time data visualization interface
- **Multi-Currency Support**: Switch between different cryptocurrency pairs
- **Probability Metrics**:
  - Upside Probability (likelihood of price increase)
  - Volatility Amplification (predicted vs historical volatility)

### Intelligent Trading System 🤖
- **AI Price Prediction**: Uses Kronos deep learning model to forecast price movements for 6 major cryptocurrencies
- **Smart Decision Making**: Integrates ChatGPT API to convert predictions into actionable trading signals
- **Risk Control**: Built-in multi-layer risk management including position sizing and stop-loss
- **Automated Execution**: Runs strategy automatically every hour without manual intervention
- **Comprehensive Logging**: Detailed records of all trading decisions and executions

## 🚀 Quick Start

### Prediction Dashboard

#### Using Docker (Recommended)

```bash
docker-compose up -d
```

#### Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run prediction updater:
```bash
python update_predictions.py
```

3. Start dashboard:
```bash
python -m http.server 8000
```

Access the dashboard at `http://localhost:8000`.

### Intelligent Trading System

#### 1. Install Trading System Dependencies

```bash
pip install -r trader_requirements.txt
```

#### 2. Configure Environment Variables

Copy the environment template and fill in your API keys:

```bash
cp .env.example .env
```

Edit the `.env` file and set the required fields:

```bash
# Binance API (spot trading permission required)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Optional: Enable simulation mode for testing
SIMULATION_MODE=true
```

#### 3. Verify Configuration

Run configuration check:

```bash
python run_trader.py --config
```

#### 4. Start Trading

**Test Mode (Recommended for First Use)**
```bash
python run_trader.py --test
```

**Continuous Run (Production Mode)**
```bash
python run_trader.py
```

## 📊 Supported Trading Pairs

- BNB/USDT (Binance Coin)
- ETH/USDT (Ethereum)
- BTC/USDT (Bitcoin)
- SOL/USDT (Solana)
- DOGE/USDT (Dogecoin)
- ADA/USDT (Cardano)

## 🔧 System Architecture

```
trader/
├── __init__.py              # Module initialization
├── binance_client.py        # Binance API client
├── chatgpt_client.py        # ChatGPT API client
├── prediction_analyzer.py   # Prediction result analyzer
├── main_strategy.py         # Main strategy logic
├── state_manager.py         # State management
├── webui_server.py          # WebUI server
└── config.py                # Configuration management

run_trader.py                # Launch script
.env.example                 # Environment variables template
trader_requirements.txt      # Trading system dependencies
```

## 📈 Trading Strategy Workflow

1. **Price Prediction**: Use Kronos model to forecast 24-hour price movements for each currency
2. **Data Analysis**: Calculate key metrics including upside probability and volatility
3. **Natural Language Conversion**: Convert prediction results into structured analysis reports
4. **Intelligent Decision**: ChatGPT analyzes reports and current positions to generate trading recommendations
5. **Risk Assessment**: Verify that trading recommendations comply with risk management requirements
6. **Execute Trades**: Automatically execute buy/sell/hold operations
7. **Log Recording**: Save complete decision and execution records

## ⚡ Risk Management

- **Minimum Trade Amount**: Default 50 USDT
- **Maximum Single Trade**: Default 500 USDT
- **Maximum Total Position**: 80% of available funds
- **Single Currency Limit**: No more than 30% of total assets
- **Stop-Loss Mechanism**: 5% stop-loss protection
- **Intelligent Analysis**: ChatGPT evaluates market risks and opportunities

## 📋 Logging and Monitoring

The system generates logs in the following locations:

- `logs/kronos_trader.log` - System operation logs
- `data/strategy_logs/` - Detailed strategy execution records

Each strategy execution records:
- Prediction results and analysis
- ChatGPT trading recommendations
- Actual executed trades
- Risk control decisions

## ⚠️  Important Notes

1. **Test First**: Enable `SIMULATION_MODE=true` for testing before live trading
2. **Capital Safety**: Only invest funds you can afford to lose
3. **API Security**: Binance API key should only have spot trading permission, do not enable other permissions
4. **Network Stability**: Ensure server network stability to avoid trading issues due to network problems
5. **Regular Checks**: Regularly monitor system status and trading results

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Failed**: Check network connection and verify API keys are correct
2. **Insufficient Balance**: Ensure you have enough USDT for trading
3. **Prediction Failed**: Verify Kronos model files are correctly downloaded
4. **ChatGPT Timeout**: OpenAI API may occasionally timeout, system will automatically retry

### View Logs

```bash
tail -f logs/kronos_trader.log
```

## 📊 Data Sources

- **Exchange**: Binance
- **Update Interval**: Hourly
- **Prediction Horizon**: 24 hours
- **Historical Data**: 360 data points (15 days)

## 📝 Development Notes

This project consists of two main components:

1. **Kronos Prediction Dashboard**: Price prediction visualization system based on Kronos deep learning model
2. **Intelligent Trading System**: Automated trading system based on prediction results and ChatGPT analysis

The core trading logic is inspired by mature quantitative trading frameworks but specifically optimized for AI prediction signals.

### Core Features
- Modular design for easy extension
- Complete error handling and retry mechanisms
- Detailed logging
- Flexible configuration management

## 📄 License

MIT License