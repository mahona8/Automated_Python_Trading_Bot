import time
from datetime import datetime
from zoneinfo import ZoneInfo

from notifications import send_failure_notification
from database import reconciliation
from trading import trade_executions
from trading import trade_functions
import broker_api
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

            print("")
            print("=" * 60)
            print("EOD LIQUIDATION STARTING")
            print("=" * 60)

            # First - sell everything recorded in DB


            positions = db_logging.get_all_positions()

            for position in positions:

                symbol = position[0]

                print(
                    f"EOD DB position: "
                    f"{symbol} x {position[1]}"
                )

                df = queries.get_latest_bars(symbol)

                try:
                    trade_executions.sell(symbol, df)

                except Exception as e:

                    print(
                        f"Error selling DB position {symbol}: {e}"
                    )

 
            # Second -  ask Alpaca what is ACTUALLY still held
            # This catches positions missing from DB, failed DB deletes,
            # previous connection failures,partial/unknown order outcomes
   
            print("")
            print("Checking Alpaca for remaining positions...")

            alpaca_flat = (
                reconciliation.close_all_alpaca_positions()
            )

            # Third - only consider EOD liquidation successful if
   
            if alpaca_flat:
                print("")
                print("EOD liquidation successful.")
                print("Alpaca confirms account is FLAT.")

                 # Make DB agree with Alpaca after EOD liquidation
                reconciliation.reconcile_positions()
                print("EOD liquidation and reconciliation complete.")

            else:
                print("")
                print(
                    "WARNING: Could not confirm Alpaca is flat."
                )

                send_failure_notification(
                    "EOD liquidation could not confirm "
                    "that Alpaca account is flat."
                )


    
            # Stop trading for rest of day
            time.sleep(3600)
            continue


        # 3 - normal trading loop
        for symbol in symbols.NASDAQ_100_SYMBOLS:

            df = queries.get_latest_bars(symbol)

            # check sells first
            result = trade_executions.sell(symbol, df)

            if result == broker_api.ORDER_UNKNOWN:
                print(f"Unknown SELL result for {symbol}. Reconciling...")
                reconciliation.reconcile_positions()
                continue

            # then check buys
            result = trade_executions.buy(symbol, df)

            if result == broker_api.ORDER_UNKNOWN:
                print(f"Unknown BUY result for {symbol}. Reconciling...")
                reconciliation.reconcile_positions()
                continue

        
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