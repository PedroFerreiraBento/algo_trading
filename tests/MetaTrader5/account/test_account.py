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
)
from algo_trading.sources.MetaTrader5_source.account.account import Account
from datetime import datetime, timezone


@pytest.fixture
def account():
    return Account()


@patch("algo_trading.sources.MetaTrader5_source.account.account.mt5")
def test_login_live_success(mock_mt5, account):
    # Mock para o método mt5.initialize
    mock_mt5.initialize.return_value = True

    # Criar um mock de mt5.AccountInfo com todos os atributos necessários
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

    # Configurar o retorno de mt5.account_info para o mock criado
    mock_mt5.account_info.return_value = mock_account_info

    # Executar o método login_live
    account_data = account.login_live(
        login=123456, server="demo.server.com", password="password123"
    )

    # Verificações
    mock_mt5.initialize.assert_called_once_with(
        "",
        login=123456,
        server="demo.server.com",
        password="password123",
        timeout=60_000,
        portable=False,
    )
    assert account_data is not None
    assert isinstance(account.live_account_data, MqlAccountInfo)
    assert account.live_account_data.login == 123456


@patch("algo_trading.sources.MetaTrader5_source.account.account.mt5")
def test_logout_success(mock_mt5, account):
    # Mock do método mt5.shutdown
    mock_mt5.shutdown.return_value = True

    # Testa o logout
    account.logout()

    # Verifica se o método shutdown foi chamado
    mock_mt5.shutdown.assert_called_once()


@patch("algo_trading.sources.MetaTrader5_source.account.account.mt5")
def test_update_live_account_data_success(mock_mt5, account):
    # Mock para mt5.account_info
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

    # Atualiza os dados da conta ao vivo
    account.update_live_account_data()

    # Verificações
    mock_mt5.account_info.assert_called_once()
    assert account.live_account_data is not None
    assert account.live_account_data.login == 123456


def test_login_backtest_success(account):
    # Simula login em conta ao vivo antes do backtest
    account.live_account_data = MqlAccountInfo(
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

    # Testa criação de conta de backtest
    backtest_data = account.login_backtest(balance=5000, leverage=100)

    # Verificações
    assert backtest_data.is_backtest_account is True
    assert backtest_data.balance == 5000
    assert backtest_data.currency == "USD"


def test_get_current_account_data(account):
    # Configura conta ao vivo
    live_data = MqlAccountInfo(
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
    account.live_account_data = live_data

    # Recupera dados ao vivo
    current_data = account.get_current_account_data()
    assert current_data == live_data

    # Configura conta de backtest
    backtest_data = account.login_backtest(balance=5000, leverage=100)
    current_data = account.get_current_account_data(backtest=True)
    assert current_data == backtest_data


@patch("algo_trading.sources.MetaTrader5_source.account.account.mt5")
def test_login_live_failure(mock_mt5, account):
    # Simula falha no método mt5.initialize
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (1, "Error Message")

    # Verifica se a exceção é levantada corretamente
    with pytest.raises(ConnectionError):
        account.login_live(
            login=123456, server="demo.server.com", password="wrong_password"
        )

    # Verifica se o shutdown foi chamado
    mock_mt5.shutdown.assert_called_once()


@patch("algo_trading.sources.MetaTrader5_source.account.account.mt5")
def test_update_live_account_data_failure(mock_mt5, account):
    # Simula falha no retorno de account_info
    mock_mt5.account_info.return_value = None

    # Verifica se a exceção é levantada corretamente
    with pytest.raises(ConnectionError):
        account.update_live_account_data()

    # Verifica se account_info foi chamado
    mock_mt5.account_info.assert_called_once()


def test_login_backtest_without_live_account(account):
    # Não configura live_account_data
    account.live_account_data = None

    # Verifica se a exceção é levantada corretamente
    with pytest.raises(PermissionError):
        account.login_backtest(balance=5000, leverage=100)


@patch("algo_trading.sources.MetaTrader5_source.account.account.mt5.history_deals_get")
def test_parse_account(mock_history_deals_get):
    # Configura o mock para mt5.history_deals_get com um dicionário contendo os parâmetros fornecidos
    initial_balance_time = datetime.now(tz=timezone.utc)
    initial_balance_time_ms = int(initial_balance_time.timestamp() * 1000)

    mock_initial_deal = MagicMock()
    attributes = {
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
        "profit": 10000.0,  # Mesmo valor do balance do teste
        "fee": 0,
        "comment": "",
        "magic": 0,
        "reason": ENUM_DEAL_REASON.DEAL_REASON_EXPERT,
        "external_id": None,
    }

    for attr, value in attributes.items():
        setattr(mock_initial_deal, attr, value)

    mock_history_deals_get.return_value = [mock_initial_deal]

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

    # Testa a criação de MqlAccountInfo
    account_info = MqlAccountInfo.parse_account(mock_account_info)

    # Verificações
    assert account_info.login == 123456
    assert account_info.balance == 10000.0
    assert len(account_info.history_deals) == 1
    assert account_info.history_deals[0].profit == 10000.0  # Verifica o valor do profit
