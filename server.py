"""
Mana Food - Servidor Web v4.0
Execute com: python server.py
"""
import sqlite3
import os
import shutil
import json
import webbrowser
import threading
import time
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent / "lanchonete"
DATA_DIR = BASE_DIR / "data"
IMG_DIR  = BASE_DIR / "imagens"
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "lanchonete.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, preco REAL NOT NULL,
        quantidade INTEGER DEFAULT 0, unidades TEXT DEFAULT 'un',
        categoria TEXT, ativo BOOLEAN DEFAULT 1,
        imagem TEXT DEFAULT '',
        custo REAL DEFAULT 0,
        markup REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, telefone TEXT DEFAULT '',
        cpf TEXT DEFAULT '', endereco TEXT DEFAULT '',
        observacao TEXT DEFAULT '', limite_credito REAL DEFAULT 0,
        ativo BOOLEAN DEFAULT 1,
        marcadores TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total REAL NOT NULL, observacao TEXT,
        tipo_pagamento TEXT DEFAULT 'dinheiro',
        cliente_id INTEGER DEFAULT NULL,
        cliente TEXT DEFAULT '',
        FOREIGN KEY (cliente_id) REFERENCES clientes(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS itens_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL, produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (venda_id) REFERENCES vendas(id),
        FOREIGN KEY (produto_id) REFERENCES produtos(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS financeiro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL, descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        data_movimentacao DATE DEFAULT (date('now','localtime')),
        categoria TEXT, pagamento TEXT DEFAULT '-',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        tipo TEXT DEFAULT 'produto',
        cor TEXT DEFAULT '#999999',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS contas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL, descricao TEXT NOT NULL,
        valor REAL NOT NULL, vencimento DATE NOT NULL,
        status TEXT DEFAULT 'pendente',
        cliente_id INTEGER DEFAULT NULL,
        cliente_fornecedor TEXT DEFAULT '',
        categoria TEXT DEFAULT 'Geral',
        venda_id INTEGER DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id))""")

    # Migrações seguras
    for sql in [
        "ALTER TABLE produtos ADD COLUMN imagem TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cliente TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cliente_id INTEGER DEFAULT NULL",
        "ALTER TABLE financeiro ADD COLUMN pagamento TEXT DEFAULT '-'",
        "ALTER TABLE contas ADD COLUMN cliente_id INTEGER DEFAULT NULL",
        "ALTER TABLE clientes ADD COLUMN marcadores TEXT DEFAULT ''",
        "ALTER TABLE contas ADD COLUMN financeiro_id INTEGER DEFAULT NULL",
        "ALTER TABLE produtos ADD COLUMN custo REAL DEFAULT 0",
        "ALTER TABLE produtos ADD COLUMN markup REAL DEFAULT 0",
        "ALTER TABLE clientes ADD COLUMN status_cliente TEXT DEFAULT 'ativo'",
        "ALTER TABLE produtos ADD COLUMN codigo TEXT DEFAULT ''",
        "CREATE TABLE IF NOT EXISTS historico_cliente (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER NOT NULL, tipo TEXT NOT NULL, descricao TEXT NOT NULL, valor REAL DEFAULT 0, data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP, referencia_id INTEGER DEFAULT NULL)",
        "CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT DEFAULT 'fechado', valor_abertura REAL DEFAULT 0, valor_fechamento REAL DEFAULT NULL, troco_abertura REAL DEFAULT 0, observacao_abertura TEXT DEFAULT '', observacao_fechamento TEXT DEFAULT '', aberto_em TIMESTAMP DEFAULT NULL, fechado_em TIMESTAMP DEFAULT NULL)",
        "CREATE TABLE IF NOT EXISTS movimentos_caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, caixa_id INTEGER NOT NULL, tipo TEXT NOT NULL, descricao TEXT NOT NULL, valor REAL NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(caixa_id) REFERENCES caixa(id))",
        "ALTER TABLE vendas ADD COLUMN caixa_id INTEGER DEFAULT NULL",
        "ALTER TABLE caixa ADD COLUMN usuario_id INTEGER DEFAULT NULL",
        "ALTER TABLE caixa ADD COLUMN usuario_nome TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cancelada INTEGER DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN motivo_cancelamento TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cancelada_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN entrega INTEGER DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN entrega_nome TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN entrega_telefone TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN entrega_endereco TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN entrega_bairro TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN entrega_referencia TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN entrega_taxa REAL DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN entrega_obs TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN tipo_atendimento TEXT DEFAULT 'balcao'",
        "ALTER TABLE vendas ADD COLUMN mesa TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN nome_cliente_mesa TEXT DEFAULT ''",
        "CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, usuario TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, perfil TEXT DEFAULT 'operador', ativo INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS log_auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, usuario_nome TEXT DEFAULT 'Sistema', acao TEXT NOT NULL, modulo TEXT NOT NULL, descricao TEXT NOT NULL, dados_antes TEXT DEFAULT '', dados_depois TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "ALTER TABLE vendas ADD COLUMN nome_cliente_balcao TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN pagamentos_mix TEXT DEFAULT ''",
        "ALTER TABLE usuarios ADD COLUMN perms_custom TEXT DEFAULT ''",
        "ALTER TABLE produtos ADD COLUMN favorito INTEGER DEFAULT 0",
        "ALTER TABLE produtos ADD COLUMN cmv_custo REAL DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN desconto REAL DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN gorjeta REAL DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN cupom TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cupom_desconto REAL DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN mesa_historico TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN status_mesa TEXT DEFAULT 'fechada'",
        "ALTER TABLE cupons ADD COLUMN validade DATE DEFAULT NULL",
        "CREATE TABLE IF NOT EXISTS mesas_ativas (id INTEGER PRIMARY KEY AUTOINCREMENT, mesa TEXT NOT NULL UNIQUE, nome_cliente TEXT DEFAULT '', aberto_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'aberta')",
        "CREATE TABLE IF NOT EXISTS cupons (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT NOT NULL UNIQUE, tipo TEXT DEFAULT 'percentual', valor REAL NOT NULL, ativo INTEGER DEFAULT 1, usos INTEGER DEFAULT 0, limite_usos INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, data DATE NOT NULL UNIQUE, meta_valor REAL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS cardapio_config (id INTEGER PRIMARY KEY AUTOINCREMENT, ativo INTEGER DEFAULT 1, titulo TEXT DEFAULT 'Nosso Cardápio', cor_primaria TEXT DEFAULT '#e67e22', exibir_preco INTEGER DEFAULT 1, exibir_estoque INTEGER DEFAULT 0, mensagem TEXT DEFAULT '')",
        "ALTER TABLE vendas ADD COLUMN status_entrega TEXT DEFAULT 'pendente'",
        "ALTER TABLE vendas ADD COLUMN entrega_saiu_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN entrega_separado_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN entrega_entregue_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN entregador TEXT DEFAULT ''",
        "ALTER TABLE itens_venda ADD COLUMN observacao TEXT DEFAULT ''",
        "ALTER TABLE itens_venda ADD COLUMN preco_editado REAL DEFAULT NULL",
        # Desconto individual por item do carrinho (o frontend já calcula e exibe
        # isso desde antes; o backend nunca persistia o valor no subtotal gravado)
        "ALTER TABLE itens_venda ADD COLUMN desconto_item REAL DEFAULT 0",
        # Entrega: cliente desistiu / não tinha ninguém em casa
        "ALTER TABLE vendas ADD COLUMN entrega_desistiu_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN entrega_motivo_desistencia TEXT DEFAULT ''",
        # Venda descartada (carrinho perdido ao clicar Nova Venda) — recuperável
        "ALTER TABLE vendas ADD COLUMN descartada INTEGER DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN descartada_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN carrinho_json TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN recuperada INTEGER DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN recuperada_em TIMESTAMP DEFAULT NULL",
        "ALTER TABLE vendas ADD COLUMN offline_id TEXT DEFAULT ''",
        "ALTER TABLE produtos ADD COLUMN descricao TEXT DEFAULT ''",
        "ALTER TABLE produtos ADD COLUMN emoji TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cartao_bandeira TEXT DEFAULT ''",
        "ALTER TABLE vendas ADD COLUMN cartao_nsu TEXT DEFAULT ''",
        "CREATE TABLE IF NOT EXISTS ingredientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, unidade TEXT DEFAULT 'un', quantidade REAL DEFAULT 0, custo REAL DEFAULT 0, estoque_minimo REAL DEFAULT 5, ativo INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS produto_ingredientes (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER NOT NULL, ingrediente_id INTEGER NOT NULL, quantidade_usada REAL NOT NULL DEFAULT 1, FOREIGN KEY(produto_id) REFERENCES produtos(id), FOREIGN KEY(ingrediente_id) REFERENCES ingredientes(id))",
        "CREATE TABLE IF NOT EXISTS promocoes (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER NOT NULL, tipo TEXT DEFAULT 'percentual', valor REAL NOT NULL, preco_promo REAL DEFAULT 0, data_inicio DATE NOT NULL, data_fim DATE NOT NULL, ativo INTEGER DEFAULT 1, descricao TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(produto_id) REFERENCES produtos(id))",
        "ALTER TABLE clientes ADD COLUMN cashback_saldo REAL DEFAULT 0",
        "ALTER TABLE clientes ADD COLUMN pontos INTEGER DEFAULT 0",
        "CREATE TABLE IF NOT EXISTS cashback_config (id INTEGER PRIMARY KEY, cashback_ativo INTEGER DEFAULT 0, cashback_percentual REAL DEFAULT 5, pontos_ativo INTEGER DEFAULT 0, pontos_por_real REAL DEFAULT 1, pontos_resgate_minimo INTEGER DEFAULT 100, pontos_valor_resgate REAL DEFAULT 10)",
        "CREATE TABLE IF NOT EXISTS movimentos_fidelidade (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER NOT NULL, tipo TEXT NOT NULL, valor REAL DEFAULT 0, pontos INTEGER DEFAULT 0, venda_id INTEGER, descricao TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "ALTER TABLE cardapio_config ADD COLUMN endereco TEXT DEFAULT ''",
        "ALTER TABLE cardapio_config ADD COLUMN telefone TEXT DEFAULT ''",
        "ALTER TABLE cardapio_config ADD COLUMN horario TEXT DEFAULT ''",
        "ALTER TABLE cardapio_config ADD COLUMN instagram TEXT DEFAULT ''",
        "ALTER TABLE cardapio_config ADD COLUMN pedido_minimo REAL DEFAULT 0",
        "ALTER TABLE cardapio_config ADD COLUMN logo TEXT DEFAULT ''",
        "CREATE TABLE IF NOT EXISTS empresa (id INTEGER PRIMARY KEY, razao_social TEXT DEFAULT '', nome_fantasia TEXT DEFAULT '', cnpj TEXT DEFAULT '', ie TEXT DEFAULT '', im TEXT DEFAULT '', endereco TEXT DEFAULT '', numero TEXT DEFAULT '', bairro TEXT DEFAULT '', cidade TEXT DEFAULT '', uf TEXT DEFAULT '', cep TEXT DEFAULT '', telefone TEXT DEFAULT '', email TEXT DEFAULT '', regime_tributario TEXT DEFAULT 'simples_nacional', crt INTEGER DEFAULT 1)",
        "CREATE TABLE IF NOT EXISTS config_fiscal (id INTEGER PRIMARY KEY, ambiente INTEGER DEFAULT 2, serie_nfce INTEGER DEFAULT 1, serie_nfe INTEGER DEFAULT 1, csc_id TEXT DEFAULT '', csc_token TEXT DEFAULT '', proximo_numero_nfce INTEGER DEFAULT 1, proximo_numero_nfe INTEGER DEFAULT 1, certificado_arquivo TEXT DEFAULT '', certificado_senha TEXT DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS entradas_xml (id INTEGER PRIMARY KEY AUTOINCREMENT, chave_acesso TEXT DEFAULT '', fornecedor TEXT DEFAULT '', cnpj_fornecedor TEXT DEFAULT '', data_emissao TEXT DEFAULT '', valor_total REAL DEFAULT 0, xml_conteudo TEXT DEFAULT '', processado INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS itens_entrada_xml (id INTEGER PRIMARY KEY AUTOINCREMENT, entrada_id INTEGER NOT NULL, codigo TEXT DEFAULT '', descricao TEXT DEFAULT '', ncm TEXT DEFAULT '', cfop TEXT DEFAULT '', unidade TEXT DEFAULT '', quantidade REAL DEFAULT 0, valor_unitario REAL DEFAULT 0, valor_total REAL DEFAULT 0, produto_id INTEGER DEFAULT NULL, FOREIGN KEY(entrada_id) REFERENCES entradas_xml(id))",
    ]:
        try: c.execute(sql); conn.commit()
        except: pass

    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO produtos (nome,preco,quantidade,unidades,categoria) VALUES (?,?,?,?,?)",
            [('X-Burger',15.00,50,'un','Lanches'),('X-Salada',17.00,50,'un','Lanches'),
             ('Hot Dog',12.00,30,'un','Lanches'),('Coca-Cola',6.00,60,'un','Bebidas'),
             ('Suco',8.00,40,'un','Bebidas'),('Agua',4.00,80,'un','Bebidas'),
             ('Batata Frita',10.00,25,'un','Porções'),('Pastel',7.00,40,'un','Frituras')])

    c.execute("SELECT COUNT(*) FROM categorias")
    if c.fetchone()[0] == 0:
        cats_prod = [('Lanches','produto','#e67e22'),('Bebidas','produto','#3498db'),
                     ('Porções','produto','#2ecc71'),('Frituras','produto','#e74c3c'),
                     ('Sobremesas','produto','#9b59b6'),('Outros','produto','#95a5a6')]
        cats_fin  = [('Vendas','financeiro','#1D9E75'),('Compras','financeiro','#e74c3c'),
                     ('Aluguel','financeiro','#e67e22'),('Salários','financeiro','#3498db'),
                     ('Fornecedor','financeiro','#9b59b6'),('Crediário','financeiro','#f39c12')]
        c.executemany("INSERT OR IGNORE INTO categorias (nome,tipo,cor) VALUES (?,?,?)",
                      cats_prod + cats_fin)

    conn.commit(); conn.close()
    print("Banco de dados OK!")


# ─── PRODUTOS ────────────────────────────────────────────────────────────────

def _gerar_codigo(c):
    """Gera código interno único no formato INT-XXXXXX"""
    while True:
        import random
        codigo = f"INT-{random.randint(100000,999999)}"
        c.execute("SELECT id FROM produtos WHERE codigo=?", (codigo,))
        if not c.fetchone():
            return codigo

def api_listar_produtos():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM produtos WHERE ativo=1 ORDER BY nome")
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r

def api_buscar_produto_codigo(q):
    """Busca produto por código de barras, código interno ou nome"""
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM produtos WHERE ativo=1 AND (codigo=? OR LOWER(nome) LIKE ?) LIMIT 10",
              (q.strip(), f'%{q.strip().lower()}%'))
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r

def api_cadastrar_produto(data):
    conn = get_connection(); cur = conn.cursor()
    imagem = data.get('imagem', '')
    if imagem and imagem.startswith('data:image'):
        try:
            ext   = imagem.split(';')[0].split('/')[-1]
            b64   = imagem.split(',')[1]
            fname = f"prod_{int(time.time()*1000)}.{ext}"
            (IMG_DIR / fname).write_bytes(base64.b64decode(b64))
            imagem = fname
        except: imagem = ''
    custo  = float(data.get('custo', 0) or 0)
    markup = float(data.get('markup', 0) or 0)
    preco  = float(data.get('preco', 0) or 0)
    # código: usa o informado ou gera automaticamente
    codigo = data.get('codigo','').strip()
    if codigo:
        # verifica duplicata
        cur.execute("SELECT id FROM produtos WHERE codigo=? AND ativo=1", (codigo,))
        if cur.fetchone():
            conn.close(); return {"ok":False,"erro":f"Código '{codigo}' já está em uso"}
    else:
        codigo = _gerar_codigo(cur)
    descricao = data.get('descricao','')
    cur.execute("""INSERT INTO produtos (nome,preco,quantidade,unidades,categoria,imagem,custo,markup,codigo,descricao)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (data['nome'], preco, int(data['quantidade']),
                 data.get('unidades','un'), data.get('categoria','Geral'), imagem, custo, markup, codigo, descricao))
    conn.commit(); new_id = cur.lastrowid; conn.close()
    _auto_publicar_cardapio()
    return {"id": new_id, "ok": True, "codigo": codigo}

def api_atualizar_produto(data):
    conn = get_connection(); c = conn.cursor()
    pid = int(data['id'])
    # Edição completa (nome, preço, código, etc.)
    if 'nome' in data:
        imagem = data.get('imagem', None)
        if imagem and imagem.startswith('data:image'):
            try:
                ext   = imagem.split(';')[0].split('/')[-1]
                b64   = imagem.split(',')[1]
                fname = f"prod_{int(time.time()*1000)}.{ext}"
                (IMG_DIR / fname).write_bytes(base64.b64decode(b64))
                imagem = fname
            except: imagem = None
        custo  = float(data.get('custo', 0) or 0)
        markup = float(data.get('markup', 0) or 0)
        preco  = float(data.get('preco', 0) or 0)
        qtd    = int(data.get('quantidade', 0) or 0)
        codigo = data.get('codigo','').strip()
        if not codigo:
            c.execute("SELECT codigo FROM produtos WHERE id=?", (pid,))
            row = c.fetchone()
            codigo = (row['codigo'] if row and row['codigo'] else _gerar_codigo(c))
        else:
            # verifica duplicata excluindo o próprio produto
            c.execute("SELECT id FROM produtos WHERE codigo=? AND id!=? AND ativo=1", (codigo, pid))
            if c.fetchone():
                conn.close(); return {"ok":False,"erro":f"Código '{codigo}' já está em uso"}
        descricao = data.get('descricao','')
        emoji_val = data.get('emoji','')
        if imagem is not None:
            c.execute("UPDATE produtos SET nome=?,preco=?,quantidade=?,unidades=?,categoria=?,custo=?,markup=?,imagem=?,codigo=?,descricao=?,emoji=? WHERE id=?",
                      (data['nome'], preco, qtd, data.get('unidades','un'), data.get('categoria','Geral'), custo, markup, imagem, codigo, descricao, emoji_val, pid))
        else:
            c.execute("UPDATE produtos SET nome=?,preco=?,quantidade=?,unidades=?,categoria=?,custo=?,markup=?,codigo=?,descricao=?,emoji=? WHERE id=?",
                      (data['nome'], preco, qtd, data.get('unidades','un'), data.get('categoria','Geral'), custo, markup, codigo, descricao, emoji_val, pid))
    elif 'quantidade' in data and 'custo' not in data:
        c.execute("UPDATE produtos SET quantidade=? WHERE id=?", (int(data['quantidade']), pid))
    elif 'custo' in data:
        custo  = float(data.get('custo',0) or 0)
        markup = float(data.get('markup',0) or 0)
        preco  = float(data.get('preco',0) or 0)
        fields = "custo=?, markup=?"
        vals   = [custo, markup]
        if preco > 0:
            fields += ", preco=?"
            vals.append(preco)
        vals.append(pid)
        c.execute(f"UPDATE produtos SET {fields} WHERE id=?", vals)
    conn.commit(); conn.close()
    _auto_publicar_cardapio()
    return {"ok": True}

def api_imagem_produto(produto_id):
    """Retorna a imagem de um produto como base64."""
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT imagem FROM produtos WHERE id=?", (produto_id,))
    row = c.fetchone(); conn.close()
    if not row or not row['imagem']: return None
    fname = row['imagem']
    fpath = IMG_DIR / fname
    if not fpath.exists(): return None
    ext = fname.split('.')[-1]
    mime = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
    b64 = base64.b64encode(fpath.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"



# ─── CATEGORIAS ──────────────────────────────────────────────────────────────

def api_listar_categorias(tipo=None):
    conn = get_connection(); cur = conn.cursor()
    if tipo:
        cur.execute("SELECT * FROM categorias WHERE tipo=? ORDER BY nome", (tipo,))
    else:
        cur.execute("SELECT * FROM categorias ORDER BY tipo, nome")
    r = [dict(x) for x in cur.fetchall()]; conn.close(); return r

def api_listar_categorias_get():
    return api_listar_categorias()

def api_cadastrar_categoria(data):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categorias (nome,tipo,cor) VALUES (?,?,?)",
                    (data['nome'].strip(), data.get('tipo','produto'), data.get('cor','#999999')))
        conn.commit(); new_id = cur.lastrowid; conn.close()
        return {"id": new_id, "ok": True}
    except Exception as e:
        conn.close(); return {"ok": False, "erro": str(e)}

def api_atualizar_categoria(data):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE categorias SET nome=?,cor=? WHERE id=?",
                (data['nome'].strip(), data.get('cor','#999999'), int(data['id'])))
    conn.commit(); conn.close(); return {"ok": True}

def api_excluir_categoria(data):
    conn = get_connection(); cur = conn.cursor()
    # Verifica se há produtos usando
    cur.execute("SELECT COUNT(*) FROM produtos WHERE categoria=? AND ativo=1",
                (data.get('nome',''),))
    if cur.fetchone()[0] > 0:
        conn.close(); return {"ok": False, "erro": "Categoria em uso por produtos ativos"}
    cur.execute("DELETE FROM categorias WHERE id=?", (int(data['id']),))
    conn.commit(); conn.close(); return {"ok": True}

# ─── CLIENTES ────────────────────────────────────────────────────────────────

def api_listar_clientes():
    conn = get_connection(); c = conn.cursor()
    c.execute("""
        SELECT cl.*,
               COALESCE(cl.status_cliente, 'ativo') AS status_cliente,
               COUNT(DISTINCT CASE WHEN v.cancelada=0 AND v.descartada=0 THEN v.id END) AS total_compras,
               COALESCE(SUM(CASE WHEN ct.status='pendente' THEN ct.valor ELSE 0 END),0) AS saldo_devedor
        FROM clientes cl
        LEFT JOIN vendas v  ON v.cliente_id = cl.id
        LEFT JOIN contas ct ON ct.cliente_id = cl.id AND ct.tipo='receber'
        WHERE cl.ativo=1
        GROUP BY cl.id ORDER BY cl.nome
    """)
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r

def api_buscar_cliente(cliente_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,))
    cl = c.fetchone()
    if not cl: conn.close(); return None
    cl = dict(cl)
    c.execute("""SELECT v.*, GROUP_CONCAT(p.nome||' x'||iv.quantidade, ', ') AS itens_str
                 FROM vendas v LEFT JOIN itens_venda iv ON iv.venda_id=v.id
                 LEFT JOIN produtos p ON p.id=iv.produto_id
                 WHERE v.cliente_id=? AND v.descartada=0 GROUP BY v.id ORDER BY v.id DESC LIMIT 20""", (cliente_id,))
    cl['vendas'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM contas WHERE cliente_id=? ORDER BY vencimento ASC", (cliente_id,))
    cl['contas'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM historico_cliente WHERE cliente_id=? ORDER BY data_evento DESC LIMIT 50", (cliente_id,))
    cl['historico'] = [dict(x) for x in c.fetchall()]
    conn.close(); return cl

def api_cadastrar_cliente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO clientes (nome,telefone,cpf,endereco,observacao,limite_credito,marcadores) VALUES (?,?,?,?,?,?,?)",
              (data['nome'], data.get('telefone',''), data.get('cpf',''),
               data.get('endereco',''), data.get('observacao',''),
               float(data.get('limite_credito',0)), data.get('marcadores','')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return {"id": new_id, "ok": True}

def api_atualizar_cliente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE clientes SET nome=?,telefone=?,cpf=?,endereco=?,observacao=?,limite_credito=?,marcadores=?,status_cliente=? WHERE id=?",
              (data['nome'], data.get('telefone',''), data.get('cpf',''),
               data.get('endereco',''), data.get('observacao',''),
               float(data.get('limite_credito',0)), data.get('marcadores',''),
               data.get('status_cliente','ativo'), int(data['id'])))
    conn.commit(); conn.close(); return {"ok": True}

def api_alterar_status_cliente(data):
    conn = get_connection(); c = conn.cursor()
    status = data.get('status_cliente', 'ativo')
    # Se inativar definitivamente (excluir), mantém ativo=0
    if status == 'excluido':
        c.execute("UPDATE clientes SET ativo=0 WHERE id=?", (int(data['id']),))
    else:
        c.execute("UPDATE clientes SET status_cliente=? WHERE id=?", (status, int(data['id'])))
    conn.commit(); conn.close(); return {"ok": True}

def api_inativar_cliente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE clientes SET ativo=0 WHERE id=?", (int(data['id']),))
    conn.commit(); conn.close(); return {"ok": True}


# ─── VENDAS ──────────────────────────────────────────────────────────────────

def api_registrar_venda(data):
    conn = get_connection(); c = conn.cursor()
    try:
        offline_id = data.get('_offline_id','')
        if offline_id:
            c.execute("SELECT id FROM vendas WHERE offline_id=?", (offline_id,))
            existing = c.fetchone()
            if existing:
                conn.close()
                return {"ok":True,"venda_id":existing['id'],"_duplicate":True}
        itens=data['itens']; total=float(data['total'])
        tipo_pag=data.get('tipo_pagamento','dinheiro')
        observacao=data.get('observacao','')
        cliente_id=data.get('cliente_id'); cliente_nm=data.get('cliente','')
        vencimento=data.get('vencimento','')
        # atendimento
        tipo_atend      = data.get('tipo_atendimento','balcao')
        pags_mix        = data.get('pagamentos_mix') or []
        desconto        = float(data.get('desconto',0) or 0)
        gorjeta         = float(data.get('gorjeta',0) or 0)
        cupom           = data.get('cupom','')
        cupom_desconto  = float(data.get('cupom_desconto',0) or 0)
        mesa            = data.get('mesa','')
        nome_cli_mesa   = data.get('nome_cliente_mesa','')
        nome_cli_balcao = data.get('nome_cliente_balcao','')
        # entrega
        entrega       = 1 if data.get('entrega') else 0
        ent_nome      = data.get('entrega_nome','')
        ent_tel       = data.get('entrega_telefone','')
        ent_end       = data.get('entrega_endereco','')
        ent_bairro    = data.get('entrega_bairro','')
        ent_ref       = data.get('entrega_referencia','')
        ent_taxa      = float(data.get('entrega_taxa',0) or 0)
        ent_obs       = data.get('entrega_obs','')
        if cliente_id:
            c.execute("SELECT nome FROM clientes WHERE id=?", (cliente_id,))
            row=c.fetchone()
            if row: cliente_nm=row['nome']
        # pega caixa aberto do usuário (ou qualquer aberto como fallback)
        uid_venda = data.get('_uid')
        if uid_venda:
            c.execute("SELECT id FROM caixa WHERE status='aberto' AND usuario_id=? ORDER BY id DESC LIMIT 1", (int(uid_venda),))
            cx = c.fetchone()
            if not cx:
                c.execute("SELECT id FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
                cx = c.fetchone()
        else:
            c.execute("SELECT id FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
            cx = c.fetchone()
        caixa_id = cx['id'] if cx else None
        # IMPORTANTE: grava data_venda explicitamente em horário LOCAL (não usar
        # o DEFAULT CURRENT_TIMESTAMP do SQLite, que é UTC — isso causava vendas
        # feitas à noite "sumirem" dos filtros de data do dia e migrarem para o
        # caixa/dia seguinte).
        data_venda_local = data.get('_offline_at') or _agora()
        c.execute("""INSERT INTO vendas
            (data_venda,total,tipo_pagamento,observacao,cliente_id,cliente,caixa_id,
             entrega,entrega_nome,entrega_telefone,entrega_endereco,entrega_bairro,
             entrega_referencia,entrega_taxa,entrega_obs,
             tipo_atendimento,mesa,nome_cliente_mesa,nome_cliente_balcao,pagamentos_mix,
             desconto,gorjeta,cupom,cupom_desconto,status_mesa,offline_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data_venda_local,total,tipo_pag,observacao,cliente_id,cliente_nm,caixa_id,
             entrega,ent_nome,ent_tel,ent_end,ent_bairro,ent_ref,ent_taxa,ent_obs,
             tipo_atend,mesa,nome_cli_mesa,nome_cli_balcao,str(pags_mix) if pags_mix else '',
             desconto,gorjeta,cupom,cupom_desconto,
             'aberta' if tipo_atend in ('mesa','local') else 'fechada',
             offline_id))
        venda_id=c.lastrowid
        # Cartão bandeira e NSU
        cartao_b = data.get('cartao_bandeira','')
        cartao_n = data.get('cartao_nsu','')
        if cartao_b or cartao_n:
            c.execute("UPDATE vendas SET cartao_bandeira=?, cartao_nsu=? WHERE id=?", (cartao_b, cartao_n, venda_id))
        # Registra/atualiza mesa ativa
        if tipo_atend in ('mesa','local') and (mesa or nome_cli_mesa):
            mesa_key = mesa or nome_cli_mesa
            try:
                c.execute("INSERT OR IGNORE INTO mesas_ativas (mesa,nome_cliente,status,aberto_em) VALUES (?,?,?,?)",
                          (mesa_key, nome_cli_mesa or nome_cli_balcao, 'aberta', data_venda_local))
            except: pass
        # Incrementa uso do cupom
        if cupom:
            c.execute("UPDATE cupons SET usos=usos+1 WHERE codigo=?", (cupom,))
        for item in itens:
            desc_item = float(item.get('desconto_item',0) or 0)
            sub = item['quantidade']*item['preco_unitario'] - desc_item
            obs_item = item.get('observacao','')
            c.execute("INSERT INTO itens_venda (venda_id,produto_id,quantidade,preco_unitario,subtotal,observacao,desconto_item) VALUES (?,?,?,?,?,?,?)",
                      (venda_id,item['produto_id'],item['quantidade'],item['preco_unitario'],sub,obs_item,desc_item))
            c.execute("UPDATE produtos SET quantidade=quantidade-? WHERE id=?",
                      (item['quantidade'],item['produto_id']))
            c.execute("SELECT ingrediente_id,quantidade_usada FROM produto_ingredientes WHERE produto_id=?",(item['produto_id'],))
            for ing in c.fetchall():
                c.execute("UPDATE ingredientes SET quantidade=quantidade-? WHERE id=?",(ing['quantidade_usada']*item['quantidade'],ing['ingrediente_id']))
        if tipo_pag=='crediario':
            desc=f"Crediario Venda #{venda_id}"+(f" - {cliente_nm}" if cliente_nm else "")
            c.execute("INSERT INTO contas (tipo,descricao,valor,vencimento,status,cliente_id,cliente_fornecedor,categoria,venda_id) VALUES ('receber',?,?,?,'pendente',?,?,'Crediario',?)",
                      (desc,total,vencimento or _hoje(),cliente_id,cliente_nm,venda_id))
        else:
            c.execute("INSERT INTO financeiro (tipo,descricao,valor,categoria,pagamento,data_movimentacao) VALUES (?,?,?,?,?,?)",
                      ('entrada',f'Venda #{venda_id}',total,'Vendas',tipo_pag,data_venda_local[:10]))
        uid=data.get('_uid'); unome=data.get('_unome','Sistema')
        ent_info = f" 🛵 Entrega: {ent_nome} — {ent_end}" if entrega else ""
        _log(c, uid, unome, 'VENDA', 'PDV',
             f"Venda #{venda_id} — {fmt_val(total)} via {tipo_pag}{ent_info}" + (f" — {cliente_nm}" if cliente_nm else ""))
        # Credita fidelidade (cashback + pontos)
        if cliente_id:
            _creditar_fidelidade(c, cliente_id, venda_id, total)
        conn.commit(); conn.close()
        return {"venda_id":venda_id,"ok":True,"caixa_id":caixa_id}
    except Exception as e:
        conn.rollback(); conn.close(); return {"ok":False,"erro":str(e)}

def api_cancelar_venda(data):
    conn = get_connection(); c = conn.cursor()
    venda_id = int(data['id'])
    motivo   = data.get('motivo','').strip()
    uid      = data.get('_uid'); unome = data.get('_unome','Sistema')
    if not motivo: conn.close(); return {"ok":False,"erro":"Informe o motivo do cancelamento"}
    c.execute("SELECT * FROM vendas WHERE id=?", (venda_id,))
    venda = c.fetchone()
    if not venda: conn.close(); return {"ok":False,"erro":"Venda não encontrada"}
    venda = dict(venda)
    if venda.get('cancelada'): conn.close(); return {"ok":False,"erro":"Venda já cancelada"}
    if venda.get('descartada'): conn.close(); return {"ok":False,"erro":"Venda descartada não pode ser cancelada — ela nunca foi finalizada. Recupere-a no Histórico se precisar agir sobre ela."}
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Marca venda como cancelada
    c.execute("UPDATE vendas SET cancelada=1, motivo_cancelamento=?, cancelada_em=? WHERE id=?",
              (motivo, agora, venda_id))
    # Estorna o lançamento financeiro (se não crediário)
    if venda['tipo_pagamento'] != 'crediario':
        c.execute("SELECT id FROM financeiro WHERE descricao=?", (f"Venda #{venda_id}",))
        fin = c.fetchone()
        if fin:
            c.execute("DELETE FROM financeiro WHERE id=?", (fin['id'],))
        # Lança saída de estorno (data local, mesma lógica do fix de fuso horário)
        c.execute("INSERT INTO financeiro (tipo,descricao,valor,categoria,pagamento,data_movimentacao) VALUES (?,?,?,?,?,?)",
                  ('saida', f"Cancelamento Venda #{venda_id} — {motivo}", venda['total'], 'Cancelamento', venda['tipo_pagamento'], _hoje()))
    # Se crediário, cancela a conta a receber gerada
    else:
        c.execute("UPDATE contas SET status='cancelado' WHERE venda_id=? AND status='pendente'", (venda_id,))
    # Devolve estoque
    c.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id=?", (venda_id,))
    for item in c.fetchall():
        c.execute("UPDATE produtos SET quantidade=quantidade+? WHERE id=?", (item['quantidade'], item['produto_id']))
    _log(c, uid, unome, 'CANCELAR_VENDA', 'PDV',
         f"Venda #{venda_id} cancelada — {fmt_val(venda['total'])} — Motivo: {motivo}")
    conn.commit(); conn.close()
    return {"ok":True}

def api_descartar_venda(data):
    """
    Salva o carrinho como 'venda descartada' antes de ser limpo pelo botão
    'Nova Venda'. Não baixa estoque, não lança financeiro e não conta em
    nenhum relatório/fechamento de caixa — fica disponível apenas no
    Histórico (e na aba Entregas, se tinha dados de entrega) para que o
    operador possa recuperá-la e finalizar depois.
    """
    conn = get_connection(); c = conn.cursor()
    try:
        itens = data.get('itens') or []
        if not itens:
            conn.close(); return {"ok":False,"erro":"Carrinho vazio, nada para descartar"}
        total = float(data.get('total', 0) or 0)
        tipo_atend = data.get('tipo_atendimento','balcao')
        entrega = 1 if data.get('entrega') else 0
        agora = _agora()
        uid = data.get('_uid'); unome = data.get('_unome','Sistema')

        # Vincula ao caixa aberto do usuário só como referência informativa —
        # todas as somas de caixa/relatório já excluem descartada=1.
        cx = None
        if uid:
            c.execute("SELECT id FROM caixa WHERE status='aberto' AND usuario_id=? ORDER BY id DESC LIMIT 1", (int(uid),))
            cx = c.fetchone()
        caixa_id = cx['id'] if cx else None

        carrinho_json = json.dumps(itens, ensure_ascii=False)

        c.execute("""INSERT INTO vendas
            (data_venda,total,tipo_pagamento,observacao,cliente_id,cliente,caixa_id,
             entrega,entrega_nome,entrega_telefone,entrega_endereco,entrega_bairro,
             entrega_referencia,entrega_taxa,entrega_obs,
             tipo_atendimento,mesa,nome_cliente_mesa,nome_cliente_balcao,
             descartada,descartada_em,carrinho_json,status_mesa)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (agora, total, data.get('tipo_pagamento','dinheiro'), data.get('observacao',''),
             data.get('cliente_id'), data.get('cliente',''), caixa_id,
             entrega, data.get('entrega_nome',''), data.get('entrega_telefone',''),
             data.get('entrega_endereco',''), data.get('entrega_bairro',''),
             data.get('entrega_referencia',''), float(data.get('entrega_taxa',0) or 0),
             data.get('entrega_obs',''),
             tipo_atend, data.get('mesa',''), data.get('nome_cliente_mesa',''),
             data.get('nome_cliente_balcao',''),
             1, agora, carrinho_json, 'fechada'))
        venda_id = c.lastrowid
        qtd_itens = sum(int(i.get('quantidade',0) or 0) for i in itens)
        _log(c, uid, unome, 'DESCARTAR_VENDA', 'PDV',
             f"Venda #{venda_id} descartada ao clicar em Nova Venda — {qtd_itens} item(ns), {fmt_val(total)}")
        conn.commit(); conn.close()
        return {"ok":True, "venda_id":venda_id}
    except Exception as e:
        conn.rollback(); conn.close(); return {"ok":False,"erro":str(e)}

def api_recuperar_venda(data):
    """Reabre uma venda descartada, devolvendo o carrinho para o PDV."""
    conn = get_connection(); c = conn.cursor()
    venda_id = int(data['id'])
    uid = data.get('_uid'); unome = data.get('_unome','Sistema')
    c.execute("SELECT * FROM vendas WHERE id=?", (venda_id,))
    venda = c.fetchone()
    if not venda: conn.close(); return {"ok":False,"erro":"Venda não encontrada"}
    venda = dict(venda)
    if not venda.get('descartada'):
        conn.close(); return {"ok":False,"erro":"Esta venda não está descartada"}
    if venda.get('recuperada'):
        conn.close(); return {"ok":False,"erro":"Esta venda já foi recuperada anteriormente"}
    agora = _agora()
    c.execute("UPDATE vendas SET recuperada=1, recuperada_em=? WHERE id=?", (agora, venda_id))
    _log(c, uid, unome, 'RECUPERAR_VENDA', 'PDV', f"Venda #{venda_id} recuperada do histórico de descartadas")
    conn.commit(); conn.close()
    try: itens = json.loads(venda.get('carrinho_json') or '[]')
    except Exception: itens = []
    return {
        "ok": True,
        "itens": itens,
        "tipo_pagamento": venda.get('tipo_pagamento','dinheiro'),
        "tipo_atendimento": venda.get('tipo_atendimento','balcao'),
        "cliente_id": venda.get('cliente_id'),
        "cliente": venda.get('cliente',''),
        "observacao": venda.get('observacao',''),
        "entrega": bool(venda.get('entrega')),
        "entrega_nome": venda.get('entrega_nome',''),
        "entrega_telefone": venda.get('entrega_telefone',''),
        "entrega_endereco": venda.get('entrega_endereco',''),
        "entrega_bairro": venda.get('entrega_bairro',''),
        "entrega_referencia": venda.get('entrega_referencia',''),
        "entrega_taxa": venda.get('entrega_taxa',0),
        "entrega_obs": venda.get('entrega_obs',''),
        "mesa": venda.get('mesa',''),
        "nome_cliente_mesa": venda.get('nome_cliente_mesa',''),
        "nome_cliente_balcao": venda.get('nome_cliente_balcao',''),
    }


# ─────────────────────────────────────────────
# CARDÁPIO ONLINE
# ─────────────────────────────────────────────
def _gerar_pagina_cardapio():
    """Gera HTML da página pública do cardápio — estilo iFood."""
    d = api_cardapio_publico()
    if not d.get("ativo"):
        return "<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>Cardápio indisponível no momento.</h2></body></html>"
    cfg   = d.get("config", {})
    prods = d.get("produtos", [])
    cor   = cfg.get("cor_primaria","#e67e22")
    titulo= cfg.get("titulo","Nosso Cardápio")
    msg   = cfg.get("mensagem","")
    endereco = cfg.get("endereco","")
    telefone = cfg.get("telefone","")
    horario  = cfg.get("horario","")
    instagram = cfg.get("instagram","")
    pedido_min = cfg.get("pedido_minimo",0)
    logo_b64   = cfg.get("logo","")
    if logo_b64 and not logo_b64.startswith('data:'):
        logo_b64 = ""
    show_preco   = cfg.get("exibir_preco",1)
    show_estoque = cfg.get("exibir_estoque",0)
    destaques = [p for p in prods if p.get("favorito")]
    cats = {}; cat_list = []
    for p in prods:
        c = p.get("cat_nome") or p.get("categoria","Outros")
        if c not in cats: cat_list.append(c)
        cats.setdefault(c,[]).append(p)
    cat_nav = ''.join(f'<a href="#cat-{i}" class="cn" onclick="selCat(this)">{c}</a>' for i,c in enumerate(cat_list))
    # Info da loja
    info_parts = []
    if endereco: info_parts.append(f'<div class="si"><span class="si-i">📍</span>{endereco}</div>')
    if horario:  info_parts.append(f'<div class="si"><span class="si-i">🕐</span>{horario}</div>')
    if telefone: info_parts.append(f'<div class="si"><span class="si-i">📞</span><a href="https://wa.me/55{telefone.replace("-","").replace(" ","").replace("(","").replace(")","")}" style="color:{cor};text-decoration:none;font-weight:600">{telefone}</a></div>')
    if pedido_min and pedido_min>0: info_parts.append(f'<div class="si"><span class="si-i">💰</span>Pedido mínimo R$ {pedido_min:.2f}'.replace(".",",")+("</div>"))
    info_html = ''.join(info_parts)
    # Produtos
    items_html = ""
    def _card(p):
        promo = p.get("promo")
        img_b64 = p.get("imagem_base64","")
        desc = p.get("descricao","") or ""
        ings = p.get("ingredientes",[])
        if img_b64:
            img_html = f'<img src="{img_b64}" alt="{p["nome"]}" class="pi">'
        else:
            emojis_map={'Lanches':'🍔','Bebidas':'🥤','Porções':'🍟','Frituras':'🥐','Sobremesas':'🍰','Outros':'🍽️'}
            emoji = emojis_map.get(p.get("categoria",""),"🍽️")
            img_html = f'<div class="pi pi-e">{emoji}</div>'
        preco_html = ""
        if show_preco:
            if promo:
                po = f'R$ {p["preco"]:.2f}'.replace(".",",")
                pp = f'R$ {promo["preco_promo"]:.2f}'.replace(".",",")
                preco_html = f'<div class="pp"><s>{po}</s> <strong>{pp}</strong></div>'
            else:
                preco_html = f'<div class="pp">{("R$ "+f"{p['preco']:.2f}").replace(".",",")}</div>'
        ings_html = '<div class="ig">'+''.join(f'<span>{x}</span>' for x in ings[:5])+'</div>' if ings else ""
        if not ings_html and desc:
            ings_html = f'<div class="pd">{desc[:80]}</div>'
        badge = '<span class="badge-promo">🔥 PROMOÇÃO</span>' if promo else ""
        fav = '<span class="badge-fav">⭐</span>' if p.get("favorito") else ""
        pid = p.get("id",0)
        preco_final = promo["preco_promo"] if promo else p["preco"]
        return f'''<div class="item" data-pid="{pid}" data-pname="{p["nome"]}" data-pprice="{preco_final:.2f}">
          <div class="item-img">{img_html}{badge}{fav}
            <button class="add-btn" onclick="event.stopPropagation();addCart({pid},this)">+</button>
          </div>
          <div class="item-info">
            <div class="item-name">{p["nome"]}</div>
            {ings_html}
            {preco_html}
          </div>
        </div>'''
    if destaques:
        items_html += '<div class="sec" id="destaques"><div class="sec-t">⭐ Destaques</div><div class="sec-g">'
        for p in destaques: items_html += _card(p)
        items_html += '</div></div>'
    for i, cat in enumerate(cat_list):
        ps = cats[cat]
        items_html += f'<div class="sec" id="cat-{i}"><div class="sec-t">{cat} <span class="sec-c">{len(ps)}</span></div><div class="sec-g">'
        for p in ps: items_html += _card(p)
        items_html += '</div></div>'
    return f'''<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<title>{titulo}</title>
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{msg or 'Veja nosso cardápio completo!'}">
<meta property="og:type" content="website">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#f5f5f5;color:#333;-webkit-font-smoothing:antialiased}}
.hero{{background:linear-gradient(135deg,{cor},#222);padding:40px 20px 30px;text-align:center;color:#fff}}
.hero-emoji{{font-size:48px;margin-bottom:8px}}
.hero h1{{font-size:28px;font-weight:900;letter-spacing:-.5px}}
.hero-msg{{font-size:14px;opacity:.85;margin-top:8px}}
.store-card{{max-width:700px;margin:-20px auto 0;background:#fff;border-radius:16px;padding:20px 24px;box-shadow:0 4px 24px rgba(0,0,0,.1);position:relative;z-index:5}}
.store-info{{display:flex;flex-direction:column;gap:6px}}
.si{{display:flex;align-items:center;gap:8px;font-size:13px;color:#555}}
.si-i{{font-size:16px;flex-shrink:0}}
.si a{{color:{cor}}}
.search-box{{max-width:700px;margin:16px auto;padding:0 16px}}
.search-box input{{width:100%;padding:12px 16px 12px 44px;border:2px solid #eee;border-radius:12px;font-size:14px;outline:none;background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' fill='none' stroke='%23999' stroke-width='2'%3E%3Ccircle cx='9' cy='9' r='7'/%3E%3Cline x1='15' y1='15' x2='20' y2='20'/%3E%3C/svg%3E") 14px center no-repeat;transition:border .2s}}
.search-box input:focus{{border-color:{cor}}}
.cats{{max-width:700px;margin:0 auto;padding:0 16px;overflow-x:auto;display:flex;gap:8px;-webkit-overflow-scrolling:touch;position:sticky;top:0;z-index:10;background:#f5f5f5;padding-top:12px;padding-bottom:12px}}
.cats::-webkit-scrollbar{{display:none}}
.cn{{flex-shrink:0;padding:8px 18px;border-radius:24px;background:#fff;color:#666;font-size:13px;font-weight:600;text-decoration:none;border:1.5px solid #eee;transition:all .2s;cursor:pointer}}
.cn:hover,.cn.act{{background:{cor};color:#fff;border-color:{cor}}}
.wrap{{max-width:700px;margin:0 auto;padding:0 16px 100px}}
.sec{{margin-top:28px}}
.sec-t{{font-size:20px;font-weight:800;color:#1a1a2e;margin-bottom:14px;display:flex;align-items:center;gap:8px}}
.sec-c{{font-size:12px;color:#999;font-weight:500}}
.sec-g{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}
.item{{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);transition:transform .15s;cursor:pointer;border:1px solid #f0f0f0}}
.item:active{{transform:scale(.97)}}
.item-img{{position:relative;width:100%;aspect-ratio:4/3;overflow:hidden;background:linear-gradient(135deg,#fef3c7,#fde68a)}}
.item-img .pi{{width:100%;height:100%;object-fit:cover;display:block}}
.item-img .pi-e{{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:48px}}
.badge-promo{{position:absolute;top:8px;left:8px;background:#e74c3c;color:#fff;font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;letter-spacing:.3px}}
.badge-fav{{position:absolute;top:8px;right:8px;font-size:18px}}
.item-info{{padding:10px 12px 14px}}
.item-name{{font-size:14px;font-weight:700;color:#1a1a2e;margin-bottom:4px;line-height:1.3}}
.pd{{font-size:11px;color:#888;line-height:1.3;margin-bottom:4px}}
.ig{{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:6px}}
.ig span{{font-size:10px;color:#888;background:#f5f5f5;padding:2px 6px;border-radius:8px}}
.pp{{font-size:16px;font-weight:800;color:{cor}}}
.pp s{{font-size:12px;color:#ccc;font-weight:400;margin-right:4px}}
.add-btn{{position:absolute;bottom:8px;right:8px;width:36px;height:36px;border-radius:50%;background:{cor};color:#fff;border:none;font-size:22px;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2);display:flex;align-items:center;justify-content:center;transition:transform .15s}}
.add-btn:active{{transform:scale(.85)}}
.cart-fab{{position:fixed;bottom:24px;right:20px;height:52px;border-radius:26px;background:{cor};color:#fff;border:none;font-size:15px;font-weight:700;cursor:pointer;box-shadow:0 4px 16px {cor}66;display:none;align-items:center;gap:8px;padding:0 20px 0 16px;z-index:40;transition:transform .15s}}
.cart-fab:active{{transform:scale(.95)}}
.cart-fab .cb{{background:#fff;color:{cor};font-size:12px;font-weight:800;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center}}
.share-fab{{position:fixed;bottom:24px;left:20px;width:48px;height:48px;border-radius:50%;background:#25D366;color:#fff;border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 12px rgba(37,211,102,.3);display:flex;align-items:center;justify-content:center;z-index:30}}
.drawer-bg{{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;display:none;opacity:0;transition:opacity .25s}}
.drawer-bg.open{{display:block;opacity:1}}
.drawer{{position:fixed;bottom:0;left:0;right:0;max-height:85vh;background:#fff;border-radius:20px 20px 0 0;z-index:51;transform:translateY(100%);transition:transform .3s ease;overflow-y:auto;padding:0 0 env(safe-area-inset-bottom)}}
.drawer.open{{transform:translateY(0)}}
.drawer-head{{padding:16px 20px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;background:#fff;z-index:2}}
.drawer-head h3{{font-size:18px;font-weight:800}}
.drawer-close{{width:36px;height:36px;border-radius:50%;border:none;background:#f5f5f5;font-size:18px;cursor:pointer}}
.drawer-items{{padding:12px 20px}}
.ci{{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f5f5f5}}
.ci-info{{flex:1;min-width:0}}
.ci-name{{font-size:14px;font-weight:600}}
.ci-price{{font-size:13px;color:{cor};font-weight:700}}
.ci-qty{{display:flex;align-items:center;gap:8px}}
.ci-qty button{{width:30px;height:30px;border-radius:50%;border:1.5px solid #ddd;background:#fff;font-size:16px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center}}
.ci-qty span{{font-size:15px;font-weight:700;min-width:20px;text-align:center}}
.drawer-footer{{padding:16px 20px;border-top:1px solid #f0f0f0;position:sticky;bottom:0;background:#fff}}
.drawer-total{{display:flex;justify-content:space-between;font-size:16px;font-weight:800;margin-bottom:12px}}
.drawer-total span:last-child{{color:{cor}}}
.wpp-btn{{width:100%;padding:14px;border-radius:12px;border:none;background:#25D366;color:#fff;font-size:15px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px}}
.wpp-btn:active{{opacity:.9}}
.name-input{{width:100%;padding:10px 14px;border:1.5px solid #eee;border-radius:10px;font-size:14px;margin-bottom:10px;outline:none}}
.name-input:focus{{border-color:{cor}}}
footer{{text-align:center;padding:24px;font-size:11px;color:#bbb}}
@media(max-width:480px){{.sec-g{{grid-template-columns:1fr 1fr;gap:8px}}.store-card{{margin:- 14px 12px 0;padding:16px}}.hero{{padding:30px 16px 24px}}.hero h1{{font-size:22px}}}}
@media(max-width:360px){{.sec-g{{grid-template-columns:1fr}}}}
</style></head>
<body>
<div class="hero">
  {f'<img src="{logo_b64}" alt="Logo" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid rgba(255,255,255,.3);margin-bottom:8px">' if logo_b64 else '<div class="hero-emoji">🍔</div>'}
  <h1>{titulo}</h1>
  {f'<div class="hero-msg">{msg}</div>' if msg else ''}
</div>
{f'<div class="store-card"><div class="store-info">{info_html}</div></div>' if info_html else ''}
<div class="search-box"><input type="text" id="busca" placeholder="Buscar no cardápio..." oninput="filtrar(this.value)"></div>
<div class="cats" id="cats-bar">{cat_nav}</div>
<div class="wrap" id="items-wrap">
  {items_html if items_html else '<p style="text-align:center;padding:60px 20px;color:#bbb">Nenhum produto disponível.</p>'}
</div>
<button class="cart-fab" id="cartFab" onclick="openDrawer()">🛒 Ver pedido <span class="cb" id="cartCount">0</span></button>
<button class="share-fab" onclick="sharePage()" title="Compartilhar">📤</button>
<div class="drawer-bg" id="drawerBg" onclick="closeDrawer()"></div>
<div class="drawer" id="drawer">
  <div class="drawer-head"><h3>🛒 Seu pedido</h3><button class="drawer-close" onclick="closeDrawer()">✕</button></div>
  <div class="drawer-items" id="cartItems"></div>
  <div class="drawer-footer">
    <div class="drawer-total"><span>Total</span><span id="cartTotal">R$ 0,00</span></div>
    <input class="name-input" id="custName" placeholder="Seu nome (opcional)">
    <button class="wpp-btn" onclick="sendWhatsApp()">💬 Enviar pedido via WhatsApp</button>
  </div>
</div>
<footer>Powered by Maná Food</footer>
<script>
var cart={{}},fone='{telefone.replace("-","").replace(" ","").replace("(","").replace(")","") if telefone else ""}',loja='{titulo}';
function fmt(v){{return'R$ '+(+v).toFixed(2).replace('.',',')}}
function addCart(id,btn){{
  var el=btn.closest('.item');
  var n=el.dataset.pname,p=parseFloat(el.dataset.pprice);
  if(!cart[id])cart[id]={{name:n,price:p,qty:0}};
  cart[id].qty++;
  btn.textContent='✓';btn.style.background='#16a34a';
  setTimeout(function(){{btn.textContent='+';btn.style.background='{cor}'}},400);
  updCart();
}}
function updCart(){{
  var items=Object.keys(cart),total=0,qtd=0;
  var fab=document.getElementById('cartFab');
  var cnt=document.getElementById('cartCount');
  items.forEach(function(k){{total+=cart[k].price*cart[k].qty;qtd+=cart[k].qty}});
  if(qtd>0){{fab.style.display='flex';cnt.textContent=qtd}}else{{fab.style.display='none'}}
  var el=document.getElementById('cartItems');
  if(!items.length){{el.innerHTML='<p style="text-align:center;color:#999;padding:20px">Carrinho vazio</p>';}}
  else{{el.innerHTML=items.filter(function(k){{return cart[k].qty>0}}).map(function(k){{
    var it=cart[k];
    return'<div class="ci"><div class="ci-info"><div class="ci-name">'+it.name+'</div><div class="ci-price">'+fmt(it.price)+'</div></div><div class="ci-qty"><button onclick="chgQty('+k+',-1)">−</button><span>'+it.qty+'</span><button onclick="chgQty('+k+',1)">+</button></div></div>';
  }}).join('')}}
  document.getElementById('cartTotal').textContent=fmt(total);
}}
function chgQty(id,d){{
  if(!cart[id])return;
  cart[id].qty+=d;
  if(cart[id].qty<=0)delete cart[id];
  updCart();
}}
function openDrawer(){{
  document.getElementById('drawerBg').classList.add('open');
  document.getElementById('drawer').classList.add('open');
}}
function closeDrawer(){{
  document.getElementById('drawerBg').classList.remove('open');
  document.getElementById('drawer').classList.remove('open');
}}
function sendWhatsApp(){{
  var items=Object.keys(cart).filter(function(k){{return cart[k].qty>0}});
  if(!items.length){{alert('Adicione itens ao pedido!');return}}
  var nome=document.getElementById('custName').value.trim();
  var total=0;
  var txt='*🛒 NOVO PEDIDO — '+loja+'*\\n';
  if(nome)txt+='👤 Cliente: *'+nome+'*\\n';
  txt+='\\n';
  items.forEach(function(k){{
    var it=cart[k];
    var sub=it.price*it.qty;total+=sub;
    txt+=it.qty+'x '+it.name+' — '+fmt(sub)+'\\n';
  }});
  txt+='\\n*💰 Total: '+fmt(total)+'*\\n';
  txt+='\\n_Pedido enviado pelo cardápio digital_';
  var num=fone?'55'+fone:'';
  var url=num?'https://wa.me/'+num+'?text='+encodeURIComponent(txt):'https://wa.me/?text='+encodeURIComponent(txt);
  window.open(url,'_blank');
}}
function sharePage(){{
  var u=window.location.href,t=loja+' — veja nosso cardápio!\\n'+u;
  if(navigator.share)navigator.share({{title:loja,text:'Confira nosso cardápio!',url:u}}).catch(function(){{}});
  else window.open('https://wa.me/?text='+encodeURIComponent(t),'_blank');
}}
function selCat(el){{
  document.querySelectorAll('.cn').forEach(function(c){{c.classList.remove('act')}});
  el.classList.add('act');
}}
function filtrar(q){{
  q=q.toLowerCase();
  document.querySelectorAll('.item').forEach(function(it){{
    var nome=it.querySelector('.item-name').textContent.toLowerCase();
    it.style.display=nome.includes(q)?'':'none';
  }});
}}
</script>
</body></html>'''


def api_cardapio_publico():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM cardapio_config LIMIT 1")
    cfg = c.fetchone()
    cfg = dict(cfg) if cfg else {"ativo":1,"titulo":"Nosso Cardápio","cor_primaria":"#e67e22","exibir_preco":1}
    if not cfg.get("ativo"):
        conn.close(); return {"ativo":False}
    c.execute("SELECT p.*,cat.nome as cat_nome FROM produtos p LEFT JOIN categorias cat ON p.categoria=cat.nome WHERE p.ativo=1 AND p.quantidade>0 ORDER BY p.favorito DESC,cat.nome,p.nome")
    prods = [dict(r) for r in c.fetchall()]
    # Busca promoções ativas hoje
    hoje = _hoje()
    c.execute("""SELECT produto_id, preco_promo, tipo, valor, descricao
                 FROM promocoes WHERE ativo=1 AND ? BETWEEN data_inicio AND data_fim""", (hoje,))
    promos_map = {}
    for pr in c.fetchall():
        pr = dict(pr)
        promos_map[pr['produto_id']] = pr
    for p in prods:
        c.execute("SELECT i.nome FROM produto_ingredientes pi JOIN ingredientes i ON pi.ingrediente_id=i.id WHERE pi.produto_id=? AND i.ativo=1 ORDER BY i.nome",(p['id'],))
        p['ingredientes'] = [r['nome'] for r in c.fetchall()]
        # Imagem base64
        if p.get('imagem'):
            fpath = IMG_DIR / p['imagem']
            if fpath.exists():
                ext = p['imagem'].split('.')[-1]
                mime = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
                p['imagem_base64'] = f"data:{mime};base64,{base64.b64encode(fpath.read_bytes()).decode()}"
            else:
                p['imagem_base64'] = ''
        else:
            p['imagem_base64'] = ''
        # Promoção ativa
        if p['id'] in promos_map:
            p['promo'] = promos_map[p['id']]
    conn.close()
    return {"ativo":True,"config":cfg,"produtos":prods}

def api_salvar_cardapio_config(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM cardapio_config")
    c.execute("""INSERT INTO cardapio_config (ativo,titulo,cor_primaria,exibir_preco,exibir_estoque,mensagem,
                 endereco,telefone,horario,instagram,pedido_minimo,logo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (int(data.get("ativo",1)), data.get("titulo","Nosso Cardápio"),
               data.get("cor_primaria","#e67e22"), int(data.get("exibir_preco",1)),
               int(data.get("exibir_estoque",0)), data.get("mensagem",""),
               data.get("endereco",""), data.get("telefone",""), data.get("horario",""),
               data.get("instagram",""), float(data.get("pedido_minimo",0) or 0),
               data.get("logo","")))
    conn.commit(); conn.close()
    _auto_publicar_cardapio()
    return {"ok":True}

# ─────────────────────────────────────────────
# BACKUP AUTOMÁTICO
# ─────────────────────────────────────────────
import shutil as _shutil
def api_fazer_backup(data=None):
    import datetime as _dt, shutil as _sh
    ts   = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    src  = str(DB_PATH)
    bdir = str(BASE_DIR / "backups")
    try:
        os.makedirs(bdir, exist_ok=True)
        if not os.path.exists(src):
            return {"ok":False,"erro":f"Banco não encontrado: {src}"}
        dst = os.path.join(bdir, f"backup_{ts}.db")
        _sh.copy2(src, dst)
        baks = sorted([f for f in os.listdir(bdir) if f.endswith('.db')])
        for _old in baks[:-30]:
            try: os.remove(os.path.join(bdir, _old))
            except: pass
        return {"ok":True,"arquivo":f"backup_{ts}.db","total":len(baks)}
    except Exception as e:
        return {"ok":False,"erro":str(e)}

def api_restaurar_backup(data):
    """Restaura o banco de dados a partir de um backup."""
    import shutil as _sh, datetime as _dt
    arquivo = data.get("arquivo","")
    if not arquivo or not arquivo.endswith('.db'):
        return {"ok":False,"erro":"Arquivo inválido"}
    # Segurança: não permite path traversal
    if '/' in arquivo or '\\' in arquivo or '..' in arquivo:
        return {"ok":False,"erro":"Nome de arquivo inválido"}
    bdir = str(BASE_DIR / "backups")
    src  = os.path.join(bdir, arquivo)
    if not os.path.exists(src):
        return {"ok":False,"erro":"Arquivo de backup não encontrado"}
    dst  = str(DB_PATH)
    # Faz backup do banco atual antes de restaurar
    ts   = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    pre  = os.path.join(bdir, f"pre_restauracao_{ts}.db")
    try:
        _sh.copy2(dst, pre)   # salva banco atual
        _sh.copy2(src, dst)   # restaura o backup
        return {"ok":True,"msg":f"Banco restaurado! Backup anterior salvo como pre_restauracao_{ts}.db"}
    except Exception as e:
        return {"ok":False,"erro":str(e)}


def api_listar_backups():
    try:
        bdir = str(BASE_DIR / "backups")
        os.makedirs(bdir, exist_ok=True)
        baks = sorted([f for f in os.listdir(bdir) if f.endswith('.db')], reverse=True)
        return {"backups": baks, "pasta": bdir}
    except Exception as e:
        return {"backups": [], "erro": str(e)}

# ─────────────────────────────────────────────
# CUPONS DE DESCONTO
# ─────────────────────────────────────────────
def api_listar_cupons():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM cupons ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close(); return rows

def api_salvar_cupom(data):
    conn = get_connection(); c = conn.cursor()
    cid  = data.get("id")
    codigo = data.get("codigo","").strip().upper()
    tipo   = data.get("tipo","percentual")
    valor  = float(data.get("valor",0))
    ativo  = int(data.get("ativo",1))
    limite = int(data.get("limite_usos",0))
    if cid:
        validade = data.get("validade","") or None
        c.execute("UPDATE cupons SET codigo=?,tipo=?,valor=?,ativo=?,limite_usos=?,validade=? WHERE id=?",
                  (codigo,tipo,valor,ativo,limite,validade,cid))
    else:
        validade = data.get("validade","") or None
    c.execute("INSERT INTO cupons (codigo,tipo,valor,ativo,limite_usos,validade) VALUES (?,?,?,?,?,?)",
                  (codigo,tipo,valor,ativo,limite,validade))
    conn.commit(); conn.close(); return {"ok":True}

def api_validar_cupom(data):
    import datetime as _dt2
    conn = get_connection(); c = conn.cursor()
    codigo = data.get("codigo","").strip().upper()
    c.execute("SELECT * FROM cupons WHERE codigo=? AND ativo=1", (codigo,))
    row = c.fetchone()
    if not row: conn.close(); return {"ok":False,"erro":"Cupom inválido ou inativo"}
    row = dict(row)
    if row["limite_usos"]>0 and row["usos"]>=row["limite_usos"]:
        conn.close(); return {"ok":False,"erro":"Cupom esgotado"}
    # Verifica validade
    if row.get("validade"):
        hoje = _dt2.date.today().isoformat()
        if row["validade"] < hoje:
            conn.close(); return {"ok":False,"erro":f"Cupom vencido em {row['validade']}"}
    conn.close(); return {"ok":True,"cupom":row}

def api_excluir_cupom(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM cupons WHERE id=?", (data["id"],))
    conn.commit(); conn.close(); return {"ok":True}

# ─────────────────────────────────────────────
# META DIÁRIA
# ─────────────────────────────────────────────
def api_meta_diaria(params=None):
    params = params or {}
    data_ref = params.get("data", _hoje())
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM metas WHERE data=?", (data_ref,))
    meta = c.fetchone()
    meta_val = dict(meta)["meta_valor"] if meta else 0
    c.execute("SELECT COALESCE(SUM(total),0) AS total FROM vendas WHERE date(data_venda)=? AND cancelada=0 AND descartada=0", (data_ref,))
    faturado = c.fetchone()["total"]
    conn.close()
    return {"data":data_ref,"meta":meta_val,"faturado":faturado,
            "progresso":round(faturado/meta_val*100,1) if meta_val>0 else 0}

def api_salvar_meta(data):
    conn = get_connection(); c = conn.cursor()
    data_ref = data.get("data", _hoje())
    valor    = float(data.get("valor",0))
    c.execute("INSERT OR REPLACE INTO metas (data,meta_valor) VALUES (?,?)", (data_ref,valor))
    conn.commit(); conn.close(); return {"ok":True}

# ─────────────────────────────────────────────
# CMV - CUSTO DA MERCADORIA VENDIDA
# ─────────────────────────────────────────────
def api_relatorio_cmv(params=None):
    params = params or {}
    de  = params.get("de",  _hoje())
    ate = params.get("ate", _hoje())
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT p.nome, p.preco, p.custo,
                        SUM(iv.quantidade) AS qtd_vendida,
                        SUM(iv.subtotal) AS receita,
                        SUM(iv.quantidade * p.custo) AS custo_total
                 FROM itens_venda iv
                 JOIN vendas v ON iv.venda_id=v.id
                 JOIN produtos p ON iv.produto_id=p.id
                 WHERE date(v.data_venda)>=? AND date(v.data_venda)<=?
                   AND v.cancelada=0 AND v.descartada=0
                 GROUP BY p.id ORDER BY receita DESC""", (de, ate))
    rows = [dict(r) for r in c.fetchall()]
    for r in rows:
        r["margem"] = round((r["receita"]-r["custo_total"])/r["receita"]*100,1) if r["receita"]>0 else 0
        r["lucro"]  = round(r["receita"]-r["custo_total"],2)
    total_receita = sum(r["receita"] for r in rows)
    total_custo   = sum(r["custo_total"] for r in rows)
    conn.close()
    return {"itens":rows,"total_receita":total_receita,"total_custo":total_custo,
            "lucro_bruto":total_receita-total_custo,
            "margem_geral":round((total_receita-total_custo)/total_receita*100,1) if total_receita>0 else 0}

# ─────────────────────────────────────────────
# REPOSIÇÃO / LEMBRETE DE COMPRA
# ─────────────────────────────────────────────
def api_reposicao(params=None):
    params = params or {}
    dias = max(1, int(params.get('dias', 7)))
    conn = get_connection(); c = conn.cursor()
    c.execute("""
        SELECT p.id, p.nome, p.codigo, p.categoria, p.unidades, p.quantidade, p.preco, p.custo,
               COALESCE(SUM(iv.quantidade), 0) AS total_vendido
        FROM produtos p
        LEFT JOIN itens_venda iv ON iv.produto_id = p.id
            AND iv.venda_id IN (
                SELECT v.id FROM vendas v
                WHERE date(v.data_venda) >= date('now','localtime', ? || ' days')
                  AND v.cancelada = 0 AND v.descartada = 0
            )
        WHERE p.ativo = 1
        GROUP BY p.id
        ORDER BY p.quantidade ASC, total_vendido DESC
    """, (f'-{dias}',))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    for r in rows:
        media = round(r['total_vendido'] / dias, 1) if dias > 0 else 0
        r['media_diaria'] = media
        r['dias_restantes'] = round(r['quantidade'] / media, 1) if media > 0 else (999 if r['quantidade'] > 0 else 0)
        sugestao = round(media * dias - r['quantidade'])
        r['sugestao'] = max(0, sugestao)
        del r['total_vendido']
    zerados = sum(1 for r in rows if r['quantidade'] <= 0)
    baixos  = sum(1 for r in rows if 0 < r['quantidade'] <= 5)
    esgotam = sum(1 for r in rows if 0 < r['dias_restantes'] <= dias and r['dias_restantes'] != 999)
    # Ingredientes
    conn2 = get_connection(); c2 = conn2.cursor()
    c2.execute("""
        SELECT i.id,i.nome,i.unidade,i.quantidade,i.custo,i.estoque_minimo,
               COALESCE(SUM(pi.quantidade_usada * iv_total.total_vendido),0) AS consumo_total
        FROM ingredientes i
        LEFT JOIN produto_ingredientes pi ON pi.ingrediente_id=i.id
        LEFT JOIN (
            SELECT iv.produto_id, SUM(iv.quantidade) AS total_vendido
            FROM itens_venda iv JOIN vendas v ON v.id=iv.venda_id
            WHERE date(v.data_venda)>=date('now','localtime',? || ' days') AND v.cancelada=0 AND v.descartada=0
            GROUP BY iv.produto_id
        ) iv_total ON iv_total.produto_id=pi.produto_id
        WHERE i.ativo=1 GROUP BY i.id ORDER BY i.quantidade ASC
    """, (f'-{dias}',))
    ings = [dict(x) for x in c2.fetchall()]; conn2.close()
    for ig in ings:
        media = round(ig['consumo_total'] / dias, 1) if dias > 0 else 0
        ig['media_diaria'] = media
        ig['dias_restantes'] = round(ig['quantidade'] / media, 1) if media > 0 else (999 if ig['quantidade'] > 0 else 0)
        ig['sugestao'] = max(0, round(media * dias - ig['quantidade']))
        del ig['consumo_total']
    ing_zerados = sum(1 for ig in ings if ig['quantidade'] <= 0)
    ing_baixos  = sum(1 for ig in ings if 0 < ig['quantidade'] <= ig.get('estoque_minimo',5))
    return {"produtos": rows, "zerados": zerados, "baixos": baixos, "esgotam_em_breve": esgotam, "dias": dias,
            "ingredientes": ings, "ing_zerados": ing_zerados, "ing_baixos": ing_baixos}

# ─────────────────────────────────────────────
# PROMOÇÕES
# ─────────────────────────────────────────────

def api_listar_promocoes():
    """Lista todas as promoções com nome e preco original do produto."""
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT prom.*, p.nome AS produto_nome, p.preco AS preco_original
                 FROM promocoes prom
                 JOIN produtos p ON prom.produto_id = p.id
                 ORDER BY prom.data_fim DESC""")
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r


def api_salvar_promocao(data):
    """Cria ou atualiza uma promoção. Calcula preco_promo automaticamente."""
    conn = get_connection(); c = conn.cursor()
    try:
        produto_id = int(data['produto_id'])
        tipo       = data.get('tipo', 'percentual')
        valor      = float(data.get('valor', 0) or 0)
        data_inicio = data.get('data_inicio', _hoje())
        data_fim    = data.get('data_fim', _hoje())
        ativo       = int(data.get('ativo', 1))
        descricao   = data.get('descricao', '')

        # Busca preco do produto para calcular preco_promo
        c.execute("SELECT preco FROM produtos WHERE id=?", (produto_id,))
        row = c.fetchone()
        if not row:
            conn.close(); return {"ok": False, "erro": "Produto nao encontrado"}
        preco = float(row['preco'])

        if tipo == 'percentual':
            preco_promo = round(preco * (1 - valor / 100), 2)
        else:  # fixo
            preco_promo = round(preco - valor, 2)
        if preco_promo < 0:
            preco_promo = 0

        prom_id = data.get('id')
        if prom_id:
            c.execute("""UPDATE promocoes SET produto_id=?, tipo=?, valor=?, preco_promo=?,
                         data_inicio=?, data_fim=?, ativo=?, descricao=? WHERE id=?""",
                      (produto_id, tipo, valor, preco_promo, data_inicio, data_fim, ativo, descricao, int(prom_id)))
        else:
            c.execute("""INSERT INTO promocoes (produto_id, tipo, valor, preco_promo, data_inicio, data_fim, ativo, descricao)
                         VALUES (?,?,?,?,?,?,?,?)""",
                      (produto_id, tipo, valor, preco_promo, data_inicio, data_fim, ativo, descricao))
            prom_id = c.lastrowid
        conn.commit(); conn.close()
        _auto_publicar_cardapio()
        return {"ok": True, "id": prom_id, "preco_promo": preco_promo}
    except Exception as e:
        conn.rollback(); conn.close(); return {"ok": False, "erro": str(e)}


def api_excluir_promocao(data):
    """Remove uma promoção pelo id."""
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM promocoes WHERE id=?", (int(data['id']),))
    conn.commit(); conn.close()
    _auto_publicar_cardapio()
    return {"ok": True}


def api_promocoes_ativas():
    """Retorna promoções ativas na data de hoje."""
    hoje = _hoje()
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT prom.*, p.nome AS produto_nome, p.preco AS preco_original
                 FROM promocoes prom
                 JOIN produtos p ON prom.produto_id = p.id
                 WHERE prom.ativo = 1 AND ? BETWEEN prom.data_inicio AND prom.data_fim
                 ORDER BY p.nome""", (hoje,))
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r


# ─────────────────────────────────────────────
# FIDELIDADE (CASHBACK + PONTOS)
# ─────────────────────────────────────────────

def api_get_cashback_config():
    """Retorna configuração de cashback/pontos. Cria padrão se não existir."""
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM cashback_config LIMIT 1")
    row = c.fetchone()
    if not row:
        c.execute("""INSERT INTO cashback_config (id, cashback_ativo, cashback_percentual,
                     pontos_ativo, pontos_por_real, pontos_resgate_minimo, pontos_valor_resgate)
                     VALUES (1, 0, 5, 0, 1, 100, 10)""")
        conn.commit()
        c.execute("SELECT * FROM cashback_config LIMIT 1")
        row = c.fetchone()
    r = dict(row); conn.close(); return r


def api_salvar_cashback_config(data):
    """Salva configuração de cashback/pontos (DELETE + INSERT)."""
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM cashback_config")
    c.execute("""INSERT INTO cashback_config (id, cashback_ativo, cashback_percentual,
                 pontos_ativo, pontos_por_real, pontos_resgate_minimo, pontos_valor_resgate)
                 VALUES (1,?,?,?,?,?,?)""",
              (int(data.get('cashback_ativo', 0)),
               float(data.get('cashback_percentual', 5) or 5),
               int(data.get('pontos_ativo', 0)),
               float(data.get('pontos_por_real', 1) or 1),
               int(data.get('pontos_resgate_minimo', 100) or 100),
               float(data.get('pontos_valor_resgate', 10) or 10)))
    conn.commit(); conn.close()
    return {"ok": True}


def _creditar_fidelidade(c, cliente_id, venda_id, total):
    """Credita cashback e/ou pontos ao cliente após uma venda.
       O cursor `c` pertence à transação da venda chamadora."""
    c.execute("SELECT * FROM cashback_config LIMIT 1")
    cfg = c.fetchone()
    if not cfg:
        return
    cfg = dict(cfg)

    if cfg.get('cashback_ativo'):
        perc = float(cfg.get('cashback_percentual', 0))
        ganho = round(total * perc / 100, 2)
        if ganho > 0:
            c.execute("UPDATE clientes SET cashback_saldo = cashback_saldo + ? WHERE id=?", (ganho, cliente_id))
            c.execute("""INSERT INTO movimentos_fidelidade (cliente_id, tipo, valor, venda_id, descricao)
                         VALUES (?, 'cashback_ganho', ?, ?, ?)""",
                      (cliente_id, ganho, venda_id, f"Cashback {perc}% sobre venda #{venda_id}"))

    if cfg.get('pontos_ativo'):
        por_real = float(cfg.get('pontos_por_real', 1))
        import math
        pts = int(math.floor(total * por_real))
        if pts > 0:
            c.execute("UPDATE clientes SET pontos = pontos + ? WHERE id=?", (pts, cliente_id))
            c.execute("""INSERT INTO movimentos_fidelidade (cliente_id, tipo, pontos, venda_id, descricao)
                         VALUES (?, 'pontos_ganho', ?, ?, ?)""",
                      (cliente_id, pts, venda_id, f"+{pts} pontos pela venda #{venda_id}"))


def api_usar_cashback(data):
    """Usa cashback do saldo do cliente. data: {cliente_id, valor}"""
    conn = get_connection(); c = conn.cursor()
    try:
        cliente_id = int(data['cliente_id'])
        valor = round(float(data['valor']), 2)
        if valor <= 0:
            conn.close(); return {"ok": False, "erro": "Valor deve ser positivo"}
        c.execute("SELECT cashback_saldo FROM clientes WHERE id=?", (cliente_id,))
        row = c.fetchone()
        if not row:
            conn.close(); return {"ok": False, "erro": "Cliente nao encontrado"}
        saldo = float(row['cashback_saldo'])
        if valor > saldo:
            conn.close(); return {"ok": False, "erro": f"Saldo insuficiente (R$ {saldo:.2f})"}
        novo_saldo = round(saldo - valor, 2)
        c.execute("UPDATE clientes SET cashback_saldo = ? WHERE id=?", (novo_saldo, cliente_id))
        c.execute("""INSERT INTO movimentos_fidelidade (cliente_id, tipo, valor, descricao)
                     VALUES (?, 'cashback_usado', ?, ?)""",
                  (cliente_id, -valor, f"Cashback utilizado: -R$ {valor:.2f}"))
        conn.commit(); conn.close()
        return {"ok": True, "novo_saldo": novo_saldo}
    except Exception as e:
        conn.rollback(); conn.close(); return {"ok": False, "erro": str(e)}


def api_resgatar_pontos(data):
    """Resgata pontos do cliente convertendo em cashback. data: {cliente_id}"""
    conn = get_connection(); c = conn.cursor()
    try:
        cliente_id = int(data['cliente_id'])
        c.execute("SELECT * FROM cashback_config LIMIT 1")
        cfg = c.fetchone()
        if not cfg:
            conn.close(); return {"ok": False, "erro": "Configuracao de fidelidade nao encontrada"}
        cfg = dict(cfg)
        minimo = int(cfg.get('pontos_resgate_minimo', 100))
        valor_resgate = float(cfg.get('pontos_valor_resgate', 10))

        c.execute("SELECT pontos, cashback_saldo FROM clientes WHERE id=?", (cliente_id,))
        row = c.fetchone()
        if not row:
            conn.close(); return {"ok": False, "erro": "Cliente nao encontrado"}
        pontos_atual = int(row['pontos'])
        saldo_atual = float(row['cashback_saldo'])

        if pontos_atual < minimo:
            conn.close(); return {"ok": False, "erro": f"Pontos insuficientes (tem {pontos_atual}, minimo {minimo})"}

        novos_pontos = pontos_atual - minimo
        novo_saldo = round(saldo_atual + valor_resgate, 2)
        c.execute("UPDATE clientes SET pontos = ?, cashback_saldo = ? WHERE id=?",
                  (novos_pontos, novo_saldo, cliente_id))
        c.execute("""INSERT INTO movimentos_fidelidade (cliente_id, tipo, pontos, descricao)
                     VALUES (?, 'pontos_resgate', ?, ?)""",
                  (cliente_id, -minimo, f"Resgate de {minimo} pontos"))
        c.execute("""INSERT INTO movimentos_fidelidade (cliente_id, tipo, valor, descricao)
                     VALUES (?, 'cashback_resgate', ?, ?)""",
                  (cliente_id, valor_resgate, f"Credito de R$ {valor_resgate:.2f} por resgate de pontos"))
        conn.commit(); conn.close()
        return {"ok": True, "novo_saldo": novo_saldo, "novos_pontos": novos_pontos}
    except Exception as e:
        conn.rollback(); conn.close(); return {"ok": False, "erro": str(e)}


def api_extrato_fidelidade(cliente_id):
    """Retorna extrato de movimentos de fidelidade + saldo atual do cliente."""
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT cashback_saldo, pontos FROM clientes WHERE id=?", (cliente_id,))
    cli = c.fetchone()
    if not cli:
        conn.close(); return {"ok": False, "erro": "Cliente nao encontrado"}
    cli = dict(cli)
    c.execute("""SELECT * FROM movimentos_fidelidade WHERE cliente_id=? ORDER BY created_at DESC LIMIT 100""",
              (cliente_id,))
    movs = [dict(x) for x in c.fetchall()]
    conn.close()
    return {"ok": True, "cashback_saldo": cli['cashback_saldo'], "pontos": cli['pontos'], "movimentos": movs}


# ─────────────────────────────────────────────
# EMPRESA
# ─────────────────────────────────────────────
def api_get_empresa():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM empresa LIMIT 1")
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO empresa (id) VALUES (1)")
        conn.commit()
        c.execute("SELECT * FROM empresa LIMIT 1")
        row = c.fetchone()
    conn.close()
    return dict(row)

def api_salvar_empresa(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM empresa")
    c.execute("""INSERT INTO empresa (id,razao_social,nome_fantasia,cnpj,ie,im,
                 endereco,numero,bairro,cidade,uf,cep,telefone,email,regime_tributario,crt)
                 VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (data.get('razao_social',''), data.get('nome_fantasia',''),
               data.get('cnpj',''), data.get('ie',''), data.get('im',''),
               data.get('endereco',''), data.get('numero',''), data.get('bairro',''),
               data.get('cidade',''), data.get('uf',''), data.get('cep',''),
               data.get('telefone',''), data.get('email',''),
               data.get('regime_tributario','simples_nacional'), int(data.get('crt',1))))
    conn.commit(); conn.close()
    return {"ok": True}

# ─────────────────────────────────────────────
# CONFIG FISCAL
# ─────────────────────────────────────────────
def api_get_fiscal():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM config_fiscal LIMIT 1")
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO config_fiscal (id) VALUES (1)")
        conn.commit()
        c.execute("SELECT * FROM config_fiscal LIMIT 1")
        row = c.fetchone()
    conn.close()
    return dict(row)

def api_salvar_fiscal(data):
    conn = get_connection(); c = conn.cursor()
    # Keep certificado_arquivo if not provided
    c.execute("SELECT certificado_arquivo FROM config_fiscal LIMIT 1")
    old = c.fetchone()
    cert = data.get('certificado_arquivo', old['certificado_arquivo'] if old else '')
    c.execute("DELETE FROM config_fiscal")
    c.execute("""INSERT INTO config_fiscal (id,ambiente,serie_nfce,serie_nfe,csc_id,csc_token,
                 proximo_numero_nfce,proximo_numero_nfe,certificado_arquivo,certificado_senha)
                 VALUES (1,?,?,?,?,?,?,?,?,?)""",
              (int(data.get('ambiente',2)), int(data.get('serie_nfce',1)),
               int(data.get('serie_nfe',1)), data.get('csc_id',''), data.get('csc_token',''),
               int(data.get('proximo_numero_nfce',1)), int(data.get('proximo_numero_nfe',1)),
               cert, data.get('certificado_senha','')))
    conn.commit(); conn.close()
    return {"ok": True}

def api_upload_certificado(data):
    """Recebe certificado .pfx em base64 e salva na pasta."""
    cert_b64 = data.get('certificado','')
    senha = data.get('senha','')
    if not cert_b64:
        return {"ok": False, "erro": "Certificado não enviado"}
    try:
        cert_dir = Path(__file__).parent / 'lanchonete' / 'certificados'
        cert_dir.mkdir(parents=True, exist_ok=True)
        fname = 'certificado.pfx'
        import base64
        content = cert_b64.split(',')[1] if ',' in cert_b64 else cert_b64
        (cert_dir / fname).write_bytes(base64.b64decode(content))
        # Salva referência no config
        conn = get_connection(); c = conn.cursor()
        c.execute("UPDATE config_fiscal SET certificado_arquivo=?, certificado_senha=? WHERE id=1",
                  (fname, senha))
        conn.commit(); conn.close()
        return {"ok": True, "arquivo": fname}
    except Exception as e:
        return {"ok": False, "erro": str(e)}

# ─────────────────────────────────────────────
# IMPORTAÇÃO XML NFe
# ─────────────────────────────────────────────
def api_importar_xml(data):
    """Recebe XML de NFe em base64 ou texto, parseia e salva."""
    import xml.etree.ElementTree as ET
    xml_content = data.get('xml','')
    if not xml_content:
        return {"ok": False, "erro": "XML não enviado"}
    try:
        # Decode base64 if needed
        if xml_content.startswith('data:'):
            import base64
            xml_content = base64.b64decode(xml_content.split(',')[1]).decode('utf-8')

        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        root = ET.fromstring(xml_content)

        # Try to find infNFe
        inf = root.find('.//nfe:infNFe', ns)
        if inf is None:
            inf = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        if inf is None:
            # Try without namespace
            inf = root.find('.//infNFe')
        if inf is None:
            return {"ok": False, "erro": "XML inválido - não encontrou infNFe"}

        # Chave de acesso
        chave = inf.get('Id','').replace('NFe','')

        # Emitente
        emit = inf.find('nfe:emit', ns) or inf.find('{http://www.portalfiscal.inf.br/nfe}emit')
        fornecedor = ''
        cnpj_forn = ''
        if emit is not None:
            xNome = emit.find('nfe:xNome', ns) or emit.find('{http://www.portalfiscal.inf.br/nfe}xNome')
            cnpjEl = emit.find('nfe:CNPJ', ns) or emit.find('{http://www.portalfiscal.inf.br/nfe}CNPJ')
            if cnpjEl is None:
                cnpjEl = emit.find('nfe:CPF', ns) or emit.find('{http://www.portalfiscal.inf.br/nfe}CPF')
            fornecedor = xNome.text if xNome is not None else ''
            cnpj_forn = cnpjEl.text if cnpjEl is not None else ''

        # Data emissão
        ide = inf.find('nfe:ide', ns) or inf.find('{http://www.portalfiscal.inf.br/nfe}ide')
        data_emissao = ''
        if ide is not None:
            dhEmi = ide.find('nfe:dhEmi', ns) or ide.find('{http://www.portalfiscal.inf.br/nfe}dhEmi')
            if dhEmi is not None:
                data_emissao = dhEmi.text[:10] if dhEmi.text else ''

        # Valor total
        total_el = inf.find('.//nfe:vNF', ns) or inf.find('.//{http://www.portalfiscal.inf.br/nfe}vNF')
        valor_total = float(total_el.text) if total_el is not None else 0

        # Salva entrada
        conn = get_connection(); c = conn.cursor()

        # Verifica duplicata
        if chave:
            c.execute("SELECT id FROM entradas_xml WHERE chave_acesso=?", (chave,))
            if c.fetchone():
                conn.close()
                return {"ok": False, "erro": "XML já importado (chave duplicada)"}

        c.execute("""INSERT INTO entradas_xml (chave_acesso,fornecedor,cnpj_fornecedor,data_emissao,valor_total,xml_conteudo)
                     VALUES (?,?,?,?,?,?)""",
                  (chave, fornecedor, cnpj_forn, data_emissao, valor_total, xml_content))
        entrada_id = c.lastrowid

        # Parseia itens (det)
        itens = []
        dets = inf.findall('nfe:det', ns) or inf.findall('{http://www.portalfiscal.inf.br/nfe}det')
        for det in dets:
            prod = det.find('nfe:prod', ns) or det.find('{http://www.portalfiscal.inf.br/nfe}prod')
            if prod is None: continue

            def _txt(el, tag):
                child = el.find('nfe:'+tag, ns) or el.find('{http://www.portalfiscal.inf.br/nfe}'+tag)
                return child.text if child is not None else ''

            item = {
                'codigo': _txt(prod,'cProd'),
                'descricao': _txt(prod,'xProd'),
                'ncm': _txt(prod,'NCM'),
                'cfop': _txt(prod,'CFOP'),
                'unidade': _txt(prod,'uCom'),
                'quantidade': float(_txt(prod,'qCom') or 0),
                'valor_unitario': float(_txt(prod,'vUnCom') or 0),
                'valor_total': float(_txt(prod,'vProd') or 0),
            }
            c.execute("""INSERT INTO itens_entrada_xml (entrada_id,codigo,descricao,ncm,cfop,unidade,quantidade,valor_unitario,valor_total)
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                      (entrada_id, item['codigo'], item['descricao'], item['ncm'], item['cfop'],
                       item['unidade'], item['quantidade'], item['valor_unitario'], item['valor_total']))
            item['id'] = c.lastrowid
            itens.append(item)

        conn.commit(); conn.close()
        return {"ok": True, "entrada_id": entrada_id, "fornecedor": fornecedor,
                "chave": chave, "valor_total": valor_total, "itens": itens, "qtd_itens": len(itens)}
    except ET.ParseError:
        return {"ok": False, "erro": "XML mal formado"}
    except Exception as e:
        return {"ok": False, "erro": str(e)}

def api_listar_entradas_xml():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM entradas_xml ORDER BY id DESC LIMIT 50")
    entradas = [dict(r) for r in c.fetchall()]
    for e in entradas:
        c.execute("SELECT * FROM itens_entrada_xml WHERE entrada_id=?", (e['id'],))
        e['itens'] = [dict(i) for i in c.fetchall()]
        del e['xml_conteudo']  # Don't send the full XML to frontend
    conn.close()
    return entradas

def api_vincular_item_xml(data):
    """Vincula item do XML a produto existente e dá entrada no estoque."""
    conn = get_connection(); c = conn.cursor()
    item_id = int(data['item_id'])
    produto_id = int(data['produto_id'])
    quantidade = float(data.get('quantidade', 0))

    c.execute("UPDATE itens_entrada_xml SET produto_id=? WHERE id=?", (produto_id, item_id))
    if quantidade > 0:
        c.execute("UPDATE produtos SET quantidade=quantidade+? WHERE id=?", (quantidade, produto_id))
    conn.commit(); conn.close()
    return {"ok": True}

def api_confirmar_entrada_xml(data):
    """Marca entrada como processada e dá entrada de todos os itens vinculados."""
    conn = get_connection(); c = conn.cursor()
    entrada_id = int(data['entrada_id'])
    c.execute("SELECT * FROM itens_entrada_xml WHERE entrada_id=? AND produto_id IS NOT NULL", (entrada_id,))
    itens = c.fetchall()
    for item in itens:
        c.execute("UPDATE produtos SET quantidade=quantidade+? WHERE id=?",
                  (item['quantidade'], item['produto_id']))
    c.execute("UPDATE entradas_xml SET processado=1 WHERE id=?", (entrada_id,))
    conn.commit(); conn.close()
    return {"ok": True, "itens_processados": len(itens)}

# ─────────────────────────────────────────────
# INGREDIENTES
# ─────────────────────────────────────────────
def api_listar_ingredientes():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM ingredientes WHERE ativo=1 ORDER BY nome")
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r

def api_cadastrar_ingrediente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO ingredientes (nome,unidade,quantidade,custo,estoque_minimo) VALUES (?,?,?,?,?)",
              (data['nome'].strip(), data.get('unidade','un'), float(data.get('quantidade',0) or 0),
               float(data.get('custo',0) or 0), float(data.get('estoque_minimo',5) or 5)))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return {"id": new_id, "ok": True}

def api_atualizar_ingrediente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE ingredientes SET nome=?,unidade=?,quantidade=?,custo=?,estoque_minimo=? WHERE id=?",
              (data['nome'].strip(), data.get('unidade','un'), float(data.get('quantidade',0) or 0),
               float(data.get('custo',0) or 0), float(data.get('estoque_minimo',5) or 5), int(data['id'])))
    conn.commit(); conn.close(); return {"ok": True}

def api_excluir_ingrediente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE ingredientes SET ativo=0 WHERE id=?", (int(data['id']),))
    conn.commit(); conn.close(); return {"ok": True}

def api_produto_ingredientes(produto_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT pi.id, pi.ingrediente_id, pi.quantidade_usada, i.nome, i.unidade
                 FROM produto_ingredientes pi JOIN ingredientes i ON pi.ingrediente_id=i.id
                 WHERE pi.produto_id=? AND i.ativo=1 ORDER BY i.nome""", (produto_id,))
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r

def api_vincular_ingrediente(data):
    conn = get_connection(); c = conn.cursor()
    pid = int(data['produto_id']); iid = int(data['ingrediente_id'])
    qtd = float(data.get('quantidade_usada', 1) or 1)
    c.execute("SELECT id FROM produto_ingredientes WHERE produto_id=? AND ingrediente_id=?", (pid, iid))
    if c.fetchone():
        c.execute("UPDATE produto_ingredientes SET quantidade_usada=? WHERE produto_id=? AND ingrediente_id=?", (qtd, pid, iid))
    else:
        c.execute("INSERT INTO produto_ingredientes (produto_id,ingrediente_id,quantidade_usada) VALUES (?,?,?)", (pid, iid, qtd))
    conn.commit(); conn.close(); return {"ok": True}

def api_desvincular_ingrediente(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM produto_ingredientes WHERE id=?", (int(data['id']),))
    conn.commit(); conn.close(); return {"ok": True}

# ─────────────────────────────────────────────
# FAVORITOS
# ─────────────────────────────────────────────
def api_toggle_favorito(data):
    conn = get_connection(); c = conn.cursor()
    pid  = int(data["id"])
    c.execute("SELECT favorito FROM produtos WHERE id=?", (pid,))
    row = c.fetchone()
    novo = 0 if (row and row["favorito"]) else 1
    c.execute("UPDATE produtos SET favorito=? WHERE id=?", (novo, pid))
    conn.commit(); conn.close()
    return {"ok":True,"favorito":novo}

# ─────────────────────────────────────────────
# MESAS — HISTÓRICO / COMANDA
# ─────────────────────────────────────────────
def api_mesa_historico(params=None):
    params = params or {}
    mesa = params.get("mesa","")
    if not mesa: return {"vendas":[]}
    conn = get_connection(); c = conn.cursor()
    # Inclui tipo_atendimento mesa E local
    c.execute("""SELECT v.*,
                 GROUP_CONCAT(p.nome||' x'||iv.quantidade, ', ') AS itens_str,
                 SUM(iv.subtotal) AS total_calculado
                 FROM vendas v
                 LEFT JOIN itens_venda iv ON iv.venda_id=v.id
                 LEFT JOIN produtos p ON p.id=iv.produto_id
                 WHERE (v.mesa=? OR v.nome_cliente_mesa=? OR
                        COALESCE(NULLIF(v.mesa,''), v.nome_cliente_mesa)=? OR
                        LOWER(v.mesa)=LOWER(?) OR LOWER(v.nome_cliente_mesa)=LOWER(?))
                   AND v.tipo_atendimento IN ('mesa','local')
                   AND v.cancelada=0 AND v.descartada=0
                   AND (v.status_mesa='aberta' OR v.status_mesa IS NULL OR v.status_mesa='')
                 GROUP BY v.id ORDER BY v.id DESC""", (mesa,mesa,mesa,mesa,mesa))
    vendas = [dict(r) for r in c.fetchall()]
    for v in vendas:
        c.execute("SELECT iv.*,p.nome FROM itens_venda iv JOIN produtos p ON iv.produto_id=p.id WHERE iv.venda_id=?", (v["id"],))
        v["itens"] = [dict(i) for i in c.fetchall()]
    total_mesa = sum(v["total"] for v in vendas)
    # Busca horário de abertura: tenta mesas_ativas, senão usa MIN(data_venda)
    c.execute("SELECT aberto_em FROM mesas_ativas WHERE mesa=?", (mesa,))
    ma = c.fetchone()
    if ma:
        aberto_em = dict(ma)["aberto_em"]
    elif vendas:
        # Usa o horário da primeira venda do dia como abertura (data local, não UTC)
        c.execute("SELECT MIN(data_venda) AS ab FROM vendas WHERE (mesa=? OR nome_cliente_mesa=?) AND cancelada=0 AND descartada=0 AND date(data_venda)=?", (mesa,mesa,_hoje()))
        row = c.fetchone()
        aberto_em = dict(row)["ab"] if row else None
    else:
        aberto_em = None
    conn.close()
    print(f'[COMANDA] mesa={mesa!r} vendas={len(vendas)} params={params}')
    return {"mesa":mesa,"vendas":vendas,"total_mesa":total_mesa,"qtd_pedidos":len(vendas),"aberto_em":aberto_em}

def api_fechar_mesa(data):
    """Fecha mesa: remove de mesas_ativas e cancela do grid (não cancela vendas)."""
    mesa = data.get("mesa","")
    if not mesa: return {"ok":False,"erro":"Mesa não informada"}
    conn = get_connection(); c = conn.cursor()
    tipo_pag = data.get("tipo_pagamento","dinheiro") or "dinheiro"
    try:
        # Remove da tabela de mesas ativas
        c.execute("DELETE FROM mesas_ativas WHERE mesa=?", (mesa,))
        # Atualiza pagamento e fecha todas as vendas da mesa
        c.execute("""UPDATE vendas SET status_mesa='fechada', mesa_historico='fechada',
                        tipo_pagamento=?
                     WHERE (mesa=? OR nome_cliente_mesa=?)
                       AND cancelada=0
                       AND descartada=0
                       AND (status_mesa='aberta' OR status_mesa IS NULL OR status_mesa='')""",
                  (tipo_pag, mesa, mesa))
        conn.commit()
    except Exception as e:
        conn.close(); return {"ok":False,"erro":str(e)}
    conn.close()
    return {"ok":True}


def api_mesas_ativas():
    """Lista todas as mesas com pedido hoje e não finalizadas."""
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT
                   COALESCE(NULLIF(v.mesa,''), v.nome_cliente_mesa) AS mesa,
                   v.nome_cliente_mesa,
                   v.tipo_atendimento,
                   MIN(v.data_venda) AS aberto_em,
                   COUNT(v.id) AS qtd_pedidos,
                   SUM(v.total) AS total_acumulado
                 FROM vendas v
                 WHERE v.tipo_atendimento IN ('mesa','local')
                   AND v.cancelada=0 AND v.descartada=0
                   AND (v.status_mesa='aberta' OR v.status_mesa IS NULL OR v.status_mesa='')
                   AND (v.mesa!='' OR v.nome_cliente_mesa!='')
                 GROUP BY COALESCE(NULLIF(v.mesa,''), v.nome_cliente_mesa)
                 ORDER BY aberto_em ASC""")
    mesas = [dict(r) for r in c.fetchall() if r['mesa']]
    conn.close()
    return {"mesas": mesas}

# ─────────────────────────────────────────────
# FIADO — salvar venda como crediário
# ─────────────────────────────────────────────
# Já suportado via tipo_pagamento='crediario' — nenhuma mudança necessária no server


def api_alterar_tipo_atendimento(data):
    """Altera o tipo de atendimento de uma venda existente."""
    conn = get_connection(); c = conn.cursor()
    vid  = int(data.get("id",0))
    tipo = data.get("tipo","")
    mesa = data.get("mesa","")
    nome_cliente_mesa = data.get("nome_cliente_mesa","")
    nome_cliente_balcao = data.get("nome_cliente_balcao","")
    if not vid or not tipo:
        conn.close(); return {"ok":False,"erro":"Dados inválidos"}
    valid = ('balcao','mesa','local','entrega')
    if tipo not in valid:
        conn.close(); return {"ok":False,"erro":"Tipo inválido"}
    c.execute("""UPDATE vendas SET tipo_atendimento=?,mesa=?,nome_cliente_mesa=?,nome_cliente_balcao=?
                 WHERE id=?""", (tipo,mesa,nome_cliente_mesa,nome_cliente_balcao,vid))
    _log(c,data.get('usuario_id',0),data.get('usuario',''),'EDITAR',f'Venda #{vid}',
         f'Tipo alterado para {tipo}')
    conn.commit(); conn.close()
    return {"ok":True}


def api_editar_venda(data):
    """Editar itens, observação ou nome do cliente de uma venda já lançada."""
    conn = get_connection(); c = conn.cursor()
    venda_id = int(data['id'])
    uid   = data.get('_uid'); unome = data.get('_unome','Sistema')
    c.execute("SELECT * FROM vendas WHERE id=?", (venda_id,))
    venda = c.fetchone()
    if not venda: conn.close(); return {"ok":False,"erro":"Venda não encontrada"}
    venda = dict(venda)
    if venda.get('cancelada'): conn.close(); return {"ok":False,"erro":"Venda cancelada não pode ser editada"}
    if venda.get('descartada'): conn.close(); return {"ok":False,"erro":"Venda descartada não pode ser editada — ela nunca foi finalizada. Recupere-a no Histórico para editar o pedido normalmente."}

    antes = {
        "observacao": venda.get('observacao',''),
        "nome_cliente_balcao": venda.get('nome_cliente_balcao',''),
        "nome_cliente_mesa": venda.get('nome_cliente_mesa',''),
        "total": venda.get('total',0),
    }

    # Campos editáveis simples
    observacao = data.get('observacao', venda.get('observacao',''))
    nome_cli_balcao = data.get('nome_cliente_balcao', venda.get('nome_cliente_balcao',''))
    nome_cli_mesa   = data.get('nome_cliente_mesa',   venda.get('nome_cliente_mesa',''))

    updates = []
    campos  = []

    # Itens: se enviados, recalcula
    novos_itens = data.get('itens')
    if novos_itens is not None:
        # Devolve estoque dos itens antigos
        c.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id=?", (venda_id,))
        for it in c.fetchall():
            c.execute("UPDATE produtos SET quantidade=quantidade+? WHERE id=?", (it['quantidade'], it['produto_id']))
        # Remove itens antigos
        c.execute("DELETE FROM itens_venda WHERE venda_id=?", (venda_id,))
        # Insere novos
        novo_total = 0
        for item in novos_itens:
            desc_item = float(item.get('desconto_item',0) or 0)
            sub = item['quantidade'] * item['preco_unitario'] - desc_item
            novo_total += sub
            c.execute("INSERT INTO itens_venda (venda_id,produto_id,quantidade,preco_unitario,subtotal,observacao,desconto_item) VALUES (?,?,?,?,?,?,?)",
                      (venda_id, item['produto_id'], item['quantidade'], item['preco_unitario'], sub, item.get('observacao',''), desc_item))
            c.execute("UPDATE produtos SET quantidade=quantidade-? WHERE id=?", (item['quantidade'], item['produto_id']))
        updates.append("total=?"); campos.append(novo_total)
        antes["novo_total"] = novo_total
    else:
        novo_total = venda.get('total',0)

    updates += ["observacao=?","nome_cliente_balcao=?","nome_cliente_mesa=?"]
    campos  += [observacao, nome_cli_balcao, nome_cli_mesa, venda_id]
    c.execute(f"UPDATE vendas SET {','.join(updates)} WHERE id=?", campos)

    # Se o total mudou, atualiza também o lançamento de entrada no financeiro
    # (sem isso, o financeiro ficava com o valor antigo da venda, divergindo
    # do total real). Crediário não gera lançamento direto em financeiro
    # (gera uma conta a receber), então fica de fora dessa correção.
    if novos_itens is not None and novo_total != antes['total'] and venda['tipo_pagamento'] != 'crediario':
        c.execute("UPDATE financeiro SET valor=? WHERE descricao=? AND tipo='entrada'",
                  (novo_total, f"Venda #{venda_id}"))

    depois = {
        "observacao": observacao,
        "nome_cliente_balcao": nome_cli_balcao,
        "nome_cliente_mesa": nome_cli_mesa,
        "total": novo_total,
    }

    _log(c, uid, unome, 'EDITAR_VENDA', 'PDV',
         f"Venda #{venda_id} editada — novo total: {fmt_val(novo_total)}",
         antes=str(antes), depois=str(depois))
    conn.commit(); conn.close()
    return {"ok":True}


def api_listar_entregas(params=None):
    """Lista vendas do tipo entrega com filtro de data e status.
    Inclui também vendas DESCARTADAS que eram do tipo entrega (carrinho perdido
    no botão Nova Venda), para que o operador possa recuperá-las — mas elas não
    contam nas métricas de receita/pendentes, já que não são vendas reais."""
    conn = get_connection(); c = conn.cursor()
    params = params or {}
    date_de  = params.get('de',  _hoje())
    date_ate = params.get('ate', _hoje())
    status   = params.get('status','')

    sql = """SELECT * FROM vendas
             WHERE tipo_atendimento='entrega' AND cancelada=0
             AND date(data_venda)>=? AND date(data_venda)<=?"""
    args = [date_de, date_ate]
    if status:
        sql += " AND status_entrega=?"; args.append(status)
    sql += " ORDER BY id DESC"

    c.execute(sql, args)
    vendas = [dict(v) for v in c.fetchall()]
    for v in vendas:
        if v.get('descartada'):
            try: v['itens'] = json.loads(v.get('carrinho_json') or '[]')
            except Exception: v['itens'] = []
        else:
            c.execute("SELECT iv.*,p.nome FROM itens_venda iv JOIN produtos p ON iv.produto_id=p.id WHERE iv.venda_id=?", (v['id'],))
            v['itens'] = [dict(i) for i in c.fetchall()]

    ativas           = [v for v in vendas if not v.get('descartada')]
    total_entregas   = len(ativas)
    pendentes        = sum(1 for v in ativas if (v.get('status_entrega') or 'pendente') == 'pendente')
    separadas        = sum(1 for v in ativas if (v.get('status_entrega') or '') == 'separado')
    saiu             = sum(1 for v in ativas if (v.get('status_entrega') or '') == 'saiu')
    entregues        = sum(1 for v in ativas if (v.get('status_entrega') or '') == 'entregue')
    desistiu         = sum(1 for v in ativas if (v.get('status_entrega') or '') == 'desistiu')
    receita          = sum(v.get('total',0) for v in ativas)
    conn.close()
    return {
        "entregas": vendas,
        "total": total_entregas,
        "pendentes": pendentes,
        "separadas": separadas,
        "saiu": saiu,
        "entregues": entregues,
        "desistiu": desistiu,
        "receita": receita,
    }


def api_atualizar_status_entrega(data):
    """Atualiza o status de entrega de uma venda."""
    conn = get_connection(); c = conn.cursor()
    venda_id = int(data['id'])
    novo_status = data.get('status','').strip()
    entregador  = data.get('entregador','').strip()
    motivo_desistencia = data.get('motivo_desistencia','').strip()
    uid   = data.get('_uid'); unome = data.get('_unome','Sistema')

    VALID = ['pendente','separado','saiu','entregue','desistiu']
    if novo_status not in VALID:
        conn.close(); return {"ok":False,"erro":f"Status inválido: {novo_status}"}
    if novo_status == 'desistiu' and not motivo_desistencia:
        conn.close(); return {"ok":False,"erro":"Informe o motivo (cliente desistiu / não tinha ninguém em casa)"}

    c.execute("SELECT status_entrega FROM vendas WHERE id=?", (venda_id,))
    row = c.fetchone()
    if not row: conn.close(); return {"ok":False,"erro":"Venda não encontrada"}
    antes_status = row['status_entrega'] or 'pendente'

    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    campos_ts = {
        'separado':  'entrega_separado_em',
        'saiu':      'entrega_saiu_em',
        'entregue':  'entrega_entregue_em',
        'desistiu':  'entrega_desistiu_em',
    }
    extra_set  = ""
    extra_args = []
    if novo_status in campos_ts:
        col = campos_ts[novo_status]
        extra_set  = f", {col}=?"
        extra_args = [agora]
    if entregador:
        extra_set  += ", entregador=?"
        extra_args += [entregador]
    if novo_status == 'desistiu':
        extra_set  += ", entrega_motivo_desistencia=?"
        extra_args += [motivo_desistencia]

    c.execute(f"UPDATE vendas SET status_entrega=? {extra_set} WHERE id=?",
              [novo_status] + extra_args + [venda_id])

    desc_log = f"Entrega Venda #{venda_id}: {antes_status} → {novo_status}" + (f" — {entregador}" if entregador else "")
    if novo_status == 'desistiu': desc_log += f" — Motivo: {motivo_desistencia}"
    _log(c, uid, unome, 'STATUS_ENTREGA', 'Entregas', desc_log)
    conn.commit(); conn.close()
    return {"ok":True}


def api_listar_vendas():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM vendas ORDER BY id DESC LIMIT 60")
    vendas=[dict(v) for v in c.fetchall()]
    for v in vendas:
        if v.get('descartada'):
            # Venda descartada não tem itens_venda reais (nunca baixou estoque);
            # os itens ficam guardados em carrinho_json para exibição/recuperação.
            try: v['itens'] = json.loads(v.get('carrinho_json') or '[]')
            except Exception: v['itens'] = []
        else:
            c.execute("SELECT iv.*,p.nome FROM itens_venda iv JOIN produtos p ON iv.produto_id=p.id WHERE iv.venda_id=?", (v['id'],))
            v['itens']=[dict(i) for i in c.fetchall()]
    conn.close(); return vendas


# ─── FINANCEIRO ──────────────────────────────────────────────────────────────

def api_financeiro():
    conn = get_connection(); c = conn.cursor()
    # A lista exibida na tela continua limitada (performance/UX), mas o saldo
    # e os totais precisam ser calculados sobre TODOS os lançamentos — antes
    # este cálculo usava só os 100 mais recentes, então o saldo exibido podia
    # ficar incorreto assim que o histórico passasse de 100 movimentações.
    c.execute("SELECT COALESCE(SUM(CASE WHEN tipo='entrada' THEN valor ELSE 0 END),0) AS ent, "
              "COALESCE(SUM(CASE WHEN tipo='saida' THEN valor ELSE 0 END),0) AS sai FROM financeiro")
    totais = c.fetchone()
    ent_total, sai_total = totais['ent'], totais['sai']
    c.execute("SELECT * FROM financeiro ORDER BY created_at DESC LIMIT 100")
    movs=[dict(m) for m in c.fetchall()]; conn.close()
    return {"movimentacoes":movs,"total_entrada":ent_total,"total_saida":sai_total,"saldo":ent_total-sai_total}

def api_registrar_movimento(data):
    conn = get_connection(); c = conn.cursor()
    data_mov = data.get('data_movimentacao') or _hoje()
    c.execute("INSERT INTO financeiro (tipo,descricao,valor,categoria,pagamento,data_movimentacao) VALUES (?,?,?,?,?,?)",
              (data['tipo'],data['descricao'],float(data['valor']),
               data.get('categoria','Outros'),data.get('pagamento','-'),data_mov))
    conn.commit(); conn.close(); return {"ok":True}


# ─── CONTAS ──────────────────────────────────────────────────────────────────

def api_listar_contas():
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT ct.*, cl.nome AS cliente_nome FROM contas ct
                 LEFT JOIN clientes cl ON cl.id=ct.cliente_id ORDER BY ct.vencimento ASC""")
    contas=[dict(x) for x in c.fetchall()]; conn.close()
    for ct in contas:
        if ct.get('cliente_nome'): ct['cliente_fornecedor']=ct['cliente_nome']
    a_pagar  =[x for x in contas if x['tipo']=='pagar']
    a_receber=[x for x in contas if x['tipo']=='receber']
    return {"contas":contas,"a_pagar":a_pagar,"a_receber":a_receber,
            "total_pagar":  sum(x['valor'] for x in a_pagar   if x['status']=='pendente'),
            "total_receber":sum(x['valor'] for x in a_receber if x['status']=='pendente')}

def api_cadastrar_conta(data):
    conn = get_connection(); c = conn.cursor()
    cliente_id=data.get('cliente_id') or None; cliente_nm=data.get('cliente_fornecedor','')
    if cliente_id:
        c.execute("SELECT nome FROM clientes WHERE id=?", (cliente_id,))
        row=c.fetchone()
        if row: cliente_nm=row['nome']
    c.execute("INSERT INTO contas (tipo,descricao,valor,vencimento,cliente_id,cliente_fornecedor,categoria) VALUES (?,?,?,?,?,?,?)",
              (data['tipo'],data['descricao'],float(data['valor']),data['vencimento'],
               cliente_id,cliente_nm,data.get('categoria','Geral')))
    conn.commit(); new_id=c.lastrowid; conn.close()
    return {"id":new_id,"ok":True}

def api_baixar_conta(data):
    conn = get_connection(); c = conn.cursor()
    conta_id=int(data['id'])
    c.execute("SELECT * FROM contas WHERE id=?", (conta_id,))
    conta=c.fetchone()
    if not conta: conn.close(); return {"ok":False,"erro":"nao encontrada"}
    conta=dict(conta)
    if conta['status']=='pago': conn.close(); return {"ok":False,"erro":"ja pago"}
    tipo_fin='entrada' if conta['tipo']=='receber' else 'saida'
    cat_fin=conta['categoria'] or ('Credito recebido' if conta['tipo']=='receber' else 'Conta paga')
    c.execute("INSERT INTO financeiro (tipo,descricao,valor,categoria,pagamento,data_movimentacao) VALUES (?,?,?,?,?,?)",
              (tipo_fin,f"Baixa: {conta['descricao']}",conta['valor'],cat_fin,'baixa manual',_hoje()))
    fin_id=c.lastrowid
    c.execute("UPDATE contas SET status='pago', financeiro_id=? WHERE id=?", (fin_id, conta_id))
    if conta.get('cliente_id'):
        c.execute("INSERT INTO historico_cliente (cliente_id,tipo,descricao,valor,referencia_id) VALUES (?,?,?,?,?)",
                  (conta['cliente_id'], 'pagamento', f"✅ Pagamento recebido: {conta['descricao']}", conta['valor'], conta_id))
    uid=data.get('_uid'); unome=data.get('_unome','Sistema')
    _log(c, uid, unome, 'BAIXA', 'Contas', f"Baixa: {conta['descricao']} — {fmt_val(conta['valor'])}")
    conn.commit(); conn.close(); return {"ok":True}

def api_estornar_conta(data):
    conn = get_connection(); c = conn.cursor()
    conta_id=int(data['id']); uid=data.get('_uid'); unome=data.get('_unome','Sistema')
    c.execute("SELECT * FROM contas WHERE id=?", (conta_id,))
    conta=c.fetchone()
    if not conta: conn.close(); return {"ok":False,"erro":"nao encontrada"}
    conta=dict(conta)
    if conta['status']!='pago': conn.close(); return {"ok":False,"erro":"conta nao esta paga"}
    if conta.get('financeiro_id'):
        c.execute("DELETE FROM financeiro WHERE id=?", (conta['financeiro_id'],))
    c.execute("UPDATE contas SET status='estornado', financeiro_id=NULL WHERE id=?", (conta_id,))
    tipo_fin='saida' if conta['tipo']=='receber' else 'entrada'
    c.execute("INSERT INTO financeiro (tipo,descricao,valor,categoria,pagamento,data_movimentacao) VALUES (?,?,?,?,?,?)",
              (tipo_fin,f"Estorno: {conta['descricao']}",conta['valor'],'Estorno','estorno manual',_hoje()))
    if conta.get('cliente_id'):
        c.execute("INSERT INTO historico_cliente (cliente_id,tipo,descricao,valor,referencia_id) VALUES (?,?,?,?,?)",
                  (conta['cliente_id'], 'estorno', f"↩ Estorno de pagamento: {conta['descricao']}", conta['valor'], conta_id))
    _log(c, uid, unome, 'ESTORNO', 'Contas', f"Estorno: {conta['descricao']} — {fmt_val(conta['valor'])}")
    conn.commit(); conn.close(); return {"ok":True}

def api_excluir_conta(data):
    conn = get_connection(); c = conn.cursor()
    uid=data.get('_uid'); unome=data.get('_unome','Sistema')
    c.execute("SELECT descricao,valor FROM contas WHERE id=?", (int(data['id']),))
    row=c.fetchone()
    c.execute("DELETE FROM contas WHERE id=?", (int(data['id']),))
    if row: _log(c, uid, unome, 'EXCLUIR', 'Contas', f"Conta excluída: {row['descricao']} — {fmt_val(row['valor'])}")
    conn.commit(); conn.close(); return {"ok":True}

def _hoje(): return datetime.now().strftime('%Y-%m-%d')
def _agora(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def fmt_val(v):
    try: return f"R$ {float(v):,.2f}".replace(',','X').replace('.',',').replace('X','.')
    except: return str(v)


# ─── CONFIG ──────────────────────────────────────────────────────────────────

DEFAULTS_CONFIG = {
    'pix_chave':      '',
    'pix_tipo':       'email',
    'pix_recebedor':  '',
    'pix_ativo':      '1',
    'nome_empresa':   'Maná Food',
    'taxa_entrega':   '0',
    'tempo_entrega':  '',
    'area_entrega':   '',
    'qtd_mesas':      '10',
    'prefixo_mesa':   'Mesa',
    'impressao_modo': 'perguntar',  # perguntar | automatico | desativado
    'impressao_dav':  '1',
    'impressao_coz':  '1',
    'tema':           'default',
    'print_metodo':       'windows',
    'print_balcao_ip':    '',
    'print_cozinha_ip':   '',
    'print_balcao_nome':  '',
    'print_cozinha_nome': '',
    'formas_pagamento_extras': '',
    'bandeiras_credito': '["Visa","Mastercard","Elo","Hipercard","Amex"]',
    'bandeiras_debito': '["Visa Electron","Maestro","Elo Débito","Mastercard Débito"]',
}

# ─── USUÁRIOS & LOG ──────────────────────────────────────────────────────────

def _hash(senha): return hashlib.sha256(senha.encode()).hexdigest()

def _seed_admin(conn, c):
    """Cria admin padrão se não existir nenhum usuário"""
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios (nome,usuario,senha,perfil) VALUES (?,?,?,?)",
                  ('Administrador','admin',_hash('admin123'),'admin'))
        conn.commit()

def _log(c, uid, unome, acao, modulo, descricao, antes='', depois=''):
    try:
        c.execute("INSERT INTO log_auditoria (usuario_id,usuario_nome,acao,modulo,descricao,dados_antes,dados_depois) VALUES (?,?,?,?,?,?,?)",
                  (uid, unome, acao, modulo, descricao, str(antes), str(depois)))
    except: pass

def api_login(data):
    conn = get_connection(); c = conn.cursor()
    _seed_admin(conn, c)
    usuario = data.get('usuario','').strip().lower()
    senha   = _hash(data.get('senha',''))
    c.execute("SELECT * FROM usuarios WHERE LOWER(usuario)=? AND senha=? AND ativo=1", (usuario, senha))
    row = c.fetchone()
    if not row: conn.close(); return {"ok": False, "erro": "Usuário ou senha incorretos"}
    u = dict(row)
    _log(c, u['id'], u['nome'], 'LOGIN', 'Auth', f"Login realizado")
    conn.commit(); conn.close()
    # Retorna perms_custom para perfil personalizado
    import json as _jlogin
    perms_obj = None
    try:
        if u.get('perms_custom'): perms_obj = _jlogin.loads(u['perms_custom'])
    except: pass
    return {"ok": True, "usuario": {"id": u['id'], "nome": u['nome'], "usuario": u['usuario'], "perfil": u['perfil'], "perms_custom": perms_obj}}

def api_listar_usuarios():
    conn = get_connection(); c = conn.cursor()
    _seed_admin(conn, c)
    c.execute("SELECT id,nome,usuario,perfil,ativo,created_at FROM usuarios ORDER BY nome")
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r

def api_cadastrar_usuario(data):
    conn = get_connection(); c = conn.cursor()
    nome    = data.get('nome','').strip()
    usuario = data.get('usuario','').strip().lower()
    senha   = data.get('senha','').strip()
    perfil  = data.get('perfil','operador')
    if perfil not in ('admin','gerente','operador','caixa'): perfil='operador'
    uid     = data.get('_uid'); unome = data.get('_unome','Sistema')
    if not nome or not usuario or not senha:
        conn.close(); return {"ok": False, "erro": "Preencha todos os campos"}
    c.execute("SELECT id FROM usuarios WHERE LOWER(usuario)=?", (usuario,))
    if c.fetchone(): conn.close(); return {"ok": False, "erro": "Usuário já existe"}
    c.execute("INSERT INTO usuarios (nome,usuario,senha,perfil) VALUES (?,?,?,?)",
              (nome, usuario, _hash(senha), perfil))
    novo_id = c.lastrowid
    _log(c, uid, unome, 'CRIAR', 'Usuários', f"Usuário '{usuario}' ({perfil}) criado")
    conn.commit(); conn.close(); return {"ok": True, "id": novo_id}

def api_atualizar_usuario(data):
    conn = get_connection(); c = conn.cursor()
    uid_alvo = int(data['id'])
    nome     = data.get('nome','').strip()
    perfil   = data.get('perfil','operador')
    if perfil not in ('admin','gerente','operador','caixa'): perfil='operador'
    ativo    = int(data.get('ativo', 1))
    uid      = data.get('_uid'); unome = data.get('_unome','Sistema')
    c.execute("SELECT nome,perfil,ativo FROM usuarios WHERE id=?", (uid_alvo,))
    antes = dict(c.fetchone() or {})
    import json as _json3
    _pcu = data.get('perms_custom')
    _pcv = _json3.dumps(_pcu) if _pcu else ''
    if _pcv:
        c.execute("UPDATE usuarios SET nome=?,perfil=?,ativo=?,perms_custom=? WHERE id=?", (nome, perfil, ativo, _pcv, uid_alvo))
    else:
        c.execute("UPDATE usuarios SET nome=?,perfil=?,ativo=? WHERE id=?", (nome, perfil, ativo, uid_alvo))
    nova_senha = data.get('nova_senha','').strip()
    if nova_senha:
        c.execute("UPDATE usuarios SET senha=? WHERE id=?", (_hash(nova_senha), uid_alvo))
        _log(c, uid, unome, 'EDITAR', 'Usuários', f"Senha do usuário #{uid_alvo} alterada")
    _log(c, uid, unome, 'EDITAR', 'Usuários',
         f"Usuário #{uid_alvo} atualizado", antes, {'nome':nome,'perfil':perfil,'ativo':ativo})
    conn.commit(); conn.close(); return {"ok": True}

def api_excluir_usuario(data):
    conn = get_connection(); c = conn.cursor()
    uid_alvo = int(data['id'])
    uid      = data.get('_uid'); unome = data.get('_unome','Sistema')
    c.execute("SELECT nome,usuario FROM usuarios WHERE id=?", (uid_alvo,))
    row = c.fetchone()
    if not row: conn.close(); return {"ok": False, "erro": "Não encontrado"}
    if uid_alvo == uid: conn.close(); return {"ok": False, "erro": "Não pode excluir a si mesmo"}
    c.execute("UPDATE usuarios SET ativo=0 WHERE id=?", (uid_alvo,))
    _log(c, uid, unome, 'EXCLUIR', 'Usuários', f"Usuário '{row['usuario']}' desativado")
    conn.commit(); conn.close(); return {"ok": True}

def api_listar_log(params):
    conn = get_connection(); c = conn.cursor()
    modulo  = params.get('modulo','')
    acao    = params.get('acao','')
    usuario = params.get('usuario','')
    limite  = int(params.get('limite', 200))
    q = "SELECT * FROM log_auditoria WHERE 1=1"
    args = []
    if modulo:  q += " AND modulo=?";        args.append(modulo)
    if acao:    q += " AND acao=?";           args.append(acao)
    if usuario: q += " AND usuario_nome LIKE ?"; args.append(f'%{usuario}%')
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limite)
    c.execute(q, args)
    r = [dict(x) for x in c.fetchall()]; conn.close(); return r


# ─── CAIXA ───────────────────────────────────────────────────────────────────

def api_apuracao_caixa(params):
    """Apuração detalhada de um caixa (aberto ou fechado)"""
    conn = get_connection(); c = conn.cursor()
    caixa_id = params.get('id')
    if caixa_id:
        c.execute("SELECT * FROM caixa WHERE id=?", (int(caixa_id),))
    else:
        c.execute("SELECT * FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row: conn.close(); return {"erro": "Nenhum caixa encontrado"}
    cx = dict(row); caixa_id = cx['id']

    # movimentos
    c.execute("SELECT * FROM movimentos_caixa WHERE caixa_id=? ORDER BY created_at", (caixa_id,))
    movimentos = [dict(m) for m in c.fetchall()]
    sangrias    = sum(m['valor'] for m in movimentos if m['tipo']=='sangria')
    suprimentos = sum(m['valor'] for m in movimentos if m['tipo']=='suprimento')
    troco       = cx['troco_abertura'] or 0

    # vendas por forma de pagamento (não canceladas)
    c.execute("""SELECT tipo_pagamento,
                        COUNT(*) AS qtd,
                        COALESCE(SUM(total),0) AS total
                 FROM vendas
                 WHERE caixa_id=? AND (cancelada=0 OR cancelada IS NULL) AND (descartada=0 OR descartada IS NULL)
                 GROUP BY tipo_pagamento""", (caixa_id,))
    vendas_pag = [dict(r) for r in c.fetchall()]

    # vendas canceladas
    c.execute("""SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total
                 FROM vendas WHERE caixa_id=? AND cancelada=1""", (caixa_id,))
    canceladas = dict(c.fetchone())

    # totais
    total_vendas = sum(v['total'] for v in vendas_pag)
    vendas_din   = next((v['total'] for v in vendas_pag if v['tipo_pagamento']=='dinheiro'), 0)
    vendas_outros= total_vendas - vendas_din

    # saldo esperado em dinheiro
    saldo_esperado_din = troco + vendas_din + suprimentos - sangrias

    # totais por tipo não-dinheiro (conferência separada)
    pag_label = {'dinheiro':'Dinheiro','pix':'PIX','cartao_credito':'Cartão Crédito',
                 'cartao_debito':'Cartão Débito','crediario':'Crediário','outro':'Outro'}

    conn.close()
    return {
        'caixa':            cx,
        'movimentos':       movimentos,
        'vendas_pag':       vendas_pag,
        'canceladas':       canceladas,
        'sangrias':         sangrias,
        'suprimentos':      suprimentos,
        'troco_abertura':   troco,
        'total_vendas':     total_vendas,
        'vendas_dinheiro':  vendas_din,
        'vendas_outros':    vendas_outros,
        'saldo_esperado_din': saldo_esperado_din,
        'pag_label':        pag_label,
    }


def api_status_caixa(params=None):
    params = params or {}
    uid      = params.get('uid')
    caixa_id = params.get('caixa_id')  # admin pode pedir status de caixa específico por id
    conn = get_connection(); c = conn.cursor()
    if caixa_id:
        c.execute("SELECT * FROM caixa WHERE status='aberto' AND id=? ORDER BY id DESC LIMIT 1", (int(caixa_id),))
    elif uid:
        c.execute("SELECT * FROM caixa WHERE status='aberto' AND usuario_id=? ORDER BY id DESC LIMIT 1", (int(uid),))
    else:
        c.execute("SELECT * FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if row:
        caixa = dict(row)
        caixa_id = caixa['id']
        c.execute("SELECT * FROM movimentos_caixa WHERE caixa_id=? ORDER BY created_at ASC", (caixa_id,))
        caixa['movimentos'] = [dict(m) for m in c.fetchall()]
        # vendas do caixa (não crediário)
        # vendas válidas (não canceladas, não crediário)
        c.execute("""SELECT tipo_pagamento, COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total
                     FROM vendas WHERE caixa_id=? AND tipo_pagamento!='crediario' AND cancelada=0 AND descartada=0
                     GROUP BY tipo_pagamento""", (caixa_id,))
        caixa['vendas_por_pag'] = [dict(r) for r in c.fetchall()]
        # total apenas das vendas finalizadas
        c.execute("SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND cancelada=0 AND descartada=0", (caixa_id,))
        vt = c.fetchone(); caixa['total_vendas'] = vt['total']; caixa['qtd_vendas'] = vt['qtd']
        # canceladas separadas (para mostrar no fechamento)
        c.execute("SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND cancelada=1", (caixa_id,))
        vc = c.fetchone(); caixa['qtd_canceladas'] = vc['qtd']; caixa['total_canceladas'] = vc['total']
        conn.close(); return {'aberto': True, 'caixa': caixa, 'usuario_caixa': caixa.get('usuario_nome','')}
    conn.close(); return {'aberto': False, 'caixa': None}

def api_abrir_caixa(data):
    conn = get_connection(); c = conn.cursor()
    uid   = data.get('_uid')
    unome = data.get('_unome','Sistema')
    # Verifica se este usuário já tem caixa aberto
    if uid:
        c.execute("SELECT id FROM caixa WHERE status='aberto' AND usuario_id=?", (int(uid),))
        if c.fetchone(): conn.close(); return {"ok": False, "erro": "Você já tem um caixa aberto"}
    troco   = float(data.get('troco_abertura', 0) or 0)
    obs     = data.get('observacao', '')
    agora   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO caixa (status,valor_abertura,troco_abertura,observacao_abertura,aberto_em,usuario_id,usuario_nome) VALUES ('aberto',?,?,?,?,?,?)",
              (troco, troco, obs, agora, uid, unome))
    caixa_id = c.lastrowid
    if troco > 0:
        c.execute("INSERT INTO movimentos_caixa (caixa_id,tipo,descricao,valor) VALUES (?,?,?,?)",
                  (caixa_id, 'abertura', f'Troco de abertura', troco))
    _log(c, uid, unome, 'ABRIR_CAIXA', 'Caixa', f"Caixa #{caixa_id} aberto — troco {fmt_val(troco)}")
    conn.commit(); conn.close()
    return {"ok": True, "caixa_id": caixa_id}

def api_fechar_caixa(data):
    conn = get_connection(); c = conn.cursor()
    uid_fechar = data.get('_uid')
    caixa_alvo = data.get('caixa_id')  # admin pode passar caixa_id específico
    # Cada usuário fecha SOMENTE seu próprio caixa
    # Admin pode fechar um caixa específico passando caixa_id
    if caixa_alvo:
        c.execute("SELECT * FROM caixa WHERE status='aberto' AND id=? ORDER BY id DESC LIMIT 1", (int(caixa_alvo),))
    elif uid_fechar:
        c.execute("SELECT * FROM caixa WHERE status='aberto' AND usuario_id=? ORDER BY id DESC LIMIT 1", (uid_fechar,))
    else:
        c.execute("SELECT * FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row: conn.close(); return {"ok": False, "erro": "Nenhum caixa aberto para este usuário"}
    caixa_id  = row['id']
    obs       = data.get('observacao', '')
    agora     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uid=data.get('_uid'); unome=data.get('_unome','Sistema')
    c.execute("SELECT COALESCE(SUM(CASE WHEN tipo IN ('abertura','suprimento') THEN valor WHEN tipo='sangria' THEN -valor ELSE 0 END),0) AS saldo FROM movimentos_caixa WHERE caixa_id=?", (caixa_id,))
    saldo_mov = c.fetchone()['saldo']
    # soma só vendas finalizadas em dinheiro (exclui canceladas e descartadas)
    c.execute("SELECT COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND tipo_pagamento='dinheiro' AND cancelada=0 AND descartada=0", (caixa_id,))
    vendas_din = c.fetchone()['total']
    # canceladas: só para registro no log
    c.execute("SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND cancelada=1", (caixa_id,))
    cx_cancel = c.fetchone()
    valor_fechamento = saldo_mov + vendas_din
    c.execute("UPDATE caixa SET status='fechado',valor_fechamento=?,observacao_fechamento=?,fechado_em=? WHERE id=?",
              (valor_fechamento, obs, agora, caixa_id))
    c.execute("INSERT INTO movimentos_caixa (caixa_id,tipo,descricao,valor) VALUES (?,?,?,?)",
              (caixa_id, 'fechamento', f'Fechamento do caixa', valor_fechamento))
    desc_cancel = f" | {cx_cancel['qtd']} canceladas ({fmt_val(cx_cancel['total'])})" if cx_cancel['qtd'] > 0 else ''
    _log(c, uid, unome, 'FECHAR_CAIXA', 'Caixa', f"Caixa #{caixa_id} fechado — {fmt_val(valor_fechamento)}{desc_cancel}")
    conn.commit(); conn.close()
    return {"ok": True, "valor_fechamento": valor_fechamento, "canceladas_qtd": cx_cancel['qtd'], "canceladas_total": cx_cancel['total']}

def api_sangria_caixa(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row: conn.close(); return {"ok": False, "erro": "Nenhum caixa aberto"}
    valor = float(data.get('valor', 0) or 0)
    if valor <= 0: conn.close(); return {"ok": False, "erro": "Valor inválido"}
    desc = data.get('descricao', 'Sangria')
    uid=data.get('_uid'); unome=data.get('_unome','Sistema')
    c.execute("INSERT INTO movimentos_caixa (caixa_id,tipo,descricao,valor) VALUES (?,?,?,?)",
              (row['id'], 'sangria', desc, valor))
    _log(c, uid, unome, 'SANGRIA', 'Caixa', f"Sangria {fmt_val(valor)} — {desc}")
    conn.commit(); conn.close(); return {"ok": True}

def api_suprimento_caixa(data):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM caixa WHERE status='aberto' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row: conn.close(); return {"ok": False, "erro": "Nenhum caixa aberto"}
    valor = float(data.get('valor', 0) or 0)
    if valor <= 0: conn.close(); return {"ok": False, "erro": "Valor inválido"}
    desc = data.get('descricao', 'Suprimento')
    uid=data.get('_uid'); unome=data.get('_unome','Sistema')
    c.execute("INSERT INTO movimentos_caixa (caixa_id,tipo,descricao,valor) VALUES (?,?,?,?)",
              (row['id'], 'suprimento', desc, valor))
    _log(c, uid, unome, 'SUPRIMENTO', 'Caixa', f"Suprimento {fmt_val(valor)} — {desc}")
    conn.commit(); conn.close(); return {"ok": True}

def api_caixas_abertos():
    """Lista todos os caixas abertos — usado pelo admin para gerenciar."""""
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM caixa WHERE status='aberto' ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    for cx in rows:
        c.execute("SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND cancelada=0 AND descartada=0", (cx['id'],))
        vt = c.fetchone(); cx['qtd_vendas'] = vt['qtd']; cx['total_vendas'] = vt['total']
    conn.close()
    return rows


def api_historico_caixas():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM caixa ORDER BY id DESC LIMIT 30")
    caixas = [dict(r) for r in c.fetchall()]
    for cx in caixas:
        c.execute("SELECT * FROM movimentos_caixa WHERE caixa_id=? ORDER BY created_at ASC", (cx['id'],))
        cx['movimentos'] = [dict(m) for m in c.fetchall()]
        c.execute("SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND cancelada=0 AND descartada=0", (cx['id'],))
        vt = c.fetchone(); cx['total_vendas'] = vt['total']; cx['qtd_vendas'] = vt['qtd']
    conn.close(); return caixas


# ─── RELATÓRIOS ──────────────────────────────────────────────────────────────

def api_relatorio(params):
    """Relatório consolidado: vendas, pagamentos, contas, clientes"""
    conn = get_connection(); c = conn.cursor()
    dt_ini = params.get('de',  '')
    dt_fim = params.get('ate', '')

    # filtro de data para vendas (exclui canceladas e descartadas do faturamento real)
    where_v = ' AND v.cancelada=0 AND v.descartada=0'
    args_v  = []
    if dt_ini: where_v += ' AND date(v.data_venda)>=?'; args_v.append(dt_ini)
    if dt_fim: where_v += ' AND date(v.data_venda)<=?'; args_v.append(dt_fim)

    # ── VENDAS GERAL ──────────────────────────────────────────────────────────
    c.execute(f"""SELECT COUNT(*) AS total_vendas,
                         COALESCE(SUM(total),0) AS faturamento,
                         COALESCE(AVG(total),0) AS ticket_medio,
                         COALESCE(MAX(total),0) AS maior_venda,
                         COALESCE(MIN(total),0) AS menor_venda
                  FROM vendas v WHERE 1=1{where_v}""", args_v)
    geral = dict(c.fetchone())

    # vendas por dia (últimos 30 dias ou período)
    c.execute(f"""SELECT date(v.data_venda) AS dia,
                         COUNT(*) AS qtd,
                         COALESCE(SUM(total),0) AS total
                  FROM vendas v WHERE 1=1{where_v}
                  GROUP BY date(v.data_venda) ORDER BY dia DESC LIMIT 30""", args_v)
    por_dia = [dict(r) for r in c.fetchall()]

    # ── VENDAS POR FORMA DE PAGAMENTO ─────────────────────────────────────────
    c.execute(f"""SELECT tipo_pagamento,
                         COUNT(*) AS qtd,
                         COALESCE(SUM(total),0) AS total
                  FROM vendas v WHERE 1=1{where_v}
                  GROUP BY tipo_pagamento ORDER BY total DESC""", args_v)
    por_pagamento = [dict(r) for r in c.fetchall()]

    # ── PRODUTOS MAIS VENDIDOS ─────────────────────────────────────────────────
    c.execute(f"""SELECT p.nome, SUM(iv.quantidade) AS qtd_vendida,
                         SUM(iv.subtotal) AS receita
                  FROM itens_venda iv
                  JOIN produtos p ON p.id=iv.produto_id
                  JOIN vendas v   ON v.id=iv.venda_id
                  WHERE 1=1{where_v}
                  GROUP BY p.id ORDER BY qtd_vendida DESC LIMIT 10""", args_v)
    top_produtos = [dict(r) for r in c.fetchall()]

    # ── CONTAS A PAGAR / RECEBER ──────────────────────────────────────────────
    hj = datetime.now().strftime('%Y-%m-%d')
    c.execute("""SELECT
        COALESCE(SUM(CASE WHEN tipo='receber' AND status='pendente' THEN valor ELSE 0 END),0) AS receber_pendente,
        COALESCE(SUM(CASE WHEN tipo='receber' AND status='pago'     THEN valor ELSE 0 END),0) AS receber_pago,
        COALESCE(SUM(CASE WHEN tipo='pagar'   AND status='pendente' THEN valor ELSE 0 END),0) AS pagar_pendente,
        COALESCE(SUM(CASE WHEN tipo='pagar'   AND status='pago'     THEN valor ELSE 0 END),0) AS pagar_pago,
        COALESCE(SUM(CASE WHEN tipo='receber' AND status='pendente' AND vencimento<? THEN valor ELSE 0 END),0) AS receber_vencido,
        COALESCE(SUM(CASE WHEN tipo='pagar'   AND status='pendente' AND vencimento<? THEN valor ELSE 0 END),0) AS pagar_vencido
        FROM contas""", (hj, hj))
    contas_resumo = dict(c.fetchone())

    # vencimentos próximos 7 dias
    c.execute("""SELECT ct.*, cl.nome AS cliente_nome FROM contas ct
                 LEFT JOIN clientes cl ON cl.id=ct.cliente_id
                 WHERE ct.status='pendente' AND ct.vencimento BETWEEN ? AND date(?,' +7 days')
                 ORDER BY ct.vencimento ASC LIMIT 20""", (hj, hj))
    proximos_venc = [dict(r) for r in c.fetchall()]
    for r in proximos_venc:
        if r.get('cliente_nome'): r['cliente_fornecedor'] = r['cliente_nome']

    # ── CLIENTES ─────────────────────────────────────────────────────────────
    c.execute("SELECT COUNT(*) AS total FROM clientes WHERE ativo=1")
    total_clientes = c.fetchone()['total']

    c.execute("""SELECT COALESCE(status_cliente,'ativo') AS st, COUNT(*) AS qtd
                 FROM clientes WHERE ativo=1 GROUP BY st""")
    clientes_por_status = [dict(r) for r in c.fetchall()]

    # top clientes por faturamento
    c.execute(f"""SELECT cl.nome, cl.telefone,
                         COUNT(DISTINCT v.id)  AS total_compras,
                         COALESCE(SUM(v.total),0) AS faturamento,
                         COALESCE(SUM(CASE WHEN ct.status='pendente' THEN ct.valor ELSE 0 END),0) AS saldo_devedor
                  FROM clientes cl
                  LEFT JOIN vendas v  ON v.cliente_id=cl.id AND v.cancelada=0 AND v.descartada=0{(' AND date(v.data_venda)>=? AND date(v.data_venda)<=?' if dt_ini and dt_fim else (' AND date(v.data_venda)>=?' if dt_ini else (' AND date(v.data_venda)<=?' if dt_fim else '')))}
                  LEFT JOIN contas ct ON ct.cliente_id=cl.id AND ct.tipo='receber'
                  WHERE cl.ativo=1
                  GROUP BY cl.id ORDER BY faturamento DESC LIMIT 10""",
              ([dt_ini, dt_fim] if dt_ini and dt_fim else ([dt_ini] if dt_ini else ([dt_fim] if dt_fim else []))))
    top_clientes = [dict(r) for r in c.fetchall()]

    # inadimplentes (saldo devedor pendente)
    c.execute("""SELECT cl.nome, cl.telefone,
                        COALESCE(SUM(ct.valor),0) AS divida,
                        COUNT(ct.id) AS contas_abertas
                 FROM clientes cl
                 JOIN contas ct ON ct.cliente_id=cl.id AND ct.tipo='receber' AND ct.status='pendente'
                 WHERE cl.ativo=1
                 GROUP BY cl.id ORDER BY divida DESC LIMIT 10""")
    inadimplentes = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        'geral':             geral,
        'por_dia':           por_dia,
        'por_pagamento':     por_pagamento,
        'top_produtos':      top_produtos,
        'contas_resumo':     contas_resumo,
        'proximos_venc':     proximos_venc,
        'total_clientes':    total_clientes,
        'clientes_por_status': clientes_por_status,
        'top_clientes':      top_clientes,
        'inadimplentes':     inadimplentes,
    }


def api_get_config():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT chave, valor FROM config")
    rows = {r['chave']: r['valor'] for r in c.fetchall()}
    conn.close()
    result = dict(DEFAULTS_CONFIG)
    result.update(rows)
    return result

def api_formas_pagamento():
    cfg = api_get_config()
    extras = cfg.get('formas_pagamento_extras','')
    try:
        extras_list = json.loads(extras) if extras else []
    except: extras_list = []
    return {"padrao":["dinheiro","pix","cartao_credito","cartao_debito","crediario"],"extras":extras_list}

def api_salvar_config(data):
    conn = get_connection(); c = conn.cursor()
    for chave, valor in data.items():
        c.execute("INSERT INTO config (chave, valor) VALUES (?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
                  (chave, str(valor)))
    conn.commit(); conn.close(); return {"ok": True}


# ─── SERVIDOR HTTP ────────────────────────────────────────────────────────────

INTERFACE_PATH = Path(__file__).parent / "interface" / "index.html"


class ManaFoodHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_json(self, data, status=200):
        body=json.dumps(data,ensure_ascii=False,default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',len(body))
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers(); self.wfile.write(body)

    def send_html(self, content):
        body=content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',len(body))
        self.send_header('Cache-Control','public, max-age=300')
        self.end_headers(); self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        from urllib.parse import unquote
        params = {unquote(k): unquote(v) for k,v in (p.split('=',1) for p in parsed.query.split('&') if '=' in p)} if parsed.query else {}
        if path in ('/','index.html'):
            self.send_html(INTERFACE_PATH.read_text(encoding='utf-8') if INTERFACE_PATH.exists()
                           else "<h2>Coloque index.html em interface/</h2>")
            return
        if path == '/cardapio':
            self.send_html(_gerar_pagina_cardapio())
            return
        if path == '/favicon.ico':
            ico = Path(__file__).parent / 'icon-192.png'
            if not ico.exists(): ico = Path(__file__).parent / 'logo.ico'
            if ico.exists():
                ctype = 'image/png' if str(ico).endswith('.png') else 'image/x-icon'
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Cache-Control','public, max-age=86400')
                self.end_headers()
                self.wfile.write(ico.read_bytes())
            return
        if path == '/manifest.json':
            mf = BASE_DIR.parent / 'manifest.json'
            if not mf.exists(): mf = Path(__file__).parent / 'manifest.json'
            if mf.exists():
                self.send_response(200)
                self.send_header('Content-Type','application/manifest+json')
                self.send_header('Access-Control-Allow-Origin','*')
                self.end_headers()
                self.wfile.write(mf.read_bytes())
            return
        if path in ('/icon-192.png', '/icon-512.png'):
            ico = Path(__file__).parent / path.lstrip('/')
            if ico.exists():
                self.send_response(200)
                self.send_header('Content-Type','image/png')
                self.end_headers()
                self.wfile.write(ico.read_bytes())
            return
        if path == '/api/relatorio':
            self.send_json(api_relatorio(params)); return
        if path == '/api/log':
            self.send_json(api_listar_log(params)); return
        if path == '/api/entregas':
            self.send_json(api_listar_entregas(params)); return
        if path == '/api/reposicao':
            self.send_json(api_reposicao(params)); return
        if path == '/api/promocoes':
            self.send_json(api_listar_promocoes()); return
        if path == '/api/promocoes/ativas':
            self.send_json(api_promocoes_ativas()); return
        if path == '/api/formas-pagamento':
            self.send_json(api_formas_pagamento()); return
        if path == '/api/cashback/config':
            self.send_json(api_get_cashback_config()); return
        if path == '/api/empresa':
            self.send_json(api_get_empresa()); return
        if path == '/api/fiscal':
            self.send_json(api_get_fiscal()); return
        if path == '/api/xml/entradas':
            self.send_json(api_listar_entradas_xml()); return
        if path == '/api/check-update':
            self.send_json(api_check_update()); return
        if path == '/api/aplicar-update':
            self.send_json(api_aplicar_update()); return
        if path.startswith('/api/fidelidade/'):
            try:
                cid=int(path.split('/')[-1])
                self.send_json(api_extrato_fidelidade(cid)); return
            except: pass
        if path == '/api/ingredientes':
            self.send_json(api_listar_ingredientes()); return
        if path.startswith('/api/produtos/') and path.endswith('/ingredientes'):
            try:
                pid=int(path.split('/')[3])
                self.send_json(api_produto_ingredientes(pid)); return
            except: pass
        if path == '/api/caixa/apuracao':
            self.send_json(api_apuracao_caixa(params)); return
        if path.startswith('/api/clientes/'):
            try:
                cid=int(path.split('/')[-1])
                cl=api_buscar_cliente(cid)
                self.send_json(cl if cl else {"erro":"nao encontrado"},200 if cl else 404)
            except: self.send_json({"erro":"id invalido"},400)
            return
        if path.startswith('/api/produtos/') and '/imagem/' not in path:
            try:
                pid=int(path.split('/')[-1])
                conn=get_connection(); c=conn.cursor()
                c.execute("SELECT * FROM produtos WHERE id=? AND ativo=1",(pid,))
                row=c.fetchone(); conn.close()
                self.send_json(dict(row) if row else {"erro":"nao encontrado"},200 if row else 404)
            except: self.send_json({"erro":"id invalido"},400)
            return
        if path.startswith('/api/produtos/imagem/'):
            try:
                pid=int(path.split('/')[-1])
                img=api_imagem_produto(pid)
                self.send_json({"imagem":img} if img else {"imagem":None})
            except: self.send_json({"imagem":None})
            return
        # Rotas com params
        param_routes = {
            '/api/meta':         api_meta_diaria,
            '/api/cmv':          api_relatorio_cmv,
            '/api/mesa/historico': api_mesa_historico,
            '/api/caixa/apuracao': api_apuracao_caixa,
        }
        if path in param_routes:
            self.send_json(param_routes[path](params)); return

        routes={'/api/produtos':api_listar_produtos,'/api/categorias':api_listar_categorias_get,'/api/clientes':api_listar_clientes,
                '/api/vendas':api_listar_vendas,'/api/cardapio':api_cardapio_publico,'/api/cupons':api_listar_cupons,'/api/backups':api_listar_backups,'/api/financeiro':api_financeiro,
                '/api/contas':api_listar_contas,'/api/config':api_get_config,
                '/api/caixa':lambda p=None: api_status_caixa(p),'/api/caixa/abertos':api_caixas_abertos,'/api/caixa/historico':api_historico_caixas,'/api/mesas/ativas':api_mesas_ativas,
                '/api/usuarios':api_listar_usuarios}
        fn=routes.get(path)
        if fn: self.send_json(fn())
        else:  self.send_json({"erro":"Rota nao encontrada"},404)

    def do_POST(self):
        length=int(self.headers.get('Content-Length',0))
        body=self.rfile.read(length)
        try:    data=json.loads(body.decode('utf-8'))
        except: self.send_json({"erro":"JSON invalido"},400); return
        path=urlparse(self.path).path
        routes={
            '/api/produtos':           api_cadastrar_produto,
            '/api/categorias':         api_cadastrar_categoria,
            '/api/categorias/atualizar': api_atualizar_categoria,
            '/api/categorias/excluir':   api_excluir_categoria,
            '/api/produtos/atualizar': api_atualizar_produto,
            '/api/clientes':           api_cadastrar_cliente,
            '/api/clientes/atualizar': api_atualizar_cliente,
            '/api/clientes/status':    api_alterar_status_cliente,
            '/api/clientes/inativar':  api_inativar_cliente,
            '/api/vendas':             api_registrar_venda,
            '/api/vendas/cancelar':    api_cancelar_venda,
            '/api/vendas/editar':      api_editar_venda,
            '/api/vendas/descartar':   api_descartar_venda,
            '/api/vendas/recuperar':   api_recuperar_venda,
            '/api/vendas/tipo':        api_alterar_tipo_atendimento,'/api/cardapio/config':    api_salvar_cardapio_config,'/api/backup':             api_fazer_backup,
            '/api/backup/restaurar':  api_restaurar_backup,'/api/cupons/salvar':      api_salvar_cupom,'/api/cupons/excluir':     api_excluir_cupom,'/api/cupons/validar':     api_validar_cupom,'/api/meta/salvar':        api_salvar_meta,'/api/produtos/favorito':  api_toggle_favorito,
            '/api/mesas/fechar':       api_fechar_mesa,
            '/api/entregas/status':    api_atualizar_status_entrega,
            '/api/financeiro':         api_registrar_movimento,
            '/api/contas':             api_cadastrar_conta,
            '/api/contas/baixar':      api_baixar_conta,
            '/api/contas/estornar':    api_estornar_conta,
            '/api/contas/excluir':     api_excluir_conta,
            '/api/config':             api_salvar_config,
            '/api/caixa/abrir':        api_abrir_caixa,
            '/api/caixa/fechar':       api_fechar_caixa,
            '/api/caixa/sangria':      api_sangria_caixa,
            '/api/caixa/suprimento':   api_suprimento_caixa,
            '/api/login':              api_login,
            '/api/usuarios':           api_cadastrar_usuario,
            '/api/usuarios/atualizar': api_atualizar_usuario,
            '/api/usuarios/excluir':   api_excluir_usuario,
            '/api/promocoes':                 api_salvar_promocao,
            '/api/promocoes/excluir':         api_excluir_promocao,
            '/api/cashback/config':           api_salvar_cashback_config,
            '/api/cashback/usar':             api_usar_cashback,
            '/api/pontos/resgatar':           api_resgatar_pontos,
            '/api/ingredientes':              api_cadastrar_ingrediente,
            '/api/ingredientes/atualizar':    api_atualizar_ingrediente,
            '/api/ingredientes/excluir':      api_excluir_ingrediente,
            '/api/produtos/ingredientes':     api_vincular_ingrediente,
            '/api/produtos/ingredientes/remover': api_desvincular_ingrediente,
            '/api/empresa':               api_salvar_empresa,
            '/api/fiscal':                api_salvar_fiscal,
            '/api/fiscal/certificado':    api_upload_certificado,
            '/api/xml/importar':          api_importar_xml,
            '/api/xml/vincular':          api_vincular_item_xml,
            '/api/xml/confirmar':         api_confirmar_entrada_xml,
            '/api/cardapio/publicar':     api_publicar_cardapio,
            '/api/imprimir':              api_imprimir,
        }
        fn=routes.get(path)
        if fn: self.send_json(fn(data))
        else:  self.send_json({"erro":"Rota nao encontrada"},404)


PORT=5000
LOCAL_VERSION = (Path(__file__).parent / 'version.txt').read_text(encoding='utf-8').strip() if (Path(__file__).parent / 'version.txt').exists() else '0.0.0'

def api_check_update():
    import urllib.request
    try:
        url = 'https://raw.githubusercontent.com/techprimedev-br/manafood/main/version.txt'
        req = urllib.request.urlopen(url, timeout=5)
        remote = req.read().decode('utf-8').strip()
        changelog = ''
        try:
            cl_url = 'https://raw.githubusercontent.com/techprimedev-br/manafood/main/changelog.txt'
            cl_req = urllib.request.urlopen(cl_url, timeout=5)
            changelog = cl_req.read().decode('utf-8').strip()
        except: pass
        tem_update = remote != LOCAL_VERSION
        return {"ok":True,"versao_local":LOCAL_VERSION,"versao_remota":remote,"tem_update":tem_update,"changelog":changelog}
    except:
        return {"ok":True,"versao_local":LOCAL_VERSION,"versao_remota":"","tem_update":False}

def api_aplicar_update():
    import urllib.request
    base_url = 'https://raw.githubusercontent.com/techprimedev-br/manafood/main/'
    base_dir = Path(__file__).parent
    arquivos = [
        ('server.py', base_dir / 'server.py'),
        ('interface/index.html', base_dir / 'interface' / 'index.html'),
        ('version.txt', base_dir / 'version.txt'),
        ('mana.py', base_dir / 'mana.py'),
        ('manifest.json', base_dir / 'manifest.json'),
        ('INICIAR.bat', base_dir / 'INICIAR.bat'),
    ]
    try:
        atualizado = 0
        for remote_path, local_path in arquivos:
            try:
                req = urllib.request.urlopen(base_url + remote_path, timeout=15)
                conteudo = req.read()
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(conteudo)
                atualizado += 1
            except: pass
        new_ver = (base_dir / 'version.txt').read_text(encoding='utf-8').strip() if (base_dir / 'version.txt').exists() else LOCAL_VERSION
        return {"ok":True,"msg":f"Atualizado! {atualizado} arquivos baixados. Reinicie o servidor.","versao":new_ver}
    except Exception as e:
        return {"ok":False,"erro":str(e)}

# ─────────────────────────────────────────────
# IMPRESSÃO DIRETA
# ─────────────────────────────────────────────
def _imprimir_escpos(ip_porta, texto):
    """Envia texto pra impressora térmica ESC/POS via socket."""
    try:
        parts = ip_porta.split(':')
        ip = parts[0].strip()
        porta = int(parts[1]) if len(parts) > 1 else 9100
        import socket as sock_mod
        s = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip, porta))
        s.send(b'\x1b\x40')  # ESC @ init
        s.send(b'\x1b\x61\x01')  # Center align
        for line in texto.split('\n'):
            s.send(line.encode('cp850', errors='replace') + b'\n')
        s.send(b'\n\n\n')  # Feed
        s.send(b'\x1d\x56\x00')  # GS V 0 — full cut
        s.close()
        return True
    except Exception as e:
        print(f"[ESCPOS] Erro: {e}")
        return False

def _imprimir_windows_direto(nome_impressora, texto):
    """Imprime texto numa impressora Windows pelo nome via PowerShell."""
    try:
        import subprocess as subp_mod
        import tempfile as tmp_mod
        tmp = tmp_mod.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        tmp.write(texto)
        tmp.close()
        subp_mod.run(['powershell', '-NoProfile', '-Command',
            f"Get-Content -Path '{tmp.name}' -Encoding UTF8 | Out-Printer -Name '{nome_impressora}'"],
            capture_output=True, timeout=10)
        os.unlink(tmp.name)
        return True
    except Exception as e:
        print(f"[PRINT] Erro: {e}")
        return False

def api_imprimir(data):
    """Endpoint de impressão direta (ESC/POS ou Windows)."""
    tipo = data.get('tipo', 'dav')  # 'dav' ou 'cozinha'
    texto = data.get('texto', '')
    if not texto:
        return {"ok": False, "erro": "Texto vazio"}

    cfg = api_get_config()
    metodo = cfg.get('print_metodo', 'windows')

    if metodo == 'escpos':
        ip = cfg.get('print_cozinha_ip', '') if tipo == 'cozinha' else cfg.get('print_balcao_ip', '')
        if not ip:
            return {"ok": False, "erro": f"IP da impressora {tipo} não configurado"}
        ok = _imprimir_escpos(ip, texto)
        return {"ok": ok, "erro": "" if ok else "Falha na conexão com a impressora"}

    elif metodo == 'direto':
        nome = cfg.get('print_cozinha_nome', '') if tipo == 'cozinha' else cfg.get('print_balcao_nome', '')
        if not nome:
            return {"ok": False, "erro": f"Nome da impressora {tipo} não configurado"}
        ok = _imprimir_windows_direto(nome, texto)
        return {"ok": ok, "erro": "" if ok else "Falha ao imprimir"}

    else:
        return {"ok": False, "erro": "Método 'windows' usa impressão pelo navegador"}

def _auto_publicar_cardapio():
    """Publica cardápio em background se token estiver configurado."""
    def _pub():
        try:
            conn = get_connection(); c = conn.cursor()
            c.execute("SELECT valor FROM config WHERE chave='github_token'")
            row = c.fetchone(); conn.close()
            if row and row['valor']:
                api_publicar_cardapio()
        except: pass
    threading.Thread(target=_pub, daemon=True).start()

def api_publicar_cardapio(data=None):
    """Gera HTML estático do cardápio e publica no GitHub Pages."""
    import urllib.request
    try:
        html = _gerar_pagina_cardapio()
        # Busca token do config ou do arquivo
        token = ''
        conn = get_connection(); c = conn.cursor()
        c.execute("SELECT valor FROM config WHERE chave='github_token'")
        row = c.fetchone()
        if row: token = row['valor']
        conn.close()
        if not token:
            token_file = Path(__file__).parent / 'github_token.txt'
            if token_file.exists(): token = token_file.read_text(encoding='utf-8').strip()
        if not token:
            return {"ok":False,"erro":"Token do GitHub não configurado. Vá em Configurações e preencha o token."}
        # Codifica HTML em base64
        import base64 as b64mod
        content_b64 = b64mod.b64encode(html.encode('utf-8')).decode('utf-8')
        # Busca SHA atual do arquivo (necessário pra atualizar)
        repo = 'techprimedev-br/manafood'
        file_path = 'docs/index.html'
        api_url = f'https://api.github.com/repos/{repo}/contents/{file_path}'
        sha = ''
        try:
            req = urllib.request.Request(api_url, headers={'Authorization':f'token {token}','User-Agent':'ManaFood'})
            resp = urllib.request.urlopen(req, timeout=10)
            import json as jmod
            info = jmod.loads(resp.read().decode('utf-8'))
            sha = info.get('sha','')
        except: pass
        # Envia arquivo
        payload = {"message":"Cardápio atualizado","content":content_b64,"branch":"main"}
        if sha: payload["sha"] = sha
        import json as jmod
        body = jmod.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=body, method='PUT',
              headers={'Authorization':f'token {token}','User-Agent':'ManaFood','Content-Type':'application/json'})
        resp = urllib.request.urlopen(req, timeout=15)
        if resp.status in (200,201):
            return {"ok":True,"url":f"https://techprimedev-br.github.io/manafood/"}
        else:
            return {"ok":False,"erro":f"GitHub retornou status {resp.status}"}
    except Exception as e:
        return {"ok":False,"erro":str(e)}

def abrir_navegador():
    time.sleep(1.2); webbrowser.open(f'http://localhost:{PORT}')

if __name__=='__main__':
    print("="*48)
    print("  MANÁ HAMBUGUERIA v4.0 — Iniciando...")
    print("="*48)
    init_database()
    threading.Thread(target=abrir_navegador,daemon=True).start()
    # Backup automático diário
    import threading as _threading
    def _backup_auto():
        import datetime as _dt, time as _time
        while True:
            agora = _dt.datetime.now()
            prox = agora.replace(hour=0,minute=0,second=0,microsecond=0) + _dt.timedelta(days=1)
            _time.sleep((prox-agora).total_seconds())
            api_fazer_backup()
    _threading.Thread(target=_backup_auto, daemon=True).start()

    httpd=HTTPServer(('0.0.0.0',PORT),ManaFoodHandler)
    print(f"Rodando em http://localhost:{PORT} | Rede: http://192.168.1.5:{PORT}")
    print("Ctrl+C para encerrar\n")
    try:    httpd.serve_forever()
    except KeyboardInterrupt: print("\nEncerrado.")
