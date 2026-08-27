import pandas as pd
import requests

# manual hardcoded list of all current Nasdaq 100 companies - July 2026
NASDAQ_100_BACKUP = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "AVGO",
    "GOOGL",
    "GOOG",
    "TSLA",
    "GOOGL",
    "COST",
    "NFLX",
    "AMD",
    "ADBE",
    "PEP",
    "CSCO",
    "TMUS",
    "INTU",
    "QCOM",
    "TXN",
    "AMGN",
    "HON",
    "ISRG",
    "BKNG",
    "SBUX",
    "GILD",
    "VRTX",
    "ADI",
    "PANW",
    "ADP",
    "REGN",
    "MDLZ",
    "LRCX",
    "MU",
    "INTC",
    "PYPL",
    "CMCSA",
    "MELI",
    "ABNB",
    "SNPS",
    "CDNS",
    "KLAC",
    "ORLY",
    "MAR",
    "CTAS",
    "CSX",
    "MRVL",
    "FTNT",
    "NXPI",
    "ROP",
    "WDAY",
    "PCAR",
    "EXC",
    "MNST",
    "AZN",
    "AEP",
    "PAYX",
    "ODFL",
    "FAST",
    "KDP",
    "DXCM",
    "EA",
    "TTWO",
    "IDXX",
    "CHTR",
    "BIIB",
    "XEL",
    "CTSH",
    "VRSK",
    "FANG",
    "CPRT",
    "GEHC",
    "ON",
    "ZS",
    "TEAM",
    "CRWD",
    "DDOG",
    "CSGP",
    "TTD",
    "ANSS",
    "CDW",
    "ILMN",
    "ALGN",
    "DLTR",
    "WBD",
    "ENPH",
    "MRNA",
    "LCID",
    "SIRI",
    "RIVN",
    "SMCI",
    "ARM",
    "APP",
    "CEG",
    "PLTR",
    "DASH",
    "COIN",
    "HOOD",
    "PANW",
    "MSTR"
]

# remove duplicate symbols from backup list
NASDAQ_100_BACKUP = list(set(NASDAQ_100_BACKUP))


# try download a live list of all current Nasdaq 100 companies
import pandas as pd
import requests


def load_nasdaq_100_symbols():

    try:
        url = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        rows = data["data"]["data"]["rows"]

        symbols = [
            row["symbol"]
            for row in rows
            if row.get("symbol")
        ]

        if len(symbols) >= 90:
            print(f"Loaded live NASDAQ-100 symbols: {len(symbols)}")
            return symbols

    except Exception as e:
        print("Nasdaq live loading failed:", e)

    print("Using backup symbols")
    return NASDAQ_100_BACKUP.copy()


NASDAQ_100_SYMBOLS = load_nasdaq_100_symbols()