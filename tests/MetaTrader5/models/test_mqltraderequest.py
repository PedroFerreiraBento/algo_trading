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
    # Testar valores válidos dentro do limite permitido
    assert validate_mt5_ulong_size(0) is None  # Limite inferior válido
    assert validate_mt5_ulong_size(2**63 - 1) is None  # Próximo ao limite superior


def test_validate_mt5_ulong_size_negative():
    # Testar valores negativos
    with pytest.raises(ValueError, match="The count must be equal or higher to zero"):
        validate_mt5_ulong_size(-1)


def test_validate_mt5_ulong_size_too_large():
    # Testar valores acima do limite permitido para ulong
    with pytest.raises(ValueError, match="Python int too large to convert MQL5 long"):
        validate_mt5_ulong_size(2**64)


# Testes para __validate_int_size no contexto de MqlTradeRequest
def test_int_size_validation_with_valid_values():
    # Testar criação de MqlTradeRequest com valores válidos
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        magic=123,  # Valor válido
        order=0,  # Limite inferior válido
        deviation=100,  # Valor válido
    )
    assert trade_request.magic == 123
    assert trade_request.order == 0
    assert trade_request.deviation == 100


def test_int_size_validation_with_negative_values():
    # Testar valores negativos
    with pytest.raises(ValueError, match="The count must be equal or higher to zero"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            magic=-123,  # Valor inválido
        )


def test_int_size_validation_with_large_values():
    # Testar valores muito grandes
    with pytest.raises(ValueError, match="Python int too large to convert MQL5 long"):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            magic=2**64,  # Valor muito grande
        )


def test_int_size_validation_default_values():
    # Testar criação de MqlTradeRequest sem valores explícitos para campos opcionais
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
    )
    assert trade_request.magic == 0  # Valor padrão válido
    assert trade_request.order is None  # Valor padrão None não causa validação


def test_int_size_validation_boundary_values():
    # Testar valores próximos aos limites
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
    # Testar valores zero como válidos
    trade_request = MqlTradeRequest(
        action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=1.0,
        price=1.12345,
        type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        magic=0,  # Valor válido
    )
    assert trade_request.magic == 0


def test_valid_expiration_for_order_time_specified():
    # Teste válido com tipo de tempo específico e expiration fornecido
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
    # Teste válido com ORDER_TIME_SPECIFIED_DAY e expiration fornecido
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
    # Teste inválido quando ORDER_TIME_SPECIFIED é usado sem expiration
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
    # Teste inválido quando ORDER_TIME_SPECIFIED_DAY é usado sem expiration
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
    # Teste inválido quando expiration é fornecido sem especificar ORDER_TIME_SPECIFIED
    with pytest.raises(ValueError, match="OrderTypeTime must be specified when the expiration is set."):
        MqlTradeRequest(
            action=ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=1.0,
            price=1.12345,
            type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            type_time=ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC,  # Não é um tipo específico que exige expiration
        )


