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

# 2. INICIALIZAÇÃO DE ESTADO (Prevenção de erros de atributo)
if "logado" not in st.session_state: st.session_state.logado = False
if "perfil" not in st.session_state: st.session_state.perfil = ""
if "igreja_id" not in st.session_state: st.session_state.igreja_id = ""
if "email" not in st.session_state: st.session_state.email = ""

# --- CSS: LIMPEZA DO HEADER (Mantendo o botão lateral) ---
st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    .block-container { padding-top: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
    # URL da planilha vinda diretamente dos Secrets
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Erro ao carregar configurações: {e}")
    st.stop()

# --- FUNÇÕES SUPORTE ---
def carregar_usuarios(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def carregar_calendario():
    try: return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except: return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

def logout():
    st.session_state.clear()
    st.rerun()

def chamar_super_agente(comando):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=comando)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    with st.spinner("🧠 Super Agente processando..."):
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    return mensagens.data[0].content[0].text.value

# ==========================================
# INTERFACE DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    t1, t2 = st.tabs(["Entrar", "Recuperar Senha"])
    
    with t1:
        with st.form("login_form"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Painel"):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                
                if not u.empty:
                    # --- LÓGICA DE BLOQUEIO RIGOROSA ---
                    status_user = str(u.iloc[0]['status']).strip().lower()
                    if status_user == 'ativo':
                        st.session_state.logado = True
                        st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = u.iloc[0]['igreja_id']
                        st.session_state.email = em
                        st.rerun()
                    else:
                        st.error("🚫 ACESSO NEGADO: Sua conta está inativa ou bloqueada.")
                else:
                    st.error("❌ E-mail ou senha incorretos.")
    with t2:
        st.link_button("📲 Suporte WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Lógica Admin vs Usuário
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    with st.sidebar:
        if st.button("🚪 SAIR DO SISTEMA", use_container_width=True, type="primary"):
            logout()
        st.divider()
        st.link_button("📸 Instagram", conf['instagram_url'], use_container_width=True)

    # ABAS PRINCIPAIS
    list_tabs = ["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": list_tabs.insert(0, "📊 Master")
    abas = st.tabs(list_tabs)

    if st.session_state.perfil == "admin": t_master, t_gen, t_story, t_cal, t_perf = abas
    else: t_gen, t_story, t_cal, t_perf = abas

    # Conteúdo da Aba Master
    if st.session_state.perfil == "admin":
        with t_master:
            st.header("📊 Gestão Master")
            st.dataframe(df_conf, use_container_width=True)

    # Conteúdo da Aba Gerador
    with t_gen:
        st.header("✨ Super Agente: Legendas")
        br = st.text_area("Tema da postagem")
        if st.button("🚀 Criar Conteúdo"):
            if br:
                resultado = chamar_super_agente(f"Legenda para Instagram, tema {br}. Use hashtags: {conf['hashtags_fixas']}")
                st.info(resultado)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")

    # Conteúdo da Aba Calendário (Onde ocorria o erro)
    with t_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Novo Agendamento"):
            with st.form("form_agendar"):
                dp = st.date_input("Data")
                tp = st.text_input("Assunto")
                if st.form_submit_button("Salvar"):
                    # Forçamos a URL aqui para garantir que não seja vazia
                    if URL_PLANILHA:
                        nv = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": dp.strftime('%Y-%m-%d'), "rede_social": "Geral", "tema": tp, "status": "Pendente"}])
                        conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=nv)
                        st.success("Salvo com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro: Link da planilha não encontrado.")
        
        df_c = carregar_calendario()
        st.dataframe(df_c[df_c['igreja_id'] == conf['igreja_id']], use_container_width=True, hide_index=True)

    # Conteúdo da Aba Perfil
    with t_perf:
        st.header("⚙️ Configurações")
        st.write(f"Usuário: **{st.session_state.email}**")
