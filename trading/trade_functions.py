import ta
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

from market_data import trading_client
from notifications import send_failure_notification

import broker_api



def get_market_clock():
    try:
        return trading_client.get_clock()

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        ConnectionResetError
    ) as e:
        print(
            "Alpaca connection failed while getting market clock."
        )
        print(e)

        send_failure_notification(
            f"Alpaca connection failed while getting market clock: {e}"
        )

        raise


def market_is_open(clock):
    return clock.is_open


def minutes_until_market_close(clock):
    now = datetime.now(
        ZoneInfo("America/New_York")
    )

    close = clock.next_close

    return (
        close - now
    ).total_seconds() / 60


def liquidate_all_positions():
    """
    Liquidate every open Alpaca position.

    This bot is LONG-ONLY.

    Procedure:
        1. Get actual positions from Alpaca.
        2. Sell every position.
        3. Wait for each order to fill.
        4. Re-query Alpaca.
        5. Confirm there are no positions remaining.

    Returns:
        True
            Alpaca is confirmed flat.

        False
            One or more positions remain, or an order failed.

        broker_api.ORDER_UNKNOWN
            An order's final state could not be determined.
    """

    print("=" * 60)
    print("STARTING EOD ALPACA LIQUIDATION")
    print("=" * 60)

    # Get actual Alpaca positions
    try:
        positions = broker_api.get_open_positions()

    except Exception as e:
        print(
            f"Could not retrieve Alpaca positions "
            f"for EOD liquidation: {e}"
        )
        return False

    if not positions:
        print("Alpaca already has no open positions.")
        print("EOD liquidation complete.")
        return True

    print(
        f"Found {len(positions)} Alpaca position(s) "
        f"to liquidate."
    )

    # Sell each actual Alpaca position
    for position in positions:

        symbol = position.symbol.upper()
        quantity = float(position.qty)

        print(
            f"EOD liquidation: "
            f"{symbol} x {quantity}"
        )

        if quantity <= 0:
            print(
                f"Unexpected non-positive position quantity "
                f"for {symbol}: {quantity}"
            )
            return False

        order = broker_api.sell_order(
            symbol,
            quantity
        )

        # Alpaca connection/order state unknown
        if order == broker_api.ORDER_UNKNOWN:
            print(
                f"Could not determine final state of "
                f"EOD SELL order for {symbol}."
            )

            # DO NOT submit another sell order
            # original order may have reached Alpaca
            # reconcile the account instead
            return broker_api.ORDER_UNKNOWN

        # order failed
        if order is None:
            print(
                f"EOD SELL order failed for {symbol}."
            )
            return False

        # order filled
        try:
            exit_price = float(order.filled_avg_price)

            print(
                f"EOD SELL filled: "
                f"{symbol} x {quantity} "
                f"@ {exit_price}"
            )

        except Exception:
            print(
                f"EOD SELL filled for {symbol}, "
                f"but could not read filled average price."
            )

    # Re-query Alpaca after all sells
    print("Verifying Alpaca account is flat...")

    try:
        remaining_positions = broker_api.get_open_positions()

    except Exception as e:
        print(
            f"Could not verify Alpaca positions after "
            f"EOD liquidation: {e}"
        )
        return False

    # confirm flat
    if not remaining_positions:
        print("=" * 60)
        print("EOD LIQUIDATION COMPLETE - ALPACA IS FLAT")
        print("=" * 60)

        return True
    

    # if positions remain:
    print(
        "WARNING: Alpaca still has open position(s) "
        "after EOD liquidation:"
    )

    for position in remaining_positions:
        print(
            f"  {position.symbol}: "
            f"{position.qty} shares"
        )

    print("=" * 60)
    print("EOD LIQUIDATION FAILED - ALPACA IS NOT FLAT")
    print("=" * 60)

    return False



def get_rsi(df, window=14):
    return ta.momentum.RSIIndicator(
        close=df["close"],
        window=window
    ).rsi()


def get_macd(df):
    macd_indicator = ta.trend.MACD(
        close=df["close"]
    )

    return (
        macd_indicator.macd(),
        macd_indicator.macd_signal(),
        macd_indicator.macd_diff()
    )


def get_vwap(df):
    return ta.volume.VolumeWeightedAveragePrice(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        volume=df["volume"]
    ).volume_weighted_average_price()


def price_above_vwap(df):
    if df is None or df.empty:
        return False

    vwap = get_vwap(df)

    return df["close"].iloc[-1] > vwap.iloc[-1]


def rsi_momentum(df):
    if df is None or df.empty:
        return False

    rsi = get_rsi(df)

    return rsi.iloc[-1] > 50


def macd_bullish_cross(df):
    if df is None or len(df) < 2:
        return False

    macd, signal, _ = get_macd(df)

    return (
        macd.iloc[-2] <= signal.iloc[-2]
        and macd.iloc[-1] > signal.iloc[-1]
    )


def macd_bearish_cross(df):
    if df is None or len(df) < 2:
        return False

    macd, signal, _ = get_macd(df)

    return (
        macd.iloc[-2] >= signal.iloc[-2]
        and macd.iloc[-1] < signal.iloc[-1]
    )

