# **Importações de Bibliotecas e Dependências Necessárias**
import pytest  # Framework de testes
from unittest.mock import patch  # Ferramenta de mock para simular chamadas de funções e métodos

# **Importação da classe Account (gerenciamento de contas do MetaTrader 5)**
from algo_trading.sources.MetaTrader5_source.account.account import Account

# **Importações de classes, enums e funções do MetaTrader 5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Modelo de informações da conta (ex.: saldo, alavancagem, lucro)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum para o modo de operação da conta (real/demo)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para o modo de stopout (percentual/valor fixo)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para o modo de cálculo de margem (hedge/redução)
)

# **Importação das funções de backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __process_account_after_candle_event,  # Função principal a ser testada
)

# **Fixture de Conta para os Testes**
@pytest.fixture
def account():
    """
    Fixture que cria uma instância de conta para os testes.
    Simula o login em uma conta ao vivo e reinicializa a conta em modo backtest.
    """
    account = Account()

    # Simula login na conta ao vivo antes do backtest
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

    return account

# **Teste: Verificação da Ordem de Execução das Funções Internas em `__process_account_after_candle_event`**
def test_process_account_after_candle_event_execution_order(account: Account):
    """
    Testa a ordem de execução das funções internas na função `__process_account_after_candle_event`.

    Objetivo:
    - Garantir que as funções internas são chamadas na ordem correta:
      1. `__backtest_pending_order_check_triggered`
      2. `__backtest_pending_order_check_expiration`
      3. `__backtest_position_check_stop_loss_reached`
      4. `__backtest_position_check_take_profit_reached`
    """
    account.login_backtest(balance=10000, leverage=100)  # Inicializa a conta com saldo e alavancagem
    operation_handler = account.backtest_account_data.operation

    # **Mock das funções internas**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_triggered", autospec=True) as mock_triggered, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_expiration", autospec=True) as mock_expiration, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_stop_loss_reached", autospec=True) as mock_stop_loss, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_take_profit_reached", autospec=True) as mock_take_profit:

        # **Evitar execução real**
        mock_triggered.side_effect = None
        mock_expiration.side_effect = None
        mock_stop_loss.side_effect = None
        mock_take_profit.side_effect = None

        # **Chamada da função principal**
        __process_account_after_candle_event(operation_handler)

        # **Verificação da ordem de execução das funções internas**
        calls = [
            mock_triggered.mock_calls[0],
            mock_expiration.mock_calls[0],
            mock_stop_loss.mock_calls[0],
            mock_take_profit.mock_calls[0],
        ]

        # **Confirmação se as funções foram chamadas na ordem correta**
        assert calls == sorted(calls, key=lambda x: x[1]), "As funções não foram chamadas na ordem esperada."


# **Teste: Verificação de Acionamento das Funções Internas**
def test_process_account_after_candle_event_functions_called(account: Account):
    """
    Testa se todas as funções internas são chamadas na função `__process_account_after_candle_event`.

    Objetivo:
    - Garantir que cada função interna é chamada pelo menos uma vez.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # **Mock das funções internas**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_triggered", autospec=True) as mock_triggered, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_expiration", autospec=True) as mock_expiration, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_stop_loss_reached", autospec=True) as mock_stop_loss, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_take_profit_reached", autospec=True) as mock_take_profit:

        # **Chamada da função principal**
        __process_account_after_candle_event(operation_handler)

        # **Verificação de chamadas**
        mock_triggered.assert_called_once(), "A função `__backtest_pending_order_check_triggered` não foi chamada."
        mock_expiration.assert_called_once(), "A função `__backtest_pending_order_check_expiration` não foi chamada."
        mock_stop_loss.assert_called_once(), "A função `__backtest_position_check_stop_loss_reached` não foi chamada."
        mock_take_profit.assert_called_once(), "A função `__backtest_position_check_take_profit_reached` não foi chamada."


