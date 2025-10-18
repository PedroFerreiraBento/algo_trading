Excelente — vamos montar um **conjunto de features** que “conversa” com o decision maker que definimos (survival de riscos concorrentes TP vs SL, com abstention e bandit). A ideia é ter:

1. **Features de snapshot** (calculadas no fechamento da barra do sinal, t₀) para estimar a probabilidade de **TP antes de SL**.
2. **Features dinâmicas** (t₀→t≤H) para atualizar o risco ao longo da operação — essenciais se você optar por hazards dependentes do tempo.

Abaixo estão as famílias de features, com definições **objetivas** (sem look-ahead), fórmulas claras e foco em criatividade útil (não “indicador de prateleira”).

---

## A) Volatilidade, dispersão e compressão (robustas a escala)

**A1. ATR% e percentis intrassessão**

* `ATR14_5m`, `ATR_pct = ATR14_5m / close_t0`.
* `p_atr`: rank/percentil de `ATR_pct` vs últimas *S* sessões (ex.: 20).
* Uso: regime de “movimento negociável” e interação com payoff em R.

**A2. Largura de bandas & compressão**

* `BBW20 = (BB_up(20,2) − BB_dn(20,2)) / close_t0`.
* `p_bbw`: percentil de `BBW20` vs 10 sessões.
* `KCw/BBw = Keltner_width(20,1.5·ATR) / Bollinger_width(20,2σ)`.
* Uso: detectar **pré-expansão** vs “chop”.

**A3. Volatilidades de OHLC (não convencionais)**

* **Parkinson** (HL): `σ²_P = (1/(4 ln2))·(ln(H/L))²` (média móvel).
* **Rogers–Satchell**: `σ²_RS = ln(H/C)·ln(H/O) + ln(L/C)·ln(L/O)` (média móvel).
* Uso: mede “true range” sem depender só do close-to-close.

**A4. Entropia e choppiness**

* **Shannon entropy** do vetor de retornos normalizados (janela N=20).
* **Choppiness Index** (objetivado com log das somas de TR).
* Uso: punir contextos de ruído lateral extremo.

---

## B) Estrutura da barra e do “N-bar pattern” (sem subjetividade)

**B1. Geometria da barra**

* `body = |close − open|`, `range = high − low`.
* `marubozu = body / range`.
* `upper_wick = high − max(close,open)`, `lower_wick = min(close,open) − low`.
* `wick_asym = (upper_wick − lower_wick) / range`.
* Uso: **thrust** e continuidade/absorção.

**B2. Thrust objetivo e breakout curto**

* `roll_high_N = max(high[-N..-1])`, `roll_low_N = min(low[-N..-1])` com *N*∈{2,3,5}.
* `break_strength = (close − roll_high_N)/ATR14` (long) ou simétrico (short).
* `follow_through = (high − close)/ATR14` (long) — mede “devolução” intrabar.
* Uso: qualidade do rompimento que gerou o sinal.

**B3. Contagem de compressão**

* `squeeze_count =` nº de barras nas últimas 10 com `BBW20 < p25`.
* `inside_ratio =` fração de **inside bars** em N=5.
* Uso: setups vindos de compressão genuína.

---

## C) VWAP/AVWAP e “distâncias funcionais”

**C1. Distâncias à VWAP**

* `dev_vwap = close − VWAP_sess`, `z_vwap = zscore(dev_vwap, 50)`.
* `q_vwap = quantile_rank(dev_vwap/ATR14, em 20 sessões)`.
* Uso: mean-reversion inteligente e filtros anti-excesso.

**C2. AVWAP do dia e do pre-market/abertura**

* `dist_avwap_day = (close − AVWAP_day)/ATR14`.
* `side_agreement = sign(close − AVWAP_day)` × lado do trade (±1).
* Uso: confirma pressão de fluxo do dia.

---

## D) Regime multi-timeframe e “pressão” de fundo

**D1. KAMA/EMA 1h (sem linhas “à mão”)**

* `kama1h`, `slope1h = Δ(kama1h, 5 barras 1h) / (ATR1h)`.
* `dist_kama1h = (close − kama1h)/ATR1h`.
* `mom1h = ROC3 (close_1h)`.
* Uso: viés direcional de fundo e **força** desse viés.

**D2. Proporção de vol MTF**

* `vol_ratio = ATR14_5m / ATR14_1h`.
* Uso: quando o micro está “nervoso” vs macro “parado” (ou vice-versa).

---

## E) Volume e pressão direcional simples (sem order book)

**E1. Spike e z-score de volume**

* `vol_spike = volume / median(volume, 50)`, `z_vol`.
* Uso: separa rompimentos “ocos” de movimentos auxiliados por fluxo.

**E2. OBV simplificado e correlação preço-volume**

* `signed_vol = ∑_{i=1..N} volume_i · sign(close_i − open_i)` (N=20).
* `corr_pv = corr(returns_1, volume_1) em janela N`.
* Uso: proxy de agressão direcional recente.

---

## F) Tempo e sazonalidade intraday (para o bandit e pro survival)

**F1. Hora do dia (cíclico)**

* `sin(hour/24·2π)`, `cos(hour/24·2π)`; e **one-hot** para blocos bons/ruins (identificados nos seus relatórios).
* `session_flags`: pré-abertura, Londres, NY, overlap.
* Uso: captura **micro-estrutura** recorrente sem “hard-codes”.

**F2. Dia da semana** (one-hot)

* Útil para penalizar quartas se forem consistentemente piores (como vimos).

---

## G) Geometria de risco (em R) — casa com o teu TP/SL/H

**G1. Distâncias normalizadas**

* `R = k_sl · ATR14` (você usa 1.2).
* `tp_R = (TP − entry)/R`, `sl_R = (entry − SL)/R` (devem bater com k’s definidos).
* `asymmetry = tp_R / sl_R` (geralmente = k_tp/k_sl).
* Uso: normaliza tudo em **R**; ótimo pro modelo prever **expectancy**.

**G2. Payoff ajustado a custos**

* `cost_R = (fees+slip)/R`, **dinâmica por ativo**.
* Uso: filtro de operabilidade real vs “edge de papel”.

---

## H) “Shapelets” e assinaturas de caminho pré-entrada (criativo e útil)

Converta os últimos **M** retornos (ex.: M=6–12 barras) em um vetor normalizado e meça a **distância** a 3–5 *shapelets* aprendidos offline (prototypes de “thrust”, “pullback raso”, “compressão”, “spike-reversão”).

* `dist_shapelet_j = ||r_{t−M+1:t} − proto_j||₂` (ou DTW simples).
* Uso: dar ao modelo “noção de forma” **sem** depender de nomes de candle.

---

## I) Features dinâmicas **durante** o trade (para hazards ao longo de t)

> Se você optar por hazards **dependentes do tempo**, atualize essas features a cada barra **até H**. Se o validator for só de *snapshot*, ignore esta seção.

**I1. Progresso para as barreiras (em R)**

* `mfe_R(t) = max_{τ≤t} (price_τ − entry)/R` (long) — excursão favorável.
* `mae_R(t) = max_{τ≤t} (entry − price_τ)/R` — excursão adversa.
* `dist_TP_R(t) = (TP − high_t)/R`, `dist_SL_R(t) = (low_t − SL)/R` (long).
* Uso: hazard cresce com **proximidade** às barreiras.

**I2. “Velocidade” e “aceleração” do trade**

* `runup_speed = Δ(mfe_R) / Δt`, `drawdown_speed = Δ(mae_R)/Δt`.
* `accel = Δ(runup_speed)` (ajuda muito survival).

**I3. Drift de volatilidade pós-entrada**

* `atr_ratio = ATR14_now / ATR14_entry`.
* `bbw_ratio = BBW_now / BBW_entry`.
* Uso: expansão pós-entrada aumenta chance de chegar em TP **mais cedo**.

**I4. Estado do stop**

* Flags: `breakeven_on`, `trailing_on`;
* `trail_gap_R = (price − SL_trailing)/R`.
* Uso: altera o **risco residual** do trade, afeta hazard de SL.

**I5. Micro regime flip**

* `sign(close_now − kama1h_now)` vs no t₀ — flag de **quebra de viés**.

**I6. Tempo decorrido (one-hot + contagem)**

* `t/H`, `one-hot(t)` para 1..H, porque a probabilidade de evento **não é homogênea** no tempo.

---

## J) Transformações e higiene (para não “se autoenganar”)

* **Rank/quantile**: aplique transformações por **janela rolling** (ex.: z-score, rank) para reduzir sensibilidade a escala/heteroscedasticidade.
* **Winsorize** extremos (p. ex. p1–p99) apenas em features, **nunca** no target.
* **Leakage guard**: tudo calculado em t₀ usa **somente** dados ≤ t₀ (e, no dinâmica, ≤ t). Nada de usar highs/lows futuros para normalizar.
* **Colinearidade**: clusterize correlações e mantenha 1–2 por grupo (ex.: ATR_pct, BBW e Parkinson vol são aparentadas; escolha a que explica melhor).
* **Monotonic constraints** (se usar GBM) para `cost_R` (pior custo ⇒ menor score) e `dist_TP_R`/`dist_SL_R` no survival (quanto mais perto do TP, maior hazard de TP, etc.).

---

## K) “Core set” inicial (se quiser começar enxuto)

**Snapshot (≈ 20 features):**
`ATR_pct, p_atr, BBW20, p_bbw, Parkinson_vol, RS_vol, marubozu, wick_asym, break_strength(N=3), follow_through, squeeze_count, inside_ratio, z_vwap, dist_avwap_day/ATR, dist_kama1h/ATR1h, slope1h/ATR1h, vol_spike, signed_vol(N=20), hour_sin/cos, weekday_1hot, cost_R, asymmetry (tp_R/sl_R).`

**Dinâmicas (se usar hazards):**
`mfe_R(t), mae_R(t), dist_TP_R(t), dist_SL_R(t), runup_speed, atr_ratio, trailing_on, breakeven_on, t/H`.

Depois, acrescente **shapelets** e `vol_ratio` conforme ganhar tração.

---

### Como isso ajuda o decision maker

* O **survival** precisa de covariáveis que expliquem **tempo-até-evento**: distâncias em R às barreiras, velocidade/aceleração do run-up, drift de volatilidade e o relógio intraday resolvem esse problema de forma **muito superior** ao binário clássico.
* O **abstention** (conformal) se beneficia de features com **boa calibração** (rank/z-score e custos explícitos ajudam muito).
* O **bandit contextual** usa hora/dia/volatilidade (`hour_sin/cos`, `weekday`, `p_atr`) para adaptar cortes e sizing sem tocar no núcleo.

Se quiser, eu transformo essa lista em um **esquema de colunas** (com nomes padronizados, unidades e janelas) e te entrego um checklist para validar “sem vazamento” antes do treino.
