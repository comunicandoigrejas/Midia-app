import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA (Deve ser o primeiro comando)
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INICIALIZAÇÃO DE SEGURANÇA (Prevenção de erros de estado)
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

# 3. CONEXÕES (Ajuste Crítico aqui)
try:
    # Capturamos a URL diretamente para vincular à conexão
    LINK_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Criamos a conexão já 'anexando' a planilha a ela
    conn = st.connection("gsheets", type=GSheetsConnection, spreadsheet=LINK_PLANILHA)
    
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
except Exception as e:
    st.error(f"⚠️ Erro nos Secrets ou Conexão: {e}")
    st.stop()

# --- FUNÇÕES DE APOIO ---
def carregar_usuarios(): 
    return conn.read(worksheet="usuarios", ttl=0)

def carregar_configuracoes(): 
    return conn.read(worksheet="configuracoes", ttl=0)

def carregar_calendario():
    try: 
        return conn.read(worksheet="calendario", ttl=0)
    except: 
        return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

# ==========================================
# INTERFACE DE LOGIN (TRAVA DE BLOQUEIO ATIVA)
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    t1, t2 = st.tabs(["Entrar", "Recuperar Senha"])
    
    with t1:
        with st.form("login_form"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema"):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                
                if not u.empty:
                    # LÓGICA DE BLOQUEIO: Se for nulo ou diferente de 'ativo', bloqueia.
                    status_raw = u.iloc[0]['status']
                    status_db = str(status_raw).strip().lower() if pd.notnull(status_raw) else "inativo"
                    
                    if status_db == "ativo":
                        st.session_state.logado = True
                        st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = u.iloc[0]['igreja_id']
                        st.session_state.email = em
                        st.rerun()
                    else:
                        st.error(f"🚫 ACESSO NEGADO: Sua conta está '{status_db}'. Procure o suporte.")
                else:
                    st.error("❌ E-mail ou senha incorretos.")
    with t2:
        st.link_button("📲 Suporte via WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Identificação de Perfil
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Escolher Igreja:", df_conf['nome_exibicao'].tolist())
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

    # --- ABA 3: CALENDÁRIO (RESOLVENDO O VALUEERROR) ---
    with t_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Novo Post"):
            with st.form("form_agendar_definitivo"):
                dp = st.date_input("Data", datetime.now())
                tp = st.text_input("Assunto")
                if st.form_submit_button("Confirmar Agendamento"):
                    # Criamos o DataFrame de dados novos
                    dados_novos = pd.DataFrame([{
                        "igreja_id": conf['igreja_id'], 
                        "data": dp.strftime('%Y-%m-%d'), 
                        "rede_social": "Geral", 
                        "tema": tp, 
                        "status": "Pendente"
                    }])
                    
                    # O PULO DO GATO: Usar a conexão vinculada ao segredo diretamente
                    try:
                        conn.create(
                            spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], 
                            worksheet="calendario", 
                            data=dados_novos
                        )
                        st.success("✅ Agendado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as error_save:
                        st.error(f"Erro ao salvar: {error_save}")
        
        # Exibição do Calendário
        df_c = carregar_calendario()
        df_filtrado = df_c[df_c['igreja_id'].astype(str) == str(conf['igreja_id'])]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
