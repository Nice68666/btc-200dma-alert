import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
PRICE_URL = "https://data-api.binance.vision/api/v3/ticker/price"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
STATE_FILE = Path("state.json")

# 要监控的币种
SYMBOLS = {
    "BTCUSDT": "BTC",
    "BNBUSDT": "BNB",
}


def get_symbol_data(symbol: str):
    params = {
        "symbol": symbol,
        "interval": "1d",
        "limit": 201
    }
    response = requests.get(BINANCE_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    closed_candles = data[:-1]
    closes = [float(candle[4]) for candle in closed_candles]

    if len(closes) < 200:
        raise Exception(f"{symbol} 日线数据不足 200 天")

    dma_200 = sum(closes[-200:]) / 200
    current_price = float(
        requests.get(PRICE_URL, params={"symbol": symbol}, timeout=15).json()["price"]
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
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def format_status(name: str, current_price: float, dma_200: float) -> str:
    difference = (current_price - dma_200) / dma_200 * 100
    if current_price < dma_200:
        status = "🔴 低于 200DMA"
    else:
        status = "🟢 高于 200DMA"

    return f"""<b>{name} 200DMA 状态</b>
当前价格：${current_price:,.2f}
200日均线：${dma_200:,.2f}
距离200DMA：{difference:+.2f}%
状态：{status}
数据来源：Binance
检查时间：{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}"""


def check_symbol(symbol: str, name: str, state: dict) -> dict:
    current_price, dma_200 = get_symbol_data(symbol)
    is_below = current_price < dma_200
    prev_below = state.get(symbol)

    print(f"{name}: 价格={current_price:.2f}, 200DMA={dma_200:.2f}, below={is_below}, prev={prev_below}")

    message = None

    if prev_below is None:
        print(f"{name}: 首次运行，仅记录状态")
    elif is_below and not prev_below:
        message = f"🚨 <b>{name} 跌破 200DMA！</b>\n\n" + format_status(name, current_price, dma_200)
    elif not is_below and prev_below:
        message = f"✅ <b>{name} 重新站上 200DMA</b>\n\n" + format_status(name, current_price, dma_200)
    else:
        print(f"{name}: 状态无变化，不发送")

    if message:
        send_message(message)
        print(f"{name}: 已发送提醒")

    state[symbol] = is_below
    return state


def main():
    if not CHAT_ID or not str(CHAT_ID).strip():
        raise Exception("CHAT_ID 为空，请检查 GitHub Secrets")

    state = load_state()

    for symbol, name in SYMBOLS.items():
        state = check_symbol(symbol, name, state)

    save_state(state)
    print("全部检查完成")


if __name__ == "__main__":
    main()
