import os
import time
import requests

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce



# ALPACA connection
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=False
)


# order status constants
ORDER_FILLED = "filled"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "canceled"
ORDER_EXPIRED = "expired"
ORDER_PENDING = "pending"
ORDER_UNKNOWN = "unknown"


# poll an order until it reaches a terminal state
# returns:
#   order object -> confiremed filled
#   none -> confirmed rejected/canceled/expired
#   oder unknown -> unable to determine final state
def wait_for_fill(
    order_id,
    max_attempts=10,
    delay=2
):

    for attempt in range(1, max_attempts + 1):

        try:

            order = trading_client.get_order_by_id(
                order_id
            )

            status = str(
                order.status
            ).lower()

            print(
                f"Order {order_id} status: "
                f"{status} "
                f"({attempt}/{max_attempts})"
            )

            # filled
            if status == ORDER_FILLED:
                return order

           # confirmed failure
            if status in {
                ORDER_REJECTED,
                ORDER_CANCELLED,
                ORDER_EXPIRED
            }:

                return None

            # still open
            if attempt < max_attempts:
                time.sleep(delay)

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout
        ) as e:

            print(
                f"Connection problem checking order "
                f"{order_id} "
                f"({attempt}/{max_attempts})"
            )

            print(e)

            # do not resubmit
            if attempt < max_attempts:

                # give connection time to recover
                time.sleep(delay * 2)

            continue

    # unknown
    print(
        f"ORDER UNKNOWN: could not determine final "
        f"state of {order_id}"
    )

    return ORDER_UNKNOWN


def buy_order(symbol, quantity):

    try:

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )

        print(
            f"Submitting BUY order: "
            f"{symbol} x {quantity}"
        )

        submitted_order = (
            trading_client.submit_order(
                order_request
            )
        )

        print(
            f"BUY submitted. "
            f"Order ID: {submitted_order.id}"
        )

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ) as e:

        print(
            "Connection failed while submitting BUY for Symbol: {symbol}\n"
            "Quantity: {quantity}\n"
            "Error: {e}\n\n"
        )
        print(e)

        return ORDER_UNKNOWN

    return wait_for_fill(
        submitted_order.id
    )


def sell_order(symbol, quantity):

    try:

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )

        print(
            f"Submitting SELL order: "
            f"{symbol} x {quantity}"
        )

        submitted_order = (
            trading_client.submit_order(
                order_request
            )
        )

        print(
            f"SELL submitted. "
            f"Order ID: {submitted_order.id}"
        )

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ) as e:

        print(
            "Connection failed while submitting SELL"
            "Symbol: {symbol}\n"
            "Quantity: {quantity}\n"
            "Error: {e}\n\n"
        )
        print(e)

        return ORDER_UNKNOWN

    return wait_for_fill(
        submitted_order.id
    )

