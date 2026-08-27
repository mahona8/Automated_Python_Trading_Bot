from trading.risk_constants import (
    MAX_TRADES_PER_DAY,         
    MAX_DAILY_LOSS_PERCENT,
    MAX_OPEN_POSITIONS,
    MIN_TIME_BETWEEN_TRADES_MINUTES,
    STOP_LOSS_PERCENT,
    TRAILING_STOP_PERCENT,
    MAX_POSITION_SIZE_PERCENT
)

import db_logging
import trading.risk_functions as risk_functions


# return True if SHOULD buy, else return False
def should_buy(symbol):

    account_value = risk_functions.get_account_value()

    if (
        risk_functions.get_num_trades_today() <= MAX_TRADES_PER_DAY
        and risk_functions.get_buying_power() >= risk_functions.calculate_position_size(symbol)
        and risk_functions.market_open() == True
        and risk_functions.get_time_between_last_trade(symbol) >= MIN_TIME_BETWEEN_TRADES_MINUTES
        and risk_functions.get_daily_pnl_percent(account_value) >= MAX_DAILY_LOSS_PERCENT
        and risk_functions.own_stock(symbol) == False
        and risk_functions.get_num_open_positions() <= MAX_OPEN_POSITIONS
    ):
        return True

    return False


# return True if SHOULD sell, else return False
def should_sell(symbol):

    # market closed -> don't sell
    if not risk_functions.market_open():
        return False

    # no position exists -> don't sell
    position = db_logging.get_position(symbol)
    if position is None:
        return False

    # get current stock price
    current_price = risk_functions.get_latest_price(symbol)
    if current_price is None:
        return False

    # get stop levels
    stop_loss = risk_functions.get_stop_loss(symbol)
    trailing_stop = risk_functions.get_trailing_stop(symbol)

    # cannot make sell decision without stop values
    if stop_loss is None or trailing_stop is None:
        return False

    # price dropped below fixed stop loss
    if current_price <= stop_loss:
        return True

    # price dropped below trailing stop
    if current_price <= trailing_stop:
        return True

    return False