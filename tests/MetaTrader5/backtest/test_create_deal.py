# Biblioteca de testes
import pytest  # Para criação e execução de testes unitários

# Módulo de conta e informações do MetaTrader5
from algo_trading.sources.MetaTrader5_source.account.account import Account  # Classe `Account` para gerenciamento de contas

# Modelos e enums relacionados ao MetaTrader5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE,  # Enum para tipos de ordens (compra, venda, limite, etc.)
    ENUM_DEAL_TYPE,  # Enum para tipos de deals (DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_DEAL_ENTRY,  # Enum para tipo de entrada do deal (IN, OUT, INOUT)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum para modo de trade da conta (real, demo, hedge)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para tipo de stopout
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para modo de margem da conta
    ENUM_ORDER_TYPE_MARKET,  # Enum para ordens de mercado
    MqlAccountInfo,  # Modelo com informações detalhadas sobre a conta do MetaTrader5
)

# Módulos auxiliares
from datetime import datetime, timezone  # Para manipulação de datas e horas
import pandas as pd  # Para manipulação de dados em série temporal (últimos candles)

# Funções para criação e manipulação de deals e posições
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_create_a_deal,  # Função interna para criação de deals no backtest
    __backtest_open_position,  # Função interna para abrir posições no modo de backtest
)

@pytest.fixture
def account():
    """Fixture que cria uma instância de conta para os testes.
    
    Simula o login em uma conta ao vivo.
    
    Returns:
        Account: Instância de conta com dados configurados.
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

def test_backtest_create_a_deal_buy_entry_in(account: Account):
    """
    Testa a função `__backtest_create_a_deal` com uma entrada do tipo BUY (`DEAL_ENTRY_IN`).
    
    Verifica:
    1. Se o deal é criado corretamente.
    2. Se o lucro (`profit`) é 0 para uma nova entrada de compra.
    3. Se os atributos importantes do deal (símbolo, tipo de ordem, comentário, magic number) estão corretos.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(balance=5000, leverage=100)  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado para 4 pontos
    account.backtest_account_data.magic_number = 123456  # Define o magic number da conta para identificar operações automáticas

    # **Configuração da posição inicial**
    symbol = "EURUSD"  # Par de moedas negociado
    initial_price = 1.12345  # Preço de abertura da posição
    initial_volume = 1.0  # Volume inicial em lotes (1 lote = 100.000 unidades)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Obtém o manipulador de operações da conta
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Define a moeda da conta

    # **Mock de candle para simular o estado do mercado**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume de ticks para simular liquidez
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o estado do mercado (último candle, tamanho do contrato e tick size)
    operation_handler.last_candle = {symbol: mock_series}  # Último candle para o par de moedas
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato (100.000 unidades por lote)
    operation_handler.tick_sizes = {symbol: 1e-05}  # Incremento mínimo de preço (0.00001 para 5 casas decimais)

    # **Configuração do modo hedge**
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING  # Permite múltiplas posições no mesmo ativo

    # **Abertura da posição inicial**
    __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Ordem de compra a mercado
        volume=initial_volume,  # Volume de 1 lote
        stop_price=1.12,  # Preço de stop-loss
        profit_price=1.13,  # Preço de take-profit
        comment="Teste de Hedge Mode",
    )

    # **Mock de posição aberta**
    position = account.backtest_account_data.positions[0]  # Obtém a posição aberta após o `__backtest_open_position`

    # **Criação do deal**
    deal_time = datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc)  # Data/hora do deal
    volume = 1.0  # Volume da nova entrada
    price = 1.1250  # Preço do deal
    comment = "Test Buy Entry"  # Comentário do deal

    # Chamada da função `__backtest_create_a_deal` para criar o deal de compra
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        volume=volume,
        price=price,
        position=position,
        comment=comment,
    )

    # **Verificações do Deal Criado**
    assert deal.symbol == symbol, "O símbolo do deal está incorreto."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "O tipo de deal deveria ser BUY."
    assert deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_IN, "A entrada do deal deveria ser IN."
    assert deal.profit == 0, "O lucro deveria ser 0 para uma nova entrada de compra."
    assert deal.comment == comment, "O comentário do deal está incorreto."
    assert deal.magic == 123456, "O magic number do deal está incorreto."

def test_backtest_create_a_deal_sell_entry_out(account: Account):
    """
    Testa a função `__backtest_create_a_deal` com uma saída parcial do tipo SELL (`DEAL_ENTRY_OUT`).
    
    Verifica:
    1. Se o deal de fechamento parcial é criado corretamente.
    2. Se o lucro é positivo quando a posição é fechada com lucro.
    3. Se os atributos importantes do deal (símbolo, tipo de ordem, volume, comentário, profit) estão corretos.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(balance=5000, leverage=100)  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado para 4 pontos
    account.backtest_account_data.magic_number = 654321  # Define o magic number

    # **Configuração da posição inicial**
    symbol = "EURUSD"  # Par de moedas negociado
    initial_price = 1.1300  # Preço de abertura da posição (para SELL)
    initial_volume = 1.0  # Volume inicial em lotes (1 lote = 100.000 unidades)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Obtém o manipulador de operações da conta
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Define a moeda da conta

    # **Mock de candle para simular o estado do mercado**
    mock_series_data = {
        "open": 1.1300,
        "high": 1.1320,
        "low": 1.1280,
        "close": initial_price,
        "tick_volume": 200,  # Volume de ticks para simular liquidez
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o estado do mercado (último candle, tamanho do contrato e tick size)
    operation_handler.last_candle = {symbol: mock_series}
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato padrão
    operation_handler.tick_sizes = {symbol: 1e-05}  # Incremento mínimo de preço

    # **Configuração do modo hedge**
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING

    # **Abertura de posição inicial de venda**
    __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Ordem de venda a mercado
        volume=initial_volume,  # Volume de 1 lote
        stop_price=1.1350,  # Preço de stop-loss
        profit_price=1.1200,  # Preço de take-profit
        comment="Teste de posição SELL",
    )

    # **Mock de posição aberta**
    position = account.backtest_account_data.positions[0]  # Obtém a posição aberta após o `__backtest_open_position`

    # **Parâmetros do deal de fechamento parcial**
    deal_time = datetime(2025, 1, 3, 13, 0, tzinfo=timezone.utc)  # Data/hora do deal
    partial_volume = 0.5  # Fechamento parcial de 0.5 lotes
    close_price = 1.1250  # Preço de fechamento
    comment = "Test Partial Close"

    # **Criação do deal de fechamento parcial**
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Ordem de compra para fechar parte da posição SELL
        volume=partial_volume,
        price=close_price,
        position=position,
        comment=comment,
    )

    # **Verificações do Deal Criado**
    assert deal.symbol == symbol, "O símbolo do deal está incorreto."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "O tipo de deal deveria ser BUY."
    assert deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT, "A entrada do deal deveria ser OUT."
    assert deal.volume == partial_volume, "O volume do deal deveria ser igual ao volume de fechamento parcial."
    assert deal.position_id == position.ticket, "O ID da posição no deal está incorreto."
    assert deal.profit == 250, "O lucro deveria ser positivo para um fechamento parcial com preço favorável."
    assert deal.comment == comment, "O comentário do deal está incorreto."
    assert deal.magic == 654321, "O magic number do deal está incorreto."

def test_backtest_create_a_deal_inout_reversal(account: Account):
    """
    Testa a função `__backtest_create_a_deal` com uma reversão (`DEAL_ENTRY_INOUT`).
    
    Verifica:
    1. Se o deal de reversão é criado corretamente.
    2. Se o lucro da reversão é calculado corretamente.
    3. Se os atributos importantes do deal (símbolo, tipo de ordem, volume, comentário, profit) estão corretos.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(balance=5000, leverage=100)  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado para 4 pontos
    account.backtest_account_data.magic_number = 789012  # Define o magic number

    # **Configuração da posição inicial**
    symbol = "EURUSD"  # Par de moedas negociado
    initial_price = 1.1300  # Preço de abertura da posição (para SELL)
    initial_volume = 1.0  # Volume inicial em lotes (1 lote = 100.000 unidades)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Obtém o manipulador de operações da conta
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Define a moeda da conta

    # **Mock de candle para simular o estado do mercado**
    mock_series_data = {
        "open": 1.1300,
        "high": 1.1320,
        "low": 1.1280,
        "close": initial_price,
        "tick_volume": 200,  # Volume de ticks para simular liquidez
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o estado do mercado (último candle, tamanho do contrato e tick size)
    operation_handler.last_candle = {symbol: mock_series}
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato padrão
    operation_handler.tick_sizes = {symbol: 1e-05}  # Incremento mínimo de preço

    # **Configuração do modo hedge**
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING

    # **Abertura de posição inicial de venda**
    __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Ordem de venda a mercado
        volume=initial_volume,  # Volume de 1 lote
        stop_price=1.1350,  # Preço de stop-loss
        profit_price=1.1200,  # Preço de take-profit
        comment="Teste de posição SELL",
    )

    # **Mock de posição aberta**
    position = account.backtest_account_data.positions[0]  # Obtém a posição aberta após o `__backtest_open_position`

    # **Parâmetros do deal de reversão**
    deal_time = datetime(2025, 1, 3, 14, 0, tzinfo=timezone.utc)  # Data/hora do deal
    reversal_volume = 2.0  # Volume maior para reverter a posição
    close_price = 1.1250  # Preço de fechamento para reverter a posição
    comment = "Test Reversal"

    # **Criação do deal de reversão**
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Ordem de compra para reverter a posição SELL
        volume=reversal_volume,
        price=close_price,
        position=position,
        comment=comment,
    )

    # **Cálculo Esperado do Lucro**
    contract_size = operation_handler.contract_sizes[symbol]
    expected_profit = round((initial_price - close_price) * contract_size * position.volume, 5)  # (1.1300 - 1.1250) * 100.000 * 1 lote

    # **Verificações do Deal Criado**
    assert deal.symbol == symbol, "O símbolo do deal está incorreto."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "O tipo de deal deveria ser BUY."
    assert deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT, "A entrada do deal deveria ser INOUT (reversão)."
    assert deal.volume == reversal_volume, "O volume do deal deveria ser igual ao volume de reversão."
    assert deal.position_id == position.ticket, "O ID da posição no deal está incorreto."
    assert deal.profit == expected_profit, f"O lucro deveria ser {expected_profit} USD para uma reversão lucrativa."
    assert deal.comment == comment, "O comentário do deal está incorreto."
    assert deal.magic == 789012, "O magic number do deal está incorreto."

def test_backtest_create_a_deal_no_order_id(account: Account):
    """
    Testa a função `__backtest_create_a_deal` com `order` como `None`.
    
    Verifica:
    1. Se um ID aleatório é gerado automaticamente quando `order` não é fornecido.
    2. Se os atributos importantes do deal (símbolo, tipo de ordem, volume, comentário, order ID) estão corretos.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(balance=5000, leverage=100)  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado para 4 pontos
    account.backtest_account_data.magic_number = 123456  # Define o magic number

    # **Configuração da posição inicial**
    symbol = "EURUSD"  # Par de moedas negociado
    initial_price = 1.1200  # Preço de abertura da posição
    initial_volume = 1.0  # Volume inicial em lotes (1 lote = 100.000 unidades)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Obtém o manipulador de operações da conta
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Define a moeda da conta

    # **Mock de candle para simular o estado do mercado**
    mock_series_data = {
        "open": 1.1195,
        "high": 1.1210,
        "low": 1.1185,
        "close": initial_price,
        "tick_volume": 150,  # Volume de ticks para simular liquidez
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o estado do mercado (último candle, tamanho do contrato e tick size)
    operation_handler.last_candle = {symbol: mock_series}
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato padrão
    operation_handler.tick_sizes = {symbol: 1e-05}  # Incremento mínimo de preço

    # **Configuração do modo hedge**
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING

    # **Abertura de posição inicial de compra**
    __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Ordem de compra a mercado
        volume=initial_volume,  # Volume de 1 lote
        stop_price=1.1150,  # Preço de stop-loss
        profit_price=1.1300,  # Preço de take-profit
        comment="Teste de posição BUY",
    )

    # **Mock de posição aberta**
    position = account.backtest_account_data.positions[0]  # Obtém a posição aberta após o `__backtest_open_position`

    # **Parâmetros do deal de compra sem ID de ordem**
    deal_time = datetime(2025, 1, 3, 15, 0, tzinfo=timezone.utc)  # Data/hora do deal
    volume = 1.0  # Volume da nova entrada
    price = 1.1250  # Preço do deal
    comment = "Test No Order ID"  # Comentário do deal

    # **Criação do deal sem order ID**
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Ordem de compra
        volume=volume,
        price=price,
        position=position,
        order=None,  # ID de ordem não fornecido
        comment=comment,
    )

    # **Verificações do Deal Criado**
    assert deal.symbol == symbol, "O símbolo do deal está incorreto."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "O tipo de deal deveria ser BUY."
    assert deal.volume == volume, "O volume do deal deveria ser igual ao volume da ordem."
    assert deal.comment == comment, "O comentário do deal está incorreto."
    assert deal.magic == 123456, "O magic number do deal está incorreto."
    assert deal.order is not None, "O ID da ordem não deveria ser None."
    assert isinstance(deal.order, int), "O ID da ordem deveria ser um número inteiro."
