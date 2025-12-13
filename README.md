# 📊 Dashboard E-Commerce

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Framework-orange)
![Plotly](https://img.shields.io/badge/Plotly-Interactive-green)

Dashboard interativo desenvolvido em **Streamlit** e **Plotly** para **visualização, análise e exploração de dados de desembolso comunitário e circulação de moedas sociais**.

A aplicação oferece **KPIs estratégicos**, **gráficos avançados**, **mapas interativos** e **filtros dinâmicos**, permitindo análises profundas e geração rápida de insights para tomada de decisão..

## Principais funcionalidades

- KPIs com indicadores-chave (total investido, beneficiados, comércio local, confiança na moeda etc.)
- Gráficos interativos: barras, linhas, boxplot, sunburst, pie
- Mapa de pontos com Plotly + mapa interativo com Folium (clusters, popups)
- Filtros em cascata (data → estado → município → banco)
- Abas temáticas para análises detalhadas
- Tabela de dados interativa e exportável

## Estrutura do repositório

```
Dashboard-main/
├── dashpetro.py           # Código principal do dashboard 
├── bancos_com_dados.xlsx  # Arquivo de dados 
├── requirements.txt       # Dependências do projeto
└── README.md              # Este arquivo
```

## Requisitos

- Python 3.8 ou superior
- pip

Dependências principais (veja `requirements.txt`):

- streamlit
- pandas
- plotly
- numpy
- openpyxl


Instale todas as dependências com:

```bash
pip install -r requirements.txt
```

## Como executar (desenvolvimento)

1. Certifique-se de ter o arquivo de dados `bancos_com_dados.xlsx` na raiz do projeto.
2. Instale as dependências (ver seção anterior).
3. Execute o dashboard:

```bash
streamlit run dashpetro.py
```

O Streamlit geralmente abre automaticamente em `http://localhost:8501`.



## Formato esperado dos dados

O arquivo Excel deve conter uma aba chamada `DADOS REAIS` com colunas (exemplos):

- `data` (date)
- `Estado` (string, ex: RJ, SP)
- `Município` (string)
- `Banco Comunitário` (string)
- `CRÉDITO TOTAL` (numérico, R$)
- `Saques` (numérico, R$)
- `VALOR GASTO NO COMÉRCIO LOCAL` (numérico, R$)
- `Número de pessoas beneficiadas pelo legado` (inteiro)
- `NÚMERO DE COMÉRCIOS CREDENCIADOS ATIVOS` (inteiro)
- `GRAU DE CONFIANÇA NA MOEDA` (numérico)

Os scripts fazem conversões numéricas e tratamento de datas automaticamente, mas certifique-se de que os nomes das colunas correspondam exatamente.

## Configurações e personalizações rápidas

- Para alterar o título/ícone/lay-out: veja `st.set_page_config` no início de `dashpetro.py`.
- Para ajustar paleta de cores: edite `color_discrete_sequence` nos gráficos Plotly.
- Para alterar thresholds ou formatos monetários, procure por formatações com `f"R$ {valor/1_000_000:.2f} Mi"`.

## Testes rápidos

- Carregamento de dados:

```python
from dashpetro import carregar_dados_reais
df = carregar_dados_reais('bancos_com_dados.xlsx')
print(df.head())
```

- Executar o Streamlit localmente e navegar pelos filtros e abas.

## Contribuição

Contribuições são bem-vindas. Para contribuir:

1. Abra uma issue descrevendo a melhoria ou bug.
2. Faça um fork do repositório e crie uma branch com a sua feature: `git checkout -b feature/nome-da-feature`.
3. Envie um pull request descrevendo as mudanças.


## Badges, CI e futuras melhorias

- Recomenda-se adicionar badges de build (GitHub Actions), cobertura de testes e versão do Python.
- Sugestões de melhorias: exportar relatórios em PDF, integração com bases em tempo real, predição com ML e painel de autorização/usuários.

## Licença
Este projeto está sob a licença MIT.





