import logging
from typing import Type
from algo_trading.sources.base_source import BaseSource
from algo_trading.sources.yfinance_source import YFinanceSource

# Configure logging
logger = logging.getLogger(__name__)

class DataHandler:
    """
    Main handler for managing data sources.
    """

    SOURCES = {
        "yfinance": YFinanceSource,
        # Future sources can be added here, e.g., "binance": BinanceSource
    }

    def __init__(self, source: str):
        """
        Initialize the DataHandler with a specific data source.

        Args:
            source (str): The key of the data source to use (e.g., "yfinance").
        """
        if source not in self.SOURCES:
            logger.error(f"Invalid data source: {source}")
            raise ValueError(f"Data source '{source}' is not supported.")
        self.source: Type[BaseSource] = self.SOURCES[source]()
        logger.info(f"DataHandler initialized with source: {source}")

    def fetch_data(self, symbol: str, **kwargs):
        """
        Fetch data from the selected data source.

        Args:
            symbol (str): The symbol to fetch data for (e.g., "AAPL").
            **kwargs: Additional parameters for the data source.

        Returns:
            pd.DataFrame: The fetched data.
        """
        try:
            logger.info(f"Fetching data for symbol: {symbol} using source: {self.source.__class__.__name__}")
            return self.source.fetch_data(symbol, **kwargs)
        except Exception as e:
            logger.error(f"Failed to fetch data for symbol: {symbol} using {self.source.__class__.__name__}: {e}")
            raise
