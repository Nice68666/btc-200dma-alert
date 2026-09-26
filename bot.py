import os
import requests
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

BINANCE_URL = "https://api.binance.com/api/v3/klines"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def get_btc_data():
    params = {
        "symbol": "BTCUSDT",
        "interval": "1d",
        "limit": 201
    }

    response = requests.get(BINANCE_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    # 最后一根日线可能还没有收盘，因此只使用完整日线
    closed_candles = data[:-1]

    closes = [float(candle[4]) for candle in closed_candles]

    if len(closes) < 200:
        raise Exception("BTC 日线数据不足 200 天")

    dma_200 = sum(closes[-200:]) / 200

    current_price = float(
        requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=15
        ).json()["price"]
    )

    return current_price, dma_200


def send_message(message):
    response = requests.post(
        TELEGRAM_URL,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=15
    )

    response.raise_for_status()


def main():
    current_price, dma_200 = get_btc_data()

    difference = (current_price - dma_200) / dma_200 * 100

    if current_price < dma_200:
        status = "🔴 低于 200DMA"
    else:
        status = "🟢 高于 200DMA"

    message = f"""₿ BTC 200DMA 状态

当前价格：${current_price:,.2f}
200日均线：${dma_200:,.2f}

距离200DMA：{difference:+.2f}%

状态：{status}

数据来源：Binance
检查时间：{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
"""

    send_message(message)


if __name__ == "__main__":
    main()
