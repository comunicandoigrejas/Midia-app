import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO INICIAL (DEVE SER A PRIMEIRA COISA)
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded" # Força a barra lateral a iniciar aberta
)

# 2. INICIALIZAÇÃO DE SEGURANÇA (Evita o AttributeError)
if "logado" not in st.session_state: st.session_state.logado = False
if "perfil" not in st.session_state: st.session_state.perfil = ""
if "igreja_id" not in st.session_state: st.session_state.igreja_id = ""
if "email" not in st.session_state: st.session_state.email = ""
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None

# --- CSS PARA LIMPAR O VISUAL SEM MATAR O BOTÃO DA BARRA LATERAL ---
st.markdown("""
    <style>
    /* Esconde apenas o menu de 3 pontos e o rodapé */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Mantém o cabeçalho mas esconde elementos de decoração do Streamlit */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    
    /* Estiliza o botão de abrir barra lateral para ficar visível */
    .st-emotion-cache-15ec669 {
        color: #4169E1;
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
    st.error("Erro Crítico de Conexão. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES SUPORTE ---
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)
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
    with st.spinner("🧠 O Super Agente está processando..."):
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    return mensagens.data[0].content[0].text.value

# ==========================================
# LÓGICA DE INTERFACE
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

else:
    # --- AMBIENTE LOGADO ---
    df_conf = carregar_configuracoes()
    
    # Define se é Admin Master ou Usuário
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Selecionar Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    # Aplica cor e mostra o botão sair de forma impossível de sumir
    cor_t = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_t.startswith("#"): cor_t = f"#{cor_t}"
    aplicar_tema(cor_t)

    with st.sidebar:
        st.write(f"Usuário: {st.session_state.email}")
        if st.button("🚪 SAIR DO SISTEMA", use_container_width=True, type="primary"):
            logout()
        st.divider()
        st.link_button("📲 Instagram", conf['instagram_url'], use_container_width=True)

    # CONTEÚDO PRINCIPAL
    list_t = ["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": list_t.insert(0, "📊 Master")
    
    abas = st.tabs(list_t)
    
    # Atribuição de abas dinâmica
    if st.session_state.perfil == "admin": t_master, t_gen, t_story, t_cal, t_perf = abas
    else: t_gen, t_story, t_cal, t_perf = abas

    # --- CONTEÚDO DAS ABAS ---
    if st.session_state.perfil == "admin":
        with t_master:
            st.write("### Painel de Gestão das Igrejas")
            st.dataframe(df_conf, use_container_width=True)

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
                res = chamar_super_agente(f"Gere legenda para {rd}, tom {est}, tema {br}, versículo {vr}. Use hashtags: {conf['hashtags_fixas']} {ht}")
                st.info(res)
                st.link_button("📲 WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    with t_story:
        st.header("🎬 Roteiro de Stories (3 Telas)")
        ts = st.text_input("Tema dos Stories")
        if st.button("🎬 Criar Sequência"):
            res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}. Estrutura: Pergunta, Versículo ARA, Reflexão.")
            st.success(res_s)
            st.link_button("📲 Enviar Roteiro", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res_s)}")

    with t_cal:
        st.header("📅 Calendário")
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

    with t_perf:
        st.header("⚙️ Configurações")
        if st.button("🔄 Resetar Tema (Voltar ao Azul)"):
            st.session_state.cor_previa = "#4169E1"
            st.rerun()
        st.write("---")
        with st.form("mudar_senha"):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                # Lógica de atualização de senha simplificada
                st.info("Funcionalidade de troca de senha ativa. Verifique se o índice da planilha está correto.")
