import pytest
from datetime import datetime, timezone, timedelta
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlTradeRequest,
    ENUM_TRADE_REQUEST_ACTIONS,
    ENUM_ORDER_TYPE,
    ENUM_ORDER_TYPE_FILLING,
    ENUM_ORDER_TYPE_TIME,
)
from algo_trading.sources.MetaTrader5_source.utils.metatrader import (
    validate_mt5_ulong_size,
)


def test_valid_trade_request():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        magic=123456,
        volume=1.0,
        price=1.12345,
        sl=1.12000,
        tp=1.13000,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        type_filling=ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_FOK,
        type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC,
        deviation=10,
    )

    assert trade_request.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL
    assert trade_request.symbol == "EURUSD"
    assert trade_request.volume == 1.0
    assert trade_request.price == 1.12345
    assert trade_request.sl == 1.12000
    assert trade_request.tp == 1.13000


def test_missing_required_fields():
    with pytest.raises(ValueError, match="Missing required fields for action"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        )


def test_invalid_price():
    with pytest.raises(ValueError, match="Price must be greater than 0"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=-1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        )


def test_invalid_stop_loss():
    with pytest.raises(ValueError, match="Invalid stop loss"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            sl=1.12500,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        )


def test_valid_pending_order():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        stoplimit=1.12200,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
        type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert trade_request.type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT
    assert trade_request.stoplimit == 1.12200
    assert trade_request.expiration > datetime.now(timezone.utc)


def test_invalid_expiration():
    with pytest.raises(ValueError, match="Invalid expiration time: must be in the future"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
            expiration=datetime.now(timezone.utc) - timedelta(days=1),
        )


def test_prepare_request():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        sl=1.12000,
        tp=1.13000,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        type_filling=ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_FOK,
        deviation=10,
    )

    prepared_request = trade_request.prepare()

    assert prepared_request["action"] == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL
    assert prepared_request["symbol"] == "EURUSD"
    assert prepared_request["volume"] == 1.0
    assert prepared_request["price"] == 1.12345
    assert prepared_request["sl"] == 1.12000
    assert prepared_request["tp"] == 1.13000
  
    
def test_trade_action_modify():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_MODIFY,
        order=12345,
        price=1.12345,
        sl=1.12000,
        tp=1.13000,
        type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert trade_request.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_MODIFY
    assert trade_request.order == 12345
    assert trade_request.price == 1.12345
    assert trade_request.sl == 1.12000
    assert trade_request.tp == 1.13000
    assert trade_request.expiration > datetime.now(timezone.utc)
    
    
def test_trade_action_remove():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_REMOVE,
        order=54321,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
    )

    assert trade_request.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_REMOVE
    assert trade_request.order == 54321
    assert trade_request.type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT
    
    
def test_invalid_trade_action_remove_missing_fields():
    with pytest.raises(ValueError, match="Missing required fields for action"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_REMOVE,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
        )
    
        
def test_valid_close_by_action():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_CLOSE_BY,
        position=1111,
        position_by=2222,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_CLOSE_BY,
    )

    assert trade_request.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_CLOSE_BY
    assert trade_request.position == 1111
    assert trade_request.position_by == 2222
    assert trade_request.type == ENUM_ORDER_TYPE.ORDER_TYPE_CLOSE_BY
    
    
def test_invalid_sl_tp_combination():
    with pytest.raises(ValueError, match="Invalid stop loss"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            sl=1.121,
            tp=1.110,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
        )
    
        
def test_default_values():
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
    )

    assert trade_request.deviation == 5
    assert trade_request.sl == 0
    assert trade_request.tp == 0
    assert trade_request.magic == 0
    assert trade_request.comment == ""
    assert trade_request.expiration is None


# Testes para validate_mt5_ulong_size -------------------------------------------------------------
def test_validate_mt5_ulong_size_valid():
    # Test valid values within the allowed limit
    assert validate_mt5_ulong_size(0) is None  # Valid lower limit
    assert validate_mt5_ulong_size(2**63 - 1) is None  # Close to upper limit


def test_validate_mt5_ulong_size_negative():
    # Test negative values
    with pytest.raises(ValueError, match="The count must be equal or higher to zero"):
        validate_mt5_ulong_size(-1)


def test_validate_mt5_ulong_size_too_large():
    # Test values above the allowed limit for ulong
    with pytest.raises(ValueError, match="Python int too large to convert MQL5 long"):
        validate_mt5_ulong_size(2**64)


# Test for __validate_int_size in the context of MqlTradeRequest
def test_int_size_validation_with_valid_values():
    # Test creation of MqlTradeRequest with valid values
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        magic=123,  # Valid value
        order=0,  # Valid lower limit
        deviation=100,  # Valid value
    )
    assert trade_request.magic == 123
    assert trade_request.order == 0
    assert trade_request.deviation == 100


def test_int_size_validation_with_negative_values():
    # Test negative values
    with pytest.raises(ValueError, match="The count must be equal or higher to zero"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            magic=-123,  # Invalid value
        )


def test_int_size_validation_with_large_values():
    # Test large values
    with pytest.raises(ValueError, match="Python int too large to convert MQL5 long"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            magic=2**64,  # Invalid value
        )


def test_int_size_validation_default_values():
    # Test creation of MqlTradeRequest without explicit values for optional fields
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
    )
    assert trade_request.magic == 0  # Default value valid
    assert trade_request.order is None  # Default value None does not cause validation


def test_int_size_validation_boundary_values():
    # Test values close to the limits
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        magic=2**63 - 1,  # Limite válido
    )
    assert trade_request.magic == 2**63 - 1


def test_int_size_validation_zero_value():
    # Test zero values as valid
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        magic=0,  # Valid value
    )
    assert trade_request.magic == 0


def test_valid_expiration_for_order_time_specified():
    # Test valid with type time specified and expiration provided
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert trade_request.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    assert trade_request.expiration is not None


def test_valid_expiration_for_order_time_specified_day():
    # Test valid with ORDER_TIME_SPECIFIED_DAY and expiration provided
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert trade_request.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY
    assert trade_request.expiration is not None


def test_invalid_missing_expiration_for_order_time_specified():
    # Test invalid when ORDER_TIME_SPECIFIED is used without expiration
    with pytest.raises(ValueError, match="Expiration must be provided for specified order time types."):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED,
            expiration=None,
        )


def test_invalid_missing_expiration_for_order_time_specified_day():
    # Test invalid when ORDER_TIME_SPECIFIED_DAY is used without expiration
    with pytest.raises(ValueError, match="Expiration must be provided for specified order time types."):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY,
            expiration=None,
        )


def test_invalid_expiration_without_order_time_specified():
    # Test invalid when expiration is provided without specifying ORDER_TIME_SPECIFIED
    with pytest.raises(ValueError, match="OrderTypeTime must be specified when the expiration is set."):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC,  # It is not a specific type that requires expiration
        )


