# 📊 Dashboard de Moedas Sociais – Edinheiro / PagDig

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Framework-orange)
![Plotly](https://img.shields.io/badge/Plotly-Interactive-green)

Dashboard interativo desenvolvido em **Streamlit** e **Plotly** para **visualização, análise e exploração de dados de desembolso comunitário e circulação de moedas sociais**, com integração à **API Edinheiro (DataHub)**.

A aplicação oferece **KPIs estratégicos**, **gráficos interativos**, **mapas geográficos** e **filtros dinâmicos**, permitindo análises exploratórias e apoio à tomada de decisão.


## Principais funcionalidades

- KPIs estratégicos:
  - Total investido (crédito emitido)
  - Moeda social em circulação
  - Gasto no comércio local
  - Saques e pagamentos de boletos
  - Beneficiados e comércios ativos
  - Grau de confiança na moeda
- Gráficos interativos (Plotly):
  - Barras (ranking de bancos comunitários)
  - Séries temporais (evolução mensal da moeda)
  - Áreas e comparativos por banco
- Mapa interativo:
  - Localização dos projetos por estado/município
- Filtros em cascata:
  - Data → Estado → Município → Banco Comunitário
- Integração com API REST (Edinheiro DataHub)
- Cache de dados para melhor performance
- Layout responsivo (wide)


## Estrutura do repositório

```
Dashboard/
├── dashpetro.py           # Código principal do dashboard (integração com API)
├── requirements.txt       # Dependências do projeto
├── .gitignore             # Arquivos ignorados pelo Git
└── README.md              # Documentação do projeto (este arquivo)
```

## Requisitos

- Python 3.8 ou superior
- pip
- Ambiente virtual (venv ou .venv)

Dependências principais (veja `requirements.txt`):

- streamlit
- pandas
- plotly
- numpy
- openpyxl
- python-dotenv
- requests

Instale todas as dependências com:

```bash
pip install -r requirements.txt
```

## Como executar (desenvolvimento)

1. Clone o repositório ou o seu fork:

```bash
git clone https://github.com/SEU-USUARIO/Dashboard.git
cd Dashboard
```

2. Crie e ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Instale as dependências (ver seção anterior).
4. Crie o arquivo `.streamlit/secrets.toml` com o conteúdo:

```toml
CLIENT_TOKEN = "seu_token_aqui"
```

5. Execute o dashboard:

```bash
streamlit run dashpetro.py
```

O Streamlit geralmente abre automaticamente em `http://localhost:8501`.


## 🔐 Configuração da API (Edinheiro)

A aplicação consome dados do endpoint:

`https://api.edinheiro.dev/datahub/metrics`

### Autenticação

A autenticação é realizada via **token de acesso**, enviado no header HTTP da requisição:
Client-Token: <seu_token_aqui>

### Gerenciamento do token

- O token **não é versionado no repositório**
- A aplicação lê o token a partir de:
  - `st.secrets["CLIENT_TOKEN"]` (Streamlit Cloud)
  - ou arquivo local `.streamlit/secrets.toml` (execução local)

### Execução no Streamlit Cloud

- O token deve ser configurado em **Settings → Secrets** do app
- Usuários finais **não precisam configurar nada**
- O dashboard funciona automaticamente ao acessar o link

### Execução local (desenvolvimento)

Crie o arquivo abaixo (não versionado):
`.streamlit/secrets.toml`
Com o conteúdo:

```toml
CLIENT_TOKEN = "seu_token_aqui"
```

Esse arquivo deve estar listado no .gitignore.

## Estrutura e origem dos dados

Os dados são obtidos a partir do endpoint "/metrics" da API do Edinheiro. Exemplo simplificado:
```json 
{
  "metrics": [
    {
      "MUNICIPIO": "Fortaleza",
      "ESTADO": "Ceará",
      "DATA": "2025-10",
      "BANCO_COMUNITARIO": "Banco X",
      "TOTAL_EMITIDO": 2200000,
      "MOEDA_SOCIAL_EM_CIRCULACAO": 700000,
      "SAQUES": 150000,
      "VALOR_GASTO_NO_COMERCIO_LOCAL": 900000
    }
  ]
}
```

Durante o carregamento, os dados passam por uma etapa de normalização e tratamento, resultando em um DataFrame com colunas como:
- data – período de referência (YYYY-MM)
- Estado – UF
- Município
- Banco Comunitário
- CRÉDITO TOTAL
- Moeda Circulação
- Saques
- Gasto Comércio Local
- Pgto Boletos
- Beneficiados
- Comércios Ativos
- Confiança Moeda (indicador calculado)

Toda a lógica de limpeza, conversão numérica e cálculos derivados está centralizada na função carregar_dados().


## 🎨 Configurações e personalizações rápidas

- Layout e título: `st.set_page_config()` no início do arquivo
- Cores dos gráficos: `color_discrete_sequence` (Plotly)
- Formatação monetária: Funções como `R$ {valor/1_000_000:.2f} Mi`
- Mapas: Ajustes em `px.scatter_mapbox()`


## Contribuição

Contribuições são bem-vindas. Para contribuir:

1. Abra uma issue descrevendo a melhoria ou bug.
2. Faça um fork do repositório e crie uma branch com a sua feature: `git checkout -b feature/nome-da-feature`.
3. Envie um pull request descrevendo as mudanças.


## 🛠 Manual para evolução do projeto

- Exportação de relatórios (PDF / Excel)
- Autenticação de usuários
- Monitoramento em tempo real
- Indicadores comparativos entre períodos
- Integração com outras instituições (ex: Banco Alegrias)
- Inclusão de novos gráficos a partir dos dados

## Licença
Este projeto está sob a licença MIT.
