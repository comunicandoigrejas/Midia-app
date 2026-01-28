import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded" # Garante que a barra lateral comece aberta
)

# 2. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO (Evita erros de Atributo)
if "logado" not in st.session_state: st.session_state.logado = False
if "perfil" not in st.session_state: st.session_state.perfil = ""
if "igreja_id" not in st.session_state: st.session_state.igreja_id = ""
if "email" not in st.session_state: st.session_state.email = ""
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None

# --- CSS PARA REMOVER FORK, GITHUB E MENU (VISUAL PROFISSIONAL) ---
st.markdown("""
    <style>
    /* Esconde o cabeçalho inteiro (remove Fork, GitHub e Menu) */
    header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0% !important;
    }
    
    /* Remove o rodapé 'Made with Streamlit' */
    footer {
        visibility: hidden;
    }

    /* Ajusta o topo da página para não ficar colado após esconder o header */
    .block-container {
        padding-top: 2rem !important;
    }

    /* Mantém a barra lateral funcional e limpa */
    [data-testid="stSidebar"] {
        padding-top: 0rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES SEGURAS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de Conexão. Verifique os Secrets (Chave API, ID do Assistente e Planilha).")
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
    t1, t2 = st.tabs(["Entrar", "Recuperar Senha"])
    
    with t1:
        with st.form("login_form"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Painel"):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                if not u.empty:
                    st.session_state.logado = True
                    st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                    st.session_state.igreja_id = u.iloc[0]['igreja_id']
                    st.session_state.email = em
                    st.rerun()
                else: st.error("E-mail ou senha incorretos.")
    
    with t2:
        st.write("Esqueceu seus dados? Entre em contato com o suporte.")
        st.link_button("📲 Suporte WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO (DASHBOARD)
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Diferencia Admin Master de Usuário
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    # Aplica o tema de cor da igreja
    cor_t = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_t.startswith("#"): cor_t = f"#{cor_t}"
    aplicar_tema(cor_t)

    # BARRA LATERAL
    with st.sidebar:
        if st.button("🚪 SAIR DO SISTEMA", use_container_width=True, type="primary"):
            logout()
        st.divider()
        st.link_button("📸 Instagram da Igreja", conf['instagram_url'], use_container_width=True)
        st.caption(f"Conectado: {st.session_state.email}")

    # CONTEÚDO PRINCIPAL (ABAS)
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

    # --- ABA 1: GERADOR DE LEGENDAS ---
    with t_gen:
        st.header("✨ Gerador de Legendas")
        col1, col2 = st.columns(2)
        with col1:
            rd = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn"])
            est = st.selectbox("Tom", ["Inspiradora", "Pentecostal", "Jovem", "Teológica"])
        with col2:
            vr = st.text_input("📖 Versículo (ARA)")
            ht = st.text_input("Hashtags Extras")
        
        br = st.text_area("Descreva o tema da postagem")
        if st.button("🚀 Criar Legenda com Super Agente"):
            if br:
                resultado = chamar_super_agente(f"Legenda para {rd}, tom {est}, tema {br}, versículo {vr}. Use: {conf['hashtags_fixas']} {ht}")
                st.info(resultado)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")

    # --- ABA 2: ROTEIRO DE STORIES ---
    with t_story:
        st.header("🎬 Sequência de 3 Stories")
        ts = st.text_input("Qual o tema dos Stories?")
        if st.button("🎬 Gerar Roteiro Estratégico"):
            if ts:
                res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}. Siga: Pergunta, Versículo ARA, Reflexão.")
                st.success(res_s)
                st.link_button("📲 Enviar Roteiro", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res_s)}")

    # --- ABA 3: CALENDÁRIO ---
    with t_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Novo Agendamento"):
            with st.form("f_cal"):
                dp = st.date_input("Data da Postagem")
                tp = st.text_input("Tema do Conteúdo")
                if st.form_submit_button("Salvar no Calendário"):
                    nv = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": dp.strftime('%Y-%m-%d'), "rede_social": "Geral", "tema": tp, "status": "Pendente"}])
                    conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=nv)
                    st.rerun()
        df_c = carregar_calendario()
        st.dataframe(df_c[df_c['igreja_id'] == conf['igreja_id']], use_container_width=True, hide_index=True)

    # --- ABA 4: PERFIL ---
    with t_perf:
        st.header("⚙️ Conta e Segurança")
        if st.button("🔄 Resetar Cor do Painel"):
            st.session_state.cor_previa = "#4169E1"
            st.rerun()
        
        st.divider()
        with st.form("update_pw"):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_at:
                    df_u.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("Senha atualizada com sucesso!")
                else: st.error("A senha atual está incorreta.")
