import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÕES DE PÁGINA
st.set_page_config(page_title="Comunicando Igrejas Pro", page_icon="⚡", layout="wide")

# CSS PARA LIMPAR A TELA (RETIRAR GITHUB/FORK)
st.markdown("""<style>header {visibility: hidden !important;} #MainMenu {visibility: hidden !important;} footer {visibility: hidden !important;} .block-container {padding-top: 1rem !important;}</style>""", unsafe_allow_html=True)

# 2. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO
if "logado" not in st.session_state: st.session_state.logado = False

# 3. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de Conexão. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)
def carregar_calendario():
    try: return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except: return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

def aplicar_tema(cor):
    st.markdown(f"""<style>.stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }} .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}</style>""", unsafe_allow_html=True)

# --- FUNÇÃO DE LOGOUT SEGURO ---
def logout():
    st.session_state.clear() # Limpa toda a memória da sessão
    st.rerun() # Reinicia o app para a tela de login

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    tab_log, tab_rec = st.tabs(["Acessar Sistema", "Recuperar Senha"])
    with tab_log:
        with st.form("form_login"):
            email_in = st.text_input("E-mail")
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                df_u = carregar_usuarios()
                user = df_u[(df_u['email'].str.lower() == email_in.lower()) & (df_u['senha'].astype(str) == str(senha_in))]
                if not user.empty:
                    if str(user.iloc[0]['status']).lower() == 'ativo':
                        st.session_state.logado = True
                        st.session_state.perfil = user.iloc[0]['perfil'].strip().lower()
                        st.session_state.igreja_id = user.iloc[0]['igreja_id']
                        st.session_state.email = email_in
                        st.rerun()
                    else: st.warning("Conta inativa.")
                else: st.error("E-mail ou senha incorretos.")
    with tab_rec:
        st.link_button("🔑 Solicitar Nova Senha (WhatsApp)", "https://wa.me/551937704733?text=Olá, esqueci minha senha.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Lógica Master vs Usuário
    if st.session_state.perfil == "admin":
        st.sidebar.title("👑 PAINEL MASTER")
        igreja_selecionada = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_selecionada].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.title(f"📱 {conf['nome_exibicao']}")

    # Aplicação do Tema
    cor_tema = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_tema.startswith("#"): cor_tema = f"#{cor_tema}"
    aplicar_tema(cor_tema)

    with st.sidebar:
        st.divider()
        st.link_button("⛪ Instagram", conf['instagram_url'])
        # BOTÃO SAIR NA SIDEBAR
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            logout()

    # Definição de Abas
    if st.session_state.perfil == "admin":
        abas = st.tabs(["📊 Gestão Master", "✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"])
        tab_master, tab_gen, tab_story, tab_cal, tab_perf = abas
    else:
        abas = st.tabs(["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"])
        tab_gen, tab_story, tab_cal, tab_perf = abas

    # (Código das outras abas omitido para brevidade, mas deve ser mantido)
    # ... ABA MASTER, ABA GERADOR, ABA STORIES, ABA CALENDARIO ...

    # --- ABA 4: PERFIL (COM BOTÃO DE SAIR EXTRA) ---
    with tab_perf:
        st.header("🎨 Personalização e Segurança")
        # (Código da paleta de cores e alteração de senha deve ser mantido)
        # ...
        
        st.divider()
        st.subheader("🚪 Encerrar Sessão")
        st.write("Deseja sair da sua conta com segurança?")
        if st.button("Sair Agora", type="primary"):
            logout()
