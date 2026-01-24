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

    # --- IDENTIDADE COM FOCO EM EMOJIS E DETALHAMENTO ---
    identidade_igreja = """
    IDENTIDADE: Você é o Social Media de uma Igreja Evangélica Pentecostal (ISOSED).
    REGRA DA BÍBLIA: Usar EXCLUSIVAMENTE João Ferreira de Almeida Revista e Atualizada (ARA) 2ª Edição (SBB).
    DIRETRIZ DE CONTEÚDO: As legendas devem ser ricas em informações, detalhadas e profundas. 
    TAMANHO MÍNIMO: Cada legenda deve ter no MÍNIMO 30 palavras.
    DINAMISMO: SEMPRE adicione emojis variados e pertinentes ao contexto bíblico e pentecostal (como 🔥, 🙏, 📖, ✨, ⛪) ao longo de todo o texto para torná-lo visualmente atraente e dinâmico.
    """

    st.title("📱 Gerador de Conteúdo ISOSED")
    st.success("✅ Acesso Liberado")

    aba_feed, aba_stories = st.tabs(["📝 Legendas de Feed", "📱 Ideias para Stories"])

    # --- FERRAMENTA 1: FEED ---
    with aba_feed:
        st.header("Gerador de Legendas")
        col1, col2 = st.columns(2)
        with col1:
            plataforma = st.selectbox("Rede Social", ("Instagram", "Facebook", "YouTube"))
            tom_de_voz = st.selectbox("Tom de Voz", ("Pentecostal/Fervoroso", "Inspirador", "Acolhedor", "Jovem", "Evangelístico"))
        with col2:
            tema_feed = st.text_area("Tema do Post", placeholder="Ex: Culto da Família...")
            instrucoes = st.text_input("Direcionamento Extra", placeholder="Ex: foco no avivamento...")
        
        if st.button("✨ Gerar Legenda ARA"):
            if tema_feed:
                with st.spinner('Escrevendo legenda dinâmica...'):
                    prompt_f = f"{identidade_igreja} Crie uma legenda informativa e dinâmica para {plataforma} com mais de 30 palavras e uso generoso de emojis. Tema: {tema_feed}. Tom: {tom_de_voz}. Obs: {instrucoes}. Use estrutura AIDA."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_f}])
                    texto = res.choices[0].message.content
                    st.code(texto, language=None)
                    
                    link_wa = f"https://wa.me/?text={urllib.parse.quote(texto)}"
                    st.link_button("📲 Enviar para o WhatsApp", link_wa)
            else:
                st.warning("Digite um tema.")

    # --- FERRAMENTA 2: STORIES ---
    with aba_stories:
        st.header("Roteiro para Stories")
        tema_st = st.text_area("Tema dos Stories", placeholder="Ex: Bom dia com fé...")
        
        if st.button("💡 Gerar Sequência"):
            if tema_st:
                with st.spinner('Criando roteiro...'):
                    # Stories também ganham emojis para facilitar a leitura rápida
                    prompt_s = f"{identidade_igreja} Crie 3 stories dinâmicos com emojis para Instagram sobre: {tema_st}. Story 1: Gancho. Story 2: Versículo ARA. Story 3: Interação."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                    texto_s = res.choices[0].message.content
                    st.markdown(texto_s)
                    
                    link_wa_s = f"https://wa.me/?text={urllib.parse.quote(texto_s)}"
                    st.link_button("📲 Enviar para o WhatsApp", link_wa_s)
            else:
                st.warning("Digite um tema.")
