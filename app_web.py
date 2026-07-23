import sqlite3
import hashlib
import io
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(
    page_title="Sistema de Controle de Torres",
    page_icon="🏗️",
    layout="wide"
)

# 2. CSS Customizado - Modo Escuro Nativo (Slate Dark - Trello Style)
st.markdown("""
    <style>
    /* Fundo Geral da Aplicação */
    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Textos e Títulos */
    h1, h2, h3, h4, h5, h6, label, p, span, div, .stMarkdown {
        color: #f8fafc !important;
    }

    /* Estilização das Abas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #1e293b !important;
        padding: 6px;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

    /* Campos de Entrada e Selects */
    input, select, textarea, div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
    }
    
    ::placeholder {
        color: #94a3b8 !important;
        opacity: 1;
    }

    /* Dropdowns / Menus */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }
    li[role="option"] {
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }
    li[role="option"]:hover {
        background-color: #334155 !important;
    }

    /* Botões */
    .stButton > button, div[data-testid="stPopover"] > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover, div[data-testid="stPopover"] > button:hover {
        background-color: #1d4ed8 !important;
    }

    /* Containers do Formulário */
    div[data-testid="stForm"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 20px !important;
    }

    /* Dataframe / Tabelas */
    [data-testid="stDataFrame"] {
        background-color: #1e293b !important;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS E SEGURANÇA ---
def get_connection():
    return sqlite3.connect("gestao_torres.db", check_same_thread=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL
            )
        ''')
        # Torres
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS torres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acionamento TEXT,
                projeto TEXT,
                revisao TEXT DEFAULT '00',
                tipo TEXT DEFAULT 'Torre',
                finalidade TEXT DEFAULT 'Fabricação',
                peso REAL DEFAULT 0.0,
                site_1 TEXT,
                site_2 TEXT,
                num_serie TEXT,
                local TEXT,
                elemento TEXT,
                cliente TEXT,
                responsavel TEXT,
                data TEXT,
                prazo TEXT,
                status_projeto TEXT DEFAULT 'Projeto',
                observacoes TEXT DEFAULT ''
            )
        ''')
        
        # Migração segura para bancos existentes
        try:
            cursor.execute("ALTER TABLE torres ADD COLUMN observacoes TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # Admin padrão
        cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, nome) VALUES (?, ?, ?)",
                ("admin", hash_password("admin123"), "Administrador")
            )
        conn.commit()

init_db()

def autenticar_usuario(username, password):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nome FROM usuarios WHERE username = ? AND password_hash = ?",
            (username, hash_password(password))
        )
        return cursor.fetchone()

def atualizar_status(torre_id, novo_status):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE torres SET status_projeto=? WHERE id=?", (novo_status, torre_id))
        conn.commit()
    st.cache_data.clear()

def atualizar_observacoes(torre_id, nova_obs):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE torres SET observacoes=? WHERE id=?", (nova_obs, torre_id))
        conn.commit()
    st.cache_data.clear()

@st.cache_data(ttl=5)
def carregar_dados():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM torres", conn)

# --- GERENCIAMENTO DE SESSÃO / LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""
    st.session_state["usuario_login"] = ""

if not st.session_state["autenticado"]:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.write("<br><br>", unsafe_allow_html=True)
        with st.form("form_login"):
            st.title("🔐 Acesso ao Sistema")
            st.caption("Digite suas credenciais para continuar")
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_entrar:
                user_info = autenticar_usuario(usuario, senha)
                if user_info:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_nome"] = user_info[0]
                    st.session_state["usuario_login"] = usuario
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.info("💡 **Acesso Padrão Inicial:** Usuário: `admin` | Senha: `admin123`")
    st.stop()

# --- SIDEBAR ---
st.sidebar.markdown(f"👤 **Usuário Logado:**\n### {st.session_state['usuario_nome']}")
st.sidebar.divider()
if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""
    st.session_state["usuario_login"] = ""
    st.rerun()

# --- APLICAÇÃO PRINCIPAL ---
df_global = carregar_dados()

col_title, col_btn = st.columns([6, 2])
with col_title:
    st.title("🏗️ Sistema de Controle de Torres")
with col_btn:
    with st.popover("➕ Cadastrar Nova Torre", use_container_width=True):
        st.subheader("Novo Cadastro")
        with st.form("form_nova_torre", clear_on_submit=True):
            f_acionamento = st.text_input("Acionamento *")
            f_projeto = st.text_input("Projeto *")
            f_cliente = st.selectbox("Cliente", ["BTC", "Del Infra", "Phoenix", "Global", "Reflay", "Winity", "Nexus", "Centennial"])
            f_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])
            f_finalidade = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo"])
            f_peso = st.number_input("Peso (kg)", min_value=0.0, step=50.0)
            f_responsavel = st.selectbox("Responsável", ["Ark Steel", "Support", "Towertec"])
            f_prazo = st.date_input("Prazo de Entrega", value=datetime.now() + timedelta(days=7))
            f_observacoes = st.text_area("Observações", placeholder="Adicione notas ou detalhes técnicos sobre o projeto...")

            if st.form_submit_button("Salvar Registro"):
                if f_acionamento and f_projeto:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO torres (acionamento, projeto, cliente, tipo, finalidade, peso, responsavel, prazo, data, observacoes, status_projeto)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Projeto')
                        ''', (f_acionamento, f_projeto, f_cliente, f_tipo, f_finalidade, f_peso, f_responsavel, f_prazo.strftime("%d/%m/%Y"), datetime.now().strftime("%d/%m/%Y"), f_observacoes))
                        conn.commit()
                    st.cache_data.clear()
                    st.success("Torre cadastrada!")
                    st.rerun()
                else:
                    st.error("Campos obrigatórios faltando.")

# ABAS DA APLICAÇÃO
aba_lista, aba_kanban, aba_dash, aba_cancelados, aba_usuarios = st.tabs([
    "📋 Listagem e Filtros", 
    "📊 Kanban Multi-Etapas", 
    "📈 Dashboards", 
    "🚫 Cancelados",
    "👥 Usuários"
])

# 1. LISTA E FILTROS
with aba_lista:
    st.subheader("Filtros de Pesquisa")
    c1, c2, c3 = st.columns(3)
    with c1:
        busca_texto = st.text_input("🔎 Pesquisa rápida", placeholder="Digite para buscar...")
    with c2:
        filtro_cliente = st.multiselect("Cliente", options=df_global["cliente"].unique() if not df_global.empty else [])
    with c3:
        filtro_status = st.multiselect("Status", options=df_global["status_projeto"].unique() if not df_global.empty else [])

    df_view = df_global.copy()
    if busca_texto and not df_view.empty:
        df_view = df_view[df_view.astype(str).apply(lambda row: row.str.contains(busca_texto, case=False).any(), axis=1)]
    if filtro_cliente and not df_view.empty:
        df_view = df_view[df_view["cliente"].isin(filtro_cliente)]
    if filtro_status and not df_view.empty:
        df_view = df_view[df_view["status_projeto"].isin(filtro_status)]

    st.subheader("Registros Encontrados")
    if not df_view.empty:
        st.dataframe(df_view, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_view.to_excel(writer, index=False, sheet_name='Torres')
        
        st.download_button(
            label="📥 Baixar Relatório em Excel",
            data=buffer.getvalue(),
            file_name=f"relatorio_torres_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Nenhum registro encontrado.")

# 2. KANBAN MULTI-ETAPAS (TRELLO STYLE)
with aba_kanban:
    st.subheader("Acompanhamento de Etapas do Projeto")
    
    # 5 etapas definidas no fluxo (incluindo Cancelado)
    etapas = ["Projeto", "Steel", "Sankhya", "Concluído", "Cancelado"]
    icones = ["📐 Projeto", "⚙️ Steel", "🏢 Sankhya", "✅ Concluído", "🚫 Cancelado"]
    
    cols = st.columns(5)

    for idx, etapa in enumerate(etapas):
        with cols[idx]:
            st.markdown(f"### {icones[idx]}")
            items = df_global[df_global["status_projeto"] == etapa]
            
            for _, item in items.iterrows():
                # Card no estilo Trello
                with st.container(border=True):
                    st.markdown(f"**#{item['id']} - {item['projeto']}**")
                    st.caption(f"**Cliente:** {item['cliente']}")
                    st.caption(f"**Peso:** {item['peso']} kg | **Prazo:** {item['prazo']}")
                    
                    # Exibição/Edição de Observações
                    obs_atual = item['observacoes'] if pd.notna(item['observacoes']) else ""
                    if obs_atual:
                        st.markdown(f"📌 *{obs_atual}*")
                    
                    with st.popover("📝 Obs", use_container_width=True):
                        st.caption(f"Editar observações do projeto #{item['id']}")
                        nova_obs_input = st.text_area("Observação:", value=obs_atual, key=f"obs_txt_{item['id']}")
                        if st.button("Salvar Obs", key=f"btn_obs_{item['id']}"):
                            atualizar_observacoes(item['id'], nova_obs_input)
                            st.rerun()

                    # Movimentação livre para qualquer etapa
                    etapa_selecionada = st.selectbox(
                        "Mover para:",
                        options=etapas,
                        index=etapas.index(etapa),
                        key=f"move_{item['id']}"
                    )
                    
                    if etapa_selecionada != etapa:
                        atualizar_status(item['id'], etapa_selecionada)
                        st.rerun()

# 3. DASHBOARDS
with aba_dash:
    st.subheader("Indicadores Gerais")
    if not df_global.empty:
        d1, d2 = st.columns(2)
        with d1:
            fig_bar = px.bar(
                df_global['cliente'].value_counts().reset_index(),
                x='cliente', y='count',
                title="Torres por Cliente",
                labels={'cliente': 'Cliente', 'count': 'Quantidade'},
                template="plotly_dark",
                color_discrete_sequence=['#2563eb']
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        with d2:
            fig_pie = px.pie(
                df_global, names='status_projeto',
                title="Distribuição por Etapa",
                hole=0.4,
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# 4. CANCELADOS (Filtro Direto)
with aba_cancelados:
    st.subheader("🚫 Projetos Cancelados")
    df_canc = df_global[df_global["status_projeto"] == "Cancelado"]
    if not df_canc.empty:
        st.dataframe(df_canc, use_container_width=True)
    else:
        st.info("Nenhum projeto cancelado registrado.")

# 5. GERENCIAMENTO DE USUÁRIOS
with aba_usuarios:
    st.subheader("👥 Gerenciamento de Usuários do Sistema")
    
    col_u1, col_u2 = st.columns([1, 1])
    
    with col_u1:
        st.markdown("### ➕ Cadastrar Novo Usuário")
        with st.form("form_novo_usuario", clear_on_submit=True):
            novo_username = st.text_input("Nome de Usuário (Login) *")
            novo_nome = st.text_input("Nome Completo *")
            nova_senha = st.text_input("Senha *", type="password")
            
            if st.form_submit_button("Cadastrar Usuário", use_container_width=True):
                if novo_username and novo_nome and nova_senha:
                    try:
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO usuarios (username, password_hash, nome) VALUES (?, ?, ?)",
                                (novo_username, hash_password(nova_senha), novo_nome)
                            )
                            conn.commit()
                        st.success(f"Usuário '{novo_username}' cadastrado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erro: Nome de usuário já existe!")
                else:
                    st.error("Preencha todos os campos obrigatórios.")

    with col_u2:
        st.markdown("### 📋 Usuários Cadastrados")
        with get_connection() as conn:
            df_users = pd.read_sql("SELECT id, username, nome FROM usuarios", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("### 🗑️ Excluir Usuário")
        user_to_delete = st.selectbox(
            "Selecione um usuário para remover", 
            df_users["username"].unique() if not df_users.empty else []
        )
        
        if st.button("Remover Usuário Selecionado", use_container_width=True):
            if user_to_delete == "admin":
                st.error("O usuário 'admin' principal não pode ser excluído!")
            elif user_to_delete == st.session_state["usuario_login"]:
                st.error("Você não pode excluir seu próprio usuário atual!")
            else:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE username = ?", (user_to_delete,))
                    conn.commit()
                st.success(f"Usuário '{user_to_delete}' removido!")
                st.rerun()
