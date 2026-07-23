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

# 2. CSS Customizado para Correção de Contrastes e Tema Profissional
st.markdown("""
    <style>
    /* Estilo Geral da Aplicação */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Forçar cor legível em todos os Títulos e Textos */
    h1, h2, h3, h4, h5, h6, label, p, span, .stMarkdown {
        color: #0f172a !important;
    }

    /* Estilização das Abas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        padding: 8px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        color: #475569 !important;
        font-weight: 600;
        border-radius: 6px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

    /* Entradas de Texto / Inputs */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
    }

    /* Cards do Kanban e Formulários */
    .css-card {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE SEGURANÇA E BANCO DE DADOS ---
def get_connection():
    return sqlite3.connect("gestao_torres.db", check_same_thread=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Tabela de Usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL
            )
        ''')
        # Tabela de Torres
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
                status_projeto TEXT DEFAULT 'A fazer'
            )
        ''')
        
        # Criar usuário administrador padrão se não existir
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

@st.cache_data(ttl=5)
def carregar_dados():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM torres", conn)

# --- GERENCIAMENTO DE SESSÃO / LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""

# TELA DE LOGIN
if not st.session_state["autenticado"]:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.write("<br><br>", unsafe_allow_html=True)
        with st.form("form_login"):
            st.title("🔐 Acesso ao Sistema")
            st.subheader("Controle de Torres e Projetos")
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar", use_container_width=True)
            
            if btn_entrar:
                user_info = autenticar_usuario(usuario, senha)
                if user_info:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_nome"] = user_info[0]
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.info("💡 **Acesso Inicial Padrão:** Usuário: `admin` | Senha: `admin123`")
    st.stop()

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.markdown(f"👤 **Usuário:** {st.session_state['usuario_nome']}")
if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
    st.session_state["autenticado"] = False
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

            if st.form_submit_button("Salvar Registro"):
                if f_acionamento and f_projeto:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO torres (acionamento, projeto, cliente, tipo, finalidade, peso, responsavel, prazo, data, status_projeto)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'A fazer')
                        ''', (f_acionamento, f_projeto, f_cliente, f_tipo, f_finalidade, f_peso, f_responsavel, f_prazo.strftime("%d/%m/%Y"), datetime.now().strftime("%d/%m/%Y")))
                        conn.commit()
                    st.cache_data.clear()
                    st.success("Torre cadastrada!")
                    st.rerun()
                else:
                    st.error("Campos obrigatórios faltando.")

# ABAS DA APLICAÇÃO
aba_lista, aba_kanban, aba_dash, aba_cancelados = st.tabs([
    "📋 Listagem e Filtros", 
    "📊 Kanban Interativo", 
    "📈 Dashboards", 
    "🚫 Cancelados"
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

# 2. KANBAN INTERATIVO
with aba_kanban:
    st.subheader("Fluxo de Produção")
    col_a_fazer, col_em_andamento, col_concluido = st.columns(3)
    
    statuses = ["A fazer", "Em andamento", "Concluído"]
    cols = [col_a_fazer, col_em_andamento, col_concluido]
    icones = ["📌 A Fazer", "⏳ Em Andamento", "✅ Concluído"]

    for idx, status in enumerate(statuses):
        with cols[idx]:
            st.markdown(f"### {icones[idx]}")
            items = df_global[df_global["status_projeto"] == status]
            
            for _, item in items.iterrows():
                with st.container(border=True):
                    st.markdown(f"**#{item['id']} - {item['projeto']}**")
                    st.caption(f"**Cliente:** {item['cliente']} | **Peso:** {item['peso']} kg")
                    st.caption(f"**Prazo:** {item['prazo']}")
                    
                    b1, b2 = st.columns(2)
                    if status == "A fazer":
                        if b1.button("Mover ➔", key=f"and_{item['id']}"):
                            atualizar_status(item['id'], "Em andamento")
                            st.rerun()
                    elif status == "Em andamento":
                        if b1.button("◀ Voltar", key=f"faz_{item['id']}"):
                            atualizar_status(item['id'], "A fazer")
                            st.rerun()
                        if b2.button("Concluir ✅", key=f"con_{item['id']}"):
                            atualizar_status(item['id'], "Concluído")
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
                color_discrete_sequence=['#2563eb']
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        with d2:
            fig_pie = px.pie(
                df_global, names='status_projeto',
                title="Status dos Projetos",
                hole=0.4,
                color_discrete_sequence=['#f59e0b', '#3b82f6', '#10b981']
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# 4. CANCELADOS
with aba_cancelados:
    st.subheader("🚫 Projetos Cancelados")
    df_canc = df_global[df_global["status_projeto"] == "Cancelado"]
    if not df_canc.empty:
        st.dataframe(df_canc, use_container_width=True)
    else:
        st.info("Nenhum projeto cancelado.")
