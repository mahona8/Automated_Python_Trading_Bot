import os

import time
import requests
from notifications import send_failure_notification

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")


trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper = False
)

# pending while order is submitted but not fulfilled
def wait_for_fill(order_id):

    attempts = 0

    while attempts < 30:

        try:
            order = trading_client.get_order_by_id(order_id)

            if order.status == "filled":
                return order

            elif order.status in ["canceled", "rejected"]:
                return None

            time.sleep(1)
            attempts += 1

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print("Alpaca connection failed while checking order status")
            print(e)

            send_failure_notification(
                f"Alpaca connection failed while checking order status.\n"
                f"Class: broker_api.py\n"
                f"Function: wait_for_fill(order_id)\n\n"
                f"Order ID: {order_id}\n"
                f"Error: {e}"
            )
            return None


def buy_order(symbol, quantity):

    try:
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )

        submitted_order = trading_client.submit_order(order_request)
        filled_order = wait_for_fill(submitted_order.id)

        return filled_order

    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as e:

        print("Alpaca connection failed while submitting buy order")
        print(e)

        send_failure_notification(
            f"Alpaca connection failed while submitting buy order.\n"
            f"Class: broker_api.py\n"
            f"Function: buy_order(symbol, quantity)\n\n"
            f"Symbol: {symbol}\n"
            f"Quantity: {quantity}\n"
            f"Error: {e}"
        )
        return None


def sell_order(symbol, quantity):

    try:
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )

        submitted_order = trading_client.submit_order(order_request)
        filled_order = wait_for_fill(submitted_order.id)

        return filled_order

    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as e:

        print("Alpaca connection failed while submitting sell order")
        print(e)

        send_failure_notification(
            f"Alpaca connection failed while submitting sell order.\n"
            f"Class: broker_api.py\n"
            f"Function: sell_order(symbol, quantity)\n\n"
            f"Symbol: {symbol}\n"
            f"Quantity: {quantity}\n"
            f"Error: {e}"
        )
        return None


