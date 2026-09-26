import os
import requests
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
PRICE_URL = "https://data-api.binance.vision/api/v3/ticker/price"
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

    closed_candles = data[:-1]
    closes = [float(candle[4]) for candle in closed_candles]

    if len(closes) < 200:
        raise Exception("BTC 日线数据不足 200 天")

    dma_200 = sum(closes[-200:]) / 200

    current_price = float(
        requests.get(PRICE_URL, params={"symbol": "BTCUSDT"}, timeout=15).json()["price"]
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
    if current_price < dma_200:
        status = "🔴 低于 200DMA"
    else:
        status = "🟢 高于 200DMA"

    return f"""₿ <b>BTC 200DMA 状态</b>
当前价格：${current_price:,.2f}
200日均线：${dma_200:,.2f}
距离200DMA：{difference:+.2f}%
状态：{status}
数据来源：Binance
检查时间：{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}"""


def main():
    print("CHAT_ID =", repr(CHAT_ID))
    if not CHAT_ID or not str(CHAT_ID).strip():
        raise Exception("CHAT_ID 为空，请检查 GitHub Secrets")

    current_price, dma_200 = get_btc_data()
    message = format_status(current_price, dma_200)
    send_message(message)
    print("已发送测试消息")
    print(f"价格: {current_price:.2f}, 200DMA: {dma_200:.2f}")


if __name__ == "__main__":
    main()
