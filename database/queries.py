from database.db import get_connection
from zoneinfo import ZoneInfo
from datetime import datetime
import pandas as pd
import time
import requests
from notifications import send_failure_notification


def get_latest_timestamp(symbol):

    symbol = symbol.upper()
    # opens database
    connection = get_connection()

    result = connection.execute(
        """
        SELECT MAX(timestamp)
        FROM bars
        WHERE symbol = ?
        """,
        [symbol]
    ).fetchone()        # returns single answer

    connection.close()

    if result[0] is None:   
        return None

    return result[0].replace(       # only return timestamp
        tzinfo=ZoneInfo("UTC")
    )


def get_all_account_balances():

    connection = get_connection()

    ny_date = datetime.now(
        ZoneInfo("America/New_York")
    ).date()

    result = connection.execute(
        """
        SELECT *
        FROM account
        WHERE date = ?;
        """,
        [ny_date]
    ).fetchall()

    connection.close()

    return result


def get_latest_bars(symbol, limit=100):

    symbol = symbol.upper()
    connection = get_connection()

    df = pd.read_sql("""
        SELECT
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            volume
        FROM bars
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, connection, params=(symbol, limit))

    connection.close()

    if df.empty:
        return None

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")

    return df


# get alpaca bars with retry logic
# retries = num attempts
# delay = initial wait time in seconds
def get_stock_bars_with_retry(client, req, retries=15, delay=5):
   
    for attempt in range(1, retries + 1):
        try:
            return client.get_stock_bars(req).df

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:

            print(f"Alpaca connection failed (attempt {attempt}/{retries})")
            print(e)

            if (attempt < retries):
                # wait time is expontential
                wait_time = delay * (2 ** (attempt - 1))
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

            else:
                print("All retries failed")

                send_failure_notification(
                    f"Alpaca connection failed after {retries} attempts to connect to market bars. queries.py\n\n"
                    f"Error: {e}"
                )

                raise