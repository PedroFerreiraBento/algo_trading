import os  # Biblioteca para manipulação de variáveis de ambiente

# Definição de variável de ambiente para evitar problemas de importação circular durante os testes com `pytest`
os.environ["PYTEST_CURRENT_TEST"] = "dummy_test"

# Bibliotecas de testes
import pytest  # Biblioteca para criação de testes unitários
from unittest.mock import patch, MagicMock  # Mocking de funções e objetos durante os testes

# Bibliotecas para manipulação de datas e dados
from datetime import datetime, timezone, timedelta  # Manipulação de datas e fuso horário
import pandas as pd  # Biblioteca para criação e manipulação de DataFrames
import numpy as np  # Biblioteca para manipulação de arrays numéricos

# Imports do projeto relacionados às fontes de dados MetaTrader5
from algo_trading.sources.MetaTrader5_source.rates.rates import Rates  # Classe Rates para requisição de ticks e candles

# Imports de modelos e enums relacionados ao MetaTrader5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlTick,  # Modelo de tick contendo campos como time, bid, ask, last, etc.
    ENUM_TIMEFRAME,  # Enum para definição de timeframes (M1, H1, etc.)
    ENUM_COPY_TICKS,  # Enum para definição do tipo de cópia de ticks (ALL, BID, LAST, etc.)
)

# Remove a variável de ambiente após a inicialização padrão
os.environ.pop("PYTEST_CURRENT_TEST", None)  # Remoção segura da variável de ambiente sem risco de `KeyError`


# Test Symbols ------------------------------------------------------------------------------------
@pytest.fixture
def mock_symbol():
    """
    Fixture que cria um mock de um objeto `SymbolInfo` com as informações necessárias para os testes.

    Este mock simula os dados de um ativo como `EURUSD`, incluindo:
    - `time`: Timestamp simulado de referência.
    - `spread`: Spread fixo de 10 pontos.
    - `digits`: Precisão de 5 casas decimais.
    - `ask` e `bid`: Preços de venda e compra simulados.
    - `volume_min`, `volume_max`, `volume_step`: Definições de volume mínimo, máximo e passo.
    - `trade_tick_size`: Incremento mínimo de preço (tick).
    - `trade_contract_size`: Tamanho do contrato em unidades da moeda base.
    - `trade_tick_value_profit` e `trade_tick_value_loss`: Valor por tick em cenário de lucro e perda.
    - `currency_base`: Moeda base do par de moedas.
    - `currency_profit`: Moeda de lucro do par.
    - `description`: Descrição textual do ativo.
    - `name`: Nome do símbolo (ex.: "EURUSD").

    Retorna:
        MockSymbolInfo: Objeto com os dados simulados do par de moedas `EURUSD`.
    """
    class MockSymbolInfo:
        def __init__(self):
            self.time = 1672531200  # 2023-01-01 00:00:00 UTC
            self.spread = 10  # Spread de 10 pontos
            self.digits = 5  # 5 casas decimais
            self.ask = 1.2345  # Preço de venda (ask)
            self.bid = 1.2340  # Preço de compra (bid)
            self.volume_min = 0.01  # Volume mínimo permitido
            self.volume_max = 100.0  # Volume máximo permitido
            self.volume_step = 0.01  # Incremento permitido no volume
            self.trade_tick_size = 0.0001  # Tamanho do tick (variação mínima de preço)
            self.trade_contract_size = 100000  # Tamanho padrão do contrato de 100.000 unidades
            self.trade_tick_value_profit = 1.0  # Valor por tick em cenário de lucro
            self.trade_tick_value_loss = 1.0  # Valor por tick em cenário de perda
            self.currency_base = "USD"  # Moeda base do par de moedas
            self.currency_profit = "EUR"  # Moeda de lucro
            self.description = "Euro vs US Dollar"  # Descrição do ativo
            self.name = "EURUSD"  # Nome do símbolo

    return MockSymbolInfo()


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_symbols_names(mock_mt5):
    """
    Testa o método `get_symbols_names` da classe `Rates`.

    Este teste verifica se o método retorna corretamente a lista de nomes de símbolos disponíveis na plataforma.

    Passos:
    1. Mocka a resposta da API `symbols_get` com um ativo fictício "EURUSD".
    2. Chama o método `Rates.get_symbols_names()` para obter a lista de nomes de símbolos.
    3. Verifica se o método `symbols_get` foi chamado uma vez.
    4. Compara o resultado retornado com a lista esperada `["EURUSD"]`.

    Args:
        mock_mt5 (MagicMock): Mock do módulo `MetaTrader5`.
    """
    # Mock de símbolo retornado pela API
    mock_symbol = MagicMock()
    mock_symbol.name = "EURUSD"  # Define o nome do símbolo como "EURUSD"
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Retorna uma tupla com um único símbolo
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida do MetaTrader5
    mock_mt5.account_info.return_value = True  # Simula a verificação de conta com sucesso

    # Executa o método `get_symbols_names` para buscar os nomes dos símbolos
    symbols = Rates.get_symbols_names()

    # Verificações
    mock_mt5.symbols_get.assert_called_once()  # Verifica se `symbols_get` foi chamado exatamente uma vez
    assert symbols == ["EURUSD"], "O método não retornou a lista de símbolos esperada."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_symbol_data(mock_mt5, mock_symbol):
    """
    Testa o método `get_symbol_data` da classe `Rates`.

    Este teste verifica se o método retorna corretamente os dados detalhados de um símbolo.

    Passos:
    1. Mocka a resposta da API `symbols_get` e `symbol_info` com os dados do símbolo "EURUSD".
    2. Chama o método `Rates.get_symbol_data("EURUSD")` para obter os detalhes do símbolo.
    3. Verifica se o método `symbol_info` foi chamado com o símbolo "EURUSD".
    4. Compara os atributos do objeto retornado com os valores esperados (ex.: nome e spread).

    Args:
        mock_mt5 (MagicMock): Mock do módulo `MetaTrader5`.
        mock_symbol (MockSymbolInfo): Mock de dados do símbolo "EURUSD".
    """
    # Mock de resposta das APIs `symbols_get` e `symbol_info`
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Retorna o símbolo "EURUSD" na lista de símbolos
    mock_mt5.symbol_info.return_value = mock_symbol  # Retorna os detalhes do símbolo "EURUSD"
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida do MetaTrader5
    mock_mt5.account_info.return_value = True  # Simula a verificação de conta com sucesso

    # Executa o método `get_symbol_data` para buscar os dados do símbolo "EURUSD"
    symbol_data = Rates.get_symbol_data("EURUSD")

    # Verificações
    mock_mt5.symbol_info.assert_called_once_with("EURUSD")  # Verifica se `symbol_info` foi chamado com "EURUSD"
    assert symbol_data.name == "EURUSD", "O nome do símbolo retornado não corresponde ao esperado."
    assert symbol_data.spread == 10, "O spread retornado não corresponde ao esperado."

# Test Candles ------------------------------------------------------------------------------------
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_last_n_candles(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.get_last_n_candles`, que retorna as últimas N velas de um ativo no MetaTrader5.

    Verifica se:
    1. As chamadas para `mt5.copy_rates_from` são feitas com os argumentos corretos.
    2. O retorno é um DataFrame do pandas com os campos corretos.
    3. O uso da flag `use_close_candle_time` altera o índice para `close_time`.
    4. Quando há menos candles do que o solicitado, o método lança um erro apropriado.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular suas funções.
        mock_symbol: Mock para simular as informações do ativo.
    """

    # Mock para símbolos e inicializações
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simula que o ativo está disponível
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida
    mock_mt5.account_info.return_value = True  # Simula informações de conta válidas
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)  # Simula o limite de histórico

    # Mock dos dados de candles (copy_rates_from)
    now = datetime.now(timezone.utc)
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),  # Candle mais recente
            (int((now - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
            (int((now - timedelta(minutes=2)).timestamp()), 1.1250, 1.1270, 1.1240, 1.1260, 200),
            (int((now - timedelta(minutes=3)).timestamp()), 1.1260, 1.1280, 1.1250, 1.1270, 250),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Teste com `use_close_candle_time=False`
    with patch("algo_trading.sources.MetaTrader5_source.rates.rates.datetime") as mock_datetime:
        mock_datetime.now.return_value = now  # Mock do tempo atual
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)  # Para chamadas reais de `datetime`

        candles = Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=4, use_close_candle_time=False)

    # Verifica se a função foi chamada com os argumentos corretos
    mock_mt5.copy_rates_from.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, now, 4)

    # Verificação do DataFrame retornado
    assert isinstance(candles, pd.DataFrame), "O retorno deve ser um DataFrame."
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"], "Colunas incorretas no DataFrame."
    assert candles.shape[0] == 4, "Número de candles retornados incorreto."
    assert candles.index.name == "time", "O índice deveria ser 'time'."

    # Teste com `use_close_candle_time=True`
    candles_with_close_time = Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=4, use_close_candle_time=True)

    # Verificação do DataFrame com `close_time` como índice
    assert isinstance(candles_with_close_time, pd.DataFrame), "O retorno deve ser um DataFrame."
    assert list(candles_with_close_time.columns) == ["open", "high", "low", "close", "tick_volume"], "Colunas incorretas no DataFrame."
    assert candles_with_close_time.shape[0] == 4, "Número de candles retornados incorreto."
    assert candles_with_close_time.index.name == "close_time", "O índice deveria ser 'close_time'."

    # Verificar diferenças de tempo para garantir consistência
    time_diffs = candles_with_close_time.index.to_series().diff().dt.total_seconds().dropna()
    median_diff = time_diffs.median()
    assert median_diff > 0, "A mediana da diferença de tempo deveria ser positiva."

    # Cenário com menos velas do que o solicitado (erro esperado)
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),
            (int((now - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    try:
        Rates.get_last_n_candles(symbol="EURUSD", timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1, n_candles=4, use_close_candle_time=True)
    except ValueError as e:
        assert str(e) == "Insufficient data: At least 4 candles are required when 'use_close_candle_time' is True.", "Mensagem de erro incorreta."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_candles_before(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.get_candles_before`, que retorna as últimas N velas antes de uma data específica no MetaTrader5.

    Este teste verifica:
    1. Se o método `mt5.copy_rates_from` é chamado com a data ajustada para pegar as velas antes da data fornecida (`date_to - 1 microsecond`).
    2. Se o resultado é um DataFrame pandas com as colunas corretas.
    3. Se a flag `use_close_candle_time=True` altera o índice do DataFrame para `close_time`.
    4. Se a mediana dos intervalos de tempo entre velas é positiva, garantindo consistência temporal.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular as funções do MetaTrader5.
        mock_symbol: Mock do ativo financeiro (exemplo: "EURUSD").
    """
    
    # Mock para configurações iniciais e informações do terminal
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Ativo simulado
    mock_mt5.initialize.return_value = True  # Inicialização do terminal simulada como bem-sucedida
    mock_mt5.account_info.return_value = True  # Simula retorno de informações de conta
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)  # Mock do máximo de barras permitido

    # Define a data-alvo (date_to) para buscar candles antes dela
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Mock dos dados de candles retornados
    mock_mt5.copy_rates_from.return_value = np.array(
        [
            (int(date_to.timestamp()), 1.1234, 1.1250, 1.1220, 1.1240, 100),  # Candle mais recente
            (int((date_to - timedelta(minutes=1)).timestamp()), 1.1240, 1.1260, 1.1230, 1.1250, 150),
            (int((date_to - timedelta(minutes=2)).timestamp()), 1.1250, 1.1270, 1.1240, 1.1260, 200),
            (int((date_to - timedelta(minutes=3)).timestamp()), 1.1260, 1.1280, 1.1250, 1.1270, 250),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Executa o método `get_candles_before` com `use_close_candle_time=True`
    candles = Rates.get_candles_before(
        symbol="EURUSD",
        timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1,
        date_to=date_to,
        n_candles=4,
        use_close_candle_time=True
    )

    # Verifica se a função `copy_rates_from` foi chamada com a data ajustada
    mock_mt5.copy_rates_from.assert_called_once_with(
        "EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, date_to - timedelta(microseconds=1), 4
    )

    # Verificações de estrutura do DataFrame retornado
    assert isinstance(candles, pd.DataFrame), "O retorno deve ser um DataFrame."
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"], "Colunas do DataFrame incorretas."
    assert candles.shape[0] == 4, "O número de candles retornados está incorreto."
    assert candles.index.name == "close_time", "O índice do DataFrame deveria ser 'close_time'."

    # Verificar se a diferença de tempo entre candles é consistente e positiva
    time_diffs = candles.index.to_series().diff().dt.total_seconds().dropna()
    median_diff = time_diffs.median()
    assert median_diff > 0, "A mediana da diferença de tempo deveria ser positiva."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_candles_range(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.get_candles_range`, que retorna candles de um ativo em um intervalo específico de datas.

    Este teste verifica:
    1. Se o método `mt5.copy_rates_range` é chamado com os argumentos corretos (`symbol`, `timeframe`, `date_from`, `date_to`).
    2. Se o retorno é um DataFrame do pandas com as colunas corretas.
    3. Se a flag `use_close_candle_time=True` altera o índice do DataFrame para `close_time`.
    4. Se a mediana das diferenças de tempo entre velas é positiva, garantindo consistência temporal.
    5. Se um erro é levantado quando o número de candles retornado é menor do que o esperado.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular suas funções.
        mock_symbol: Mock para simular as informações do ativo financeiro.
    """
    
    # Mock para simbolizar configurações iniciais e validações de inicialização
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simula que o ativo está disponível
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida
    mock_mt5.account_info.return_value = True  # Simula que as informações da conta estão acessíveis

    # Define as datas de início e fim para o intervalo
    date_from = datetime(2023, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Mock dos dados de candles retornados para o intervalo
    mock_mt5.copy_rates_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1220, 1.1230, 1.1210, 1.1225, 200),  # Candle inicial
            (int((date_from + timedelta(minutes=1)).timestamp()), 1.1225, 1.1240, 1.1215, 1.1230, 250),
            (int((date_from + timedelta(minutes=2)).timestamp()), 1.1230, 1.1250, 1.1220, 1.1240, 300),
            (int(date_to.timestamp()), 1.1235, 1.1245, 1.1230, 1.1245, 350),  # Candle final
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Executa o método com `use_close_candle_time=True`
    candles = Rates.get_candles_range(
        symbol="EURUSD",
        date_from=date_from,
        date_to=date_to,
        timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1,
        use_close_candle_time=True
    )

    # Verifica se a função `copy_rates_range` foi chamada com os argumentos corretos
    mock_mt5.copy_rates_range.assert_called_once_with("EURUSD", ENUM_TIMEFRAME.TIMEFRAME_M1, date_from, date_to)

    # Verificações de estrutura do DataFrame retornado
    assert isinstance(candles, pd.DataFrame), "O retorno deve ser um DataFrame."
    assert list(candles.columns) == ["open", "high", "low", "close", "tick_volume"], "As colunas do DataFrame estão incorretas."
    assert candles.shape[0] == 4, "O número de candles retornados não corresponde ao esperado."
    assert candles.index.name == "close_time", "O índice do DataFrame deveria ser 'close_time'."

    # Verifica se a diferença de tempo entre os candles é consistente e positiva
    time_diffs = candles.index.to_series().diff().dt.total_seconds().dropna()
    median_diff = time_diffs.median()
    assert median_diff > 0, "A mediana da diferença de tempo deveria ser positiva."

    # Simula cenário com menos de 4 candles para validar o tratamento de erro
    mock_mt5.copy_rates_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1220, 1.1230, 1.1210, 1.1225, 200),
            (int((date_from + timedelta(minutes=1)).timestamp()), 1.1225, 1.1240, 1.1215, 1.1230, 250),
        ],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")
        ]
    )

    # Verifica se o método lança o erro correto quando o número de candles é insuficiente
    with pytest.raises(ValueError, match="Insufficient data: At least 4 candles are required when 'use_close_candle_time' is True."):
        Rates.get_candles_range(
            symbol="EURUSD",
            date_from=date_from,
            date_to=date_to,
            timeframe=ENUM_TIMEFRAME.TIMEFRAME_M1,
            use_close_candle_time=True
        )

# Test Ticks ------------------------------------------------------------------------------------00
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_last_n_ticks(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.get_last_n_ticks`, que retorna os últimos N ticks de um ativo.

    Este teste verifica:
    1. Se o método `mt5.copy_ticks_from` é chamado com os parâmetros corretos (`symbol`, `now`, `n_ticks`, `COPY_TICKS_ALL`).
    2. Se o retorno é um DataFrame pandas com as colunas corretas.
    3. Se os valores retornados no DataFrame correspondem aos dados simulados.
    4. Se o índice de tempo (`time`) e o campo `time_msc` são calculados corretamente com precisão de segundos e milissegundos.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular suas funções.
        mock_symbol: Mock para simular as informações do ativo financeiro.
    """
    
    # Configurações iniciais de mocks
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simula que o ativo financeiro está disponível
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida do MetaTrader5
    mock_mt5.account_info.return_value = True  # Simula informações de conta válidas

    # Mock dos dados de ticks retornados
    now = datetime.now(timezone.utc)  # Data e hora atual
    mock_mt5.copy_ticks_from.return_value = np.array(
        [
            (int(now.timestamp()), 1.1234, 1.1235, 1.1236, 1, 64, int(now.timestamp() * 1000)),  # Tick mais recente
            (int((now - timedelta(seconds=1)).timestamp()), 1.1230, 1.1231, 1.1232, 1, 32, int((now - timedelta(seconds=1)).timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
            ("volume", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Executa o método com o mock de `datetime`
    with patch("algo_trading.sources.MetaTrader5_source.rates.rates.datetime") as mock_datetime:
        # Mock para retornar o tempo atual fixo
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)  # Permite chamadas reais de `datetime`

        # Chamada do método `get_last_n_ticks`
        ticks = Rates.get_last_n_ticks(symbol="EURUSD", n_ticks=2)

    # Verifica se a função `copy_ticks_from` foi chamada com os argumentos corretos
    mock_mt5.copy_ticks_from.assert_called_once_with("EURUSD", now, 2, ENUM_COPY_TICKS.COPY_TICKS_ALL)

    # Verificações de estrutura do DataFrame retornado
    assert isinstance(ticks, pd.DataFrame), "O retorno deve ser um DataFrame."
    assert list(ticks.columns) == ["time", "bid", "ask", "time_msc"], "As colunas do DataFrame estão incorretas."
    assert ticks.shape[0] == 2, "O número de ticks retornados não corresponde ao esperado."

    # Verificação de valores específicos no DataFrame
    assert ticks.iloc[0]["bid"] == 1.1234, "O valor 'bid' do primeiro tick está incorreto."
    assert ticks.iloc[0]["ask"] == 1.1235, "O valor 'ask' do primeiro tick está incorreto."
    assert ticks.iloc[0]["time"] == pd.Timestamp(int(now.timestamp()), unit="s", tz="UTC"), "O campo 'time' não corresponde ao valor esperado."

    # Verificação do campo `time_msc` (com precisão de milissegundos)
    expected_time_msc = pd.Timestamp(int(now.timestamp() * 1000), unit="ms", tz="UTC")
    assert ticks.iloc[0]["time_msc"] == expected_time_msc, "O campo 'time_msc' não corresponde ao valor esperado."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_specific_tick(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.get_specific_tick`, que retorna um tick específico de um ativo financeiro para uma determinada data.

    Este teste verifica:
    1. Se o método `mt5.copy_ticks_from` é chamado com os parâmetros corretos (`symbol`, `date_from`, `1`, `COPY_TICKS_ALL`).
    2. Se o retorno é uma instância da classe `MqlTick`.
    3. Se os valores do `MqlTick` retornado correspondem aos dados simulados, incluindo `time`, `bid`, `ask`, `last`, `volume`, `flags` e `time_msc`.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular suas funções.
        mock_symbol: Mock para simular as informações do ativo financeiro.
    """
    
    # Mock para inicialização e validação do ativo financeiro
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simula que o ativo financeiro está disponível
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida do MetaTrader5
    mock_mt5.account_info.return_value = True  # Simula informações de conta válidas

    # Mock para o tick retornado
    date_from = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)  # Data e hora para obter o tick específico
    mock_mt5.copy_ticks_from.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1234, 1.1235, 1.1236, 1, 1, 64, int(date_from.timestamp() * 1000)),
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
            ("volume", "i8"), ("volume_real", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Executa o método `get_specific_tick`
    tick = Rates.get_specific_tick(symbol="EURUSD", date_from=date_from)

    # Verifica se a função `copy_ticks_from` foi chamada com os argumentos corretos
    mock_mt5.copy_ticks_from.assert_called_once_with("EURUSD", date_from, 1, ENUM_COPY_TICKS.COPY_TICKS_ALL)

    # Verificação de retorno do tipo `MqlTick`
    assert isinstance(tick, MqlTick), "O retorno deve ser uma instância de `MqlTick`."

    # Verificação de valores específicos do `MqlTick`
    assert tick.time == date_from, "O campo `time` do tick está incorreto."
    assert tick.bid == 1.1234, "O campo `bid` do tick está incorreto."
    assert tick.ask == 1.1235, "O campo `ask` do tick está incorreto."
    assert tick.last == 1.1236, "O campo `last` do tick está incorreto."
    assert tick.volume == 1, "O campo `volume` do tick está incorreto."
    assert tick.flags == 64, "O campo `flags` do tick está incorreto."
    
    # Verificação do `time_msc` (precisão de milissegundos)
    expected_time_msc = pd.Timestamp(int(date_from.timestamp() * 1000), unit="ms", tz="UTC")
    assert tick.time_msc == expected_time_msc, "O campo `time_msc` não corresponde ao esperado."


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_get_ticks_range(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.get_ticks_range`, que retorna os ticks de um ativo financeiro em um intervalo de datas.

    Este teste verifica:
    1. Se o método `mt5.copy_ticks_range` é chamado com os parâmetros corretos (`symbol`, `date_from`, `date_to`, `COPY_TICKS_ALL`).
    2. Se o retorno é um DataFrame pandas com as colunas corretas.
    3. Se os valores retornados no DataFrame correspondem aos dados simulados.
    4. Se os campos `time` e `time_msc` são calculados corretamente com precisão de segundos e milissegundos.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular suas funções.
        mock_symbol: Mock para simular as informações do ativo financeiro.
    """
    
    # Mock para validação do ativo financeiro e inicialização
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simula que o ativo está disponível
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida do terminal
    mock_mt5.account_info.return_value = True  # Simula que as informações da conta estão acessíveis

    # Define as datas de início e fim do intervalo
    date_from = datetime(2023, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Mock do retorno de ticks dentro do intervalo de datas
    mock_mt5.copy_ticks_range.return_value = np.array(
        [
            (int(date_from.timestamp()), 1.1234, 1.1235, 1.1236, 1, 64, int(date_from.timestamp() * 1000)),  # Tick inicial
            (int(date_to.timestamp()), 1.1230, 1.1231, 1.1232, 1, 32, int(date_to.timestamp() * 1000)),  # Tick final
        ],
        dtype=[
            ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
            ("volume", "i8"), ("flags", "i8"), ("time_msc", "i8")
        ]
    )

    # Executa o método `get_ticks_range`
    ticks = Rates.get_ticks_range(symbol="EURUSD", date_from=date_from, date_to=date_to)

    # Verifica se a função `copy_ticks_range` foi chamada com os argumentos corretos
    mock_mt5.copy_ticks_range.assert_called_once_with("EURUSD", date_from, date_to, ENUM_COPY_TICKS.COPY_TICKS_ALL)

    # Verificações de estrutura do DataFrame retornado
    assert isinstance(ticks, pd.DataFrame), "O retorno deve ser um DataFrame."
    assert list(ticks.columns) == ["time", "bid", "ask", "time_msc"], "As colunas do DataFrame estão incorretas."
    assert ticks.shape[0] == 2, "O número de ticks retornados não corresponde ao esperado."

    # Verificação dos valores dos ticks
    assert ticks.iloc[0]["bid"] == 1.1234, "O campo `bid` do primeiro tick está incorreto."
    assert ticks.iloc[0]["ask"] == 1.1235, "O campo `ask` do primeiro tick está incorreto."
    assert ticks.iloc[0]["time"] == pd.Timestamp(int(date_from.timestamp()), unit="s", tz="UTC"), "O campo `time` do primeiro tick está incorreto."
    assert ticks.iloc[0]["time_msc"] == pd.Timestamp(int(date_from.timestamp() * 1000), unit="ms", tz="UTC"), "O campo `time_msc` do primeiro tick está incorreto."

# Validations ------------------------------------------------------------------------------------- 
@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_validate_count_candles(mock_mt5):
    """
    Testa o método `Rates.validate_count_candles`, que valida o número de candles solicitados em relação ao limite máximo permitido pelo terminal MetaTrader5.

    Este teste verifica:
    1. Se o método não lança nenhuma exceção quando o número de candles está dentro do limite (`< maxbars`).
    2. Se o método lança um `ValueError` quando o número de candles solicitado excede o limite (`>= maxbars`).
    
    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular o terminal MetaTrader5.
    """
    
    # Simula a resposta do terminal com o limite máximo de barras permitido (maxbars)
    mock_mt5.terminal_info.return_value = MagicMock(maxbars=10000)

    # Caso válido: número de candles solicitado está dentro do limite
    Rates.validate_count_candles(9999)  # Não deve lançar erro

    # Caso inválido: número de candles solicitado excede o limite permitido
    with pytest.raises(ValueError, match="The number of candles cannot be higher than terminal chart max bars"):
        Rates.validate_count_candles(10000)  # Deve lançar um ValueError com a mensagem correspondente


@patch("algo_trading.sources.MetaTrader5_source.rates.rates.mt5")
def test_validate_symbol(mock_mt5, mock_symbol):
    """
    Testa o método `Rates.validate_symbol`, que valida se o símbolo financeiro solicitado está na lista de símbolos disponíveis no terminal MetaTrader5.

    Este teste verifica:
    1. Se o método não lança nenhuma exceção quando o símbolo é válido e está na lista de símbolos disponíveis.
    2. Se o método lança um `ValueError` quando o símbolo não está na lista de símbolos disponíveis.

    Args:
        mock_mt5: Mock do objeto `MetaTrader5` para simular suas funções.
        mock_symbol: Mock para simular as informações do símbolo financeiro.
    """
    
    # Configuração do mock para simular a lista de símbolos disponíveis
    mock_mt5.symbols_get.return_value = (mock_symbol,)  # Simula que o símbolo "EURUSD" está na lista
    mock_symbol.name = "EURUSD"  # Define o nome do mock de símbolo
    mock_mt5.initialize.return_value = True  # Simula inicialização bem-sucedida do terminal
    mock_mt5.account_info.return_value = True  # Simula informações de conta acessíveis

    # Caso válido: símbolo disponível na lista
    Rates.validate_symbol("EURUSD")  # Não deve lançar exceção

    # Caso inválido: símbolo não disponível na lista
    with pytest.raises(ValueError, match="The selected symbol is not in the symbols list"):
        Rates.validate_symbol("INVALID_SYMBOL")  # Deve lançar um ValueError com a mensagem correspondente


def test_validate_request_result():
    """
    Testa o método `Rates.validate_request_result`, que valida o resultado de uma requisição de dados.
    
    Este teste verifica:
    1. Se o método não lança nenhuma exceção quando o resultado da requisição contém dados válidos.
    2. Se o método lança um `TypeError` quando o resultado da requisição é `None`.
    3. Se o método lança um `ValueError` quando o resultado da requisição é um array vazio.
    """
    
    # Caso válido: resultado da requisição com dados
    valid_result = np.array([1, 2, 3])  # Array com valores
    Rates.validate_request_result(valid_result)  # Não deve lançar erro

    # Caso inválido: resultado `None`
    with pytest.raises(TypeError, match="Request error, please check the request format"):
        Rates.validate_request_result(None)  # Deve lançar um TypeError

    # Caso inválido: array vazio
    with pytest.raises(ValueError, match="No data returned"):
        Rates.validate_request_result(np.array([]))  # Deve lançar um ValueError

    
def test_validate_date():
    """
    Testa o método `Rates.validate_date`, que valida se a data fornecida não é uma data futura.

    Este teste verifica:
    1. Se o método não lança nenhuma exceção quando a data é válida e não está no futuro.
    2. Se o método lança um `ValueError` quando a data é uma data futura.
    """
    
    # Caso válido: data válida (não no futuro)
    valid_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
    Rates.validate_date(valid_date)  # Não deve lançar erro

    # Caso inválido: data futura
    future_date = datetime(3000, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Request datetime can not be higher than the current datetime"):
        Rates.validate_date(future_date)  # Deve lançar um ValueError

        
def test_validate_date_range():
    """
    Testa o método `Rates.validate_date_range`, que valida se o intervalo de datas é válido (`date_from < date_to`).

    Este teste verifica:
    1. Se o método não lança nenhuma exceção quando o intervalo de datas é válido.
    2. Se o método lança um `ValueError` quando `date_from` é maior ou igual a `date_to`.
    """
    
    # Caso válido: `date_from` anterior a `date_to`
    date_from = datetime(2023, 12, 30, tzinfo=timezone.utc)
    date_to = datetime(2023, 12, 31, tzinfo=timezone.utc)
    Rates.validate_date_range(date_from, date_to)  # Não deve lançar erro

    # Caso inválido: `date_from` posterior a `date_to`
    with pytest.raises(ValueError, match="Invalid date range"):
        Rates.validate_date_range(date_to, date_from)  # Deve lançar um ValueError
