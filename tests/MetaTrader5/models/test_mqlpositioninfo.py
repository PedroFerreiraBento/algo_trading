import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from algo_trading.sources.MetaTrader5_source.models.metatrader import MqlPositionInfo, validate_prices, ENUM_POSITION_TYPE, ENUM_ORDER_TYPE


class MockTradePosition:
    """Mock class for simulating mt5.TradePosition objects."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def test_valid_position_creation():
    """Test creating a valid MqlPositionInfo instance."""
    position = MqlPositionInfo(
        ticket=12345,
        time=datetime.now(timezone.utc),  # Corrigido
        time_msc=datetime.now(timezone.utc),  # Corrigido
        time_update=datetime.now(timezone.utc),  # Corrigido
        time_update_msc=datetime.now(timezone.utc),  # Corrigido
        type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        magic=42,
        identifier=999,
        reason=0,
        volume=1.0,
        price_open=1.2345,
        sl=1.2000,
        tp=1.2500,
        price_current=1.2400,
        swap=0.0,
        profit=100.0,
        symbol="EURUSD",
        comment="Test position",
        external_id="external_12345",
    )
    assert position.ticket == 12345
    assert position.volume > 0
    assert position.sl < position.tp
    

def test_invalid_volume():
    """Test validation error for volume <= 0."""
    with pytest.raises(ValidationError, match="Volume must be greater than zero"):
        MqlPositionInfo(
            ticket=12345,
            time=datetime.now(timezone.utc),
            time_msc=datetime.now(timezone.utc),
            time_update=datetime.now(timezone.utc),
            time_update_msc=datetime.now(timezone.utc),
            type=0,
            volume=0.0,  # Invalid
            price_open=1.2345,
            sl=1.2000,
            tp=1.2500,
            price_current=1.2400,
            swap=0.0,
            profit=100.0,
            identifier=999,
            reason=0,
            symbol="EURUSD",
        )


def test_invalid_sl_tp():
    """Test invalid Stop Loss and Take Profit relationship."""
    with pytest.raises(ValueError, match="Invalid stop loss"):
        validate_prices(price=1.2400, order_type=0, sl=1.2500, tp=1.2000)  # SL > price

    with pytest.raises(ValueError, match="Invalid take profit"):
        validate_prices(price=1.2400, order_type=0, sl=1.2000, tp=1.2300)  # TP < price


def test_invalid_stop_limit():
    """Test invalid stop limit position."""
    with pytest.raises(ValueError, match="Invalid stop limit"):
        validate_prices(price=1.2400, order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT, stoplimit=1.2500)  # Invalid for sell stop limit


def test_parse_position_valid():
    """Test parsing a valid mock TradePosition object."""
    mock = MockTradePosition(
        ticket=12345,
        time=int(datetime.now(timezone.utc).timestamp()),
        time_msc=int(datetime.now(timezone.utc).timestamp() * 1000),
        time_update=int(datetime.now(timezone.utc).timestamp()),
        time_update_msc=int(datetime.now(timezone.utc).timestamp() * 1000),
        type=0,
        magic=42,
        identifier=999,
        reason=0,
        volume=1.0,
        price_open=1.2345,
        sl=1.2000,
        tp=1.2500,
        price_current=1.2400,
        swap=0.0,
        profit=100.0,
        symbol="EURUSD",
        comment="Mock position",
        external_id="external_12345",
    )
    position = MqlPositionInfo.parse_position(mock)
    assert position.ticket == 12345
    assert position.price_open == 1.2345
    assert position.symbol == "EURUSD"


def test_parse_position_missing_attributes():
    """Test parsing fails with missing attributes."""
    mock = MockTradePosition(ticket=12345)  # Missing required attributes
    with pytest.raises(ValueError, match="Expected an mt5.TradePosition object with all required attributes"):
        MqlPositionInfo.parse_position(mock)


def test_update_method():
    """Test updating attributes using the update method."""
    position = MqlPositionInfo(
        ticket=12345,
        time=datetime.now(timezone.utc),
        time_msc=datetime.now(timezone.utc),
        time_update=datetime.now(timezone.utc),
        time_update_msc=datetime.now(timezone.utc),
        type=0,
        magic=42,
        identifier=999,
        reason=0,
        volume=1.0,
        price_open=1.2345,
        sl=1.2000,
        tp=1.2500,
        price_current=1.2400,
        swap=0.0,
        profit=100.0,
        symbol="EURUSD",
        comment="Test position",
        external_id="external_12345",
    )
    position.update(price_current=1.2450, profit=150.0)
    assert position.price_current == 1.2450
    assert position.profit == 150.0
