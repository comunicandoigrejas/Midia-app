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
    initial_sidebar_state="collapsed"
)

# 2. INICIALIZAÇÃO DE ESTADO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None
for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS: TUDO CENTRALIZADO E OCULTANDO O HEADER DO GITHUB ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    footer { visibility: hidden !important; }

    .block-container {
        padding-top: 2rem !important;
        max-width: 85% !important;
        margin: auto;
    }

    .church-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 1.5rem;
        font-family: 'Inter', sans-serif;
        text-transform: uppercase;
        letter-spacing: -1px;
    }
    
    .stTabs { display: flex; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"]
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro nos Secrets.")
    st.stop()

# --- FUNÇÕES SUPORTE ---
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def chamar_super_agente(comando):
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=comando)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
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
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        with st.form("login"):
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Painel", use_container_width=True):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                if not u.empty and str(u.iloc[0]['status']).strip().lower() == 'ativo':
                    st.session_state.logado, st.session_state.perfil, st.session_state.igreja_id, st.session_state.email = True, str(u.iloc[0]['perfil']).strip().lower(), u.iloc[0]['igreja_id'], em
                    st.rerun()
                else: st.error("Acesso negado.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    if st.session_state.perfil == "admin":
        escolha = st.selectbox("💎 Gestor Master", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == escolha].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]

    cor_atual = st.session_state.cor_previa if st.session_state.cor_previa else str(conf['cor_tema'])
    if not cor_atual.startswith("#"): cor_atual = f"#{cor_atual}"
    
    # DNA Salvo para uso interno
    dna_salvo = str(conf['dna_ministerial']) if 'dna_ministerial' in conf and pd.notnull(conf['dna_ministerial']) else "Linguagem cristã padrão."

    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor_atual} !important; color: white !important; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor_atual} !important; color: white !important; border-radius: 5px; }}
        .church-title {{ color: {cor_atual}; }}
        </style>
        <div class="church-title">⛪ {conf['nome_exibicao']}</div>
    """, unsafe_allow_html=True)

    t_gen, t_story, t_insta, t_perf, t_sair = st.tabs(["✨ Legendas", "🎬 Stories", "📸 Instagram", "⚙️ Perfil", "🚪 Sair"])

    # --- ABA LEGENDAS ---
    with t_gen:
        st.header("✨ Super Agente: Legendas ARA")
        c1, col2 = st.columns(2)
        with c1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook"])
            tom = st.selectbox("Tom", ["Inspirador", "Pentecostal", "Jovem", "Teológico"])
        with col2:
            ver = st.text_input("📖 Versículo ARA")
            ht = st.text_input("🏷️ Hashtags Extras")
        
        tema = st.text_area("📝 O que vamos postar?")
        if st.button("🚀 Gerar Legenda"):
            if tema:
                prompt = (f"DNA da Igreja: {dna_salvo}. "
                          f"Gere legenda para {rede}, tom {tom}, tema {tema}, versículo {ver}. ARA. "
                          f"Hashtags: {conf['hashtags_fixas']} {ht}")
                res = chamar_super_agente(prompt)
                st.info(res)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    # --- ABA STORIES ---
    with t_story:
        st.header("🎬 Roteiro de Stories")
        ts = st.text_input("Tema da sequência:")
        if st.button("🎬 Criar Roteiro"):
            if ts:
                prompt_s = (f"DNA Ministerial: {dna_salvo}. Crie 3 stories sobre {ts} para {conf['nome_exibicao']}.")
                st.success(chamar_super_agente(prompt_s))

    # --- ABA INSTAGRAM ---
    with t_insta:
        st.header("📸 Central do Instagram")
        c_a, c_b = st.columns(2)
        with c_a: st.link_button("Ir para o Perfil", str(conf['instagram_url']), use_container_width=True)
        with c_b: st.link_button("✨ Criar Nova Postagem", "https://www.instagram.com/create/select/", use_container_width=True)

    # --- ABA PERFIL (CAMPO EM BRANCO + RESUMO DISCRETO) ---
    with t_perf:
        st.header("⚙️ Configurações da Igreja")
        
        st.subheader("🧬 DNA Ministerial")
        dna_input = st.text_area(
            "Atualizar DNA Ministerial:", 
            value="", 
            placeholder="Digite aqui para atualizar o estilo de escrita da IA...",
            help="O texto salvo aqui molda como a IA escreve para sua denominação específica."
        )
        
        # MENSAGEM DISCRETA LOGO ABAIXO DO CAMPO
        resumo_dna = (dna_salvo[:120] + '...') if len(dna_salvo) > 120 else dna_salvo
        st.caption(f"**DNA atual:** {resumo_dna}")
        
        st.divider()
        col_c, col_d = st.columns(2)
        with col_c:
            nova_cor = st.color_picker("Cor do sistema:", cor_atual)
        
        if st.button("💾 Salvar Configurações"):
            df_full = carregar_configuracoes()
            idx = df_full.index[df_full['igreja_id'] == conf['igreja_id']].tolist()
            if idx:
                df_full.at[idx[0], 'cor_tema'] = nova_cor
                if dna_input.strip():
                    df_full.at[idx[0], 'dna_ministerial'] = dna_input
                
                conn.update(spreadsheet=URL_PLANILHA, worksheet="configuracoes", data=df_full)
                st.session_state.cor_previa = nova_cor
                st.success("✅ Atualizado com sucesso!")
                time.sleep(1)
                st.rerun()

        st.divider()
        with st.form("senha"):
            st.subheader("🔒 Segurança")
            s_at, s_nv = st.text_input("Senha Atual", type="password"), st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Alterar Senha"):
                df_u = carregar_usuarios()
                idx_u = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx_u and str(df_u.at[idx_u[0], 'senha']) == s_at:
                    df_u.at[idx_u[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("✅ Senha alterada!")
                else: st.error("Senha incorreta.")

    # --- ABA SAIR ---
    with t_sair:
        if st.button("🔴 Confirmar Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
