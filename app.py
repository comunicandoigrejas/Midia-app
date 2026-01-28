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

# 2. INICIALIZAÇÃO DE ESTADO (Session State)
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS: INTERFACE PROFISSIONAL (ESCONDE GITHUB, FORK E MENU) ---
st.markdown("""
    <style>
    /* Remove botões do GitHub, Fork e 'View Source' */
    [data-testid="stHeaderActionElements"] { display: none !important; }
    
    /* Esconde o menu de 3 pontos e o botão de Deploy */
    .stAppDeployButton, #MainMenu { display: none !important; }

    /* Cabeçalho transparente para manter o botão de recolher sidebar */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: inherit !important;
    }

    /* Remove o rodapé e ajusta o topo */
    footer { visibility: hidden !important; }
    .block-container { padding-top: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de conexão. Verifique os Secrets no Streamlit Cloud.")
    st.stop()

# --- FUNÇÕES DE APOIO ---
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
                # TRAVA DE SEGURANÇA: STATUS ATIVO
                status_raw = u.iloc[0]['status']
                status_db = str(status_raw).strip().lower() if pd.notnull(status_raw) else "inativo"
                
                if status_db == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                    st.session_state.igreja_id = u.iloc[0]['igreja_id']
                    st.session_state.email = em
                    st.rerun()
                else:
                    st.error("🚫 ACESSO NEGADO: Sua conta está inativa ou bloqueada.")
            else:
                st.error("❌ E-mail ou senha incorretos.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    # 1. Carregar Configurações da Igreja
    df_conf = carregar_configuracoes()
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Painel Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]

    # 2. Definir Cor Atual (Evita NameError)
    cor_atual = st.session_state.cor_previa if st.session_state.cor_previa else str(conf['cor_tema'])
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"
    aplicar_tema(cor_atual)

    # 3. Barra Lateral
    with st.sidebar:
        st.subheader(f"⛪ {conf['nome_exibicao']}")
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.link_button("📸 Instagram", str(conf['instagram_url']), use_container_width=True)

    # 4. Criação das Abas (Definidas antes do uso com 'with')
    lista_abas = ["✨ Legendas", "🎬 Stories", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": lista_abas.insert(0, "📊 Master")
    
    # Esta linha garante que t_gen e outras variáveis existam
    objetos_abas = st.tabs(lista_abas)

    # Lógica para distribuir as variáveis conforme o perfil
    if st.session_state.perfil == "admin":
        t_master, t_gen, t_story, t_perf = objetos_abas
        with t_master:
            st.header("📊 Gestão Master")
            st.dataframe(df_conf, use_container_width=True, hide_index=True)
    else:
        t_gen, t_story, t_perf = objetos_abas

    # --- ABA LEGENDAS ---
    with t_gen:
        st.header("✨ Super Agente: Gerador de Legendas")
        br = st.text_area("Descreva o tema da postagem ou o versículo base:")
        if st.button("🚀 Criar Legenda"):
            if br:
                resultado = chamar_super_agente(f"Legenda para Instagram, tema {br}. Use hashtags: {conf['hashtags_fixas']}")
                st.info(resultado)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")

    # --- ABA STORIES ---
    with t_story:
        st.header("🎬 Super Agente: Roteiro de Stories")
        ts = st.text_input("Qual o tema da sequência de Stories?")
        if st.button("🎬 Gerar Roteiro"):
            if ts:
                resultado_s = chamar_super_agente(f"Crie roteiro de 3 stories sobre {ts} para {conf['nome_exibicao']}.")
                st.success(resultado_s)

    # --- ABA PERFIL ---
    with t_perf:
        st.header("⚙️ Configurações da Conta")
        
        # Troca de Cor
        st.subheader("🎨 Identidade Visual")
        nova_cor = st.color_picker("Escolha a cor do seu painel:", cor_atual)
        if st.button("🖌️ Aplicar Cor"):
            st.session_state.cor_previa = nova_cor
            st.rerun()
        
        st.divider()
        
        # Troca de Senha
        st.subheader("🔑 Alterar Senha")
        with st.form("nova_senha"):
            s_atual = st.text_input("Senha Atual", type="password")
            s_nova = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_atual:
                    df_u.at[idx[0], 'senha'] = s_nova
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("✅ Senha alterada com sucesso!")
                else:
                    st.error("❌ Senha atual incorreta.")
