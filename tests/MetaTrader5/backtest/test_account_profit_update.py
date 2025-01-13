# **Importações de bibliotecas e dependências necessárias**

# Importações de bibliotecas padrão
import pytest  # Framework para testes
from datetime import datetime, timezone  # Manipulação de datas e fusos horários
import pandas as pd  # Biblioteca para manipulação de dados

# **Importações de classes, enums e funções do MetaTrader 5**

# Modelos e enums para operações no MetaTrader 5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Modelo de informações de conta
    ENUM_ORDER_TYPE_MARKET,  # Enum para tipos de ordens de mercado (compra/venda)
    ENUM_SYMBOL_CALC_MODE,  # Enum para modos de cálculo de símbolo (Forex, CFDs, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum para modos de negociação da conta
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para modos de stop-out da conta
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para modos de margem da conta
    ENUM_SYMBOL_SWAP_MODE,  # Enum para modos de cálculo de swap
)

# Funções de backtest do MetaTrader 5
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_update_price_and_profit,  # Função para atualizar preço e lucro das posições
    __backtest_position_open,  # Função para abrir posições de mercado durante o backtest
    __backtest_position_apply_swap_to_positions,  # Função para aplicar swaps às posições abertas
)

# Classe de gerenciamento de conta
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe `Account` para login e gerenciamento de dados da conta


# **Fixture para configuração inicial da conta**
@pytest.fixture
def account():
    """
    Cria uma instância de conta com dados simulados para testes.
    """
    account = Account()
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


# **Teste 1: Atualização de preço e lucro para uma posição de compra (BUY)**
def test_update_buy_position_price_and_profit(account: Account):
    """
    Testa a atualização do preço atual e cálculo de lucro para uma posição de compra (BUY).

    Objetivo:
    - Verificar se o preço de abertura da posição é calculado corretamente considerando o spread.
    - Validar se o preço atual da posição é atualizado com base no último preço de fechamento.
    - Garantir que o lucro é calculado de forma precisa com base na diferença de preços.
    """
    # Reinicializa a conta no backtest com saldo inicial e alavancagem configurados
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"
    contract_size = 100_000  # 1 lote = 100.000 unidades
    tick_size = 0.00001  # 1 pip = 0.00001

    # Define os dados do novo símbolo como um dicionário
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_candle_price = 1.14  # Preço de fechamento do candle
    last_candle = {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_candle_price}

    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(last_candle, name=last_candle_time),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Último candle de preço**
    open_position_price = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )

    # **Abertura da posição de compra (BUY)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )

    # **Atualização de preço e lucro da posição**
    __backtest_position_update_price_and_profit(operation_handler)
    positions = account.backtest_account_data.positions

    # **Verificação do preço de abertura e do preço atual**
    assert (
        positions[0].price_open == open_position_price
    ), "O preço de abertura da posição não bate com o esperado."
    assert (
        positions[0].price_current == close_candle_price
    ), "O preço atual não foi atualizado corretamente."

    # **Verificação do lucro esperado**
    expected_profit = round(
        (close_candle_price - open_position_price) * contract_size, 2
    )
    assert (
        positions[0].profit == expected_profit
    ), f"Lucro incorreto. Esperado: {expected_profit}, obtido: {positions[0].profit}"


# **Teste 2: Atualização de preço e prejuízo para uma posição de venda (SELL)**
def test_update_sell_position_price_and_profit(account: Account):
    """
    Testa a atualização do preço atual e cálculo de prejuízo para uma posição de venda (SELL).

    Objetivo:
    - Verificar se o preço de abertura da posição é calculado corretamente considerando o spread.
    - Validar se o preço atual da posição é atualizado com base no último preço de fechamento.
    - Garantir que o lucro/prejuízo é calculado de forma precisa com base na diferença de preços.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    symbol = "EURUSD"
    contract_size = 100_000
    tick_size = 0.00001
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_candle_price = 1.14
    last_candle = {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_candle_price}

    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(last_candle, name=last_candle_time),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    position_price_current = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )

    # **Abertura da posição de venda (SELL)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=1,
        comment="Position 2 (Sell)",
    )

    # **Atualização de preço atual e prejuízo**
    __backtest_position_update_price_and_profit(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].price_open == close_candle_price
    ), "O preço de abertura da posição não bate com o esperado."
    assert (
        positions[0].price_current == position_price_current
    ), "O preço atual não foi atualizado corretamente."

    expected_profit = round(
        (position_price_current - close_candle_price) * contract_size * -1, 2
    )
    assert (
        positions[0].profit == expected_profit
    ), f"Prejuízo incorreto. Esperado: {expected_profit}, obtido: {positions[0].profit}"


# **Teste 3: Lucro zero se o preço não mudou**
def test_update_position_no_price_change(account: Account):
    """
    Testa a atualização do preço atual e cálculo de lucro/prejuízo com preço inalterado.

    Objetivo:
    - Garantir que o preço de abertura da posição de compra seja calculado corretamente considerando o spread.
    - Manter o mesmo preço de fechamento no `last_candle` após a abertura da posição.
    - Verificar que o lucro permanece zero quando o preço não muda.
    """
    # **Reinicializa a conta no backtest com saldo inicial e alavancagem configurados**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"  # Par de moedas
    contract_size = 100_000  # 1 lote = 100.000 unidades da moeda base
    tick_size = 0.00001  # Precisão do preço (1 pip = 0.00001)

    # **Último candle antes de abrir a posição**
    last_candle_time_before = datetime(
        2025, 1, 10, 12, 0, tzinfo=timezone.utc
    )  # Horário do último candle antes da abertura
    close_candle_price = 1.12  # Preço de fechamento
    last_candle_before = {
        "open": close_candle_price,
        "high": 1.15,
        "low": 1.11,
        "close": close_candle_price,
    }

    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(last_candle_before, name=last_candle_time_before),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Cálculo do preço de abertura ajustado pelo spread**
    open_position_price = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )

    # **Abertura da posição de compra (`BUY`)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Tipo de ordem: compra
        volume=1,  # Volume de 1 lote
        comment="Position 1 (Buy)",  # Comentário identificando a posição
    )

    # **Último candle após a abertura da posição (mesmo preço de fechamento)**
    last_candle_time_after = datetime(
        2025, 1, 10, 12, 5, tzinfo=timezone.utc
    )  # Horário posterior à abertura
    last_candle_after = {
        "open": close_candle_price,
        "high": 1.15,
        "low": 1.11,
        "close": open_position_price,
    }

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle_after, name=last_candle_time_after
    )

    # **Atualização de preço atual e cálculo do lucro**
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Atualiza o preço atual e lucro da posição
    positions = account.backtest_account_data.positions  # Obtém as posições abertas

    # **Verificação do preço de abertura e do preço atual**
    assert (
        positions[0].price_open == open_position_price
    ), f"O preço de abertura da posição está incorreto. Esperado: {open_position_price}, obtido: {positions[0].price_open}"
    assert (
        positions[0].price_current == open_position_price
    ), f"O preço atual não foi atualizado corretamente. Esperado: {open_position_price}, obtido: {positions[0].price_current}"

    # **Verificação do lucro esperado**
    expected_profit = 0.0  # O lucro esperado deve ser zero porque o preço não mudou
    assert (
        positions[0].profit == expected_profit
    ), f"Lucro incorreto. Esperado: {expected_profit}, obtido: {positions[0].profit}"


# **Teste 4: Lucro negativo para uma posição de compra (`BUY`) com `swap` aplicado**
def test_account_profit_with_buy_position_and_swap(account: Account):
    """
    Testa o cálculo do `profit` total da conta considerando uma posição de compra (`BUY`) com lucro negativo
    devido ao `swap` e aplicação do spread.

    Objetivo:
    - Verificar se o preço de abertura da posição é calculado corretamente considerando o spread.
    - Validar se o `swap` é aplicado corretamente após o horário de fechamento (22:00 UTC).
    - Garantir que o lucro total da conta seja atualizado corretamente com o `swap`.
    """
    account.login_backtest(
        balance=10000, leverage=100
    )  # Reinicializa a conta com saldo inicial e alavancagem configurados
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulação de spread de 4 pips

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"  # Par de moedas
    tick_size = 0.00001  # Precisão do preço (1 pip = 0.00001)

    # **Último candle antes do horário de fechamento**
    last_candle_time = datetime(
        2025, 1, 10, 12, 0, tzinfo=timezone.utc
    )  # Sexta-feira, 12h UTC
    close_candle_price = 1.15  # Preço de fechamento do último candle

    # **Define os preços do candle antes de abrir a posição**
    last_candle = {"open": 1.12, "high": 1.16, "low": 1.11, "close": close_candle_price}

    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(last_candle, name=last_candle_time),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = last_candle_time

    open_position_price = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )  # Preço de abertura com spread

    # **Abertura de posição de compra (`BUY`)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Ordem de compra
        volume=1,  # 1 lote
        comment="Position 1 (Buy)",  # Comentário para identificar a posição
    )

    # **Candle após o horário de fechamento para ativar o `swap`**
    last_candle_time_swap = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira, 23h UTC

    # Atualiza o último candle para validar o swap
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle, name=last_candle_time_swap
    )

    # **Aplicação do swap às posições abertas**
    __backtest_position_apply_swap_to_positions(
        operation_handler
    )  # Aplica o `swap` após o horário de fechamento (22h UTC)

    # **Atualização de preço atual e cálculo de lucro**
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Atualiza o preço atual e o lucro/prejuízo com o `swap`
    positions = account.backtest_account_data.positions  # Obtém as posições abertas

    # **Verificação do preço de abertura, `swap` e lucro esperado**
    assert (
        positions[0].price_open == open_position_price
    ), f"O preço de abertura está incorreto. Esperado: {open_position_price}, obtido: {positions[0].price_open}"
    assert (
        positions[0].swap == -1.0
    ), f"O valor do `swap` está incorreto. Esperado: -1.0, obtido: {positions[0].swap}"
    assert (
        positions[0].profit == -4.0
    ), f"O lucro da posição está incorreto. Esperado: -4.0, obtido: {positions[0].profit}"

    # **Cálculo do lucro total da conta**
    total_profit_with_swap = round(positions[0].swap + positions[0].profit, 2)
    assert (
        account.backtest_account_data.profit == total_profit_with_swap
    ), f"Lucro total da conta está incorreto. Esperado: {total_profit_with_swap}, obtido: {account.backtest_account_data.profit}"
