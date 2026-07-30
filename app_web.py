import hashlib
import io
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# ── CONEXÃO COM O SUPABASE (POSTGRESQL) ─────────────────────────────────────
if "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]
else:
    DATABASE_URL = "sqlite:///gestao_torres.db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

TZ_BR = ZoneInfo("America/Sao_Paulo")

def agora_br():
    return datetime.now(TZ_BR)

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Sistema de Controle de Projetos",
    page_icon="📊",
    layout="wide"
)

# 2. CSS CUSTOMIZADO
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

    .kanban-card .stButton > button {
        padding: 2px 6px !important;
        font-size: 12px !important;
        min-height: unset !important;
        line-height: 1 !important;
    }
    .kanban-card .stButton > button:hover {
        background-color: #1d4ed8 !important;
    }

    div[data-testid="stPopover"] {
        max-width: 450px !important;
        max-height: 80vh !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
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

        result_user = conn.execute(text("SELECT COUNT(*) FROM usuarios")).fetchone()[0]
        if result_user == 0:
            conn.execute(
                text("INSERT INTO usuarios (username, password_hash, nome) VALUES (:u, :h, :n)"),
                {"u": "admin", "h": hash_password("admin123"), "n": "Administrador"}
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

# --- FUNÇÕES UTILITÁRIAS (inalteradas) ---
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

def converter_duracao_para_segundos(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return 0
    if isinstance(valor, (int, float)):
        return int(valor)
    match = re.match(r'(\d{1,4}):([0-5]\d):([0-5]\d)', str(valor).strip())
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return h * 3600 + m * 60 + s
    try:
        return int(float(str(valor).replace(',', '.')))
    except:
        return 0

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

def carregar_dados_db():
    return pd.read_sql("SELECT * FROM torres", engine)

def atualizar_df_global():
    st.session_state.df_global = carregar_dados_db()

# ... (todas as ações de relógio, editar, excluir, etc. – mantidas exatamente como no último código)

# ================ SESSÃO PERSISTENTE ================
def set_cookie(nome, valor, dias=30):
    js = f"""
    <script>
        var d = new Date();
        d.setTime(d.getTime() + ({dias} * 24 * 60 * 60 * 1000));
        var expires = "expires="+ d.toUTCString();
        document.cookie = "{nome}=" + "{valor}" + ";" + expires + ";path=/";
    </script>
    """
    st.components.v1.html(js, height=0, width=0)

def get_cookie(nome):
    js = f"""
    <script>
        var name = "{nome}=";
        var decodedCookie = decodeURIComponent(document.cookie);
        var ca = decodedCookie.split(';');
        var valor = "";
        for(var i = 0; i <ca.length; i++) {{
            var c = ca[i];
            while (c.charAt(0) == ' ') {{
                c = c.substring(1);
            }}
            if (c.indexOf(name) == 0) {{
                valor = c.substring(name.length, c.length);
                break;
            }}
        }}
        window.parent.postMessage({{type: "streamlit:setComponentValue", value: valor}}, "*");
    </script>
    """
    cookie = st.components.v1.html(js, height=0, width=0)
    return cookie

def salvar_sessao(usuario_nome, usuario_login):
    st.session_state["autenticado"] = True
    st.session_state["usuario_nome"] = usuario_nome
    st.session_state["usuario_login"] = usuario_login
    dados = json.dumps({"nome": usuario_nome, "login": usuario_login})
    set_cookie("gestao_session", dados, 30)

def restaurar_sessao():
    if "autenticado" in st.session_state and st.session_state["autenticado"]:
        return
    cookie_value = get_cookie("gestao_session")
    if cookie_value:
        try:
            dados = json.loads(cookie_value)
            st.session_state["autenticado"] = True
            st.session_state["usuario_nome"] = dados["nome"]
            st.session_state["usuario_login"] = dados["login"]
        except:
            pass

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""
    st.session_state["usuario_login"] = ""

if not st.session_state["autenticado"]:
    restaurar_sessao()

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
                    salvar_sessao(user_info[0], usuario)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

st.sidebar.markdown(f"👤 **Usuário Logado:**\n### {st.session_state['usuario_nome']}")
st.sidebar.divider()
if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""
    st.session_state["usuario_login"] = ""
    set_cookie("gestao_session", "", -1)
    st.rerun()

# --- DATAFRAME GLOBAL ---
if "df_global" not in st.session_state:
    atualizar_df_global()

df_global = st.session_state.df_global

col_title, col_b1, col_b2 = st.columns([6, 2, 2], vertical_alignment="center")
with col_title:
    st.title("Controle de Projetos")

# --- IMPORTAÇÃO DE PLANILHA (com limpeza forçada da data) ---
with col_b1:
    with st.popover("📥 Importar Planilha", use_container_width=True):
        st.subheader("Carregar Cadastros (.xlsx / .csv)")
        uploaded_file = st.file_uploader("Selecione o arquivo", type=["xlsx", "csv"])
        importar_como_concluido = st.checkbox("✅ Importar todos como Concluídos", value=False)
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

                        if importar_como_concluido:
                            status_import = 'Concluído'
                        else:
                            status_import = obter_valor_coluna(row_dict, ['status_projeto', 'status', 'etapa'], 'Projeto')
                            status_validos = ['Projeto', 'Steel', 'Sankhya', 'Concluído', 'Cancelado']
                            if status_import not in status_validos:
                                status_import = 'Projeto'

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

                        # >>> LIMPEZA DEFINITIVA DA DATA (remove qualquer hora/minuto) <<<
                        data_cad_str = obter_valor_coluna(row_dict, ['data', 'data de cadastro', 'data_cadastro'], "")
                        # Captura apenas a parte da data (YYYY-MM-DD ou DD/MM/YYYY) usando regex
                        match = re.search(r'(\d{2,4}[-/]\d{2,4}[-/]\d{2,4})', data_cad_str)
                        if match:
                            data_limpa = match.group(1)
                            # Substitui barras por hífens para padronizar
                            data_limpa = data_limpa.replace('/', '-')
                            # Tenta converter e formatar como DD/MM/YYYY
                            try:
                                dt_parsed = pd.to_datetime(data_limpa, dayfirst=True, errors='coerce')
                                if pd.notna(dt_parsed):
                                    data_cad = dt_parsed.strftime("%d/%m/%Y")
                                else:
                                    data_cad = agora_br().strftime("%d/%m/%Y")
                            except:
                                data_cad = agora_br().strftime("%d/%m/%Y")
                        else:
                            data_cad = agora_br().strftime("%d/%m/%Y")

                        prazo_str = obter_valor_coluna(row_dict, ['prazo', 'prazo de entrega', 'prazo_entrega'], "")
                        match = re.search(r'(\d{2,4}[-/]\d{2,4}[-/]\d{2,4})', prazo_str)
                        if match:
                            prazo_limpa = match.group(1).replace('/', '-')
                            try:
                                dt_prazo = pd.to_datetime(prazo_limpa, dayfirst=True, errors='coerce')
                                if pd.notna(dt_prazo):
                                    prazo = dt_prazo.strftime("%d/%m/%Y")
                                else:
                                    prazo = (agora_br() + timedelta(days=7)).strftime("%d/%m/%Y")
                            except:
                                prazo = (agora_br() + timedelta(days=7)).strftime("%d/%m/%Y")
                        else:
                            prazo = (agora_br() + timedelta(days=7)).strftime("%d/%m/%Y")

                        t_proj = converter_duracao_para_segundos(
                            obter_valor_coluna(row_dict, ['tempo_projeto', 'tempo projeto', 'tempo_projeto_sec'], '0')
                        )
                        t_steel = converter_duracao_para_segundos(
                            obter_valor_coluna(row_dict, ['tempo_steel', 'tempo steel', 'tempo_steel_sec'], '0')
                        )
                        t_sankhya = converter_duracao_para_segundos(
                            obter_valor_coluna(row_dict, ['tempo_sankhya', 'tempo sankhya', 'tempo_sankhya_sec'], '0')
                        )

                        inicio_proj = obter_valor_coluna(row_dict, ['inicio_projeto', 'fim_projeto_inicio'], '')
                        fim_proj = obter_valor_coluna(row_dict, ['fim_projeto', 'fim projeto'], '')
                        inicio_steel = obter_valor_coluna(row_dict, ['inicio_steel', 'fim_steel_inicio'], '')
                        fim_steel = obter_valor_coluna(row_dict, ['fim_steel', 'fim steel'], '')
                        inicio_sankhya = obter_valor_coluna(row_dict, ['inicio_sankhya', 'fim_sankhya_inicio'], '')
                        fim_sankhya = obter_valor_coluna(row_dict, ['fim_sankhya', 'fim sankhya'], '')

                        observacoes = obter_valor_coluna(row_dict, ['observações', 'observacoes', 'obs'], 'Importado via planilha')

                        conn.execute(text('''
                            INSERT INTO torres (acionamento, projeto, revisao, cliente, tipo, finalidade, peso,
                                                site_1, site_2, num_serie, local, elemento, responsavel, prazo,
                                                data, observacoes, status_projeto,
                                                tempo_projeto_sec, inicio_projeto, fim_projeto,
                                                tempo_steel_sec, inicio_steel, fim_steel,
                                                tempo_sankhya_sec, inicio_sankhya, fim_sankhya)
                            VALUES (:ac, :proj, :rev, :cli, :tipo, :fin, :peso, :s1, :s2, :ns, :loc, :elem, :resp, :prazo, :data, :obs, :status,
                                    :tp, :ip, :fp, :ts, :is, :fs, :tsk, :isk, :fsk)
                        '''), {
                            "ac": acionamento, "proj": projeto, "rev": revisao, "cli": cliente, "tipo": tipo, "fin": finalidade,
                            "peso": peso, "s1": site_1, "s2": site_2, "ns": num_serie, "loc": local, "elem": elemento,
                            "resp": responsavel, "prazo": prazo, "data": data_cad, "obs": observacoes, "status": status_import,
                            "tp": t_proj, "ip": inicio_proj, "fp": fim_proj,
                            "ts": t_steel, "is": inicio_steel, "fs": fim_steel,
                            "tsk": t_sankhya, "isk": inicio_sankhya, "fsk": fim_sankhya
                        })
                        registros_inseridos += 1
                atualizar_df_global()
                st.success(f"{registros_inseridos} registros importados com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao importar: {e}")

# --- CADASTRO EM TRÊS COLUNAS (mantido igual) ---
with col_b2:
    with st.popover("➕ Cadastrar Projeto", use_container_width=True):
        # ... (código do cadastro manual inalterado)
        pass

# ABAS
aba_lista, aba_kanban, aba_dash, aba_finalizados, aba_cancelados, aba_usuarios = st.tabs([
    "📋 Listagem e Tempos", "📊 Kanban Multi-Etapas", "📈 Dashboards",
    "✅ Finalizados", "🚫 Cancelados", "👥 Usuários & Cadastros"
])

# ============ LISTAGEM (com filtro de data) ============
with aba_lista:
    # ... (mesmo código da listagem com filtro de data)
    pass

# ============ KANBAN ============
with aba_kanban:
    # ... (mesmo código do Kanban)
    pass

# ============ DASHBOARD ============
with aba_dash:
    # ... (mesmo código do dashboard)
    pass

# ============ FINALIZADOS / CANCELADOS ============
with aba_finalizados:
    st.subheader("✅ Projetos Finalizados")
    df_fin = df_global[df_global["status_projeto"] == "Concluído"]
    if not df_fin.empty:
        st.dataframe(df_fin, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum projeto finalizado.")

with aba_cancelados:
    st.subheader("🚫 Projetos Cancelados")
    df_canc = df_global[df_global["status_projeto"] == "Cancelado"]
    if not df_canc.empty:
        st.dataframe(df_canc, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum projeto cancelado.")

# ============ USUÁRIOS & CADASTROS (com botão de correção de datas) ============
with aba_usuarios:
    st.subheader("👥 Gerenciamento do Sistema (Usuários, Clientes & Responsáveis)")
    tab_u_sub1, tab_u_sub2, tab_u_sub3, tab_u_sub4 = st.tabs(["👤 Usuários", "🏢 Clientes", "👷 Responsáveis", "🛠️ Ferramentas"])
    
    with tab_u_sub1:
        # ... (cadastro de usuários mantido)
        pass

    with tab_u_sub2:
        # ... (clientes)
        pass

    with tab_u_sub3:
        # ... (responsáveis)
        pass

    with tab_u_sub4:
        st.markdown("### 🧹 Correção de Datas")
        st.warning("Use este botão para converter **todas** as datas que estão no formato ISO (AAAA-MM-DD HH:MM:SS) para DD/MM/YYYY.")
        if st.button("🔄 Corrigir datas do banco", use_container_width=True):
            with engine.begin() as conn:
                # Corrige campo 'data'
                conn.execute(text("""
                    UPDATE torres
                    SET data = TO_CHAR(data::date, 'DD/MM/YYYY')
                    WHERE data ~ '^\d{4}-\d{2}-\d{2}'
                """))
                # Corrige campo 'prazo' (se aplicável)
                conn.execute(text("""
                    UPDATE torres
                    SET prazo = TO_CHAR(prazo::date, 'DD/MM/YYYY')
                    WHERE prazo ~ '^\d{4}-\d{2}-\d{2}'
                """))
                # Corrige datas de início/fim se existirem
                for col in ['inicio_projeto', 'fim_projeto', 'inicio_steel', 'fim_steel', 'inicio_sankhya', 'fim_sankhya']:
                    conn.execute(text(f"""
                        UPDATE torres
                        SET {col} = TO_CHAR({col}::date, 'DD/MM/YYYY')
                        WHERE {col} ~ '^\d{{4}}-\d{{2}}-\d{{2}}'
                    """))
            atualizar_df_global()
            st.success("Datas corrigidas com sucesso! Recarregue a página se necessário.")
            st.rerun()

        st.markdown("---")
        st.markdown("Após corrigir, **todas as datas** exibirão apenas o dia/mês/ano. Novas importações já são gravadas corretamente.")
