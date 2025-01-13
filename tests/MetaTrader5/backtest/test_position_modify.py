# **Bibliotecas de Testes**
import pytest  # Biblioteca para criação e execução de testes unitários.

# **Bibliotecas de Datas e Horários**
from datetime import (
    datetime,
    timezone,
    timedelta,
)  # Utilizadas para definir timestamps com fuso horário UTC e manipulação de datas/horas.

# **Modelos e Enums do MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Modelo que contém informações da conta de trading (e.g., saldo, margem, nome da conta).
    ENUM_ACCOUNT_TRADE_MODE,  # Enum que define o modo de operação da conta (e.g., demo, real).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para o modo de stop-out (e.g., percentual ou valor fixo).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para definir o tipo de margem da conta (e.g., hedge, netting).
    ENUM_ORDER_TYPE_MARKET,  # Enum que define os tipos de ordens a mercado (e.g., BUY/SELL).
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
)

# **Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_open,  # Função que simula a abertura de posições em modo de backtest.
    __backtest_position_modify,  # Função que simula a modificação de posições em modo de backtest.
)

# **Exceções Personalizadas**
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
)  # Exceção personalizada levantada quando não é possível selecionar uma posição.

# **Classe de Conta**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe `Account` utilizada para login e gerenciamento das informações de conta de trading.

# **Biblioteca de Manipulação de Dados**
import pandas as pd  # Biblioteca utilizada para criar e manipular objetos `Series` que simulam candles de mercado.


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


def test_backtest_modify_position_single_position(account: Account):
    """
    Testa a função `__backtest_modify_position` quando existe apenas uma posição aberta.

    Verifica:
    1. Se a posição é selecionada automaticamente quando não é passado um `ticket`.
    2. Se os atributos `stop_price`, `profit_price` e `comment` são modificados corretamente.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da Conta de Backtest**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100.
    account.backtest_account_data.magic_number = (
        654321  # Define o magic number da conta para identificar operações.
    )

    # **Configuração da Posição Inicial**
    symbol = "EURUSD"  # Par de moedas negociado.
    initial_volume = 1.0  # Volume inicial da posição (1 lote = 100.000 unidades).
    initial_price = 1.12345  # Preço de abertura da posição.
    initial_stop_price = 1.1200  # Preço de stop-loss.
    initial_profit_price = 1.1300  # Preço de take-profit.
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle.

    # **Mock de Candle para Simulação de Mercado**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume de ticks para simular liquidez.
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o último candle para o par de moedas.
    operation_handler = (
        account.backtest_account_data.operation
    )  # Obtém o manipulador de operações.
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

    # **Abertura da Posição Inicial**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Ordem de compra a mercado.
        volume=initial_volume,
        stop_price=initial_stop_price,
        profit_price=initial_profit_price,
        comment="Initial position",  # Comentário inicial.
    )
    position = account.backtest_account_data.positions[0]  # Obtém a posição aberta.

    # **Parâmetros de Modificação**
    new_stop_price = 1.1180  # Novo preço de stop-loss.
    new_profit_price = 1.1350  # Novo preço de take-profit.
    new_comment = "Modified position"  # Novo comentário.

    # **Modificação da Posição**
    __backtest_position_modify(
        operation_class=operation_handler,
        stop_price=new_stop_price,
        profit_price=new_profit_price,
        comment=new_comment,
    )

    # **Verificações**
    assert position.sl == new_stop_price, "O stop-loss não foi atualizado corretamente."
    assert (
        position.tp == new_profit_price
    ), "O take-profit não foi atualizado corretamente."
    assert (
        position.comment == new_comment
    ), "O comentário não foi atualizado corretamente."


def test_backtest_modify_position_no_position_found(account: Account):
    """
    Testa a função `__backtest_modify_position` quando não há posições abertas ou
    quando o `ticket` fornecido não corresponde a nenhuma posição.

    Verifica:
    1. Se uma exceção `CouldNotSelectPosition` é levantada quando não há posições.
    2. Se uma exceção é levantada quando o `ticket` fornecido é inválido.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da Conta de Backtest**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100.
    operation_handler = (
        account.backtest_account_data.operation
    )  # Manipulador de operações.
    symbol = "EURUSD"  # Par de moedas negociado.
    initial_price = 1.12345  # Preço de abertura da posição.
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle.

    # **Mock de Candle para Simulação de Mercado**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume de ticks para simular liquidez.
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

    # **Teste: Nenhuma posição aberta**
    with pytest.raises(CouldNotSelectPosition, match="Could not select the position"):
        __backtest_position_modify(
            operation_class=operation_handler,
            stop_price=1.1200,
            profit_price=1.1300,
            comment="Attempt to modify non-existent position",
        )

    # **Abertura de uma posição**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1.0,
        stop_price=1.1200,
        profit_price=1.1300,
        comment="Position 1",
    )

    # **Teste: `ticket` incorreto**
    with pytest.raises(CouldNotSelectPosition, match=r"Could not select the position"):
        __backtest_position_modify(
            operation_class=operation_handler,
            position=999999,  # `Ticket` inválido (não corresponde a nenhuma posição).
            stop_price=1.1190,
            profit_price=1.1380,
            comment="Attempt to modify with wrong ticket",
        )


def test_backtest_modify_position_specific_ticket(account: Account):
    """
    Testa a função `__backtest_modify_position` quando há múltiplas posições abertas e
    um `ticket` específico é fornecido.

    Verifica:
    1. Se a posição correta é selecionada pelo `ticket`.
    2. Se os atributos `stop_price`, `profit_price` e `comment` são modificados corretamente.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """
    # **Configuração da Conta de Backtest**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100.
    symbol = "EURUSD"  # Par de moedas negociado.
    operation_handler = (
        account.backtest_account_data.operation
    )  # Manipulador de operações.
    initial_price = 1.12345  # Preço de abertura da posição.
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle.

    # **Mock de Candle para Simulação de Mercado**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume de ticks para simular liquidez.
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

    # **Abertura de Duas Posições**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1.0,
        stop_price=1.1200,
        profit_price=1.1300,
        comment="Position 1",
    )

    # **Atualização do Timestamp para Garantir Diferença entre as Ordens**
    updated_time = operation_handler.backtest_symbols_data.loc[
        symbol
    ].last_candle.name + timedelta(days=2)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        mock_series_data, name=pd.to_datetime(updated_time)
    )

    # Segunda posição com timestamp diferente.
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1.0,
        stop_price=1.1220,
        profit_price=1.1350,
        comment="Position 2",
    )

    # **Seleciona a Posição a ser Modificada**
    position_to_modify = account.backtest_account_data.positions[
        1
    ]  # Seleciona a segunda posição.

    # **Parâmetros de Modificação**
    new_stop_price = 1.1190  # Novo stop-loss.
    new_profit_price = 1.1380  # Novo take-profit.
    new_comment = "Updated Position 2"  # Novo comentário.

    # **Modificação da Posição**
    __backtest_position_modify(
        operation_class=operation_handler,
        stop_price=new_stop_price,
        profit_price=new_profit_price,
        position=position_to_modify.ticket,  # Fornece o `ticket` específico.
        comment=new_comment,
    )

    # **Verificações**
    assert (
        position_to_modify.sl == new_stop_price
    ), "O stop-loss não foi atualizado corretamente."
    assert (
        position_to_modify.tp == new_profit_price
    ), "O take-profit não foi atualizado corretamente."
    assert (
        position_to_modify.comment == new_comment
    ), "O comentário não foi atualizado corretamente."
