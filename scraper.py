import re
import pdfplumber
from database import engine, SessionLocal, Base
from models import DiarioOficial, ContratoAuditado

# se nao existir, cria as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# padroes de regex
PATTERNS = {
    "cnpj": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
    "valor": r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}",
    "processo": r"\b\d{2}/\d{3,6}/\d{4}\b" 
}

def extract_entities_from_text(text: str) -> dict:
    """extrai CNPJs, valores financeiros e numeros de processo usando regex"""
    extracted = {
        "cnpjs": list(set(re.findall(PATTERNS["cnpj"], text))),
        "valores": list(set(re.findall(PATTERNS["valor"], text))),
        "processos": list(set(re.findall(PATTERNS["processo"], text)))
    }
    return extracted

def parse_valor_float(valor_str: str) -> float:
    """Converte 'R$ 450.000,00' para 450000.0 (Float)."""
    clean_str = valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
    return float(clean_str)


def salvar_no_banco(nome_arquivo: str, texto_amostra: str):
    """Extrai dados e grava no PostgreSQL."""
    db = SessionLocal()
    try:
        # registra o diário lido
        novo_diario = DiarioOficial(nome_arquivo=nome_arquivo)
        db.add(novo_diario)
        db.commit()
        db.refresh(novo_diario)

        # extrai dados
        entities = extract_entities_from_text(texto_amostra)
        
        # associação simples dos dados encontrados para simulação
        cnpj = entities["cnpjs"][0] if entities["cnpjs"] else None
        num_processo = entities["processos"][0] if entities["processos"] else None
        
        valor_num = None
        if entities["valores"]:
            valor_num = parse_valor_float(entities["valores"][0])

        # cria o registro do contrato
        novo_contrato = ContratoAuditado(
            diario_id=novo_diario.id,
            cnpj_empresa=cnpj,
            valor=valor_num,
            numero_processo=num_processo,
            texto_contexto=texto_amostra.strip()
        )
        
        db.add(novo_contrato)
        db.commit()
        
        print(f"contrato ID {novo_contrato.id} salvo no PostgreSQL com sucesso.")
        
    except Exception as e:
        db.rollback()
        print(f"erro ao salvar no banco: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # teste rápido com um texto de exemplo
    sample_text = """
    EXTRATO DE CONTRATO Nº 102/2024
    PROCESSO ADMINISTRATIVO: 09/123/2024
    PARTES: Secretaria Municipal de Infraestrutura e a empresa CONSTRUTORA RIO LTDA, CNPJ: 12.345.678/0001-90.
    OBJETO: Reformas nas vias urbanas do bairro Centro.
    VALOR TOTAL: R$ 450.000,00 (quatrocentos e cinquenta mil reais).
    DOTAÇÃO ORÇAMENTÁRIA: Saúde e Infraestrutura.
    """
    
    print("testando ingestão no postgreSQL")
    salvar_no_banco("diario_teste_2026.pdf", sample_text)