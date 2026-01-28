import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd

# 1. Configurações de Interface
st.set_page_config(page_title="Comunicando Igrejas - Painel", layout="wide")
st.markdown("<style>header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# 2. Conexões Iniciais
try:
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error("🚨 Verifique os Secrets: O link da planilha ou a chave OpenAI estão faltando.")
    st.stop()

# --- FUNÇÕES DE BANCO DE DADOS ---
def carregar_usuarios():
    # ttl=0 obriga o app a ler a planilha em tempo real
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    st.subheader("Painel de Gestão de Mídia")
    
    with st.form("login"):
        email_i = st.text_input("E-mail")
        senha_i = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar Painel"):
            df_u = carregar_usuarios()
            # Validação: ignora maiúsculas e espaços extras
            user = df_u[(df_u['email'].str.lower().str.strip() == email_i.lower().strip()) & 
                        (df_u['senha'].astype(str) == str(senha_i))]
            
            if not user.empty:
                # Resolve o problema do 'Ativo' vs 'ativo'
                if user.iloc[0]['status'].strip().lower() == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = user.iloc[0]['perfil']
                    st.session_state.igreja_id = user.iloc[0]['igreja_id']
                    st.session_state.email = email_i
                    st.rerun()
                else:
                    st.error("Acesso bloqueado. Verifique o status da assinatura.")
            else:
                st.error("E-mail ou senha incorretos.")
else:
    # --- AMBIENTE LOGADO (MULTITENANCY) ---
    df_config = carregar_configuracoes()
    
    if st.session_state.perfil == "admin":
        st.sidebar.title("👑 MASTER ADMIN")
        nome_igreja = st.sidebar.selectbox("Simular Igreja:", df_config['nome_exibicao'].tolist())
        config = df_config[df_config['nome_exibicao'] == nome_igreja].iloc[0]
    else:
        config = df_config[df_config['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.title(f"📱 {config['nome_exibicao']}")

    with st.sidebar:
        st.link_button("⛪ Instagram da Igreja", config['instagram_url'])
        st.divider()
        if st.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()

    # --- ABA DE GERAÇÃO ---
    st.header(f"Gestão de Mídia: {config['nome_exibicao']}")
    versiculo = st.text_input("📖 Versículo Base (Ex: João 3:16)")
    tema = st.text_area("Tema do Post")
    
    if st.button("✨ Gerar Legenda ARA"):
        if versiculo and tema:
            with st.spinner("IA processando sua legenda..."):
                prompt = f"Social media da igreja {config['nome_exibicao']}. Use Bíblia ARA. Legenda +30 palavras, emojis pentecostais e hashtags: {config['hashtags_fixas']}. Tema: {tema}. Versículo: {versiculo}."
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                texto = res.choices[0].message.content
                
                st.code(texto, language=None)
                
                # CORREÇÃO DOS EMOJIS: Codifica o texto para link de URL
                texto_url = urllib.parse.quote(texto)
                link_wa = f"https://api.whatsapp.com/send?text={texto_url}"
                st.link_button("📲 Enviar para o WhatsApp", link_wa)
        else:
            st.warning("Preencha todos os campos.")
