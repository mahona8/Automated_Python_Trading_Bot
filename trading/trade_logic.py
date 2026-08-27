import trading.trade_functions as trade_functions



# returns true (buy) or false (don't buy)
def buy_indicators(df):

    if (trade_functions.price_above_vwap(df) == True
    and (50 <=trade_functions.rsi_momentum(df) <= 70) and
    trade_functions.macd_bullish_cross(df) == True):
        return True
    else:
        return False
    

# returns true (sell) or false (don't sell)
def sell_indicators(df):
    if (trade_functions.price_above_vwap(df) == False
    and (30 <= trade_functions.rsi_momentum(df) <= 45) and
    trade_functions.macd_bearish_cross(df) == True):
        return True
    else:
        return False


# sell all open positions at EOD
def close_all_positions():
    if(trade_functions.minutes_until_market_close() <= 15):
        return True
    else:
        return False