import streamlit as st  # Corrigido: adicionado o 'as'
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
if "email_salvo" not in st.session_state: st.session_state.email_salvo = "" # Para o "Lembrar E-mail"

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
# INTERFACE DE LOGIN (COM LEMBRAR E-MAIL)
# ==========================================
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🚀 Comunicando Igrejas</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        with st.form("login"):
            # O campo agora busca o valor salvo caso exista
            em = st.text_input("E-mail", value=st.session_state.email_salvo)
            se = st.text_input("Senha", type="password")
            lembrar = st.checkbox("Lembrar meu e-mail", value=True if st.session_state.email_salvo else False)
            
            if st.form_submit_button("Entrar no Painel", use_container_width=True):
                df_u = carregar_usuarios()
                u = df_u[(df_u['email'].str.lower() == em.lower()) & (df_u['senha'].astype(str) == str(se))]
                
                if not u.empty and str(u.iloc[0]['status']).strip().lower() == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = str(u.iloc[0]['perfil']).strip().lower()
                    st.session_state.igreja_id = u.iloc[0]['igreja_id']
                    st.session_state.email = em
                    
                    # Salva ou remove o e-mail da memória baseado no checkbox
                    if lembrar:
                        st.session_state.email_salvo = em
                    else:
                        st.session_state.email_salvo = ""
                        
                    st.rerun()
                else: st.error("Acesso negado ou dados incorretos.")

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
        .stButton>button {{ background-color: {cor_atual} !important; color: white !important; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor_atual} !important; color: white !important; border-radius: 5px; }}
        .church-title {{ color: {cor_atual}; }}
        </style>
        <div class="church-title">⛪ {conf['nome_exibicao']}</div>
    """, unsafe_allow_html=True)

    t_gen, t_story, t_brief, t_insta, t_perf, t_sair = st.tabs([
        "✨ Legendas", "🎬 Stories", "🎨 Briefing Visual", "📸 Instagram", "⚙️ Perfil", "🚪 Sair"
    ])

    # --- ABA 1: LEGENDAS ---
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
                prompt = f"DNA da Igreja: {dna_salvo}. Legenda para {rede}, tom {tom}, tema {tema}, versículo {ver}. ARA. Hashtags: {conf['hashtags_fixas']} {ht}"
                res = chamar_super_agente(prompt)
                st.info(res)
                st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res)}")

    # --- ABA 2: STORIES ---
    with t_story:
        st.header("🎬 Roteiro de Stories")
        ts = st.text_input("Tema da sequência:")
        if st.button("🎬 Criar Roteiro"):
            if ts:
                st.success(chamar_super_agente(f"DNA Ministerial: {dna_salvo}. Crie 3 stories sobre {ts} para {conf['nome_exibicao']}."))

    # --- ABA 3: BRIEFING VISUAL ---
    with t_brief:
        st.header("🎨 Diretor de Criação: Briefing para o Designer")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            tema_briefing = st.text_input("🎯 Tema da Postagem", placeholder="Ex: Culto de Jovens, Santa Ceia...")
        with col_b2:
            formato_briefing = st.selectbox("🖼️ Formato do Post", ["Publicação Única", "Carrossel", "Capa de Reels", "Cartaz"])
        
        if st.button("🎨 Gerar Briefing de Arte"):
            if tema_briefing:
                prompt_briefing = (
                    f"Atue como Diretor de Arte. DNA da Igreja: {dna_salvo}. "
                    f"Crie um briefing para o tema: '{tema_briefing}' no formato {formato_briefing}. "
                    f"Inclua: Paleta de Cores, Estilo de Foto, Tipografia e Descrição por telas."
                )
                res_brief = chamar_super_agente(prompt_briefing)
                st.markdown("---")
                st.subheader(f"💡 Sugestão para: {tema_briefing}")
                st.warning(res_brief)
                
                texto_whatsapp = (
                    f"*🎨 BRIEFING VISUAL - {conf['nome_exibicao']}*\n\n"
                    f"*🎯 TEMA:* {tema_briefing}\n"
                    f"*🖼️ FORMATO:* {formato_briefing}\n\n"
                    f"*📋 ORIENTAÇÕES:* \n{res_brief}"
                )
                st.link_button("📲 Enviar Briefing para o Designer", f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_whatsapp)}")

    # --- ABA 4: INSTAGRAM ---
    with t_insta:
        st.header("📸 Central do Instagram")
        c_a, c_b = st.columns(2)
        with c_a: st.link_button("Ir para o Perfil", str(conf['instagram_url']), use_container_width=True)
        with c_b: st.link_button("✨ Criar Nova Postagem", "https://www.instagram.com/create/select/", use_container_width=True)

    # --- ABA 5: PERFIL ---
    with t_perf:
        st.header("⚙️ Configurações da Igreja")
        st.subheader("🧬 DNA Ministerial")
        dna_input = st.text_area("Atualizar DNA Ministerial:", value="", placeholder="Digite para atualizar...")
        resumo_dna = (dna_salvo[:120] + '...') if len(dna_salvo) > 120 else dna_salvo
        st.caption(f"**DNA atual:** {resumo_dna}")
        
        st.divider()
        col_c, col_d = st.columns(2)
        with col_c: nova_cor = st.color_picker("Cor do sistema:", cor_atual)
        
        if st.button("💾 Salvar Configurações"):
            df_full = carregar_configuracoes()
            idx = df_full.index[df_full['igreja_id'] == conf['igreja_id']].tolist()
            if idx:
                df_full.at[idx[0], 'cor_tema'] = nova_cor
                if dna_input.strip(): df_full.at[idx[0], 'dna_ministerial'] = dna_input
                conn.update(spreadsheet=URL_PLANILHA, worksheet="configuracoes", data=df_full)
                st.session_state.cor_previa = nova_cor
                st.success("✅ Atualizado!")
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

    # --- ABA 6: SAIR (AJUSTADA PARA PRESERVAR E-MAIL) ---
    with t_sair:
        st.header("🚪 Encerrar Sessão")
        if st.button("🔴 Confirmar Logout", use_container_width=True):
            # Guardamos o e-mail antes de limpar tudo
            email_temp = st.session_state.email_salvo
            st.session_state.clear()
            # Devolvemos apenas o e-mail para o próximo login
            st.session_state.email_salvo = email_temp
            st.session_state.logado = False
            st.rerun()
