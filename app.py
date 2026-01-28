import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(
    page_title="Comunicando Igrejas Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="auto"
)

# 2. INICIALIZAÇÃO DE ESTADO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS: INTERFACE BLINDADA (SEM FORK/GITHUB E COM BOTÃO SIDEBAR) ---
st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"], .stAppDeployButton, #MainMenu { display: none !important; }
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: inherit !important; }
    footer { visibility: hidden !important; }
    .block-container { padding-top: 2rem !important; }
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

# --- FUNÇÕES DE APOIO ---
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def aplicar_tema(cor):
    st.markdown(f"""<style>
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}
    </style>""", unsafe_allow_html=True)

def chamar_super_agente(comando):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=comando)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    with st.spinner("🧠 O Super Agente está processando sua estratégia..."):
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
        if st.form_submit_button("Acessar Painel"):
            df_u = carregar_usuarios()
            u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
            if not u.empty:
                status_raw = u.iloc[0]['status']
                status_db = str(status_raw).strip().lower() if pd.notnull(status_raw) else "inativo"
                if status_db == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                    st.session_state.igreja_id = u.iloc[0]['igreja_id']
                    st.session_state.email = em
                    st.rerun()
                else: st.error("🚫 Conta inativa. Procure o suporte.")
            else: st.error("❌ E-mail ou senha incorretos.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    if st.session_state.perfil == "admin":
        st.sidebar.subheader("👑 Painel Master")
        igreja_nome = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_nome].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]

    # Definição de Cor (Evita NameError)
    cor_atual = st.session_state.cor_previa if st.session_state.cor_previa else str(conf['cor_tema'])
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"
    aplicar_tema(cor_atual)

    with st.sidebar:
        st.subheader(f"⛪ {conf['nome_exibicao']}")
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.link_button("📸 Instagram", str(conf['instagram_url']), use_container_width=True)

    # ABAS
    lista_abas = ["✨ Legendas", "🎬 Stories", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": lista_abas.insert(0, "📊 Master")
    obj_abas = st.tabs(lista_abas)

    if st.session_state.perfil == "admin": t_master, t_gen, t_story, t_perf = obj_abas
    else: t_gen, t_story, t_perf = obj_abas

    # --- ABA MASTER ---
    if st.session_state.perfil == "admin":
        with t_master:
            st.header("📊 Gestão Master")
            st.dataframe(df_conf, use_container_width=True, hide_index=True)

    # --- ABA 1: LEGENDAS (COMPLETA) ---
    with t_gen:
        st.header("✨ Gerador de Conteúdo ARA")
        
        # Grid de Opções
        col1, col2 = st.columns(2)
        with col1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn", "WhatsApp"])
            tom = st.selectbox("Tom da Mensagem", ["Inspirador", "Pentecostal", "Jovem", "Teológico", "Informativo"])
        with col2:
            ver = st.text_input("📖 Versículo Base (ARA)", placeholder="Ex: João 10:10")
            hashtags_extra = st.text_input("🏷️ Hashtags Extras", placeholder="Ex: #fé #church")
        
        tema_post = st.text_area("📝 Descreva o tema da postagem (O que aconteceu ou vai acontecer?)")
        
        if st.button("🚀 Criar Minha Legenda"):
            if tema_post:
                prompt_completo = (
                    f"Atue como um especialista em mídias sociais para igrejas. "
                    f"Gere uma legenda para {rede}, com tom {tom}. "
                    f"O tema é: {tema_post}. "
                    f"Inclua o versículo: {ver}. "
                    f"Use a Bíblia Almeida Revista e Atualizada (ARA). "
                    f"Hashtags obrigatórias: {conf['hashtags_fixas']} {hashtags_extra}"
                )
                resultado = chamar_super_agente(prompt_completo)
                st.markdown("---")
                st.subheader("📝 Sugestão do Super Agente:")
                st.info(resultado)
                st.link_button("📲 Enviar para WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")
            else:
                st.warning("Por favor, descreva o tema da postagem.")

    # --- ABA 2: STORIES ---
    with t_story:
        st.header("🎬 Roteiro de Stories (3 Telas)")
        t_story_input = st.text_input("Qual o tema da sequência?")
        if st.button("🎬 Gerar Roteiro"):
            if t_story_input:
                prompt_s = f"Crie um roteiro de 3 stories sobre {t_story_input} para a igreja {conf['nome_exibicao']}. Use emojis e Bíblia ARA."
                res_s = chamar_super_agente(prompt_s)
                st.success(res_s)
                st.link_button("📲 Enviar Roteiro", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res_s)}")

    # --- ABA 3: PERFIL ---
    with t_perf:
        st.header("⚙️ Personalização e Segurança")
        nova_cor = st.color_picker("🎨 Escolha a cor do seu painel:", cor_atual)
        if st.button("🖌️ Aplicar Cor"):
            st.session_state.cor_previa = nova_cor
            st.rerun()
        
        st.divider()
        with st.form("f_senha"):
            st.subheader("🔑 Alterar Senha")
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_at:
                    df_u.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("✅ Senha alterada!")
                else: st.error("❌ Erro na senha atual.")
