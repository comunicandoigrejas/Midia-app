import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÕES E ESTILO DINÂMICO
st.set_page_config(page_title="Comunicando Igrejas Pro", page_icon="⚡", layout="wide")

# Inicializa variáveis de sessão para evitar erros de navegação
if "logado" not in st.session_state:
    st.session_state.logado = False
if "cor_previa" not in st.session_state:
    st.session_state.cor_previa = None

# 2. CONEXÕES SEGURAS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Erro de conexão: {e}. Verifique seus Secrets no Streamlit Cloud.")
    st.stop()

# --- FUNÇÕES DE CARREGAMENTO ---
def carregar_usuarios():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios", ttl=0)

def carregar_configuracoes():
    return conn.read(spreadsheet=URL_PLANILHA, worksheet="configuracoes", ttl=0)

def carregar_calendario():
    try:
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="calendario", ttl=0)
    except:
        # Se a aba ainda não existir, cria um esqueleto para não quebrar o app
        return pd.DataFrame(columns=['igreja_id', 'data', 'rede_social', 'tema', 'status'])

# --- INJETOR DE CSS PARA TEMA PERSONALIZADO ---
def aplicar_tema(cor):
    st.markdown(f"""
        <style>
        /* Cor dos botões principais */
        .stButton>button {{ background-color: {cor}; color: white; border-radius: 8px; border: none; font-weight: bold; }}
        .stButton>button:hover {{ background-color: {cor}; opacity: 0.8; color: white; }}
        /* Cor das abas selecionadas */
        .stTabs [aria-selected="true"] {{ background-color: {cor}; color: white !important; border-radius: 5px; }}
        /* Esconder cabeçalho e rodapé padrão */
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
            email_input = st.text_input("E-mail de Usuário")
            senha_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Painel"):
                df_u = carregar_usuarios()
                user = df_u[(df_u['email'].str.lower() == email_input.lower()) & (df_u['senha'].astype(str) == str(senha_input))]
                
                if not user.empty:
                    if str(user.iloc[0]['status']).lower() == 'ativo':
                        st.session_state.logado = True
                        st.session_state.igreja_id = user.iloc[0]['igreja_id']
                        st.session_state.perfil = user.iloc[0]['perfil']
                        st.rerun()
                    else:
                        st.warning("Sua conta está inativa. Procure o administrador.")
                else:
                    st.error("E-mail ou senha incorretos.")

    with tab_rec:
        st.write("Esqueceu seus dados? Clique no botão abaixo para falar com nosso suporte técnico.")
        st.link_button("🔑 Solicitar Nova Senha", "https://wa.me/SEUNUMERO?text=Olá, preciso resetar minha senha no painel.")

# ==========================================
# DASHBOARD (APÓS LOGIN)
# ==========================================
else:
    # Carrega configurações da igreja logada
    df_config = carregar_configuracoes()
    conf_igreja = df_config[df_config['igreja_id'] == st.session_state.igreja_id]
    
    if conf_igreja.empty:
        st.error("Configurações não encontradas na planilha para este usuário.")
        st.stop()
    
    config = conf_igreja.iloc[0]
    
    # Define a cor base (Trata se estiver sem o #)
    cor_base = str(config['cor_tema']).strip() if pd.notnull(config['cor_tema']) else "#4169E1"
    if not cor_base.startswith("#"): cor_base = f"#{cor_base}"
    
    aplicar_tema(cor_base)

    st.sidebar.title(f"📱 {config['nome_exibicao']}")
    with st.sidebar:
        st.info(f"Logado como: {st.session_state.perfil}")
        if st.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()

    # ABAS DO SISTEMA
    tab_gen, tab_story, tab_cal, tab_cor = st.tabs([
        "✨ Legendas", "🎬 Stories", "📅 Calendário", "🎨 Personalizar"
    ])

    # --- ABA 1: GERADOR DE LEGENDAS ---
    with tab_gen:
        st.header("Criador de Conteúdo IA")
        col_a, col_b = st.columns(2)
        with col_a:
            rede = st.selectbox("Rede Social", ["Instagram", "Facebook", "LinkedIn", "TikTok"])
            estilo = st.selectbox("Tom de Voz", ["Inspiradora", "Pentecostal", "Teológica", "Jovem", "Urgente"])
        with col_b:
            versiculo = st.text_input("📖 Versículo Base (ARA)", placeholder="Ex: João 1:1")
            hashtags_extra = st.text_input("Hashtags Extras", placeholder="Separe por espaço")
        
        briefing = st.text_area("Sobre o que é a postagem?")
        
        if st.button("✨ Gerar Legenda Profissional"):
            if briefing:
                progresso = st.progress(0)
                with st.spinner("A IA está escrevendo sua legenda..."):
                    # Simulação de progresso visual
                    progresso.progress(50)
                    prompt = f"Atue como Social Media Cristão. Crie uma legenda para {rede} com tom {estilo}. Use Bíblia ARA. Mínimo 50 palavras. Tema: {briefing}. Versículo: {versiculo}. Use muitos emojis. Inclua as hashtags da igreja: {config['hashtags_fixas']} e extras: {hashtags_extra}."
                    
                    try:
                        res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                        legenda = res.choices[0].message.content
                        progresso.progress(100)
                        
                        st.subheader("Resultado:")
                        st.code(legenda, language=None)
                        
                        # Link Seguro WhatsApp
                        texto_wa = urllib.parse.quote(legenda)
                        st.link_button("📲 Enviar para o WhatsApp", f"https://api.whatsapp.com/send?text={texto_wa}")
                    except Exception as ia_err:
                        st.error(f"Erro na geração: {ia_err}")
            else:
                st.warning("Descreva o tema da postagem.")

    # --- ABA 2: ROTEIRO DE STORIES ---
    with tab_story:
        st.header("Roteiro de Stories (Sequência)")
        tema_story = st.text_input("Qual o tema da sequência de Stories?")
        if st.button("🎬 Criar Roteiro Estratégico"):
            with st.spinner("Gerando sequência engajadora..."):
                prompt_s = f"Crie um roteiro de 4 stories para a igreja {config['nome_exibicao']} sobre {tema_story}. Divida em: Story 1 (Gancho), Story 2 (Conteúdo), Story 3 (Interação), Story 4 (CTA)."
                res_s = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_s}])
                st.write(res_s.choices[0].message.content)

    # --- ABA 3: CALENDÁRIO & AGENDAMENTO ---
    with tab_cal:
        st.header("📅 Gestão de Cronograma")
        
        # 1. FORMULÁRIO PARA NOVO AGENDAMENTO
        with st.expander("➕ Agendar Nova Postagem", expanded=False):
            with st.form("novo_agendamento"):
                col_d, col_r = st.columns(2)
                with col_d:
                    data_post = st.date_input("Data da Postagem", datetime.now())
                with col_r:
                    rede_post = st.selectbox("Rede Social", ["Instagram", "Facebook", "YouTube", "WhatsApp"])
                
                tema_post = st.text_input("Tema/Assunto do Post")
                
                if st.form_submit_button("Salvar no Calendário"):
                    if tema_post:
                        try:
                            # Prepara os dados para salvar
                            novo_dado = pd.DataFrame([{
                                "igreja_id": st.session_state.igreja_id,
                                "data": data_post.strftime('%Y-%m-%d'),
                                "rede_social": rede_post,
                                "tema": tema_post,
                                "status": "Pendente"
                            }])
                            
                            # Envia para o Google Sheets (Aba calendario)
                            # Nota: O gsheets_connection usa o método 'update' ou 'create' para escrever
                            conn.create(spreadsheet=URL_PLANILHA, worksheet="calendario", data=novo_dado)
                            
                            st.success("✅ Postagem agendada com sucesso!")
                            st.balloons()
                            st.rerun() # Atualiza a tela para mostrar o novo item
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                    else:
                        st.warning("Por favor, preencha o tema do post.")

        st.divider()

        # 2. VISUALIZAÇÃO DO CALENDÁRIO ATUAL
        st.subheader("Seu Cronograma")
        df_calendario = carregar_calendario()
        
        # Filtra apenas para a igreja logada
        cal_igreja = df_calendario[df_calendario['igreja_id'].astype(str).str.lower() == st.session_state.igreja_id.lower()]
        
        if not cal_igreja.empty:
            # Organiza por data mais próxima
            cal_igreja = cal_igreja.sort_values(by='data', ascending=True)
            
            # Exibe a tabela formatada
            st.dataframe(
                cal_igreja[['data', 'rede_social', 'tema', 'status']], 
                use_container_width=True,
                hide_index=True
            )
            
            # Botão de ajuda para o usuário
            st.caption("ℹ️ Para editar ou excluir postagens, entre em contato com o administrador.")
        else:
            st.info("Você ainda não tem postagens agendadas. Use o botão acima para começar!")

    # --- ABA 4: PERSONALIZAÇÃO (A PALETA DE 20 CORES) ---
    with tab_cor:
        st.header("🎨 Cores do Painel")
        st.write("Escolha uma cor abaixo para testar o visual do seu painel.")
        
        # O DICIONÁRIO QUE ESTAVA DANDO ERRO (FECHADO CORRETAMENTE AGORA)
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
        for i, (nome, hex_code) in enumerate(paleta.items()):
            with cols[i % 5]:
                if st.button(nome, key=nome):
                    st.session_state.cor_previa = hex_code
        
        st.divider()
        cor_selecionada = st.color_picker("Ajuste Manual:", st.session_state.get('cor_previa', cor_base))
        
        col_preview, col_save = st.columns(2)
        with col_preview:
            if st.button("👁️ Aplicar Visual"):
                aplicar_tema(cor_selecionada)
                st.toast("Visual atualizado!")
        with col_save:
            msg_cor = urllib.parse.quote(f"Olá! Gostaria de definir minha cor como {cor_selecionada}")
            st.link_button("💾 Salvar Permanente", f"https://api.whatsapp.com/send?phone=SEUNUMERO&text={msg_cor}")
