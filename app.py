import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
import time
from datetime import datetime

# 1. CONFIGURAÇÕES DE PÁGINA E UI
st.set_page_config(page_title="Comunicando Igrejas Pro", page_icon="⚡", layout="wide")

# CSS para esconder o menu do Streamlit e o botão de Fork do GitHub
st.markdown("""
    <style>
    header {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .block-container {padding-top: 1rem !important;}
    </style>
    """, unsafe_allow_html=True)

# 2. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None

# 3. CONEXÕES (Secrets)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    ASSISTANT_ID = st.secrets["OPENAI_ASSISTANT_ID"] # ID do seu Assistente
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de Conexão. Verifique os Secrets (API Key, Assistant ID e Planilha).")
    st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)
def carregar_calendario():
    try: return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except: return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

def aplicar_tema(cor):
    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }}
        .stButton>button:hover {{ opacity: 0.8; color: white; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}
        </style>
    """, unsafe_allow_html=True)

def logout():
    st.session_state.clear()
    st.rerun()

# --- FUNÇÃO DO SUPER AGENTE (ASSISTANTS API) ---
def chamar_super_agente(comando):
    # Cria a Thread (conversa)
    thread = client.beta.threads.create()
    
    # Envia a mensagem do usuário
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=comando
    )
    
    # Executa o Agente (Run)
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
                return "Desculpe, o Agente encontrou um erro ao processar. Tente novamente."
    
    # Recupera a resposta final
    mensagens = client.beta.threads.messages.list(thread_id=thread.id)
    return mensagens.data[0].content[0].text.value

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    tab_log, tab_rec = st.tabs(["Acessar Sistema", "Recuperar Senha"])
    
    with tab_log:
        with st.form("form_login"):
            email_in = st.text_input("E-mail")
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                df_u = carregar_usuarios()
                user = df_u[(df_u['email'].str.lower() == email_in.lower()) & (df_u['senha'].astype(str) == str(senha_in))]
                if not user.empty:
                    if str(user.iloc[0]['status']).lower() == 'ativo':
                        st.session_state.logado = True
                        st.session_state.perfil = str(user.iloc[0]['perfil']).strip().lower()
                        st.session_state.igreja_id = user.iloc[0]['igreja_id']
                        st.session_state.email = email_in
                        st.rerun()
                    else: st.warning("Conta inativa.")
                else: st.error("E-mail ou senha incorretos.")

    with tab_rec:
        st.subheader("Esqueceu sua senha?")
        st.link_button("🔑 Solicitar Nova Senha (WhatsApp)", "https://wa.me/551937704733?text=Olá, esqueci minha senha no painel.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # Diferencia Admin Master de Usuário Comum
    if st.session_state.perfil == "admin":
        st.sidebar.title("👑 PAINEL MASTER")
        igreja_selecionada = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_selecionada].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.title(f"📱 {conf['nome_exibicao']}")

    # Aplicação do Tema de Cor
    cor_tema = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_tema.startswith("#"): cor_tema = f"#{cor_tema}"
    aplicar_tema(cor_tema)

    # Sidebar
    with st.sidebar:
        if st.button("🚪 Sair do Sistema", use_container_width=True, type="primary"): logout()
        st.divider()
        st.link_button("⛪ Instagram da Igreja", conf['instagram_url'])
        st.caption(f"Logado como: {st.session_state.email}")

    # Definição das Abas
    list_abas = ["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"]
    if st.session_state.perfil == "admin": list_abas.insert(0, "📊 Gestão Master")
    abas = st.tabs(list_abas)

    if st.session_state.perfil == "admin": tab_master, tab_gen, tab_story, tab_cal, tab_perf = abas
    else: tab_gen, tab_story, tab_cal, tab_perf = abas

    # --- ABA MASTER ---
    if st.session_state.perfil == "admin":
        with tab_master:
            st.header("📊 Gestão Geral")
            st.dataframe(df_conf, use_container_width=True)

    # --- ABA 1: GERADOR (SUPER AGENTE) ---
    with tab_gen:
        st.header(f"✨ Super Agente: Legendas")
        c1, c2 = st.columns(2)
        with c1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn"])
            estilo = st.selectbox("Tom", ["Inspiradora", "Pentecostal", "Teológica", "Jovem"])
        with c2:
            ver = st.text_input("📖 Versículo (ARA)")
            hashtags_ex = st.text_input("Hashtags Extras")
        
        brief = st.text_area("Sobre o que é a postagem?")
        if st.button("🚀 Gerar Legenda com Super Agente"):
            if brief:
                # Comando formatado para o Assistente
                prompt = f"Gere uma legenda para {rede}. Tom: {estilo}. Tema: {brief}. Versículo: {ver}. Hashtags da igreja: {conf['hashtags_fixas']} {hashtags_ex}. Lembre-se: Mínimo 50 palavras e muitos emojis!"
                resultado = chamar_super_agente(prompt)
                st.info(resultado)
                st.link_button("📲 Enviar p/ WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado)}")

    # --- ABA 2: STORIES (SUPER AGENTE) ---
    with tab_story:
        st.header("🎬 Super Agente: Roteiro de Stories")
        tema_s = st.text_input("Assunto da sequência")
        if st.button("🎬 Gerar 3 Telas Estratégicas"):
            if tema_s:
                prompt_s = f"Crie uma sequência de 3 stories sobre {tema_s} para a igreja {conf['nome_exibicao']}. Siga a estrutura: Pergunta, Versículo ARA e Reflexão. Use muitos emojis!"
                resultado_s = chamar_super_agente(prompt_s)
                st.success(resultado_s)
                st.link_button("📲 Enviar Roteiro p/ WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resultado_s)}")

    # --- ABA 3: CALENDÁRIO ---
    with tab_cal:
        st.header("📅 Agendamento")
        with st.expander("➕ Nova Postagem"):
            with st.form("form_cal"):
                d_p = st.date_input("Data", datetime.now())
                r_p = st.selectbox("Rede", ["Instagram", "Facebook", "WhatsApp"])
                t_p = st.text_input("Assunto")
                if st.form_submit_button("Salvar"):
                    n = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": d_p.strftime('%Y-%m-%d'), "rede_social": r_p, "tema": t_p, "status": "Pendente"}])
                    conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=n)
                    st.success("Agendado!")
                    st.rerun()
        df_ver_c = carregar_calendario()
        meu_c = df_ver_c[df_ver_c['igreja_id'] == conf['igreja_id']].sort_values(by='data')
        st.dataframe(meu_c[['data', 'rede_social', 'tema', 'status']], use_container_width=True, hide_index=True)

    # --- ABA 4: PERFIL ---
    with tab_perf:
        st.header("⚙️ Configurações e Segurança")
        paleta = {"Azul Catedral": "#2C3E50", "Vinho": "#7B241C", "Verde": "#556B2F", "Roxo": "#4A235A", "Grafite": "#212121", "Laranja": "#E17055", "Amarelo": "#FBC531", "Azul Royal": "#0984E3", "Vermelho": "#D63031", "Verde Menta": "#00B894", "Areia": "#C2B280", "Terracota": "#E2725B", "Azul Céu": "#87CEEB", "Lavanda": "#A29BFE", "Marrom": "#4E342E"}
        cols = st.columns(5)
        for i, (n, h) in enumerate(paleta.items()):
            with cols[i % 5]:
                if st.button(n, key=n): st.session_state.cor_previa = h
        
        c_p = st.color_picker("Ajuste manual:", st.session_state.get('cor_previa', cor_tema))
        if st.button("👁️ Testar Visual"): aplicar_tema(c_p)
        st.link_button("💾 Salvar Cor (WhatsApp)", f"https://wa.me/551937704733?text=Alterar cor permanente para {c_p}")

        st.divider()
        with st.form("form_pw"):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Alterar Senha"):
                df_u_p = carregar_usuarios()
                idx = df_u_p.index[df_u_p['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u_p.at[idx[0], 'senha']) == s_at:
                    df_u_p.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u_p)
                    st.success("Senha alterada!")
                else: st.error("Erro na senha atual.")
