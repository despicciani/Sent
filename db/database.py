import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text

# string de Conexão com o PostgreSQL rodando no Docker
# Formato: postgresql://USUARIO:SENHA@HOST:PORTA/NOME_DO_BANCO
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://sent_admin:sent_secret@localhost:5432/sent_db"
)

# gerencia a piscina de conexões com o Postgres
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    conn.commit()

# sessão para realizar operações (insert, select, etc)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base para a criação dos nossos modelos de tabela
Base = declarative_base()

def get_db():
    """Gera uma sessão do banco de dados e garante que ela seja fechada após o uso."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()