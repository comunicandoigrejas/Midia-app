import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA (Sempre a primeira linha)
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INICIALIZAÇÃO DE SEGURANÇA (Prevenção de AttributeError)
if "logado" not in st.session_state: st.session_state.logado = False
if "perfil" not in st.session_state: st.session_state.perfil = ""
if "igreja_id" not in st.session_state: st.session_state.igreja_id = ""
if "email" not in st.session_state: st.session_state.email = ""

# --- CSS PARA VISUAL LIMPO (Sem Fork/GitHub) ---
st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    .block-container { padding-top: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES (Com Verificação de Link)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
    # Pegamos o link diretamente para evitar o erro de 'Spreadsheet must be specified'
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Erro de Configuração: {e}")
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
                    # --- TRAVA DE SEGURANÇA: BLOQUEIO DE CONTA ---
                    status_raw = str(u.iloc[0]['status']).strip().lower()
                    if status_raw == 'ativo':
                        st.session_state.logado = True
                        st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = u.iloc[0]['igreja_id']
                        st.session_state.email = em
                        st.rerun()
                    else:
                        st.error("🚫 Conta Bloqueada ou Inativa. Procure o administrador.")
                else:
                    st.error("❌ E-mail ou senha incorretos.")
    with t2:
        st.link_button("📲 Suporte WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    # BARRA LATERAL
    with st.sidebar:
        if st.button("🚪 SAIR", use_container_width=True, type="primary"): logout()
        st.divider()
        st.link_button("📸 Instagram", conf['instagram_url'], use_container_width=True)

    # ABAS
    abas = st.tabs(["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"])
    t_gen, t_story, t_cal, t_perf = abas

    # --- ABA 1: GERADOR ---
    with t_gen:
        st.header("✨ Gerador com Super Agente")
        br = st.text_area("Tema da postagem")
        if st.button("🚀 Criar Conteúdo"):
            if br:
                res = chamar_super_agente(f"Legenda para Instagram, tema {br}. Use: {conf['hashtags_fixas']}")
                st.info(res)
                st.link_button("📲 WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    # --- ABA 2: STORIES ---
    with t_story:
        st.header("🎬 Roteiro de Stories")
        ts = st.text_input("Tema dos Stories")
        if st.button("🎬 Gerar Sequência"):
            res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}.")
            st.success(res_s)

    # --- ABA 3: CALENDÁRIO (FIXO PARA EVITAR VALUEERROR) ---
    with t_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Novo Agendamento"):
            with st.form("f_cal"):
                dp = st.date_input("Data")
                tp = st.text_input("Tema")
                if st.form_submit_button("Salvar"):
                    if URL_PLANILHA: # Verifica se o link existe antes de salvar
                        nv = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": dp.strftime('%Y-%m-%d'), "rede_social": "Geral", "tema": tp, "status": "Pendente"}])
                        conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=nv)
                        st.success("Salvo!")
                        st.rerun()
                    else:
                        st.error("Erro: Link da planilha não configurado.")

    # --- ABA 4: PERFIL ---
    with t_perf:
        st.header("⚙️ Minha Conta")
        st.write(f"Conectado como: **{st.session_state.email}**")
