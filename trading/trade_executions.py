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


# official and FINAl buy signal
def buy(symbol, df):
    # if indicators = true AND risk checks = false
    if (trade_logic.buy_indicators(df) == True) and risk_logic.should_buy(symbol) == True:

        position_value = risk_functions.calculate_position_size(symbol)
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

        # prevent any crazy big buy orders
        estimated_cost = quantity * current_price
        if estimated_cost > risk_functions.get_buying_power():
            print("Trade blocked: insufficient buying power")
            return False

        # place order
        order = broker_api.buy_order(symbol, quantity)

        if order == broker_api.ORDER_UNKNOWN:

            print(
                f"BUY order state UNKNOWN for {symbol}. "
            )
            return broker_api.ORDER_UNKNOWN

        if order is None:
            return False
        
        entry_time = datetime.now(ZoneInfo("UTC"))
        entry_price = float(order.filled_avg_price)
        stop_loss = entry_price * (1 - risk_constants.STOP_LOSS_PERCENT)
        trailing_stop = entry_price * (1 - risk_constants.TRAILING_STOP_PERCENT)
        side = "buy"
        reason = "buy_signal"
        pnl = None

        # log
        db_logging.add_position(symbol, quantity, entry_price,
                             entry_time, stop_loss, trailing_stop)

        db_logging.add_trade(symbol, side, quantity,
                 entry_price, entry_time, reason, pnl)
    else:
        return False


# official and FINAl sell signal 
def sell(symbol, df):

    if df is None or df.empty:
        return 

    # if indicators = true OR risk checks = true OR market close approaching
    if (trade_logic.sell_indicators(df) == True
        or risk_logic.should_sell(symbol) == True
        or trade_functions.minutes_until_market_close() <= 15):

        # determine reason
        if trade_functions.minutes_until_market_close() <= 15:
            reason = "market_closure"

        elif risk_logic.should_sell(symbol) == True:
            reason = "risk_signal"

        elif trade_logic.sell_indicators(df) == True:
            reason = "sell_signal"

        else:
            reason = None

        # get current position
        position = db_logging.get_position(symbol)

        if position is None:
            return False

        quantity = float(position[1])
        entry_price = float(position[2])

        order = broker_api.sell_order(symbol, quantity)

        if order == broker_api.ORDER_UNKNOWN:

            print(
            f"SELL order state UNKNOWN for {symbol}. "
            )
            return broker_api.ORDER_UNKNOWN

        if order is None:
            print(f"Sell order failed for {symbol}.")
            return False

        # get actual sell fill price
        exit_price = float(order.filled_avg_price)

        # calculate profit/loss
        pnl = risk_functions.calculate_pnl(
            entry_price,
            exit_price,
            quantity
        )

        side = "sell"
        trade_time = datetime.now(ZoneInfo("UTC"))

        # log completed trade
        db_logging.add_trade(
            symbol,
            side,
            quantity,
            exit_price,
            trade_time,
            reason,
            pnl
        )

        # remove open position
        db_logging.remove_position(symbol)

    else:
        return False