# Bibliotecas de teste
import pytest  # Biblioteca para criação e execução de testes unitários

# Imports relacionados ao MetaTrader5 (modelos e enums)
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE,  # Enum para tipos de ordens (compra, venda, limite, etc.)
    ENUM_DEAL_TYPE,  # Enum para tipos de deals (DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_POSITION_TYPE,  # Enum para tipos de posição (buy ou sell)
    ENUM_DEAL_ENTRY,  # Enum para tipo de entrada do deal (entrada, saída, reversão)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum para modo de trade da conta (real, demo, hedge)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para tipo de stopout
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para modo de margem da conta
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    MqlPositionInfo,  # Modelo que representa informações sobre a posição aberta
    MqlAccountInfo,  # Modelo que representa as informações da conta do MetaTrader5
)

# Imports de funções de backtest (funções internas que realizam cálculos e lógica de simulação)
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __get_deal_type,  # Função para determinar o tipo de deal com base no tipo de ordem
    __get_entry,  # Função para determinar o tipo de entrada com base no tipo de ordem e posição
    __backtest_get_profit,  # Função para calcular o lucro ou prejuízo de uma posição no backtest
    __validate_operation_handler_attributes_for_symbol,  # Função para verificar se existem atributos ausentes
)

# Imports para manipulação de datas e fuso horário
from datetime import (
    datetime,
    timezone,
)  # Para criação e manipulação de objetos de data/hora com timezone

# Import da classe Account (gerenciamento de conta para o backtest)
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe Account para login e gerenciamento de informações de conta

# Biblioteca de manipulação de dados
import pandas as pd  # Utilizada para criar e manipular DataFrames e Series, que simulam os candles e dados de ticks


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
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100.

    return account


def test_get_deal_type():
    """
    Testa a função `__get_deal_type`, que determina o tipo de deal com base no tipo de ordem.

    Este teste verifica:
    1. Se a função retorna `DEAL_TYPE_BUY` para tipos de ordem de compra.
    2. Se a função retorna `DEAL_TYPE_SELL` para tipos de ordem de venda.
    3. Se a função lança um `TypeError` para tipos de ordem inválidos.
    """
    # Teste de tipos de ordem de compra
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_BUY) == ENUM_DEAL_TYPE.DEAL_TYPE_BUY
    )
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP)
        == ENUM_DEAL_TYPE.DEAL_TYPE_BUY
    )

    # Teste de tipos de ordem de venda
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_SELL)
        == ENUM_DEAL_TYPE.DEAL_TYPE_SELL
    )
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT)
        == ENUM_DEAL_TYPE.DEAL_TYPE_SELL
    )

    # Tipo de ordem inválido
    with pytest.raises(TypeError, match="Invalid order type"):
        __get_deal_type("INVALID_ORDER_TYPE")


def test_get_entry():
    """
    Testa a função `__get_entry`, que determina o tipo de entrada do deal com base na posição atual e no tipo de ordem.

    Este teste verifica:
    1. Se a função retorna `DEAL_ENTRY_IN` para novas entradas na mesma direção.
    2. Se a função retorna `DEAL_ENTRY_OUT` para fechamento parcial ou total de uma posição.
    3. Se a função retorna `DEAL_ENTRY_INOUT` para reversões de posição.
    """
    # Mock de posição BUY com volume de 1.0
    position_buy = MqlPositionInfo(
        ticket=12345,
        time=datetime.now(timezone.utc),  # Corrigido
        time_msc=datetime.now(timezone.utc),  # Corrigido
        time_update=datetime.now(timezone.utc),  # Corrigido
        time_update_msc=datetime.now(timezone.utc),  # Corrigido
        type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        magic=42,
        identifier=999,
        reason=0,
        volume=1.0,
        price_open=1.2345,
        sl=1.2000,
        tp=1.2500,
        price_current=1.2400,
        swap=0.0,
        profit=100.0,
        symbol="EURUSD",
        comment="Test position",
        external_id="external_12345",
    )

    # Teste de nova entrada (IN)
    assert (
        __get_entry(0.5, ENUM_ORDER_TYPE.ORDER_TYPE_BUY, position_buy)
        == ENUM_DEAL_ENTRY.DEAL_ENTRY_IN
    )

    # Teste de fechamento parcial (OUT)
    assert (
        __get_entry(1.0, ENUM_ORDER_TYPE.ORDER_TYPE_SELL, position_buy)
        == ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT
    )

    # Teste de reversão (INOUT)
    assert (
        __get_entry(2.0, ENUM_ORDER_TYPE.ORDER_TYPE_SELL, position_buy)
        == ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT
    )


def test_backtest_get_profit(account: Account):
    """
    Testa a função `__backtest_get_profit`, que calcula o lucro ou prejuízo de uma posição de backtest.

    Este teste verifica:
    1. Se o lucro é calculado corretamente para posições de compra e venda.
    2. Se o retorno é zero para preços de abertura e fechamento iguais.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """

    # Configuração da conta de backtest:
    # Define o saldo inicial, a alavancagem e ativa o modo de backtest.
    account.login_backtest(balance=5000, leverage=100)

    # Define o spread simulado para o par de moedas (4 pontos)
    account.backtest_account_data.simulated_spread = 4

    # Obtém o manipulador de operações a partir da conta de backtest
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"

    # Par de moedas e configuração inicial da posição
    symbol: str = "EURUSD"
    initial_price = 1.12345  # Preço de abertura da posição
    initial_volume = 1.0  # Volume inicial da posição (em lotes)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Mock de candle para simulação de mercado
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume de ticks simulando liquidez no mercado
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define os dados do novo símbolo como um dicionário
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
        "last_candle": mock_series,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Caso 1: Posição de compra com lucro**
    # Preço de abertura: 1.1200 | Preço de fechamento: 1.1250 | Lucro esperado: 500 unidades na moeda base (USD)
    profit_buy = __backtest_get_profit(
        operation_class=operation_handler,
        symbol=symbol,
        price_open=1.1200,  # Preço no momento da abertura
        price_close=1.1250,  # Preço no momento do fechamento
        price_volume=initial_volume,  # Volume negociado (1 lote padrão)
        position_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,  # Tipo de posição (compra)
    )
    assert profit_buy == 500, "O lucro da posição de compra deveria ser 500 USD."

    # **Caso 2: Posição de venda com prejuízo**
    # Preço de abertura: 1.1300 | Preço de fechamento: 1.1350 | Prejuízo esperado: -500 unidades na moeda base (USD)
    profit_sell = __backtest_get_profit(
        operation_class=operation_handler,
        symbol=symbol,
        price_open=1.1300,
        price_close=1.1350,
        price_volume=1.0,
        position_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,  # Tipo de posição (venda)
    )
    assert profit_sell == -500, "O prejuízo da posição de venda deveria ser -500 USD."

    # **Caso 3: Sem lucro nem prejuízo**
    # Preço de abertura e fechamento iguais (1.1200)
    assert (
        __backtest_get_profit(
            operation_handler,
            symbol,
            1.1200,
            1.1200,
            1.0,
            ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        )
        == 0
    ), "O lucro deveria ser zero quando os preços de abertura e fechamento são iguais."


def test_validate_operation_handler_attributes_success(account: Account):
    """
    Testa se a função não levanta erros quando todos os atributos necessários estão presentes.
    """
    symbol = "EURUSD"
    operation_handler = account.backtest_account_data.operation
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Mock de candle para simulação de mercado
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": 1.12,
        "tick_volume": 100,  # Volume de ticks simulando liquidez no mercado
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define os dados do novo símbolo como um dicionário
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
        "last_candle": mock_series,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Chamada sem erro
    __validate_operation_handler_attributes_for_symbol(operation_handler, symbol)


def test_validate_operation_handler_missing_last_candle(account: Account):
    """
    Testa se levanta exceção quando os dados de `last_candle` estão ausentes.
    """
    symbol = "EURUSD"
    operation_handler = account.backtest_account_data.operation
    # Mock de candle para simulação de mercado

    # Define os dados do novo símbolo como um dicionário
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
        "last_candle": None,
    }

    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    with pytest.raises(
        ValueError,
        match=f"Os dados para o símbolo '{symbol}' contêm valores nulos ou ausentes nas seguintes colunas: last_candle.",
    ):
        __validate_operation_handler_attributes_for_symbol(operation_handler, symbol)


def test_validate_operation_handler_missing_symbol(account: Account):
    """
    Testa se levanta exceção quando o símbolo não está presente nos atributos.
    """
    symbol_missing = "USDJPY"
    symbol_present = "EURUSD"
    operation_handler = account.backtest_account_data.operation
    # Mock de candle para simulação de mercado
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": 1.12,
        "tick_volume": 100,  # Volume de ticks simulando liquidez no mercado
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define os dados do novo símbolo como um dicionário
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
        "last_candle": mock_series,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol_present])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    with pytest.raises(
        ValueError,
        match=f"Dados para o símbolo '{symbol_missing}' estão ausentes no DataFrame.",
    ):
        __validate_operation_handler_attributes_for_symbol(
            operation_handler, symbol_missing
        )
