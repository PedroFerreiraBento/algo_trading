# Documentação do arquivo `backtest_results_EURUSD_operations.parquet`

Este documento descreve a estrutura, semântica e formas de uso do arquivo `scripts/strategies/000002-z_vig/backtest_results_EURUSD_operations.parquet`. Ele reúne os pares de operações (abertura/fechamento) gerados por `z_vig_backtest.py` e é posteriormente enriquecido por `features_generation.py` com uma janela de contexto de candles e features por operação.

## Origem dos dados

- **Backtest**: `scripts/strategies/000002-z_vig/z_vig_backtest.py`
  - Constrói pares de operações a partir de `history_deals` (MT5), agrupando por `position_id` e identificando o primeiro `IN` como abertura e `OUT/INOUT` como fechamento.
- **Enriquecimento**: `scripts/strategies/000002-z_vig/features_generation.py`
  - Recalcula todas as features por candle em `backtest_results_EURUSD_df5.parquet`.
  - Anexa, para cada operação, os últimos N candles (padrão 50, parametrizável) anteriores à abertura, incluindo o candle da abertura, com todas as features calculadas por candle, em `context_candles_json`.

## Esquema de colunas (nível operação)

As colunas abaixo existem por linha/registro da operação (um par open/close):

- **`position_id`** (int)
  - Identificador da posição no backtest.
- **`symbol`** (str)
  - Símbolo negociado, p.ex. `"EURUSD"`.
- **`open_time`** (datetime)
  - Instante de abertura (derivado do deal `IN`). Pode estar em milissegundos (epoch) originalmente; o pipeline padroniza para `datetime64[ns, UTC]`.
- **`close_time`** (datetime)
  - Instante de fechamento (deal `OUT`/`INOUT`), também padronizado para UTC.
- **`open_price`** (float)
  - Preço de abertura do deal `IN`.
- **`close_price`** (float)
  - Preço no deal de fechamento correspondente.
- **`direction`** (str)
  - `"BUY"` ou `"SELL"`, inferido do tipo do primeiro deal de entrada.
- **`volume`** (float)
  - Volume do fechamento (para consistência com MT5; pode ser replicado do deal de saída).
- **`reason`** (enum/str)
  - Razão do fechamento (p.ex. TP/SL/TimeExit), conforme `ENUM_DEAL_REASON`.
- **`total_profit`** (float)
  - Soma de `profit + swap + commission` do deal de fechamento (pode ser negativa/positiva).
- **`comment`** (str)
  - Comentário associado ao deal (ex.: `ZVIG-TURBO-LONG`).
- **`context_candles_json`** (str contendo JSON)
  - Janela temporal de N candles imediatamente anteriores ao `open_time`, incluindo o candle da abertura. Cada elemento do array contém `time` + todas as colunas do dataframe de 5 minutos com features (ver seção abaixo).

## `context_candles_json` (nível candle)

É um array JSON de objetos. Cada objeto representa um candle de 5m com todas as features disponíveis na época da abertura da operação. Estrutura geral:

```json
[
  {
    "time": "2025-01-01T10:35:00+00:00",
    "open": 1.10012,
    "high": 1.10045,
    "low": 1.09990,
    "close": 1.10030,
    "atr14": 0.00042,
    "atr_pct": 0.00038,
    "bbw20": 0.0015,
    "tr": 0.00060,
    "tr_med20": 0.00055,
    "z50": -0.85,
    "p_bbw": 0.62,
    "p_atr": 0.48,
    "kama50": 1.10005,
    "kama_slope": 0.00012,
    "roll_high": 1.10060,
    "roll_low": 1.09980,
    "p_bbw_prev": 0.61,
    "z_min3": -0.90,
    "z_max3": 0.40,
    "prev_high": 1.10040,
    "prev_low": 1.09985,
    "roll_high3": 1.10065,
    "roll_low3": 1.09978,
    "body": 0.00018
  }
]
```

- **`time`**: string ISO 8601 em UTC do instante do candle.
- Demais campos: todas as colunas existentes em `backtest_results_EURUSD_df5.parquet` após o processamento por `features_generation.py`.
- Valores `NaN`/não definidos são serializados como `null`.

### Lista de features por candle

Conforme `features_generation.py`/`z_vig_backtest.py`, o conjunto (sujeito a extensão futura) inclui:

- **OHLC**: `open`, `high`, `low`, `close`.
- **Volatilidade/Amplitude**:
  - `atr14` (ATR 14)
  - `atr_pct` (`atr14/close`)
  - `tr` (True Range do candle)
  - `tr_med20` (mediana de `tr` em 20)
- **Bandas/Compressão**:
  - `bbw20` (Bollinger Bandwidth, 20/2)
  - `p_bbw` (percent rank de `bbw20` em janela longa)
  - `p_bbw_prev` (lag de `p_bbw`)
- **Desvio/VWAP**:
  - `z50` (z-score do desvio do preço para o `session_vwap`, janela 50)
  - `z_min3`, `z_max3` (mínimo/máximo do z-score nas últimas 3 barras)
- **Tendência (1h alinhado em 5m)**:
  - `kama50` (KAMA 50 no 1h reamostrado em 5m)
  - `kama_slope` (diferença de 5 períodos do `kama50` no 1h)
- **Quebra/Triagem**:
  - `roll_high`, `roll_low` (máximo/mínimo rolling das últimas `thrust_lb` barras, com `shift(1)`)
  - `roll_high3`, `roll_low3` (máximo/mínimo rolling de 3 barras)
  - `prev_high`, `prev_low` (lag de uma barra)
  - `body` (|close - open|)

> Observação: `features_generation.py` garante preenchimentos de segurança, p.ex. `kama50` é preenchido com média móvel de 60 e `bfill()` quando necessário; `atr14`/`tr_med20` são `bfill()` para evitar lacunas no início do dataset.

## Parâmetro da janela de contexto

- Controlado por `PREV_CANDLES` no topo de `features_generation.py`.
- Padrão: `50`. Pode ser alterado via variável de ambiente `ZVIG_PREV_CANDLES`.
- A janela inclui o candle de entrada + os `N` candles imediatamente anteriores a ele, com busca por índice (candle mais recente ≤ `open_time`).

## Considerações de timezone e índices

- `open_time`/`close_time` são padronizados para `UTC`.
- O dataframe de 5m (`df5`) usa `DatetimeIndex` em UTC, e o alinhamento 1h→5m usa `merge_asof` com fallback de `ffill` quando necessário.
- `context_candles_json` sempre serializa `time` em ISO UTC.

## Como carregar e usar no Pandas

```python
import json
import pandas as pd

ops_path = r"scripts/strategies/000002-z_vig/backtest_results_EURUSD_operations.parquet"
ops = pd.read_parquet(ops_path)

# Converter open_time/close_time para datetime (se necessário)
ops["open_time"] = pd.to_datetime(ops["open_time"], utc=True, errors="coerce")
ops["close_time"] = pd.to_datetime(ops["close_time"], utc=True, errors="coerce")

# Exemplo: expandir o JSON de contexto da primeira operação
ctx = json.loads(ops.loc[0, "context_candles_json"])  # lista de dicts por candle
ctx_df = pd.DataFrame(ctx)
ctx_df["time"] = pd.to_datetime(ctx_df["time"], utc=True)
print(ctx_df.tail())
```

## Boas práticas e observações

- **Tamanho do arquivo**: `context_candles_json` pode aumentar significativamente o tamanho do parquet, pois armazena arrays por linha.
- **Formato alternativo**: se for necessário modelar os candles de contexto em formato normalizado (uma linha por candle por operação) ou em colunas achatadas (p.ex., `close_t-0`, `close_t-1`, ...), considere uma transformação posterior.
- **Validações**: ao consumir o JSON, trate `null` como ausente e converta tipos conforme necessário para modelos/treinamento.

## Versões e compatibilidade

- Gerado por `z_vig_backtest.py` e enriquecido por `features_generation.py` nesta base de código.
- Dependente de `pandas` e `numpy` (versões conforme ambiente Conda `backtestenv`).
