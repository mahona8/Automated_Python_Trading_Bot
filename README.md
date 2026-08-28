
OVERVIEW:

A Python-based automated trading bot that downloads 1-minute market data 
for the Nasdaq-100 and applies a momentum trading strategy to identify potential 
trading opportunities. The project is designed for automated market-data analysis 
and strategy execution.



PROJECT STRUCTURE:

- database:
	- db.py				        create database & connect to db functions
	- market.duckdb		    	actual database (non-readable)
	- queries.py			    database functions
	- __init__.py			    treat database as a python package (not a folder)
    - reconciliation.py 		sends compares database to Alpaca and updates database to Alpaca
      								if discrepancies occur (due to connection failure)
- trading:
	- trade_functions.py		  functions involving indicators but no trading logic
	- trade_logic.py		      using indicator functions to form buy/sell logic	
	- trade_executions.py     combining trade and risk logic to make final decision,
                                 buys stock using broker_api.py and logs them using logging.py
	- risk_functions.py		    functions involving info but no risk logic
	- risk_logic.py           using risk functions to form risk logic	

- .env				secret Alpaca keys storage

- market_data.py		Connect to Alpaca, download & store market data

symbols.py			    list of symbols (companies), both live and backup hardcoded NASDAQ 100

logging.py                    update positions and trades table functions

main.py                        main file to run project from

broker_api.py                 connects to Alpaca to buy and sell orders. Controls paper vs live currency

data_for_user_functions.py        uses functions to display data in text format

data_for_user_display.py          asks user what info they want to display & executes. Runs separate from main.py

requirements.txt          	automatically records everything currently installed in .venv including all packages

notifications.py         	sends phone notifications



DATABASE:


* store all timestamps as UTC * (database is not timezone aware tho so times have to be adapted BEFORE they enter the table


- bars = symbol info (gets updated)

- positions = stock that I CURRENTLY own (gets updates)

- trades = all trades I have ever made (NEVER gets updated)
				- side = buy/sell
				- pnl = profit and loss

- account = account balance day by day


bars
PK = symbol, timestamp
________________________
symbol
timestamp
open
high
low
close
volume
rsi
macd
macd_signal
macd_histogram
vwap


positions
PK = symbol
_______________
symbol
quantity
entry_price
entry_time
highest_price
stop_loss
trailing_stop


trades
PK = trade_id
_______________
trade_id
symbol
side
quantity
price
trade_time
reason
pnl


account
PK = date
_______________
date
account_balance












