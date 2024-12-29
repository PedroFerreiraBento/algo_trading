# Documentação para Testes de Estratégias de Trading

## Sumário
- [Documentação para Testes de Estratégias de Trading](#documentação-para-testes-de-estratégias-de-trading)
  - [Sumário](#sumário)
  - [Dados Necessários para Teste de Estratégia](#dados-necessários-para-teste-de-estratégia)
    - [Identificação](#identificação)
    - [Performance e Risco](#performance-e-risco)
    - [Amostra e Período de Estudo](#amostra-e-período-de-estudo)
    - [Dados e Indicadores](#dados-e-indicadores)
  - [Exemplo de Preenchimento](#exemplo-de-preenchimento)

---

## Dados Necessários para Teste de Estratégia

### Identificação
- **ID da Estratégia:**  
  Um identificador único para cada estratégia. Este ID é utilizado para rastrear, comparar e organizar os testes e os resultados da estratégia no banco de dados.

- **Criado em:**  
  Data de registro da estratégia na tabela, informando quando ela foi inserida no estudo.

- **Nome:**  
  Um nome descritivo e único para identificar a estratégia (e.g., *SMA Crossover (50/200)* ou *RSI Overbought Filter*).

- **Categoria:**  
  Tipo de estratégia de acordo com sua abordagem (e.g., *Trend Following*, *Mean Reversion*, *Momentum*, etc.).

- **Referências:**  
  Pode incluir:
  - IDs de outras estratégias das quais esta foi derivada.
  - Links externos para recursos ou dados relacionados (e.g., papers, artigos ou fontes de dados).

---

### Performance e Risco
- **Performance (%):**  
  Retorno percentual obtido com a estratégia durante o período de teste, calculado em relação ao capital inicial.

- **Drawdown (%):**  
  Máxima redução percentual do capital durante o período de teste, indicando o pior cenário enfrentado.

- **Relação Risco/Retorno:**  
  A razão entre o retorno obtido e o risco assumido. Pode ser calculada usando métricas como o índice de Sharpe ou razão simples entre risco e lucro.

---

### Amostra e Período de Estudo
- **Tamanho da Amostra:**  
  Número total de negociações (trades) realizadas durante o estudo, usado para medir a significância estatística dos resultados.

- **Início - Período do Estudo:**  
  Data inicial do período utilizado no estudo (e.g., *2020-01-01*).

- **Fim - Período do Estudo:**  
  Data final do período utilizado no estudo (e.g., *2023-01-01*).

---

### Dados e Indicadores
- **Base de Dados Utilizada:**  
  Fonte dos dados históricos utilizados para testar a estratégia (e.g., *Yahoo Finance*, *Bloomberg*, *Binance*).

- **Indicadores Usados:**  
  Lista dos indicadores técnicos usados na estratégia (e.g., *SMA*, *RSI*, *MACD*, *Bollinger Bands*). Deve ser especificado também o período ou configuração de cada indicador.

- **Intervalo de Tempo (Timeframe):**  
  O intervalo de tempo em que as análises foram realizadas, como:
  - *1min* (um minuto)
  - *1d* (diário)
  - *1w* (semanal)

- **Ativos:**  
  Lista dos ativos utilizados na estratégia (e.g., *AAPL*, *BTC/USD*, *EUR/USD*). Especificar o mercado em que foram testados (ações, forex, cripto, etc.).

---

## Exemplo de Preenchimento
```yaml
ID da Estratégia: 001  
Criado em: 2024-12-27  
Nome: SMA Crossover (50/200)  
Categoria: Trend Following  
Referências:  
  - Estratégia 000: SMA Crossover (20/50)  
  - Link: [Paper sobre SMA Crossover](https://example.com/sma-crossover-paper)  

Performance (%): 12.34  
Drawdown (%): -5.67  
Tamanho da Amostra: 150 trades  
Relação Risco/Retorno: 2.18  
Início - Período do Estudo: 2020-01-01  
Fim - Período do Estudo: 2023-01-01  
Base de Dados Utilizada: Yahoo Finance  
Indicadores Usados: SMA-50, SMA-200  
Intervalo de Tempo (Timeframe): 1d  
Ativos: AAPL  
