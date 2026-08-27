import time
from datetime import datetime
from zoneinfo import ZoneInfo

from trading import trade_executions
from trading import trade_functions
import market_data
import symbols
import db_logging
import data_for_user_functions
from database import queries



def main():

    while True:

        # 1 - check if market is open
        if not trade_functions.market_is_open():
            print("market is closed")
            time.sleep(60)
            continue

        # get market data from Alpaca
        market_data.update_market_data()

        # 2 - emergency EOD close
        if trade_functions.minutes_until_market_close() < 15:

            positions = db_logging.get_all_positions()

            for position in positions:
                symbol = position[0]

                # get latest data if needed
                df = queries.get_latest_bars(symbol)

                trade_executions.sell(symbol, df)

            # add current account balance of this date to account table
            account_balance = trade_functions.get_account_value()
            date = datetime.now(
                ZoneInfo("America/New_York")
            ).date()
            data_for_user_functions.add_account_balance(date, account_balance)

            print("Sold all positions")
            # after this stop buying
            time.sleep(3600)            # 1 hour
            continue


        # 3 - normal trading loop
        for symbol in symbols.NASDAQ_100_SYMBOLS:

            df = queries.get_latest_bars(symbol)

            # check sells first
            trade_executions.sell(symbol, df)

            # then check buys
            trade_executions.buy(symbol, df)

        
        # 4 - update positions if current price > highest_price 
        # needed for trailing stop
        positions = db_logging.get_all_positions()

        for position in positions:

            symbol = position[0]
            highest_price = position[4]
            stop_loss = position[5]

            # get latest market data for this held position
            df = queries.get_latest_bars(symbol)
            current_price = df["close"].iloc[-1]

            # new high reached
            if current_price > highest_price:

                new_highest_price = current_price

                # example: trailing stop 5% below highest price
                new_trailing_stop = current_price * 0.95

                db_logging.update_position(
                    symbol,
                    new_highest_price,
                    stop_loss,
                    new_trailing_stop
                )

        # 5 - wait for next minute bar
        time.sleep(60)


# only run main() if this file is being run directly, not imported by another file
if __name__ == "__main__":
    main()