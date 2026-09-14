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

        # 1 - GET MARKET CLOCK ONCE
        try:
            clock = trade_functions.get_market_clock()
        except Exception as e:
            print("")
            print("ERROR: Could not get market clock.")
            print(e)

            # don't hammer Alpaca if connection is unavailable
            time.sleep(60)
            continue



        # 2 - CHECK IS MARKET OPEN
        if not trade_functions.market_is_open(clock):
            print("Market is closed.")
            time.sleep(60)
            continue



        # 3 - CALCULATE TIME UNTIL MARKET CLOSE ONCE
        try:
            minutes_to_close = trade_functions.minutes_until_market_close(clock)
        except Exception as e:
            print("ERROR: Could not calculate minutes until market close.")
            print(e)

            time.sleep(60)
            continue

        print("")
        print("-" * 60)
        print(f"Market open. Minutes until close: {minutes_to_close:.2f}")
        print("-" * 60)



        # 4 - EOD lLIQUIDATION
        if minutes_to_close < 15:

            print("")
            print("=" * 60)
            print("EOD LIQUIDATION STARTING")
            print("=" * 60)

            # first close positions known by my DB
            positions = db_logging.get_all_positions()

            if not positions:
                print("No DB positions to liquidate.")
            else:
                print(f"Found {len(positions)} DB position(s).")

            for position in positions:
                symbol = position[0]

                print("")
                print(f"EOD DB position: {symbol} x {position[1]}")

                try:
                    df = queries.get_latest_bars(symbol)

                    if df is None or df.empty:
                        print(
                            f"Could not get market data for {symbol}. "
                            f"Skipping DB liquidation attempt."
                        )
                        continue

                    result = trade_executions.sell(
                        symbol,
                        df,
                        minutes_to_close=minutes_to_close
                    )

                    if result == broker_api.ORDER_UNKNOWN:
                        print(
                            f"EOD SELL for {symbol} returned UNKNOWN."
                        )

                        # don't resubmit order
                        # reconciliation will determine whether Alpaca
                        # actually received/filled order
                        try:
                            reconciliation.reconcile_positions()
                        except Exception as reconcile_error:
                            print(
                                f"Reconciliation failed after unknown "
                                f"EOD SELL for {symbol}: "
                                f"{reconcile_error}"
                            )

                    elif result is False:
                        print(
                            f"EOD SELL failed or was not completed "
                            f"for {symbol}."
                        )

                    else:
                        print(
                            f"EOD SELL completed for {symbol}."
                        )

                except Exception as e:
                    print(
                        f"ERROR liquidating DB position {symbol}: {e}"
                    )

                    send_failure_notification(
                        f"EOD LIQUIDATION ERROR\n\n"
                        f"Symbol: {symbol}\n"
                        f"Error: {e}"
                    )

                    # continue trying remaining positions
                    continue

            # Second check Alpaca directly
            # This catches:
            # - positions not in our DB
            # - unknown orders that actually filled
            # - DB failures
            # - any other discrepancy
            print("")
            print("Checking Alpaca for remaining positions...")

            try:
                alpaca_flat = reconciliation.close_all_alpaca_positions()
            except Exception as e:
                print(
                    "ERROR while closing remaining Alpaca positions:"
                )
                print(e)

                alpaca_flat = False

                send_failure_notification(
                    f"EOD ALPACA LIQUIDATION ERROR\n\n"
                    f"Class: main.py\n"
                    f"4 - EOD LIQUIDATION\n\n"
                    f"Error: {e}"
                )

            # final result
            if alpaca_flat:
                print("")
                print("=" * 60)
                print("EOD LIQUIDATION SUCCESSFUL")
                print("Alpaca confirms account is FLAT.")
                print("=" * 60)

                # make sure my DB agrees with Alpaca being flat
                try:
                    reconciliation.reconcile_positions()
                except Exception as e:
                    print(
                        "WARNING: Alpaca is flat, but final DB "
                        f"reconciliation failed: {e}"
                    )

                    send_failure_notification(
                        f"4 - EOD DB RECONCILIATION WARNING\n\n"
                        f"Alpaca confirmed FLAT, but DB reconciliation failed.\n\n "
                        f"Error: {e}"
                    )

            else:
                print("")
                print("=" * 60)
                print("WARNING: COULD NOT CONFIRM ALPACA IS FLAT")
                print("=" * 60)

                send_failure_notification(
                    "4 - EOD LIQUIDATION"
                    "EOD liquidation could not confirm "
                    "that the Alpaca account is flat"
                )

            # don't immediately start making trades again
            # sleep until the next reasonable trading cycle
            time.sleep(3600)
            continue



        # 5 - GET ACCOUNT ONCE PER LOOP
        try:
            account = broker_api.trading_client.get_account()

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
            print("ERROR: Could not retrieve Alpaca account.")
            print(e)

            # there's no point evaluating BUY decisions if we
            # can't determine account equity/buying power
            time.sleep(60)
            continue



        # 6 - UPDATE MARKET DATA
        try:
            market_data.update_market_data()
        except Exception as e:
            print("")
            print("ERROR updating market data.")
            print(e)

            # don't trade using potentially stale/missing data
            time.sleep(60)
            continue



        # 7 - PROCESS EACH SYMBOL
        for symbol in symbols.NASDAQ_100_SYMBOLS:

            print("")
            print(f"Processing {symbol}...")

            try:
                # get latest bars from local DB.
                # NO Alpaca API request
                df = queries.get_latest_bars(symbol)

                if df is None or df.empty:
                    print(
                        f"No market data available for {symbol}. "
                        f"Skipping."
                    )
                    continue

                # sell first
                result = trade_executions.sell(
                    symbol,
                    df,
                    minutes_to_close=minutes_to_close
                )

                if result == broker_api.ORDER_UNKNOWN:

                    print(
                        f"SELL order state UNKNOWN for {symbol}."
                    )

                    print(
                        "Reconciling DB with Alpaca before "
                        "continuing to the next symbol..."
                    )

                    try:
                        reconciliation.reconcile_positions()
                    except Exception as e:
                        print(
                            f"Reconciliation failed after unknown "
                            f"SELL for {symbol}: {e}"
                        )

                    # -----------------------------------------
                    # IMPORTANT:
                    # Do NOT try to buy this same symbol
                    # We don't know whether the SELL happened
                    # Move directly to the next symbol
                    # -----------------------------------------
                    continue

                # buy
                result = trade_executions.buy(
                    symbol,
                    df,
                    account
                )

                if result == broker_api.ORDER_UNKNOWN:

                    print(
                        f"BUY order state UNKNOWN for {symbol}."
                    )

                    print(
                        "Reconciling DB with Alpaca before "
                        "continuing to the next symbol..."
                    )

                    try:
                        reconciliation.reconcile_positions()
                    except Exception as e:
                        print(
                            f"Reconciliation failed after unknown "
                            f"BUY for {symbol}: {e}"
                        )

                    # -----------------------------------------
                    # IMPORTANT:
                    # Never automatically resubmit the BUY
                    # Move to the next symbol
                    # -----------------------------------------
                    continue

            except Exception as e:

                # -------------------------------------------------
                # A failure on one symbol should NEVER kill the
                # entire trading loop.
                # -------------------------------------------------
                print("")
                print(
                    f"ERROR processing {symbol}:"
                )
                print(e)

                # continue to next symbol
                continue



        # 8 - UPDATE TRAILING STOPS
        print("")
        print("Updating trailing stops...")

        try:
            positions = db_logging.get_all_positions()
        except Exception as e:
            print(
                f"Could not retrieve DB positions "
                f"for trailing stops: {e}"
            )
            positions = []

        for position in positions:

            try:
                symbol = position[0]
                highest_price = float(position[4])
                stop_loss = float(position[5])

                # market data comes from local DB
                df = queries.get_latest_bars(symbol)

                if df is None or df.empty:
                    print(
                        f"No latest bars for {symbol}. "
                        f"Skipping trailing stop update."
                    )
                    continue

                current_price = float(df["close"].iloc[-1])

                # new high
                if current_price > highest_price:

                    new_highest_price = current_price
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
                        f"{symbol}: trailing stop updated. "
                        f"Highest=${new_highest_price:.2f}, "
                        f"Trailing Stop=${new_trailing_stop:.2f}"
                    )

            except Exception as e:

                print(
                    f"ERROR updating trailing stop for "
                    f"{position[0]}: {e}"
                )

                # don't let one bad DB/data row stop the bot
                continue



        # 9 - WAIT BEFORE NEXT CYCLE
        print("")
        print("Cycle complete.")
        print("Sleeping for 60 seconds...")
        print("")

        time.sleep(60)


if __name__ == "__main__":
    main()