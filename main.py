"""
main.py

Main entry point and control loop of the swing trading bot.
Handles initialization, data fetching, and coordination of other modules.

Author: M Haghverdi
Date: 2025-07-26
"""
import os
import time
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5
from typing import Tuple, Optional
import pandas as pd

SYMBOL         = "EURUSD"
TIMEFRAME      = mt5.TIMEFRAME_H4
BAR_COUNT      = 200

os.makedirs("logs", exist_ok=True)
log_filename = f"logs/log_{datetime.now():%Y-%m-%d_%H-%M-%S}.txt"
def log(msg: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(log_filename, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def check_market_open() -> Tuple[bool, Optional[timedelta]]:
    now = datetime.now(timezone.utc)
    wd = now.weekday()
    hour = now.hour

    if (wd == 6 and hour >= 21) or (0 <= wd <= 3) or (wd == 4 and hour < 21):
        return True, None

    if wd == 4 and hour >= 21:
        days = 2
    elif wd == 5:
        days = 1
    elif wd == 6 and hour < 21:
        days = 0
    else:
        days = 0

    next_open = (now + timedelta(days=days)).replace(
        hour=21, minute=0, second=0, microsecond=0
    )

    return False, next_open - now


def main():
    if not mt5.initialize():
        print("[❌] Failed to connect to MetaTrader 5.")
        return
    log("[✅] Connected to MetaTrader 5.")

    last_checked_candle_time = None

    while True:
        market_open, delta = check_market_open()
        if not market_open:
            hours, rem = divmod(int(delta.total_seconds()), 3600)
            minutes = rem // 60
            log(f"[ℹ️] Market closed. Opens in {hours}h {minutes}m.")
            time.sleep(60)
            continue      

        latest_bar = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 1)

        if latest_bar is None or len(latest_bar) == 0:
            log("[❌] Failed to get latest candle.")
            time.sleep(10)
            continue

        latest_df = pd.DataFrame(latest_bar)
        latest_df['time'] = pd.to_datetime(latest_bar['time'], unit='s', utc=True)
        latest_candle_time = latest_df['time'].iloc[-1]

        if last_checked_candle_time is not None and latest_candle_time <= last_checked_candle_time:
            time.sleep(1)
            continue

        log(f"[🆕] New candle detected at {latest_candle_time}")
        last_checked_candle_time = latest_candle_time

        bars = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, BAR_COUNT)
        if bars is None or len(bars) < BAR_COUNT:
            log("[❌] Not enough historical data.")
            time.sleep(10)
            continue                        

        df = pd.DataFrame(bars)
        df['time'] = pd.to_datetime(bars['time'], unit='s', utc=True)
        df.set_index('time', inplace=True)

        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[⛔] Terminated by user.")
