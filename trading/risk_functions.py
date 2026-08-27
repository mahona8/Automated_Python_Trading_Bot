from database.db import get_connection
from market_data import trading_client
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import requests

from notifications import send_failure_notification
from trading.risk_constants import MAX_POSITION_SIZE_PERCENT
from trading.risk_constants import STOP_LOSS_PERCENT
from trading.risk_constants import TRAILING_STOP_PERCENT
import db_logging

# get from Alpaca, not database
# returns total account value
def get_account_value(retries=15, delay=5):

    for attempt in range(1, retries + 1):
        try:
            account = trading_client.get_account()
            return float(account.equity)

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print(f"Alpaca connection failed while getting account value "
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
                    f"to get account value."
                    f"Class: risk_functions.py"
                    f"Function: get_account_value(int retries, int delay)\n\n"
                    f"Error: {e}"
                )
                raise

# get info from Alpaca
# returns current money available for new trades
def get_buying_power(retries=15, delay=5):

    for attempt in range(1, retries + 1):
        try:
            account = trading_client.get_account()
            return float(account.buying_power)

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print(f"Alpaca connection failed while getting buying power "
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
                    f"to get buying power."
                    f"Class: risk_functions.py"
                    f"Function: get_buying_power(int retries, int delay)\n\n"
                    f"Error: {e}"
                )
                raise

# get info from Alpaca: True or False
def market_open(retries=15, delay=5):

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
                    f"to check market status."
                    f"Class: risk_functions.py"
                    f"Function: market_open(int retries, int delay)\n\n"
                    f"Error: {e}"
                )
                raise


# how much money should go into this trade? - 10% of total account balance
def calculate_position_size(symbol):
    account_value = get_account_value()
    return account_value * MAX_POSITION_SIZE_PERCENT


# get current price of open positions for stop loss and trailing stop
def get_latest_price(symbol):

    connection = get_connection()

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
    connection.close()

    if result is None:
        return None

    return result[0]


# returns time last trade I made was
def get_latest_trade_time(symbol):

    # opens database
    connection = get_connection()

    result = connection.execute(
        """
        SELECT MAX(trade_time)
        FROM trades
        WHERE symbol = ?;
        """,
        [symbol]
    ).fetchone()      
    connection.close()

    if result[0] is None:
        return None

    return result[0].replace(
        tzinfo=ZoneInfo("UTC")
    )   


# returns num minutes between last trade I made and now
def get_time_between_last_trade(symbol):

    last_trade_time = get_latest_trade_time(symbol)

    if last_trade_time is None:
        return 9999999      # in case no previous trade exists

    current_time = datetime.now(ZoneInfo("UTC"))

    time_difference = current_time - last_trade_time

    minutes = time_difference.total_seconds() / 60

    return minutes


# calculate pnl when sell a stock
def calculate_pnl(entry_price, exit_price, quantity):

    pnl = (exit_price - entry_price) * quantity

    return pnl


# return sum of pnl for this day
def get_daily_pnl():

    connection = get_connection()

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

    connection.close()

    return result[0] or 0       # 0 in case no trades have been made, doesn't return NULL then


# can return positive (profit) or negative (loss) values
def get_daily_pnl_percent(account_value):

    # prevent diviion error
    if account_value == 0:
        return 0

    daily_pnl = get_daily_pnl()

    return daily_pnl / account_value


# how many trades have I made today
def get_num_trades_today():

    connection = get_connection()

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

    connection.close()

    return result[0]


# do I already own this stock
def own_stock(symbol):

    connection = get_connection()

    result = connection.execute(
        """
        SELECT *
        FROM positions
        WHERE symbol = ?
        """,
        [symbol]
    ).fetchone()     
    connection.close()
    return result is not None     # returns True if I own stock, else False
    

# how many open posiyions do I currently have
def get_num_open_positions():

    connection = get_connection()

    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM positions
        """
    ).fetchone()
    connection.close()
    return result[0]


# uses entry price to calculate price where sell must happen due to loss
def get_stop_loss(symbol):

    position = db_logging.get_position(symbol)

    if position is None:
        return None

    entry_price = position[2]

    return entry_price * (1 - STOP_LOSS_PERCENT)


# uses highest price SINCE buying to calculate price where sell must happen due to loss
def get_trailing_stop(symbol):

    position = db_logging.get_position(symbol)

    if position is None:
        return None

    highest_price = position[4]

    return highest_price * (1 - TRAILING_STOP_PERCENT)


