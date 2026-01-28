import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA (Sempre o primeiro comando)
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INICIALIZAÇÃO DE SEGURANÇA (Prevenção de AttributeError)
if "logado" not in st.session_state: st.session_state.logado = False
if "perfil" not in st.session_state: st.session_state.perfil = ""
if "igreja_id" not in st.session_state: st.session_state.igreja_id = ""
if "email" not in st.session_state: st.session_state.email = ""
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None

# --- CSS AGRESSIVO: ESCONDE FORK, GITHUB, MENU E RODAPÉ ---
st.markdown("""
    <style>
    /* Esconde o botão de Fork, Ícone do GitHub e o Menu de 3 pontos */
    [data-testid="stHeaderActionElements"], 
    .st-emotion-cache-12fmjuu, 
    #MainMenu {
        display: none !important;
    }
    
    /* Torna o cabeçalho invisível mas mantém o botão da sidebar */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: transparent !important;
    }

    /* Remove o rodapé 'Made with Streamlit' */
    footer {
        visibility: hidden !important;
    }

    /* Ajusta o espaçamento para o conteúdo não subir demais */
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
    st.error(f"⚠️ Erro de Configuração: {e}")
    st.stop()

# --- FUNÇÕES DE APOIO ---
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

def chamar_super_agente(comando):
    # Cria a Thread (conversa)
    thread = client.beta.threads.create()
    
    # Adiciona a mensagem do usuário
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=comando
    )
    
    # Executa o Agente
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID
    )
    
    # Polling (Espera a resposta)
    with st.spinner("🧠 O Super Agente está processando sua estratégia..."):
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run.status in ["failed", "cancelled", "expired"]:
                return "Erro: O Agente falhou. Verifique as instruções na OpenAI."
    
    # Recupera a resposta final
    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    return mensagens.data[0].content[0].text.value

# ==========================================
# INTERFACE DE LOGIN (COM BLOQUEIO REAL)
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
                    # Lógica de bloqueio: remove espaços e valida se está 'ativo'
                    status_raw = u.iloc[0]['status']
                    status_db = str(status_raw).strip().lower() if pd.notnull(status_raw) else "inativo"
                    
                    if status_db == 'ativo':
                        st.session_state.logado = True
                        st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = u.iloc[0]['igreja_id']
                        st.session_state.email = em
                        st.rerun()
                    else:
                        st.error(f"🚫 ACESSO BLOQUEADO: Sua conta está '{status_db}'. Procure o suporte.")
                else:
                    st.error("❌ E-mail ou senha incorretos.")
    with t2:
        st.link_button("📲 Suporte WhatsApp", "https://wa.me/551937704733")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Define Visão de Admin ou Usuário
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Modo Administrador")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.subheader(f"⛪ {conf['nome_exibicao']}")

    # Aplicação de Cores
    cor_t = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_t.startswith("#"): cor_t = f"#{cor_t}"
    aplicar_tema(cor_t)

    with st.sidebar:
        if st.button("🚪 SAIR DO SISTEMA", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.link_button("📲 Instagram", conf['instagram_url'], use_container_width=True)
        st.caption(f"Usuário: {st.session_state.email}")

    # ABAS PRINCIPAIS
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

    # --- ABA 2: ROTEIRO DE STORIES ---
    with t_story:
        st.header("🎬 Sequência de 3 Stories")
        ts = st.text_input("Qual o tema dos Stories?")
        if st.button("🎬 Criar Roteiro Estratégico"):
            if ts:
                prompt_s = f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}. Regra: Pergunta, Versículo ARA, Reflexão."
                resultado_s = chamar_super_agente(prompt_s)
                st.success(resultado_s) # Garante que o texto apareça na tela
                st.link_button("📲 Enviar Roteiro", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado_s)}")

    # --- ABA 3: CALENDÁRIO ---
    with t_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Novo Post"):
            with st.form("form_calendario"):
                dp = st.date_input("Data", datetime.now())
                tp = st.text_input("Assunto")
                if st.form_submit_button("Salvar"):
                    # Força o uso da URL dos Secrets para evitar erro de 'Spreadsheet must be specified'
                    url_segura = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    nv = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": dp.strftime('%Y-%m-%d'), "rede_social": "Geral", "tema": tp, "status": "Pendente"}])
                    conn.create(spreadsheet=url_segura, worksheet="calendario", data=nv)
                    st.success("Salvo!")
                    st.rerun()
        
        df_c = carregar_calendario()
        df_filtrado = df_c[df_c['igreja_id'].astype(str) == str(conf['igreja_id'])]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # --- ABA 4: PERFIL ---
    with t_perf:
        st.header("⚙️ Configurações")
        st.write(f"Conectado como: **{st.session_state.email}**")
        if st.button("🔄 Atualizar Senha (Suporte)"):
            st.info("Entre em contato com o suporte para redefinir sua senha com segurança.")
