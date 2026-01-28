import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO INICIAL (FORÇA A BARRA LATERAL A APARECER)
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 2. INICIALIZAÇÃO DE SEGURANÇA (SESSION STATE)
if "logado" not in st.session_state: st.session_state.logado = False
if "perfil" not in st.session_state: st.session_state.perfil = ""
if "igreja_id" not in st.session_state: st.session_state.igreja_id = ""
if "email" not in st.session_state: st.session_state.email = ""
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None

# --- CSS ESTRATÉGICO: ESCONDE O DESNECESSÁRIO, MANTÉM O BOTÃO LATERAL ---
st.markdown("""
    <style>
    /* 1. Esconde o botão de 'Fork' e o ícone do GitHub no canto direito */
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    
    /* 2. Esconde o menu de 3 pontos (MainMenu) */
    #MainMenu {
        display: none !important;
    }

    /* 3. Torna o cabeçalho transparente para manter o botão da sidebar visível */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
        color: inherit;
    }

    /* 4. Esconde o rodapé */
    footer {
        visibility: hidden;
    }

    /* 5. Ajusta o espaçamento do conteúdo */
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
    st.error("Erro de Conexão. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE SUPORTE ---
def carregar_usuarios(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes(): 
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def carregar_calendario():
    try: return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except: return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

def aplicar_tema(cor):
    st.markdown(f"""<style>
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}
    </style>""", unsafe_allow_html=True)

def logout():
    st.session_state.clear()
    st.rerun()

# --- FUNÇÃO DO SUPER AGENTE (ASSISTANTS API) ---
def chamar_super_agente(comando):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=comando)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    with st.spinner("🧠 O Super Agente está processando sua estratégia..."):
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run.status in ["failed", "cancelled", "expired"]:
                return "Erro ao processar. Tente novamente."
    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    return mensagens.data[0].content[0].text.value

# ==========================================
# INTERFACE DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    t1, t2 = st.tabs(["Entrar", "Recuperar Senha"])
    
    with t1:
        with st.form("login"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                if not u.empty:
                    st.session_state.logado = True
                    st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                    st.session_state.igreja_id = u.iloc[0]['igreja_id']
                    st.session_state.email = em
                    st.rerun()
                else: st.error("Dados incorretos.")
    with t2:
        st.link_button("🔑 Suporte WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Define visão de Admin ou Usuário
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    # Aplicação do Tema
    cor_t = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_t.startswith("#"): cor_t = f"#{cor_t}"
    aplicar_tema(cor_t)

    with st.sidebar:
        if st.button("🚪 SAIR DO SISTEMA", use_container_width=True, type="primary"):
            logout()
        st.divider()
        st.link_button("📲 Instagram", conf['instagram_url'], use_container_width=True)
        st.caption(f"Usuário: {st.session_state.email}")

    # CONTEÚDO PRINCIPAL
    list_t = ["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": list_t.insert(0, "📊 Master")
    
    abas = st.tabs(list_t)
    
    if st.session_state.perfil == "admin": t_master, t_gen, t_story, t_cal, t_perf = abas
    else: t_gen, t_story, t_cal, t_perf = abas

    # --- ABA MASTER ---
    if st.session_state.perfil == "admin":
        with t_master:
            st.header("📊 Gestão Master")
            st.dataframe(df_conf, use_container_width=True)

    # --- ABA 1: GERADOR ---
    with t_gen:
        st.header("✨ Gerador de Legendas (Super Agente)")
        c1, c2 = st.columns(2)
        with c1:
            rd = st.selectbox("Rede", ["Instagram", "Facebook", "LinkedIn"])
            est = st.selectbox("Tom", ["Inspiradora", "Pentecostal", "Jovem", "Teológica"])
        with c2:
            vr = st.text_input("📖 Versículo (Ex: João 1:1)")
            ht = st.text_input("Hashtags Extras")
        
        br = st.text_area("Tema do post")
        if st.button("🚀 Criar Legenda"):
            if br:
                res = chamar_super_agente(f"Gere legenda para {rd}, tom {est}, tema {br}, versículo {vr}. Use: {conf['hashtags_fixas']} {ht}")
                st.info(res)
                st.link_button("📲 WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    # --- ABA 2: STORIES ---
    with t_story:
        st.header("🎬 Roteiro de Stories (3 Telas)")
        ts = st.text_input("Tema dos Stories")
        if st.button("🎬 Criar Sequência"):
            res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}. Estrutura: Pergunta, Versículo ARA, Reflexão.")
            st.success(res_s)
            st.link_button("📲 Enviar Roteiro", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res_s)}")

    # --- ABA 3: CALENDÁRIO ---
    with t_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Agendar"):
            with st.form("f_cal"):
                dp = st.date_input("Data")
                tp = st.text_input("Assunto")
                if st.form_submit_button("Salvar"):
                    nv = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": dp.strftime('%Y-%m-%d'), "rede_social": "Geral", "tema": tp, "status": "Pendente"}])
                    conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=nv)
                    st.rerun()
        df_c = carregar_calendario()
        st.dataframe(df_c[df_c['igreja_id'] == conf['igreja_id']], use_container_width=True, hide_index=True)

    # --- ABA 4: PERFIL ---
    with t_perf:
        st.header("⚙️ Configurações")
        with st.form("mudar_senha"):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_at:
                    df_u.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("Senha atualizada!")
                else: st.error("Dados incorretos.")
