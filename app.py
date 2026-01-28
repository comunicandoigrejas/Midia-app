import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÕES E ESTILO DINÂMICO
st.set_page_config(page_title="Comunicando Igrejas Pro", page_icon="⚡", layout="wide")

# Inicializa sessão
if "logado" not in st.session_state:
    st.session_state.logado = False

# 2. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de conexão. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_usuarios():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def carregar_calendario():
    # Garante que a aba existe, senão retorna um DataFrame vazio
    try:
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except:
        return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

# --- INJETOR DE TEMA PERSONALIZADO ---
def aplicar_tema(cor):
    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 10px; border: none; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white; border-radius: 5px; }}
        header {{visibility: hidden;}} footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# TELA DE LOGIN & RECUPERAÇÃO
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    aba_login, aba_esqueci = st.tabs(["Acessar Painel", "Esqueci minha senha"])
    
    with aba_login:
        with st.form("login_form"):
            email_i = st.text_input("E-mail")
            senha_i = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                df_u = carregar_usuarios()
                user = df_u[(df_u['email'].str.lower() == email_i.lower()) & (df_u['senha'].astype(str) == str(senha_i))]
                if not user.empty:
                    st.session_state.logado = True
                    st.session_state.igreja_id = user.iloc[0]['igreja_id']
                    st.session_state.perfil = user.iloc[0]['perfil']
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

    with aba_esqueci:
        st.write("Dificuldades para acessar? Solicite uma nova senha ao nosso suporte.")
        st.link_button("🔑 Recuperar Senha via WhatsApp", "https://wa.me/SEUNUMERO?text=Olá, esqueci minha senha no painel.")

# ==========================================
# AMBIENTE LOGADO (DASHBOARD)
# ==========================================
else:
    df_config = carregar_configuracoes()
    # Busca a linha da igreja logada
    config_row = df_config[df_config['igreja_id'] == st.session_state.igreja_id]
    
    if config_row.empty:
        st.error("Configurações da igreja não encontradas.")
        st.stop()
    
    config = config_row.iloc[0]
    
    # Tratamento de Cor com Fallback Seguro
    cor_atual = str(config['cor_tema']).strip() if pd.notnull(config['cor_tema']) else "#4169E1"
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"
    aplicar_tema(cor_atual)

    st.sidebar.title(f"📱 {config['nome_exibicao']}")
    with st.sidebar:
        st.write(f"Conectado como: {st.session_state.perfil}")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.logado = False
            st.rerun()

    # ABAS DO APP
    tab_gerador, tab_stories, tab_calendario, tab_perfil = st.tabs([
        "✨ Gerador de Legendas", "📱 Sequência de Stories", "📅 Calendário", "🎨 Personalizar"
    ])

    # --- ABA 1: GERADOR TURBINADO ---
    with tab_gerador:
        st.header("Criador de Postagens Profissionais")
        c1, c2 = st.columns(2)
        with c1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn", "WhatsApp Status"])
            estilo = st.selectbox("Linguagem", ["Inspiradora", "Pentecostal", "Teológica/Formal", "Jovem", "Urgente"])
        with c2:
            ver = st.text_input("📖 Versículo Base (ARA)")
            extras = st.text_input("Hashtags Extras (separe por espaço)")
        
        tema = st.text_area("Descrição da postagem")
        
        if st.button("✨ Gerar Conteúdo (+50 palavras)"):
            if tema:
                with st.spinner("IA criando estratégia..."):
                    prompt = f"Atue como Social Media Expert Cristão. Crie uma legenda para {rede} com abordagem {estilo}. Use Bíblia ARA. Mínimo de 50 palavras. Tema: {tema}. Versículo: {ver}. Finalize com as hashtags da igreja: {config['hashtags_fixas']} e extras: {extras}."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                    texto = res.choices[0].message.content
                    st.code(texto, language=None)
                    st.link_button("📲 Enviar para WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto)}")

    # --- ABA 2: STORIES ---
    with tab_stories:
        st.header("Roteiro para Stories")
        tema_s = st.text_input("Assunto da sequência")
        if st.button("🎬 Criar Roteiro"):
            with st.spinner("Planejando cenas..."):
                prompt_s = f"Crie um roteiro de 4 stories para a igreja {config['nome_exibicao']} sobre {tema_s}. Story 1: Gancho, 2: Conteúdo, 3: Interação, 4: Chamada."
                res_s = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                st.write(res_s.choices[0].message.content)

    # --- ABA 3: CALENDÁRIO ---
    with tab_calendario:
        st.header("Cronograma de Postagens")
        df_cal = carregar_calendario()
        cal_igreja = df_cal[df_cal['igreja_id'] == st.session_state.igreja_id]
        if not cal_igreja.empty:
            st.dataframe(cal_igreja[['data', 'rede_social', 'tema', 'status']], use_container_width=True)
        else:
            st.info("Nenhuma postagem agendada nesta igreja.")

    # --- ABA 4: PERSONALIZAÇÃO (AS 20 CORES) ---
    with tab_perfil:
        st.header("🎨 Identidade do Painel")
        paleta = {
            "Azul Catedral": "#2C3E50", "Vinho Clássico": "#7B241C", "Verde Oliva": "#556B2F",
            "Roxo Imperial": "#4A235A", "Bronze": "#A0522D", "Grafite": "#212121",
            "Azul Petróleo": "#0E4B5A", "Ultravioleta": "#6C5CE7", "Rosa Chá": "#E84393",
            "Cinza Concreto": "#636E72", "Laranja Fogo": "#E17055", "Amarelo Glória": "#FBC531",
            "Azul Royal": "#0984E3", "Vermelho Vivo": "#D63031", "Verde Menta": "#00B894",
            "Areia": "#C2B280", "Terracota": "#E2725B", "Azul Céu": "#87CEEB",
