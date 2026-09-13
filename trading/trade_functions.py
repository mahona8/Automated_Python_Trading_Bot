
import ta
from market_data import trading_client
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from notifications import send_failure_notification


# Get market clock
# Alpaca request once
def get_market_clock():

    try:
        return trading_client.get_clock()

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ) as e:

        print("Alpaca connection failed while getting market clock.")
        print(e)

        send_failure_notification(
            "Alpaca connection failed while getting market clock.\n"
            "Class: trade_functions.py\n"
            "Function: get_market_clock()\n\n"
            f"Error: {e}"
        )

        raise


# is market open?
def market_is_open(clock):

    return clock.is_open


# Minutes until market closure
def minutes_until_market_close(clock):

    now = datetime.now(ZoneInfo("America/New_York"))

    close = clock.next_close

    return (close - now).total_seconds() / 60


# RSI
def get_rsi(df, window=14):

    df["rsi"] = ta.momentum.RSIIndicator(
        close=df["close"],
        window=window
    ).rsi()

    return df


# MACD
def get_macd(df):

    macd = ta.trend.MACD(
        close=df["close"],
        window_fast=3,
        window_slow=10,
        window_sign=16
    )

    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    return df


# VWAP
def get_vwap(df):

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    typical_price = (
        df["high"] +
        df["low"] +
        df["close"]
    ) / 3

    pv = typical_price * df["volume"]

    ny_dates = df.index.tz_convert(
        "America/New_York"
    ).date

    df["vwap"] = (
        pv.groupby(ny_dates).cumsum()
        /
        df["volume"].groupby(ny_dates).cumsum()
    )

    return df


# price above VWAP
def price_above_vwap(df):

    if df is None or df.empty:
        return False

    if "vwap" not in df.columns:
        df = get_vwap(df)

    latest = df.iloc[-1]

    return latest["close"] > latest["vwap"]


# RSI momentum
def rsi_momentum(df):

    if "rsi" not in df.columns:
        df = get_rsi(df)

    latest = df.iloc[-1]

    return latest["rsi"]


# MACD bullish cross
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


# MACD bearish cross
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

