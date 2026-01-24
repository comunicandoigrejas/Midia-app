import streamlit as st
from openai import OpenAI

# 1. Configuração da Página
st.set_page_config(page_title="Gerador de Mídia - ISOSED", page_icon="📱", layout="centered")

# 2. Conexão com a IA
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 3. Identidade Teológica da Igreja (Regra ARA)
identidade_igreja = """
IDENTIDADE: Você é o Social Media de uma Igreja Evangélica Pentecostal (ISOSED). 
REGRA DA BÍBLIA: Usar EXCLUSIVAMENTE João Ferreira de Almeida Revista e Atualizada (ARA) 2ª Edição (SBB).
"""

st.title("📱 Gerador de Conteúdo ISOSED")
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
                prompt_f = f"{identidade_igreja} Crie uma legenda para {plataforma}. Tema: {tema_feed}. Tom: {tom_de_voz}. Obs: {instrucoes}. Use estrutura AIDA (Atenção, Interesse, Desejo, Ação)."
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
                prompt_s = f"{identidade_igreja} Crie 3 stories para Instagram sobre: {tema_st}. Story 1: Gancho de impacto. Story 2: Versículo ARA exato. Story 3: Interação (Enquete/Caixinha)."
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                st.subheader("Roteiro:")
                st.markdown(res.choices[0].message.content)
        else:
            st.warning("⚠️ Digite um tema para os Stories.")
