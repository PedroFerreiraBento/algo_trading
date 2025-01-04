# Imports para bibliotecas externas
import pytest  # Biblioteca para criação de testes unitários
from datetime import datetime, timezone  # Classes para manipulação de datas e fuso horário
import pandas as pd  # Biblioteca para manipulação de DataFrames

# Imports de enums, classes e modelos relacionados ao MetaTrader5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE_MARKET,  # Enum para tipos de ordens de mercado
    ENUM_POSITION_TYPE,  # Enum para tipos de posições (compra/venda)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para modos de margem de conta
    MqlAccountInfo,  # Modelo de informações da conta MetaTrader5
    ENUM_ACCOUNT_TRADE_MODE,  # Enum para modos de operação da conta
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para modos de stopout da conta
    ENUM_DEAL_TYPE,  # Enum para tipos de negócio (ex.: execução de ordem)
    ENUM_DEAL_ENTRY,  # Enum para entradas de negociação (entrada, saída)
)

# Imports de funções específicas relacionadas ao backtest
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __hedge_create_position_and_deal,  # Função interna para criar posição e negócio no modo hedge
    __netting_create_position_and_deal,  # Função interna para criar posição e negócio no modo netting
    __backtest_open_position,  # Função interna para abrir posição durante um backtest
)

# Import do módulo Account (gerenciamento de conta)
from algo_trading.sources.MetaTrader5_source.account.account import Account


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


def test_hedge_create_position_and_deal(account):
    """Teste para `__hedge_create_position_and_deal`.

    Este teste verifica o comportamento da função ao criar uma posição e registrar um deal
    em uma conta de backtest configurada no modo hedge.

    O modo hedge permite que múltiplas posições sejam abertas no mesmo par de moedas, 
    possibilitando posições de compra e venda simultâneas sem agregação.

    Passos do teste:
    1. Configuração inicial da conta de backtest com saldo e spread.
    2. Execução da função `__hedge_create_position_and_deal` com parâmetros específicos.
    3. Verificação das posições abertas e do histórico de deals para garantir o comportamento correto.

    Args:
        account (Account): Fixture que fornece uma conta de backtest pré-configurada.
    """

    # Configuração da conta de backtest:
    # Define o saldo inicial e alavancagem e ativa o modo de backtest.
    account.login_backtest(balance=5000, leverage=100)

    # Define o spread simulado para o par de moedas (4 pontos)
    account.backtest_account_data.simulated_spread = 4

    # Obtém o manipulador de operações a partir da conta de backtest
    operation_handler = account.backtest_account_data.operation

    # Parâmetros para criação da posição
    symbol = "EURUSD"  # Par de moedas a ser negociado
    order_type = ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY  # Tipo de ordem (compra)
    position_time = datetime(2023, 12, 31, tzinfo=timezone.utc)  # Data e hora da operação
    price = 1.12345  # Preço de entrada da posição
    volume = 1.0  # Volume da posição (em lotes)

    # Executa a função de criação de posição e registro de deal
    __hedge_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=order_type,
        position_time=position_time,
        price=price,
        volume=volume,
        stop_price=1.12000,  # Stop-loss configurado
        profit_price=1.13000,  # Take-profit configurado
    )

    # Verificação 1: Deve existir exatamente uma posição aberta após a execução
    assert len(operation_handler.account_data.positions) == 1, "A posição não foi criada corretamente."

    # Verificação 2: O histórico de deals deve ter exatamente duas entradas:
    # - 1º: Deal de inicialização da conta (entrada do saldo inicial).
    # - 2º: Deal correspondente à abertura da nova posição.
    assert len(operation_handler.account_data.history_deals) == 2, "O histórico de deals não foi atualizado corretamente."

    # Acessa a posição e o último deal para validar suas informações
    position = operation_handler.account_data.positions[0]  # Posição aberta
    deal = operation_handler.account_data.history_deals[-1]  # Último deal registrado

    # Verificação 3: Valida as informações da posição aberta
    assert position.symbol == symbol, "O símbolo da posição não corresponde ao esperado."
    assert position.volume == volume, "O volume da posição está incorreto."
    assert position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY, "O tipo de posição deveria ser de compra."
    assert deal.price == price, "O preço de entrada no deal não corresponde ao esperado."

def test_netting_create_position_and_deal_partial_close(account):
    """
    Testa o fechamento parcial de uma posição em conta de backtest com netting.

    Este teste verifica se, ao fechar parcialmente uma posição, a operação é
    realizada corretamente e os dados de posição e histórico de deals são atualizados.

    Args:
        account: Fixture que configura uma conta de backtest com valores iniciais.
    """
    
    # Configura a conta de backtest com um saldo inicial e um spread simulado.
    account.login_backtest(balance=5000, leverage=100)
    account.backtest_account_data.simulated_spread = 4  # Simula um spread de 4 pontos.
    
    # Obtém o manipulador de operações da conta de backtest.
    operation_handler = account.backtest_account_data.operation
    operation_handler.contract_sizes = {"EURUSD": 100_000}  # Define o tamanho do contrato.
    operation_handler.tick_sizes = {"EURUSD": 1e-05}  # Define o tamanho do tick (precisão do preço).

    # **PASSO 1:** Cria uma posição de **compra (BUY)**.
    symbol = "EURUSD"  # Ativo a ser negociado.
    position_time = datetime(2023, 12, 31, tzinfo=timezone.utc)  # Tempo da posição.

    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Ordem de compra.
        position_time=position_time,
        price=1.12345,  # Preço de abertura.
        volume=1.0,  # Volume da posição (1 lote).
    )
    
    # **PASSO 2:** Fecha parcialmente a posição com uma **venda (SELL)**.
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Ordem de venda.
        position_time=position_time,
        price=1.12,  # Preço de fechamento.
        volume=0.5,  # Fecha metade do volume (0.5 lotes).
    )
    
    # **Verificações:** Confirma se os valores de posição e histórico de deals foram atualizados corretamente.

    # A posição restante deve ter volume de 0.5 lotes.
    assert operation_handler.account_data.positions[0].volume == 0.5

    # A direção da posição deve permanecer como BUY (pois foi uma venda parcial).
    assert operation_handler.account_data.positions[0].type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY

    # Deve haver exatamente 3 deals no histórico:
    # 1º: Deal de inicialização da conta de backtest (inicialização com saldo).
    # 2º: Abertura da posição de compra (BUY).
    # 3º: Fechamento parcial da posição com venda (SELL).
    assert len(operation_handler.account_data.history_deals) == 3

    # Verifica se o lucro da operação foi calculado corretamente.
    # Cálculo esperado:
    # - Diferença de preço: (1.12345 - 1.12) = 0.00345 (pontos perdidos).
    # - Volume parcial: 0.5 (lotes).
    # - Tamanho do contrato: 100_000 unidades da moeda base.
    # Lucro: 100_000 * 0.5 * -0.00345 = -172.5.
    assert operation_handler.account_data.history_deals[-1].profit == -172.5

def test_netting_create_position_and_deal_reversal(account):
    """Teste para a função `__netting_create_position_and_deal` com reversão de posição.

    Este teste simula um cenário de reversão em uma conta configurada para netting,
    onde uma posição aberta (SELL) é revertida com uma nova posição oposta (BUY).
    Verifica-se se a posição original é fechada e se o lucro/perda é calculado corretamente.

    Args:
        account (Account): Fixture que fornece uma conta de backtest configurada.
    """
    
    # Configuração inicial da conta de backtest
    account.login_backtest(balance=5000, leverage=100)  # Inicializa o backtest com saldo de 5000 e alavancagem de 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado de 4 pontos

    # Parâmetros da posição inicial (SELL)
    symbol = "EURUSD"  # Par de moedas negociado
    position_time = datetime(2023, 12, 31, tzinfo=timezone.utc)  # Data/hora da execução
    initial_price = 1.12345  # Preço de abertura da posição SELL
    initial_volume = 1.0  # Volume inicial da posição (em lotes)

    # Obtém o manipulador de operações a partir da conta de backtest
    operation_handler = account.backtest_account_data.operation
    operation_handler.contract_sizes = {symbol: 100_000}  # Define o tamanho do contrato para o par de moedas
    operation_handler.tick_sizes = {symbol: 1e-05}  # Define o menor incremento de preço para o par

    # Criação da posição inicial de venda (SELL)
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        position_time=position_time,
        price=initial_price,
        volume=initial_volume,
    )

    # Verificações após abertura da posição inicial:
    # Deve haver exatamente uma posição aberta do tipo SELL
    assert len(operation_handler.account_data.positions) == 1, "A posição inicial não foi criada corretamente."
    assert operation_handler.account_data.positions[0].type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL, "A posição inicial deveria ser de venda."

    # Parâmetros para a reversão da posição (compra maior que o volume da venda inicial)
    reversal_price = 1.12500  # Preço de entrada da posição BUY (reversão)
    reversal_volume = 2.0  # Volume maior para forçar a reversão completa

    # Execução da posição oposta de compra (BUY)
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        position_time=position_time,
        price=reversal_price,
        volume=reversal_volume,
    )

    # Verificações após a reversão:
    # Deve haver apenas uma posição aberta e deve ser do tipo BUY
    assert len(operation_handler.account_data.positions) == 1, "A posição não foi revertida corretamente."
    position = operation_handler.account_data.positions[0]
    assert position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY, "A posição deveria ser de compra após a reversão."
    assert position.volume == 1.0, "O volume da posição está incorreto após a reversão."

    # Verificações no histórico de deals:
    # Deve haver exatamente 3 deals: criação da posição SELL, fechamento da SELL e abertura da BUY
    assert len(operation_handler.account_data.history_deals) == 3, "O histórico de deals não foi atualizado corretamente."

    # Verifica o lucro/perda do deal de fechamento da posição
    last_deal = operation_handler.account_data.history_deals[-1]
    expected_profit = operation_handler.contract_sizes[symbol] * (initial_price - reversal_price) * initial_volume
    assert last_deal.profit == round(expected_profit, 5), f"O lucro esperado é {expected_profit}, mas foi {last_deal.profit}."
    assert last_deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "O tipo do último deal deveria ser BUY após a reversão."
    assert last_deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT, "A entrada do último deal deveria ser de reversão (INOUT)."

def test_backtest_open_position_hedging(account):
    """
    Testa a função __backtest_open_position para o modo Hedge.

    Verifica se a função realiza a abertura de posições corretamente em uma conta configurada para o modo Hedge,
    onde múltiplas posições na mesma ou em direções opostas são permitidas.
    """

    # Configuração inicial da conta de backtest
    account.login_backtest(balance=5000, leverage=100)  # Inicializa o backtest com saldo de 5000 e alavancagem de 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado de 4 pontos

    # Parâmetros da posição inicial
    symbol = "EURUSD"  # Par de moedas negociado
    initial_price = 1.12345  # Preço de abertura da posição
    initial_volume = 1.0  # Volume inicial da posição (em lotes)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Obtém o manipulador de operações a partir da conta de backtest
    operation_handler = account.backtest_account_data.operation

    # Mock de candle para simulação
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o estado simulado do mercado
    operation_handler.last_candle = {symbol: mock_series}  # Define os últimos candles para o par de moedas
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato padrão de forex
    operation_handler.tick_sizes = {symbol: 1e-05}  # Incremento mínimo de preço (tick size)

    # Configuração para modo Hedge
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING

    # Execução do teste: abertura de posição de compra no modo Hedge
    result = __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=initial_volume,
        stop_price=1.12,  # Preço de stop-loss
        profit_price=1.13,  # Preço de take-profit
        comment="Teste de Hedge Mode",
    )

    # Verificações de resultado
    assert result is True, "A função não retornou True para Hedge mode."
    assert len(operation_handler.account_data.positions) == 1, "A posição não foi criada corretamente no modo Hedge."
    assert operation_handler.account_data.positions[0].type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY, "A posição deveria ser do tipo BUY."
    assert operation_handler.account_data.positions[0].symbol == symbol, "O símbolo da posição não corresponde ao esperado."
    assert operation_handler.account_data.positions[0].volume == initial_volume, "O volume da posição está incorreto."

    # Verificação de histórico de deals
    assert len(operation_handler.account_data.history_deals) == 2, "O histórico de deals não foi atualizado corretamente."
    last_deal = operation_handler.account_data.history_deals[-1]
    assert last_deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "O último deal deveria ser do tipo BUY."
    assert last_deal.symbol == symbol, "O símbolo do último deal não corresponde ao esperado."
    assert last_deal.volume == initial_volume, "O volume do último deal não corresponde ao esperado."


def test_backtest_open_position_netting(account):
    """
    Testa a função __backtest_open_position para o modo Netting.

    Verifica se a função realiza a abertura e fechamento de posições corretamente em uma conta configurada para o modo Netting,
    onde apenas uma posição consolidada por símbolo é permitida.
    """

    # Configuração inicial da conta de backtest
    account.login_backtest(balance=5000, leverage=100)  # Inicializa o backtest com saldo de 5000 e alavancagem de 1:100
    account.backtest_account_data.simulated_spread = 4  # Define o spread simulado de 4 pontos

    # Parâmetros da posição inicial
    symbol = "EURUSD"  # Par de moedas negociado
    initial_price = 1.12345  # Preço de abertura da posição
    initial_volume = 1.0  # Volume inicial da posição (em lotes)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Data/hora do candle

    # Obtém o manipulador de operações a partir da conta de backtest
    operation_handler = account.backtest_account_data.operation

    # Mock de candle para simulação
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define o estado simulado do mercado
    operation_handler.last_candle = {symbol: mock_series}  # Define os últimos candles para o par de moedas
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato padrão de forex
    operation_handler.tick_sizes = {symbol: 1e-05}  # Incremento mínimo de preço (tick size)

    # Configuração para modo Netting
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_NETTING

    # Execução do teste: abertura de posição de compra no modo Netting
    result = __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=initial_volume,
        stop_price=1.12,  # Preço de stop-loss
        profit_price=1.13,  # Preço de take-profit
        comment="Teste de Netting Mode",
    )

    # Verificações de resultado
    assert result is True, "A função não retornou True para Netting mode."
    assert len(operation_handler.account_data.positions) == 1, "O modo Netting permitiu múltiplas posições no mesmo par de moedas."
    assert operation_handler.account_data.positions[0].type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY, "A posição deveria ser do tipo BUY."
    assert operation_handler.account_data.positions[0].symbol == symbol, "O símbolo da posição não corresponde ao esperado."

    # Teste de reversão de posição (venda na mesma moeda)
    result = __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=1.8,
        comment="Reversão de posição no Netting Mode",
    )

    assert result is True, "A função não retornou True para reversão no Netting mode."
    assert operation_handler.account_data.positions[0].type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL, "A posição não foi revertida para SELL corretamente."
    assert operation_handler.account_data.positions[0].volume == 0.8, "O volume da posição está incorreto após a reversão."

    # Verificação de histórico de deals
    assert len(operation_handler.account_data.history_deals) == 3, "O histórico de deals não foi atualizado corretamente após a reversão."
    last_deal = operation_handler.account_data.history_deals[-1]
    assert last_deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_SELL, "O último deal deveria ser do tipo SELL após a reversão."
    assert last_deal.symbol == symbol, "O símbolo do último deal não corresponde ao esperado."
    assert last_deal.volume == 1.8, "O volume do último deal não corresponde ao esperado."
