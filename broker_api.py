import os
import time
import requests

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

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
#   order unknown -> unable to determine final state
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

            status = order.status

            print(
                f"Order {order_id} status: "
                f"{status} "
                f"({attempt}/{max_attempts})"
            )

            # Filled
            if status == OrderStatus.FILLED:
                return order

            # Confirmed failure
            if status in {
                OrderStatus.REJECTED,
                OrderStatus.CANCELED,
                OrderStatus.EXPIRED
            }:
                return None

            # Still open
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

            # Do not resubmit
            if attempt < max_attempts:

                # Give connection time to recover
                time.sleep(delay * 2)

            continue

    # Unknown
    print(
        f"ORDER UNKNOWN: could not determine final "
        f"state of {order_id}"
    )

    return ORDER_UNKNOWN

