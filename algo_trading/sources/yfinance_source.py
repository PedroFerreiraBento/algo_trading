import logging
import yfinance as yf
import pandas as pd
from .base_source import BaseSource

# Configure logging
logger = logging.getLogger(__name__)

class YFinanceSource(BaseSource):
    """
    Data source plugin for fetching data from yfinance.
    """

    def fetch_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Fetch historical data for a given symbol using yfinance.

        Args:
            symbol (str): The stock ticker symbol (e.g., "AAPL").
            period (str): The period of historical data to fetch (default: "1y").
            interval (str): The interval of the data (default: "1d").

        Returns:
            pd.DataFrame: The fetched data.
        """
        try:
            logger.info(f"Fetching data for symbol: {symbol} (period={period}, interval={interval})")
            df = yf.download(symbol, period=period, interval=interval)
            if df.empty:
                logger.warning(f"No data found for symbol: {symbol}")
                raise ValueError(f"No data found for symbol: {symbol}")
            logger.info(f"Data successfully fetched for symbol: {symbol}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data from yfinance: {e}")
            raise RuntimeError(f"Failed to fetch data from yfinance: {e}")
