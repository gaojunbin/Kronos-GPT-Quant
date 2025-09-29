import gc
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
import pytz
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from binance.client import Client

from model import KronosTokenizer, Kronos, KronosPredictor

# --- Configuration ---
Config = {
    "REPO_PATH": Path(__file__).parent.resolve(),
    "MODEL_PATH": "../Kronos_model",
    "SYMBOLS": ['BNBUSDT', 'ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'DOGEUSDT', 'ADAUSDT'],  # 多币种配置
    "INTERVAL": '1h',
    "HIST_POINTS": 360,
    "PRED_HORIZON": 24,
    "N_PREDICTIONS": 30,
    "VOL_WINDOW": 24,
}


def load_model():
    """Loads the Kronos model and tokenizer."""
    print("Loading Kronos model...")
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-2k", cache_dir=Config["MODEL_PATH"])
    model = Kronos.from_pretrained("NeoQuasar/Kronos-mini", cache_dir=Config["MODEL_PATH"])
    tokenizer.eval()
    model.eval()
    predictor = KronosPredictor(model, tokenizer, device="cpu", max_context=512)
    print("Model loaded successfully.")
    return predictor


def make_prediction(df, predictor):
    """Generates probabilistic forecasts using the Kronos model."""
    last_timestamp = df['timestamps'].max()
    start_new_range = last_timestamp + pd.Timedelta(hours=1)
    new_timestamps_index = pd.date_range(
        start=start_new_range,
        periods=Config["PRED_HORIZON"],
        freq='H'
    )
    y_timestamp = pd.Series(new_timestamps_index, name='y_timestamp')
    x_timestamp = df['timestamps']
    x_df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]

    with torch.no_grad():
        print("Making main prediction (T=1.0)...")
        begin_time = time.time()
        close_preds_main, volume_preds_main = predictor.predict(
            df=x_df, x_timestamp=x_timestamp, y_timestamp=y_timestamp,
            pred_len=Config["PRED_HORIZON"], T=1.0, top_p=0.95,
            sample_count=Config["N_PREDICTIONS"], verbose=True
        )
        print(f"Main prediction completed in {time.time() - begin_time:.2f} seconds.")

        # print("Making volatility prediction (T=0.9)...")
        # begin_time = time.time()
        # close_preds_volatility, _ = predictor.predict(
        #     df=x_df, x_timestamp=x_timestamp, y_timestamp=y_timestamp,
        #     pred_len=Config["PRED_HORIZON"], T=0.9, top_p=0.9,
        #     sample_count=Config["N_PREDICTIONS"], verbose=True
        # )
        # print(f"Volatility prediction completed in {time.time() - begin_time:.2f} seconds.")
        close_preds_volatility = close_preds_main

    return close_preds_main, volume_preds_main, close_preds_volatility


def fetch_binance_data(symbol):
    """Fetches K-line data from the Binance public API for a specific symbol."""
    interval = Config["INTERVAL"]
    limit = Config["HIST_POINTS"] + Config["VOL_WINDOW"]

    print(f"Fetching {limit} bars of {symbol} {interval} data from Binance...")
    client = Client()
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore']
    df = pd.DataFrame(klines, columns=cols)

    df = df[['open_time', 'open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']]
    df.rename(columns={'quote_asset_volume': 'amount', 'open_time': 'timestamps'}, inplace=True)

    df['timestamps'] = pd.to_datetime(df['timestamps'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        df[col] = pd.to_numeric(df[col])

    print(f"Data for {symbol} fetched successfully.")
    return df


def calculate_metrics(hist_df, close_preds_df, v_close_preds_df):
    """
    Calculates upside and volatility amplification probabilities for the 24h horizon.
    """
    last_close = hist_df['close'].iloc[-1]

    # 1. Upside Probability (for the 24-hour horizon)
    # This is the probability that the price at the end of the horizon is higher than now.
    final_hour_preds = close_preds_df.iloc[-1]
    upside_prob = (final_hour_preds > last_close).mean()

    # 2. Volatility Amplification Probability (over the 24-hour horizon)
    hist_log_returns = np.log(hist_df['close'] / hist_df['close'].shift(1))
    historical_vol = hist_log_returns.iloc[-Config["VOL_WINDOW"]:].std()

    amplification_count = 0
    for col in v_close_preds_df.columns:
        full_sequence = pd.concat([pd.Series([last_close]), v_close_preds_df[col]]).reset_index(drop=True)
        pred_log_returns = np.log(full_sequence / full_sequence.shift(1))
        predicted_vol = pred_log_returns.std()
        if predicted_vol > historical_vol:
            amplification_count += 1

    vol_amp_prob = amplification_count / len(v_close_preds_df.columns)

    print(f"Upside Probability (24h): {upside_prob:.2%}, Volatility Amplification Probability: {vol_amp_prob:.2%}")
    return upside_prob, vol_amp_prob


def create_plot(hist_df, close_preds_df, volume_preds_df, symbol):
    """Generates and saves a comprehensive forecast chart for a specific symbol."""
    print(f"Generating comprehensive forecast chart for {symbol}...")
    # plt.style.use('seaborn-v0_8-whitegrid')
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(15, 10), sharex=True,
        gridspec_kw={'height_ratios': [3, 1]}
    )

    hist_time = hist_df['timestamps']
    last_hist_time = hist_time.iloc[-1]
    pred_time = pd.to_datetime([last_hist_time + timedelta(hours=i + 1) for i in range(len(close_preds_df))])

    ax1.plot(hist_time, hist_df['close'], color='royalblue', label='Historical Price', linewidth=1.5)
    mean_preds = close_preds_df.mean(axis=1)
    ax1.plot(pred_time, mean_preds, color='darkorange', linestyle='-', label='Mean Forecast')
    ax1.fill_between(pred_time, close_preds_df.min(axis=1), close_preds_df.max(axis=1), color='darkorange', alpha=0.2, label='Forecast Range (Min-Max)')
    ax1.set_title(f'{symbol} Probabilistic Price & Volume Forecast (Next {Config["PRED_HORIZON"]} Hours)', fontsize=16, weight='bold')
    ax1.set_ylabel('Price (USDT)')
    ax1.legend()
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)

    ax2.bar(hist_time, hist_df['volume'], color='skyblue', label='Historical Volume', width=0.03)
    ax2.bar(pred_time, volume_preds_df.mean(axis=1), color='sandybrown', label='Mean Forecasted Volume', width=0.03)
    ax2.set_ylabel('Volume')
    ax2.set_xlabel('Time (SGT)')
    ax2.legend()
    ax2.grid(True, which='both', linestyle='--', linewidth=0.5)

    separator_time = hist_time.iloc[-1] + timedelta(minutes=30)
    for ax in [ax1, ax2]:
        ax.axvline(x=separator_time, color='red', linestyle='--', linewidth=1.5, label='_nolegend_')
        ax.tick_params(axis='x', rotation=30)

    fig.tight_layout()
    charts_dir = Config["REPO_PATH"] / 'charts'
    charts_dir.mkdir(exist_ok=True)
    chart_path = charts_dir / f'prediction_chart_{symbol}.png'
    fig.savefig(chart_path, dpi=120)
    plt.close(fig)
    print(f"Chart saved to: {chart_path}")
    return chart_path


def update_html_predictions_data(predictions_data):
    """直接更新HTML文件中的predictionsData"""
    html_path = Config["REPO_PATH"] / 'index.html'

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 将预测数据转换为JavaScript格式
    js_data = json.dumps(predictions_data, ensure_ascii=False, indent=12)

    # 使用正则表达式替换predictionsData
    pattern = r'(let predictionsData = ){.*?}(\s*;)'
    replacement = f'\\g<1>{js_data}\\g<2>'

    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"HTML中的预测数据已更新")


def update_html(upside_prob, vol_amp_prob):
    """
    Updates the index.html file with the latest metrics and timestamp.
    This version uses a more robust lambda function for replacement to avoid formatting errors.
    """
    print("Updating index.html...")
    html_path = Config["REPO_PATH"] / 'index.html'
    # 使用新加坡时间
    singapore_tz = pytz.timezone('Asia/Singapore')
    now_sgt_str = datetime.now(singapore_tz).strftime('%Y-%m-%d %H:%M:%S')
    upside_prob_str = f'{upside_prob:.1%}'
    vol_amp_prob_str = f'{vol_amp_prob:.1%}'

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Robustly replace content using lambda functions
    content = re.sub(
        r'(<strong id="update-time">).*?(</strong>)',
        lambda m: f'{m.group(1)}{now_sgt_str}{m.group(2)}',
        content
    )
    content = re.sub(
        r'(<p class="metric-value" id="upside-prob">).*?(</p>)',
        lambda m: f'{m.group(1)}{upside_prob_str}{m.group(2)}',
        content
    )
    content = re.sub(
        r'(<p class="metric-value" id="vol-amp-prob">).*?(</p>)',
        lambda m: f'{m.group(1)}{vol_amp_prob_str}{m.group(2)}',
        content
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("HTML file updated successfully.")


def git_commit_and_push(commit_message):
    """Adds, commits, and pushes specified files to the Git repository."""
    print("Performing Git operations...")
    try:
        os.chdir(Config["REPO_PATH"])
        subprocess.run(['git', 'add', 'prediction_chart.png', 'index.html'], check=True, capture_output=True, text=True)
        commit_result = subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True, text=True)
        print(commit_result.stdout)
        push_result = subprocess.run(['git', 'push'], check=True, capture_output=True, text=True)
        print(push_result.stdout)
        print("Git push successful.")
    except subprocess.CalledProcessError as e:
        output = e.stdout if e.stdout else e.stderr
        if "nothing to commit" in output or "Your branch is up to date" in output:
            print("No new changes to commit or push.")
        else:
            print(f"A Git error occurred:\n--- STDOUT ---\n{e.stdout}\n--- STDERR ---\n{e.stderr}")


def main_task(model):
    """执行一次完整的多币种预测更新周期"""
    singapore_start_time = datetime.now(pytz.timezone('Asia/Singapore'))
    print("\n" + "=" * 60 + f"\n开始多币种预测任务 at {singapore_start_time} SGT\n" + "=" * 60)

    # 获取新加坡时间
    singapore_tz = pytz.timezone('Asia/Singapore')
    singapore_time = datetime.now(singapore_tz).strftime('%Y-%m-%d %H:%M:%S')

    predictions_data = {
        "last_updated": singapore_time,
        "symbols": {}
    }

    # 处理每个币种
    for symbol in Config["SYMBOLS"]:
        print(f"\n--- 处理币种: {symbol} ---")
        try:
            # 获取数据
            df_full = fetch_binance_data(symbol)
            df_for_model = df_full.iloc[:-1]

            # 预测
            close_preds, volume_preds, v_close_preds = make_prediction(df_for_model, model)

            # 准备数据
            hist_df_for_plot = df_for_model.tail(Config["HIST_POINTS"])
            hist_df_for_metrics = df_for_model.tail(Config["VOL_WINDOW"])

            # 计算指标
            upside_prob, vol_amp_prob = calculate_metrics(hist_df_for_metrics, close_preds, v_close_preds)

            # 生成图表
            chart_path = create_plot(hist_df_for_plot, close_preds, volume_preds, symbol)

            # 保存预测数据
            predictions_data["symbols"][symbol] = {
                "upside_prob": f"{upside_prob:.1%}",
                "vol_amp_prob": f"{vol_amp_prob:.1%}",
                "chart_file": f"charts/prediction_chart_{symbol}.png"
            }

            print(f"{symbol} 预测完成: 上涨概率 {upside_prob:.1%}, 波动性放大概率 {vol_amp_prob:.1%}")

            # 清理内存
            del df_full, df_for_model, close_preds, volume_preds, v_close_preds
            del hist_df_for_plot, hist_df_for_metrics
            gc.collect()

        except Exception as e:
            print(f"处理 {symbol} 时发生错误: {e}")
            predictions_data["symbols"][symbol] = {
                "upside_prob": "N/A",
                "vol_amp_prob": "N/A",
                "chart_file": None,
                "error": str(e)
            }

    # 直接更新HTML中的预测数据
    update_html_predictions_data(predictions_data)

    # 为向后兼容，仍然更新HTML中的时间戳和第一个币种的数据
    first_symbol = Config["SYMBOLS"][0]
    if first_symbol in predictions_data["symbols"] and "error" not in predictions_data["symbols"][first_symbol]:
        # 从百分比字符串转换回数字
        upside_str = predictions_data["symbols"][first_symbol]["upside_prob"]
        vol_amp_str = predictions_data["symbols"][first_symbol]["vol_amp_prob"]
        upside_prob = float(upside_str.rstrip('%')) / 100
        vol_amp_prob = float(vol_amp_str.rstrip('%')) / 100
        update_html(upside_prob, vol_amp_prob)

    singapore_time_end = datetime.now(singapore_tz)
    print(f"\n多币种预测完成 {singapore_time_end:%Y-%m-%d %H:%M} SGT")
    print("-" * 60 + "\n--- 任务成功完成 ---\n" + "-" * 60 + "\n")


def run_scheduler(model):
    """A continuous scheduler that runs the main task hourly."""
    while True:
        now = datetime.now(timezone.utc)
        next_run_time = (now + timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
        sleep_seconds = (next_run_time - now).total_seconds()

        if sleep_seconds > 0:
            now_sgt = now.astimezone(pytz.timezone('Asia/Singapore'))
            next_run_sgt = next_run_time.astimezone(pytz.timezone('Asia/Singapore'))
            print(f"Current time: {now_sgt:%Y-%m-%d %H:%M:%S SGT}.")
            print(f"Next run at: {next_run_sgt:%Y-%m-%d %H:%M:%S SGT}. Waiting for {sleep_seconds:.0f} seconds...")
            time.sleep(sleep_seconds)

        try:
            main_task(model)
        except Exception as e:
            print(f"\n!!!!!! A critical error occurred in the main task !!!!!!!")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("Retrying in 5 minutes...")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            time.sleep(300)


if __name__ == '__main__':
    model_path = Path(Config["MODEL_PATH"])
    model_path.mkdir(parents=True, exist_ok=True)

    loaded_model = load_model()
    main_task(loaded_model)  # Run once on startup
    run_scheduler(loaded_model)  # Start the schedule