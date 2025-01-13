# **Importações de bibliotecas e dependências necessárias**
import pytest  # Framework de testes
from unittest.mock import (
    patch,
)  # Ferramenta de mock para simular chamadas de funções e métodos

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
    __process_account_update_data,  # Função de atualização dos dados da conta no backtest
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


# **Teste: Verificação da Ordem de Execução das Funções Internas**
def test_process_update_data_execution_order(account: Account):
    """
    Testa a ordem de execução das funções internas na função `__process_update_data`.

    Objetivo:
    - Garantir que as funções internas são chamadas na ordem correta:
      1. `__backtest_position_apply_swap_to_positions`
      2. `__backtest_position_update_price_and_profit`
      3. `__backtest_account_update_margin`
      4. `__backtest_account_check_margin_call`
      5. `__backtest_account_process_stop_out`
    """
    account.login_backtest(
        balance=10000, leverage=100
    )  # Inicializa a conta com saldo e alavancagem
    operation_handler = account.backtest_account_data.operation

    # **Mock das funções internas**
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_apply_swap_to_positions",
        autospec=True,
    ) as mock_swap, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_update_price_and_profit",
        autospec=True,
    ) as mock_update_price, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_account_update_margin",
        autospec=True,
    ) as mock_update_margin, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_account_check_margin_call",
        autospec=True,
    ) as mock_check_margin_call, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_account_process_stop_out",
        autospec=True,
    ) as mock_process_stop_out:

        # **Evitar execução real**
        mock_swap.side_effect = None
        mock_update_price.side_effect = None
        mock_update_margin.side_effect = None
        mock_check_margin_call.side_effect = None
        mock_process_stop_out.side_effect = None

        # **Chamada da função principal**
        __process_account_update_data(operation_handler)

        # **Verificação da ordem de execução das funções internas**
        calls = [
            mock_swap.mock_calls[0],
            mock_update_price.mock_calls[0],
            mock_update_margin.mock_calls[0],
            mock_check_margin_call.mock_calls[0],
            mock_process_stop_out.mock_calls[0],
        ]

        # **Confirmação se as funções foram chamadas na ordem correta**
        assert calls == sorted(
            calls, key=lambda x: x[1]
        ), "As funções não foram chamadas na ordem esperada."
