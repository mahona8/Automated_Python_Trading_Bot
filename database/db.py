import duckdb


# open the database file market.duckdb (or create it)
def get_connection():

    connection = duckdb.connect(
        "myCode/database/market.duckdb"
    )
    return connection


# wrapper function
def create_tables():

    connection = get_connection()

    create_bars_table(connection)
    create_positions_table(connection)
    create_trades_table(connection)
    create_account_balance_table(connection)

    connection.close()


def create_bars_table(connection):

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bars (
            symbol TEXT,
            timestamp TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            PRIMARY KEY(symbol, timestamp)
        )
    """)


def create_positions_table(connection):

    connection.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            symbol TEXT PRIMARY KEY,
            quantity DOUBLE,
            entry_price DOUBLE,
            entry_time TIMESTAMP,
            highest_price DOUBLE,
            stop_loss DOUBLE,
            trailing_stop DOUBLE
        )
    """)


def create_trades_table(connection):

    connection.execute("""
        CREATE SEQUENCE IF NOT EXISTS trade_id_seq;
    """)

    # automatically creates a unique int trade_id in ascending order
    connection.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY DEFAULT nextval('trade_id_seq'),
            symbol TEXT,
            side TEXT,
            quantity DOUBLE,
            price DOUBLE,
            trade_time TIMESTAMP,
            reason TEXT,
            pnl DOUBLE
        )
    """)


def create_account_balance_table(connection):

    connection.execute("""
        CREATE TABLE IF NOT EXISTS account (
            date DATE PRIMARY KEY,
            account_balance DOUBLE
        )
    """)