
import os
import time
import requests

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from dotenv import load_dotenv


# ENVIRONMENT / ALPACA CLIENT

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=False
)


ORDER_FILLED = "filled"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "canceled"
ORDER_EXPIRED = "expired"
ORDER_PENDING = "pending"
ORDER_UNKNOWN = "unknown"


def wait_for_fill(order_id, max_attempts=10, delay=2):
    """
    Wait for an Alpaca order to reach a terminal state.

    Returns:
        order object       -> order filled successfully
        None               -> order rejected/cancelled/expired
        ORDER_UNKNOWN      -> could not determine final state
    """

    for attempt in range(max_attempts):
        try:
            order = trading_client.get_order_by_id(order_id)

            status = str(order.status).lower()

            print(
                f"Order {order_id} status: "
                f"{status} "
                f"(attempt {attempt + 1}/{max_attempts})"
            )

            if status == ORDER_FILLED:
                return order

            if status in (
                ORDER_REJECTED,
                ORDER_CANCELLED,
                ORDER_EXPIRED
            ):
                print(
                    f"Order {order_id} ended with status: {status}"
                )
                return None

            time.sleep(delay)

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            ConnectionResetError
        ) as e:
            # IMPORTANT:
            # Do NOT submit another order here
            # original order may have reached Alpaca even though the response was lost
            print(
                f"Connection error while checking order "
                f"{order_id}: {e}"
            )
            time.sleep(delay)

        except Exception as e:
            print(
                f"Unexpected error while checking order "
                f"{order_id}: {e}"
            )
            time.sleep(delay)

    print(
        f"Could not determine final status of order "
        f"{order_id} after {max_attempts} attempts."
    )

    return ORDER_UNKNOWN



def buy_order(symbol, quantity):
    """
    Submit a market BUY order.

    Returns:
        filled order object
        None
        ORDER_UNKNOWN
    """

    try:
        quantity = float(quantity)

        if quantity <= 0:
            print(
                f"Cannot submit BUY order for {symbol}: "
                f"quantity={quantity}"
            )
            return None

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )

        order = trading_client.submit_order(
            order_data=order_request
        )

        print(
            f"BUY order submitted: "
            f"{symbol} x {quantity}"
        )

        return wait_for_fill(order.id)

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        ConnectionResetError
    ) as e:
        print(
            f"Connection error submitting BUY order "
            f"for {symbol}: {e}"
        )

        # we don't know whether Alpaca received the order
        # don't blindly resubmit
        return ORDER_UNKNOWN

    except Exception as e:
        print(
            f"BUY order failed for {symbol}: {e}"
        )
        return None



def sell_order(symbol, quantity):
    """
    Submit a market SELL order.

    This bot is long-only, so this function is used to
    reduce/close an existing long position.

    Returns:
        filled order object
        None
        ORDER_UNKNOWN
    """

    try:
        quantity = float(quantity)

        if quantity <= 0:
            print(
                f"Cannot submit SELL order for {symbol}: "
                f"quantity={quantity}"
            )
            return None

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )

        order = trading_client.submit_order(
            order_data=order_request
        )

        print(
            f"SELL order submitted: "
            f"{symbol} x {quantity}"
        )

        return wait_for_fill(order.id)

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        ConnectionResetError
    ) as e:
        print(
            f"Connection error submitting SELL order "
            f"for {symbol}: {e}"
        )

        # order may have reached Alpaca
        # don't blindly resubmit
        return ORDER_UNKNOWN

    except Exception as e:
        print(
            f"SELL order failed for {symbol}: {e}"
        )
        return None



def get_open_positions():
    """
    Return the bot's current Alpaca positions.

    The bot is long-only, so positions with a negative quantity
    are treated as unexpected account state rather than as
    short positions to manage.

    Returns:
        list of Alpaca position objects
    """

    try:
        return trading_client.get_all_positions()

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        ConnectionResetError
    ) as e:
        print(
            f"Connection error getting Alpaca positions: {e}"
        )
        raise

    except Exception as e:
        print(
            f"Error getting Alpaca positions: {e}"
        )
        raise

