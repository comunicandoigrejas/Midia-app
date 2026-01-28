import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd

# 1. CONFIGURAÇÃO DA PÁGINA E INTERFACE
st.set_page_config(
    page_title="Comunicando Igrejas - Painel de Mídia", 
    page_icon="🚀", 
    layout="wide"
)

# --- ESCONDER ELEMENTOS DO STREAMLIT ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÕES (SERVICE ACCOUNT + OPENAI)
# A biblioteca GSheetsConnection lerá automaticamente o JSON dos Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    # Link da planilha guardado nos Secrets
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Erro de Conexão Crítico: {e}")
    st.stop()

# --- FUNÇÕES DE BUSCA DE DADOS ---
def carregar_usuarios():
    # ttl=0 garante que o login reflita mudanças imediatas na planilha
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

# --- INICIALIZAÇÃO DO ESTADO DE LOGIN ---
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None
    st.session_state.igreja_id = None

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🚀 Comunicando Igrejas")
    st.subheader("Seu assistente inteligente de mídia eclesiástica")
    
    with st.form("login_form"):
        email_i = st.text_input("E-mail de acesso")
        senha_i = st.text_input("Senha", type="password")
        btn_login = st.form_submit_button("Acessar Painel")
        
        if btn_login:
            df_u = carregar_usuarios()
            # Validação robusta: ignora espaços e maiúsculas no e-mail
            user = df_u[
                (df_u['email'].str.lower().str.strip() == email_i.lower().strip()) & 
                (df_u['senha'].astype(str) == str(senha_i))
            ]
            
            if not user.empty:
                # Verifica se o status é Ativo (aceita 'Ativo' ou 'ativo')
                if user.iloc[0]['status'].strip().lower() == 'ativo':
                    st.session_state.logado = True
                    st.session_state.perfil = user.iloc[0]['perfil']
                    st.session_state.igreja_id = user.iloc[0]['igreja_id']
                    st.session_state.email = email_i
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("⚠️ Sua conta está inativa. Entre em contato com o suporte.")
            else:
                st.error("❌ E-mail ou senha incorretos.")
    
    st.caption("Dificuldades no acesso? Contate @comunicandoigrejas")

# ==========================================
# AMBIENTE LOGADO
# ==========================================
else:
    df_config = carregar_configuracoes()
    
    # --- IDENTIFICAÇÃO DO TENANT (IGREJA) ---
    if st.session_state.perfil == "admin":
        st.sidebar.title("👑 MASTER ADMIN")
        opcoes_igrejas = df_config['nome_exibicao'].tolist()
        igreja_selecionada = st.sidebar.selectbox("Simular Igreja:", opcoes_igrejas)
        config = df_config[df_config['nome_exibicao'] == igreja_selecionada].iloc[0]
    else:
        config = df_config[df_config['igreja_id'] == st.session_state.igreja_id].iloc[0]
        st.sidebar.title(f"📱 {config['nome_exibicao']}")

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.info(f"Usuário: {st.session_state.email}")
        st.link_button("⛪ Nosso Instagram", config['instagram_url'])
        st.divider()
        st.link_button("🔧 Suporte Comunicando", "https://www.instagram.com/comunicandoigrejas/")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.logado = False
            st.rerun()

    # --- DEFINIÇÃO DE ABAS ---
    if st.session_state.perfil == "admin":
        tab_master, tab_gerador = st.tabs(["📊 Gestão Master", "✨ Gerador de Conteúdo"])
    else:
        tab_gerador, tab_perfil = st.tabs(["✨ Gerador de Conteúdo", "⚙️ Meu Perfil"])

    # --- ABA MASTER (SÓ PARA ADMIN) ---
    if st.session_state.perfil == "admin":
        with tab_master:
            st.header("Painel Master de Clientes")
            col1, col2, col3 = st.columns(3)
            col1.metric("Igrejas Clientes", len(df_config))
            col2.metric("Status Planilha", "Conectado (JSON)")
            
            st.subheader("Configurações Gerais")
            st.dataframe(df_config, use_container_width=True)
            
            st.subheader("Usuários do Sistema")
            st.dataframe(carregar_usuarios(), use_container_width=True)

    # --- ABA GERADOR (PARA TODOS) ---
    with tab_gerador:
        st.header(f"Criador de Legendas - {config['nome_exibicao']}")
        
        col_v, col_t = st.columns([1, 2])
        with col_v:
            versiculo_base = st.text_input("📖 Versículo Base", placeholder="Ex: João 14:6")
        with col_t:
            tema_post = st.text_area("Sobre o que é o post?", placeholder="Ex: Convite para o culto de Domingo às 19h...")
        
        direcionamento = st.text_input("Direcionamento Extra (Opcional)", placeholder="Ex: Focar no Pr. Amarildo, avisar da Santa Ceia...")

        if st.button("✨ Gerar Legenda com Bíblia ARA"):
            if versiculo_base and tema_post:
                with st.spinner("Refletindo na Palavra e gerando conteúdo..."):
                    
                    # PROMPT ESTRUTURADO COM AS REGRAS DE NEGÓCIO
                    prompt_f = f"""
                    IDENTIDADE: Você é Social Media da igreja {config['nome_exibicao']}.
                    REGRA BÍBLICA: Use EXCLUSIVAMENTE a tradução João Ferreira de Almeida Revista e Atualizada (ARA) 2ª Edição.
                    VERSÍCULO: {versiculo_base}. Toda a legenda deve ser baseada neste versículo.
                    TEMA: {tema_post}.
                    DIRECIONAMENTO: {direcionamento}.
                    TAMANHO: No mínimo 30 palavras.
                    ESTILO: Use muitos emojis (🔥, 🙏, 📖, ✨, ⛪) para dinamismo.
                    HASHTAGS: Gere 3 hashtags temáticas e finalize com as fixas: {config['hashtags_fixas']}
                    ESTRUTURA: Use o modelo AIDA (Atenção, Interesse, Desejo, Ação).
                    """
                    
                    try:
                        res = client.chat.completions.create(
                            model="gpt-3.5-turbo", 
                            messages=[{"role": "user", "content": prompt_f}]
                        )
                        texto_gerado = res.choices[0].message.content
                        
                        st.subheader("Legenda Gerada:")
                        st.code(texto_gerado, language=None)
                        
                        # TRATAMENTO DE EMOJIS PARA O WHATSAPP
                        texto_url = urllib.parse.quote(texto_gerado)
                        link_wa = f"https://api.whatsapp.com/send?text={texto_url}"
                        st.link_button("📲 Enviar para o WhatsApp", link_wa)
                        
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")
            else:
                st.warning("⚠️ Preencha o Versículo e o Tema para continuar.")

    # --- ABA PERFIL / CONFIGURAÇÕES (VERSÃO 20 CORES) ---
with tab_perfil:
    st.header("🎨 Personalização da Identidade Visual")
    st.write("Selecione uma cor abaixo para testar o visual do seu painel em tempo real.")

    # Dicionário com as 20 cores
    paleta = {
        "Azul Catedral": "#2C3E50", "Vinho Clássico": "#7B241C", "Verde Oliva": "#556B2F",
        "Roxo Imperial": "#4A235A", "Bronze": "#A0522D", "Grafite": "#212121",
        "Azul Petróleo": "#0E4B5A", "Ultravioleta": "#6C5CE7", "Rosa Chá": "#E84393",
        "Cinza Concreto": "#636E72", "Laranja Fogo": "#E17055", "Amarelo Glória": "#FBC531",
        "Azul Royal": "#0984E3", "Vermelho Vivo": "#D63031", "Verde Menta": "#00B894",
        "Areia": "#C2B280", "Terracota": "#E2725B", "Azul Céu": "#87CEEB",
        "Lavanda": "#A29BFE", "Marrom Café": "#4E342E"
    }

    # Criando o Grid de Cores (5 colunas x 4 linhas)
    colunas = st.columns(5)
    for i, (nome, hex_code) in enumerate(paleta.items()):
        with colunas[i % 5]:
            if st.button(nome, key=hex_code):
                st.session_state.cor_previa = hex_code
                st.toast(f"Testando: {nome}")

    st.divider()

    # Seletor Livre e Prévia
  # --- TRATAMENTO DE SEGURANÇA PARA A COR ---
# 1. Pegamos a cor da sessão (prévia) ou da planilha
cor_da_planilha = str(config['cor_tema']).strip() if pd.notnull(config['cor_tema']) else "#FF4B4B"

# 2. Se o usuário esqueceu o '#', nós adicionamos automaticamente
if not cor_da_planilha.startswith("#"):
    cor_da_planilha = f"#{cor_da_planilha}"

# 3. Garantimos que a cor tenha um tamanho válido (ex: #FFFFFF ou #FFF)
if len(cor_da_planilha) not in [4, 7]:
    cor_da_planilha = "#FF4B4B" # Fallback para vermelho caso o código seja inválido

# Agora usamos o valor tratado no widget
cor_final = st.color_picker(
    "Ajuste fino da cor:", 
    st.session_state.get('cor_previa', cor_da_planilha)
)
    
    col_previa, col_acao = st.columns(2)
    with col_previa:
        if st.button("👁️ Aplicar Prévia Visual"):
            aplicar_tema(cor_final)
            st.success("Visual alterado! (Apenas para esta sessão)")

    with col_acao:
        # Botão que gera o link para o WhatsApp do suporte
        msg_wa = urllib.parse.quote(f"Olá! Gostaria de definir a cor da {config['nome_exibicao']} como {cor_final}")
        st.link_button("💾 Salvar Permanentemente", f"https://api.whatsapp.com/send?phone=SEUNUMERO&text={msg_wa}")
