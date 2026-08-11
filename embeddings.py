import os
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from database import SessionLocal
from models import ContratoAuditado

# baixa e carrega o modelo NLP local
print("carregando modelo de embeddings")
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_and_save_embeddings():
    """Busca contratos sem embedding no banco, gera o vetor e salva"""
    db: Session = SessionLocal()
    
    # pega contratos que ainda não tem embedding gerado
    contratos_sem_vetor = db.query(ContratoAuditado).filter(ContratoAuditado.embedding == None).all()
    
    if not contratos_sem_vetor:
        print("todos os contratos já possuem embeddings")
        db.close()
        return

    print(f"gerando embeddings para {len(contratos_sem_vetor)} contratos")
    
    for contrato in contratos_sem_vetor:
        # pega o texto do contrato para gerar o vetor de contexto
        texto_para_vetorizar = contrato.texto_contexto
        
        # gera o embedding --- array de 384 dimensões
        vetor = model.encode(texto_para_vetorizar)
        
        # salva no banco
        contrato.embedding = vetor.tolist()
        
    db.commit()
    print("embeddings gerados e salvos com sucesso no Postgres")
    db.close()

if __name__ == "__main__":
    generate_and_save_embeddings()