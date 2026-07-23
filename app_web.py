import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# 1. Configuração Inicial da Página
st.set_page_config(
    page_title="Gestão Integrada de Torres",
    page_icon="🏗️",
    layout="wide"
)

# Estilo visual customizado
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .kanban-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        border-left: 4px solid #1f538d;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Conexão e Banco de Dados
def get_connection():
    return sqlite3.connect("gestao_torres.db", check_same_thread=False)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
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
                status_projeto TEXT DEFAULT 'A fazer',
                inicio_andamento_proj TEXT,
                fim_andamento_proj TEXT
            )
        ''')
        conn.commit()

init_db()

# Função para atualizar status rapidamente via Kanban
def atualizar_status(torre_id, novo_status):
    with get_connection() as conn:
        cursor = conn.cursor()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if novo_status == "Em andamento":
            cursor.execute("UPDATE torres SET status_projeto=?, inicio_andamento_proj=? WHERE id=?", (novo_status, agora, torre_id))
        elif novo_status == "Concluído":
            cursor.execute("UPDATE torres SET status_projeto=?, fim_andamento_proj=? WHERE id=?", (novo_status, agora, torre_id))
        else:
            cursor.execute("UPDATE torres SET status_projeto=? WHERE id=?", (novo_status, torre_id))
        conn.commit()
    st.cache_data.clear()

# Leitura com Cache para Alta Performance
@st.cache_data(ttl=5)
def carregar_dados():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM torres", conn)

df_global = carregar_dados()

# --- BARRA SUPERIOR E AÇÕES ---
st.title("🏗️ Sistema Integrado de Controle de Torres")

col_top1, col_top2 = st.columns([6, 2])

with col_top2:
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

# --- NAVEGAÇÃO DE ABAS ---
aba_lista, aba_kanban, aba_dash, aba_cancelados = st.tabs([
    "📋 Listagem e Filtros", 
    "📊 Kanban Interativo", 
    "📈 Dashboards", 
    "🚫 Cancelados"
])

# =========================================================================
# ABA 1: LISTA E BUSCA
# =========================================================================
with aba_lista:
    st.subheader("Filtros de Pesquisa")
    c1, c2, c3 = st.columns(3)
    with c1:
        busca_texto = st.text_input("🔎 Buscar por palavra-chave")
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
        
        # Gerar Excel para download
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
        st.info("Nenhum registro encontrado com os filtros aplicados.")

# =========================================================================
# ABA 2: KANBAN INTERATIVO
# =========================================================================
with aba_kanban:
    st.subheader("Acompanhamento do Fluxo de Produção")
    
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
                    st.caption(f"Cliente: {item['cliente']} | Peso: {item['peso']} kg")
                    st.caption(f"Prazo: {item['prazo']}")
                    
                    # Botões de movimentação rápida
                    btn_c1, btn_c2 = st.columns(2)
                    if status == "A fazer":
                        if btn_c1.button("Mover ➔", key=f"and_{item['id']}"):
                            atualizar_status(item['id'], "Em andamento")
                            st.rerun()
                    elif status == "Em andamento":
                        if btn_c1.button("◀ Voltar", key=f"faz_{item['id']}"):
                            atualizar_status(item['id'], "A fazer")
                            st.rerun()
                        if btn_c2.button("Concluir ✅", key=f"con_{item['id']}"):
                            atualizar_status(item['id'], "Concluído")
                            st.rerun()

# =========================================================================
# ABA 3: DASHBOARDS INTERATIVOS (PLOTLY)
# =========================================================================
with aba_dash:
    st.subheader("Visão Geral do Desempenho")
    if not df_global.empty:
        d_col1, d_col2 = st.columns(2)
        
        with d_col1:
            fig_bar = px.bar(
                df_global['cliente'].value_counts().reset_index(),
                x='cliente', y='count',
                title="Torres por Cliente",
                labels={'cliente': 'Cliente', 'count': 'Quantidade'},
                color_discrete_sequence=['#1f538d']
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with d_col2:
            fig_pie = px.pie(
                df_global, names='status_projeto',
                title="Distribuição de Status de Projetos",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# =========================================================================
# ABA 4: CANCELADOS
# =========================================================================
with aba_cancelados:
    st.subheader("🚫 Projetos Cancelados ou Interrompidos")
    df_canc = df_global[df_global["status_projeto"] == "Cancelado"]
    if not df_canc.empty:
        st.dataframe(df_canc, use_container_width=True)
    else:
        st.info("Nenhum projeto cancelado registrado.")
