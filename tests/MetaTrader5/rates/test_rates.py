import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from algo_trading.sources.MetaTrader5_source.rates import Rates
from algo_trading.sources.MetaTrader5_source.models.metatrader import MqlSymbolInfo, MqlTick, ENUM_TIMEFRAME, ENUM_COPY_TICKS
import pandas as pd
import numpy as np

# Test Symbols ------------------------------------------------------------------------------------
@pytest.fixture
def mock_symbol():
    """Mock a SymbolInfo-like object."""
    class MockSymbolInfo:
        def __init__(self):
            self.time = 1672531200  # 2023-01-01 00:00:00 UTC
            self.spread = 10
            self.digits = 5
            self.ask = 1.2345
            self.bid = 1.2340
            self.volume_min = 0.01
            self.volume_max = 100.0
            self.volume_step = 0.01
            self.trade_tick_size = 0.0001
            self.trade_contract_size = 100000
            self.trade_tick_value_profit = 1.0
            self.trade_tick_value_loss = 1.0
            self.currency_base = "USD"
            self.currency_profit = "EUR"
            self.description = "Euro vs US Dollar"
            self.name = "EURUSD"

    return MockSymbolInfo()

@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_symbols_names(mock_mt5):
    # Mock para symbols_get
    mock_symbol = MagicMock()
    mock_symbol.name = "EURUSD"
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True

    # Executa o método
    symbols = Rates.get_symbols_names()

    # Verificações
    mock_mt5.symbols_get.assert_called_once()
    assert symbols == ["EURUSD"]


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_symbol_data(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.symbol_info.return_value = mock_symbol
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True

    # Executa o método
    symbol_data = Rates.get_symbol_data("EURUSD")

    # Verificações
    mock_mt5.symbol_info.assert_called_once_with("EURUSD")
    assert symbol_data.name == "EURUSD"
    assert symbol_data.spread == 10


# Test Candles ------------------------------------------------------------------------------------
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_last_n_candles(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)
    
    # Mock para copy_rates_from
    now = datetime.now(timezone.utc)
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),
            (int((now - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Executa o método
    with patch("algo_trading.sources.MetaTrader5_source.rates.rates.datetime") as mock_datetime:
        # Configura o mock para retornar a data específica
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        candles = Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=2)

    # Verificações
    mock_mt5.copy_rates_from.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, now, 2)
    assert isinstance(candles, pd.DataFrame)
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"]
    assert candles.shape[0] == 2


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_candles_before(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)
    
    # Mock para copy_rates_from
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(date_to.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),
            (int((date_to - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Executa o método
    candles = Rates.get_candles_before(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, date_to=date_to, n_candles=2)

    # Verificações
    mock_mt5.copy_rates_from.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, date_to, 2)
    assert isinstance(candles, pd.DataFrame)
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"]
    assert candles.shape[0] == 2
    
    
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_candles_range(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True
    
    # Mock para copy_rates_range
    date_from = datetime(2023, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    mock_mt5.copy_rates_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1220, 1.1230, 1.1210, 1.1225, 200),
            (int(date_to.timestamp()), 1.1230, 1.1240, 1.1220, 1.1235, 300),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Executa o método
    candles = Rates.get_candles_range(symbol="EURUSD", date_from=date_from, date_to=date_to, timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1)

    # Verificações
    mock_mt5.copy_rates_range.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, date_from, date_to)
    assert isinstance(candles, pd.DataFrame)
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"]
    assert candles.shape[0] == 2
    
    
# Test Ticks ------------------------------------------------------------------------------------00
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_last_n_ticks(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True

    # Mock para copy_ticks_from
    now = datetime.now(timezone.utc)
    mock_mt5.copy_ticks_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1235, 1.1236, 1, 64, int(now.timestamp() * 1000)),
            (int((now - timedelta(seconds=1)).timestamp()), 1.1230, 1.1231, 1.1232, 1, 32, int((now - timedelta(seconds=1)).timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"), 
            ("volume", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Executa o método
    with patch("algo_trading.sources.MetaTrader5_source.rates.rates.datetime") as mock_datetime:
        # Configura o mock para retornar a data específica
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        ticks = Rates.get_last_n_ticks(symbol="EURUSD", n_ticks=2)

    # Verificações
    mock_mt5.copy_ticks_from.assert_called_once_with("EURUSD", now, 2, ENUM_COPY_TICKS.COPY_TICKS_ALL)
    assert isinstance(ticks, pd.DataFrame)
    assert list(ticks.columns) == ["time", "bid", "ask", "time_msc"]
    assert ticks.shape[0] == 2

    # Verifica os valores do DataFrame
    assert ticks.iloc[0]["bid"] == 1.1234
    assert ticks.iloc[0]["ask"] == 1.1235
    assert ticks.iloc[0]["time"] == pd.Timestamp(int(now.timestamp()), unit="s", tz="UTC")
    
    # Ajusta a verificação para considerar milissegundos
    expected_time_msc = pd.Timestamp(int(now.timestamp() * 1000), unit="ms", tz="UTC")
    assert ticks.iloc[0]["time_msc"] == expected_time_msc


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_specific_tick(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True

    # Mock para copy_ticks_from
    date_from = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    mock_mt5.copy_ticks_from.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1234, 1.1235, 1.1236, 1, 1, 64, int(date_from.timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"), 
            ("volume", "i8"), ("volume_real", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Executa o método
    tick = Rates.get_specific_tick(symbol="EURUSD", date_from=date_from)

    # Verificações
    mock_mt5.copy_ticks_from.assert_called_once_with("EURUSD", date_from, 1, ENUM_COPY_TICKS.COPY_TICKS_ALL)
    assert isinstance(tick, MqlTick)

    # Verifica os valores do MqlTick
    assert tick.time == date_from
    assert tick.bid == 1.1234
    assert tick.ask == 1.1235
    assert tick.last == 1.1236
    assert tick.volume == 1
    assert tick.flags == 64
    assert tick.time_msc == date_from


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_ticks_range(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True

    # Mock para copy_ticks_range
    date_from = datetime(2023, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    mock_mt5.copy_ticks_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1234, 1.1235, 1.1236, 1, 64, int(date_from.timestamp() * 1000)),
            (int(date_to.timestamp()), 1.1230, 1.1231, 1.1232, 1, 32, int(date_to.timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"), 
            ("volume", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Executa o método
    ticks = Rates.get_ticks_range(symbol="EURUSD", date_from=date_from, date_to=date_to)

    # Verificações
    mock_mt5.copy_ticks_range.assert_called_once_with("EURUSD", date_from, date_to, ENUM_COPY_TICKS.COPY_TICKS_ALL)
    assert isinstance(ticks, pd.DataFrame)
    assert list(ticks.columns) == ["time", "bid", "ask", "time_msc"]
    assert ticks.shape[0] == 2

    # Verifica os valores do DataFrame
    assert ticks.iloc[0]["bid"] == 1.1234
    assert ticks.iloc[0]["ask"] == 1.1235
    assert ticks.iloc[0]["time"] == pd.Timestamp(int(date_from.timestamp()), unit="s", tz="UTC")
    assert ticks.iloc[0]["time_msc"] == pd.Timestamp(int(date_from.timestamp() * 1000), unit="ms", tz="UTC")

    
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_validate_count_candles(mock_mt5):
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)

    # Validação bem-sucedida
    Rates.validate_count_candles(9999)  # Não deve lançar erro

    # Exceção para valor inválido
    with pytest.raises(ValueError, match="The number of candles cannot be higher than terminal chart max bars"):
        Rates.validate_count_candles(10000)
        

@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_validate_symbol(mock_mt5, mock_symbol):
    # Mock para symbol_info
    mock_mt5.symbols_get.return_value = (mock_symbol,)
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = True

    # Validação bem-sucedida
    Rates.validate_symbol("EURUSD")

    # Exceção para símbolo inválido
    with pytest.raises(ValueError, match="The selected symbol is not in the symbols list"):
        Rates.validate_symbol("INVALID_SYMBOL")


def test_validate_request_result():
    # Validação bem-sucedida
    valid_result = np.array([1, 2, 3])
    Rates.validate_request_result(valid_result)  # Não deve lançar erro

    # Exceção para resultado None
    with pytest.raises(TypeError, match="Request error, please check the request format"):
        Rates.validate_request_result(None)

    # Exceção para resultado vazio
    with pytest.raises(ValueError, match="No data returned"):
        Rates.validate_request_result(np.array([]))

    
def test_validate_date():
    # Data válida
    valid_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
    Rates.validate_date(valid_date)  # Não deve lançar erro

    # Exceção para data futura
    future_date = datetime(3000, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Request datetime can not be higher than the current datetime"):
        Rates.validate_date(future_date)
        
        
def test_validate_date_range():
    # Range válido
    date_from = datetime(2023, 12, 30, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, tzinfo=timezone.utc)
    Rates.validate_date_range(date_from, date_to)  # Não deve lançar erro

    # Exceção para range inválido
    with pytest.raises(ValueError, match="Invalid date range"):
        Rates.validate_date_range(date_to, date_from)

