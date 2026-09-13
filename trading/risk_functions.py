from database.db import get_connection

from datetime import datetime
from zoneinfo import ZoneInfo

from trading.risk_constants import (
    MAX_POSITION_SIZE_PERCENT,
    STOP_LOSS_PERCENT,
    TRAILING_STOP_PERCENT
)

import db_logging



# account info
def get_account_value(account):

    return float(account.equity)


def get_buying_power(account):

    return float(account.buying_power)


# position size
def calculate_position_size(account):

    account_value = get_account_value(account)

    return account_value * MAX_POSITION_SIZE_PERCENT


# latest price
def get_latest_price(symbol):

    connection = get_connection()

    try:

        result = connection.execute(
            """
            SELECT close
            FROM bars
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [symbol]
        ).fetchone()

    finally:
        connection.close()

    if result is None:
        return None

    return result[0]


# latest trade time
def get_latest_trade_time(symbol):

    connection = get_connection()

    try:

        result = connection.execute(
            """
            SELECT MAX(trade_time)
            FROM trades
            WHERE symbol = ?;
            """,
            [symbol]
        ).fetchone()

    finally:
        connection.close()

    if result[0] is None:
        return None

    return result[0].replace(
        tzinfo=ZoneInfo("UTC")
    )


# time since last trade
def get_time_between_last_trade(symbol):

    last_trade_time = get_latest_trade_time(symbol)

    if last_trade_time is None:
        return 9999999

    current_time = datetime.now(
        ZoneInfo("UTC")
    )

    time_difference = (
        current_time - last_trade_time
    )

    return time_difference.total_seconds() / 60


# PNL
def calculate_pnl(
    entry_price,
    exit_price,
    quantity
):

    return (
        (exit_price - entry_price)
        * quantity
    )


# daily PNL
def get_daily_pnl():

    connection = get_connection()

    try:

        ny_date = datetime.now(
            ZoneInfo("America/New_York")
        ).date()

        result = connection.execute(
            """
            SELECT SUM(pnl)
            FROM trades
            WHERE DATE(trade_time) = ?;
            """,
            [ny_date]
        ).fetchone()

    finally:
        connection.close()

    return result[0] or 0


# daily PNL %
def get_daily_pnl_percent(account_value):

    if account_value == 0:
        return 0

    return get_daily_pnl() / account_value


# number of trades today
def get_num_trades_today():

    connection = get_connection()

    try:

        ny_date = datetime.now(
            ZoneInfo("America/New_York")
        ).date()

        result = connection.execute(
            """
            SELECT COUNT(*)
            FROM trades
            WHERE DATE(trade_time) = ?;
            """,
            [ny_date]
        ).fetchone()

    finally:
        connection.close()

    return result[0]


# do I own this stock alreday?
def own_stock(symbol):

    connection = get_connection()

    try:

        result = connection.execute(
            """
            SELECT *
            FROM positions
            WHERE symbol = ?
            """,
            [symbol]
        ).fetchone()

    finally:
        connection.close()

    return result is not None


# number of open positions
def get_num_open_positions():

    connection = get_connection()

    try:

        result = connection.execute(
            """
            SELECT COUNT(*)
            FROM positions
            """
        ).fetchone()

    finally:
        connection.close()

    return result[0]


# stop loss
def get_stop_loss(symbol):

    position = db_logging.get_position(symbol)

    if position is None:
        return None

    entry_price = float(position[2])

    return (
        entry_price *
        (1 - STOP_LOSS_PERCENT)
    )


# trailing stop
def get_trailing_stop(symbol):

    position = db_logging.get_position(symbol)

    if position is None:
        return None

    highest_price = float(position[4])

    return (
        highest_price *
        (1 - TRAILING_STOP_PERCENT)
    )

