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
    initial_sidebar_state="auto" # Permite que o botão de recolher funcione
)

# 2. INICIALIZAÇÃO DE ESTADO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS DE PROTEÇÃO MÁXIMA: ELIMINA CABEÇALHO E RODAPÉ ---
st.markdown("""
    <style>
    /* Esconde o cabeçalho inteiro (remove Fork, GitHub,) */
    [data-testid="stHeader"] {
        display: none !important;
    }

    /* Remove o rodapé 'Made with Streamlit' */
    footer {
        visibility: hidden !important;
    }

    /* Mantém o cabeçalho transparente para o botão '>' aparecer */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: inherit !important;
    }

    /* Esconde elementos específicos caso o header tente reaparecer */
    #MainMenu, .stAppDeployButton, [data-testid="stHeaderActionElements"] {
        display: none !important;
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
        if st.form_submit_button("Acessar Sistema"):
            df_u = carregar_usuarios()
            u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
            if not u.empty:
                status_db = str(u.iloc[0]['status']).strip().lower() if pd.notnull(u.iloc[0]['status']) else "inativo"
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
# ... (código anterior do login)
else:
    # Este bloco só roda se o usuário estiver logado
    df_conf = carregar_configuracoes()
    
    # A BARRA LATERAL PRECISA ESTAR ALINHADA AQUI (4 espaços para dentro do else)
    with st.sidebar:
        st.subheader(f"⛪ {conf['nome_exibicao']}")
        
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
            
        st.divider()
        st.link_button("📸 Instagram", conf['instagram_url'], use_container_width=True)
    
    # O restante das abas também segue este alinhamento
    abas = st.tabs(["✨ Legendas", "🎬 Stories", "⚙️ Perfil"])
    # ...
        
        # Botão de Logout
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
            
        st.divider()
        
        # Link para o Instagram da Igreja
        st.link_button("📸 Instagram da Igreja", conf['instagram_url'], use_container_width=True)
        
        st.caption(f"Usuário: {st.session_state.email}")

    abas = st.tabs(["✨ Legendas", "🎬 Stories", "⚙️ Perfil"])
    t_gen, t_story, t_perf = abas

  # --- ABA 1: GERADOR DE LEGENDAS ---
    with t_gen:
        st.header("✨ Gerador ARA (Super Agente)")
        col1, col2 = st.columns(2)
        with col1:
            rd = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn"])
            est = st.selectbox("Tom", ["Inspiradora", "Pentecostal", "Jovem", "Teológica"])
        with col2:
            vr = st.text_input("📖 Versículo (ARA)")
            ht = st.text_input("Hashtags Extras")
        
        br = st.text_area("Descreva o tema da postagem")
        if st.button("🚀 Criar Legenda"):
            if br:
                prompt = f"Gere legenda para {rd}, tom {est}, tema {br}, versículo {vr}. Use hashtags: {conf['hashtags_fixas']} {ht}"
                resultado = chamar_super_agente(prompt)
                st.info(resultado) # Garante que o texto apareça na tela
                st.link_button("📲 Enviar p/ WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")
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
