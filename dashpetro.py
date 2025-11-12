import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="Dashboard de Desembolso Comunitário",
    page_icon="💰",
    layout="wide"
)


css_final = """
<style>
    /* 1. Força o layout a usar 100% da largura da tela */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-top: 1rem;
    }
    /* 2. Centraliza o título principal */
    h3 {
        text-align: center;
        font-size: 2rem !important;
    }
    /* 3. Ajusta a fonte dos KPIs para um tamanho legível */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 1rem;
        white-space: normal !important;
        overflow-wrap: break-word;
    }
</style>
"""
st.markdown(css_final, unsafe_allow_html=True)


@st.cache_data
def carregar_dados_reais(caminho_arquivo="bancos_com_dados.xlsx"):
    try:
        df = pd.read_excel(caminho_arquivo, sheet_name="DADOS REAIS")
        df.columns = df.columns.str.strip()
        df['data'] = pd.to_datetime(df['data'])
        
        colunas_numericas = [
            'CRÉDITO TOTAL', 'Saques', 'Moeda social em circulação', 
            'VALOR GASTO NO COMÉRCIO LOCAL', 'PAGAMENTO DE BOLETOS/CONVÊNIOS',
            'Número de pessoas beneficiadas pelo legado', 'Uso do legado em Microcrédito',
            'Uso do legado em Projetos Sociais', 'NÚMERO DE COMÉRCIOS CREDENCIADOS ATIVOS',
            'NÚMERO DE COMÉRCIOS COM VENDA', 'GRAU DE CONFIANÇA NA MOEDA'
        ]
        for col in colunas_numericas:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        coordenadas = {
            "BA": (-12.9777, -38.5016), "RJ": (-22.9068, -43.1729), 
            "SP": (-23.5505, -46.6333), "MG": (-19.9167, -43.9345),
            "PE": (-8.0476, -34.8770), "CE": (-3.7172, -38.5433),
            "AM": (-3.1190, -60.0217), "PA": (-1.4558, -48.5024),
            "GO": (-16.6869, -49.2648), "RS": (-30.0346, -51.2177),
            "SC": (-27.5954, -48.5480), "PR": (-25.4284, -49.2733)
        }
        df['Latitude'] = df['Estado'].map(lambda uf: coordenadas.get(str(uf).upper(), (0,0))[0] + np.random.normal(0, 0.1))
        df['Longitude'] = df['Estado'].map(lambda uf: coordenadas.get(str(uf).upper(), (0,0))[1] + np.random.normal(0, 0.1))

        return df
    except Exception as e:
        st.error(f"Ocorreu um erro crítico ao carregar os dados: {e}")
        return pd.DataFrame()

# Carregar os dados
df = carregar_dados_reais()

if df.empty:
    st.stop()

# ===============================
# SIDEBAR COM FILTROS EM CASCATA
# ===============================
with st.sidebar:
    
    st.title("Filtros")

    min_data = df['data'].min().date()
    max_data = df['data'].max().date()
    data_inicio = st.date_input("Data Início", min_data, min_value=min_data, max_value=max_data)
    data_fim = st.date_input("Data Fim", max_data, min_value=min_data, max_value=max_data)

    df_periodo_filtrado = df[
        (df['data'].dt.date >= data_inicio) &
        (df['data'].dt.date <= data_fim)
    ]

    estados_disponiveis = ["Todos"] + sorted(list(df_periodo_filtrado["Estado"].unique()))
    estado_selecionado = st.selectbox("Estado", estados_disponiveis)

    if estado_selecionado == "Todos":
        df_estado_filtrado = df_periodo_filtrado
    else:
        df_estado_filtrado = df_periodo_filtrado[df_periodo_filtrado["Estado"] == estado_selecionado]
    
    municipios_disponiveis = ["Todos"] + sorted(list(df_estado_filtrado["Município"].unique()))
    municipio_selecionado = st.selectbox("Município", municipios_disponiveis)

    if municipio_selecionado == "Todos":
        df_municipio_filtrado = df_estado_filtrado
    else:
        df_municipio_filtrado = df_estado_filtrado[df_estado_filtrado["Município"] == municipio_selecionado]
        
    bancos_disponiveis = ["Todos"] + sorted(list(df_municipio_filtrado["Banco Comunitário"].unique()))
    banco_selecionado = st.selectbox("Banco Comunitário", bancos_disponiveis)

# ===============================
# APLICAÇÃO FINAL DO FILTRO
# ===============================
if banco_selecionado == "Todos":
    df_filtrado = df_municipio_filtrado
else:
    df_filtrado = df_municipio_filtrado[df_municipio_filtrado["Banco Comunitário"] == banco_selecionado]

# ===============================
# LAYOUT DO DASHBOARD PRINCIPAL
# ===============================
st.markdown("### PAGDIG | DESEMBOLSO COMUNITÁRIO")

# --- ESTRUTURA PRINCIPAL DO LAYOUT ---
col_esquerda, col_direita = st.columns([1.5, 2])

# --- CONTEÚDO DA COLUNA ESQUERDA ---
with col_esquerda:
    st.subheader("Crédito por Banco Comunitário")
    if not df_filtrado.empty:
        credito_por_banco = df_filtrado.groupby('Banco Comunitário')['CRÉDITO TOTAL'].sum().sort_values(ascending=True).reset_index()
        fig_iniciativa = px.bar(
            credito_por_banco, x='CRÉDITO TOTAL', y='Banco Comunitário', orientation='h',
            text=credito_por_banco['CRÉDITO TOTAL'].apply(lambda x: f'R$ {x/1_000_000:.2f} Mi'),
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_iniciativa.update_layout(showlegend=False, yaxis_title=None, xaxis_title=None, height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_iniciativa, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")

    st.subheader("Localização dos Projetos")
    if not df_filtrado.empty:
        fig_mapa = px.scatter_mapbox(
            df_filtrado, lat="Latitude", lon="Longitude", size="CRÉDITO TOTAL", color="Banco Comunitário",
            hover_name="Município", hover_data={"CRÉDITO TOTAL": ":.2f"},
            mapbox_style="open-street-map", zoom=3.5, center={"lat": -14.2350, "lon": -51.9253}, height=320
        )
        fig_mapa.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_mapa, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")

# --- CONTEÚDO DA COLUNA DIREITA ---
with col_direita:
    # --- KPIs ---
    if not df_filtrado.empty:
        total_investido = df_filtrado['CRÉDITO TOTAL'].sum()
        beneficiados = df_filtrado['Número de pessoas beneficiadas pelo legado'].sum()
        confianca_moeda_media = df_filtrado['GRAU DE CONFIANÇA NA MOEDA'].mean()
        gasto_comercio_local = df_filtrado['VALOR GASTO NO COMÉRCIO LOCAL'].sum()
        moeda_circulacao = df_filtrado['Moeda social em circulação'].sum()
        total_saques = df_filtrado['Saques'].sum()
        legado_microcredito = df_filtrado['Uso do legado em Microcrédito'].sum()
        comercios_ativos = df_filtrado['NÚMERO DE COMÉRCIOS CREDENCIADOS ATIVOS'].sum()
    else:
        total_investido = beneficiados = confianca_moeda_media = gasto_comercio_local = 0
        moeda_circulacao = total_saques = legado_microcredito = comercios_ativos = 0

    # --- MUDANÇA ESTRUTURAL DEFINITIVA: 2 COLUNAS PARA OS KPIs ---
    with st.container(border=True):
        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            kpi_col1.metric("Confiança na Moeda (Média)", f"{confianca_moeda_media:.2f}")
            kpi_col1.metric("Uso em Microcrédito", f"R$ {legado_microcredito/1000:.2f} k")
            kpi_col1.metric("Total Investido (Crédito)", f"R$ {total_investido/1_000_000:.2f} Mi")
            kpi_col1.metric("Gasto no Comércio Local", f"R$ {gasto_comercio_local/1_000_000:.2f} Mi")
        with kpi_col2:
            kpi_col2.metric("Comércios Credenciados Ativos", f"{comercios_ativos:,}")
            kpi_col2.metric("Beneficiados pelo Legado", f"{int(beneficiados)}")
            kpi_col2.metric("Moeda Social Circulação", f"R$ {moeda_circulacao/1_000_000:.2f} Mi")
            kpi_col2.metric("Saques", f"R$ {total_saques/1_000_000:.2f} Mi")
    
    # --- Gráfico de Evolução no Tempo ---
    st.subheader("Fundo Gerado no Período | Por Moeda")
    if not df_filtrado.empty:
        df_data = df_filtrado.groupby([pd.Grouper(key='data', freq='ME'), 'Banco Comunitário'])['Moeda social em circulação'].sum().reset_index()
        df_data['data'] = df_data['data'].dt.strftime('%b %Y')
        fig_data = px.bar(
            df_data, x='data', y='Moeda social em circulação', color='Banco Comunitário',
            labels={'Moeda social em circulação': 'Valor Gerado (R$)', 'data': 'Mês', 'Banco Comunitário': 'Moeda'},
        )
        fig_data.update_layout(yaxis_title=None, xaxis_title=None, height=350, legend_title_text='')
        st.plotly_chart(fig_data, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")