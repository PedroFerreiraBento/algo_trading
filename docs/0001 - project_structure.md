# Estrutura do Projeto - Forex Backtester

Este documento descreve a estrutura do projeto **Forex Backtester**, explicando o propósito de cada pasta e arquivo. A organização modular facilita a manutenção, expansão e reutilização de código.

---

## Estrutura Geral
```plaintext
forex-backtester/
│
├── analysis/               # Scripts de análise de desempenho
│   ├── metrics.py          # Cálculo de métricas como drawdown, Sharpe ratio
│   ├── visualizations.py   # Criação de gráficos e relatórios
│   └── report_generator.py # Gerador de relatórios em PDF/HTML
│
├── data/                   # Armazenamento de dados históricos e processados
│   ├── raw/                # Dados brutos baixados (ex: arquivos CSV)
│   ├── processed/          # Dados já pré-processados para análise
│   └── ticks/              # Dados de ticks, se disponíveis
│
├── logs/                   # Armazenamento de logs (operações e eventos)
│   └── backtest.log        # Log principal do backtest
│
├── docs/                   # Documentação do projeto
│   ├── project_structure.md # Estrutura do projeto (este conteúdo)
│   ├── api_usage.md         # Como usar APIs externas (ex.: Yahoo Finance)
│   ├── strategies_guide.md  # Guia de estratégias implementadas
│   └── analysis_guide.md    # Guia de análise e relatórios
│
├── notebooks/              # Jupyter notebooks para análise exploratória
│   └── data_exploration.ipynb
│
├── strategies/             # Implementação de estratégias
│   ├── moving_average.py   # Exemplo: Estratégia de média móvel
│   ├── rsi.py              # Exemplo: Estratégia baseada no RSI
│   └── base_strategy.py    # Classe base para estratégias
│
├── tests/                  # Scripts de teste para validar funções
│   ├── test_data.py        # Testes relacionados ao carregamento de dados
│   ├── test_strategies.py  # Testes para verificar estratégias
│   └── test_analysis.py    # Testes para métricas e visualizações
│
├── utils/                  # Funções auxiliares e genéricas
│   ├── file_manager.py     # Funções para manipulação de arquivos
│   ├── logger.py           # Configuração de logs
│   └── helpers.py         # Funções úteis gerais
│
├── requirements.txt        # Lista de dependências do projeto
├── config.py               # Configurações globais do projeto
├── main.py                 # Ponto de entrada principal para rodar o backtest
└── README.md               # Descrição do projeto e instruções
```

---

## Descrição das Pastas e Arquivos

### **1. `data/`**
- **Propósito:** Armazena dados históricos e pré-processados usados no backtest.
- **Subpastas:**
  - **`raw/`:** Dados brutos obtidos diretamente das APIs ou outras fontes.
  - **`processed/`:** Dados já limpos e estruturados para uso.
  - **`ticks/`:** Dados de ticks capturados durante as operações (se disponíveis).

### **2. `strategies/`**
- **Propósito:** Contém as implementações de estratégias de trading.
- **Arquivos:**
  - **`moving_average.py`:** Exemplo de estratégia baseada em médias móveis.
  - **`rsi.py`:** Estratégia utilizando o Indicador de Força Relativa (RSI).
  - **`base_strategy.py`:** Classe base para implementar novas estratégias.

### **3. `analysis/`**
- **Propósito:** Scripts para análise de desempenho e geração de relatórios.
- **Arquivos:**
  - **`metrics.py`:** Calcula métricas como drawdown e Sharpe ratio.
  - **`visualizations.py`:** Cria gráficos para análise visual.
  - **`report_generator.py`:** Gera relatórios detalhados em PDF/HTML.

### **4. `logs/`**
- **Propósito:** Armazena os logs de execução e eventos do projeto.
- **Arquivos:**
  - **`backtest.log`:** Registra operações, erros e outros eventos relevantes.

### **5. `docs/`**
- **Propósito:** Documentação completa do projeto.
- **Arquivos:**
  - **`project_structure.md`:** Este documento.
  - **`api_usage.md`:** Guia para usar APIs externas.
  - **`strategies_guide.md`:** Explicações das estratégias implementadas.
  - **`analysis_guide.md`:** Guia para interpretar as métricas e relatórios.

### **6. `tests/`**
- **Propósito:** Scripts para testar funcionalidades individuais do projeto.
- **Arquivos:**
  - **`test_data.py`:** Testa funções relacionadas ao carregamento de dados.
  - **`test_strategies.py`:** Valida a lógica das estratégias.
  - **`test_analysis.py`:** Testa os scripts de análise.

### **7. `notebooks/`**
- **Propósito:** Armazena notebooks Jupyter para análises exploratórias e desenvolvimento inicial.
- **Arquivos:**
  - **`data_exploration.ipynb`:** Notebook para análise exploratória de dados históricos.

### **8. `utils/`**
- **Propósito:** Funções auxiliares para operações comuns.
- **Arquivos:**
  - **`file_manager.py`:** Gerencia leitura e escrita de arquivos.
  - **`logger.py`:** Configura e gerencia logs do projeto.
  - **`helpers.py`:** Funções genéricas úteis.

### **9. Arquivos Principais**
- **`requirements.txt`:** Lista as dependências necessárias para rodar o projeto.
- **`config.py`:** Define configurações globais (ex.: caminhos, parâmetros padrão).
- **`main.py`:** Ponto de entrada principal para executar o backtest.
- **`README.md`:** Fornece uma visão geral do projeto e instruções de uso.

---

### **Recomendações de Manutenção**
- **Organização:** Mantenha cada pasta restrita ao seu propósito.
- **Atualização:** Sempre atualize a documentação em `docs/` ao adicionar ou alterar funcionalidades.
- **Padrões de Nomeação:** Use convenções consistentes para arquivos, funções e classes.

---

Se precisar de mais informações ou ajustes, consulte os outros documentos na pasta `docs/`.
