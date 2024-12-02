import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import webbrowser

# Configuração inicial do banco de dados
DB_NAME = "sistema_vendas.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabelas do sistema, criação das tabela do banco de dados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            marca TEXT,
            tamanho TEXT,
            preco_compra REAL NOT NULL,
            preco_venda REAL NOT NULL,
            data_compra DATE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            profissional TEXT NOT NULL,
            cliente TEXT,
            data DATE NOT NULL,
            FOREIGN KEY (id_produto) REFERENCES produtos (id)
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT NOT NULL,
        endereco TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone TEXT NOT NULL,
        data_nascimento DATE NOT NULL,
        data_cadastro DATE NOT NULL
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profissionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            area_atuacao TEXT,
            cpf TEXT NOT NULL UNIQUE,
            data_nascimento DATE,
            endereco TEXT,
            observacao TEXT
        )
    """)
    conn.commit()
    conn.close()

# Função genérica para executar comandos no banco de dados
def execute_query(query, params=None, fetch=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    if fetch:
        data = cursor.fetchall()
        conn.close()
        return data
    conn.commit()
    conn.close()

# Função de login
def verificar_login(email, senha):
    if email == "email" and senha == "senha":
        return True
    return False

# Tela de Login
def tela_login():
    st.title("Sistema de Vendas - Login")
    email = st.text_input("E-mail", key="login_email")
    senha = st.text_input("Senha", type="password", key="login_senha")
    if st.button("Entrar"):
        if verificar_login(email, senha):
            st.session_state["logado"] = True
            st.session_state["email"] = email
            st.success("Login realizado com sucesso!")

# Funções de manipulação de produtos
def cadastrar_produto():
    st.title("Cadastro de Produtos")
    with st.form("product_form", clear_on_submit=True):
        nome_produto = st.text_input("Nome do Produto", placeholder="Digite o nome do produto")
        marca = st.text_input("Marca", placeholder="Digite a marca do produto")
        tamanho = st.text_input("Tamanho", placeholder="Digite o tamanho ou especificação")
        preco_compra = st.number_input("Preço de Compra", min_value=0.01, step=0.01, format="%.2f")
        preco_venda = st.number_input("Preço de Venda", min_value=0.01, step=0.01, format="%.2f")
        data_compra = st.date_input("Data da Compra")

        # Botão para submeter o formulário
        if st.form_submit_button("Cadastrar"):
            # Validação de campos obrigatórios
            if not (nome_produto and marca and tamanho and preco_compra > 0 and preco_venda > 0 and data_compra):
                st.error("Todos os campos são obrigatórios! Por favor, preencha todos os campos.")
            else:
                # Comando SQL para inserir o produto no banco de dados
                query = """
                INSERT INTO produtos (nome, marca, tamanho, preco_compra, preco_venda, data_compra)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (
                    nome_produto,
                    marca,
                    tamanho,
                    preco_compra,
                    preco_venda,
                    data_compra.strftime("%Y-%m-%d")
                )
                try:
                    execute_query(query, params)
                    st.success(f"Produto '{nome_produto}' cadastrado com sucesso!")
                except sqlite3.Error as e:
                    st.error(f"Erro ao cadastrar o produto: {e}")

# Estoque de produtos
# Estoque de produtos
def estoque():
    st.title("Estoque de Produtos")

    # Consultar movimentações e produtos do banco de dados
    movimentacoes = execute_query("""
        SELECT id_produto, tipo, quantidade
        FROM movimentacoes
    """, fetch=True)

    produtos = execute_query("""
        SELECT id, nome, marca, tamanho, preco_compra, preco_venda
        FROM produtos
    """, fetch=True)

    if not movimentacoes or not produtos:
        st.write("Nenhuma movimentação ou produto cadastrado.")
        return

    # Criar DataFrames para movimentações e produtos
    df_movimentacoes = pd.DataFrame(movimentacoes, columns=["ID Produto", "Tipo", "Quantidade"])
    df_produtos = pd.DataFrame(produtos, columns=[
        "ID Produto", "Nome", "Marca", "Tamanho", "Preço Compra", "Preço Venda"
    ])

    # Calcular saldo (compras - vendas) para cada produto
    saldo_produtos = (
        df_movimentacoes.groupby("ID Produto")
        .apply(lambda x: x.loc[x["Tipo"] == "Compra", "Quantidade"].sum() - x.loc[x["Tipo"] == "Venda", "Quantidade"].sum())
    )

    # Filtrar apenas produtos com saldo positivo (em estoque)
    produtos_em_estoque = saldo_produtos[saldo_produtos > 0]

    if not produtos_em_estoque.empty:
        # Mesclar dados do saldo com as informações dos produtos
        df_saldo = pd.DataFrame({
            "ID Produto": produtos_em_estoque.index,
            "Saldo": produtos_em_estoque.values
        })

        df_estoque = pd.merge(df_saldo, df_produtos, on="ID Produto")

        # Reorganizar as colunas para exibição
        df_estoque = df_estoque[[
            "ID Produto", "Nome", "Marca", "Tamanho", "Preço Compra", "Preço Venda", "Saldo"
        ]]

        # Exibir os produtos em estoque
        st.dataframe(df_estoque)
    else:
        st.write("Nenhum produto em estoque no momento.")

# Movimentações de produtos
# Movimentações de produtos
def movimentacoes():
    st.title("Movimentações de Produtos")

    # Recuperar IDs dos produtos cadastrados no banco
    produtos = execute_query("SELECT id FROM produtos", fetch=True)
    profissionais = execute_query("SELECT nome FROM profissionais", fetch=True)
    clientes = execute_query("SELECT nome FROM clientes", fetch=True)

    if not produtos:
        st.warning("Nenhum produto cadastrado. Por favor, cadastre produtos antes de registrar movimentações.")
        return

    # Criar listas suspensas com os dados do banco
    ids_produtos = [str(row[0]) for row in produtos]
    profissionais_nomes = [row[0] for row in profissionais]
    clientes_nomes = [row[0] for row in clientes]

    with st.form("movement_form", clear_on_submit=True):
        id_produto_selecionado = st.selectbox("ID do Produto", ids_produtos)
        tipo = st.selectbox("Tipo de Movimentação", ["Venda", "Compra"])
        quantidade = st.number_input("Quantidade", min_value=1)

        # Seleção de profissional responsável
        if profissionais_nomes:
            profissional = st.selectbox("Profissional Responsável", profissionais_nomes)
        else:
            st.warning("Nenhum profissional cadastrado. Cadastre um antes de prosseguir.")
            profissional = None

        # Seleção de cliente (somente para vendas)
        cliente = None
        if tipo == "Venda":
            if clientes_nomes:
                cliente = st.selectbox("Cliente", clientes_nomes)
            else:
                st.warning("Nenhum cliente cadastrado. Cadastre um antes de prosseguir.")
                cliente = None

        data = st.date_input("Data", value=datetime.today())

        if st.form_submit_button("Registrar Movimentação"):
            if profissional and (tipo != "Venda" or cliente):
                execute_query("""
                    INSERT INTO movimentacoes (id_produto, tipo, quantidade, profissional, cliente, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_produto_selecionado, tipo, quantidade, profissional, cliente if cliente else None, data))
                st.success("Movimentação registrada com sucesso!")
            else:
                st.error("Por favor, selecione todos os campos obrigatórios.")

    # Exibir histórico de movimentações
    st.subheader("Histórico de Movimentações")
    historico = execute_query("""
        SELECT m.id, m.id_produto AS "ID Produto", m.tipo, m.quantidade, m.profissional, m.cliente, m.data
        FROM movimentacoes m
    """, fetch=True)
    if historico:
        df = pd.DataFrame(historico, columns=[
            "ID", "ID Produto", "Tipo", "Quantidade", "Profissional", "Cliente", "Data"
        ])
        st.dataframe(df)
    else:
        st.write("Nenhuma movimentação registrada.")

# Cadastro de clientes
# Cadastro de clientes
# Função para cadastro de clientes
def cadastrar_cliente():
    st.title("Cadastro de Clientes")
    with st.form("client_form", clear_on_submit=True):
        nome_completo = st.text_input("Nome Completo", placeholder="Digite o nome completo do cliente")
        cpf = st.text_input("CPF", placeholder="Digite o CPF do cliente (apenas números)")
        endereco = st.text_area("Endereço Completo", placeholder="Digite o endereço completo")
        email = st.text_input("E-mail", placeholder="Digite o e-mail do cliente")
        telefone = st.text_input("Número de Telefone", placeholder="Digite o número de telefone")
        data_nascimento = st.date_input("Data de Nascimento")
        data_cadastro = datetime.today().strftime("%Y-%m-%d")  # Data de cadastro automática

        st.write(f"Data de Cadastro: {data_cadastro}")

        # Botão para submeter o formulário
        if st.form_submit_button("Cadastrar"):
            # Validação de campos obrigatórios
            if not (nome_completo and cpf and endereco and email and telefone and data_nascimento):
                st.error("Todos os campos são obrigatórios! Por favor, preencha todos os campos.")
            else:
                # Comando SQL para inserir o cliente no banco de dados
                query = """
                INSERT INTO clientes (nome, cpf, endereco, email, telefone, data_nascimento, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    nome_completo,
                    cpf,
                    endereco,
                    email,
                    telefone,
                    data_nascimento.strftime("%Y-%m-%d"),
                    data_cadastro
                )
                try:
                    execute_query(query, params)
                    st.success(f"Cliente '{nome_completo}' cadastrado com sucesso!")
                except sqlite3.Error as e:
                    st.error(f"Erro ao cadastrar o cliente: {e}")

# Cadastro de profissionais
# Cadastro de profissionais
def cadastrar_profissional():
    st.title("Cadastro de Profissionais")
    with st.form("professional_form", clear_on_submit=True):
        nome = st.text_input("Nome Completo", placeholder="Digite o nome completo")
        area_atuacao = st.text_input("Área de Atuação", placeholder="Digite a área de atuação")
        cpf = st.text_input("CPF", placeholder="Digite o CPF")
        data_nascimento = st.date_input("Data de Nascimento")
        endereco = st.text_area("Endereço", placeholder="Digite o endereço")
        observacao = st.text_area("Observação (opcional)")

        if st.form_submit_button("Cadastrar"):
            if not (nome and area_atuacao and cpf and data_nascimento and endereco):
                st.error("Todos os campos são obrigatórios, exceto Observação!")
            else:
                query = """
                INSERT INTO profissionais (nome, area_atuacao, cpf, data_nascimento, endereco, observacao)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (nome, area_atuacao, cpf, data_nascimento.strftime("%Y-%m-%d"), endereco, observacao)
                try:
                    execute_query(query, params)
                    st.success("Profissional cadastrado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("Erro: CPF já cadastrado.")

# Produtos cadastrados
def produtos_cadastrados():
    st.title("Produtos Cadastrados")
    produtos = execute_query("SELECT * FROM produtos", fetch=True)
    if produtos:
        df = pd.DataFrame(produtos, columns=[
            "ID", "Nome", "Marca", "Tamanho", "Preço Compra", "Preço Venda", "Data Compra"
        ])
        st.dataframe(df)
    else:
        st.write("Nenhum produto cadastrado.")

# Planilha de clientes
def planilha_clientes():
    st.title("Clientes Cadastrados")

    # Consultar informações dos clientes no banco de dados
    clientes = execute_query("SELECT * FROM clientes", fetch=True)

    if clientes:
        # Criar um DataFrame com os dados dos clientes
        df_clientes = pd.DataFrame(clientes, columns=[
            "ID", "Nome", "CPF", "Endereço", "E-mail","Telefone","Data de Nascimento","Data_Cadastro"
        ])
        st.dataframe(df_clientes)  # Exibir os dados em uma tabela interativa

        # Botão para exportar a tabela para um arquivo CSV
        csv = df_clientes.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar Planilha de Clientes",
            data=csv,
            file_name="clientes.csv",
            mime="text/csv"
        )
    else:
        st.write("Nenhum cliente cadastrado.")


# Sistema principal, onde vai verificar se voce está logado ou não,
if "logado" not in st.session_state or not st.session_state["logado"]:
    init_db()
    tela_login()
else:
    st.sidebar.title("Sistema de Vendas")
    page = st.sidebar.radio(
        "Navegação",
        ["Cadastro de Produtos", "Estoque", "Movimentações", "Cadastro de Clientes", "Cadastro de Profissionais", "Produtos Cadastrados","Clientes Cadastrados"]
    )
    # essa parte vai verificar qual botão está selecionado para aparecer na tela as funções criadas das determinadas funções
    if page == "Cadastro de Produtos":
        cadastrar_produto()
    elif page == "Estoque":
        estoque()
    elif page == "Movimentações":
        movimentacoes()
    elif page == "Cadastro de Clientes":
        cadastrar_cliente()
    elif page == "Cadastro de Profissionais":
        cadastrar_profissional()
    elif page == "Produtos Cadastrados":
        produtos_cadastrados()
    elif page == "Clientes Cadastrados":
        planilha_clientes()

    st.sidebar.markdown("---") # vai colocar a linha para separa o filtro
    col1, col2 = st.sidebar.columns(2)  # vai separar os botois em duas colunas

    with col1:
        if st.button("Dashboard"):
            webbrowser.open_new_tab("https://app.powerbi.com/view?r=eyJrIjoiMzQwZmNkZGMtMmY1Zi00MWE3LTkyZmUtOTQ3ODYwZDkwZmM5IiwidCI6IjQxODVkYjBhLTQxNmItNDE4ZS05ZWZmLTdlYWVhZDZiNWE0NCJ9") # aqui voce vai colocar o link do dashboard
    with col2:
        if st.button("Informações"):
            webbrowser.open_new_tab("https://example.com") # aqui voce vai colocar o link de algumas informações

