"""Market data provider using yfinance.

Provides historical prices, options chains, fundamentals, and company info
via yfinance. No API key needed — all data is free.
"""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from src.data.models import CompanyFacts, FinancialMetrics, Price


def get_stock_prices(ticker: str, start_date: str, end_date: str) -> list[Price]:
    """Fetch historical OHLCV prices for a ticker via yfinance.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of Price objects sorted by date
    """
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=end_date, auto_adjust=True)

    if df.empty:
        return []

    prices = []
    for date_idx, row in df.iterrows():
        prices.append(
            Price(
                open=round(row["Open"], 4),
                close=round(row["Close"], 4),
                high=round(row["High"], 4),
                low=round(row["Low"], 4),
                volume=int(row["Volume"]),
                time=date_idx.strftime("%Y-%m-%d"),
            )
        )
    return prices


def get_stock_prices_df(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch historical prices as a DataFrame (convenience wrapper)."""
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=end_date, auto_adjust=True)
    if not df.empty:
        df.index = df.index.tz_localize(None)
        df.index.name = "Date"
    return df


def get_fundamentals(ticker: str) -> dict:
    """Fetch company fundamentals via yfinance.

    Returns dict with key financial metrics: market_cap, pe_ratio, margins, etc.
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "ticker": ticker,
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        "ev_to_revenue": info.get("enterpriseToRevenue"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "gross_margin": info.get("grossMargins"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "current_ratio": info.get("currentRatio"),
        "debt_to_equity": info.get("debtToEquity"),
        "free_cash_flow": info.get("freeCashflow"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "avg_volume": info.get("averageVolume"),
        "shares_outstanding": info.get("sharesOutstanding"),
    }


def get_company_info(ticker: str) -> CompanyFacts:
    """Fetch company info and metadata via yfinance."""
    stock = yf.Ticker(ticker)
    info = stock.info

    return CompanyFacts(
        ticker=ticker,
        name=info.get("longName", info.get("shortName", ticker)),
        industry=info.get("industry"),
        sector=info.get("sector"),
        exchange=info.get("exchange"),
        market_cap=info.get("marketCap"),
        number_of_employees=info.get("fullTimeEmployees"),
        website_url=info.get("website"),
        location=f"{info.get('city', '')}, {info.get('state', '')}, {info.get('country', '')}".strip(", "),
    )


def get_options_chain(ticker: str, expiration: str | None = None) -> dict:
    """Fetch options chain data for a ticker.

    Args:
        ticker: Stock ticker symbol
        expiration: Optional expiration date (YYYY-MM-DD). If None, uses nearest expiry.

    Returns:
        Dict with 'calls', 'puts' DataFrames and metadata
    """
    stock = yf.Ticker(ticker)
    expirations = stock.options

    if not expirations:
        return {"error": f"No options available for {ticker}", "calls": None, "puts": None}

    if expiration and expiration in expirations:
        target_exp = expiration
    else:
        target_exp = expirations[0]

    chain = stock.option_chain(target_exp)

    return {
        "ticker": ticker,
        "expiration": target_exp,
        "available_expirations": list(expirations),
        "calls": chain.calls.to_dict(orient="records"),
        "puts": chain.puts.to_dict(orient="records"),
        "calls_count": len(chain.calls),
        "puts_count": len(chain.puts),
    }


def get_financials(ticker: str) -> dict:
    """Fetch financial statements (income, balance sheet, cash flow) via yfinance."""
    stock = yf.Ticker(ticker)

    result = {}

    income = stock.financials
    if income is not None and not income.empty:
        result["income_statement"] = income.to_dict()

    balance = stock.balance_sheet
    if balance is not None and not balance.empty:
        result["balance_sheet"] = balance.to_dict()

    cashflow = stock.cashflow
    if cashflow is not None and not cashflow.empty:
        result["cash_flow"] = cashflow.to_dict()

    return result


def get_current_price(ticker: str) -> float | None:
    """Get the current/latest price for a ticker."""
    stock = yf.Ticker(ticker)
    info = stock.info
    return info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
