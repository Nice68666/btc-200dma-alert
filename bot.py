import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# 使用 Binance 数据专用接口，避免 GitHub Actions 所在地区 451 限制
BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
PRICE_URL = "https://data-api.binance.vision/api/v3/ticker/price"

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
STATE_FILE = Path("state.json")


def get_btc_data():
    params = {
        "symbol": "BTCUSDT",
        "interval": "1d",
        "limit": 201
    }
    response = requests.get(BINANCE_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    # 最后一根日线可能还没收盘，只使用已完整收盘的日线
    closed_candles = data[:-1]
    closes = [float(candle[4]) for candle in closed_candles]

    if len(closes) < 200:
        raise Exception("BTC 日线数据不足 200 天")

    dma_200 = sum(closes[-200:]) / 200

    current_price = float(
        requests.get(
            PRICE_URL,
            params={"symbol": "BTCUSDT"},
            timeout=15
        ).json()["price"]
    )
    return current_price, dma_200


def send_message(message: str):
    response = requests.post(
        TELEGRAM_URL,
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=15
    )
    response.raise_for_status()


def format_status(current_price: float, dma_200: float) -> str:
    difference = (current_price - dma_200) / dma_200 * 100
