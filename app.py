import streamlit as st
from openai import OpenAI

# 1. Configuração da Página
st.set_page_config(page_title="Acesso Restrito - Grupo Shekiná", page_icon="🛡️", layout="centered")

# ==========================================
# SISTEMA DE LOGIN E SEGURANÇA
# ==========================================
def check_password():
    """Retorna `True` se a senha estiver correta."""
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

    # ==========================================
    # TELA DE LOGIN (VISÍVEL PARA TODOS)
    # ==========================================
    
    # --- 1. BOTÃO NO TOPO DA PÁGINA PRINCIPAL ---
    st.link_button("🔧 By Comunicando Igrejas", "https://www.instagram.com/comunicandoigrejas/")
    # st.divider() # Linha divisória opcional

    # --- 2. CONTEÚDO DA BARRA LATERAL ---
    with st.sidebar:
        st.title("🎸 Grupo Shekiná")
        st.header("MIDIA ISOSED COSMOPOLIS")

    # --- CONTEÚDO PRINCIPAL DA TELA DE LOGIN ---
    st.title("🛡️ Acesso Restrito")
    st.info("Bem-vindo ao sistema do Grupo Shekiná. Por favor, identifique-se.")

    st.text_input("Senha de Acesso:", type="password", on_change=password_entered, key="password")

    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Senha incorreta. Tente novamente.")

    # O botão "Acessar Sistema" não é estritamente necessário com `on_change`, 
    # mas pode ser adicionado se preferir um clique explícito.
    # st.button("Acessar Sistema", on_click=password_entered)

    return False

# --- SE O LOGIN FOR SUCESSO, MOSTRA O APP ---
if check_password():

    # 2. Conexão com a IA
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # 3. Identidade Teológica da Igreja
    identidade_igreja = """
    IDENTIDADE: Você é o Social Media de uma Igreja Evangélica Pentecostal (ISOSED).
    REGRA DA BÍBLIA: Usar EXCLUSIVAMENTE João Ferreira de Almeida Revista e Atualizada (ARA) 2ª Edição (SBB).
    """

    st.title("📱 Gerador de Conteúdo ISOSED")
    st.success("✅ Acesso Liberado")
    st.markdown("Crie legendas e roteiros de stories baseados na Palavra.")

    # 4. Interface das Ferramentas
    aba_feed, aba_stories = st.tabs(["📝 Legendas de Feed", "📱 Ideias para Stories"])

    # ==========================================
    # FERRAMENTA 1: LEGENDAS DE FEED
    # ==========================================
    with aba_feed:
        st.header("Gerador de Legendas")
        
        col1, col2 = st.columns(2)
        with col1:
            plataforma = st.selectbox("Rede Social", ("Instagram", "Facebook", "YouTube"))
            tom_de_voz = st.selectbox("Tom de Voz", ("Pentecostal/Fervoroso", "Inspirador", "Jovem", "Evangelístico"))
        with col2:
            tema_feed = st.text_area("Tema do Post", placeholder="Ex: Culto da Família, Texto base: Salmos 122...")
            instrucoes = st.text_input("Direcionamento Extra", placeholder="Ex: texto curto, fazer convite...")
        
        if st.button("✨ Gerar Legenda ARA"):
            if tema_feed:
                with st.spinner('Escrevendo legenda... ⏳'):
                    prompt_f = f"{identidade_igreja} Crie uma legenda para {plataforma}. Tema: {tema_feed}. Tom: {tom_de_voz}. Obs: {instrucoes}. Use estrutura AIDA."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_f}])
                    st.subheader("Sua Legenda:")
                    st.code(res.choices[0].message.content, language=None)
            else:
                st.warning("⚠️ Digite um tema para gerar a legenda.")

    # ==========================================
    # FERRAMENTA 2: SEQUÊNCIA DE STORIES
    # ==========================================
    with aba_stories:
        st.header("Roteiro para Stories")
        st.markdown("Gere uma sequência de 3 stories interativos.")
        
        tema_st = st.text_area("Tema dos Stories", placeholder="Ex: Bom dia com fé / Convite para o culto...")
        
        if st.button("💡 Gerar Sequência de Stories"):
            if tema_st:
                with st.spinner('Criando sequência... ⏳'):
                    prompt_s = f"{identidade_igreja} Crie 3 stories para Instagram sobre: {tema_st}. Story 1: Gancho de impacto. Story 2: Versículo ARA exato. Story 3: Interação."
                    res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                    st.subheader("Roteiro:")
                    st.markdown(res.choices[0].message.content)
            else:
                st.warning("⚠️ Digite um tema para os Stories.")

    # Mantendo o botão também no rodapé após o login
    st.divider()
    st.link_button("🔧 By Comunicando Igrejas", "https://www.instagram.com/comunicandoigrejas/")
