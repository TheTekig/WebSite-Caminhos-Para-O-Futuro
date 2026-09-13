"""
Camada de acesso ao banco de dados.

Funciona com dois bancos, escolhidos automaticamente:
- Se a variável de ambiente DATABASE_URL estiver definida (ex: no Render,
  apontando pro Postgres), usa Postgres.
- Caso contrário, usa um arquivo SQLite local em `data/sorteio.db` — é o
  que acontece automaticamente quando você roda o projeto na sua máquina.

O restante do código (main.py) não sabe nem precisa saber qual dos dois
está sendo usado por baixo dos panos.
"""
import json
import os
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, text

from . import config

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    # Render (e outros provedores) às vezes fornecem a URL como
    # "postgres://", mas o driver moderno espera "postgresql://".
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=2)
    IS_POSTGRES = True
else:
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    engine = create_engine(f"sqlite:///{config.DB_PATH}")
    IS_POSTGRES = False


@contextmanager
def get_conn():
    with engine.begin() as conn:
        yield conn


def init_db():
    if IS_POSTGRES:
        ddl_tabela = """
            CREATE TABLE IF NOT EXISTS inscricoes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                telefone TEXT NOT NULL,
                cpf TEXT,
                extra TEXT DEFAULT '{}',
                criado_em TEXT NOT NULL,
                sorteado INTEGER NOT NULL DEFAULT 0,
                sorteado_em TEXT,
                posicao_sorteio INTEGER
            )
        """
    else:
        ddl_tabela = """
            CREATE TABLE IF NOT EXISTS inscricoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                telefone TEXT NOT NULL,
                cpf TEXT,
                extra TEXT DEFAULT '{}',
                criado_em TEXT NOT NULL,
                sorteado INTEGER NOT NULL DEFAULT 0,
                sorteado_em TEXT,
                posicao_sorteio INTEGER
            )
        """
    with get_conn() as conn:
        conn.execute(text(ddl_tabela))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email ON inscricoes(email)"))


def criar_inscricao(nome: str, email: str, telefone: str, cpf: str | None, extra: dict) -> int:
    with get_conn() as conn:
        result = conn.execute(
            text("""INSERT INTO inscricoes (nome, email, telefone, cpf, extra, criado_em)
                     VALUES (:nome, :email, :telefone, :cpf, :extra, :criado_em)
                     RETURNING id"""),
            {
                "nome": nome.strip(),
                "email": email.strip().lower(),
                "telefone": telefone.strip(),
                "cpf": (cpf or "").strip(),
                "extra": json.dumps(extra, ensure_ascii=False),
                "criado_em": datetime.utcnow().isoformat(),
            },
        )
        return result.scalar()


def email_ja_existe(email: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            text("SELECT 1 FROM inscricoes WHERE email = :email"), {"email": email.strip().lower()}
        ).fetchone()
        return row is not None


def listar_inscricoes(apenas_nao_sorteados: bool = False):
    query = "SELECT * FROM inscricoes"
    if apenas_nao_sorteados:
        query += " WHERE sorteado = 0"
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        rows = conn.execute(text(query)).mappings().all()
        return [_row_to_dict(dict(r)) for r in rows]


def contar_inscricoes():
    with get_conn() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM inscricoes")).scalar()
        sorteados = conn.execute(text("SELECT COUNT(*) FROM inscricoes WHERE sorteado = 1")).scalar()
        return {"total": total, "sorteados": sorteados, "disponiveis": total - sorteados}


def sortear_vencedor(excluir_ja_sorteados: bool = True):
    """Sorteia 1 inscrição aleatória usando o RANDOM() do banco (funciona igual em SQLite e Postgres)."""
    query = "SELECT * FROM inscricoes"
    if excluir_ja_sorteados:
        query += " WHERE sorteado = 0"
    query += " ORDER BY RANDOM() LIMIT 1"
    with get_conn() as conn:
        row = conn.execute(text(query)).mappings().fetchone()
        if not row:
            return None
        vencedor = _row_to_dict(dict(row))
        posicao = conn.execute(text("SELECT COALESCE(MAX(posicao_sorteio), 0) + 1 FROM inscricoes")).scalar()
        conn.execute(
            text("UPDATE inscricoes SET sorteado = 1, sorteado_em = :dt, posicao_sorteio = :pos WHERE id = :id"),
            {"dt": datetime.utcnow().isoformat(), "pos": posicao, "id": vencedor["id"]},
        )
        vencedor["sorteado"] = 1
        vencedor["posicao_sorteio"] = posicao
        return vencedor


def listar_vencedores():
    with get_conn() as conn:
        rows = conn.execute(
            text("SELECT * FROM inscricoes WHERE sorteado = 1 ORDER BY posicao_sorteio ASC")
        ).mappings().all()
        return [_row_to_dict(dict(r)) for r in rows]


def resetar_sorteio():
    """Zera todos os sorteios (mantém as inscrições) para recomeçar o sorteio."""
    with get_conn() as conn:
        conn.execute(text("UPDATE inscricoes SET sorteado = 0, sorteado_em = NULL, posicao_sorteio = NULL"))


def excluir_inscricao(inscricao_id: int):
    with get_conn() as conn:
        conn.execute(text("DELETE FROM inscricoes WHERE id = :id"), {"id": inscricao_id})


def _row_to_dict(d: dict) -> dict:
    try:
        d["extra"] = json.loads(d.get("extra") or "{}")
    except (json.JSONDecodeError, TypeError):
        d["extra"] = {}
    return d
