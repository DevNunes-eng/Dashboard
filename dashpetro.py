import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
import os
import requests
import unicodedata
from geopy.geocoders import Nominatim

# Carrega as variáveis do arquivo .env para o ambiente
##load_dotenv("secret.env")

# ----------------------------------------------------
# CONFIGURAÇÃO DA API
# ----------------------------------------------------
# Endpoint base da API 
API_BASE_URL = "https://api.edinheiro.dev/datahub" 
# Chave da API
##token = os.getenv("CLIENT_TOKEN") 
token = st.secrets["CLIENT_TOKEN"]
HEADERS = {"Client-Token": token}

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
    
    /* 4. Estilo para os botões de navegação (tabs) */
    .tab-container {
        display: flex;
        background-color: transparent;
        padding: 0;
        margin-bottom: 1rem;
        gap: 8px;
    }
    
    /* Remove estilo padrão dos botões do Streamlit dentro das tabs */
    .stButton > button {
        border: 1px solid #404040 !important;
        background-color: #262730 !important;
        color: #ffffff !important;
        padding: 6px 20px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15) !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        background-color: #31333d !important;
        color: #ffffff !important;
        border-color: #505050 !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important;
    }
    
    /* Estilo para botão ativo/primário */
    .stButton > button[kind="primary"] {
        background-color: #1e1e2e !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: 2px solid #4a9eff !important;
        box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1e1e2e !important;
        border-color: #5dadff !important;
        box-shadow: 0 3px 10px rgba(74, 158, 255, 0.4) !important;
    }
</style>
"""
st.markdown(css_final, unsafe_allow_html=True)

# ----------------------------------------------------
# FUNÇÃO AUXILIAR PARA FORMATAÇÃO
# ----------------------------------------------------
def formatar_moeda(valor):
    """Formata valor numérico como moeda brasileira."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ----------------------------------------------------
# 2. DICIONÁRIO DE COORDENADAS DE MUNICÍPIOS
# ----------------------------------------------------

@st.cache_resource
def get_geolocator():
    """Instancia o geolocator com cache para evitar recriação."""
    return Nominatim(user_agent="dashpetro-dashboard", timeout=5)


@st.cache_data(ttl=604800)
def geocode_municipio_estado(municipio_norm, uf_norm):
    """Geocodifica município + UF (norm.) usando Nominatim, com cache de 7 dias."""
    if not municipio_norm or not uf_norm:
        return None
    geolocator = get_geolocator()
    try:
        query = f"{municipio_norm.title()}, {uf_norm}, Brasil"
        location = geolocator.geocode(
            query,
            language="pt",
            addressdetails=False,
            exactly_one=True,
            country_codes="br"
        )
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        return None
    return None

# ----------------------------------------------------
# 3. FUNÇÃO GENÉRICA DE BUSCA DA API
# ----------------------------------------------------

@st.cache_data(ttl=43200)  # Cache por 12 horas
def fetch_data(endpoint_path):
    """Função genérica e cacheada para buscar JSON de um endpoint específico."""
    url = f"{API_BASE_URL}{endpoint_path}"
    
    if not token:
        st.error("ERRO DE CONFIGURAÇÃO: Token da API não encontrado. Verifique seu arquivo .env.")
        return None

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        st.error(f"Erro HTTP ao acessar a API {endpoint_path} (Status: {response.status_code}): {http_err}")
        st.info("Verifique se o token é válido e se a API está no ar.")
        return None
    except requests.exceptions.RequestException as conn_err:
        st.error(f"Erro de Conexão com a API {endpoint_path}: {conn_err}")
        st.info(f"Verifique se o endereço '{url}' está acessível.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro crítico na busca dos dados de {endpoint_path}: {e}")
        return None


# ----------------------------------------------------
# 3. FUNÇÃO PRINCIPAL DE CARREGAMENTO E PROCESSAMENTO
# ----------------------------------------------------

@st.cache_data(ttl=43200)  # Cache por 12 horas
def carregar_dados_reais():
    """Busca dados do endpoint /metrics, processa e retorna o DataFrame final."""
    
    # CHAMA A API
    dados_json = fetch_data("/metrics") 
    
    if not dados_json:
        return pd.DataFrame()

    # Verifica estrutura do JSON
    if isinstance(dados_json, dict) and "metrics" in dados_json:
        lista_dados = dados_json["metrics"]
    elif isinstance(dados_json, list):
        lista_dados = dados_json
    else:
        st.error("Formato inesperado da API.")
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame.from_records(lista_dados)
        
        if df.empty:
            return pd.DataFrame()

    
        df.columns = df.columns.str.strip().str.upper()
        

        # Mapeamento
        df.rename(columns={
            "MUNICIPIO": "Município",
            "ESTADO": "Estado",
            "DATA": "data",          
            "BANCO_COMUNITARIO": "Banco Comunitário",
            "MOEDA_SOCIAL_EM_CIRCULACAO": "Moeda social em circulação",
            "SAQUES": "Saques",
            "VALOR_GASTO_NO_COMERCIO_LOCAL": "VALOR GASTO NO COMÉRCIO LOCAL",
            "VALOR_MOVIMENTADO_POR_BOLETOS": "PAGAMENTO DE BOLETOS/CONVÊNIOS",
            "NUMERO_DE_COMERCIOS_CREDENCIADOS_ATIVOS": "NÚMERO DE COMÉRCIOS CREDENCIADOS ATIVOS",
            "TOTAL_DE_CONTAS_ATIVAS": "Número de pessoas beneficiadas pelo legado",
            "TOTAL_EMITIDO": "Total Emitido",
            "ARRECADACAO_DE_TAXAS": "Arrecadação de Taxas",
            "NUMERO_DE_COMERCIOS_CREDENCIADOS": "Comércios Credenciados",
            "QUANTIDADE_DE_OPERACOES_REALIZADAS": "Operações Realizadas",
            "CEP": "CEP"
        }, inplace=True)
        
        # Tratamento de Data
        if 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data'], format='%Y-%m', errors='coerce') 
        else:
            # DEBUG EXTRA: Mostra quais colunas existem se falhar
            st.error(f"Coluna 'data' não encontrada. Colunas disponíveis: {df.columns.tolist()}")
            return pd.DataFrame() 
        
        # Tratamento de Colunas Faltantes
        if "CRÉDITO TOTAL" not in df.columns:
            if "Total Emitido" in df.columns:
                df["CRÉDITO TOTAL"] = df["Total Emitido"]
            else:
                df["CRÉDITO TOTAL"] = 0

        colunas_a_garantir = [
            'Uso do legado em Microcrédito', 'Uso do legado em Projetos Sociais',
            'NÚMERO DE COMÉRCIOS COM VENDA', 'GRAU DE CONFIANÇA NA MOEDA'
        ]
        for col in colunas_a_garantir:
            if col not in df.columns:
                df[col] = 0

        #  Conversão Numérica
        colunas_numericas = [
            'CRÉDITO TOTAL', 'Saques', 'Moeda social em circulação', 
            'VALOR GASTO NO COMÉRCIO LOCAL', 'PAGAMENTO DE BOLETOS/CONVÊNIOS',
            'Número de pessoas beneficiadas pelo legado', 
            'NÚMERO DE COMÉRCIOS CREDENCIADOS ATIVOS', 'Total Emitido'
        ]
        
        for col in colunas_numericas:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Cálculo da Confiança
        if 'Saques' in df.columns and 'Moeda social em circulação' in df.columns:
            df['GRAU DE CONFIANÇA NA MOEDA'] = np.where(
                df['Saques'] == 0,
                0, 
                df['Moeda social em circulação'] / df['Saques'] 
            )

        def normalizar_texto(texto):
            if pd.isna(texto):
                return ""
            texto = str(texto).strip().upper()
            texto = unicodedata.normalize("NFD", texto)
            texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
            return " ".join(texto.split())

        # Mapeia nomes completos de estados para UF
        mapa_estados = {
            "AC": "AC", "ACRE": "AC",
            "AL": "AL", "ALAGOAS": "AL",
            "AP": "AP", "AMAPA": "AP", "AMAPÁ": "AP",
            "AM": "AM", "AMAZONAS": "AM",
            "BA": "BA", "BAHIA": "BA",
            "CE": "CE", "CEARA": "CE", "CEARÁ": "CE",
            "DF": "DF", "DISTRITO FEDERAL": "DF",
            "ES": "ES", "ESPIRITO SANTO": "ES", "ESPÍRITO SANTO": "ES",
            "GO": "GO", "GOIAS": "GO", "GOIÁS": "GO",
            "MA": "MA", "MARANHAO": "MA", "MARANHÃO": "MA",
            "MT": "MT", "MATO GROSSO": "MT",
            "MS": "MS", "MATO GROSSO DO SUL": "MS",
            "MG": "MG", "MINAS GERAIS": "MG",
            "PA": "PA", "PARA": "PA", "PARÁ": "PA",
            "PB": "PB", "PARAIBA": "PB", "PARAÍBA": "PB",
            "PR": "PR", "PARANA": "PR", "PARANÁ": "PR",
            "PE": "PE", "PERNAMBUCO": "PE",
            "PI": "PI", "PIAUI": "PI", "PIAUÍ": "PI",
            "RJ": "RJ", "RIO DE JANEIRO": "RJ",
            "RN": "RN", "RIO GRANDE DO NORTE": "RN",
            "RS": "RS", "RIO GRANDE DO SUL": "RS",
            "RO": "RO", "RONDONIA": "RO", "RONDÔNIA": "RO",
            "RR": "RR", "RORAIMA": "RR",
            "SC": "SC", "SANTA CATARINA": "SC",
            "SP": "SP", "SAO PAULO": "SP", "SÃO PAULO": "SP",
            "SE": "SE", "SERGIPE": "SE",
            "TO": "TO", "TOCANTINS": "TO",
        }

        # Coordenadas de fallback por estado (capital)
        coordenadas_estados = {
             "BA": (-12.9714, -38.5014), "RJ": (-22.9068, -43.1729), 
             "SP": (-23.5505, -46.6333), "MG": (-19.9167, -43.9345),
             "PE": (-8.0476, -34.8770), "CE": (-3.7172, -38.5433),
             "AM": (-3.1190, -60.0217), "PA": (-1.4558, -48.5024),
             "GO": (-16.6869, -49.2648), "RS": (-30.0346, -51.2177),
             "SC": (-27.5954, -48.5480), "PR": (-25.4284, -49.2733),
             "AL": (-9.6498, -35.7089), "AC": (-9.9747, -67.8100),
             "AP": (0.0345, -51.0694), "DF": (-15.8267, -47.9218),
             "ES": (-20.3155, -40.3128), "MA": (-2.5307, -44.3068),
             "MT": (-15.6010, -56.0974), "MS": (-20.4697, -54.6201),
             "PB": (-7.1153, -34.8610), "PI": (-5.0892, -42.8019),
             "RN": (-5.7945, -35.2110), "RO": (-8.7619, -63.9039),
             "RR": (2.8190, -60.6714), "SE": (-10.9472, -37.0731),
             "TO": (-10.1840, -48.3336)
        }

        # Geocodifica TODOS os registros com valor positivo de circulação
        if 'Município' in df.columns and 'Estado' in df.columns:
            # Cria colunas normalizadas
            df['Município_norm'] = df['Município'].apply(normalizar_texto)
            df['Estado_norm'] = df['Estado'].apply(normalizar_texto)
            df['UF'] = df['Estado_norm'].apply(lambda e: mapa_estados.get(e, e if len(e) == 2 else ""))

            # Identifica pares únicos que precisam de geocodificação
            pares_unicos = df[df['Moeda social em circulação'] > 0][['Município', 'Estado', 'Município_norm', 'Estado_norm', 'UF']].drop_duplicates()

            coords_map = {}
            for _, row_geo in pares_unicos.iterrows():
                municipio_norm = row_geo['Município_norm']
                estado_norm = row_geo['Estado_norm']
                uf_val = row_geo['UF']

                # Tenta geocodificar município + UF
                coord = geocode_municipio_estado(municipio_norm, uf_val or estado_norm)

                # Fallback: capital do estado
                if coord is None:
                    uf_cap = uf_val if len(uf_val) == 2 else mapa_estados.get(estado_norm, "")
                    coord = coordenadas_estados.get(uf_cap)

                coords_map[(row_geo['Município'], row_geo['Estado'])] = coord if coord else (0, 0)

            # Atribui coordenadas para TODOS os registros, independente do valor
            def atribuir_coord(row):
                # Primeiro tenta buscar coordenadas do mapa de geocodificação
                coord = coords_map.get((row['Município'], row['Estado']))
                
                # Se não encontrou, tenta usar capital do estado como fallback final
                if coord is None or coord == (0, 0):
                    uf = mapa_estados.get(normalizar_texto(row['Estado']), normalizar_texto(row['Estado']))
                    coord = coordenadas_estados.get(uf, (0, 0))
                
                return pd.Series({'Latitude': coord[0], 'Longitude': coord[1]})

            df[['Latitude', 'Longitude']] = df.apply(atribuir_coord, axis=1)
            
            # Remove colunas auxiliares
            df.drop(['Município_norm', 'Estado_norm', 'UF'], axis=1, inplace=True)

        return df
    
    except Exception as e:
        st.error(f"Ocorreu um erro crítico no processamento dos dados: {e}")
        return pd.DataFrame()
    

# ----------------------------------------------------
# CARREGAMENTO INICIAL (DEVE SER FEITO ANTES DA SIDEBAR)
# ----------------------------------------------------

# Chama a função principal para obter o DataFrame, aproveitando o cache
df = carregar_dados_reais()

# Se o DF estiver vazio devido a erro na API, para a execução
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

    # ⬇️ ADICIONE ISTO - Botão no rodapé da sidebar:
    st.divider()
    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        if st.button("🔄 Atualizar Dados", key="btn_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_btn2:
        st.caption(f"🕐 {datetime.now().strftime('%H:%M')}")
    
    # Debug de Geocodificação
    with st.expander("🔍 Debug de Geocodificação"):
        if not df.empty:
            df_debug = df[df['Moeda social em circulação'] > 0][['Município', 'Estado', 'Moeda social em circulação', 'Latitude', 'Longitude']].drop_duplicates()
            df_debug = df_debug.sort_values('Moeda social em circulação', ascending=False)
            df_debug['Status'] = df_debug.apply(
                lambda row: '✅ OK' if row['Latitude'] != 0 and row['Longitude'] != 0 else '❌ Sem coord', 
                axis=1
            )
            st.dataframe(df_debug, use_container_width=True, height=300)
            
            total_com_coord = len(df_debug[df_debug['Latitude'] != 0])
            total_sem_coord = len(df_debug[df_debug['Latitude'] == 0])
            st.caption(f"✅ Com coordenadas: {total_com_coord} | ❌ Sem coordenadas: {total_sem_coord}")


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
st.markdown("### DESEMBOLSO COMUNITÁRIO 💵")

# ===============================
# SISTEMA DE NAVEGAÇÃO POR PÁGINAS
# ===============================
# Inicializa o estado da página se não existir
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1

# Botões de navegação estilo tabs
st.markdown('<div class="tab-container">', unsafe_allow_html=True)
col_btn1, col_btn2, col_btn3, col_spacer = st.columns([1.5, 1.5, 1.5, 5.5])
with col_btn1:
    if st.button("🪙 Indicadores Gerais", key="btn_page1", use_container_width=True, type="primary" if st.session_state.pagina_atual == 1 else "secondary"):
        st.session_state.pagina_atual = 1
        st.rerun()
with col_btn2:
    if st.button("📊 Visualizações Detalhadas", key="btn_page2", use_container_width=True, type="primary" if st.session_state.pagina_atual == 2 else "secondary"):
        st.session_state.pagina_atual = 2
        st.rerun()
with col_btn3:
    if st.button("📈 Análises Complementares", key="btn_page3", use_container_width=True, type="primary" if st.session_state.pagina_atual == 3 else "secondary"):
        st.session_state.pagina_atual = 3
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ===============================
# RENDERIZAÇÃO DA PÁGINA SELECIONADA
# ===============================
if st.session_state.pagina_atual == 1:
    # --- PÁGINA 1: INDICADORES GERAIS ---
    
    # Calcula KPIs
    if df_filtrado.empty:
        total_investido = beneficiados = confianca_moeda = 0
        gasto_comercio = moeda_circ = saques_totais = microcredito = comercios_ativos = 0
    else:
        total_investido = df_filtrado["CRÉDITO TOTAL"].sum()
        beneficiados = df_filtrado["Número de pessoas beneficiadas pelo legado"].sum()
        confianca_moeda = df_filtrado["GRAU DE CONFIANÇA NA MOEDA"].mean()
        gasto_comercio = df_filtrado["VALOR GASTO NO COMÉRCIO LOCAL"].sum()
        moeda_circ = df_filtrado["Moeda social em circulação"].sum()
        saques_totais = df_filtrado["Saques"].sum()
        microcredito = df_filtrado["Uso do legado em Microcrédito"].sum() if "Uso do legado em Microcrédito" in df_filtrado.columns else 0
        comercios_ativos = df_filtrado["NÚMERO DE COMÉRCIOS CREDENCIADOS ATIVOS"].sum()
    
    # ======================================
    # LINHA 1 – BARRAS (ESQ) + KPIs (DIR)
    # ======================================
    linha1_esq, linha1_dir = st.columns([1.5, 2], gap="medium")
    
    # ---- Coluna Esquerda: Top 15 Crédito por Banco ----
    with linha1_esq:
        st.subheader("Crédito por Banco Comunitário (Top 15)")
        if not df_filtrado.empty:
            df_bar = (
                df_filtrado.groupby("Banco Comunitário", as_index=False)["CRÉDITO TOTAL"]
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
    
    # ---- Coluna Direita: KPIs (2 colunas) ----
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
        if not df_filtrado.empty and "Latitude" in df_filtrado.columns:
            fig_map = px.scatter_mapbox(
                df_filtrado,
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
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                legend=dict(
                    orientation="h",
                    y=-0.1,
                    x=0.5,
                    xanchor="center"
                ),
            )
    
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Sem dados para exibir no mapa.")
    
    # ---- Coluna Direita: Fundo Gerado por Moeda ----
    with linha2_dir:
        st.subheader("Fundo Gerado no Período | Por Moeda")
    
        df_time = (
            df_filtrado.groupby([pd.Grouper(key="data", freq="ME"), "Banco Comunitário"])["Moeda social em circulação"]
            .sum()
            .reset_index()
        )
    
        if not df_time.empty:
            df_time["MesStr"] = df_time["data"].dt.strftime("%b %Y")
    
            fig_data = px.bar(
                df_time,
                x="MesStr",
                y="Moeda social em circulação",
                color="Banco Comunitário",
                labels={
                    "Moeda social em circulação": "Valor Gerado (R$)",
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

elif st.session_state.pagina_atual == 2:
    # --- PÁGINA 2: VISUALIZAÇÕES DETALHADAS ---
    # --- ESTRUTURA PRINCIPAL DO LAYOUT ---
    col_esquerda, col_direita = st.columns([1, 1])

    # --- CONTEÚDO DA COLUNA ESQUERDA ---
    with col_esquerda:
        st.subheader("Top 10 Bancos Comunitários por Moeda Social em Circulação")
        if not df_filtrado.empty:
            # Agrupa por banco e soma a moeda em circulação
            top10_bancos = (
                df_filtrado.groupby("Banco Comunitário")["Moeda social em circulação"]
                .sum()
                .sort_values(ascending=True)  # Ordem crescente para barras horizontais
                .tail(10)  # Top 10
            )
            
            # Importa plotly.graph_objects
            import plotly.graph_objects as go
            
            # Cria o gráfico de barras horizontais
            fig_top10 = go.Figure()
            
            fig_top10.add_trace(go.Bar(
                x=top10_bancos.values,
                y=top10_bancos.index,
                orientation='h',
                marker=dict(
                    color=['#003f5c', '#2f4b7c', '#665191', '#a05195', '#d45087', 
                        '#f95d6a', '#ff7c43', '#ffa600', '#1f77b4', '#003f5c'],
                    line=dict(color='rgba(255, 255, 255, 0.3)', width=1)
                ),
                text=[f'R$ {val:,.0f}' for val in top10_bancos.values],
                textposition='outside',
                textfont=dict(size=12),
                hovertemplate='<b>%{y}</b><br>Moeda em Circulação: R$ %{x:,.2f}<extra></extra>'
            ))
            
            fig_top10.update_layout(
                xaxis_title="Moeda em Circulação (R$)",
                yaxis_title="",
                height=350,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11),
                margin=dict(l=200, r=80, t=20, b=50),
                xaxis=dict(
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    showgrid=True,
                    zeroline=False,
                    range=[0, 38000000]
                ),
                yaxis=dict(
                    showgrid=False
                )
            )
            
            st.plotly_chart(fig_top10, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    # --- CONTEÚDO DA COLUNA DIREITA ---
    with col_direita:
        # --- MAPA DE CALOR DE DENSIDADE DA MOEDA EM CIRCULAÇÃO ---
        st.subheader("Densidade da Moeda em Circulação")
        if not df_filtrado.empty and 'Latitude' in df_filtrado.columns and 'Longitude' in df_filtrado.columns:
            # Agrupa por município/estado para evitar duplicatas e somar valores
            df_map = df_filtrado[
                (df_filtrado['Latitude'] != 0) & 
                (df_filtrado['Longitude'] != 0) &
                (df_filtrado['Moeda social em circulação'] > 0)
            ].groupby(['Município', 'Estado', 'Latitude', 'Longitude'], as_index=False).agg({
                'Moeda social em circulação': 'sum',
                'Banco Comunitário': 'first'
            })
            
            if not df_map.empty:
                # Normaliza o tamanho em escala logarítmica para melhor visualização
                import numpy as np
                df_map['size_normalized'] = np.log1p(df_map['Moeda social em circulação']) * 3
                
                # Cria o mapa de pontos individuais
                fig_heatmap = px.scatter_mapbox(
                    df_map,
                    lat='Latitude',
                    lon='Longitude',
                    size='size_normalized',
                    color='Moeda social em circulação',
                    center=dict(lat=-14.2350, lon=-51.9253),
                    zoom=3.8,
                    mapbox_style="carto-positron",
                    color_continuous_scale="Turbo",
                    size_max=25,
                    opacity=0.7,
                    hover_name='Município',
                    hover_data={
                        'Estado': True,
                        'Banco Comunitário': True,
                        'Moeda social em circulação': ':,.2f',
                        'Latitude': False,
                        'Longitude': False,
                        'size_normalized': False
                    },
                    labels={'Moeda social em circulação': 'Moeda (R$)'}
                )
                
                fig_heatmap.update_layout(
                    height=350,
                    margin=dict(l=0, r=0, t=0, b=0),
                    coloraxis_colorbar=dict(
                        title="Circulação<br>(R$)",
                        thicknessmode="pixels",
                        thickness=15,
                        lenmode="pixels",
                        len=200
                    )
                )
                
                st.plotly_chart(fig_heatmap, use_container_width=True)
                st.caption(f"📍 Exibindo {len(df_map)} localidades no mapa")
            else:
                st.info("Sem dados de localização para exibir o mapa.")
        else:
            st.info("Sem dados para exibir o mapa de densidade.")

    # --- KPIs E GRÁFICO DE EVOLUÇÃO ABAIXO ---
    st.markdown("---")

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


    # --- Layout com dois gráficos lado a lado ---
    col_waterfall, col_evolucao = st.columns([1, 1])

    # --- Gráfico Waterfall: Fluxo da Moeda Social ---
    with col_waterfall:
        st.subheader("Fluxo da Moeda Social – Entrada, Estoque e Saída")
        if not df_filtrado.empty:
            import plotly.graph_objects as go
            
            # Calcula valores
            entrada_emitido = df_filtrado['Total Emitido'].sum()
            estoque_atual = df_filtrado['Moeda social em circulação'].sum()
            saida_total = df_filtrado['Saques'].sum() + df_filtrado['PAGAMENTO DE BOLETOS/CONVÊNIOS'].sum()
            
            # Cria gráfico waterfall
            fig_waterfall = go.Figure(go.Waterfall(
                name="Fluxo",
                orientation="v",
                measure=["absolute", "relative", "total"],
                x=["Entrada<br>(Emitido)", "Estoque Atual", "Saída"],
                textposition="outside",
                text=[f"R$ {entrada_emitido:,.0f}", f"R$ {estoque_atual:,.0f}", f"R$ {saida_total:,.0f}"],
                y=[entrada_emitido, estoque_atual - entrada_emitido, saida_total],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "#17BECF"}},
                decreasing={"marker": {"color": "#EF553B"}},
                totals={"marker": {"color": "#636EFA"}}
            ))
            
            fig_waterfall.update_layout(
                height=320,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=50, r=50, t=30, b=80),
                yaxis=dict(
                    title="Valor (R$)",
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    range=[0, 300000000]
                ),
                xaxis=dict(
                    title="",
                )
            )
            
            st.plotly_chart(fig_waterfall, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    # --- Heatmap de Intensidade Mensal das Operações ---
    with col_evolucao:
        st.subheader("Heatmap – Intensidade Mensal das Operações")
        if not df_filtrado.empty:
            # Cria DataFrame com os indicadores necessários
            df_heatmap = df_filtrado.copy()
            df_heatmap['Mes'] = df_heatmap['data'].dt.to_period('M').astype(str)
            
            # Agrupa por mês e soma os indicadores
            indicadores = {
                'Moeda social em circulação': 'Moeda social em circulação',
                'Saques': 'Saques',
                'VALOR GASTO NO COMÉRCIO LOCAL': 'VALOR GASTO NO COMÉRCIO LOCAL'
            }
            
            df_pivot_list = []
            for label, coluna in indicadores.items():
                df_temp = df_heatmap.groupby('Mes')[coluna].sum().reset_index()
                df_temp['Indicador'] = label
                df_temp.rename(columns={coluna: 'Valor'}, inplace=True)
                df_pivot_list.append(df_temp)
            
            df_pivot = pd.concat(df_pivot_list, ignore_index=True)
            
            # Cria pivot table para o heatmap
            matriz_heatmap = df_pivot.pivot(index='Indicador', columns='Mes', values='Valor').fillna(0)
            
            # Cria o heatmap
            import plotly.graph_objects as go
            
            # Define valores mínimo e máximo para escala
            z_min = 0
            z_max = matriz_heatmap.values.max()
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=matriz_heatmap.values,
                x=matriz_heatmap.columns,
                y=matriz_heatmap.index,
                zmin=z_min,
                zmax=z_max,
                colorscale=[
                    [0, 'rgb(255, 255, 255)'],      # Branco para zero
                    [0.001, 'rgb(173, 216, 230)'],  # Azul claro visível para valores > 0
                    [0.2, 'rgb(135, 206, 250)'],    # Azul céu
                    [0.4, 'rgb(70, 130, 180)'],     # Azul aço
                    [0.6, 'rgb(30, 144, 255)'],     # Azul dodger
                    [0.8, 'rgb(0, 100, 200)'],      # Azul médio
                    [1, 'rgb(0, 63, 92)']           # Azul escuro
                ],
                hovertemplate='<b>%{y}</b><br>Mês: %{x}<br>Valor: R$ %{z:,.0f}<extra></extra>',
                colorbar=dict(
                    title=dict(text="Valor (R$)", side="right"),
                    tickmode="linear",
                    tick0=0,
                    dtick=10000000
                ),
                ygap=1   # Espaçamento vertical entre células (linhas horizontais)
            ))
            
            fig_heatmap.update_layout(
                height=400,
                xaxis=dict(
                    title="Mês",
                    tickangle=-45,
                    side='bottom',
                    showgrid=False
                ),
                yaxis=dict(
                    title="Indicador",
                    tickfont=dict(size=11),
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.3)',
                    gridwidth=1
                ),
                margin=dict(l=220, r=50, t=30, b=80),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

elif st.session_state.pagina_atual == 3:
    # --- PÁGINA 3: ANÁLISES COMPLEMENTARES ---
    
    # --- LINHA 1: Dois gráficos superiores ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Gráfico de Barras - Distribuição por Estado")
        if not df_filtrado.empty:
            import plotly.graph_objects as go
            
            # Agrupa por estado e conta bancos comunitários
            df_estados = df_filtrado.groupby('Estado')['Banco Comunitário'].nunique().sort_values(ascending=False).head(10)
            
            fig_estados = go.Figure(data=[
                go.Bar(
                    x=df_estados.index,
                    y=df_estados.values,
                    marker=dict(
                        color=df_estados.values,
                        colorscale='Viridis',
                        showscale=False
                    ),
                    text=df_estados.values,
                    textposition='outside'
                )
            ])
            
            fig_estados.update_layout(
                height=350,
                xaxis_title="Estado",
                yaxis_title="Número de Bancos",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=50, r=50, t=30, b=50),
                showlegend=False,
                yaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)')
            )
            
            st.plotly_chart(fig_estados, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    with col2:
        st.subheader("📈 Evolução Temporal - Moeda em Circulação")
        if not df_filtrado.empty:
            # Agrupa por data e soma moeda em circulação
            df_temporal = df_filtrado.groupby('data')['Moeda social em circulação'].sum().reset_index()
            
            fig_temporal = px.line(
                df_temporal,
                x='data',
                y='Moeda social em circulação',
                markers=True,
                line_shape='spline'
            )
            
            fig_temporal.update_traces(
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8, color='#ff7f0e')
            )
            
            fig_temporal.update_layout(
                height=350,
                xaxis_title="Data",
                yaxis_title="Moeda em Circulação (R$)",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=50, r=50, t=30, b=50),
                hovermode='x unified',
                yaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)')
            )
            
            st.plotly_chart(fig_temporal, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    st.markdown("---")
    
    # --- LINHA 2: Dois gráficos inferiores ---
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.subheader("🥧 Distribuição de Saques vs Comercio Local")
        if not df_filtrado.empty:
            # Calcula totais
            total_saques = df_filtrado['Saques'].sum()
            total_comercio = df_filtrado['VALOR GASTO NO COMÉRCIO LOCAL'].sum()
            
            fig_pizza = go.Figure(data=[
                go.Pie(
                    labels=['Saques', 'Comércio Local'],
                    values=[total_saques, total_comercio],
                    hole=0.4,
                    marker=dict(colors=['#EF553B', '#17BECF']),
                    textinfo='label+percent',
                    textposition='outside'
                )
            ])
            
            fig_pizza.update_layout(
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=50, r=50, t=30, b=50),
                showlegend=True
            )
            
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    with col4:
        st.subheader("📊 Ranking de Municípios - Top 10")
        if not df_filtrado.empty:
            # Agrupa por município e soma a moeda em circulação
            df_municipios = (
                df_filtrado.groupby('Município')['Moeda social em circulação']
                .sum()
                .sort_values(ascending=True)
                .tail(10)
            )
            
            fig_municipios = go.Figure(data=[
                go.Bar(
                    x=df_municipios.values,
                    y=df_municipios.index,
                    orientation='h',
                    marker=dict(
                        color=df_municipios.values,
                        colorscale='Blues',
                        showscale=False
                    ),
                    text=[f'R$ {val:,.0f}' for val in df_municipios.values],
                    textposition='outside'
                )
            ])
            
            fig_municipios.update_layout(
                height=350,
                xaxis_title="Moeda em Circulação (R$)",
                yaxis_title="",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=150, r=80, t=30, b=50),
                showlegend=False,
                xaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)')
            )
            
            st.plotly_chart(fig_municipios, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")