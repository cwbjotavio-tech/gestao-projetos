import hashlib
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# Lê a URL do Supabase configurada nos Secrets do Streamlit Cloud
if "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]
else:
    # Fallback opcional caso queira testar localmente sem secrets
    DATABASE_URL = "sqlite:///gestao_torres.db"

# Cria o engine do SQLAlchemy compatível com PostgreSQL e o Supabase
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Fuso horário do Brasil
TZ_BR = ZoneInfo("America/Sao_Paulo")

def agora_br():
    return datetime.now(TZ_BR)

# 1. Configuração da Página
st.set_page_config(
    page_title="Sistema de Controle de Projetos",
    page_icon="📊",
    layout="wide"
)

# 2. CSS Customizado
st.markdown("""
    <style>
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        font-family: 'Inter', sans-serif;
    }
    
    h1 {
        font-size: 1.8rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        font-weight: 700 !important;
    }

    h2, h3, h4, h5, h6 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.5rem !important;
    }

    label, p, span, div, .stMarkdown {
        color: #f8fafc !important;
    }

    .stTabs {
        margin-top: 0.5rem !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #1e293b !important;
        padding: 4px;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

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

    .stButton > button, div[data-testid="stPopover"] > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
        font-size: 13px !important;
    }
    .stButton > button:hover, div[data-testid="stPopover"] > button:hover {
        background-color: #1d4ed8 !important;
    }

    [data-testid="stDataFrame"] {
        background-color: #1e293b !important;
        border-radius: 8px;
        border: 1px solid #334155;
    }

    [data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        padding: 10px !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS E SEGURANÇA ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS responsaveis (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS torres (
                id SERIAL PRIMARY KEY,
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
        '''))
        
        # Seeds padrão se tabelas estiverem vazias
        result_user = conn.execute(text("SELECT COUNT(*) FROM usuarios")).fetchone()[0]
        if result_user == 0:
            conn.execute(
                text("INSERT INTO usuarios (username, password_hash, nome) VALUES (:username, :password_hash, :nome)"),
                {"username": "admin", "password_hash": hash_password("admin123"), "nome": "Administrador"}
            )
        
        result_cli = conn.execute(text("SELECT COUNT(*) FROM clientes")).fetchone()[0]
        if result_cli == 0:
            for cli in ["BTC", "Del Infra", "Phoenix", "Global", "Reflay", "Winity", "Nexus", "Centennial"]:
                conn.execute(
                    text("INSERT INTO clientes (nome) VALUES (:nome) ON CONFLICT (nome) DO NOTHING"),
                    {"nome": cli}
                )

        result_resp = conn.execute(text("SELECT COUNT(*) FROM responsaveis")).fetchone()[0]
        if result_resp == 0:
            for resp in ["Ark Steel", "Support", "Towertec"]:
                conn.execute(
                    text("INSERT INTO responsaveis (nome) VALUES (:nome) ON CONFLICT (nome) DO NOTHING"),
                    {"nome": resp}
                )

init_db()

# --- FUNÇÕES UTILITÁRIAS ---
def obter_locais_cadastrados():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT local FROM torres WHERE local IS NOT NULL AND local != '' ORDER BY local"))
        return [row[0] for row in result.fetchall()]

def obter_elementos_cadastrados():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT elemento FROM torres WHERE elemento IS NOT NULL AND elemento != '' ORDER BY elemento"))
        return [row[0] for row in result.fetchall()]

def obter_clientes():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT nome FROM clientes ORDER BY nome"))
        return [row[0] for row in result.fetchall()]

def obter_responsaveis():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT nome FROM responsaveis ORDER BY nome"))
        return [row[0] for row in result.fetchall()]

def classificar_situacao(row):
    if row['status_projeto'] == 'Concluído':
        return 'Finalizado'
    elif row['status_projeto'] == 'Cancelado':
        return 'Cancelado'
    elif row['estado_relogio'] == 'parado':
        return 'Parados'
    else:
        return 'Em Progresso'

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
            if dt_inicio.tzinfo is None:
                dt_inicio = dt_inicio.replace(tzinfo=TZ_BR)
            sec += max(0, int((agora_br() - dt_inicio).total_seconds()))
        except Exception:
            pass
    return sec

def obter_valor_coluna(row_dict, nomes_possiveis, padrao=""):
    row_norm = {str(k).strip().lower(): v for k, v in row_dict.items()}
    for nome in nomes_possiveis:
        nome_norm = nome.strip().lower()
        if nome_norm in row_norm:
            val = row_norm[nome_norm]
            if pd.notna(val) and str(val).strip() != "" and str(val).lower() != "nan":
                return str(val).strip()
    return padrao

def acao_iniciar_relogio(torre_id, etapa_key):
    now_br = agora_br()
    now_iso = now_br.isoformat()
    now_str = now_br.strftime("%d/%m/%Y %H:%M")
    with engine.begin() as conn:
        res = conn.execute(text(f"SELECT inicio_{etapa_key} FROM torres WHERE id=:id"), {"id": torre_id}).fetchone()
        if not res or not res[0]:
            conn.execute(text(f"UPDATE torres SET inicio_{etapa_key}=:val WHERE id=:id"), {"val": now_str, "id": torre_id})
        conn.execute(text("UPDATE torres SET estado_relogio='rodando', timestamp_ultimo_inicio=:ts WHERE id=:id"), {"ts": now_iso, "id": torre_id})
    st.cache_data.clear()

def acao_pausar_relogio(torre_id, etapa_key):
    now_br = agora_br()
    with engine.begin() as conn:
        res = conn.execute(text(f"SELECT tempo_{etapa_key}_sec, timestamp_ultimo_inicio FROM torres WHERE id=:id"), {"id": torre_id}).fetchone()
        if res and res[1]:
            try:
                dt_inicio = datetime.fromisoformat(res[1])
                if dt_inicio.tzinfo is None:
                    dt_inicio = dt_inicio.replace(tzinfo=TZ_BR)
                elapsed = max(0, int((now_br - dt_inicio).total_seconds()))
            except Exception:
                elapsed = 0
            novo_tempo = (res[0] or 0) + elapsed
            conn.execute(
                text(f"UPDATE torres SET tempo_{etapa_key}_sec=:tempo, estado_relogio='parado', timestamp_ultimo_inicio='' WHERE id=:id"),
                {"tempo": novo_tempo, "id": torre_id}
            )
    st.cache_data.clear()

def acao_finalizar_etapa(torre_id, etapa_atual, proxima_etapa):
    etapa_key = etapa_atual.lower()
    now_br = agora_br()
    now_str = now_br.strftime("%d/%m/%Y %H:%M")
    with engine.begin() as conn:
        res = conn.execute(text(f"SELECT tempo_{etapa_key}_sec, timestamp_ultimo_inicio, estado_relogio FROM torres WHERE id=:id"), {"id": torre_id}).fetchone()
        novo_tempo = res[0] or 0 if res else 0
        
        if res and res[2] == 'rodando' and res[1]:
            try:
                dt_inicio = datetime.fromisoformat(res[1])
                if dt_inicio.tzinfo is None:
                    dt_inicio = dt_inicio.replace(tzinfo=TZ_BR)
                novo_tempo += max(0, int((now_br - dt_inicio).total_seconds()))
            except Exception:
                pass
        
        conn.execute(text(f'''
            UPDATE torres SET 
                tempo_{etapa_key}=:tempo, 
                fim_{etapa_key}=:fim, 
                estado_relogio='parado', 
                timestamp_ultimo_inicio='',
                status_projeto=:status
            WHERE id=:id
        '''.replace(f"tempo_{etapa_key}", f"tempo_{etapa_key}_sec")), {
            "tempo": novo_tempo,
            "fim": now_str,
            "status": proxima_etapa,
            "id": torre_id
        })
    st.cache_data.clear()

def acao_retroceder_etapa(torre_id, etapa_atual):
    anterior_map = {
        "Steel": "Projeto",
        "Sankhya": "Steel",
        "Concluído": "Sankhya",
        "Cancelado": "Sankhya"
    }
    if etapa_atual not in anterior_map:
        return
    etapa_anterior = anterior_map[etapa_atual]
    etapa_anterior_key = etapa_anterior.lower()
    with engine.begin() as conn:
        conn.execute(text(f'''
            UPDATE torres SET 
                status_projeto=:status, 
                fim_{etapa_anterior_key}='',
                estado_relogio='parado',
                timestamp_ultimo_inicio=''
            WHERE id=:id
        '''), {"status": etapa_anterior, "id": torre_id})
    st.cache_data.clear()

def acao_cancelar_projeto(torre_id, etapa_atual):
    etapa_key = etapa_atual.lower() if etapa_atual.lower() in ['projeto', 'steel', 'sankhya'] else 'projeto'
    now_br = agora_br()
    with engine.begin() as conn:
        res = conn.execute(text(f"SELECT tempo_{etapa_key}_sec, timestamp_ultimo_inicio, estado_relogio FROM torres WHERE id=:id"), {"id": torre_id}).fetchone()
        novo_tempo = res[0] or 0 if res else 0
        
        if res and res[2] == 'rodando' and res[1]:
            try:
                dt_inicio = datetime.fromisoformat(res[1])
                if dt_inicio.tzinfo is None:
                    dt_inicio = dt_inicio.replace(tzinfo=TZ_BR)
                novo_tempo += max(0, int((now_br - dt_inicio).total_seconds()))
            except Exception:
                pass
        
        conn.execute(text(f'''
            UPDATE torres SET 
                tempo_{etapa_key}_sec=:tempo, 
                estado_relogio='parado', 
                timestamp_ultimo_inicio='',
                status_projeto='Cancelado'
            WHERE id=:id
        '''), {"tempo": novo_tempo, "id": torre_id})
    st.cache_data.clear()

def excluir_torre(torre_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM torres WHERE id=:id"), {"id": torre_id})
    st.cache_data.clear()

def editar_torre_completo(torre_id, acionamento, projeto, revisao, tipo, finalidade, peso, site_1, site_2, num_serie, local, elemento, cliente, responsavel, data_cad, prazo, observacoes):
    with engine.begin() as conn:
        conn.execute(text('''
            UPDATE torres SET 
                acionamento=:acionamento, projeto=:projeto, revisao=:revisao, tipo=:tipo, finalidade=:finalidade, peso=:peso, 
                site_1=:site_1, site_2=:site_2, num_serie=:num_serie, local=:local, elemento=:elemento, cliente=:cliente, 
                responsavel=:responsavel, data=:data, prazo=:prazo, observacoes=:observacoes
            WHERE id=:id
        '''), {
            "acionamento": acionamento, "projeto": projeto, "revisao": revisao, "tipo": tipo, 
            "finalidade": finalidade, "peso": peso, "site_1": site_1, "site_2": site_2, 
            "num_serie": num_serie, "local": local, "elemento": elemento, "cliente": cliente, 
            "responsavel": responsavel, "data": data_cad, "prazo": prazo, "observacoes": observacoes, "id": torre_id
        })
    st.cache_data.clear()

def autenticar_usuario(username, password):
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT nome FROM usuarios WHERE username = :username AND password_hash = :hash"),
            {"username": username, "hash": hash_password(password)}
        ).fetchone()
        return res

@st.cache_data(ttl=3)
def carregar_dados():
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM torres", conn)

# --- TELA DE LOGIN E SESSÃO ---
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

col_title, col_b1, col_b2 = st.columns([6, 2, 2], vertical_alignment="center")

with col_title:
    st.title("Controle de Projetos")

# --- IMPORTAÇÃO DE PLANILHA ---
with col_b1:
    with st.popover("📥 Importar Planilha", use_container_width=True):
        st.subheader("Carregar Cadastros (.xlsx / .csv)")
        uploaded_file = st.file_uploader("Selecione o arquivo", type=["xlsx", "csv"])
        if uploaded_file and st.button("Confirmar Importação"):
            try:
                df_imp = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                
                registros_inseridos = 0
                with engine.begin() as conn:
                    for _, row in df_imp.iterrows():
                        row_dict = row.to_dict()
                        
                        acionamento = obter_valor_coluna(row_dict, ['acionamento', 'acionamento*'])
                        projeto = obter_valor_coluna(row_dict, ['projeto', 'projeto*'])
                        
                        if not acionamento and not projeto:
                            continue

                        revisao = obter_valor_coluna(row_dict, ['revisão', 'revisao', 'rev'], '00')
                        cliente = obter_valor_coluna(row_dict, ['cliente'], 'BTC')
                        tipo = obter_valor_coluna(row_dict, ['tipo'], 'Torre')
                        finalidade = obter_valor_coluna(row_dict, ['finalidade'], 'Fabricação')
                        
                        peso_raw = obter_valor_coluna(row_dict, ['peso (kg)', 'peso', 'peso_kg'], '0')
                        try:
                            peso = float(str(peso_raw).replace(',', '.'))
                        except ValueError:
                            peso = 0.0

                        site_1 = obter_valor_coluna(row_dict, ['site i', 'site 1', 'site_1', 'site1'])
                        site_2 = obter_valor_coluna(row_dict, ['site ii', 'site 2', 'site_2', 'site2'])
                        num_serie = obter_valor_coluna(row_dict, ['nº. série', 'nº série', 'num serie', 'num_serie', 'série', 'serie'])
                        local = obter_valor_coluna(row_dict, ['local'])
                        elemento = obter_valor_coluna(row_dict, ['elemento'])
                        responsavel = obter_valor_coluna(row_dict, ['responsável', 'responsavel'], 'Support')
                        prazo = obter_valor_coluna(row_dict, ['prazo'], (agora_br() + timedelta(days=7)).strftime("%d/%m/%Y"))
                        observacoes = obter_valor_coluna(row_dict, ['observações', 'observacoes', 'obs'], 'Importado via planilha')

                        conn.execute(text('''
                            INSERT INTO torres (
                                acionamento, projeto, revisao, cliente, tipo, finalidade, peso,
                                site_1, site_2, num_serie, local, elemento, responsavel, prazo,
                                data, observacoes, status_projeto
                            )
                            VALUES (:ac, :proj, :rev, :cli, :tipo, :fin, :peso, :s1, :s2, :ns, :loc, :elem, :resp, :prazo, :data, :obs, 'Projeto')
                        '''), {
                            "ac": acionamento, "proj": projeto, "rev": revisao, "cli": cliente, "tipo": tipo, "fin": finalidade, "peso": peso,
                            "s1": site_1, "s2": site_2, "ns": num_serie, "loc": local, "elem": elemento, "resp": responsavel, "prazo": prazo,
                            "data": agora_br().strftime("%d/%m/%Y"), "obs": observacoes
                        })
                        registros_inseridos += 1

                st.cache_data.clear()
                st.success(f"{registros_inseridos} registros importados com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao importar: {e}")

# --- CADASTRO EM TRÊS COLUNAS ---
with col_b2:
    with st.popover("➕ Cadastrar Projeto", use_container_width=True):
        st.subheader("Novo Cadastro")
        locais_cadastrados = obter_locais_cadastrados()
        elementos_cadastrados = obter_elementos_cadastrados()
        lista_clientes = obter_clientes()
        lista_responsaveis = obter_responsaveis()
        
        with st.form("form_nova_torre", clear_on_submit=True):
            col_fc1, col_fc2, col_fc3 = st.columns(3)
            with col_fc1:
                f_acionamento = st.text_input("Acionamento *")
                f_projeto = st.text_input("Projeto *")
                f_revisao = st.text_input("Revisão", value="00")
                f_cliente = st.selectbox("Cliente", options=lista_clientes if lista_clientes else ["BTC"])
                f_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])

            with col_fc2:
                f_finalidade = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo", "Cálculo"])
                f_peso = st.number_input("Peso (kg)", min_value=0.0, step=50.0)
                f_site1 = st.text_input("Site I")
                f_site2 = st.text_input("Site II")
                f_num_serie = st.text_input("Nº Série")

            with col_fc3:
                f_local_existente = st.selectbox("Local / Cidade (Padrão)", options=[""] + locais_cadastrados)
                f_local_novo = st.text_input("Ou digite um novo Local")
                
                f_elemento_existente = st.selectbox("Elemento (Padrão)", options=[""] + elementos_cadastrados)
                f_elemento_novo = st.text_input("Ou digite um novo Elemento")
                
                f_responsavel = st.selectbox("Responsável", options=lista_responsaveis if lista_responsaveis else ["Support"])
                f_data_cad = st.date_input("Data de Cadastro", value=agora_br().date())
                f_prazo = st.date_input("Prazo de Entrega", value=agora_br() + timedelta(days=7))

            f_observacoes = st.text_area("Observações")

            if st.form_submit_button("Salvar Registro", use_container_width=True):
                f_local_final = f_local_novo.strip() if f_local_novo.strip() else f_local_existente
                f_elemento_final = f_elemento_novo.strip() if f_elemento_novo.strip() else f_elemento_existente
                if f_acionamento and f_projeto:
                    with engine.begin() as conn:
                        conn.execute(text('''
                            INSERT INTO torres (acionamento, projeto, revisao, cliente, tipo, finalidade, peso, site_1, site_2, num_serie, local, elemento, responsavel, prazo, data, observacoes, status_projeto)
                            VALUES (:ac, :proj, :rev, :cli, :tipo, :fin, :peso, :s1, :s2, :ns, :loc, :elem, :resp, :prazo, :data, :obs, 'Projeto')
                        '''), {
                            "ac": f_acionamento, "proj": f_projeto, "rev": f_revisao, "cli": f_cliente, "tipo": f_tipo, 
                            "fin": f_finalidade, "peso": f_peso, "s1": f_site1, "s2": f_site2, "ns": f_num_serie, 
                            "loc": f_local_final, "elem": f_elemento_final, "resp": f_responsavel, 
                            "prazo": f_prazo.strftime("%d/%m/%Y"), "data": f_data_cad.strftime("%d/%m/%Y"), "obs": f_observacoes
                        })
                    st.cache_data.clear()
                    st.success("Projeto cadastrado!")
                    st.rerun()

# ABAS DA APLICAÇÃO
aba_lista, aba_kanban, aba_dash, aba_finalizados, aba_cancelados, aba_usuarios = st.tabs([
    "📋 Listagem e Tempos", 
    "📊 Kanban Multi-Etapas", 
    "📈 Dashboards", 
    "✅ Finalizados",
    "🚫 Cancelados",
    "👥 Usuários & Cadastros"
])

# 1. LISTAGEM
with aba_lista:
    st.subheader("Filtros e Relatório Completo")
    c1, c2, c3 = st.columns(3)
    with c1:
        busca_texto = st.text_input("🔎 Pesquisa rápida", placeholder="Buscar por projeto, acionamento...", key="pesquisa_rapida_lista")
    with c2:
        filtro_status = st.multiselect("Etapa (Status)", options=df_global["status_projeto"].dropna().unique() if not df_global.empty else [])
    with c3:
        filtro_situacao = st.multiselect("Situação do Projeto", options=["Em Progresso", "Parados", "Finalizado", "Cancelado"])

    df_view = df_global.copy()

    if not df_view.empty:
        df_view['situacao_filtro'] = df_view.apply(classificar_situacao, axis=1)

    if busca_texto and not df_view.empty:
        df_view = df_view[df_view.astype(str).apply(lambda row: row.str.contains(busca_texto, case=False).any(), axis=1)]
    if filtro_status and not df_view.empty:
        df_view = df_view[df_view["status_projeto"].isin(filtro_status)]
    if filtro_situacao and not df_view.empty:
        df_view = df_view[df_view["situacao_filtro"].isin(filtro_situacao)]

    if not df_view.empty:
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
        df_view['Situação'] = df_view['situacao_filtro']
        
        df_view['Progresso (%)'] = df_view['status_projeto'].map({
            'Projeto': '25%', 'Steel': '50%', 'Sankhya': '75%', 'Concluído': '100%', 'Cancelado': '0%'
        }).fillna('0%')
        
        df_view['Status Geral'] = df_view['estado_relogio'].map({
            'rodando': '🟢 Em Execução', 'parado': '🔴 Pausado'
        }).fillna('🔴 Pausado')
        
        df_view['Data de Cadastro'] = df_view['data'].apply(lambda x: x if x else '-')
        df_view['Fim Projeto'] = df_view['fim_projeto'].apply(lambda x: x if x else '-')
        df_view['Fim Steel'] = df_view['fim_steel'].apply(lambda x: x if x else '-')
        df_view['Fim Sankhya'] = df_view['fim_sankhya'].apply(lambda x: x if x else '-')
        
        df_view['Tempo Projeto'] = df_view.apply(lambda row: formatar_segundos(obter_tempo_decorrido_etapa(row, 'projeto')), axis=1)
        df_view['Tempo Steel'] = df_view.apply(lambda row: formatar_segundos(obter_tempo_decorrido_etapa(row, 'steel')), axis=1)
        df_view['Tempo Sankhya'] = df_view.apply(lambda row: formatar_segundos(obter_tempo_decorrido_etapa(row, 'sankhya')), axis=1)

        cols_display = [
            'ID', 'Acionamento', 'Projeto', 'Revisão', 'Tipo', 'Finalidade', 'Peso (kg)',
            'Site I', 'Site II', 'Nº. Série', 'Local', 'Elemento', 'Cliente', 'Responsável',
            'Data', 'Prazo', 'Etapa', 'Situação', 'Progresso (%)', 'Status Geral', 'Data de Cadastro',
            'Fim Projeto', 'Fim Steel', 'Fim Sankhya', 'Tempo Projeto', 'Tempo Steel',
            'Tempo Sankhya'
        ]
        
        st.dataframe(df_view[cols_display], use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("⚡ Ações na Listagem (Editar / Excluir / Salvar)")
        col_sel, col_act1, col_act2 = st.columns([3, 1, 1])

        opcoes_torres = {f"#{row['id']} - {row['projeto']} ({row['cliente']})": row['id'] for _, row in df_view.iterrows()}
        
        with col_sel:
            torre_selecionada_label = st.selectbox("Selecione um projeto para modificar:", list(opcoes_torres.keys()))
            id_selecionado = opcoes_torres[torre_selecionada_label]
            item_sel = df_view[df_view['id'] == id_selecionado].iloc[0]

        with col_act1:
            with st.popover("✏️ Editar Projeto", use_container_width=True):
                st.write(f"**Editando ID #{id_selecionado}**")
                locais_cadastrados_edit = obter_locais_cadastrados()
                elementos_cadastrados_edit = obter_elementos_cadastrados()
                cli_edit = obter_clientes()
                resp_edit = obter_responsaveis()
                
                with st.form(key=f"form_edit_list_{id_selecionado}"):
                    e_ac = st.text_input("Acionamento", value=str(item_sel['Acionamento']))
                    e_proj = st.text_input("Projeto", value=str(item_sel['Projeto']))
                    e_rev = st.text_input("Revisão", value=str(item_sel['Revisão'] or '00'))
                    e_cli = st.selectbox("Cliente", options=cli_edit, index=cli_edit.index(item_sel['Cliente']) if item_sel['Cliente'] in cli_edit else 0)
                    e_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"], index=["Torre", "Rooftop", "Item para site", "Projeto interno"].index(str(item_sel['Tipo'])) if str(item_sel['Tipo']) in ["Torre", "Rooftop", "Item para site", "Projeto interno"] else 0)
                    e_fin = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo", "Cálculo"], index=["Fabricação", "Estimativa de Custo", "Cálculo"].index(str(item_sel['Finalidade'])) if str(item_sel['Finalidade']) in ["Fabricação", "Estimativa de Custo", "Cálculo"] else 0)
                    e_peso = st.number_input("Peso (kg)", value=float(item_sel['Peso (kg)']))
                    e_s1 = st.text_input("Site I", value=str(item_sel['Site I'] or ''))
                    e_s2 = st.text_input("Site II", value=str(item_sel['Site II'] or ''))
                    e_ns = st.text_input("Nº Série", value=str(item_sel['Nº. Série'] or ''))
                    
                    e_loc_atual = str(item_sel['Local'] or '')
                    idx_loc = locais_cadastrados_edit.index(e_loc_atual) + 1 if e_loc_atual in locais_cadastrados_edit else 0
                    e_loc_existente = st.selectbox("Local / Cidade (Padrão)", options=[""] + locais_cadastrados_edit, index=idx_loc)
                    e_loc_novo = st.text_input("Ou digite um novo Local", value="" if idx_loc > 0 else e_loc_atual)

                    e_elem_atual = str(item_sel['Elemento'] or '')
                    idx_elem = elementos_cadastrados_edit.index(e_elem_atual) + 1 if e_elem_atual in elementos_cadastrados_edit else 0
                    e_elem_existente = st.selectbox("Elemento (Padrão)", options=[""] + elementos_cadastrados_edit, index=idx_elem)
                    e_elem_novo = st.text_input("Ou digite um novo Elemento", value="" if idx_elem > 0 else e_elem_atual)

                    e_resp = st.selectbox("Responsável", options=resp_edit, index=resp_edit.index(item_sel['Responsável']) if item_sel['Responsável'] in resp_edit else 0)
                    
                    try:
                        dt_parsed = datetime.strptime(str(item_sel['Data']), "%d/%m/%Y").date()
                    except:
                        dt_parsed = agora_br().date()
                    e_data = st.date_input("Data de Cadastro", value=dt_parsed)
                    e_prazo = st.text_input("Prazo", value=str(item_sel['Prazo']))
                    e_obs = st.text_area("Observações", value=str(df_global[df_global['id'] == id_selecionado]['observacoes'].values[0] if 'observacoes' in df_global.columns else ''))

                    if st.form_submit_button("Salvar Alterações", use_container_width=True):
                        f_loc_final = e_loc_novo.strip() if e_loc_novo.strip() else e_loc_existente
                        f_elem_final = e_elem_novo.strip() if e_elem_novo.strip() else e_elem_existente
                        editar_torre_completo(id_selecionado, e_ac, e_proj, e_rev, e_tipo, e_fin, e_peso, e_s1, e_s2, e_ns, f_loc_final, f_elem_final, e_cli, e_resp, e_data.strftime("%d/%m/%Y"), e_prazo, e_obs)
                        st.success("Alterações salvas com sucesso!")
                        st.rerun()

        with col_act2:
            if st.button("🗑️ Excluir Projeto", use_container_width=True):
                excluir_torre(id_selecionado)
                st.success(f"Projeto #{id_selecionado} excluído!")
                st.rerun()

# 2. KANBAN MULTI-ETAPAS
with aba_kanban:
    st.subheader("Kanban Operacional de Etapas")
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    etapas = [
        ("Projeto", col_k1),
        ("Steel", col_k2),
        ("Sankhya", col_k3),
        ("Concluído", col_k4)
    ]
    
    for nome_etapa, coluna in etapas:
        with coluna:
            st.markdown(f"### 📌 {nome_etapa}")
            if not df_global.empty:
                itens_etapa = df_global[df_global['status_projeto'] == nome_etapa]
                for _, item in itens_etapa.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**#{item['id']} - {item['projeto']}**")
                        st.caption(f"Cliente: {item['cliente']} | Resp: {item['responsavel']}")
                        
                        etapa_key = nome_etapa.lower()
                        if etapa_key in ['projeto', 'steel', 'sankhya']:
                            seg = obter_tempo_decorrido_etapa(item, etapa_key)
                            st.text(f"⏱️ Tempo: {formatar_segundos(seg)}")
                            
                            is_running = (item['estado_relogio'] == 'rodando')
                            c_b1, c_b2 = st.columns(2)
                            with c_b1:
                                if not is_running:
                                    if st.button("▶️", key=f"play_{item['id']}_{nome_etapa}", help="Iniciar Cronômetro"):
                                        acao_iniciar_relogio(item['id'], etapa_key)
                                        st.rerun()
                                else:
                                    if st.button("⏸️", key=f"pause_{item['id']}_{nome_etapa}", help="Pausar Cronômetro"):
                                        acao_pausar_relogio(item['id'], etapa_key)
                                        st.rerun()
                            with c_b2:
                                proxima_map = {"Projeto": "Steel", "Steel": "Sankhya", "Sankhya": "Concluído"}
                                if nome_etapa in proxima_map:
                                    if st.button("✔ Avançar", key=f"av_{item['id']}_{nome_etapa}"):
                                        acao_finalizar_etapa(item['id'], nome_etapa, proxima_map[nome_etapa])
                                        st.rerun()
                            
                            if nome_etapa != "Projeto":
                                if st.button("⬅️ Voltar Etapa", key=f"back_{item['id']}_{nome_etapa}"):
                                    acao_retroceder_etapa(item['id'], nome_etapa)
                                    st.rerun()

                            if st.button("🚫 Cancelar", key=f"cancel_{item['id']}_{nome_etapa}"):
                                acao_cancelar_projeto(item['id'], nome_etapa)
                                st.rerun()

# 3. DASHBOARDS
with aba_dash:
    st.subheader("Indicadores e Métricas de Desempenho")
    if not df_global.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Projetos", len(df_global))
        m2.metric("Em Andamento", len(df_global[df_global['status_projeto'].isin(['Projeto', 'Steel', 'Sankhya'])]))
        m3.metric("Concluídos", len(df_global[df_global['status_projeto'] == 'Concluído']))
        m4.metric("Cancelados", len(df_global[df_global['status_projeto'] == 'Cancelado']))

        st.divider()
        c_ch1, c_ch2 = st.columns(2)
        with c_ch1:
            fig_cli = px.pie(df_global, names='cliente', title="Projetos por Cliente", hole=0.4)
            fig_cli.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", font_color="#f8fafc")
            st.plotly_chart(fig_cli, use_container_width=True)
        with c_ch2:
            fig_status = px.bar(df_global['status_projeto'].value_counts().reset_index(), x='status_projeto', y='count', title="Distribuição por Etapa", labels={'status_projeto': 'Etapa', 'count': 'Quantidade'})
            fig_status.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", font_color="#f8fafc")
            st.plotly_chart(fig_status, use_container_width=True)

# 4. FINALIZADOS
with aba_finalizados:
    st.subheader("Projetos Concluídos com Sucesso")
    if not df_global.empty:
        df_fin = df_global[df_global['status_projeto'] == 'Concluído']
        if not df_fin.empty:
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum projeto finalizado até o momento.")

# 5. CANCELADOS
with aba_cancelados:
    st.subheader("Projetos Cancelados")
    if not df_global.empty:
        df_canc = df_global[df_global['status_projeto'] == 'Cancelado']
        if not df_canc.empty:
            st.dataframe(df_canc, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum projeto cancelado.")

# 6. USUÁRIOS & CADASTROS
with aba_usuarios:
    st.subheader("Gerenciamento de Clientes, Responsáveis e Usuários")
    uc1, uc2, uc3 = st.columns(3)
    
    with uc1:
        st.markdown("### 🏢 Clientes")
        lista_c = obter_clientes()
        for c in lista_c:
            st.text(f"• {c}")
        with st.form("form_novo_cli"):
            novo_c = st.text_input("Adicionar Cliente")
            if st.form_submit_button("Cadastrar Cliente"):
                if novo_c:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO clientes (nome) VALUES (:nome) ON CONFLICT (nome) DO NOTHING"), {"nome": novo_c})
                    st.success("Cliente adicionado!")
                    st.rerun()

    with uc2:
        st.markdown("### 👷 Responsáveis")
        lista_r = obter_responsaveis()
        for r in lista_r:
            st.text(f"• {r}")
        with st.form("form_novo_resp"):
            novo_r = st.text_input("Adicionar Responsável")
            if st.form_submit_button("Cadastrar Responsável"):
                if novo_r:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO responsaveis (nome) VALUES (:nome) ON CONFLICT (nome) DO NOTHING"), {"nome": novo_r})
                    st.success("Responsável adicionado!")
                    st.rerun()

    with uc3:
        st.markdown("### 🔐 Usuários do Sistema")
        with engine.connect() as conn:
            df_users = pd.read_sql("SELECT username, nome FROM usuarios", conn)
        st.dataframe(df_users, hide_index=True, use_container_width=True)
        
        with st.form("form_novo_usuario"):
            u_login = st.text_input("Novo Username")
            u_nome = st.text_input("Nome Completo")
            u_senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Criar Usuário"):
                if u_login and u_senha and u_nome:
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO usuarios (username, password_hash, nome) VALUES (:u, :h, :n)"),
                            {"u": u_login, "h": hash_password(u_senha), "n": u_nome}
                        )
                    st.success("Usuário criado!")
                    st.rerun()

#apagar daqui pa baixo
import hashlib
from sqlalchemy import create_engine, text

# Substitua pela sua string de conexão real do PostgreSQL (ou use st.secrets["database"]["url"])
DATABASE_URL = "postgresql://postgres:[SUA_SENHA]@[SEU_HOST]:5432/postgres"
engine = create_engine(DATABASE_URL)

def hash_password(password):
    # Altere esta função caso o seu projeto utilize outro método (ex: bcrypt)
    return hashlib.sha256(password.encode()).hexdigest()

def criar_usuario_admin():
    username = "admin"
    senha_pura = "admin123"
    nome = "Administrador"
    
    # Gera o hash da senha
    senha_hash = hash_password(senha_pura)
    
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO public.usuarios (username, password_hash, nome) 
                VALUES (:username, :password_hash, :nome)
                ON CONFLICT (username) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash;
            """),
            {
                "username": username,
                "password_hash": senha_hash,
                "nome": nome
            }
        )
    print(f"Usuário '{username}' cadastrado/atualizado com sucesso!")

if __name__ == "__main__":
    criar_usuario_admin()
