from trading import trade_logic
from trading import trade_functions
from trading import risk_logic
from trading import risk_functions
from trading import risk_constants
import broker_api
import db_logging
from datetime import datetime
from zoneinfo import ZoneInfo


# place alpaca orders
# update positions table
# update trades table

# official and FINAL buy signal
def buy(symbol, df, account):

    # if indicators AND risk checks 
    if (
        trade_logic.buy_indicators(df)
        and risk_logic.should_buy(symbol, account)
    ):

        position_value = risk_functions.calculate_position_size(account)
        current_price = risk_functions.get_latest_price(symbol)

        if current_price is None:
            return False

        quantity = round(position_value / current_price, 6)

        if quantity <= 0:
            print(
                f"Trade blocked: position size ${position_value:.2f} "
                f"is too small to buy {symbol} at ${current_price:.2f}"
            )
            return False

        estimated_cost = quantity * current_price

        if estimated_cost > risk_functions.get_buying_power(account):
            print("Trade blocked: insufficient buying power")
            return False

        # Place order
        order = broker_api.buy_order(symbol, quantity)

        if order == broker_api.ORDER_UNKNOWN:
            print(f"BUY order state UNKNOWN for {symbol}.")
            return broker_api.ORDER_UNKNOWN

        if order is None:
            return False

        entry_time = datetime.now(ZoneInfo("UTC"))
        entry_price = float(order.filled_avg_price)

        stop_loss = (
            entry_price *
            (1 - risk_constants.STOP_LOSS_PERCENT)
        )

        trailing_stop = (
            entry_price *
            (1 - risk_constants.TRAILING_STOP_PERCENT)
        )

        side = "buy"
        reason = "buy_signal"
        pnl = None

        db_logging.add_position(
            symbol,
            quantity,
            entry_price,
            entry_time,
            stop_loss,
            trailing_stop
        )

        db_logging.add_trade(
            symbol,
            side,
            quantity,
            entry_price,
            entry_time,
            reason,
            pnl
        )

        return True

    return False


# official and FINAL sell signal
def sell(symbol, df, minutes_to_close):

    if df is None or df.empty:
        return False

    sell_signal = trade_logic.sell_indicators(df)
    risk_signal = risk_logic.should_sell(symbol)

    # indicators OR risk check OR market close approaching
    if (
        sell_signal
        or risk_signal
        or minutes_to_close <= 15
    ):

        # determine reason
        if minutes_to_close <= 15:
            reason = "market_closure"

        elif risk_signal:
            reason = "risk_signal"

        elif sell_signal:
            reason = "sell_signal"

        else:
            reason = None

        # Get current position
        position = db_logging.get_position(symbol)

        if position is None:
            return False

        quantity = float(position[1])
        entry_price = float(position[2])

        order = broker_api.sell_order(symbol, quantity)

        if order == broker_api.ORDER_UNKNOWN:
            print(
                f"SELL order state UNKNOWN for {symbol}."
            )
            return broker_api.ORDER_UNKNOWN

        if order is None:
            print(f"Sell order failed for {symbol}.")
            return False

        exit_price = float(order.filled_avg_price)

        pnl = risk_functions.calculate_pnl(
            entry_price,
            exit_price,
            quantity
        )

        side = "sell"
        trade_time = datetime.now(ZoneInfo("UTC"))

        db_logging.add_trade(
            symbol,
            side,
            quantity,
            exit_price,
            trade_time,
            reason,
            pnl
        )

        db_logging.remove_position(symbol)

        return True

    return False

