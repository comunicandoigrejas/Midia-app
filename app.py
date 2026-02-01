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
if "email_salvo" not in st.session_state: st.session_state.email_salvo = ""

for chave in ["perfil", "igreja_id", "email"]:
    if chave not in st.session_state: st.session_state[chave] = ""

# --- 🛠️ CSS: CORREÇÃO DEFINITIVA PARA CELULAR EM PÉ (PORTRAIT) ---
st.markdown("""
    <style>
    /* Remove elementos de cabeçalho nativos */
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    footer { visibility: hidden !important; }

    /* Ajuste de Desktop (85% para ficar elegante) */
    .block-container {
        padding-top: 1rem !important;
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

    /* 📱 AJUSTES AGRESSIVOS PARA CELULAR EM PÉ (PORTRAIT) */
    @media screen and (max-width: 768px) {
        /* Força a página a ocupar 100% da largura sem sobras laterais */
        .block-container {
            max-width: 100% !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-top: 0.5rem !important;
        }
        
        .church-title {
            font-size: 1.3rem !important; /* Título menor para não quebrar linha */
            margin-top: 0.5rem !important;
            margin-bottom: 0.8rem !important;
        }

        /* Ajuste das Abas (Tabs) para caberem em telas estreitas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px !important;
            display: flex !important;
            justify-content: space-between !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding-left: 4px !important;
            padding-right: 4px !important;
            font-size: 0.75rem !important; /* Letra pequena o suficiente para o modo retrato */
            min-width: auto !important;
        }

        /* Ajuste de inputs e botões para mobile */
        .stButton>button {
            width: 100% !important;
            font-size: 0.85rem !important;
        }
        
        input, select, textarea {
            font-size: 16px !important; /* Evita o zoom automático do iPhone ao clicar */
        }
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
    c1, c2, c3 = st.columns([0.1, 0.8, 0.1]) # Ajustado para ocupar quase tudo no mobile
    with c2:
        with st.form("login"):
            em = st.text_input("E-mail", value=st.session_state.email_salvo)
            se = st.text_input("Senha", type="password")
            lembrar = st.checkbox("Lembrar e-mail", value=True if st.session_state.email_salvo else False)
            if st.form_submit_button("Entrar no Painel", use_container_width=True):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                if not u.empty and str(u.iloc[0]['status']).strip().lower() == 'ativo':
                    st.session_state.logado, st.session_state.perfil, st.session_state.igreja_id, st.session_state.email = True, str(u.iloc[0]['perfil']).strip().lower(), u.iloc[0]['igreja_id'], em
                    st.session_state.email_salvo = em if lembrar else ""
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
    dna_salvo = str(conf['dna_ministerial']) if 'dna_ministerial' in conf and pd.notnull(conf['dna_ministerial']) else "Linguagem cristã padrão."

    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor_atual} !important; color: white !important; font-size: 0.9rem; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor_atual} !important; color: white !important; border-radius: 5px; }}
        .church-title {{ color: {cor_atual}; }}
        </style>
        <div class="church-title"> {conf['nome_exibicao']}</div>
    """, unsafe_allow_html=True)

    t_gen, t_story, t_brief, t_insta, t_perf, t_sair = st.tabs([
        "✨ Leg.", "🎬 Sto.", "🎨 Brief.", "📸 Insta", "⚙️ Perf.", "🚪 Sair"
    ])

    # --- ABA LEGENDAS ---
    with t_gen:
        st.header("✨ Legendas ARA")
        rede = st.selectbox("Rede", ["Instagram", "Facebook"])
        tom = st.selectbox("Tom", ["Inspirador", "Pentecostal", "Jovem", "Teológico"])
        ver = st.text_input("📖 Versículo ARA")
        ht = st.text_input("🏷️ Hashtags")
        tema = st.text_area("📝 Tema do post")
        if st.button("🚀 Gerar Legenda", use_container_width=True):
            if tema:
                prompt = f"DNA: {dna_salvo}. Legenda {rede}, tom {tom}, tema {tema}, versículo {ver}. ARA. Hashtags: {conf['hashtags_fixas']} {ht}"
                res = chamar_super_agente(prompt)
                st.info(res)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}", use_container_width=True)

    # --- ABA STORIES ---
    with t_story:
        st.header("🎬 Roteiro Stories")
        ts = st.text_input("Tema da sequência:")
        if st.button("🎬 Criar Roteiro", use_container_width=True):
            if ts:
                st.success(chamar_super_agente(f"DNA: {dna_salvo}. 3 stories sobre {ts} para {conf['nome_exibicao']}."))

    # --- ABA BRIEFING VISUAL ---
    with t_brief:
        st.header("🎨 Briefing Visual")
        tema_briefing = st.text_input("🎯 Tema", placeholder="Ex: Santa Ceia...")
        formato_briefing = st.selectbox("🖼️ Formato", ["Único", "Carrossel", "Reels", "Cartaz"])
        if st.button("🎨 Gerar Briefing", use_container_width=True):
            if tema_briefing:
                prompt_briefing = f"Diretor de Arte. DNA: {dna_salvo}. Briefing tema: '{tema_briefing}' formato {formato_briefing}."
                res_brief = chamar_super_agente(prompt_briefing)
                st.warning(res_brief)
                texto_wa = f"*🎨 BRIEFING - {conf['nome_exibicao']}*\n*🎯 TEMA:* {tema_briefing}\n*📋:* {res_brief}"
                st.link_button("📲 Enviar ao Designer", f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wa)}", use_container_width=True)

    # --- ABA INSTAGRAM ---
    with t_insta:
        st.header("📸 Instagram")
        st.link_button("Ir para o Perfil", str(conf['instagram_url']), use_container_width=True)
        st.link_button("✨ Criar Nova Postagem", "https://www.instagram.com/create/select/", use_container_width=True)

    # --- ABA PERFIL ---
    with t_perf:
        st.header("⚙️ Perfil")
        dna_input = st.text_area("Atualizar DNA:", value="", placeholder="Digite para atualizar...")
        res_dna = (dna_salvo[:80] + '...') if len(dna_salvo) > 80 else dna_salvo
        st.caption(f"**DNA atual:** {res_dna}")
        nova_cor = st.color_picker("Cor do sistema:", cor_atual)
        if st.button("💾 Salvar Configurações", use_container_width=True):
            df_f = carregar_configuracoes()
            idx = df_f.index[df_f['igreja_id'] == conf['igreja_id']].tolist()
            if idx:
                df_f.at[idx[0], 'cor_tema'] = nova_cor
                if dna_input.strip(): df_f.at[idx[0], 'dna_ministerial'] = dna_input
                conn.update(spreadsheet=URL_PLANILHA, worksheet="configuracoes", data=df_f)
                st.session_state.cor_previa = nova_cor
                st.success("✅ Atualizado!")
                time.sleep(1)
                st.rerun()

    # --- ABA SAIR ---
    with t_sair:
        if st.button("🔴 Confirmar Logout", use_container_width=True):
            em_temp = st.session_state.email_salvo
            st.session_state.clear()
            st.session_state.email_salvo = em_temp
            st.rerun()
