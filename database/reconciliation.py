from datetime import datetime
from zoneinfo import ZoneInfo

import db_logging
import broker_api

from trading.risk_constants import (
    STOP_LOSS_PERCENT,
    TRAILING_STOP_PERCENT
)


# ---------------------------------------------------------
# GET ALPACA POSITIONS
# ---------------------------------------------------------

def get_alpaca_positions():

    positions = broker_api.trading_client.get_all_positions()

    result = {}

    for position in positions:

        symbol = position.symbol.upper()

        quantity = float(position.qty)
        entry_price = float(position.avg_entry_price)

        result[symbol] = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": entry_price
        }

    return result


# ---------------------------------------------------------
# RECONCILE DB WITH ALPACA
# ---------------------------------------------------------

def reconcile_positions():
    """
    Alpaca is authoritative.

    Only positions that do not match are changed.

    Matching positions are left completely untouched.

    Cases handled:

        1. Alpaca and DB match
           -> do nothing

        2. Alpaca has position, DB does not
           -> add position to DB

        3. DB has position, Alpaca does not
           -> remove position from DB

        4. Both have position but quantities differ
           -> update DB quantity only

    Existing DB information such as:
        entry_time
        highest_price
        stop_loss
        trailing_stop

    is preserved whenever possible.
    """

    print("")
    print("=" * 60)
    print("POSITION RECONCILIATION")
    print("=" * 60)

    # -----------------------------------------------------
    # GET ALPACA POSITIONS
    # -----------------------------------------------------

    try:

        alpaca_positions = get_alpaca_positions()

    except Exception as e:

        print(
            "Could not retrieve positions from Alpaca."
        )
        print(e)

        return False

    # -----------------------------------------------------
    # GET DB POSITIONS
    # -----------------------------------------------------

    db_positions = db_logging.get_all_positions()

    db_position_dict = {
        row[0]: {
            "symbol": row[0],
            "quantity": float(row[1]),
            "entry_price": float(row[2]),
            "entry_time": row[3],
            "highest_price": float(row[4]),
            "stop_loss": float(row[5]),
            "trailing_stop": float(row[6])
        }
        for row in db_positions
    }

    alpaca_symbols = set(alpaca_positions.keys())
    db_symbols = set(db_position_dict.keys())

    all_symbols = alpaca_symbols | db_symbols

    changes_made = False

    # -----------------------------------------------------
    # COMPARE EACH POSITION
    # -----------------------------------------------------

    for symbol in sorted(all_symbols):

        alpaca_position = alpaca_positions.get(symbol)
        db_position = db_position_dict.get(symbol)

        # =================================================
        # CASE 1:
        # BOTH EXIST
        # =================================================

        if alpaca_position and db_position:

            alpaca_qty = alpaca_position["quantity"]
            db_qty = db_position["quantity"]

            # ---------------------------------------------
            # QUANTITY MATCHES
            # ---------------------------------------------

            if abs(alpaca_qty - db_qty) < 0.000001:

                print(
                    f"OK      {symbol}: "
                    f"Alpaca={alpaca_qty}, "
                    f"DB={db_qty}"
                )

            # ---------------------------------------------
            # QUANTITY DOES NOT MATCH
            # ---------------------------------------------

            else:

                print(
                    f"MISMATCH {symbol}: "
                    f"Alpaca={alpaca_qty}, "
                    f"DB={db_qty}"
                )

                print(
                    f"Updating DB quantity for {symbol}: "
                    f"{db_qty} -> {alpaca_qty}"
                )

                db_logging.update_position_quantity(
                    symbol,
                    alpaca_qty
                )

                changes_made = True

        # =================================================
        # CASE 2:
        # ALPACA HAS POSITION, DB DOES NOT
        # =================================================

        elif alpaca_position and not db_position:

            quantity = alpaca_position["quantity"]
            entry_price = alpaca_position["entry_price"]

            print(
                f"MISSING DB {symbol}: "
                f"Alpaca={quantity}, "
                f"DB=0"
            )

            print(
                f"Adding {symbol} to DB."
            )

            recovered_time = datetime.now(
                ZoneInfo("UTC")
            )

            stop_loss = (
                entry_price *
                (1 - STOP_LOSS_PERCENT)
            )

            trailing_stop = (
                entry_price *
                (1 - TRAILING_STOP_PERCENT)
            )

            db_logging.add_position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                entry_time=recovered_time,
                stop_loss=stop_loss,
                trailing_stop=trailing_stop
            )

            changes_made = True

        # =================================================
        # CASE 3:
        # DB HAS POSITION, ALPACA DOES NOT
        # =================================================

        elif db_position and not alpaca_position:

            print(
                f"STALE DB {symbol}: "
                f"Alpaca=0, "
                f"DB={db_position['quantity']}"
            )

            print(
                f"Removing stale DB position: {symbol}"
            )

            db_logging.remove_position(symbol)

            changes_made = True

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    if not changes_made:

        print("")
        print(
            "Reconciliation complete: "
            "no DB changes required."
        )

    else:

        print("")
        print(
            "Reconciliation complete: "
            "only mismatched positions were updated."
        )

    # -----------------------------------------------------
    # VERIFY
    # -----------------------------------------------------

    print("")
    print("Verifying reconciliation...")

    try:

        alpaca_positions_after = get_alpaca_positions()

    except Exception as e:

        print(
            "Could not verify Alpaca positions."
        )
        print(e)

        return False

    db_positions_after = db_logging.get_all_positions()

    db_after = {
        row[0]: float(row[1])
        for row in db_positions_after
    }

    # Check every Alpaca position exists in DB
    # with the correct quantity.

    for symbol, alpaca_position in alpaca_positions_after.items():

        alpaca_qty = alpaca_position["quantity"]
        db_qty = db_after.get(symbol)

        if db_qty is None:

            print(
                f"RECONCILIATION FAILED: "
                f"{symbol} exists in Alpaca but not DB."
            )

            return False

        if abs(alpaca_qty - db_qty) >= 0.000001:

            print(
                f"RECONCILIATION FAILED: "
                f"{symbol} "
                f"Alpaca={alpaca_qty}, "
                f"DB={db_qty}"
            )

            return False

    # Check DB does not contain stale positions.

    for symbol, db_qty in db_after.items():

        if symbol not in alpaca_positions_after:

            print(
                f"RECONCILIATION FAILED: "
                f"{symbol} exists in DB but not Alpaca."
            )

            return False

    print("")
    print(
        "Reconciliation verified successfully."
    )
    print("=" * 60)

    return True