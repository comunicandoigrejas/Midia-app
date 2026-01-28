import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="auto"
)

# 2. INICIALIZAÇÃO DE ESTADO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

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
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def chamar_super_agente(comando):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=comando)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    with st.spinner("🧠 O Super Agente está processando..."):
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
        if st.form_submit_button("Acessar Painel"):
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
                else: st.error("🚫 Conta inativa.")
            else: st.error("❌ E-mail ou senha incorretos.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0] if st.session_state.perfil != "admin" else df_conf.iloc[0]

    cor_atual = st.session_state.cor_previa if st.session_state.cor_previa else str(conf['cor_tema'])
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"

    # --- 🛠️ CSS: BOTÃO UNIFICADO + RECUO LATERAL DA PÁGINA ---
    st.markdown(f"""
        <style>
        /* 1. Remove ícones do topo */
        [data-testid="stHeaderActionElements"], .stAppDeployButton, #MainMenu {{
            display: none !important;
        }}

        /* 2. Botão de ABRIR (Centralizado na esquerda) */
        [data-testid="stSidebarCollapseButton"] {{
            position: fixed !important;
            top: 50% !important;
            left: 0px !important;
            transform: translateY(-50%) !important;
            z-index: 1000000 !important;
            background-color: {cor_atual} !important;
            color: white !important;
            border-radius: 0 15px 15px 0 !important;
            width: 45px !important;
            height: 60px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 5px 0px 15px rgba(0,0,0,0.3) !important;
        }}

        /* 3. Botão de FECHAR (Grudado na borda da sidebar aberta) */
        section[data-testid="stSidebar"] button {{
            position: fixed !important;
            top: 50% !important;
            left: 336px !important; 
            transform: translateY(-50%) !important;
            z-index: 1000001 !important;
            background-color: {cor_atual} !important;
            color: white !important;
            border-radius: 0 15px 15px 0 !important;
            width: 45px !important;
            height: 60px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        /* 4. LEVAR TODA A PÁGINA MAIS PARA A LATERAL DIREITA */
        .block-container {{
            padding-left: 10% !important; /* Cria um corredor de segurança na esquerda */
            padding-right: 5% !important;
            max-width: 95% !important;
        }}

        /* Estilos de Cores */
        header[data-testid="stHeader"] {{ background-color: rgba(0,0,0,0) !important; border: none !important; }}
        footer {{ visibility: hidden !important; }}
        .stButton>button {{ background-color: {cor_atual}; color: white; border-radius: 8px; font-weight: bold; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor_atual}; color: white !important; border-radius: 5px; }}
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.subheader(f"⛪ {conf['nome_exibicao']}")
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.link_button("📸 Instagram", str(conf['instagram_url']), use_container_width=True)

    # ABAS
    t_gen, t_story, t_perf = st.tabs(["✨ Legendas", "🎬 Stories", "⚙️ Perfil"])

    # --- ABA LEGENDAS ---
    with t_gen:
        st.header("✨ Gerador de Conteúdo ARA")
        col1, col2 = st.columns(2)
        with col1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "WhatsApp"])
            tom = st.selectbox("Tom", ["Inspirador", "Pentecostal", "Jovem", "Teológico"])
        with col2:
            ver = st.text_input("📖 Versículo Base (ARA)", placeholder="Ex: João 10:10")
            ht_extra = st.text_input("🏷️ Hashtags Extras")
        
        tema_post = st.text_area("📝 Sobre o que vamos postar?")
        if st.button("🚀 Criar Minha Legenda"):
            if tema_post:
                prompt = f"Gere legenda para {rede}, tom {tom}, tema {tema_post}, versículo {ver}. Bíblia ARA. Use hashtags: {conf['hashtags_fixas']} {ht_extra}"
                resultado = chamar_super_agente(prompt)
                st.info(resultado)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")

    # --- ABA STORIES ---
    with t_story:
        st.header("🎬 Super Agente: Stories")
        ts = st.text_input("Tema dos Stories")
        if st.button("🎬 Criar Roteiro"):
            if ts:
                res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}.")
                st.success(res_s)

    # --- ABA PERFIL ---
    with t_perf:
        st.header("⚙️ Personalização")
        nova_cor = st.color_picker("Cor da igreja:", cor_atual)
        if st.button("🖌️ Aplicar Cor"):
            st.session_state.cor_previa = nova_cor
            st.rerun()
