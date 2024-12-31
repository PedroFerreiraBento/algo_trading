import pytest
from pydantic import ValidationError
from algo_trading.sources.MetaTrader5_source.models.metatrader import MqlTradeResult, ENUM_TRADE_RETCODE  # Substitua pelo caminho correto do módulo


class MockOrderSendResult:
    """Mock class for mt5.OrderSendResult to simulate trade result objects."""
    def __init__(self, retcode, deal, order, volume, price, bid, ask, comment, request_id, retcode_external):
        self.retcode = retcode
        self.deal = deal
        self.order = order
        self.volume = volume
        self.price = price
        self.bid = bid
        self.ask = ask
        self.comment = comment
        self.request_id = request_id
        self.retcode_external = retcode_external


def test_valid_trade_result():
    """Test creation of a valid trade result."""
    result = MqlTradeResult(
        retcode=ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE,
        deal=123456,
        order=654321,
        volume=1.0,
        price=1.2345,
        bid=1.2300,
        ask=1.2400,
        comment="Test comment",
        request_id=42,
        retcode_external=200
    )
    assert result.volume == 1.0
    assert result.price == 1.2345
    assert result.bid <= result.ask


def test_invalid_volume():
    """Test validation error for volume <= 0."""
    with pytest.raises(ValidationError, match="Volume must be greater than zero"):
        MqlTradeResult(
            retcode=ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE,
            deal=123456,
            order=654321,
            volume=0.0,  # Invalid volume
            price=1.2345,
            bid=1.2300,
            ask=1.2400,
            comment="Test comment",
            request_id=42,
            retcode_external=200
        )


def test_invalid_bid_ask_relationship():
    """Test validation error for bid > ask."""
    with pytest.raises(ValidationError, match="Bid price must not exceed ask price"):
        MqlTradeResult(
            retcode=ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE,
            deal=123456,
            order=654321,
            volume=1.0,
            price=1.2345,
            bid=1.2500,  # Invalid bid
            ask=1.2400,  # Invalid ask
            comment="Test comment",
            request_id=42,
            retcode_external=200
        )


def test_invalid_price_vs_bid():
    """Test validation error for price < bid."""
    with pytest.raises(ValidationError, match="Price must be greater than or equal to bid"):
        MqlTradeResult(
            retcode=ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE,
            deal=123456,
            order=654321,
            volume=1.0,
            price=1.2299,  # Invalid price
            bid=1.2300,
            ask=1.2400,
            comment="Test comment",
            request_id=42,
            retcode_external=200
        )


def test_parse_result_valid():
    """Test parse_result method with a valid mock object."""
    mock_result = MockOrderSendResult(
        retcode=ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE,
        deal=123456,
        order=654321,
        volume=1.0,
        price=1.2345,
        bid=1.2300,
        ask=1.2400,
        comment="Mock comment",
        request_id=42,
        retcode_external=200
    )
    parsed_result = MqlTradeResult.parse_result(mock_result)
    assert parsed_result.retcode == ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE
    assert parsed_result.deal == 123456
    assert parsed_result.order == 654321
    assert parsed_result.bid <= parsed_result.ask


def test_parse_result_invalid_attributes():
    """Test parse_result raises an error when required attributes are missing."""
    class IncompleteMockResult:
        def __init__(self):
            self.retcode = 0  # Missing other attributes

    mock_result = IncompleteMockResult()
    with pytest.raises(ValueError, match="Expected an mt5.OrderSendResult object with all required attributes"):
        MqlTradeResult.parse_result(mock_result)
