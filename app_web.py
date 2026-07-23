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

# 2. CSS Customizado - Modo Escuro Slate Dark (Trello Style)
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

    /* Cartões de Métricas */
    [data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        padding: 12px !important;
        border-radius: 8px !important;
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS torres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acionamento TEXT,
                projeto TEXT,
                revisao TEXT DEFAULT '00',
                tipo TEXT DEFAULT 'Torre',
                finalidade TEXT DEFAULT 'Fabricação',
                peso REAL DEFAULT 0.0,
                site_1 TEXT DEFAULT '',
                site_2 TEXT DEFAULT '',
                num_serie TEXT DEFAULT '',
                local TEXT DEFAULT '',
                elemento TEXT DEFAULT '',
                cliente TEXT,
                responsavel TEXT,
                data TEXT,
                prazo TEXT,
                status_projeto TEXT DEFAULT 'Projeto',
                observacoes TEXT DEFAULT '',
                estado_relogio TEXT DEFAULT 'parado',
                timestamp_ultimo_inicio TEXT DEFAULT '',
                tempo_projeto_sec INTEGER DEFAULT 0,
                inicio_projeto TEXT DEFAULT '',
                fim_projeto TEXT DEFAULT '',
                tempo_steel_sec INTEGER DEFAULT 0,
                inicio_steel TEXT DEFAULT '',
                fim_steel TEXT DEFAULT '',
                tempo_sankhya_sec INTEGER DEFAULT 0,
                inicio_sankhya TEXT DEFAULT '',
                fim_sankhya TEXT DEFAULT ''
            )
        ''')
        
        # Migração dinâmica de colunas
        cols_novas = [
            ("revisao", "TEXT DEFAULT '00'"),
            ("site_1", "TEXT DEFAULT ''"),
            ("site_2", "TEXT DEFAULT ''"),
            ("num_serie", "TEXT DEFAULT ''"),
            ("local", "TEXT DEFAULT ''"),
            ("elemento", "TEXT DEFAULT ''"),
            ("observacoes", "TEXT DEFAULT ''"),
            ("estado_relogio", "TEXT DEFAULT 'parado'"),
            ("timestamp_ultimo_inicio", "TEXT DEFAULT ''"),
            ("tempo_projeto_sec", "INTEGER DEFAULT 0"),
            ("inicio_projeto", "TEXT DEFAULT ''"),
            ("fim_projeto", "TEXT DEFAULT ''"),
            ("tempo_steel_sec", "INTEGER DEFAULT 0"),
            ("inicio_steel", "TEXT DEFAULT ''"),
            ("fim_steel", "TEXT DEFAULT ''"),
            ("tempo_sankhya_sec", "INTEGER DEFAULT 0"),
            ("inicio_sankhya", "TEXT DEFAULT ''"),
            ("fim_sankhya", "TEXT DEFAULT ''")
        ]
        for col_nome, col_tipo in cols_novas:
            try:
                cursor.execute(f"ALTER TABLE torres ADD COLUMN {col_nome} {col_tipo}")
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

# --- FUNÇÕES UTILITÁRIAS DE TEMPO E AÇÕES ---
def formatar_segundos(segundos):
    if not segundos or segundos <= 0:
        return "00:00:00"
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"

def obter_tempo_decorrido_etapa(item, etapa_key):
    coluna = f'tempo_{etapa_key}_sec'
    if coluna not in item or pd.isna(item[coluna]):
        return 0
    
    sec = item[coluna] or 0
    if item['status_projeto'].lower() == etapa_key and item['estado_relogio'] == 'rodando' and item['timestamp_ultimo_inicio']:
        try:
            dt_inicio = datetime.fromisoformat(item['timestamp_ultimo_inicio'])
            sec += int((datetime.now() - dt_inicio).total_seconds())
        except Exception:
            pass
    return sec

def acao_iniciar_relogio(torre_id, etapa_key):
    now_iso = datetime.now().isoformat()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT inicio_{etapa_key} FROM torres WHERE id=?", (torre_id,))
        res = cursor.fetchone()
        if not res or not res[0]:
            cursor.execute(f"UPDATE torres SET inicio_{etapa_key}=? WHERE id=?", (now_str, torre_id))
        cursor.execute("UPDATE torres SET estado_relogio='rodando', timestamp_ultimo_inicio=? WHERE id=?", (now_iso, torre_id))
        conn.commit()
    st.cache_data.clear()

def acao_pausar_relogio(torre_id, etapa_key):
    now = datetime.now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT tempo_{etapa_key}_sec, timestamp_ultimo_inicio FROM torres WHERE id=?", (torre_id,))
        res = cursor.fetchone()
        if res and res[1]:
            dt_inicio = datetime.fromisoformat(res[1])
            elapsed = int((now - dt_inicio).total_seconds())
            novo_tempo = (res[0] or 0) + elapsed
            cursor.execute(f"UPDATE torres SET tempo_{etapa_key}_sec=?, estado_relogio='parado', timestamp_ultimo_inicio='' WHERE id=?", (novo_tempo, torre_id))
            conn.commit()
    st.cache_data.clear()

def acao_finalizar_etapa(torre_id, etapa_atual, proxima_etapa):
    etapa_key = etapa_atual.lower()
    now = datetime.now()
    now_str = now.strftime("%d/%m/%Y %H:%M")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT tempo_{etapa_key}_sec, timestamp_ultimo_inicio, estado_relogio FROM torres WHERE id=?", (torre_id,))
        res = cursor.fetchone()
        novo_tempo = res[0] or 0 if res else 0
        if res and res[2] == 'rodando' and res[1]:
            dt_inicio = datetime.fromisoformat(res[1])
            novo_tempo += int((now - dt_inicio).total_seconds())
        
        cursor.execute(f'''
            UPDATE torres SET 
                tempo_{etapa_key}_sec=?, 
                fim_{etapa_key}=?, 
                estado_relogio='parado', 
                timestamp_ultimo_inicio='',
                status_projeto=?
            WHERE id=?
        ''', (novo_tempo, now_str, proxima_etapa, torre_id))
        conn.commit()
    st.cache_data.clear()

def excluir_torre(torre_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM torres WHERE id=?", (torre_id,))
        conn.commit()
    st.cache_data.clear()

def editar_torre_completo(torre_id, acionamento, projeto, revisao, tipo, finalidade, peso, site_1, site_2, num_serie, local, elemento, cliente, responsavel, prazo, observacoes):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE torres SET 
                acionamento=?, projeto=?, revisao=?, tipo=?, finalidade=?, peso=?, 
                site_1=?, site_2=?, num_serie=?, local=?, elemento=?, cliente=?, 
                responsavel=?, prazo=?, observacoes=?
            WHERE id=?
        ''', (acionamento, projeto, revisao, tipo, finalidade, peso, site_1, site_2, num_serie, local, elemento, cliente, responsavel, prazo, observacoes, torre_id))
        conn.commit()
    st.cache_data.clear()

def autenticar_usuario(username, password):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM usuarios WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
        return cursor.fetchone()

@st.cache_data(ttl=3)
def carregar_dados():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM torres", conn)

# --- TELA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""
    st.session_state["usuario_login"] = ""

if not st.session_state["autenticado"]:
    _, col_l2, _ = st.columns([1, 2, 1])
    with col_l2:
        st.write("<br><br>", unsafe_allow_html=True)
        with st.form("form_login"):
            st.title("🔐 Acesso ao Sistema")
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                user_info = autenticar_usuario(usuario, senha)
                if user_info:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_nome"] = user_info[0]
                    st.session_state["usuario_login"] = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.info("💡 **Acesso Padrão:** Usuário: `admin` | Senha: `admin123`")
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

col_title, col_b1, col_b2 = st.columns([5, 2, 2])
with col_title:
    st.title("🏗️ Controle de Torres")

with col_b1:
    with st.popover("📥 Importar Planilha", use_container_width=True):
        st.subheader("Carregar Cadastros (.xlsx / .csv)")
        uploaded_file = st.file_uploader("Selecione o arquivo", type=["xlsx", "csv"])
        if uploaded_file and st.button("Confirmar Importação"):
            try:
                df_imp = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                with get_connection() as conn:
                    cursor = conn.cursor()
                    for _, row in df_imp.iterrows():
                        cursor.execute('''
                            INSERT INTO torres (acionamento, projeto, cliente, tipo, finalidade, peso, responsavel, prazo, data, observacoes, status_projeto)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Projeto')
                        ''', (
                            str(row.get('acionamento', '')),
                            str(row.get('projeto', '')),
                            str(row.get('cliente', 'BTC')),
                            str(row.get('tipo', 'Torre')),
                            str(row.get('finalidade', 'Fabricação')),
                            float(row.get('peso', 0.0) if pd.notna(row.get('peso')) else 0.0),
                            str(row.get('responsavel', 'Support')),
                            str(row.get('prazo', datetime.now().strftime("%d/%m/%Y"))),
                            datetime.now().strftime("%d/%m/%Y"),
                            str(row.get('observacoes', 'Importado via planilha'))
                        ))
                    conn.commit()
                st.cache_data.clear()
                st.success("Planilha importada com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao importar: {e}")

with col_b2:
    with st.popover("➕ Cadastrar Torre", use_container_width=True):
        st.subheader("Novo Cadastro")
        with st.form("form_nova_torre", clear_on_submit=True):
            f_acionamento = st.text_input("Acionamento *")
            f_projeto = st.text_input("Projeto *")
            f_revisao = st.text_input("Revisão", value="00")
            f_cliente = st.selectbox("Cliente", ["BTC", "Del Infra", "Phoenix", "Global", "Reflay", "Winity", "Nexus", "Centennial"])
            f_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])
            f_finalidade = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo"])
            f_peso = st.number_input("Peso (kg)", min_value=0.0, step=50.0)
            f_site1 = st.text_input("Site I")
            f_site2 = st.text_input("Site II")
            f_num_serie = st.text_input("Nº Série")
            f_local = st.text_input("Local")
            f_elemento = st.text_input("Elemento")
            f_responsavel = st.selectbox("Responsável", ["Ark Steel", "Support", "Towertec"])
            f_prazo = st.date_input("Prazo de Entrega", value=datetime.now() + timedelta(days=7))
            f_observacoes = st.text_area("Observações")

            if st.form_submit_button("Salvar Registro"):
                if f_acionamento and f_projeto:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO torres (acionamento, projeto, revisao, cliente, tipo, finalidade, peso, site_1, site_2, num_serie, local, elemento, responsavel, prazo, data, observacoes, status_projeto)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Projeto')
                        ''', (f_acionamento, f_projeto, f_revisao, f_cliente, f_tipo, f_finalidade, f_peso, f_site1, f_site2, f_num_serie, f_local, f_elemento, f_responsavel, f_prazo.strftime("%d/%m/%Y"), datetime.now().strftime("%d/%m/%Y"), f_observacoes))
                        conn.commit()
                    st.cache_data.clear()
                    st.success("Torre cadastrada!")
                    st.rerun()

# ABAS
aba_lista, aba_kanban, aba_dash, aba_cancelados, aba_usuarios = st.tabs([
    "📋 Listagem e Tempos", 
    "📊 Kanban Multi-Etapas", 
    "📈 Dashboards", 
    "🚫 Cancelados",
    "👥 Usuários"
])

# 1. LISTA COM CONTROLE DE TEMPO DETALHADO, COLUNAS RESTAURADAS E AÇÕES
with aba_lista:
    st.subheader("Filtros e Relatório Completo")
    c1, c2, c3 = st.columns(3)
    with c1:
        busca_texto = st.text_input("🔎 Pesquisa rápida", placeholder="Buscar por projeto, acionamento...")
    with c2:
        filtro_cliente = st.multiselect("Cliente", options=df_global["cliente"].dropna().unique() if not df_global.empty else [])
    with c3:
        filtro_status = st.multiselect("Status", options=df_global["status_projeto"].dropna().unique() if not df_global.empty else [])

    df_view = df_global.copy()
    if busca_texto and not df_view.empty:
        df_view = df_view[df_view.astype(str).apply(lambda row: row.str.contains(busca_texto, case=False).any(), axis=1)]
    if filtro_cliente and not df_view.empty:
        df_view = df_view[df_view["cliente"].isin(filtro_cliente)]
    if filtro_status and not df_view.empty:
        df_view = df_view[df_view["status_projeto"].isin(filtro_status)]

    if not df_view.empty:
        # Montagem de todas as colunas correspondentes à imagem do usuário
        df_view['ID'] = df_view['id']
        df_view['Acionamento'] = df_view['acionamento']
        df_view['Projeto'] = df_view['projeto']
        df_view['Revisão'] = df_view['revisao'].fillna('00')
        df_view['Tipo'] = df_view['tipo']
        df_view['Finalidade'] = df_view['finalidade']
        df_view['Peso (kg)'] = df_view['peso']
        df_view['Site I'] = df_view['site_1'].fillna('')
        df_view['Site II'] = df_view['site_2'].fillna('')
        df_view['Nº. Série'] = df_view['num_serie'].fillna('')
        df_view['Local'] = df_view['local'].fillna('')
        df_view['Elemento'] = df_view['elemento'].fillna('')
        df_view['Cliente'] = df_view['cliente']
        df_view['Responsável'] = df_view['responsavel']
        df_view['Data'] = df_view['data']
        df_view['Prazo'] = df_view['prazo']
        df_view['Etapa'] = df_view['status_projeto']
        
        # Cálculos de Progresso e Status
        df_view['Progresso (%)'] = df_view['status_projeto'].map({
            'Projeto': '25%', 'Steel': '50%', 'Sankhya': '75%', 'Concluído': '100%', 'Cancelado': '0%'
        }).fillna('0%')
        
        df_view['Status Geral'] = df_view['estado_relogio'].map({
            'rodando': '🟢 Em Execução', 'parado': '🔴 Pausado'
        }).fillna('🔴 Pausado')
        
        df_view['Data de Cadastro'] = df_view['inicio_projeto'].apply(lambda x: x if x else '-')
        df_view['Fim Projeto'] = df_view['fim_projeto'].apply(lambda x: x if x else '-')
        df_view['Fim Steel'] = df_view['fim_steel'].apply(lambda x: x if x else '-')
        df_view['Fim Sankhya'] = df_view['fim_sankhya'].apply(lambda x: x if x else '-')
        
        df_view['Tempo Projeto'] = df_view.apply(lambda row: formatar_segundos(obter_tempo_decorrido_etapa(row, 'projeto')), axis=1)
        df_view['Tempo Steel'] = df_view.apply(lambda row: formatar_segundos(obter_tempo_decorrido_etapa(row, 'steel')), axis=1)
        df_view['Tempo Sankhya'] = df_view.apply(lambda row: formatar_segundos(obter_tempo_decorrido_etapa(row, 'sankhya')), axis=1)

        df_view['Status Projeto'] = df_view.apply(lambda r: 'Concluído' if r['fim_projeto'] else ('Em Andamento' if r['status_projeto'] == 'Projeto' else 'Pendente'), axis=1)
        df_view['Status Steel'] = df_view.apply(lambda r: 'Concluído' if r['fim_steel'] else ('Em Andamento' if r['status_projeto'] == 'Steel' else 'Pendente'), axis=1)
        df_view['Status Sankhya'] = df_view.apply(lambda r: 'Concluído' if r['fim_sankhya'] else ('Em Andamento' if r['status_projeto'] == 'Sankhya' else 'Pendente'), axis=1)

        cols_display = [
            'ID', 'Acionamento', 'Projeto', 'Revisão', 'Tipo', 'Finalidade', 'Peso (kg)',
            'Site I', 'Site II', 'Nº. Série', 'Local', 'Elemento', 'Cliente', 'Responsável',
            'Data', 'Prazo', 'Etapa', 'Progresso (%)', 'Status Geral', 'Data de Cadastro',
            'Fim Projeto', 'Fim Steel', 'Fim Sankhya', 'Tempo Projeto', 'Tempo Steel',
            'Tempo Sankhya', 'Status Projeto', 'Status Steel', 'Status Sankhya'
        ]
        
        st.dataframe(df_view[cols_display], use_container_width=True, hide_index=True)

        st.divider()

        # PAINEL DE AÇÕES (EDITAR / EXCLUIR NA LISTAGEM)
        st.subheader("⚡ Ações na Listagem (Editar / Excluir Registros)")
        col_sel, col_act1, col_act2 = st.columns([3, 1, 1])

        opcoes_torres = {f"#{row['id']} - {row['projeto']} ({row['cliente']})": row['id'] for _, row in df_view.iterrows()}
        
        with col_sel:
            torre_selecionada_label = st.selectbox("Selecione um projeto para modificar:", list(opcoes_torres.keys()))
            id_selecionado = opcoes_torres[torre_selecionada_label]
            item_sel = df_view[df_view['id'] == id_selecionado].iloc[0]

        with col_act1:
            with st.popover("✏️ Editar Projeto", use_container_width=True):
                st.write(f"**Editando ID #{id_selecionado}**")
                with st.form(key=f"form_edit_list_{id_selecionado}"):
                    e_ac = st.text_input("Acionamento", value=str(item_sel['acionamento']))
                    e_proj = st.text_input("Projeto", value=str(item_sel['projeto']))
                    e_rev = st.text_input("Revisão", value=str(item_sel['revisao'] or '00'))
                    e_cli = st.selectbox("Cliente", ["BTC", "Del Infra", "Phoenix", "Global", "Reflay", "Winity", "Nexus", "Centennial"], index=0)
                    e_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])
                    e_fin = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo"])
                    e_peso = st.number_input("Peso (kg)", value=float(item_sel['peso']))
                    e_s1 = st.text_input("Site I", value=str(item_sel['site_1'] or ''))
                    e_s2 = st.text_input("Site II", value=str(item_sel['site_2'] or ''))
                    e_ns = st.text_input("Nº Série", value=str(item_sel['num_serie'] or ''))
                    e_loc = st.text_input("Local", value=str(item_sel['local'] or ''))
                    e_elem = st.text_input("Elemento", value=str(item_sel['elemento'] or ''))
                    e_resp = st.selectbox("Responsável", ["Ark Steel", "Support", "Towertec"])
                    e_prazo = st.text_input("Prazo", value=str(item_sel['prazo']))
                    e_obs = st.text_area("Observações", value=str(item_sel['observacoes'] or ''))
                    
                    if st.form_submit_button("Salvar Alterações"):
                        editar_torre_completo(id_selecionado, e_ac, e_proj, e_rev, e_tipo, e_fin, e_peso, e_s1, e_s2, e_ns, e_loc, e_elem, e_cli, e_resp, e_prazo, e_obs)
                        st.success("Projeto atualizado com sucesso!")
                        st.rerun()

        with col_act2:
            with st.popover("🗑️ Excluir Projeto", use_container_width=True):
                st.warning(f"Excluir definitivamente o projeto #{id_selecionado}?")
                if st.button("Sim, Excluir", key=f"del_list_{id_selecionado}"):
                    excluir_torre(id_selecionado)
                    st.success("Projeto excluído!")
                    st.rerun()

        st.write("<br>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_view[cols_display].to_excel(writer, index=False, sheet_name='Torres')
        
        st.download_button(
            label="📥 Baixar Relatório Completo em Excel",
            data=buffer.getvalue(),
            file_name=f"relatorio_torres_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Nenhum registro encontrado.")

# 2. KANBAN MULTI-ETAPAS
with aba_kanban:
    st.subheader("Acompanhamento e Controle de Tempo por Etapa")
    
    etapas_ordem = ["Projeto", "Steel", "Sankhya", "Concluído", "Cancelado"]
    icones = ["📐 Projeto", "⚙️ Steel", "🏢 Sankhya", "✅ Concluído", "🚫 Cancelado"]
    
    cols = st.columns(5)

    for idx, etapa_coluna in enumerate(etapas_ordem):
        with cols[idx]:
            st.markdown(f"### {icones[idx]}")
            
            for _, item in df_global.iterrows():
                id_item = item['id']
                etapa_atual = item['status_projeto']
                etapa_key = etapa_coluna.lower()
                is_etapa_ativa = (etapa_coluna == etapa_atual)
                
                with st.container(border=True):
                    st.markdown(f"**#{id_item} - {item['projeto']}**")
                    st.caption(f"**Cliente:** {item['cliente']} | **Prazo:** {item['prazo']}")
                    
                    segundos_etapa = obter_tempo_decorrido_etapa(item, etapa_key) if etapa_key in ['projeto', 'steel', 'sankhya'] else 0
                    tempo_str = formatar_segundos(segundos_etapa)
                    
                    if is_etapa_ativa:
                        if etapa_coluna in ["Projeto", "Steel", "Sankhya"]:
                            st.markdown(f"⏱️ **Tempo na Etapa:** `{tempo_str}`")
                            if item['estado_relogio'] == 'rodando':
                                st.caption("🟢 **Em Execução**")
                            else:
                                st.caption("🔴 **Pausado/Aguardando**")

                            proxima_etapa = etapas_ordem[etapas_ordem.index(etapa_coluna) + 1]
                            
                            c_btn1, c_btn2 = st.columns(2)
                            with c_btn1:
                                if item['estado_relogio'] == 'parado':
                                    if st.button("▶️ Iniciar", key=f"start_{id_item}_{etapa_key}"):
                                        acao_iniciar_relogio(id_item, etapa_key)
                                        st.rerun()
                                else:
                                    if st.button("⏸️ Pausar", key=f"pause_{id_item}_{etapa_key}"):
                                        acao_pausar_relogio(id_item, etapa_key)
                                        st.rerun()
                            
                            with c_btn2:
                                if st.button("✅ Finalizar", key=f"fin_{id_item}_{etapa_key}"):
                                    acao_finalizar_etapa(id_item, etapa_coluna, proxima_etapa)
                                    st.rerun()

                            if st.button("🚫 Cancelar Projeto", key=f"canc_{id_item}_{etapa_key}", use_container_width=True):
                                acao_finalizar_etapa(id_item, etapa_coluna, "Cancelado")
                                st.rerun()
                        elif etapa_coluna == "Concluído":
                            st.success("✅ Projeto Concluído")
                        elif etapa_coluna == "Cancelado":
                            st.error("🚫 Projeto Cancelado")

                        c_ed1, c_ed2 = st.columns(2)
                        with c_ed1:
                            with st.popover("✏️ Editar", use_container_width=True):
                                with st.form(key=f"edit_form_{id_item}"):
                                    e_ac = st.text_input("Acionamento", value=item['acionamento'])
                                    e_proj = st.text_input("Projeto", value=item['projeto'])
                                    e_rev = st.text_input("Revisão", value=item['revisao'] or '00')
                                    e_cli = st.selectbox("Cliente", ["BTC", "Del Infra", "Phoenix", "Global", "Reflay", "Winity", "Nexus", "Centennial"], index=0)
                                    e_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])
                                    e_fin = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo"])
                                    e_peso = st.number_input("Peso (kg)", value=float(item['peso']))
                                    e_s1 = st.text_input("Site I", value=item['site_1'] or '')
                                    e_s2 = st.text_input("Site II", value=item['site_2'] or '')
                                    e_ns = st.text_input("Nº Série", value=item['num_serie'] or '')
                                    e_loc = st.text_input("Local", value=item['local'] or '')
                                    e_elem = st.text_input("Elemento", value=item['elemento'] or '')
                                    e_resp = st.selectbox("Responsável", ["Ark Steel", "Support", "Towertec"])
                                    e_prazo = st.text_input("Prazo", value=item['prazo'])
                                    e_obs = st.text_area("Observações", value=item['observacoes'] or "")
                                    if st.form_submit_button("Salvar"):
                                        editar_torre_completo(id_item, e_ac, e_proj, e_rev, e_tipo, e_fin, e_peso, e_s1, e_s2, e_ns, e_loc, e_elem, e_cli, e_resp, e_prazo, e_obs)
                                        st.rerun()

                        with c_ed2:
                            with st.popover("🗑️ Excluir", use_container_width=True):
                                st.write("Confirmar exclusão?")
                                if st.button("Sim, Excluir", key=f"del_{id_item}"):
                                    excluir_torre(id_item)
                                    st.rerun()

                    else:
                        idx_etapa_coluna = etapas_ordem.index(etapa_coluna)
                        idx_etapa_atual = etapas_ordem.index(etapa_atual) if etapa_atual in etapas_ordem else -1
                        
                        if idx_etapa_coluna < idx_etapa_atual:
                            st.success(f"✓ Concluído ({tempo_str})")
                        else:
                            st.caption("🔒 *Aguardando etapa anterior*")

# 3. DASHBOARDS COMPLETO COM NOVOS GRÁFICOS E FILTROS
with aba_dash:
    st.subheader("📈 Dashboard de Desempenho e Indicadores")
    
    if not df_global.empty:
        with st.expander("🔍 Filtros do Dashboard", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                dash_clientes = st.multiselect("Filtrar por Cliente:", options=df_global['cliente'].dropna().unique(), key="dash_cli")
            with col_f2:
                dash_responsaveis = st.multiselect("Filtrar por Responsável:", options=df_global['responsavel'].dropna().unique(), key="dash_resp")
            with col_f3:
                dash_tipos = st.multiselect("Filtrar por Tipo:", options=df_global['tipo'].dropna().unique(), key="dash_tipo")

        df_dash = df_global.copy()
        if dash_clientes:
            df_dash = df_dash[df_dash['cliente'].isin(dash_clientes)]
        if dash_responsaveis:
            df_dash = df_dash[df_dash['responsavel'].isin(dash_responsaveis)]
        if dash_tipos:
            df_dash = df_dash[df_dash['tipo'].isin(dash_tipos)]

        if not df_dash.empty:
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total de Projetos", len(df_dash))
            with m2:
                st.metric("Em Andamento", len(df_dash[~df_dash['status_projeto'].isin(['Concluído', 'Cancelado'])]))
            with m3:
                st.metric("Concluídos", len(df_dash[df_dash['status_projeto'] == 'Concluído']))
            with m4:
                st.metric("Peso Total", f"{df_dash['peso'].sum():,.1f} kg")

            st.divider()

            g1, g2 = st.columns(2)

            with g1:
                df_status = df_dash['status_projeto'].value_counts().reset_index()
                df_status.columns = ['status_projeto', 'count']
                fig_status = px.bar(
                    df_status,
                    x='status_projeto', y='count',
                    title="📊 Quantidade de Projetos por Etapa",
                    labels={'status_projeto': 'Etapa', 'count': 'Qtd. de Projetos'},
                    text_auto=True,
                    template="plotly_dark",
                    color='status_projeto',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_status.update_layout(showlegend=False)
                st.plotly_chart(fig_status, use_container_width=True)

            with g2:
                avg_proj = (df_dash['tempo_projeto_sec'].fillna(0).mean()) / 3600
                avg_steel = (df_dash['tempo_steel_sec'].fillna(0).mean()) / 3600
                avg_sankhya = (df_dash['tempo_sankhya_sec'].fillna(0).mean()) / 3600

                df_tempo_medio = pd.DataFrame({
                    'Etapa': ['Projeto', 'Steel', 'Sankhya'],
                    'Tempo Médio (Horas)': [round(avg_proj, 2), round(avg_steel, 2), round(avg_sankhya, 2)]
                })

                fig_tempo = px.bar(
                    df_tempo_medio,
                    x='Etapa', y='Tempo Médio (Horas)',
                    title="⏱️ Tempo Médio por Etapa (Horas)",
                    labels={'Tempo Médio (Horas)': 'Média de Horas', 'Etapa': 'Etapa'},
                    text_auto='.2f',
                    template="plotly_dark",
                    color='Etapa',
                    color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b']
                )
                fig_tempo.update_layout(showlegend=False)
                st.plotly_chart(fig_tempo, use_container_width=True)

            st.divider()

            g3, g4 = st.columns(2)

            with g3:
                df_cli = df_dash['cliente'].value_counts().reset_index()
                df_cli.columns = ['cliente', 'count']
                fig_bar = px.bar(
                    df_cli,
                    x='cliente', y='count',
                    title="🏢 Quantidade de Torres por Cliente",
                    labels={'cliente': 'Cliente', 'count': 'Quantidade'},
                    text_auto=True,
                    template="plotly_dark",
                    color_discrete_sequence=['#2563eb']
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with g4:
                df_resp_peso = df_dash.groupby('responsavel')['peso'].sum().reset_index()
                fig_peso = px.pie(
                    df_resp_peso,
                    values='peso', names='responsavel',
                    title="⚖️ Peso Total (kg) por Responsável",
                    hole=0.4,
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig_peso, use_container_width=True)
        else:
            st.warning("Nenhum projeto encontrado com os filtros selecionados.")
    else:
        st.info("Nenhum registro encontrado no banco de dados para o Dashboard.")

# 4. CANCELADOS
with aba_cancelados:
    st.subheader("🚫 Projetos Cancelados")
    df_canc = df_global[df_global["status_projeto"] == "Cancelado"]
    if not df_canc.empty:
        st.dataframe(df_canc, use_container_width=True)
    else:
        st.info("Nenhum projeto cancelado.")

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
                            cursor.execute("INSERT INTO usuarios (username, password_hash, nome) VALUES (?, ?, ?)",
                                           (novo_username, hash_password(nova_senha), novo_nome))
                            conn.commit()
                        st.success(f"Usuário '{novo_username}' cadastrado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erro: Nome de usuário já existe!")

    with col_u2:
        st.markdown("### 📋 Usuários Cadastrados")
        with get_connection() as conn:
            df_users = pd.read_sql("SELECT id, username, nome FROM usuarios", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
