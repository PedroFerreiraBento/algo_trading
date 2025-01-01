import pytest
from unittest.mock import patch, MagicMock
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
    ENUM_DEAL_ENTRY,
    ENUM_DEAL_TYPE,
    ENUM_DEAL_REASON,
    ENUM_ORDER_TYPE,
    ENUM_ORDER_TYPE_TIME,
    ENUM_ORDER_TYPE_FILLING,
    ENUM_ORDER_STATE,
    ENUM_ORDER_REASON,
    ENUM_POSITION_TYPE,
)
from datetime import datetime, timezone, timedelta


@patch("algo_trading.sources.MetaTrader5_source.models.metatrader.mt5")
def test_parse_account_success(mock_mt5):
    # Mock de mt5.AccountInfo
    mock_account_info = MagicMock()
    attributes = {
        "login": 123456,
        "trade_mode": ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_DEMO,
        "leverage": 100,
        "limit_orders": 200,
        "margin_so_mode": ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT,
        "trade_allowed": True,
        "trade_expert": True,
        "margin_mode": ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
        "currency_digits": 2,
        "fifo_close": False,
        "balance": 10000.0,
        "credit": 0.0,
        "profit": 0.0,
        "equity": 10000.0,
        "margin": 0.0,
        "margin_free": 10000.0,
        "margin_level": 0.0,
        "margin_so_call": 50.0,
        "margin_so_so": 30.0,
        "margin_initial": 0.0,
        "margin_maintenance": 0.0,
        "assets": 0.0,
        "liabilities": 0.0,
        "commission_blocked": 0.0,
        "name": "Demo Account",
        "server": "demo.server.com",
        "currency": "USD",
        "company": "MetaTrader Company",
    }
    for attr, value in attributes.items():
        setattr(mock_account_info, attr, value)

    mock_mt5.account_info.return_value = mock_account_info

    # Mock para histórico de deals
    initial_balance_time = datetime.now(tz=timezone.utc)
    initial_balance_time_ms = int(initial_balance_time.timestamp() * 1000)
    mock_deal = MagicMock()
    deal_attrs = {
        "symbol": "",
        "ticket": initial_balance_time_ms,
        "order": 0,
        "time": initial_balance_time.replace(microsecond=0),
        "time_msc": initial_balance_time_ms,
        "type": ENUM_DEAL_TYPE.DEAL_TYPE_BALANCE,
        "entry": ENUM_DEAL_ENTRY.DEAL_ENTRY_IN,
        "position_id": 0,
        "volume": 0,
        "price": 0,
        "commission": 0,
        "swap": 0,
        "profit": 10000.0,
        "fee": 0,
        "comment": "",
        "magic": 0,
        "reason": ENUM_DEAL_REASON.DEAL_REASON_EXPERT,
        "external_id": None,
    }
    for attr, value in deal_attrs.items():
        setattr(mock_deal, attr, value)

    mock_mt5.history_deals_get.return_value = [mock_deal]

    # Testa a criação de MqlAccountInfo
    account_info = MqlAccountInfo.parse_account(mock_account_info)

    # Verificações
    assert account_info.login == 123456
    assert account_info.balance == 10000.0
    assert len(account_info.history_deals) == 1
    assert account_info.history_deals[0].profit == 10000.0


@patch("algo_trading.sources.MetaTrader5_source.models.metatrader.mt5")
def test_parse_account_missing_attributes(mock_mt5):
    # Mock de mt5.AccountInfo com atributos faltando
    mock_account_info = MagicMock()
    delattr(mock_account_info, "login")  # Remove um atributo obrigatório

    # Verifica se um ValueError é levantado
    with pytest.raises(ValueError):
        MqlAccountInfo.parse_account(mock_account_info)


@patch("algo_trading.sources.MetaTrader5_source.models.metatrader.mt5")
def test_update_positions(mock_mt5):
    # Configuração do mock para positions_get
    mock_position = MagicMock()
    mock_position.ticket = 123456
    mock_position.time = int(datetime.now(tz=timezone.utc).timestamp())
    mock_position.time_msc = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    mock_position.time_update = int(datetime.now(tz=timezone.utc).timestamp())
    mock_position.time_update_msc = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    mock_position.type = ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    mock_position.magic = 42
    mock_position.identifier = 7891011
    mock_position.reason = 1  # Exemplo de motivo
    mock_position.volume = 1.0
    mock_position.price_open = 1.12345
    mock_position.sl = 1.12000
    mock_position.tp = 1.13000
    mock_position.price_current = 1.12400
    mock_position.swap = 0.5
    mock_position.profit = 10.0
    mock_position.symbol = "EURUSD"
    mock_position.comment = "Test position"
    mock_position.external_id = "EXTERNAL12345"

    mock_mt5.positions_get.return_value = [mock_position]

    # Criação do objeto MqlPositionInfo e atualização das posições
    account_info = MqlAccountInfo(
        login=123456,
        trade_mode=ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_DEMO,
        leverage=100,
        limit_orders=200,
        margin_so_mode=ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT,
        trade_allowed=True,
        trade_expert=True,
        margin_mode=ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
        currency_digits=2,
        fifo_close=False,
        balance=10000.0,
        credit=0.0,
        profit=0.0,
        equity=10000.0,
        margin=0.0,
        margin_free=10000.0,
        margin_level=0.0,
        margin_so_call=50.0,
        margin_so_so=30.0,
        margin_initial=0.0,
        margin_maintenance=0.0,
        assets=0.0,
        liabilities=0.0,
        commission_blocked=0.0,
        name="Demo Account",
        server="demo.server.com",
        currency="USD",
        company="MetaTrader Company",
    )

    account_info.update_positions()

    # Verifica se as posições foram atualizadas
    assert len(account_info.positions) == 1
    assert account_info.positions[0].symbol == "EURUSD"


@patch("algo_trading.sources.MetaTrader5_source.models.metatrader.mt5")
def test_update_orders(mock_mt5):
    # Configuração do mock para orders_get
    mock_order = MagicMock()
    mock_order.ticket = 123456
    mock_order.time_setup = int(datetime.now(tz=timezone.utc).timestamp())
    mock_order.time_setup_msc = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    mock_order.time_done = int((datetime.now(tz=timezone.utc) + timedelta(hours=1)).timestamp())
    mock_order.time_done_msc = int((datetime.now(tz=timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
    mock_order.time_expiration = int((datetime.now(tz=timezone.utc) + timedelta(days=1)).timestamp())
    mock_order.type = ENUM_ORDER_TYPE.ORDER_TYPE_BUY
    mock_order.type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC
    mock_order.type_filling = ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_IOC
    mock_order.state = ENUM_ORDER_STATE.ORDER_STATE_PLACED
    mock_order.magic = 42
    mock_order.position_id = 7891011
    mock_order.position_by_id = 1121314
    mock_order.reason = ENUM_ORDER_REASON.ORDER_REASON_EXPERT
    mock_order.volume_initial = 1.0
    mock_order.volume_current = 0.5
    mock_order.price_open = 1.12345
    mock_order.price_current = 1.12400
    mock_order.sl = 1.12000
    mock_order.tp = 1.13000
    mock_order.price_stoplimit = None
    mock_order.symbol = "USDJPY"
    mock_order.comment = "Test order"
    mock_order.external_id = "EXTERNAL12345"

    mock_mt5.orders_get.return_value = [mock_order]

    # Criação do objeto MqlTradeOrder e atualização das ordens
    account_info = MqlAccountInfo(
        login=123456,
        trade_mode=ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_DEMO,
        leverage=100,
        limit_orders=200,
        margin_so_mode=ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT,
        trade_allowed=True,
        trade_expert=True,
        margin_mode=ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
        currency_digits=2,
        fifo_close=False,
        balance=10000.0,
        credit=0.0,
        profit=0.0,
        equity=10000.0,
        margin=0.0,
        margin_free=10000.0,
        margin_level=0.0,
        margin_so_call=50.0,
        margin_so_so=30.0,
        margin_initial=0.0,
        margin_maintenance=0.0,
        assets=0.0,
        liabilities=0.0,
        commission_blocked=0.0,
        name="Demo Account",
        server="demo.server.com",
        currency="USD",
        company="MetaTrader Company",
    )

    account_info.update_orders()

    # Verifica se as ordens foram atualizadas
    assert len(account_info.orders) == 1
    assert account_info.orders[0].symbol == "USDJPY"
