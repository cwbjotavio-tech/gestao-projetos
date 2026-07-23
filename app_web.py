import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Sistema de Controle de Torres",
    page_icon="🏗️",
    layout="wide"
)

# --- BANCO DE DADOS ---
def init_db():
    try:
        with sqlite3.connect("gestao_torres.db", timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS torres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acionamento TEXT,
                    projeto TEXT,
                    revisao TEXT DEFAULT '00',
                    tipo TEXT DEFAULT 'Torre',
                    finalidade TEXT DEFAULT 'Fabricação',
                    peso REAL,
                    site_1 TEXT,
                    site_2 TEXT,
                    num_serie TEXT,
                    local TEXT,
                    elemento TEXT,
                    cliente TEXT,
                    responsavel TEXT,
                    data TEXT,
                    prazo TEXT,
                    status_projeto TEXT DEFAULT 'Em andamento',
                    status_steel TEXT DEFAULT 'A fazer',
                    status_sankhya TEXT DEFAULT 'A fazer',
                    inicio_andamento_proj TEXT,
                    fim_andamento_proj TEXT,
                    inicio_andamento_steel TEXT,
                    fim_andamento_steel TEXT,
                    inicio_andamento_sank TEXT,
                    fim_andamento_sank TEXT
                )
            ''')
            
            # Garantir colunas essenciais caso o banco seja antigo
            for col, tipo_col in [
                ("prazo", "TEXT"), ("tipo", "TEXT DEFAULT 'Torre'"), 
                ("revisao", "TEXT DEFAULT '00'"), ("finalidade", "TEXT DEFAULT 'Fabricação'")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE torres ADD COLUMN {col} {tipo_col}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")

init_db()

# Função para carregar dados do banco em um DataFrame pandas
def carregar_dados_df():
    try:
        with sqlite3.connect("gestao_torres.db", timeout=10.0) as conn:
            df = pd.read_sql("SELECT * FROM torres", conn)
            return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# --- INTERFACE PRINCIPAL (STREAMLIT) ---
st.title("🏗️ Sistema de Controle de Torres")

# Abas do sistema
aba_cadastro, aba_kanban, aba_indicadores, aba_cancelados = st.tabs([
    "📋 Cadastro e Informações", 
    "📊 Acompanhamento (Kanban)", 
    "📈 Indicadores (Dashboards)", 
    "🚫 Cancelados"
])

df_global = carregar_dados_df()

# =========================================================================
# ABA 1: CADASTRO E INFORMAÇÕES
# =========================================================================
with aba_cadastro:
    st.subheader("Gerenciamento de Torres e Projetos")
    
    col_btn1, col_btn2 = st.columns([2, 8])
    with col_btn1:
        if st.button("➕ Cadastrar Nova Torre", use_container_width=True):
            st.session_state["modal_cadastro"] = True

    # Modal / Formulário de Cadastro
    if st.session_state.get("modal_cadastro", False):
        with st.form("form_cadastro"):
            st.write("### Preencha os dados da Torre")
            c1, c2, c3 = st.columns(3)
            with c1:
                acionamento = st.text_input("Acionamento *")
                projeto = st.text_input("Projeto *")
                revisao = st.text_input("Revisão", value="00")
                tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])
                finalidade = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo"])
            with c2:
                peso = st.text_input("Peso (kg)", value="0")
                site_1 = st.text_input("Site I")
                site_2 = st.text_input("Site II")
                num_serie = st.text_input("Nº de Série")
                local = st.text_input("Local")
            with c3:
                elemento = st.text_input("Elemento")
                cliente = st.selectbox("Cliente", ["BTC", "Del Infra", "Phoenix", "Global", "Reflay", "Winity", "Nexus", "Centennial"])
                responsavel = st.selectbox("Responsável", ["Ark Steel", "Support", "Towertec"])
                data_cad = st.text_input("Data", value=datetime.now().strftime("%d/%m/%Y"))
                prazo_cad = st.text_input("Prazo", value=(datetime.now() + timedelta(days=5)).strftime("%d/%m/%Y"))

            submitted = st.form_submit_button("Salvar Cadastro")
            if submitted:
                if not acionamento or not projeto:
                    st.warning("Os campos 'Acionamento' e 'Projeto' são obrigatórios!")
                else:
                    try:
                        peso_val = float(peso.replace(',', '.'))
                        with sqlite3.connect("gestao_torres.db", timeout=10.0) as conn:
                            cursor = conn.cursor()
                            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute('''
                                INSERT INTO torres (
                                    acionamento, projeto, revisao, tipo, finalidade, peso, site_1, site_2, 
                                    num_serie, local, elemento, cliente, responsavel, data, prazo,
                                    status_projeto, inicio_andamento_proj
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Em andamento', ?)
                            ''', (acionamento, projeto, revisao, tipo, finalidade, peso_val, site_1, site_2, 
                                  num_serie, local, elemento, cliente, responsavel, data_cad, prazo_cad, agora))
                            conn.commit()
                        st.success("Torre cadastrada com sucesso!")
                        st.session_state["modal_cadastro"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    st.divider()

    # Filtros de Busca
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        busca = st.text_input("🔍 Pesquisa rápida", placeholder="Digite para buscar...")
    with f_col2:
        tipos_disponiveis = ["Todos"] + list(df_global["tipo"].dropna().unique()) if not df_global.empty else ["Todos"]
        filtro_tipo = st.selectbox("Filtrar por Tipo", tipos_disponiveis)
    with f_col3:
        status_disponiveis = ["Todos", "Em andamento", "Concluído", "Cancelado"]
        filtro_status = st.selectbox("Filtrar por Status", status_disponiveis)

    # Filtragem do DataFrame
    df_filtrado = df_global.copy()
    if not df_filtrado.empty:
        if busca:
            df_filtrado = df_filtrado[df_filtrado.astype(str).apply(lambda x: x.str.contains(busca, case=False)).any(axis=1)]
        if filtro_tipo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["tipo"] == filtro_tipo]
        if filtro_status != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status_projeto"] == filtro_status]

    st.subheader("⏳ Projetos em Andamento / A Fazer")
    if not df_filtrado.empty:
        df_andamento = df_filtrado[df_filtrado["status_projeto"] != "Cancelado"]
        st.dataframe(df_andamento, use_container_width=True)
    else:
        st.info("Nenhum registro encontrado.")

# =========================================================================
# ABA 2: KANBAN
# =========================================================================
with aba_kanban:
    st.subheader("📊 Acompanhamento de Projetos (Kanban)")
    st.markdown("*Apenas projetos com finalidade 'Fabricação' e ativos aparecem aqui.*")
    
    if not df_global.empty:
        fab_df = df_global[(df_global["finalidade"] == "Fabricação") & (df_global["status_projeto"] != "Cancelado")]
        
        col_k1, col_k2, col_k3 = st.columns(3)
        with col_k1:
            st.markdown("### 📌 A Fazer")
            a_fazer = fab_df[fab_df["status_projeto"] == "A fazer"]
            for _, row in a_fazer.iterrows():
                st.info(f"**ID {row['id']}** - {row['projeto']}\n\nCliente: {row['cliente']}")
        with col_k2:
            st.markdown("### ⏳ Em Andamento")
            em_and = fab_df[fab_df["status_projeto"] == "Em andamento"]
            for _, row in em_and.iterrows():
                st.warning(f"**ID {row['id']}** - {row['projeto']}\n\nCliente: {row['cliente']}")
        with col_k3:
            st.markdown("### ✅ Concluído")
            concl = fab_df[fab_df["status_projeto"] == "Concluído"]
            for _, row in concl.iterrows():
                st.success(f"**ID {row['id']}** - {row['projeto']}\n\nCliente: {row['cliente']}")

# =========================================================================
# ABA 3: INDICADORES
# =========================================================================
with aba_indicadores:
    st.subheader("📈 Indicadores e Dashboards")
    if not df_global.empty:
        c_ind1, c_ind2 = st.columns(2)
        with c_ind1:
            st.write("#### Quantidade de Torres por Cliente")
            fig, ax = plt.subplots(figsize=(6, 4))
            df_global["cliente"].value_counts().plot(kind="bar", ax=ax, color="#1f538d")
            plt.xticks(rotation=45)
            st.pyplot(fig)
        with c_ind2:
            st.write("#### Status dos Projetos")
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            df_global["status_projeto"].value_counts().plot(kind="pie", ax=ax2, autopct='%1.1f%%')
            st.pyplot(fig2)

# =========================================================================
# ABA 4: CANCELADOS
# =========================================================================
with aba_cancelados:
    st.subheader("🚫 Torres Canceladas")
    if not df_global.empty:
        df_canc = df_global[df_global["status_projeto"] == "Cancelado"]
        if not df_canc.empty:
            st.dataframe(df_canc, use_container_width=True)
        else:
            st.info("Nenhuma torre cancelada.")
