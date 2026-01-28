import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time

# 1. CONFIGURAÇÃO DE PÁGINA (Estado 'auto' permite o botão de recolher)
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="auto"
)

# 2. INICIALIZAÇÃO DE SEGURANÇA
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS AJUSTADO: ESCONDE O DESNECESSÁRIO E MANTÉM O BOTÃO DE RECUAR ---
st.markdown("""
    <style>
    /* Esconde apenas os botões da direita: Fork, GitHub e View Source */
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* Esconde o botão de Deploy e o Menu de 3 pontos */
    .stAppDeployButton, #MainMenu {
        display: none !important;
    }

    /* Mantém o header mas o deixa transparente para o botão '>' aparecer */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: inherit !important;
    }

    /* Remove o rodapé 'Made with Streamlit' */
    footer {
        visibility: hidden !important;
    }

    /* Ajuste de margem para o conteúdo começar de forma elegante */
    .block-container {
        padding-top: 2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de conexão. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES SUPORTE ---
def carregar_usuarios(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def aplicar_tema(cor):
    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}
        </style>
    """, unsafe_allow_html=True)

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
    with st.form("login"):
        em = st.text_input("E-mail")
        se = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            df_u = carregar_usuarios()
            u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
            if not u.empty:
                status_raw = u.iloc[0]['status']
                status_db = str(status_raw).strip().lower() if pd.notnull(status_raw) else "inativo"
                if status_db == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                    st.session_state.igreja_id = u.iloc[0]['igreja_id']
                    st.session_state.email = em
                    st.rerun()
                else: st.error("🚫 ACESSO NEGADO: Conta inativa.")
            else: st.error("❌ E-mail ou senha incorretos.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    if st.session_state.perfil == "admin":
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]

    # Aplicação do Tema
    cor_atual = st.session_state.cor_previa if st.session_state.cor_previa else str(conf['cor_tema'])
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"
    aplicar_tema(cor_atual)

    with st.sidebar:
        st.subheader(f"⛪ {conf['nome_exibicao']}")
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.link_button("📸 Instagram", conf['instagram_url'], use_container_width=True)

    abas = st.tabs(["✨ Legendas", "🎬 Stories", "⚙️ Perfil"])
    t_gen, t_story, t_perf = abas

    with t_gen:
        st.header("✨ Super Agente: Conteúdo")
        br = st.text_area("O que vamos criar?")
        if st.button("🚀 Criar Legenda"):
            if br:
                res = chamar_super_agente(f"Legenda para Instagram, tema {br}. Use hashtags: {conf['hashtags_fixas']}")
                st.info(res)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    with t_story:
        st.header("🎬 Super Agente: Stories")
        ts = st.text_input("Tema dos Stories")
        if st.button("🎬 Criar Roteiro"):
            if ts:
                res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}.")
                st.success(res_s)

    with t_perf:
        st.header("⚙️ Personalização e Segurança")
        nova_cor = st.color_picker("Cor da igreja:", cor_atual)
        if st.button("🖌️ Aplicar Cor"):
            st.session_state.cor_previa = nova_cor
            st.rerun()
        
        st.divider()
        with st.form("form_senha"):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_at:
                    df_u.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("✅ Senha alterada!")
                else: st.error("❌ Senha atual incorreta.")
