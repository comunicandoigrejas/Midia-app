import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd

# 1. Configurações de Layout
st.set_page_config(page_title="Comunicando Igrejas - Painel", layout="wide")

# Esconder elementos do Streamlit para um visual profissional
st.markdown("<style>header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# 2. Inicialização de Conexões
try:
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error(f"Erro na inicialização: {e}")
    st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_usuarios():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios")

def carregar_configuracoes():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes")

# --- LÓGICA DE SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    st.subheader("Painel de Gestão de Mídia")
    
    with st.form("login_form"):
        email_i = st.text_input("E-mail")
        senha_i = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar Sistema"):
            df_u = carregar_usuarios()
            # Validação simples (garantindo que senha seja tratada como texto)
            user = df_u[(df_u['email'] == email_i) & (df_u['senha'].astype(str) == str(senha_i))]
            
            if not user.empty:
                if user.iloc[0]['status'] == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = user.iloc[0]['perfil']
                    st.session_state.igreja_id = user.iloc[0]['igreja_id']
                    st.session_state.email = email_i
                    st.rerun()
                else:
                    st.error("Assinatura inativa. Fale com o suporte.")
            else:
                st.error("Credenciais inválidas.")
else:
    # --- AMBIENTE LOGADO (MULTITENANCY) ---
    df_config = carregar_configuracoes()
    
    # Identifica a igreja do usuário
    if st.session_state.perfil == "admin":
        st.sidebar.title("👑 MASTER ADMIN")
        igreja_selecionada = st.sidebar.selectbox("Simular Igreja:", df_config['nome_exibicao'].tolist())
        config = df_config[df_config['nome_exibicao'] == igreja_selecionada].iloc[0]
    else:
        config = df_config[df_config['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.title(f"📱 {config['nome_exibicao']}")

    # Barra Lateral
    with st.sidebar:
        st.link_button("⛪ Instagram da Igreja", config['instagram_url'])
        st.divider()
        st.link_button("🔧 Suporte Comunicando", "https://www.instagram.com/comunicandoigrejas/")
        if st.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()

    # --- ABAS DO SISTEMA ---
    if st.session_state.perfil == "admin":
        tab_admin, tab_gerador = st.tabs(["📊 Gestão Master", "✨ Gerador"])
        with tab_admin:
            st.write("### Painel do Proprietário")
            st.dataframe(df_config) # Mostra todas as igrejas para o Admin
    else:
        tab_gerador, tab_perfil = st.tabs(["✨ Gerador", "⚙️ Perfil"])

    # --- FERRAMENTA GERADORA ---
    with tab_gerador:
        st.header(f"Criando Conteúdo para: {config['nome_exibicao']}")
        
        versiculo = st.text_input("📖 Versículo Base")
        tema = st.text_area("Sobre o que é o post?")
        
        if st.button("✨ Gerar Legenda Profissional"):
            if versiculo and tema:
                with st.spinner("IA processando..."):
                    prompt = f"""
                    Igreja: {config['nome_exibicao']}
                    Base: {versiculo}
                    Hashtags Fixas: {config['hashtags_fixas']}
                    Regra: Bíblia ARA, +30 palavras, emojis pentecostais e hashtags temáticas.
                    Tema: {tema}
                    """
                    # Aqui entra a chamada real da OpenAI (client.chat.completions.create...)
                    st.success("Legenda gerada com sucesso! (Conecte sua lógica da OpenAI aqui)")
                    st.code(f"Texto exemplo baseado em {versiculo}...\n\n{config['hashtags_fixas']}", language=None)
            else:
                st.warning("Preencha o versículo e o tema.")
