from database.db import get_connection, create_tables
from database.queries import get_latest_timestamp
from database.queries import get_stock_bars_with_retry

import os
from dotenv import load_dotenv
import pandas as pd

from symbols import NASDAQ_100_SYMBOLS

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY,
)

# used to access market clock & other possible methods
trading_client = TradingClient(
    API_KEY, 
    SECRET_KEY, 
    paper = False
    )

print("Alpaca client created successfully")
create_tables()

def update_market_data():

    # use UTC consistently
    now = datetime.now(ZoneInfo("UTC"))

    # symbols that need data
    symbols_to_download = []
    symbol_start_dates = {}

    # ---------------------------------------------------------
    # 1. CHECK DATABASE
    # ---------------------------------------------------------

    for symbol in NASDAQ_100_SYMBOLS:

        timestamp = get_latest_timestamp(symbol)
        print(symbol, timestamp)

        # brand-new symbol/database
        if timestamp is None:

            # Initial download
            start_date = now - timedelta(days=10)

            symbols_to_download.append(symbol)
            symbol_start_dates[symbol] = start_date

        # existing symbol - update missing data
        elif timestamp < now - timedelta(minutes=2):

            # overlap by 1 hour to catch delayed/missing bars
            start_date = timestamp - timedelta(hours=1)

            symbols_to_download.append(symbol)
            symbol_start_dates[symbol] = start_date

    # ---------------------------------------------------------
    # 2. NOTHING TO UPDATE
    # ---------------------------------------------------------

    if not symbols_to_download:
        print("All stocks are already up to date")
        return

    print(
        f"Downloading {len(symbols_to_download)} symbols from Alpaca"
    )

    # ---------------------------------------------------------
    # 3. BATCH SYMBOLS
    # ---------------------------------------------------------

    BATCH_SIZE = 20

    # Number of recent 1-minute bars required per symbol
    INITIAL_BAR_LIMIT = 300

    all_bars = []

    for i in range(0, len(symbols_to_download), BATCH_SIZE):

        batch = symbols_to_download[i:i + BATCH_SIZE]

        print(
            f"\nDownloading batch "
            f"{(i // BATCH_SIZE) + 1} "
            f"({len(batch)} symbols)..."
        )

        for symbol in batch:

            print(f"  Downloading {symbol}...")

            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame(
                    amount=1,
                    unit=TimeFrameUnit.Minute
                ),
                start=symbol_start_dates[symbol],
                limit=INITIAL_BAR_LIMIT
            )

            try:
                stock_bars = get_stock_bars_with_retry(
                    client,
                    req
                )

            except Exception as e:

                print(
                    f"  Failed to download {symbol}: {e}"
                )

                continue

            if stock_bars.empty:

                print(
                    f"  No data found for {symbol}"
                )

                continue

            stock_bars = stock_bars.reset_index()

            # Make absolutely sure we only retain this symbol
            stock_bars = stock_bars[
                stock_bars["symbol"] == symbol
            ].copy()

            if stock_bars.empty:

                print(
                    f"  No data found for {symbol}"
                )

                continue

            # Only keep data from the required start date
            stock_bars = stock_bars[
                stock_bars["timestamp"]
                >= symbol_start_dates[symbol]
            ].copy()

            if stock_bars.empty:

                print(
                    f"  No new bars found for {symbol}"
                )

                continue

            all_bars.append(stock_bars)

            print(
                f"  {symbol}: {len(stock_bars)} bars"
            )

    # ---------------------------------------------------------
    # 4. NO DATA
    # ---------------------------------------------------------

    if not all_bars:

        print("No data returned from Alpaca")
        return

    # Combine all downloaded symbols
    bars_to_save = pd.concat(
        all_bars,
        ignore_index=True
    )

    # ---------------------------------------------------------
    # 5. SAVE TO DATABASE
    # ---------------------------------------------------------

    connection = get_connection()

    connection.register(
        "bars_dataframe",
        bars_to_save
    )

    connection.execute("""
        INSERT OR IGNORE INTO bars
        SELECT
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            volume
        FROM bars_dataframe
    """)

    connection.close()

    print(
        f"Saved {len(bars_to_save)} bars"
    )

    print(
        f"Successfully processed "
        f"{bars_to_save['symbol'].nunique()} / "
        f"{len(symbols_to_download)} symbols"
    )

    print("Market data update complete")


