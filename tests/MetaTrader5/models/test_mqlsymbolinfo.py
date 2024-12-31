import pytest
from datetime import datetime, timezone
from algo_trading.sources.MetaTrader5_source.models.metatrader import MqlSymbolInfo
from algo_trading.sources.MetaTrader5_source.utils.exceptions import NotExpectedParseType

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

def test_parse_symbol(mock_symbol):
    """Test parsing a valid SymbolInfo object."""
    parsed = MqlSymbolInfo.parse_symbol(mock_symbol)
    assert parsed.time == datetime(2023, 1, 1, tzinfo=timezone.utc)  # Ajuste para UTC
    assert parsed.spread == 10
    assert parsed.ask == 1.2345
    assert parsed.bid == 1.2340
    assert parsed.volume_min == 0.01
    assert parsed.volume_max == 100.0
    assert parsed.currency_base == "USD"
    assert parsed.name == "EURUSD"
    
def test_invalid_symbol_type():
    """Test parsing an invalid type."""
    with pytest.raises(NotExpectedParseType):
        MqlSymbolInfo.parse_symbol("not a symbol")

def test_volume_validation(mock_symbol):
    """Test validation for volume_min and volume_max."""
    mock_symbol.volume_min = 10
    mock_symbol.volume_max = 5
    with pytest.raises(ValueError, match="volume_max must be greater than volume_min"):
        MqlSymbolInfo.parse_symbol(mock_symbol)

def test_bid_ask_validation(mock_symbol):
    """Test validation for bid <= ask."""
    mock_symbol.bid = 1.2350  # Higher than ask
    with pytest.raises(ValueError, match="bid must not exceed ask"):
        MqlSymbolInfo.parse_symbol(mock_symbol)

def test_volume_min_greater_than_zero(mock_symbol):
    """Test that volume_min must be greater than 0."""
    mock_symbol.volume_min = -0.01  # Valor inválido
    with pytest.raises(ValueError, match="Input should be greater than 0"):
        MqlSymbolInfo.parse_symbol(mock_symbol)
        
def test_optional_fields_with_defaults(mock_symbol):
    """Test that optional fields fall back to their default values."""
    mock_symbol.time = None
    mock_symbol.spread = None
    mock_symbol.ask = None
    mock_symbol.bid = None
    parsed = MqlSymbolInfo.parse_symbol(mock_symbol)
    assert parsed.time is None
    assert parsed.spread == 0  # Valor padrão
    assert parsed.ask == 0.0  # Valor padrão
    assert parsed.bid == 0.0  # Valor padrão

