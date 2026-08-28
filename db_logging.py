from database.db import get_connection

# POSITION TABLE FUNCTIONS

def add_position(symbol, quantity, entry_price,
                 entry_time, stop_loss, trailing_stop):
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO positions (symbol, quantity, entry_price, 
            entry_time, highest_price, stop_loss, trailing_stop)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [symbol, quantity, entry_price, entry_time,
         entry_price, stop_loss, trailing_stop]
    )
    connection.close()


def update_position(symbol, highest_price,
                 stop_loss, trailing_stop):
    connection = get_connection()
    connection.execute(
        """
        UPDATE positions
        SET highest_price = ?,
        stop_loss = ?,
        trailing_stop = ?
        WHERE symbol = ?
        """,
        [highest_price, stop_loss, trailing_stop, symbol]
    )
    connection.close()


# get all info about a specific stock in open position
def get_position(symbol):

    connection = get_connection()
    result = connection.execute(
        """
        SELECT *
        FROM positions
        WHERE symbol = ?
        """,
        [symbol]
    ).fetchone()
    connection.close()
    return result


def remove_position(symbol):
    connection = get_connection()
    connection.execute(
        """
        DELETE FROM positions
        WHERE symbol = ?
        """,
        [symbol]
    )
    connection.close()


def get_all_positions():

    connection = get_connection()
    result = connection.execute(
        """
        SELECT *
        FROM positions
        """
    ).fetchall()    # gets rows before connection to db closes

    connection.close()
    return result


# TRADES TABLE FUNCTIONS


def add_trade(symbol, side, quantity,
                 price, trade_time, reason, pnl):
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO trades (symbol, side, 
            quantity, price, trade_time, reason, pnl)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [symbol, side, quantity,
         price, trade_time, reason, pnl]
    )
    connection.close()


# get 1 unique trade by id
def get_trade(trade_id):

    connection = get_connection()
    result = connection.execute(
        """
        SELECT *
        FROM trades
        WHERE trade_id = ?
        """,
        [trade_id]
    ).fetchone()
    connection.close()
    return result


def get_all_trades():

    connection = get_connection()
    result = connection.execute(
        """
        SELECT *
        FROM trades
        """
    ).fetchall()    # gets rows before connection to db closes

    connection.close()
    return result


# POSITION RECONCILIATION HELPER FUNCTIONS

def delete_all_positions():
    """
    Delete all local open-position records.

    WARNING:
    This only changes the database.
    It does NOT sell anything at Alpaca.
    """

    connection = get_connection()

    connection.execute(
        """
        DELETE FROM positions
        """
    )
    connection.close()


def replace_position(
    symbol,
    quantity,
    entry_price,
    entry_time,
    stop_loss,
    trailing_stop
):
    """
    Replace/create a position in the local DB.

    Used by reconciliation when Alpaca is considered
    authoritative.
    """

    connection = get_connection()

    connection.execute(
        """
        DELETE FROM positions
        WHERE symbol = ?
        """,
        [symbol]
    )

    connection.execute(
        """
        INSERT INTO positions (
            symbol,
            quantity,
            entry_price,
            entry_time,
            highest_price,
            stop_loss,
            trailing_stop
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            symbol,
            quantity,
            entry_price,
            entry_time,
            entry_price,
            stop_loss,
            trailing_stop
        ]
    )
    connection.close()


def get_position_symbols():

    connection = get_connection()

    result = connection.execute(
        """
        SELECT symbol
        FROM positions
        """
    ).fetchall()
    connection.close()

    return {row[0] for row in result}


def update_position_quantity(symbol, quantity):
    connection = get_connection()

    connection.execute(
        """
        UPDATE positions
        SET quantity = ?
        WHERE symbol = ?
        """,
        [quantity, symbol]
    )

    connection.close()