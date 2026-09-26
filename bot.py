import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

BOT_TOKEN = os.environ["BOT_TOKEN"]   # ← 必须是这个名字
CHAT_ID = os.environ["CHAT_ID"]       # ← 必须是这个名字
BINANCE_URL = "https://api.binance.com/api/v3/klines"
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
            "https://api.binance.com/api/v3/ticker/price",
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
    return {"below": None}  # None = 首次运行，还没有状态


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
    current_price, dma_200 = get_btc_data()
    is_below = current_price < dma_200
    state = load_state()
    prev_below = state.get("below")

    message = None

    if prev_below is None:
        # 首次运行：只记录状态，不发消息（避免启动时刷屏）
        state["below"] = is_below
        save_state(state)
        print(f"首次运行，已记录状态：below={is_below}")
        return

    if is_below and not prev_below:
        # 刚刚跌破
        message = (
            "🚨 <b>BTC 跌破 200DMA！</b>\n\n"
            + format_status(current_price, dma_200)
        )
    elif not is_below and prev_below:
        # 刚刚重新站上
        message = (
            "✅ <b>BTC 重新站上 200DMA</b>\n\n"
            + format_status(current_price, dma_200)
        )
    # 其余情况（持续高于 或 持续低于）都不发消息

    if message:
        send_message(message)
        print("已发送提醒消息")
    else:
        print(f"状态无变化（below={is_below}），不发送消息")

    # 更新并保存状态
    state["below"] = is_below
    save_state(state)


if __name__ == "__main__":
    main()
