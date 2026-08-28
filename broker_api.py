import os
import time
import requests

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from notifications import send_failure_notification


API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=False
)


# ---------------------------------------------------------
# ORDER STATUS CONSTANTS
# ---------------------------------------------------------

ORDER_FILLED = "filled"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "canceled"
ORDER_EXPIRED = "expired"
ORDER_PENDING = "pending"
ORDER_UNKNOWN = "unknown"


# ---------------------------------------------------------
# WAIT FOR ORDER FILL
# ---------------------------------------------------------

def wait_for_fill(
    order_id,
    max_attempts=30,
    delay=1,
    connection_retry_delay=2
):
    """
    Wait for an Alpaca order to reach a terminal state.

    Returns:
        order object -> filled
        None         -> confirmed rejected/canceled/expired
        ORDER_UNKNOWN -> unable to determine final state
    """

    attempts = 0

    while attempts < max_attempts:

        attempts += 1

        try:
            order = trading_client.get_order_by_id(order_id)

            status = str(order.status).lower()

            print(
                f"Order {order_id} status: {status} "
                f"(attempt {attempts}/{max_attempts})"
            )

            if status == ORDER_FILLED:
                return order

            if status in {
                ORDER_REJECTED,
                ORDER_CANCELLED,
                ORDER_EXPIRED
            }:
                return None

            # Still open/pending
            time.sleep(delay)

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout
        ) as e:

            print(
                f"Alpaca connection failed while checking "
                f"order {order_id} "
                f"(attempt {attempts}/{max_attempts})"
            )
            print(e)

            if attempts < max_attempts:
                time.sleep(connection_retry_delay)

    print(
        f"Could not determine final status of order "
        f"{order_id}."
    )

    send_failure_notification(
        f"UNKNOWN Alpaca order state.\n"
        f"Class: broker_api.py\n"
        f"Function: wait_for_fill()\n\n"
        f"Order ID: {order_id}"
    )

    return ORDER_UNKNOWN


# ---------------------------------------------------------
# BUY ORDER
# ---------------------------------------------------------

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

        submitted_order = trading_client.submit_order(
            order_request
        )

        print(
            f"BUY order submitted successfully. "
            f"Order ID: {submitted_order.id}"
        )

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ) as e:

        # -------------------------------------------------
        # IMPORTANT:
        #
        # The request may have reached Alpaca even though
        # we never received the response.
        #
        # DO NOT resubmit the order here.
        # -------------------------------------------------

        print(
            "Connection failed while submitting BUY order."
        )
        print(e)

        send_failure_notification(
            f"UNKNOWN BUY ORDER STATE.\n"
            f"Class: broker_api.py\n"
            f"Function: buy_order()\n\n"
            f"Symbol: {symbol}\n"
            f"Quantity: {quantity}\n"
            f"Error: {e}\n\n"
            f"DO NOT automatically resubmit this order."
        )

        return ORDER_UNKNOWN

    # -----------------------------------------------------
    # WAIT FOR FILL
    # -----------------------------------------------------

    filled_order = wait_for_fill(
        submitted_order.id
    )

    return filled_order


# ---------------------------------------------------------
# SELL ORDER
# ---------------------------------------------------------

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

        submitted_order = trading_client.submit_order(
            order_request
        )

        print(
            f"SELL order submitted successfully. "
            f"Order ID: {submitted_order.id}"
        )

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ) as e:

        # -------------------------------------------------
        # DO NOT assume the sell failed.
        # -------------------------------------------------

        print(
            "Connection failed while submitting SELL order."
        )
        print(e)

        send_failure_notification(
            f"UNKNOWN SELL ORDER STATE.\n"
            f"Class: broker_api.py\n"
            f"Function: sell_order()\n\n"
            f"Symbol: {symbol}\n"
            f"Quantity: {quantity}\n"
            f"Error: {e}\n\n"
            f"DO NOT automatically resubmit this order."
        )

        return ORDER_UNKNOWN

    filled_order = wait_for_fill(
        submitted_order.id
    )

    return filled_order