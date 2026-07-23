import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# Configuração da página para ocupar a largura inteira
st.set_page_config(page_title="Gestão de Projetos e Engenharia", layout="wide")

# Conexão com o Banco de Dados SQLite
def conectar_banco():
    conn = sqlite3.connect('sistema_projetos.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            serie TEXT PRIMARY KEY,
            acionamento TEXT,
            site_i TEXT,
            site_ii TEXT,
            codigo TEXT,
            descricao TEXT,
            local TEXT,
            fornecedor TEXT,
            cliente TEXT,
            prazo TEXT,
            conclusao TEXT,
            data_op TEXT,
            tipo TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = conectar_banco()

st.title("📊 Gestão de Projetos e Engenharia")

# Abas na Web
aba1, aba2, aba3 = st.tabs(["Quadro Principal", "Cadastrar / Importar Lote", "Etapas e Status"])

with aba1:
    st.subheader("Quadro de Projetos")
    
    # Campo de Pesquisa Geral
    pesquisa = st.text_input("🔍 Pesquisar no quadro:", "")
    
    # Buscar dados do banco
    df = pd.read_sql("SELECT * FROM projetos", conn)
    
    if not df.empty:
        # Renomear colunas para exibição amigável
        colunas_map = {
            'serie': 'Cód. Série',
            'acionamento': 'Acionamento',
            'site_i': 'Site I',
            'site_ii': 'Site II',
            'codigo': 'Código',
            'descricao': 'Descrição',
            'local': 'Local',
            'fornecedor': 'Fornecedor',
            'cliente': 'Cliente',
            'prazo': 'Prazo',
            'conclusao': 'Conclusão',
            'data_op': 'Data O.P.',
            'tipo': 'Tipo',
            'status': 'Status'
        }
        df_exibicao = df.rename(columns=colunas_map)
        
        # Filtrar dados se houver pesquisa
        if pesquisa:
            filtro = df_exibicao.astype(str).apply(lambda x: x.str.contains(pesquisa, case=False)).any(axis=1)
            df_exibicao = df_exibicao[filtro]
            
        # Exibir tabela interativa (atualizado para o novo padrão de largura)
        st.dataframe(df_exibicao, width='stretch', hide_index=True)
    else:
        st.info("Nenhum projeto cadastrado ainda. Vá na aba 'Cadastrar / Importar Lote' para adicionar dados.")

with aba2:
    st.subheader("Gerenciamento de Cadastros")
    
    col_cad1, col_cad2 = st.columns(2)
    
    with col_cad1:
        st.markdown("### Cadastro Individual")
        with st.form("form_cadastro"):
            c_serie = st.text_input("Cód. Série (Obrigatório)")
            c_acionamento = st.text_input("Acionamento")
            c_site_i = st.text_input("Site I")
            c_site_ii = st.text_input("Site II")
            c_codigo = st.text_input("Código")
            c_descricao = st.text_input("Descrição")
            c_local = st.text_input("Local")
            c_fornecedor = st.text_input("Fornecedor")
            c_cliente = st.text_input("Cliente")
            c_prazo = st.text_input("Prazo (dd/mm/aaaa)", value=datetime.now().strftime("%d/%m/%Y"))
            c_conclusao = st.text_input("Conclusão (dd/mm/aaaa)", value=datetime.now().strftime("%d/%m/%Y"))
            c_data_op = st.text_input("Data O.P. (dd/mm/aaaa)", value=datetime.now().strftime("%d/%m/%Y"))
            c_tipo = st.text_input("Tipo")
            c_status = st.selectbox("Status", ["Não Iniciado", "Em Andamento", "Concluído", "Parado"])
            
            submitted = st.form_submit_button("Salvar Projeto")
            if submitted:
                if c_serie:
                    try:
                        cursor.execute('''
                            INSERT INTO projetos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (c_serie, c_acionamento, c_site_i, c_site_ii, c_codigo, c_descricao, 
                              c_local, c_fornecedor, c_cliente, c_prazo, c_conclusao, c_data_op, c_tipo, c_status))
                        conn.commit()
                        st.success("Projeto cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar (Cód. Série já deve existir): {e}")
                else:
                    st.warning("O campo 'Cód. Série' é obrigatório!")

    with col_cad2:
        st.markdown("### 📋 Colar do Excel (Em Lote)")
        st.write("Cole abaixo as linhas copiadas da sua planilha (respeitando a ordem das colunas).")
        texto_lote = st.text_area("Cole os dados aqui:")
        
        if st.button("Processar Importação em Lote"):
            if texto_lote:
                linhas = texto_lote.strip().split("\n")
                importados = 0
                for linha in linhas:
                    if not linha.strip(): continue
                    colunas = linha.split("\t")
                    if len(colunas) >= 14:
                        vals = [c.strip() for c in colunas[:14]]
                        try:
                            cursor.execute("INSERT OR REPLACE INTO projetos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(vals))
                            importados += 1
                        except Exception:
                            pass
                conn.commit()
                st.success(f"{importados} registros importados com sucesso!")
                st.rerun()
            else:
                st.warning("A caixa de texto está vazia.")

with aba3:
    st.subheader("Etapas e Status do Projeto")
    st.write("Gerenciamento detalhado das etapas por projeto (em desenvolvimento).")