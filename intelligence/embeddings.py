import os
import re
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import ContratoAuditado

# baixa e carrega o modelo NLP local
print("carregando modelo de embeddings")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def extrair_apenas_objeto(texto: str) -> str:
    """Extrai apenas a parte semântica importante do contrato para evitar ruído."""
    match = re.search(
        r"OBJETO(?:\s+DO\s+CONTRATO)?:\s*(.*?)(?=\s*(?:\bVALOR(?:\s+GLOBAL|\s+ESTIMADO|\s+TOTAL)?\b\s*:|\bDOTAÇÃO(?:\s+ORÇAMENTÁRIA)?\b\s*:|\bPRAZO(?:\s+DE\s+VIGÊNCIA|\s+DE\s+CONTRATAÇÃO)?\b\s*:|\bFUNDAMENTO(?:\s+LEGAL)?\b\s*:|\bASSINATURA\b\s*:|\bNATUREZA(?:\s+DA\s+DESPESA)?\b\s*:|\bPROGRAMA(?:\s+DE\s+TRABALHO)?\b\s*:|\bNOTA(?:\s+DE\s+EMPENHO)?\b\s*:|\bPARTES\b\s*:|\bRAZÃO\b\s*:|$))",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return texto.strip()

def generate_and_save_embeddings():
    """Busca contratos sem embedding no banco, gera o vetor e salva"""
    db: Session = SessionLocal()
    
    contratos = db.query(ContratoAuditado).all()    

    for contrato in contratos:
        objeto_limpo = extrair_apenas_objeto(contrato.texto_contexto)
        
        # Cria um texto focado na semântica: Categoria + Objeto real
        texto_semantico = f"Categoria: {contrato.categoria}. Objeto: {objeto_limpo}"
        
        vetor = model.encode(texto_semantico)
        contrato.embedding = vetor.tolist()
        
    db.commit()
    print("novos embeddings salvos com sucesso")
    db.close()

if __name__ == "__main__":
    generate_and_save_embeddings()