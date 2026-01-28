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
    initial_sidebar_state="collapsed" # Inicia sem sidebar
)

# 2. INICIALIZAÇÃO DE ESTADO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS ULTRA-CLEAN: REMOVE TUDO (SIDEBAR, HEADER E GITHUB) ---
st.markdown("""
    <style>
    /* 1. Esconde o Header inteiro (Fork, GitHub, Menu somem aqui) */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* 2. Esconde a barra lateral e o botão de controle nativo */
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* 3. Remove o rodapé */
    footer {
        visibility: hidden !important;
    }

    /* 4. Ajusta o conteúdo para começar do topo e centraliza o título */
    .block-container {
        padding-top: 2rem !important;
        max-width: 80% !important;
        margin: auto;
    }

    .church-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 2rem;
        font-family: 'Inter', sans-serif;
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
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

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
    st.markdown("<h1 style='text-align: center;'>🚀 Comunicando Igrejas</h1>", unsafe_allow_html=True)
    with st.container():
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.form("login"):
                em = st.text_input("E-mail")
                se = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Sistema", use_container_width=True):
                    df_u = carregar_usuarios()
                    u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                    if not u.empty:
                        if str(u.iloc[0]['status']).strip().lower() == 'ativo':
                            st.session_state.logado = True
                            st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                            st.session_state.igreja_id = u.iloc[0]['igreja_id']
                            st.session_state.email = em
                            st.rerun()
                        else: st.error("🚫 Conta inativa.")
                    else: st.error("❌ Dados incorretos.")

# ==========================================
# AMBIENTE LOGADO (SEM BARRA LATERAL)
# ==========================================
else:
    df_conf = carregar_configuracoes()
    # No modo sem sidebar, o Admin seleciona a igreja no topo se necessário
    if st.session_state.perfil == "admin":
        conf_list = df_conf['nome_exibicao'].tolist()
        escolha = st.selectbox("💎 Gestor Master: Selecione a Igreja", conf_list)
        conf = df_conf[df_conf['nome_exibicao'] == escolha].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]

    # Cor e Tema
    cor_atual = st.session_state.cor_previa if st.session_state.cor_previa else str(conf['cor_tema'])
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"
    
    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor_atual} !important; color: white !important; font-weight: bold; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor_atual} !important; color: white !important; }}
        .church-title {{ color: {cor_atual}; }}
        </style>
        <div class="church-title">⛪ {conf['nome_exibicao']}</div>
    """, unsafe_allow_html=True)

    # NAVEGAÇÃO POR ABAS (Substitui a Sidebar)
    t_gen, t_story, t_insta, t_perf, t_sair = st.tabs([
        "✨ Legendas", 
        "🎬 Stories", 
        "📸 Instagram", 
        "⚙️ Perfil", 
        "🚪 Sair"
    ])

    # --- ABA 1: LEGENDAS ---
    with t_gen:
        st.header("✨ Gerador de Conteúdo ARA")
        c1, c2 = st.columns(2)
        with c1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "WhatsApp"])
            tom = st.selectbox("Tom", ["Inspirador", "Pentecostal", "Jovem", "Teológico"])
        with c2:
            ver = st.text_input("📖 Versículo Base (ARA)", placeholder="Ex: João 10:10")
            ht = st.text_input("🏷️ Hashtags Extras")
        
        tema = st.text_area("📝 O que vamos criar hoje?")
        if st.button("🚀 Gerar Legenda Premium"):
            if tema:
                res = chamar_super_agente(f"Gere legenda para {rede}, tom {tom}, tema {tema}, versículo {ver}. ARA. Hashtags: {conf['hashtags_fixas']} {ht}")
                st.info(res)
                st.link_button("📲 Enviar para WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    # --- ABA 2: STORIES ---
    with t_story:
        st.header("🎬 Roteiro de Stories")
        ts = st.text_input("Tema da sequência:")
        if st.button("🎬 Criar Roteiro"):
            if ts:
                res_s = chamar_super_agente(f"Crie 3 stories sobre {ts} para {conf['nome_exibicao']}.")
                st.success(res_s)

    # --- ABA 3: INSTAGRAM (Link Direto) ---
    with t_insta:
        st.header("📸 Link do Instagram")
        st.write(f"Acesse o perfil oficial da **{conf['nome_exibicao']}**")
        st.link_button("🚀 Abrir Instagram Agora", str(conf['instagram_url']), use_container_width=True)

    # --- ABA 4: PERFIL ---
    with t_perf:
        st.header("⚙️ Configurações e Identidade")
        nova_cor = st.color_picker("Personalizar cor do sistema:", cor_atual)
        if st.button("🖌️ Salvar Nova Cor"):
            st.session_state.cor_previa = nova_cor
            st.rerun()
        
        st.divider()
        with st.form("senha_form"):
            st.subheader("🔒 Alterar Senha")
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Credenciais"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_at:
                    df_u.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("✅ Senha atualizada!")
                else: st.error("❌ Senha atual incorreta.")

    # --- ABA 5: SAIR ---
    with t_sair:
        st.header("🚪 Encerrar Sessão")
        st.warning("Deseja realmente sair do sistema?")
        if st.button("🔴 Confirmar Logout e Sair"):
            st.session_state.clear()
            st.rerun()
