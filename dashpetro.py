import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from dotenv import load_dotenv
import requests

# Carrega variáveis do .env
load_dotenv()

# CARREGAMENTO DO TOKEN
try:
    # Tenta pegar dos Secrets do Streamlit (Prioridade para Cloud)
    TOKEN = st.secrets["CLIENT_TOKEN"]
except Exception:
    # Se falhar (ambiente local sem secrets.toml), pega do .env
    TOKEN = os.getenv("CLIENT_TOKEN")

if not TOKEN:
    st.error("Erro Crítico: Token não encontrado. Verifique se o CLIENT_TOKEN está no .env ou nos Secrets.")
    st.stop()

# Constantes de Configuração
API_BASE_URL = "https://api.edinheiro.dev/datahub"
HEADERS = {"Client-Token": TOKEN}

# Mapeamentos Estáticos (Movidos para escopo global para performance/leitura)
MAPA_ESTADO_UF = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAPÁ": "AP", "AMAZONAS": "AM",
    "BAHIA": "BA", "CEARA": "CE", "CEARÁ": "CE", "DISTRITO FEDERAL": "DF",
    "ESPIRITO SANTO": "ES", "ESPÍRITO SANTO": "ES", "GOIAS": "GO", "GOIÁS": "GO",
    "MARANHAO": "MA", "MARANHÃO": "MA", "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG", "PARA": "PA", "PARÁ": "PA", "PARAIBA": "PB", "PARAÍBA": "PB",
    "PARANA": "PR", "PARANÁ": "PR", "PERNAMBUCO": "PE", "PIAUI": "PI", "PIAUÍ": "PI",
    "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS",
    "RONDONIA": "RO", "RONDÔNIA": "RO", "RORAIMA": "RR", "SANTA CATARINA": "SC",
    "SAO PAULO": "SP", "SÃO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO"
}

COORDENADAS_UF = {
    "AC": (-9.9754, -67.8249), "AL": (-9.5713, -36.7820), "AP": (0.9020, -52.0030),
    "AM": (-3.4168, -65.8561), "BA": (-12.5797, -41.7007), "CE": (-5.4984, -39.3206),
    "DF": (-15.7998, -47.8645), "ES": (-19.1834, -40.3089), "GO": (-15.9340, -49.8270),
    "MA": (-4.9609, -45.2744), "MT": (-12.6819, -56.9211), "MS": (-20.7722, -54.7863),
    "MG": (-18.5122, -44.5550), "PA": (-1.9981, -54.9306), "PB": (-7.2399, -36.7819),
    "PR": (-25.2521, -52.0215), "PE": (-8.8137, -36.9541), "PI": (-7.7183, -42.7289),
    "RJ": (-22.9099, -43.1729), "RN": (-5.4026, -36.9541), "RS": (-30.0346, -51.2177),
    "RO": (-11.5057, -63.5806), "RR": (2.7376, -62.0751), "SC": (-27.2423, -50.2189),
    "SP": (-23.5505, -46.6333), "SE": (-10.5741, -37.3857), "TO": (-10.1753, -48.2982)
}

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="Dashboard de Desembolso Comunitário",
    page_icon="💰",
    layout="wide"
)

# CSS Otimizado
st.markdown("""
<style>
    .main .block-container { max-width: 100%; padding: 1rem 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; }
    [data-testid="stMetricLabel"] p { font-size: 0.9rem; font-weight: 600; }
    h3 { text-align: center; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 2. FUNÇÕES AUXILIARES
# ===============================

def formatar_moeda(valor, prefixo="R$"):
    """Formata valores para Mi (Milhões) ou k (Milhares) de forma consistente."""
    if valor >= 1_000_000:
        return f"{prefixo} {valor/1_000_000:.2f} Mi"
    elif valor >= 1_000:
        return f"{prefixo} {valor/1_000:.2f} k"
    return f"{prefixo} {valor:.2f}"

@st.cache_data(ttl=3600)
def fetch_data(endpoint: str):
    """Busca dados na API com tratamento de timeout e erro."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)  
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.warning(f"A API demorou demais para responder em {endpoint}. Tente novamente mais tarde.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar com a API ({endpoint}): {e}")
        return None

def obter_lat_lon(estado):
    """Retorna lat/lon baseada na sigla ou nome do estado."""
    if not estado or pd.isna(estado): return 0, 0
    
    estado_upper = str(estado).strip().upper()
    uf = estado_upper if len(estado_upper) == 2 else MAPA_ESTADO_UF.get(estado_upper)
    
    # Retorna coordenadas base do estado + pequeno jitter determinístico (baseado no hash do nome) 
    # para evitar sobreposição exata sem usar random (que muda a cada refresh)
    base = COORDENADAS_UF.get(uf, (0, 0))
    if base == (0,0): return base
    
    # Opcional: Se quiser espalhar os pontos, usar hash do nome do banco
    return base

# ===============================
# 3. PROCESSAMENTO DE DADOS
# ===============================

@st.cache_data
def carregar_dados():
    data = fetch_data("/metrics")
    if not data: return pd.DataFrame()

    # Normaliza JSON (seja dict com chave 'metrics' ou lista direta)
    lista_metrics = data.get("metrics", []) if isinstance(data, dict) else data
    
    df = pd.DataFrame(lista_metrics)
    if df.empty: return df

    # Normalização de Nomes de Colunas (Strip + Upper)
    df.columns = df.columns.str.strip().str.upper()

    # Mapa de Renomeação (De -> Para)
    rename_map = {
        "MUNICIPIO": "Município", "ESTADO": "Estado", "DATA": "data",
        "BANCO_COMUNITARIO": "Banco Comunitário", "CEP": "CEP",
        "MOEDA_SOCIAL_EM_CIRCULACAO": "Moeda Circulação",
        "SAQUES": "Saques",
        "VALOR_GASTO_NO_COMERCIO_LOCAL": "Gasto Comércio Local",
        "VALOR_MOVIMENTADO_POR_BOLETOS": "Pgto Boletos",
        "NUMERO_DE_COMERCIOS_CREDENCIADOS_ATIVOS": "Comércios Ativos",
        "TOTAL_DE_CONTAS_ATIVAS": "Beneficiados",
        "TOTAL_EMITIDO": "Total Emitido",
        "Uso do legado em Microcrédito": "Microcrédito" # Caso venha da API
    }
    df.rename(columns=rename_map, inplace=True)

    # Garante colunas essenciais com valor 0 se não existirem
    cols_numericas = [
        "Total Emitido", "Saques", "Moeda Circulação", "Gasto Comércio Local", 
        "Pgto Boletos", "Beneficiados", "Comércios Ativos", "Microcrédito"
    ]
    for col in cols_numericas:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Criação de Colunas Calculadas
    df['CRÉDITO TOTAL'] = df['Total Emitido'] # Assumindo equivalência
    df['Confiança Moeda'] = np.where(df['Saques'] == 0, 0, df['Moeda Circulação'] / df['Saques'])
    
    # Tratamento de Data
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], format='%Y-%m', errors='coerce')
    
    # Tratamento Geográfico
    if 'Estado' in df.columns:
        # Aplica a função de coordenadas
        coords = df['Estado'].apply(obter_lat_lon)
        df['Latitude'] = coords.apply(lambda x: x[0])
        df['Longitude'] = coords.apply(lambda x: x[1])

        # Adiciona um pequeno "jitter" (ruído) apenas para visualização, 
        # para que múltiplos bancos na mesma cidade não fiquem exatamente um em cima do outro
        # Usando hash para ser determinístico (sempre o mesmo lugar)
        df['Latitude'] += df.index * 0.0001
        df['Longitude'] += df.index * 0.0001

    return df

# ===============================
# 4. APLICAÇÃO (DASHBOARD)
# ===============================

df = carregar_dados()

if df.empty:
    st.warning("Nenhum dado disponível para exibição.")
    st.stop()

# --- SIDEBAR (FILTROS) ---
with st.sidebar:
    st.title("Filtros")
    
    # Datas
    min_d, max_d = df['data'].min().date(), df['data'].max().date()
    d_inicio = st.date_input("Início", min_d, min_value=min_d, max_value=max_d)
    d_fim = st.date_input("Fim", max_d, min_value=min_d, max_value=max_d)
    
    mask_data = (df['data'].dt.date >= d_inicio) & (df['data'].dt.date <= d_fim)
    df_f = df[mask_data]

    # Filtros Hierárquicos (Estado -> Município -> Banco)
    def criar_filtro(label, coluna, dataframe):
        opcoes = ["Todos"] + sorted(dataframe[coluna].unique().astype(str))
        selecao = st.selectbox(label, opcoes)
        return dataframe if selecao == "Todos" else dataframe[dataframe[coluna] == selecao]

    df_f = criar_filtro("Estado", "Estado", df_f)
    df_f = criar_filtro("Município", "Município", df_f)
    df_f = criar_filtro("Banco Comunitário", "Banco Comunitário", df_f)


# ===============================
# 4. LAYOUT PRINCIPAL
# ===============================

st.markdown("### PAGDIG | DESEMBOLSO COMUNITÁRIO")

# ---------- KPIs (agregados) ----------
if df_f.empty:
    total_investido = beneficiados = confianca_moeda = 0
    gasto_comercio = moeda_circ = saques_totais = microcredito = comercios_ativos = 0
else:
    total_investido = df_f["CRÉDITO TOTAL"].sum()
    beneficiados = df_f["Beneficiados"].sum()
    confianca_moeda = df_f["Confiança Moeda"].mean()
    gasto_comercio = df_f["Gasto Comércio Local"].sum()
    moeda_circ = df_f["Moeda Circulação"].sum()
    saques_totais = df_f["Saques"].sum()
    microcredito = df_f["Microcrédito"].sum() if "Microcrédito" in df_f.columns else 0
    comercios_ativos = df_f["Comércios Ativos"].sum()

# ======================================
# LINHA 1 – BARRAS (ESQ) + KPIs (DIR)
# ======================================
linha1_esq, linha1_dir = st.columns([1.5, 2], gap="medium")

# ---- Coluna Esquerda: Top 15 Crédito por Banco ----
with linha1_esq:
    st.subheader("Crédito por Banco Comunitário (Top 15)")
    if not df_f.empty:
        df_bar = (
            df_f.groupby("Banco Comunitário", as_index=False)["CRÉDITO TOTAL"]
            .sum()
            .nlargest(15, "CRÉDITO TOTAL")
            .sort_values("CRÉDITO TOTAL")
        )

        fig_bar = px.bar(
            df_bar,
            x="CRÉDITO TOTAL",
            y="Banco Comunitário",
            orientation="h",
            text=df_bar["CRÉDITO TOTAL"].apply(lambda x: formatar_moeda(x)),
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_bar.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=320,
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig_bar.update_yaxes(automargin=True)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")

# ---- Coluna Direita: KPIs (voltar ao estilo antigo, 2 colunas) ----
with linha1_dir:
    with st.container(border=True):
        kpi1, kpi2 = st.columns(2)

        with kpi1:
            st.metric("Confiança na Moeda (Média)", f"{confianca_moeda:.2f}")
            st.metric("Uso em Microcrédito", formatar_moeda(microcredito))
            st.metric("Total Investido (Crédito)", formatar_moeda(total_investido))
            st.metric("Gasto no Comércio Local", formatar_moeda(gasto_comercio))

        with kpi2:
            st.metric("Comércios Credenciados Ativos", f"{int(comercios_ativos):,}")
            st.metric("Beneficiados pelo Legado", f"{int(beneficiados):,}")
            st.metric("Moeda Social em Circulação", formatar_moeda(moeda_circ))
            st.metric("Saques", formatar_moeda(saques_totais))

# ======================================
# LINHA 2 – MAPA (ESQ) + BARRAS TEMPORAIS (DIR)
# ======================================
linha2_esq, linha2_dir = st.columns([1.5, 2], gap="medium")

# ---- Coluna Esquerda: Mapa ----
with linha2_esq:
    st.subheader("Localização dos Projetos")
    if not df_f.empty and "Latitude" in df_f.columns:
        fig_map = px.scatter_mapbox(
            df_f,
            lat="Latitude",
            lon="Longitude",
            color="Banco Comunitário",
            hover_name="Município",
            hover_data={
                "Estado": True,
                "CRÉDITO TOTAL": ":.2f",
                "Latitude": False,
                "Longitude": False,
            },
            zoom=3.3,
            mapbox_style="open-street-map",
            height=320,
        )

        fig_map.update_layout(
            margin={"r":0, "t":0, "l":0, "b":0},
            legend=dict(
            orientation="h",
            y=-0.1,      # legenda embaixo
            x=0.5,
            xanchor="center"
            ),
        )

        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Sem dados para exibir no mapa.")


# ---- Coluna Direita: Fundo Gerado por Moeda  ----
with linha2_dir:
    st.subheader("Fundo Gerado no Período | Por Moeda")

    df_time = (
        df_f.groupby([pd.Grouper(key="data", freq="ME"), "Banco Comunitário"])["Moeda Circulação"]
        .sum()
        .reset_index()
    )

    if not df_time.empty:
        df_time["MesStr"] = df_time["data"].dt.strftime("%b %Y")

        fig_data = px.bar(
            df_time,
            x="MesStr",
            y="Moeda Circulação",
            color="Banco Comunitário",
            labels={
                "Moeda Circulação": "Valor Gerado (R$)",
                "MesStr": "Mês",
                "Banco Comunitário": "Moeda",
            },
        )
        fig_data.update_layout(
            yaxis_title=None,
            xaxis_title=None,
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            legend_title_text="",
        )
        st.plotly_chart(fig_data, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")
