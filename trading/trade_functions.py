import ta
from market_data import trading_client
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import requests
from notifications import send_failure_notification


# return bool
def market_is_open(retries=15, delay=5):

    for attempt in range(1, retries + 1):
        try:
            clock = trading_client.get_clock()
            return clock.is_open

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print(f"Alpaca connection failed while checking market status "
                  f"(attempt {attempt}/{retries})")
            print(e)

            if attempt < retries:
                # wait time is exponential
                wait_time = delay * (2 ** (attempt - 1))
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

            else:
                print("All retries failed")

                send_failure_notification(
                    f"Alpaca connection failed after {retries} attempts "
                    f"to check market status.\n"
                    f"Class: trade_functions.py\n"
                    f"Function: market_is_open(int retries, int delay)\n\n"
                    f"Error: {e}"
                )
                raise


# returns datetime object
def get_market_closing_time(retries=15, delay=5):

    for attempt in range(1, retries + 1):
        try:
            return trading_client.get_clock().next_close

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print(f"Alpaca connection failed while getting market closing time "
                  f"(attempt {attempt}/{retries})")
            print(e)

            if attempt < retries:
                # wait time is exponential
                wait_time = delay * (2 ** (attempt - 1))
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

            else:
                print("All retries failed")

                send_failure_notification(
                    f"Alpaca connection failed after {retries} attempts "
                    f"to get market closing time.\n"
                    f"Class: trade_functions.py\n"
                    f"Function: get_market_closing_time(int retries, int delay)\n\n"
                    f"Error: {e}"
                )
                raise


# returns float in mins until market close
def minutes_until_market_close(retries=15, delay=5):

    for attempt in range(1, retries + 1):
        try:
            now = datetime.now(ZoneInfo("America/New_York"))
            close = trading_client.get_clock().next_close
            return (close - now).total_seconds() / 60

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print(f"Alpaca connection failed while calculating minutes "
                  f"until market close (attempt {attempt}/{retries})")
            print(e)

            if attempt < retries:
                # wait time is exponential
                wait_time = delay * (2 ** (attempt - 1))
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

            else:
                print("All retries failed")

                send_failure_notification(
                    f"Alpaca connection failed after {retries} attempts "
                    f"to calculate minutes until market close.\n"
                    f"Class: trade_functions.py\n"
                    f"Function: minutes_until_market_close(int retries, int delay)\n\n"
                    f"Error: {e}"
                )
                raise


# - RSI: overbought or oversold?
# Range: 0-100
# below 30 = buy
# above 70 = sell

def get_rsi(df, window = 14): 
    df["rsi"] = ta.momentum.RSIIndicator(
        close = df["close"],
        window = window
    ).rsi()
    return df


# MACD - changes in strength, direction & momentum

# MACD & SIGNAL:
# buy: macd line crosses above signal line (bullish)
# sell: macd line crosses below signal line (bearish)

# MACD & HISTOGRAM
# macd trading above 0 line: uptrend
# macd trading below 0 line: downtrend

# im using day-trading parameters not standard
def get_macd(df):
    macd  = ta.trend.MACD(close=df["close"], window_fast=3,
    window_slow=10,
    window_sign=16)

    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    return df


# VWAP - Combines price and volume average
# Resets at the start of each day
def get_vwap(df):

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
        
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    pv = typical_price * df["volume"]

    ny_dates = df.index.tz_convert("America/New_York").date

    df["vwap"] = (
        pv.groupby(ny_dates).cumsum()
        / df["volume"].groupby(ny_dates).cumsum()
    )

    return df


# is price above or below vwap line
# rturns true if price > vwap, else false
def price_above_vwap(df):

    if df is None or df.empty:
        return False

    # Make sure VWAP exists
    if "vwap" not in df.columns:
        df = get_vwap(df)

    # get latest row of dataframe
    latest = df.iloc[-1]
    return latest["close"] > latest["vwap"]


# returns rsi number between 0-100
def rsi_momentum(df):

    if "rsi" not in df.columns:
        df = get_rsi(df)

    latest = df.iloc[-1]
    return latest["rsi"]


# returns true if JUST NOW macd > signal, else returns false
def macd_bullish_cross(df):

    if "macd" not in df.columns:
        df = get_macd(df)

    previous = df.iloc[-2]
    latest = df.iloc[-1]

    return (
        previous["macd"] <= previous["macd_signal"]
        and
        latest["macd"] > latest["macd_signal"]
    )
    

# returns true if JUST NOW macd < signal, else returns false
def macd_bearish_cross(df):
    
    if "macd" not in df.columns:
        df = get_macd(df)
  

    previous = df.iloc[-2]
    latest = df.iloc[-1]

    return (
            previous["macd"] >= previous["macd_signal"]
            and
            latest["macd"] < latest["macd_signal"]
        )