# Importações de bibliotecas e dependências necessárias
import pytest
from datetime import datetime, timezone
import pandas as pd

# Importações de classes, enums e funções do MetaTrader 5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,
    ENUM_ORDER_TYPE_MARKET,
    ENUM_SYMBOL_CALC_MODE,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
    ENUM_SYMBOL_SWAP_MODE,
)
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_account_update_equity,
    __backtest_account_update_margin,
    __backtest_position_open,
    __backtest_position_update_price_and_profit,
    __backtest_position_apply_swap_to_positions,
    __backtest_account_check_margin_call,
    __backtest_account_process_stop_out,
)
from algo_trading.sources.MetaTrader5_source.account.account import Account


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


# **Teste 1: Atualização de Equity com Posição de Compra (`BUY`)**
def test_update_equity_with_buy_position(account: Account):
    """
    Testa a atualização do equity da conta com uma posição de compra aberta.

    Objetivo:
    - Verificar se o equity da conta é atualizado corretamente com base no saldo e lucro da posição.
    - Considerar o `simulated_spread` e o `swap` na atualização do equity.
    """
    # **Inicializa a conta de backtest com saldo inicial e alavancagem configurados**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"  # Par de moedas
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.14  # Preço de fechamento do último candle
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_price},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Último candle de preço antes da atualização**
    operation_handler.account_data.backtest_last_swap_date = (
        last_candle_time  # Data do último swap
    )

    # **Abertura de uma posição de compra (BUY)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,  # Volume da posição (1 lote)
        comment="Position 1 (Buy)",
    )

    # **Atualiza o último candle com um novo horário e o mesmo preço para aplicar o swap**
    last_candle_time = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira, 23h
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_price},
        name=last_candle_time,
    )

    # **Atualização do swap, lucro e equity**
    __backtest_position_apply_swap_to_positions(operation_handler)
    __backtest_position_update_price_and_profit(operation_handler)
    __backtest_account_update_equity(operation_handler)

    # **Equity calculado**
    account_equity = account.backtest_account_data.equity

    # **Cálculo esperado**
    position = account.backtest_account_data.positions[0]  # Posição de compra aberta
    expected_equity = (
        account.backtest_account_data.balance + position.profit + position.swap
    )  # Equity esperado

    # **Verificação do equity**
    assert (
        account_equity == expected_equity
    ), f"Equity incorreto. Esperado: {expected_equity}, obtido: {account_equity}"


# **Teste 2: Atualização de Margem com Posição de Venda (`SELL`)**
def test_update_account_margin_with_sell_position(account: Account):
    """
    Testa a atualização de margem com uma posição de venda (`SELL`) aberta.

    Objetivo:
    - Verificar se a margem utilizada, margem livre e nível de margem são calculados corretamente com base no preço e alavancagem.
    """
    # **Inicializa a conta de backtest com saldo inicial e alavancagem configurados**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"  # Par de moedas
    contract_size = 100_000  # 1 lote = 100.000 unidades da moeda base

    # **Último candle de preço**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.12  # Preço de fechamento do último candle
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(
            {"open": 1.10, "high": 1.13, "low": 1.08, "close": close_price},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = (
        last_candle_time  # Data do último swap
    )

    # **Abertura de uma posição de venda (SELL)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Tipo de ordem: venda
        volume=1,  # Volume da posição (1 lote)
        comment="Position 2 (Sell)",  # Comentário identificando a posição
    )

    # **Atualiza o último candle com um novo horário e o mesmo preço para aplicar o swap**
    last_candle_time = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira, 23h

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_price},
        name=last_candle_time,
    )

    # **Atualização de margem**
    __backtest_position_apply_swap_to_positions(
        operation_class=operation_handler
    )  # Calcula e atualiza margem utilizada, margem livre e nível de margem
    __backtest_position_update_price_and_profit(
        operation_class=operation_handler
    )  # Calcula e atualiza margem utilizada, margem livre e nível de margem
    __backtest_account_update_margin(
        operation_class=operation_handler
    )  # Calcula e atualiza margem utilizada, margem livre e nível de margem
    margin_used = account.backtest_account_data.margin  # Margem total utilizada
    margin_free = (
        account.backtest_account_data.margin_free
    )  # Margem livre (equity - margem usada)
    margin_level = account.backtest_account_data.margin_level  # Nível de margem (%)

    # **Cálculos esperados**
    expected_margin = round(
        (contract_size * close_price) / account.backtest_account_data.leverage, 2
    )  # Margem usada
    expected_margin_free = round(
        account.backtest_account_data.equity - expected_margin, 2
    )  # Margem livre
    expected_margin_level = round(
        (account.backtest_account_data.equity / expected_margin) * 100, 3
    )  # Nível de margem (%)

    # **Verificações**
    assert (
        margin_used == expected_margin
    ), f"Margem usada incorreta. Esperado: {expected_margin}, obtido: {margin_used}"
    assert (
        margin_free == expected_margin_free
    ), f"Margem livre incorreta. Esperado: {expected_margin_free}, obtido: {margin_free}"
    assert (
        margin_level == expected_margin_level
    ), f"Nível de margem incorreto. Esperado: {expected_margin_level}%, obtido: {margin_level}%"


# **Teste 3: Atualização de Equity com Lucro Zero**
def test_update_equity_with_zero_profit(account: Account):
    """
    Testa a atualização do equity com lucro zero (sem posições abertas).
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # Atualização do equity sem posições abertas
    __backtest_account_update_equity(operation_handler)
    equity = account.backtest_account_data.equity

    # O equity deve ser igual ao saldo quando não há lucro/prejuízo
    expected_equity = 10000.0
    assert (
        equity == expected_equity
    ), f"Equity incorreto com lucro zero. Esperado: {expected_equity}, obtido: {equity}"


# **Teste 4: Atualização de Margem com Nenhuma Posição Aberta**
def test_update_account_margin_with_no_positions(account: Account):
    """
    Testa a atualização de margem quando não há posições abertas.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # Atualização de margem sem posições abertas
    __backtest_account_update_margin(operation_handler)

    margin_used = account.backtest_account_data.margin
    margin_free = account.backtest_account_data.margin_free
    margin_level = account.backtest_account_data.margin_level

    # Com nenhuma posição aberta, margem usada deve ser zero
    assert (
        margin_used == 0.0
    ), f"Margem usada incorreta. Esperado: 0.0, obtido: {margin_used}"
    assert (
        margin_free == 10000.0
    ), f"Margem livre incorreta. Esperado: 10000.0, obtido: {margin_free}"
    assert margin_level == float(
        "inf"
    ), f"Nível de margem incorreto. Esperado: infinito, obtido: {margin_level}"


# **Teste 5: Verificação de Margin Call (`__check_margin_call`)**
def test_check_margin_call(account: Account, caplog):
    """
    Testa a verificação de margin call com base no nível de margem e modo de stopout configurado.

    Objetivo:
    - Verificar se um aviso de `margin call` é emitido corretamente quando o nível de margem cai abaixo do limite configurado (`margin_so_call`).
    - Testar diferentes modos de stopout (`percent` e `money`) e validar os alertas de margem.
    - Garantir que o nível de margem calculado seja exatamente igual ao nível desejado.
    """
    # **Inicializa a conta de backtest com saldo inicial e alavancagem configurados**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    # **Configuração de parâmetros de margem e stopout**
    account.backtest_account_data.margin_so_mode = (
        ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
    )  # Stopout por porcentagem
    account.backtest_account_data.margin_so_call = (
        50.0  # Nível de margem mínimo permitido (%)
    )

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"  # Par de moedas
    contract_size = 100_000  # 1 lote = 100.000 unidades da moeda base
    tick_size = 0.00001  # Precisão do preço (1 pip = 0.00001)
    volume = 1  # Volume da posição (1 lote)

    # **Último candle de preço antes da posição**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.12  # Preço de fechamento do candle
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(
            {"open": 1.10, "high": 1.13, "low": 1.08, "close": close_price},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Abertura de uma posição de venda (`SELL`)**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Tipo de ordem: venda
        volume=volume,  # Volume de 1 lote
        comment="Position 1 (Sell)",  # Comentário identificando a posição
    )

    # **Simulação de um novo preço para provocar um cenário de margin call**
    desired_level = (
        40.0  # Nível de margem desejado para simular o alerta de margin call (40%)
    )
    margin_used = (
        close_price * contract_size * volume
    ) / account.backtest_account_data.leverage  # Margem usada
    spread = (
        account.backtest_account_data.simulated_spread * tick_size
    )  # Valor do spread em pontos

    # **Cálculo do próximo preço de fechamento para atingir o nível de margem desejado**
    next_price = round(
        ((desired_level * margin_used) / 100 - account.backtest_account_data.balance)
        / (-contract_size * volume)
        + close_price
        - spread,
        5,
    )

    # **Atualização do último candle com o novo preço de fechamento**
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.10, "high": 1.13, "low": 1.08, "close": next_price},
        name=last_candle_time,
    )

    # **Atualização de margem e cálculo de lucro**
    __backtest_position_apply_swap_to_positions(
        operation_handler
    )  # Aplica o swap às posições abertas
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Atualiza o lucro/prejuízo com base no último preço
    __backtest_account_update_margin(
        operation_handler
    )  # Atualiza a margem usada, margem livre e nível de margem

    # **Captura os logs de nível `WARNING` para verificar mensagens de aviso**
    with caplog.at_level("WARNING"):
        __backtest_account_check_margin_call(
            operation_handler
        )  # Verifica se um alerta de margin call é emitido

    # **Cálculo esperado do nível de margem**
    expected_margin_level = (
        operation_handler.account_data.margin_level
    )  # Nível de margem atual

    # **Verificação do nível de margem e margem call**
    assert (
        round(expected_margin_level, 3) == desired_level
    ), f"Nível de margem não está no nível esperado. Esperado: {desired_level}%, obtido: {expected_margin_level:.2f}%"
    assert "[MARGIN CALL]" in caplog.text, "Aviso de margin call não foi registrado."
    assert (
        f"[MARGIN CALL] Nível de margem abaixo do limite ({expected_margin_level:.2f}%)."
        in caplog.text
    ), "Mensagem de alerta incorreta."


# **Teste 6: Processamento de Stop Out (`__process_stop_out`)**
def test_process_stop_out(account: Account, caplog):
    """
    Testa o processamento de stop out, verificando o fechamento de posições quando o nível de margem
    cai abaixo do limite permitido.

    Objetivo:
    - Verificar se as posições são fechadas corretamente em ordem FIFO ou pela maior perda, dependendo do `fifo_close`.
    - Validar os logs de alerta e o nível de margem após o processo de stop out.
    - Certificar-se de que múltiplos logs de stop out sejam gerados corretamente.
    """
    # **Inicialização da conta de backtest**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Spread simulado de 4 pips

    # **Configuração de parâmetros de stop out**
    account.backtest_account_data.margin_so_mode = (
        ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
    )  # Stop out baseado em percentual
    account.backtest_account_data.margin_so_call = 50.0  # Chamada de margem: 50%
    account.backtest_account_data.margin_so_so = 20.0  # Stop out efetivo: 20%
    account.backtest_account_data.fifo_close = False  # Fecha posições pela maior perda

    # **Configuração de parâmetros do mercado**
    symbol = "EURUSD"
    contract_size = 100_000  # 1 lote = 100.000 unidades
    tick_size = 0.00001  # Precisão do preço (1 pip = 0.00001)

    # **Criação do último candle de preço**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.12  # Preço de fechamento
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": pd.Series(
            {"open": 1.10, "high": 1.13, "low": 1.08, "close": close_price},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Abertura de múltiplas posições**
    sell_volume = 2  # 2 lotes na posição SELL
    buy_volume = 1  # 1 lote na posição BUY
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=buy_volume,
        comment="Position 1 (Buy)",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=sell_volume,
        comment="Position 2 (Sell)",
    )

    # **Simulação de preço crítico para provocar o stop out**
    desired_level = 10  # Nível de margem crítico (10%)
    balance = account.backtest_account_data.balance
    spread = account.backtest_account_data.simulated_spread * tick_size
    margin_used_sell = (
        close_price * contract_size * sell_volume
    ) / account.backtest_account_data.leverage
    margin_used_buy = (
        (close_price + spread) * contract_size * buy_volume
    ) / account.backtest_account_data.leverage
    margin_used = margin_used_buy + margin_used_sell

    numerator = (
        (desired_level * margin_used / 100)
        - balance
        + (margin_used_buy * account.backtest_account_data.leverage)
        + (contract_size * sell_volume * (spread - close_price))
    )
    denominator = contract_size * (buy_volume - sell_volume)
    critical_price = numerator / denominator

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.10, "high": 1.13, "low": 1.08, "close": critical_price},
        name=last_candle_time,
    )

    # **Atualização de lucro, margem e verificação do stop out**
    __backtest_position_apply_swap_to_positions(
        operation_handler
    )  # Aplica o swap às posições abertas
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Atualiza o lucro das posições abertas
    __backtest_account_update_margin(
        operation_handler
    )  # Atualiza a margem utilizada, margem livre e nível de margem

    # **Captura os logs para verificar mensagens de alerta e eventos de stop out**
    with caplog.at_level("INFO"):
        __backtest_account_process_stop_out(operation_handler)

    # **Verificações de logs e status após stop out**
    stop_out_logs = [
        record.message for record in caplog.records if "[STOP OUT]" in record.message
    ]
    final_logs = [
        record.message
        for record in caplog.records
        if "[STOP OUT FINALIZADO]" in record.message
    ]

    # **Verificações principais**
    assert len(stop_out_logs) > 0, "Nenhum aviso de stop out foi registrado."
    assert (
        len(final_logs) == 1
    ), "O log final de stop out não foi registrado corretamente."
    assert (
        account.backtest_account_data.margin_level
        > account.backtest_account_data.margin_so_so
    ), "O nível de margem não foi restaurado após o stop out."
    assert (
        account.backtest_account_data.margin_level == 30
    ), "O nível de margem restaurado não é o esperado (30%)."
    assert (
        len(account.backtest_account_data.positions) == 1
    ), "Nem todas as posições foram fechadas corretamente durante o stop out."

    # **Verificações de valores atualizados da conta**
    assert (
        account.backtest_account_data.equity == 336.01
    ), "Equity atualizado incorreto."
    assert (
        account.backtest_account_data.profit == 9648.0
    ), "Profit atualizado incorreto."
    assert (
        account.backtest_account_data.balance == -9311.99
    ), "Balance atualizado incorreto."
    assert (
        account.backtest_account_data.margin == 1120.04
    ), "Margem utilizada incorreta."
    assert (
        account.backtest_account_data.margin_free == -784.03
    ), "Margem livre atualizada incorreta."

    # **Verificação das mensagens de stop out**
    assert (
        "Nível de margem atingido! Iniciando fechamento das posições..."
        in stop_out_logs[0]
    ), "Mensagem inicial de stop out incorreta."
    assert (
        "Nível de margem restaurado após fechamento das posições." in caplog.text
    ), "Mensagem de restauração de margem após stop out não foi registrada."
    assert (
        "Saldo" in final_logs[0] and "Equity" in final_logs[0]
    ), "Log final de stop out não contém informações de saldo e equity."
