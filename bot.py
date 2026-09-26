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


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"below": None}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


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
    # 先检查关键环境变量
    if not CHAT_ID or not CHAT_ID.strip():
        raise Exception("CHAT_ID 为空！请到 GitHub Secrets 正确设置 CHAT_ID = 664869150")

    current_price, dma_200 = get_btc_data()
    is_below = current_price < dma_200
    state = load_state()
    prev_below = state.get("below")

    message = None

    if prev_below is None:
        # 首次运行：只记录状态，不发消息
        state["below"] = is_below
        save_state(state)
        print(f"首次运行，已记录状态：below={is_below}")
        print(f"当前价格: {current_price:.2f}, 200DMA: {dma_200:.2f}")
        return

    if is_below and not prev_below:
        message = (
            "🚨 <b>BTC 跌破 200DMA！</b>\n\n"
            + format_status(current_price, dma_200)
        )
    elif not is_below and prev_below:
        message = (
            "✅ <b>BTC 重新站上 200DMA</b>\n\n"
            + format_status(current_price, dma_200)
        )

    if message:
        send_message(message)
        print("已发送提醒消息")
    else:
        print(f"状态无变化（below={is_below}），不发送消息")

    state["below"] = is_below
    save_state(state)


if __name__ == "__main__":
    main()def main():
    if not CHAT_ID or not CHAT_ID.strip():
        raise Exception("CHAT_ID 为空！请到 GitHub Secrets 正确设置 CHAT_ID = 664869150")

    current_price, dma_200 = get_btc_data()
    is_below = current_price < dma_200

    # 临时：每次都发送状态，用来测试 Telegram 是否通
    message = format_status(current_price, dma_200)
    send_message(message)
    print("已发送测试消息")
    print(f"当前价格: {current_price:.2f}, 200DMA: {dma_200:.2f}, below={is_below}")
