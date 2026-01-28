import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INICIALIZAÇÃO DE ESTADO
for chave in ["logado", "perfil", "igreja_id", "email"]:
    if chave not in st.session_state:
        st.session_state[chave] = False if chave == "logado" else ""

# --- CSS: VISUAL LIMPO ---
st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    .block-container { padding-top: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES (Sem o argumento problemático)
try:
    # Apenas criamos a conexão simples
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Armazenamos a URL em uma variável global para uso constante
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
except Exception as e:
    st.error(f"⚠️ Erro nos Secrets: {e}")
    st.stop()

# --- FUNÇÕES DE APOIO ---
def carregar_usuarios(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def carregar_calendario():
    try: 
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except: 
        return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

# ==========================================
# INTERFACE DE LOGIN (TRAVA DE BLOQUEIO)
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    t1, t2 = st.tabs(["Entrar", "Suporte"])
    
    with t1:
        with st.form("login_form"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema"):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                
                if not u.empty:
                    # Limpeza rigorosa do status
                    status_raw = u.iloc[0]['status']
                    status_db = str(status_raw).strip().lower() if pd.notnull(status_raw) else "inativo"
                    
                    if status_db == "ativo":
                        st.session_state.logado = True
                        st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = u.iloc[0]['igreja_id']
                        st.session_state.email = em
                        st.rerun()
                    else:
                        st.error(f"🚫 ACESSO NEGADO: Status '{status_db}'. Procure o suporte.")
                else:
                    st.error("❌ E-mail ou senha incorretos.")
    with t2:
        st.link_button("📲 WhatsApp Suporte", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Define Perfil
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    with st.sidebar:
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()

    abas = st.tabs(["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"])
    t_gen, t_story, t_cal, t_perf = abas

   Erro ao salvar: Spreadsheet must be specified
