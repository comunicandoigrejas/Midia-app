import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÕES DE PÁGINA
st.set_page_config(page_title="Comunicando Igrejas Pro", page_icon="⚡", layout="wide")

# Inicialização de variáveis de estado
if "logado" not in st.session_state:
    st.session_state.logado = False
if "cor_previa" not in st.session_state:
    st.session_state.cor_previa = None

# 2. CONEXÕES SEGURAS (Service Account)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Erro de Conexão: {e}. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE DADOS ---
def carregar_usuarios():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def carregar_calendario():
    try:
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except:
        return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

# --- INJETOR DE TEMA PERSONALIZADO ---
def aplicar_tema(cor):
    st.markdown(f"""
        <style>
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }}
        .stButton>button:hover {{ opacity: 0.8; color: white; }}
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}
        header {{visibility: hidden;}} footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# TELA DE LOGIN & RECUPERAÇÃO
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
                        st.session_state.igreja_id = user.iloc[0]['igreja_id']
                        st.session_state.perfil = user.iloc[0]['perfil']
                        st.session_state.email = email_in
                        st.rerun()
                    else: st.warning("Conta inativa.")
                else: st.error("E-mail ou senha incorretos.")

    with tab_rec:
        st.write("Esqueceu sua senha? Solicite uma nova ao administrador.")
        st.link_button("🔑 Solicitar Nova Senha", "https://wa.me/SEUNUMERO?text=Olá, esqueci minha senha.")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_conf = carregar_configuracoes()
    conf = df_conf[df_conf['igreja_id'] == st.session_state.igreja_id].iloc[0]
    
    # Tratamento de Cor
    cor_tema = str(conf['cor_tema']).strip() if pd.notnull(conf['cor_tema']) else "#4169E1"
    if not cor_tema.startswith("#"): cor_tema = f"#{cor_tema}"
    aplicar_tema(cor_tema)

    st.sidebar.title(f"📱 {conf['nome_exibicao']}")
    with st.sidebar:
        st.link_button("⛪ Instagram da Igreja", conf['instagram_url'])
        if st.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()

    # --- LEMBRETE DO DIA ---
    df_cal_hoje = carregar_calendario()
    hoje = datetime.now().strftime('%Y-%m-%d')
    tarefa_hoje = df_cal_hoje[(df_cal_hoje['igreja_id'] == st.session_state.igreja_id) & (df_cal_hoje['data'].astype(str) == hoje)]
    
    if not tarefa_hoje.empty:
        st.warning(f"📌 **Lembrete de Hoje:** Você tem {len(tarefa_hoje)} postagem(ns) agendada(s). Confira na aba Calendário!")

    tab_gen, tab_story, tab_cal, tab_perf = st.tabs(["✨ Legendas", "🎬 Stories", "📅 Calendário", "⚙️ Perfil"])

    # --- ABA 1: GERADOR ---
    with tab_gen:
        st.header("Gerador de Legendas ARA")
        c1, c2 = st.columns(2)
        with c1:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn"])
            estilo = st.selectbox("Tom", ["Inspiradora", "Pentecostal", "Jovem", "Teológica"])
        with c2:
            ver = st.text_input("📖 Versículo", placeholder="Ex: Salmos 23:1")
            hashtags_ex = st.text_input("Hashtags Extras", placeholder="Separe por espaço")
        
        brief = st.text_area("Sobre o que é o post?")
        if st.button("✨ Gerar Conteúdo"):
            if brief:
                with st.spinner("IA Escrevendo..."):
                    prompt = f"Social Media Cristão. Legenda {rede}, tom {estilo}, Bíblia ARA. +50 palavras. Tema: {brief}. Versículo: {ver}. Use emojis. Use hashtags: {conf['hashtags_fixas']} {hashtags_ex}."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                    texto = res.choices[0].message.content
                    st.code(texto, language=None)
                    st.link_button("📲 Enviar para WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto)}")

    # --- ABA 2: STORIES ---
    with tab_story:
        st.header("Roteiro de Stories")
        tema_s = st.text_input("Tema da sequência")
        if st.button("🎬 Criar Roteiro"):
            with st.spinner("Gerando..."):
                prompt_s = f"Crie roteiro de 4 stories para {conf['nome_exibicao']} sobre {tema_s}."
                res_s = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                st.write(res_s.choices[0].message.content)

    # --- ABA 3: CALENDÁRIO & AGENDAMENTO ---
    with tab_cal:
        st.header("📅 Agendamento de Postagens")
        with st.expander("➕ Nova Postagem"):
            with st.form("form_cal"):
                d_post = st.date_input("Data", datetime.now())
                r_post = st.selectbox("Plataforma", ["Instagram", "Facebook", "WhatsApp"])
                t_post = st.text_input("Assunto")
                if st.form_submit_button("Salvar no Calendário"):
                    if t_post:
                        novo = pd.DataFrame([{"igreja_id": st.session_state.igreja_id, "data": d_post.strftime('%Y-%m-%d'), "rede_social": r_post, "tema": t_post, "status": "Pendente"}])
                        conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=novo)
                        st.success("Agendado!")
                        st.rerun()
        
        st.divider()
        df_ver_cal = carregar_calendario()
        meu_cal = df_ver_cal[df_ver_cal['igreja_id'] == st.session_state.igreja_id].sort_values(by='data')
        st.dataframe(meu_cal[['data', 'rede_social', 'tema', 'status']], use_container_width=True, hide_index=True)

    # --- ABA 4: PERFIL (CORES E SENHA) ---
    with tab_perf:
        st.header("🎨 Personalização e Segurança")
        paleta = {
            "Azul Catedral": "#2C3E50", "Vinho Clássico": "#7B241C", "Verde Oliva": "#556B2F",
            "Roxo Imperial": "#4A235A", "Bronze": "#A0522D", "Grafite": "#212121",
            "Azul Petróleo": "#0E4B5A", "Ultravioleta": "#6C5CE7", "Rosa Chá": "#E84393",
            "Cinza Concreto": "#636E72", "Laranja Fogo": "#E17055", "Amarelo Glória": "#FBC531",
            "Azul Royal": "#0984E3", "Vermelho Vivo": "#D63031", "Verde Menta": "#00B894",
            "Areia": "#C2B280", "Terracota": "#E2725B", "Azul Céu": "#87CEEB",
            "Lavanda": "#A29BFE", "Marrom Café": "#4E342E"
        }
        cols = st.columns(5)
        for i, (nome, hex) in enumerate(paleta.items()):
            with cols[i % 5]:
                if st.button(nome, key=nome): st.session_state.cor_previa = hex
        
        c_pick = st.color_picker("Cor personalizada:", st.session_state.get('cor_previa', cor_tema))
        if st.button("👁️ Testar Visual"): aplicar_tema(c_pick)
        st.link_button("💾 Salvar Cor (WhatsApp)", f"https://api.whatsapp.com/send?phone=SEUNUMERO&text=Alterar cor para {c_pick}")

        st.divider()
        st.subheader("🔐 Alterar Minha Senha")
        with st.form("form_senha"):
            s_atual = st.text_input("Senha Atual", type="password")
            s_nova = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                df_u_pw = carregar_usuarios()
                idx = df_u_pw.index[df_u_pw['email'].str.lower() == st.session_state.email.lower()].tolist()
                if idx and str(df_u_pw.at[idx[0], 'senha']) == s_atual:
                    df_u_pw.at[idx[0], 'senha'] = s_nova
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="usuarios", data=df_u_pw)
                    st.success("Senha alterada!")
                else: st.error("Senha atual incorreta.")
