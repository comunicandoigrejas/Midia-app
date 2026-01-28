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
    initial_sidebar_state="expanded"
)

# 2. INICIALIZAÇÃO DE SEGURANÇA
for chave in ["logado", "perfil", "igreja_id", "email"]:
    if chave not in st.session_state:
        st.session_state[chave] = False if chave == "logado" else ""

# --- CSS ULTRA-AGRESSIVO: REMOVE FORK, GITHUB, MENU E RODAPÉ ---
st.markdown("""
    <style>
    /* Esconde botões de ação (Fork, GitHub, Deploy) */
    [data-testid="stHeaderActionElements"], 
    .stAppDeployButton,
    button[title="View source on GitHub"] {
        display: none !important;
    }
    
    /* Esconde o menu de 3 pontos (MainMenu) */
    #MainMenu {
        visibility: hidden !important;
    }

    /* Torna o cabeçalho invisível para esconder a barra cinza */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: transparent !important;
        border: none !important;
    }

    /* Remove o rodapé 'Made with Streamlit' */
    footer {
        visibility: hidden !important;
    }

    /* Remove espaços inúteis no topo */
    .block-container {
        padding-top: 1rem !important;
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

# --- FUNÇÕES DE APOIO ---
def carregar_usuarios(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def chamar_super_agente(comando):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=comando)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    
    with st.spinner("🧠 O Super Agente está processando sua estratégia..."):
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run.status in ["failed", "cancelled", "expired"]:
                return "Erro: O Agente falhou. Verifique as instruções na OpenAI."
    
    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    return mensagens.data[0].content[0].text.value

# ==========================================
# INTERFACE DE LOGIN (COM BLOQUEIO REAL)
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    t1, t2 = st.tabs(["Entrar", "Suporte"])
    
    with t1:
        with st.form("login"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                
                if not u.empty:
                    # Trava de Bloqueio
                    status_db = str(u.iloc[0]['status']).strip().lower() if pd.notnull(u.iloc[0]['status']) else "inativo"
                    
                    if status_db == 'ativo':
                        st.session_state.logado = True
                        st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = u.iloc[0]['igreja_id']
                        st.session_state.email = em
                        st.rerun()
                    else:
                        st.error("🚫 ACESSO NEGADO: Sua conta está inativa.")
                else:
                    st.error("❌ Dados incorretos.")
    with t2:
        st.link_button("📲 Suporte WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Painel Master")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    with st.sidebar:
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.link_button("📸 Instagram", conf['instagram_url'], use_container_width=True)

    # ABAS (REMOVIDO CALENDÁRIO)
    list_tabs = ["✨ Legendas", "🎬 Stories", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": list_tabs.insert(0, "📊 Gestão Master")
    
    tabs = st.tabs(list_tabs)
    
    if st.session_state.perfil == "admin": t_master, t_gen, t_story, t_perf = tabs
    else: t_gen, t_story, t_perf = tabs

    # ABA MASTER
    if st.session_state.perfil == "admin":
        with t_master:
            st.write("### Controle de Igrejas")
            st.dataframe(df_conf, use_container_width=True, hide_index=True)

    # ABA LEGENDAS
    with t_gen:
        st.header("✨ Super Agente: Gerador de Conteúdo")
        c1, c2 = st.columns(2)
        with c1:
            rd = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn"])
            est = st.selectbox("Tom", ["Inspiradora", "Pentecostal", "Jovem", "Teológica"])
        with c2:
            vr = st.text_input("📖 Versículo (Ex: João 10:10)")
            ht = st.text_input("Hashtags Extras")
        
        br = st.text_area("Descreva o tema da postagem")
        if st.button("🚀 Criar Minha Legenda"):
            if br:
                res = chamar_super_agente(f"Gere legenda para {rd}, tom {est}, tema {br}, versículo {vr}. Use as hashtags fixas: {conf['hashtags_fixas']} {ht}")
                st.markdown("---")
                st.subheader("📝 Resultado:")
                st.info(res) # Exibe o texto na tela
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    # ABA STORIES
    with t_story:
        st.header("🎬 Super Agente: Roteiro de Stories")
        ts = st.text_input("Qual o tema da sequência?")
        if st.button("🎬 Gerar Roteiro de 3 Telas"):
            if ts:
                res_s = chamar_super_agente(f"Crie um roteiro de 3 stories sobre {ts} para a igreja {conf['nome_exibicao']}. Use emojis e a Bíblia ARA.")
                st.markdown("---")
                st.subheader("🎬 Roteiro Sugerido:")
                st.success(res_s) # Exibe o texto na tela
                st.link_button("📲 Enviar Roteiro WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res_s)}")

    # ABA PERFIL
    with t_perf:
        st.header("⚙️ Minha Conta")
        st.write(f"Conectado como: **{st.session_state.email}**")
        st.write(f"Status da Conta: **Ativo** ✨")
