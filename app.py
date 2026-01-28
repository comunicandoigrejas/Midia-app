import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd

# --- BLOCO DE DIAGNÓSTICO TEMPORÁRIO ---
st.write("### 🔍 Diagnóstico de Conexão")
if "connections" in st.secrets:
    st.write("✅ Gaveta 'connections' encontrada!")
    if "gsheets" in st.secrets["connections"]:
        st.write("✅ Pasta 'gsheets' encontrada!")
        if "spreadsheet" in st.secrets["connections"]["gsheets"]:
            st.write("✅ Link 'spreadsheet' encontrado!")
        else:
            st.error("❌ Link 'spreadsheet' NÃO encontrado dentro de gsheets.")
    else:
        st.error("❌ Pasta 'gsheets' NÃO encontrada dentro de connections.")
else:
    st.error("❌ Gaveta 'connections' NÃO encontrada nos Secrets.")
# ---------------------------------------

# 1. Configurações Iniciais
st.set_page_config(page_title="Comunicando Igrejas - Painel", layout="wide")

# 2. Conexão e Segurança
# Buscamos a URL uma única vez para usar no app todo
try:
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("🚨 Erro nos Secrets: O link da planilha não foi encontrado ou está formatado errado.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- FUNÇÕES DE BANCO DE DADOS (AGORA COM LINK EXPLÍCITO) ---
def carregar_usuarios():
    # Passamos o link diretamente aqui para não ter erro
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios")

def carregar_configuracoes():
    # Passamos o link diretamente aqui também
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes")

# ... (Restante do seu código de login e abas segue abaixo)

# --- LÓGICA DE ACESSO ---
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    st.subheader("Painel de Gestão de Mídia")
    
    with st.form("login_form"):
        email_input = st.text_input("E-mail")
        senha_input = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Acessar Sistema")
        
        if submit:
            df_u = carregar_usuarios()
            user = df_u[(df_u['email'] == email_input) & (df_u['senha'] == str(senha_input))]
            
            if not user.empty:
                if user.iloc[0]['status'] == 'ativo':
                    st.session_state.logado = True
                    st.session_state.email = email_input
                    st.session_state.perfil = user.iloc[0]['perfil']
                    st.session_state.igreja_id = user.iloc[0]['igreja_id']
                    st.rerun()
                else:
                    st.error("Sua assinatura está inativa. Entre em contato com o suporte.")
            else:
                st.error("E-mail ou senha incorretos.")
else:
    # --- AMBIENTE LOGADO ---
    df_config = carregar_configuracoes()
    # Busca config da igreja específica (ou de todas se for Master)
    if st.session_state.perfil == "admin":
        igreja_nome = "MASTER ADMIN"
    else:
        config_igreja = df_config[df_config['igreja_id'] == st.session_state.igreja_id].iloc[0]
        igreja_nome = config_igreja['nome_exibicao']

    with st.sidebar:
        st.title(f"📱 {igreja_nome}")
        if st.session_state.perfil != "admin":
            st.link_button("⛪ Instagram da Igreja", config_igreja['instagram_url'])
        st.divider()
        st.link_button("🔧 By Comunicando Igrejas", "https://www.instagram.com/comunicandoigrejas/")
        if st.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()

    # --- DEFINIÇÃO DAS ABAS ---
    if st.session_state.perfil == "admin":
        abas = st.tabs(["👑 Master Admin", "✨ Gerador de Conteúdo"])
    else:
        abas = st.tabs(["✨ Gerador de Conteúdo", "⚙️ Meu Perfil"])

    # ---------------------------------------------------------
    # ABA MASTER (SÓ O DONO VÊ)
    # ---------------------------------------------------------
    if st.session_state.perfil == "admin":
        with abas[0]:
            st.header("📊 Gestão de Clientes")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total de Igrejas", len(df_config))
            with col_b:
                df_u = carregar_usuarios()
                ativos = len(df_u[df_u['status'] == 'ativo'])
                st.metric("Usuários Ativos", ativos)

            st.subheader("Igrejas Cadastradas")
            st.dataframe(df_config, use_container_width=True)

            st.subheader("Gerenciar Usuários")
            st.dataframe(df_u, use_container_width=True)
            
            st.info("💡 Para adicionar ou remover igrejas, basta editar sua Planilha Google e atualizar esta página.")

    # ---------------------------------------------------------
    # ABA GERADOR (TODOS VÊEM)
    # ---------------------------------------------------------
    indice_gerador = 1 if st.session_state.perfil == "admin" else 0
    with abas[indice_gerador]:
        st.header("🎨 Criador de Conteúdo")
        
        # Se for admin, ele pode escolher qual igreja simular
        if st.session_state.perfil == "admin":
            igreja_selecionada = st.selectbox("Simular Igreja:", df_config['nome_exibicao'].tolist())
            config_atual = df_config[df_config['nome_exibicao'] == igreja_selecionada].iloc[0]
        else:
            config_atual = config_igreja

        st.info(f"Gerando para: **{config_atual['nome_exibicao']}**")
        
        # Aqui entra o seu código original da IA (ARA, 30 palavras, Hashtags Fixas)
        # Exemplo de como usar a hashtag da planilha:
        hashtags_da_igreja = config_atual['hashtags_fixas']
        
        # ... [Restante do seu código da OpenAI que já funciona] ...
        st.write(f"Hashtags que serão usadas: {hashtags_da_igreja}")
