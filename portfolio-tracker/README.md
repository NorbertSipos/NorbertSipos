# Portfolio Tracker

Local dashboard with live quotes, P/L, allocation and news. Python 3 standard library only, no installs.

    python3 server.py
    # open http://localhost:8000   (PORT=9000 python3 server.py to change)

- Edit `portfolio.json` to change holdings (units, average price, currency, news search).
- Quotes refresh every 15s (Yahoo Finance, unofficial/delayed), news every 5 min (Google News RSS).
- Totals are converted to EUR using live EURUSD / EURRON rates.
- Tickers: `EXXX.DE`, `SXR8.DE`, `SPCX`, `TVBETETF.RO`. If a feed shows an error, check the symbol on finance.yahoo.com.
