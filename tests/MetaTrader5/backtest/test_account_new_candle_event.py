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
    __process_account_new_candle_event,  # Função principal a ser testada
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


# **Teste 1: Verificação da Ordem de Execução das Funções Internas**
def test_process_account_new_candle_event_execution_order(account: Account):
    """
    Testa a ordem de execução das funções internas na função `__process_account_new_candle_event`.

    Objetivo:
    - Garantir que as funções internas são chamadas na ordem correta:
      1. `__process_account_after_candle_event`
      2. `__process_account_update_data`
    """
    account.login_backtest(balance=10000, leverage=100)  # Inicializa a conta com saldo e alavancagem
    operation_handler = account.backtest_account_data.operation

    # **Mock das funções internas**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_after_candle_event", autospec=True) as mock_after_candle_event, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_update_data", autospec=True) as mock_update_data:

        # **Evitar execução real**
        mock_after_candle_event.side_effect = None
        mock_update_data.side_effect = None

        # **Chamada da função principal**
        __process_account_new_candle_event(operation_handler)

        # **Verificação da ordem de execução das funções internas**
        calls = [
            mock_after_candle_event.mock_calls[0],
            mock_update_data.mock_calls[0],
        ]

        # **Confirmação se as funções foram chamadas na ordem correta**
        assert calls == sorted(calls, key=lambda x: x[1]), "As funções não foram chamadas na ordem esperada."


# **Teste 2: Verificação de Chamadas das Funções Internas**
def test_process_account_new_candle_event_functions_called(account: Account):
    """
    Testa se todas as funções internas são chamadas na função `__process_account_new_candle_event`.

    Objetivo:
    - Garantir que cada função interna é chamada pelo menos uma vez.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # **Mock das funções internas**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_after_candle_event", autospec=True) as mock_after_candle_event, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_update_data", autospec=True) as mock_update_data:

        # **Chamada da função principal**
        __process_account_new_candle_event(operation_handler)

        # **Verificação de chamadas**
        mock_after_candle_event.assert_called_once(), "A função `__process_account_after_candle_event` não foi chamada."
        mock_update_data.assert_called_once(), "A função `__process_account_update_data` não foi chamada."

