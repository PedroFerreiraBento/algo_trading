import os  # Library for environment variable manipulation

# Definition of environment variable to avoid import circular issues during tests with `pytest`
os.environ["PYTEST_CURRENT_TEST"] = "dummy_test"

# Test libraries
import pytest  # Library for creating unit tests
from unittest.mock import patch, MagicMock  # Mocking of functions and objects during tests

# Data and data manipulation libraries
from datetime import datetime, timezone, timedelta  # Data and timezone manipulation
import pandas as pd  # Library for creating and manipulating DataFrames
import numpy as np  # Library for numerical array manipulation

# Imports from the project related to MetaTrader5 data sources
from algo_trading.sources.MetaTrader5_source.rates.rates import Rates  # Classe Rates for requesting ticks and candles

# Im    ports of models and enums related to MetaTrader5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlTick,  # Model of tick containing fields such as time, bid, ask, last, etc.
    ENUM_TIMEFRAME,  # Enum for definition of timeframes (M1, H1, etc.)
    ENUM_COPY_TICKS,  # Enum for definition of tick copy type (ALL, BID, LAST, etc.)
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
)

# Remove the environment variable after default initialization
os.environ.pop("PYTEST_CURRENT_TEST", None)  # Safe removal of the environment variable without risk of `KeyError`


# Test Symbols ------------------------------------------------------------------------------------
@pytest.fixture
def mock_symbol():
    """
    Fixture to create a mock of a `SymbolInfo` object with the necessary information for tests.

    This mock simulates the data of an asset like `EURUSD`, including:
    - `time`: Simulated reference timestamp.
    - `spread`: Fixed spread of 10 points.
    - `digits`: Precision of 5 decimal places.
    - `ask` and `bid`: Simulated ask and bid prices.
    - `volume_min`, `volume_max`, `volume_step`: Definitions of minimum, maximum, and step volume.
    - `trade_tick_size`: Minimum price increment (tick).
    - `trade_contract_size`: Contract size in base currency units.
    - `trade_tick_value_profit` and `trade_tick_value_loss`: Value per tick in profit and loss scenarios.
    - `currency_base`: Base currency of the currency pair.
    - `currency_profit`: Profit currency of the currency pair.
    - `description`: Textual description of the asset.
    - `name`: Name of the symbol (e.g., "EURUSD").

    Returns:
        MockSymbolInfo: Object containing simulated data for the currency pair `EURUSD`.
    """
    class MockSymbolInfo:
        def __init__(self):
            self.time = 1672531200  # 2023-01-01 00:00:00 UTC
            self.spread = 10  # Spread of 10 points
            self.digits = 5  # 5 decimal places
            self.ask = 1.2345  # Ask price
            self.bid = 1.2340  # Bid price
            self.volume_min = 0.01  # Minimum volume allowed
            self.volume_max = 100.0  # Maximum volume allowed
            self.volume_step = 0.01  # Increment allowed in volume
            self.trade_calc_mode = ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX # Type of profit and margin calculation
            self.trade_tick_size = 0.0001  # Minimum price increment (tick)
            self.trade_contract_size = 100000  # Contract size in base currency units
            self.trade_tick_value_profit = 1.0  # Value per tick in profit scenario
            self.trade_tick_value_loss = 1.0  # Value per tick in loss scenario
            self.currency_base = "USD"  # Base currency of the currency pair
            self.currency_profit = "EUR"  # Profit currency of the currency pair
            self.description = "Euro vs US Dollar"  # Description of the asset
            self.name = "EURUSD"  # Name of the symbol
            self.trade_calc_mode = ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX
            self.swap_mode = ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS
            self.swap_long = -1
            self.swap_short = -.5
            self.swap_rollover3days = 3
            
    return MockSymbolInfo()


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_symbols_names(mock_mt5):
    """
    Tests the `get_symbols_names` method of the `Rates` class.

    This test verifies if the method returns the correct list of symbol names available in the platform.

    Steps:
    1. Mocks the API response `symbols_get` with a fictitious symbol "EURUSD".
    2. Calls the `Rates.get_symbols_names()` method to obtain the list of symbol names.
    3. Verifies if the method `symbols_get` was called once.
    4. Compares the returned result with the expected list `["EURUSD"]`.

    Args:
        mock_mt5 (MagicMock): Mock of the `MetaTrader5` module.
    """
    # Mock of the symbol returned by the API
    mock_symbol = MagicMock()
    mock_symbol.name = "EURUSD"  # Define the name of the symbol as "EURUSD"
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Returns a tuple with a single symbol
    mock_mt5.initialize.return_value = True  # Simulates successful initialization of MetaTrader5
    mock_mt5.account_info.return_value = True  # Simulates successful account verification

    # Executes the `get_symbols_names` method to retrieve the list of symbol names
    symbols = Rates.get_symbols_names()

    # Verifications
    mock_mt5.symbols_get.assert_called_once()  # Verifies if `symbols_get` was called exactly once
    assert symbols == ["EURUSD"], "The method did not return the expected list of symbols."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_symbol_data(mock_mt5, mock_symbol):
    """
    Tests the `get_symbol_data` method of the `Rates` class.

    This test verifies if the method returns the correct detailed data of a symbol.

    Steps:
    1. Mocks the API response `symbols_get` and `symbol_info` with the data of the symbol "EURUSD".
    2. Calls the `Rates.get_symbol_data("EURUSD")` method to obtain the details of the symbol.
    3. Verifies if the method `symbol_info` was called with the symbol "EURUSD".
    4. Compares the attributes of the returned object with the expected values (e.g., name and spread).

    Args:
        mock_mt5 (MagicMock): Mock of the `MetaTrader5` module.
        mock_symbol (MockSymbolInfo): Mock of the symbol "EURUSD".
    """
    # Mock of the API responses `symbols_get` and `symbol_info`
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Returns the symbol "EURUSD" in the list of symbols
    mock_mt5.symbol_info.return_value = mock_symbol  # Returns the details of the symbol "EURUSD"
    mock_mt5.initialize.return_value = True  # Simulates successful initialization of MetaTrader5
    mock_mt5.account_info.return_value = True  # Simulates successful account verification

    # Executes the `get_symbol_data` method to retrieve the details of the symbol "EURUSD"
    symbol_data = Rates.get_symbol_data("EURUSD")

    # Verifications
    mock_mt5.symbol_info.assert_called_once_with("EURUSD")  # Verifies if `symbol_info` was called with "EURUSD"
    assert symbol_data.name == "EURUSD", "The returned symbol name does not match the expected value."
    assert symbol_data.spread == 10, "The returned spread does not match the expected value."

# Test Candles ------------------------------------------------------------------------------------
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_last_n_candles(mock_mt5, mock_symbol):
    """
    Tests the `Rates.get_last_n_candles` method, which returns the last N candles of an asset in MetaTrader5.

    Verifies if:
    1. The calls to `mt5.copy_rates_from` are made with the correct arguments.
    2. The return is a pandas DataFrame with the correct fields.
    3. The use of the `use_close_candle_time` flag changes the index to `close_time`.
    4. When there are fewer candles than requested, the method raises an appropriate error.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock to simulate the asset information.
    """

    # Mock of symbols and initializations
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulates that the asset is available
    mock_mt5.initialize.return_value = True  # Simulates successful initialization
    mock_mt5.account_info.return_value = True  # Simulates valid account information
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)  # Simulates the history limit

    # Mock of candle data (copy_rates_from)
    now = datetime.now(timezone.utc)
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),  # Most recent candle
            (int((now - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
            (int((now - timedelta(minutes=2)).timestamp()), 1.1250, 1.1270, 1.1240, 1.1260, 200),
            (int((now - timedelta(minutes=3)).timestamp()), 1.1260, 1.1280, 1.1250, 1.1270, 250),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Test with `use_close_candle_time=False`
    with patch("algo_trading.sources.MetaTrader5_source.rates.rates.datetime") as mock_datetime:
        mock_datetime.now.return_value = now  # Mock of the current time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)  # For real `datetime` calls

        candles = Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=4, use_close_candle_time=False)

    # Verifies if the function was called with the correct arguments
    mock_mt5.copy_rates_from.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, now, 4)

    # Verification of the returned DataFrame
    assert isinstance(candles, pd.DataFrame), "The return should be a DataFrame."
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"], "Incorrect columns in the DataFrame."
    assert candles.shape[0] == 4, "Número de candles retornados incorreto."
    assert candles.index.name == "time", "O índice deveria ser 'time'."

    # Test with `use_close_candle_time=True`
    candles_with_close_time = Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=4, use_close_candle_time=True)

    # Verification of the DataFrame with `close_time` as index
    assert isinstance(candles_with_close_time, pd.DataFrame), "The return should be a DataFrame."
    assert list(candles_with_close_time.columns) == ["open", "high", "low", "close", "tick_volume"], "Incorrect columns in the DataFrame."
    assert candles_with_close_time.shape[0] == 4, "The number of candles returned is incorrect."
    assert candles_with_close_time.index.name == "close_time", "The index should be 'close_time'."

    # Verify time differences to ensure consistency
    time_diffs = candles_with_close_time.index.to_series().diff().dt.total_seconds().dropna()
    median_diff = time_diffs.median()
    assert median_diff > 0, "The median time difference should be positive."

    # Scenario with fewer candles than requested (expected error)
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),
            (int((now - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    try:
        Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=4, use_close_candle_time=True)
    except ValueError as e:
        assert str(e) == "Insufficient data: At least 4 candles are required when 'use_close_candle_time' is True.", "Mensagem de erro incorreta."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_candles_before(mock_mt5, mock_symbol):
    """
    Tests the `Rates.get_candles_before` method, which returns the last N candles before a specific date in MetaTrader5.

    Verifies if:
    1. The method `mt5.copy_rates_from` is called with the date adjusted to fetch candles before the provided date (`date_to - 1 microsecond`).
    2. The result is a pandas DataFrame with the correct columns.
    3. The flag `use_close_candle_time=True` changes the DataFrame index to `close_time`.
    4. The median of the time intervals between candles is positive, ensuring temporal consistency.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock of the asset (e.g., "EURUSD").
    """
    
    # Mock of initial settings and terminal information
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulated asset
    mock_mt5.initialize.return_value = True  # Simulated successful terminal initialization
    mock_mt5.account_info.return_value = True  # Simulated account information
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)  # Mock of the maximum number of bars allowed

    # Define a data-alvo (date_to) para buscar candles antes dela
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Mock of returned candle data
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(date_to.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),  # Most recent candle
            (int((date_to - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
            (int((date_to - timedelta(minutes=2)).timestamp()), 1.1250, 1.1270, 1.1240, 1.1260, 200),
            (int((date_to - timedelta(minutes=3)).timestamp()), 1.1260, 1.1280, 1.1250, 1.1270, 250),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Executa o método `get_candles_before` com `use_close_candle_time=True`
    candles = Rates.get_candles_before(
        symbol="EURUSD",
        timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1,
        date_to=date_to,
        n_candles=4,
        use_close_candle_time=True
    )

    # Verifies if the function `copy_rates_from` was called with the adjusted date
    mock_mt5.copy_rates_from.assert_called_once_with(
        "EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, date_to - timedelta(microseconds=1), 4
    )

    # Verifications of the returned DataFrame structure
    assert isinstance(candles, pd.DataFrame), "The return should be a DataFrame."
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"], "Incorrect columns in the DataFrame."
    assert candles.shape[0] == 4, "The number of candles returned is incorrect."
    assert candles.index.name == "close_time", "The DataFrame index should be 'close_time'."

    # Verifies if the time difference between candles is consistent and positive
    time_diffs = candles.index.to_series().diff().dt.total_seconds().dropna()
    median_diff = time_diffs.median()
    assert median_diff > 0, "The median time difference should be positive."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_candles_range(mock_mt5, mock_symbol):
    """
    Tests the `Rates.get_candles_range` method, which returns candles of an asset in a specific date range.

    Verifies if:
    1. The method `mt5.copy_rates_range` is called with the correct arguments (`symbol`, `timeframe`, `date_from`, `date_to`).
    2. The return is a pandas DataFrame with the correct columns.
    3. The flag `use_close_candle_time=True` changes the DataFrame index to `close_time`.
    4. The median of the time intervals between candles is positive, ensuring temporal consistency.
    5. An error is raised when the number of candles returned is less than expected.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock of the asset (e.g., "EURUSD").
    """
    
    # Mock of initial settings and validations
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulates that the asset is available
    mock_mt5.initialize.return_value = True  # Simulates successful initialization
    mock_mt5.account_info.return_value = True  # Simulates that account information is accessible

    # Define the start and end dates for the interval
    date_from = datetime(2023, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Mock of returned candle data for the interval
    mock_mt5.copy_rates_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1220, 1.1230, 1.1210, 1.1225, 200),  # Initial candle
            (int((date_from + timedelta(minutes=1)).timestamp()), 1.1225, 1.1240, 1.1215, 1.1230, 250),
            (int((date_from + timedelta(minutes=2)).timestamp()), 1.1230, 1.1250, 1.1220, 1.1240, 300),
            (int(date_to.timestamp()), 1.1235, 1.1245, 1.1230, 1.1245, 350),  # Candle final
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Execute the method with `use_close_candle_time=True`
    candles = Rates.get_candles_range(
        symbol="EURUSD",
        date_from=date_from,
        date_to=date_to,
        timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1,
        use_close_candle_time=True
    )

    # Verifies if the function `copy_rates_range` was called with the correct arguments
    mock_mt5.copy_rates_range.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, date_from, date_to)

    # Verifications of the returned DataFrame structure
    assert isinstance(candles, pd.DataFrame), "The return should be a DataFrame."
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"], "The columns of the DataFrame are incorrect."
    assert candles.shape[0] == 4, "The number of candles returned does not match the expected value."
    assert candles.index.name == "close_time", "The DataFrame index should be 'close_time'."

    # Verifies if the time difference between candles is consistent and positive
    time_diffs = candles.index.to_series().diff().dt.total_seconds().dropna()
    median_diff = time_diffs.median()
    assert median_diff > 0, "The median time difference should be positive."

    # Simulate a scenario with less than 4 candles to validate error handling
    mock_mt5.copy_rates_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1220, 1.1230, 1.1210, 1.1225, 200),
            (int((date_from + timedelta(minutes=1)).timestamp()), 1.1225, 1.1240, 1.1215, 1.1230, 250),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Verifies if the method raises the correct error when the number of candles is insufficient
    with pytest.raises(ValueError, match="Insufficient data: At least 4 candles are required when 'use_close_candle_time' is True."):
        Rates.get_candles_range(
            symbol="EURUSD",
            date_from=date_from,
            date_to=date_to,
            timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1,
            use_close_candle_time=True
        )

# Test Ticks ------------------------------------------------------------------------------------00
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_last_n_ticks(mock_mt5, mock_symbol):
    """
    Tests the `Rates.get_last_n_ticks` method, which returns the last N ticks of an asset.

    Verifies if:
    1. The method `mt5.copy_ticks_from` is called with the correct arguments (`symbol`, `now`, `n_ticks`, `COPY_TICKS_ALL`).
    2. The return is a pandas DataFrame with the correct columns.
    3. The values returned in the DataFrame match the simulated data.
    4. The `time` index and the `time_msc` field are calculated correctly with second and millisecond precision.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock of the asset information.
    """
    
    # Initial mock settings
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulates that the asset is available
    mock_mt5.initialize.return_value = True  # Simulates successful initialization of MetaTrader5
    mock_mt5.account_info.return_value = True  # Simulates valid account information

    # Mock of returned tick data
    now = datetime.now(timezone.utc)  # Date and time now
    mock_mt5.copy_ticks_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1235, 1.1236, 1, 64, int(now.timestamp() * 1000)),  # Most recent tick
            (int((now - timedelta(seconds=1)).timestamp()), 1.1230, 1.1231, 1.1232, 1, 32, int((now - timedelta(seconds=1)).timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
            ("volume", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Execute the method with the mock of `datetime`
    with patch("algo_trading.sources.MetaTrader5_source.rates.rates.datetime") as mock_datetime:
        # Mock to return the fixed current time
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)  # Allows real calls to `datetime`

        # Call the `get_last_n_ticks` method
        ticks = Rates.get_last_n_ticks(symbol="EURUSD", n_ticks=2)

    # Verifies if the function `copy_ticks_from` was called with the correct arguments
    mock_mt5.copy_ticks_from.assert_called_once_with("EURUSD", now, 2, ENUM_COPY_TICKS.COPY_TICKS_ALL)

    # Verifications of the returned DataFrame structure
    assert isinstance(ticks, pd.DataFrame), "The return should be a DataFrame."
    assert list(ticks.columns) == ["time", "bid", "ask", "time_msc"], "The columns of the DataFrame are incorrect."
    assert ticks.shape[0] == 2, "The number of ticks returned does not match the expected value."

    # Verification of specific values in the DataFrame
    assert ticks.iloc[0]["bid"] == 1.1234, "The value 'bid' of the first tick is incorrect."
    assert ticks.iloc[0]["ask"] == 1.1235, "The value 'ask' of the first tick is incorrect."
    assert ticks.iloc[0]["time"] == pd.Timestamp(int(now.timestamp()), unit="s", tz="UTC"), "The 'time' field does not match the expected value."

    # Verification of the `time_msc` field (with millisecond precision)
    expected_time_msc = pd.Timestamp(int(now.timestamp() * 1000), unit="ms", tz="UTC")
    assert ticks.iloc[0]["time_msc"] == expected_time_msc, "The 'time_msc' field does not match the expected value."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_specific_tick(mock_mt5, mock_symbol):
    """
    Tests the `Rates.get_specific_tick` method, which returns a specific tick of an asset for a given date.

    Verifies if:
    1. The method `mt5.copy_ticks_from` is called with the correct arguments (`symbol`, `date_from`, `1`, `COPY_TICKS_ALL`).
    2. The return is an instance of the `MqlTick` class.
    3. The values of the returned `MqlTick` match the simulated data, including `time`, `bid`, `ask`, `last`, `volume`, `flags` and `time_msc`.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock of the asset information.
    """
    
    # Mock for initialization and validation of the asset
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulates that the asset is available
    mock_mt5.initialize.return_value = True  # Simulates successful initialization of MetaTrader5
    mock_mt5.account_info.return_value = True  # Simulates valid account information

    # Mock for the returned tick
    date_from = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)  # Date and time to get the specific tick
    mock_mt5.copy_ticks_from.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1234, 1.1235, 1.1236, 1, 1, 64, int(date_from.timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
            ("volume", "i8"), ("volume_real", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Call the `get_specific_tick` method
    tick = Rates.get_specific_tick(symbol="EURUSD", date_from=date_from)

    # Verifies if the function `copy_ticks_from` was called with the correct arguments
    mock_mt5.copy_ticks_from.assert_called_once_with("EURUSD", date_from, 1, ENUM_COPY_TICKS.COPY_TICKS_ALL)

    # Verifies if the return is an instance of the `MqlTick` class
    assert isinstance(tick, MqlTick), "The return should be an instance of `MqlTick`."

    # Verifies specific values of the returned `MqlTick`
    assert tick.time == date_from, "The `time` field of the tick is incorrect."
    assert tick.bid == 1.1234, "The `bid` field of the tick is incorrect."
    assert tick.ask == 1.1235, "The `ask` field of the tick is incorrect."
    assert tick.last == 1.1236, "The `last` field of the tick is incorrect."
    assert tick.volume == 1, "The `volume` field of the tick is incorrect."
    assert tick.flags == 64, "The `flags` field of the tick is incorrect."
    
    # Verifies the `time_msc` field (with millisecond precision)
    expected_time_msc = pd.Timestamp(int(date_from.timestamp() * 1000), unit="ms", tz="UTC")
    assert tick.time_msc == expected_time_msc, "The `time_msc` field does not match the expected value."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_ticks_range(mock_mt5, mock_symbol):
    """
    Tests the `Rates.get_ticks_range` method, which returns the ticks of an asset in a date range.

    Verifies if:
    1. The method `mt5.copy_ticks_range` is called with the correct arguments (`symbol`, `date_from`, `date_to`, `COPY_TICKS_ALL`).
    2. The return is a pandas DataFrame with the correct columns.
    3. The values returned in the DataFrame match the simulated data.
    4. The `time` and `time_msc` fields are calculated correctly with second and millisecond precision.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock of the asset information.
    """
    
    # Mock for validation of the asset and initialization
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulates that the asset is available
    mock_mt5.initialize.return_value = True  # Simulates successful initialization of the terminal
    mock_mt5.account_info.return_value = True  # Simulates that account information is accessible

    # Define the start and end dates of the interval
    date_from = datetime(2023, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Mock for the return of ticks within the date range
    mock_mt5.copy_ticks_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1234, 1.1235, 1.1236, 1, 64, int(date_from.timestamp() * 1000)),  # Initial tick
            (int(date_to.timestamp()), 1.1230, 1.1231, 1.1232, 1, 32, int(date_to.timestamp() * 1000)),  # Final tick
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
            ("volume", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Call the `get_ticks_range` method
    ticks = Rates.get_ticks_range(symbol="EURUSD", date_from=date_from, date_to=date_to)

    # Verifies if the function `copy_ticks_range` was called with the correct arguments
    mock_mt5.copy_ticks_range.assert_called_once_with("EURUSD", date_from, date_to, ENUM_COPY_TICKS.COPY_TICKS_ALL)

    # Verifications of the returned DataFrame structure
    assert isinstance(ticks, pd.DataFrame), "The return should be a DataFrame."
    assert list(ticks.columns) == ["time", "bid", "ask", "time_msc"], "The columns of the DataFrame are incorrect."
    assert ticks.shape[0] == 2, "The number of ticks returned does not match the expected value."

    # Verification of the values of the ticks
    assert ticks.iloc[0]["bid"] == 1.1234, "The `bid` field of the first tick is incorrect."
    assert ticks.iloc[0]["ask"] == 1.1235, "The `ask` field of the first tick is incorrect."
    assert ticks.iloc[0]["time"] == pd.Timestamp(int(date_from.timestamp()), unit="s", tz="UTC"), "The `time` field of the first tick is incorrect."
    assert ticks.iloc[0]["time_msc"] == pd.Timestamp(int(date_from.timestamp() * 1000), unit="ms", tz="UTC"), "The `time_msc` field of the first tick is incorrect."

# Validations ------------------------------------------------------------------------------------- 
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_validate_count_candles(mock_mt5):
    """
    Tests the `Rates.validate_count_candles` method, which validates the number of candles requested in relation to the maximum limit allowed by the MetaTrader5 terminal.

    This test verifies:
    1. If the method does not raise any exception when the number of candles is within the limit (`< maxbars`).
    2. If the method raises a `ValueError` when the number of candles requested exceeds the limit (`>= maxbars`).
    
    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate the MetaTrader5 terminal.
    """
    
    # Simulates the terminal response with the maximum number of bars allowed (maxbars)
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)

    # Valid case: the number of candles requested is within the limit
    Rates.validate_count_candles(9999)  # Should not raise an error

    # Invalid case: the number of candles requested exceeds the limit
    with pytest.raises(ValueError, match="The number of candles cannot be higher than terminal chart max bars"):
        Rates.validate_count_candles(10000)  # Should raise a ValueError with the corresponding message


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_validate_symbol(mock_mt5, mock_symbol):
    """
    Tests the `Rates.validate_symbol` method, which validates if the requested financial symbol is in the list of available symbols in the MetaTrader5 terminal.

    This test verifies:
    1. If the method does not raise any exception when the symbol is valid and is in the list of available symbols.
    2. If the method raises a `ValueError` when the symbol is not in the list of available symbols.

    Args:
        mock_mt5: Mock of the `MetaTrader5` object to simulate its functions.
        mock_symbol: Mock to simulate the financial symbol information.
    """
    
    # Mock for simulating the list of available symbols
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simulates that the symbol "EURUSD" is in the list
    mock_symbol.name = "EURUSD"  # Define the name of the mock symbol
    mock_mt5.initialize.return_value = True  # Simulates successful initialization of the terminal
    mock_mt5.account_info.return_value = True  # Simulates that account information is accessible

    # Valid case: the symbol is valid and is in the list of available symbols
    Rates.validate_symbol("EURUSD")  # Should not raise an exception

    # Invalid case: the symbol is not in the list of available symbols
    with pytest.raises(ValueError, match="The selected symbol is not in the symbols list"):
        Rates.validate_symbol("INVALID_SYMBOL")  # Should raise a ValueError with the corresponding message


def test_validate_request_result():
    """
    Tests the `Rates.validate_request_result` method, which validates the result of a data request.
    
    This test verifies:
    1. If the method does not raise any exception when the result of the request contains valid data.
    2. If the method raises a `TypeError` when the result of the request is `None`.
    3. If the method raises a `ValueError` when the result of the request is an empty array.
    """
    
    # Valid case: the result of the request contains valid data
    valid_result = np.array([1, 2, 3])  # Array with values
    Rates.validate_request_result(valid_result)  # Should not raise an error

    # Invalid case: the result of the request is `None`
    with pytest.raises(TypeError, match="Request error, please check the request format"):
        Rates.validate_request_result(None)  # Should raise a TypeError

    # Invalid case: the result of the request is an empty array
    with pytest.raises(ValueError, match="No data returned"):
        Rates.validate_request_result(np.array([]))  # Should raise a ValueError

    
def test_validate_date():
    """
    Tests the `Rates.validate_date` method, which validates if the provided date is not a future date.

    This test verifies:
    1. If the method does not raise any exception when the date is valid and is not in the future.
    2. If the method raises a `ValueError` when the date is a future date.
    """
    
    # Valid case: the date is valid (not in the future)
    valid_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
    Rates.validate_date(valid_date)  # Should not raise an error

    # Invalid case: the date is a future date
    future_date = datetime(3000, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Request datetime can not be higher than the current datetime"):
        Rates.validate_date(future_date)  # Should raise a ValueError

        
def test_validate_date_range():
    """
    Tests the `Rates.validate_date_range` method, which validates if the date range is valid (`date_from < date_to`).

    This test verifies:
    1. If the method does not raise any exception when the date range is valid.
    2. If the method raises a `ValueError` when `date_from` is greater than or equal to `date_to`.
    """
    
    # Valid case: `date_from` anterior a `date_to`
    date_from = datetime(2023, 12, 30, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, tzinfo=timezone.utc)
    Rates.validate_date_range(date_from, date_to)  # Should not raise an error

    # Invalid case: `date_from` posterior a `date_to`
    with pytest.raises(ValueError, match="Invalid date range"):
        Rates.validate_date_range(date_to, date_from)  # Should raise a ValueError
