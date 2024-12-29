import logging
from abc import ABC, abstractmethod
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

class BaseSource(ABC):
    """
    Abstract base class for all data sources.
    """

    @abstractmethod
    def fetch_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """
        Fetch data for a given symbol.

        Args:
            symbol (str): The symbol to fetch data for (e.g., "AAPL").
            **kwargs: Additional parameters for the data source.

        Returns:
            pd.DataFrame: The fetched data.
        """
        logger.debug(f"Attempting to fetch data for symbol: {symbol}")
        pass
