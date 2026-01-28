import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÕES DE PÁGINA
st.set_page_config(page_title="Comunicando Igrejas Pro", page_icon="⚡", layout="wide")

# CSS PARA LIMPAR A TELA (RETIRAR GITHUB/FORK)
st.markdown("""<style>header {visibility: hidden !important;} #MainMenu {visibility: hidden !important;} footer {visibility: hidden !important;} .block-container {padding-top: 1rem !important;}</style>""", unsafe_allow_html=True)

# 2. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO
if "logado" not in st.session_state: st.session_state.logado = False
if "cor_previa" not in st.session_state: st.session_state.cor_previa = None

# 3. CONEXÕES
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro de Conexão. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_usuarios(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)
def carregar_configuracoes(): return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)
def carregar_calendario():
    try: return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except: return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

def aplicar_tema(cor):
    st.markdown(f"""<style>.stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }} .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}</style>""", unsafe_allow_html=True)

def logout():
    st.session_state.clear()
    st.rerun()

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
        st.subheader("Suporte Técnico")
        st.link_button("🔑 Solicitar Nova Senha (WhatsApp)", "https://wa.me/551937704733?text=Olá, esqueci minha senha.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    
    # --- LÓGICA DE IDENTIFICAÇÃO ---
    if st.session_state.perfil == "admin":
        st.sidebar.title("👑 PAINEL MASTER")
        igreja_selecionada = st.sidebar.selectbox("Simular Igreja:", df_conf['nome_exibicao'].tolist())
        conf = df_conf[df_conf['nome_exibicao'] == igreja_selecionada].iloc[0]
    else:
        conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.title(f"📱 {conf['nome_exibicao']}")

    # Tema e Cores
    cor_tema = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_tema.startswith("#"): cor_tema = f"#{cor_tema}"
    aplicar_tema(cor_tema)

    with st.sidebar:
        st.divider()
        st.link_button("⛪ Instagram da Igreja", conf['instagram_url'])
        if st.button("🚪 Sair do Sistema", use_container_width=True): logout()

    # --- DEFINIÇÃO DAS ABAS DINÂMICAS ---
    list_abas = ["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"]
    if st.session_state.perfil == "admin":
        list_abas.insert(0, "📊 Gestão Master")

    abas_criadas = st.tabs(list_abas)

    if st.session_state.perfil == "admin":
        tab_master, tab_gen, tab_story, tab_cal, tab_perf = abas_criadas
    else:
        tab_gen, tab_story, tab_cal, tab_perf = abas_criadas

    # --- ABA MASTER (SÓ ADMIN) ---
    if st.session_state.perfil == "admin":
        with tab_master:
            st.header("📊 Painel de Controle Master")
            c_m1, c_m2 = st.columns(2)
            c_m1.metric("Igrejas Cadastradas", len(df_conf))
            c_m2.metric("Usuários no Sistema", len(carregar_usuarios()))
            st.subheader("Configurações Gerais")
            st.dataframe(df_conf, use_container_width=True)

    # --- ABA 1: GERADOR DE LEGENDAS ---
    with tab_gen:
        st.header(f"Criador de Legendas - {conf['nome_exibicao']}")
        col1, col2 = st.columns(2)
        with col1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn"])
            estilo = st.selectbox("Tom da Linguagem", ["Inspiradora", "Pentecostal", "Teológica", "Jovem"])
        with col2:
            ver = st.text_input("📖 Versículo (ARA)", placeholder="Ex: João 3:16")
            hashtags_ex = st.text_input("Hashtags Extras")
        
        briefing = st.text_area("Sobre o que é a postagem?")
        if st.button("✨ Gerar Legenda Profissional"):
            if briefing:
                with st.spinner("Escrevendo..."):
                    prompt = f"Social Media Cristão. Legenda para {rede}, tom {estilo}, Bíblia ARA. Mínimo 50 palavras. Tema: {briefing}. Versículo: {ver}. Use emojis. Use hashtags fixas: {conf['hashtags_fixas']} e extras: {hashtags_ex}."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                    texto = res.choices[0].message.content
                    st.code(texto, language=None)
                    st.link_button("📲 Enviar p/ WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto)}")

    # --- ABA 2: STORIES (3 TELAS) ---
    with tab_story:
        st.header("🎬 Roteiro de Stories (Sequência)")
        tema_s = st.text_input("Qual o tema dos Stories?")
        if st.button("🎬 Criar Roteiro de 3 Telas"):
            if tema_s:
                with st.spinner("Planejando..."):
                    prompt_s = f"Crie 3 stories para {conf['nome_exibicao']} sobre {tema_s}. Tela 1: Pergunta interativa. Tela 2: Versículo ARA. Tela 3: Reflexão curta e CTA."
                    res_s = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                    st.info(res_s.choices[0].message.content)
                    st.link_button("📲 Enviar Roteiro p/ WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(res_s.choices[0].message.content)}")

    # --- ABA 3: CALENDÁRIO ---
    with tab_cal:
        st.header("📅 Agendamento de Postagens")
        with st.expander("➕ Nova Postagem"):
            with st.form("form_cal"):
                d_p = st.date_input("Data", datetime.now())
                r_p = st.selectbox("Rede", ["Instagram", "Facebook", "WhatsApp"])
                t_p = st.text_input("Assunto")
                if st.form_submit_button("Agendar"):
                    novo = pd.DataFrame([{"igreja_id": conf['igreja_id'], "data": d_p.strftime('%Y-%m-%d'), "rede_social": r_p, "tema": t_p, "status": "Pendente"}])
                    conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=novo)
                    st.success("Salvo!")
                    st.rerun()
        
        df_cal = carregar_calendario()
        meu_cal = df_cal[df_cal['igreja_id'] == conf['igreja_id']].sort_values(by='data')
        st.dataframe(meu_cal[['data', 'rede_social', 'tema', 'status']], use_container_width=True, hide_index=True)

    # --- ABA 4: PERFIL (CORES E SENHA) ---
    with tab_perf:
        st.header("⚙️ Configurações da Conta")
        
        # Paleta de 20 Cores
        st.subheader("🎨 Personalizar Cor do Painel")
        paleta = {"Azul Catedral": "#2C3E50", "Vinho": "#7B241C", "Verde Oliva": "#556B2F", "Roxo": "#4A235A", "Bronze": "#A0522D", "Grafite": "#212121", "Azul Petróleo": "#0E4B5A", "Ultravioleta": "#6C5CE7", "Rosa Chá": "#E84393", "Cinza": "#636E72", "Laranja": "#E17055", "Amarelo": "#FBC531", "Azul Royal": "#0984E3", "Vermelho": "#D63031", "Verde Menta": "#00B894", "Areia": "#C2B280", "Terracota": "#E2725B", "Azul Céu": "#87CEEB", "Lavanda": "#A29BFE", "Marrom": "#4E342E"}
        c_cols = st.columns(5)
        for i, (n, h) in enumerate(paleta.items()):
            with c_cols[i % 5]:
                if st.button(n, key=n): st.session_state.cor_previa = h
        
        c_pick = st.color_picker("Ajuste manual:", st.session_state.get('cor_previa', cor_tema))
        if st.button("👁️ Aplicar Visual"): aplicar_tema(c_pick)
        st.link_button("💾 Salvar Cor (WhatsApp)", f"https://wa.me/551937704733?text=Alterar cor {conf['nome_exibicao']} para {c_pick}")

        st.divider()
        st.subheader("🔐 Segurança")
        with st.form("form_pw"):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Alterar Senha"):
                df_u = carregar_usuarios()
                idx = df_u.index[df_u['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u.at[idx[0], 'senha']) == s_at:
                    df_u.at[idx[0], 'senha'] = s_nv
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u)
                    st.success("Senha alterada!")
                else: st.error("Senha incorreta.")
