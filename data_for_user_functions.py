from datetime import datetime
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import pandas as pd

from database.db import get_connection
from market_data import trading_client
import db_logging

def print_menu():

    return """
    please enter the number of your option or type 'exit'

    1: display account balance
    2: display account balance over time
    3: display a particular trade
    4: display a particular position
    5: display all trades made today
    6: display all positions
    7: display all trades
    """


def display_current_account_balance():

    account = trading_client.get_account()
    print("Account balance:", account.equity)


# uses matplotlib to use line graph with dynamic time
def display_account_balance_over_time():

    connection = get_connection()

    # read data
    df = connection.execute("""
    SELECT date, account_balance
    FROM account
    ORDER BY date
    """).fetchdf()

    # plot
    plt.plot(df["date"], df["account_balance"])

    # extend x-axis to the current date
    plt.xlim(
    df["date"].min(),
    pd.Timestamp.now(tz="America/New_York").tz_localize(None)
)

    # labels 
    plt.xlabel("date")
    plt.ylabel("account_value")
    plt.title("account_value Over Time")

    plt.show()


def add_account_balance(date, account_balance):

    connection = get_connection()
    connection.execute(
        """
        INSERT INTO account (date, account_balance)
        VALUES (?, ?)
        """,
        [date, account_balance]
    )
    connection.close()


def display_trade(trade_id):

    trade = db_logging.get_trade(trade_id)

    if trade is None:
        print(f"No trade found with trade_id {trade_id}")
        return

    price = f"{trade[4]:.2f}" if trade[4] is not None else "N/A"        # truncate to 2 decimals
    pnl = f"{trade[7]:.2f}" if trade[7] is not None else "N/A"
    trade_time = trade[5].strftime("%Y-%m-%d %H:%M") if trade[5] is not None else "N/A"     # truncate to min

    print("trade_id: ", trade[0])
    print("symbol: ", trade[1])
    print("side: ", trade[2])
    print("quantity: ", trade[3])
    print("price: ", price)
    print("trade_time: ", trade_time)
    print("reason: ", trade[6])
    print("pnl: ", pnl)


def display_position(symbol):

    position = db_logging.get_position(symbol)
    entry_time = position[3].strftime("%Y-%m-%d %H:%M")  
    entry_price = f"{position[2]:.2f}"   
    highest_price = f"{position[4]:.2f}"  

    print("symbol: ", position[0])
    print("quantity: ", position[1])
    print("entry_price: ", entry_price)
    print("entry_time: ", entry_time)
    print("highest_price: ", highest_price)
    print("stop_loss: ", position[5])
    print("trailing_stop: ", position[6])


def display_all_trades_today():

    ny_date = datetime.now(ZoneInfo("America/New_York")).date()

    connection = get_connection()

    trades = connection.execute(
        """
        SELECT *
        FROM trades
        WHERE DATE(trade_time) = ?
        """,
        [ny_date]
    ).fetchall()

    connection.close()
    display_trade_header()

    for trade in trades:
        display_trade_row(trade)
    

def display_all_positions():

    positions = db_logging.get_all_positions()

    print("   SYMBOL   |   QUANTITY    |   ENTRY_PRICE   |",
          "       ENTRY_TIME       |   HIGHEST_PRICE   |",
          "       STOP_LOSS       |   TRAILING_STOP   ")

    for position in positions:

        entry_price = f"{position[2]:.2f}" if position[2] is not None else "N/A"
        entry_time = position[3].strftime("%Y-%m-%d %H:%M") if position[3] is not None else "N/A"
        highest_price = f"{position[4]:.2f}" if position[4] is not None else "N/A"

        print("    ", position[0], "        ", position[1],
              "        ", entry_price, "            ", entry_time,
              "            ", highest_price, "            ", position[5],
              "            ", position[6])


def display_trade_header():
    print("   TRADE_ID   |   SYMBOL    |   SIDE   |",
          "   QUANTITY   |   PRICE   |", "        TRADE TIME        |"
             "       REASON       |       PNL       ")


def display_trade_row(trade):

    pnl = f"{trade[7]:.2f}" if trade[7] is not None else "N/A"      # truncate to 2 decimals rounded
    price = f"{trade[4]:.2f}" 
    trade_time = trade[5].strftime("%Y-%m-%d %H:%M")                

    print("    ", trade[0], "        ", trade[1], 
              "        ", trade[2], "        ", trade[3], 
              "        ", price, "        ", trade_time,
              "        ", trade[6], "        ", pnl   
              )


def display_all_trades():

    trades = db_logging.get_all_trades()
    display_trade_header()

    for trade in trades:
        display_trade_row(trade)
        
