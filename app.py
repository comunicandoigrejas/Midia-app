import streamlit as st
from openai import OpenAI
import urllib.parse

# 1. Configuração da Página
st.set_page_config(page_title="Mídia ISOSED", page_icon="📱", layout="centered")

# --- ESCONDER A BARRA SUPERIOR DO STREAMLIT ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# SISTEMA DE LOGIN E SEGURANÇA
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    with st.sidebar:
        st.title("📱 Midia ISOSED Cosmópolis")
        st.link_button("⛪ Instagram ISOSED", "https://www.instagram.com/isosedcosmopolissp/")
        st.divider()
        st.link_button("🔧 By Comunicando Igrejas", "https://www.instagram.com/comunicandoigrejas/")

    st.title("🔒 Acesso Restrito")
    st.info("Bem-vindo ao sistema da Mídia ISOSED. Por favor, identifique-se.")
    st.text_input("Senha de Acesso:", type="password", on_change=password_entered, key="password")

    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Senha incorreta.")

    return False

# --- SE O LOGIN FOR SUCESSO ---
if check_password():

    with st.sidebar:
        st.title("📱 Midia ISOSED Cosmópolis")
        st.link_button("⛪ Instagram ISOSED", "https://www.instagram.com/isosedcosmopolissp/")
        st.divider()
        st.link_button("🔧 By Comunicando Igrejas", "https://www.instagram.com/comunicandoigrejas/")

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # --- IDENTIDADE: ARA + 30 PALAVRAS + EMOJIS DINÂMICOS ---
    identidade_igreja = """
    IDENTIDADE: Você é o Social Media de uma Igreja Evangélica Pentecostal (ISOSED).
    REGRA DA BÍBLIA: Usar EXCLUSIVAMENTE João Ferreira de Almeida Revista e Atualizada (ARA) 2ª Edição (SBB).
    DIRETRIZ DE CONTEÚDO: Legendas profundas (mínimo 30 palavras). 
    FOCO NA PALAVRA: O usuário fornecerá um versículo. Baseie TODA a reflexão e mensagem da legenda obrigatoriamente nesse versículo.
    DINAMISMO: SEMPRE adicione emojis variados (🔥, 🙏, 📖, ✨, ⛪) para um visual dinâmico.
    """

    st.title("📱 Gerador de Conteúdo ISOSED")
    st.success("✅ Acesso Liberado")

    aba_feed, aba_stories = st.tabs(["📝 Legendas de Feed", "📱 Ideias para Stories"])

    # --- FERRAMENTA 1: FEED ---
    with aba_feed:
        st.header("Gerador de Legendas")
        
        versiculo_base = st.text_input("📖 Versículo Base", placeholder="Ex: Salmos 147:3")
        
        col1, col2 = st.columns(2)
        with col1:
            plataforma = st.selectbox("Rede Social", ("Instagram", "Facebook", "YouTube"))
            tom_de_voz = st.selectbox("Tom de Voz", ("Pentecostal/Fervoroso", "Inspirador", "Acolhedor", "Jovem", "Evangelístico"))
        with col2:
            tema_feed = st.text_area("Tema do Post", placeholder="Ex: Culto de Cura e Libertação...")
            instrucoes = st.text_input("Direcionamento Extra", placeholder="Ex: Mencionar Pr. Amarildo...")
        
        if st.button("✨ Gerar Legenda ARA"):
            if tema_feed and versiculo_base:
                with st.spinner('Criando legenda com emojis...'):
                    prompt_f = f"{identidade_igreja} \nVERSÍCULO: {versiculo_base}. \nCrie uma legenda informativa para {plataforma} (+30 palavras) baseada no versículo. Tema: {tema_feed}. Tom: {tom_de_voz}. Obs: {instrucoes}. Use estrutura AIDA e emojis."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_f}])
                    texto = res.choices[0].message.content
                    
                    st.subheader("Sua Legenda:")
                    st.code(texto, language=None)
                    
                    # CORREÇÃO DOS EMOJIS: Codificação UTF-8 explícita
                    texto_para_url = urllib.parse.quote(texto)
                    link_wa = f"https://api.whatsapp.com/send?text={texto_para_url}"
                    
                    st.link_button("📲 Enviar para o WhatsApp", link_wa)
                    st.caption("Dica: Se o link falhar no seu aparelho, você também pode copiar o texto acima e colar direto no WhatsApp.")
            else:
                st.warning("⚠️ Preencha o Tema e o Versículo Base.")

    # --- FERRAMENTA 2: STORIES ---
    with aba_stories:
        st.header("Roteiro para Stories")
        versiculo_st = st.text_input("📖 Versículo para Stories", placeholder="Ex: Salmos 23:1")
        tema_st = st.text_area("Tema dos Stories", placeholder="Ex: Convite para o Culto da Família...")
        
        if st.button("💡 Gerar Sequência"):
            if tema_st and versiculo_st:
                with st.spinner('Criando roteiro bíblico...'):
                    prompt_s = f"{identidade_igreja} \nVERSÍCULO: {versiculo_st}. \nCrie 3 stories dinâmicos baseados nesse versículo. Story 1: Gancho. Story 2: O versículo ARA explicado. Story 3: Interação."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                    texto_s = res.choices[0].message.content
                    
                    st.subheader("Roteiro:")
                    st.markdown(texto_s)
                    
                    # CORREÇÃO DOS EMOJIS PARA STORIES
                    texto_s_para_url = urllib.parse.quote(texto_s)
                    link_wa_s = f"https://api.whatsapp.com/send?text={texto_s_para_url}"
                    
                    st.link_button("📲 Enviar para o WhatsApp", link_wa_s)
            else:
                st.warning("⚠️ Preencha o Tema e o Versículo.")
