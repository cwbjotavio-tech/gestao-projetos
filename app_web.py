import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Projetos e Torres",
    page_icon="🏗️",
    layout="wide"
)

# ---------------------------------------------------------
# INICIALIZAÇÃO DO BANCO DE DADOS
# ---------------------------------------------------------
def init_db():
    try:
        # Lê a URL configurada nos Secrets do Streamlit Cloud
        database_url = st.secrets["DATABASE_URL"]
        
        # Cria o engine do SQLAlchemy
        engine = create_engine(database_url)
        
        # Garante a criação das tabelas essenciais no Supabase
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projetos (
                    id SERIAL PRIMARY KEY,
                    nome_projeto VARCHAR(255) NOT NULL,
                    cliente VARCHAR(255),
                    responsavel VARCHAR(255),
                    status VARCHAR(50)
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS torres (
                    id SERIAL PRIMARY KEY,
                    projeto_id INTEGER REFERENCES projetos(id) ON DELETE CASCADE,
                    num_serie VARCHAR(100),
                    acionamento VARCHAR(100),
                    revisao VARCHAR(50),
                    peso NUMERIC,
                    sites VARCHAR(100),
                    etapa_projeto VARCHAR(50),
                    etapa_steel VARCHAR(50),
                    etapa_sankhya VARCHAR(50)
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255),
                    email VARCHAR(255),
                    perfil VARCHAR(50)
                );
            """))
            
        return engine
    except Exception as e:
        st.error(f"Erro crítico ao inicializar o banco de dados: {e}")
        return None

# ---------------------------------------------------------
# FLUXO PRINCIPAL DA APLICAÇÃO
# ---------------------------------------------------------
def main():
    engine = init_db()
    
    if engine is None:
        st.stop("Não foi possível prosseguir sem a conexão com o banco de dados. Verifique a URL nos Secrets e reinicie o app.")

    st.title("🏗️ Sistema de Gestão de Projetos e Torres")
    
    # Menu lateral de navegação
    menu = st.sidebar.selectbox(
        "Navegação", 
        ["Dashboard", "Gerenciar Projetos", "Controle de Torres", "Usuários e Clientes"]
    )

    if menu == "Dashboard":
        st.header("📊 Visão Geral do Sistema")
        st.success("Conectado ao PostgreSQL / Supabase com sucesso!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Projetos Cadastrados")
            try:
                df_projetos = pd.read_sql("SELECT * FROM projetos", engine)
                if not df_projetos.empty:
                    st.dataframe(df_projetos, use_container_width=True)
                else:
                    st.info("Nenhum projeto cadastrado.")
            except Exception:
                st.warning("Tabela de projetos vazia.")

        with col2:
            st.subheader("Torres Cadastradas")
            try:
                df_torres = pd.read_sql("SELECT * FROM torres", engine)
                if not df_torres.empty:
                    st.dataframe(df_torres, use_container_width=True)
                else:
                    st.info("Nenhuma torre cadastrada.")
            except Exception:
                st.warning("Tabela de torres vazia.")

    elif menu == "Gerenciar Projetos":
        st.header("📁 Cadastro e Edição de Projetos")
        
        with st.form("form_projeto"):
            nome = st.text_input("Nome do Projeto")
            cliente = st.text_input("Cliente")
            responsavel = st.text_input("Responsável")
            status = st.selectbox("Status", ["Em Andamento", "Congelado", "Concluído"])
            
            submitted = st.form_submit_button("Salvar Projeto")
            if submitted and nome:
                try:
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO projetos (nome_projeto, cliente, responsavel, status) VALUES (:n, :c, :r, :s)"),
                            {"n": nome, "c": cliente, "r": responsavel, "s": status}
                        )
                    st.success("Projeto cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar projeto: {e}")

    elif menu == "Controle de Torres":
        st.header("🗼 Gerenciamento de Torres")
        st.write("Acompanhamento detalhado por acionamento, projeto, revisão, peso, sites, numeração de série e etapas.")
        
        try:
            projetos_df = pd.read_sql("SELECT id, nome_projeto FROM projetos", engine)
            if projetos_df.empty:
                st.warning("Cadastre um projeto primeiro antes de adicionar torres.")
            else:
                with st.form("form_torre"):
                    projeto_dict = dict(zip(projetos_df["nome_projeto"], projetos_df["id"]))
                    proj_escolhido = st.selectbox("Selecione o Projeto", list(projeto_dict.keys()))
                    
                    num_serie = st.text_input("Numeração de Série")
                    acionamento = st.text_input("Acionamento")
                    revisao = st.text_input("Revisão")
                    peso = st.number_input("Peso (kg)", min_value=0.0, format="%.2f")
                    sites = st.text_input("Sites")
                    
                    st.markdown("### Controle de Etapas")
                    etapa_projeto = st.selectbox("Etapa Projeto", ["Pendente", "Em Andamento", "Concluído"])
                    etapa_steel = st.selectbox("Etapa Steel", ["Pendente", "Em Andamento", "Concluído"])
                    etapa_sankhya = st.selectbox("Etapa Sankhya", ["Pendente", "Em Andamento", "Concluído"])
                    
                    submit_torre = st.form_submit_button("Cadastrar Torre")
                    
                    if submit_torre and num_serie:
                        proj_id = projeto_dict[proj_escolhido]
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO torres (
                                    projeto_id, num_serie, acionamento, revisao, peso, sites, 
                                    etapa_projeto, etapa_steel, etapa_sankhya
                                ) VALUES (
                                    :pid, :ns, :ac, :rev, :pes, :sit, :ep, :es, :esan
                                )
                            """), {
                                "pid": proj_id, "ns": num_serie, "ac": acionamento, 
                                "rev": revisao, "pes": peso, "sit": sites,
                                "ep": etapa_projeto, "es": etapa_steel, "esan": etapa_sankhya
                            })
                        st.success("Torre cadastrada com sucesso!")
                        st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar dados para torres: {e}")

    elif menu == "Usuários e Clientes":
        st.header("👥 Administração de Usuários")
        with st.form("form_usuario"):
            nome_usuario = st.text_input("Nome do Usuário")
            email_usuario = st.text_input("E-mail")
            perfil = st.selectbox("Perfil", ["Administrador", "Visualizador", "Engenheiro"])
            
            submit_user = st.form_submit_button("Salvar Usuário")
            if submit_user and nome_usuario:
                try:
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO usuarios (nome, email, perfil) VALUES (:n, :e, :p)"),
                            {"n": nome_usuario, "e": email_usuario, "p": perfil}
                        )
                    st.success("Usuário salvo com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar usuário: {e}")

if __name__ == "__main__":
    main()
