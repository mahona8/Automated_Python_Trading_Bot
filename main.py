import time

from notifications import send_failure_notification

from database import reconciliation
from trading import trade_executions
from trading import trade_functions

import broker_api
import market_data
import symbols
import db_logging

from database import queries


def main():

    print("=" * 60)
    print("TRADING BOT STARTED")
    print("=" * 60)

    while True:


        # 1 - GET MARKET CLOCK


        try:

            clock = (
                trade_functions.get_market_clock()
            )

        except Exception as e:

            print("")
            print(
                "ERROR: Could not get market clock."
            )
            print(e)

            # don't hammer Alpaca if the connection is unavailable.
            time.sleep(60)

            continue


        # 2 - CHECK IS MARKET OPEN?


        if not trade_functions.market_is_open(clock):

            print(
                "Market is closed."
            )

            time.sleep(60)

            continue


        # 3 - CALCULATE MINUTES UNTIL CLOSE


        try:

            minutes_to_close = (
                trade_functions
                .minutes_until_market_close(clock)
            )

        except Exception as e:

            print(
                "ERROR: Could not calculate "
                "minutes until market close."
            )

            print(e)

            time.sleep(60)

            continue

        print("")
        print("-" * 60)

        print(
            f"Market open. "
            f"Minutes until close: "
            f"{minutes_to_close:.2f}"
        )

        print("-" * 60)


        # 4 - EOD LIQUIDATION


        if minutes_to_close < 15:

            print("")
            print("=" * 60)
            print("EOD LIQUIDATION STARTING")
            print("=" * 60)

            # -------------------------------------------------
            # IMPORTANT:
            # Alpaca is authoritative for EOD liquidation.
            # We do NOT loop through DB positions here.
            #
            # This catches:
            #
            # - DB positions
            # - positions missing from DB
            # - positions created by an unknown order
            # - DB failures
            # - reconciliation discrepancies
            # -------------------------------------------------

            try:

                alpaca_flat = (
                    trade_functions.liquidate_all_positions()
                )

            except Exception as e:

                print("")
                print(
                    "ERROR during Alpaca EOD "
                    "liquidation:"
                )

                print(e)

                alpaca_flat = False

                send_failure_notification(
                    "4 - EOD ALPACA LIQUIDATION ERROR\n\n"
                    "The bot could not complete the "
                    "Alpaca EOD liquidation process.\n\n"
                    f"Error: {e}"
                )

            # alpaca is flat
            if alpaca_flat:

                print("")
                print("=" * 60)
                print("EOD LIQUIDATION SUCCESSFUL")
                print("Alpaca confirms account is FLAT.")
                print("=" * 60)


                # now reconcile local database
                try:

                    reconciliation_success = (
                        reconciliation.reconcile_positions()
                    )

                except Exception as e:

                    reconciliation_success = False

                    print(
                        "WARNING: Alpaca is flat, "
                        "but DB reconciliation raised "
                        "an exception."
                    )

                    print(e)

                if not reconciliation_success:

                    print("")
                    print(
                        "WARNING: Alpaca is FLAT, "
                        "but DB reconciliation could "
                        "not be confirmed."
                    )

                    send_failure_notification(
                        "4 - EOD DB RECONCILIATION WARNING\n\n"
                        "Alpaca confirmed FLAT, but "
                        "database reconciliation failed."
                    )

            # alpaca is NOT flat:
            else:

                print("")
                print("=" * 60)
                print(
                    "WARNING: COULD NOT CONFIRM "
                    "ALPACA IS FLAT"
                )
                print("=" * 60)

                send_failure_notification(
                    "4 - EOD LIQUIDATION\n\n"
                    "EOD liquidation could not confirm "
                    "that the Alpaca account is flat."
                )

            # don't start trading again this cycle
            print("")
            print(
                "EOD processing complete."
            )

            print(
                "Waiting before next trading cycle..."
            )

            time.sleep(3600)

            continue


        # 5 - GET ACCOUNT


        try:

            account = (
                broker_api
                .trading_client
                .get_account()
            )

            print("")
            print(
                f"Account equity: "
                f"${float(account.equity):,.2f}"
            )

            print(
                f"Buying power: "
                f"${float(account.buying_power):,.2f}"
            )

        except Exception as e:

            print("")
            print(
                "ERROR: Could not retrieve "
                "Alpaca account."
            )

            print(e)

            time.sleep(60)

            continue


        # 6 - UPDATE MARKET DATA


        try:

            market_data.update_market_data()

        except Exception as e:

            print("")
            print(
                "ERROR updating market data."
            )

            print(e)

            # don't trade with potentially stale or missing data.
            time.sleep(60)

            continue


        # 7 - PROCESS EACH SYMBOL


        for symbol in symbols.NASDAQ_100_SYMBOLS:

            print("")
            print(
                f"Processing {symbol}..."
            )

            try:

                # market data from local db
                df = (
                    queries
                    .get_latest_bars(symbol)
                )

                if df is None or df.empty:

                    print(
                        f"No market data available "
                        f"for {symbol}. "
                        f"Skipping."
                    )

                    continue

                # sell first
                result = (
                    trade_executions.sell(
                        symbol,
                        df,
                        minutes_to_close=minutes_to_close
                    )
                )

                # unkown sell
                if result == broker_api.ORDER_UNKNOWN:

                    print(
                        f"SELL order state UNKNOWN "
                        f"for {symbol}."
                    )

                    print(
                        "Reconciling DB with Alpaca "
                        "before continuing..."
                    )

                    try:

                        reconciliation.reconcile_positions()

                    except Exception as e:

                        print(
                            f"Reconciliation failed "
                            f"after unknown SELL "
                            f"for {symbol}: {e}"
                        )

                    # IMPORTANT:
                    #
                    # din't buy this symbol
                    # we don't know whether the SELL actually happened

                    continue

                # buy
                result = (
                    trade_executions.buy(
                        symbol,
                        df,
                        account
                    )
                )

                # unkown buy
                if result == broker_api.ORDER_UNKNOWN:

                    print(
                        f"BUY order state UNKNOWN "
                        f"for {symbol}."
                    )

                    print(
                        "Reconciling DB with Alpaca "
                        "before continuing..."
                    )

                    try:

                        reconciliation.reconcile_positions()

                    except Exception as e:

                        print(
                            f"Reconciliation failed "
                            f"after unknown BUY "
                            f"for {symbol}: {e}"
                        )

                    # IMPORTANT:
                    # Never automatically resubmit the BUY

                    continue

            except Exception as e:

                # one symbol must never kill the whole bot
                print("")

                print(
                    f"ERROR processing {symbol}:"
                )

                print(e)

                continue


        # 8 - UPDATE TRAILING STOPS


        print("")
        print(
            "Updating trailing stops..."
        )

        try:

            positions = (
                db_logging.get_all_positions()
            )

        except Exception as e:

            print(
                "Could not retrieve DB positions "
                "for trailing stops:"
            )

            print(e)

            positions = []

        for position in positions:

            try:

                symbol = position[0]

                highest_price = float(
                    position[4]
                )

                stop_loss = float(
                    position[5]
                )

                # local market data
                df = (
                    queries
                    .get_latest_bars(symbol)
                )

                if df is None or df.empty:

                    print(
                        f"No latest bars for "
                        f"{symbol}. "
                        f"Skipping trailing "
                        f"stop update."
                    )

                    continue

                current_price = float(
                    df["close"].iloc[-1]
                )

                # new high price
                if current_price > highest_price:

                    new_highest_price = (
                        current_price
                    )

                    new_trailing_stop = (
                        current_price * 0.95
                    )

                    db_logging.update_position(
                        symbol,
                        new_highest_price,
                        stop_loss,
                        new_trailing_stop
                    )

                    print(
                        f"{symbol}: trailing stop "
                        f"updated. "
                        f"Highest="
                        f"${new_highest_price:.2f}, "
                        f"Trailing Stop="
                        f"${new_trailing_stop:.2f}"
                    )

            except Exception as e:

                print(
                    f"ERROR updating trailing stop "
                    f"for {position[0]}: {e}"
                )

                # don't let one bad DB/data row stop the trading loop

                continue


        # 9 - WAIT
       

        print("")
        print(
            "Cycle complete."
        )

        print(
            "Sleeping for 60 seconds..."
        )

        print("")

        time.sleep(60)



if __name__ == "__main__":
    main()