from sqlalchemy.orm import Session
from database import SessionLocal
from models import ContratoAuditado
from sentence_transformers import SentenceTransformer

# carregamos o mesmo modelo usado dos embeddings
print("carregando modelo NLP")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def search_similar_contracts(query: str, top_k: int = 3):
    """
    Transforma a pergunta do usuário em vetor e busca no banco (pgvector)
    pelos contratos semanticamente mais próximos.
    """
    db: Session = SessionLocal()
    
    try:
        # transforma a query de texto em um array de 384 dimensões
        query_vector = model.encode(query).tolist()
        
        # busca no Postgres ordenando pela distancia do cosseno
        resultados = db.query(ContratoAuditado).order_by(
            ContratoAuditado.embedding.cosine_distance(query_vector)
        ).limit(top_k).all()
        
        return resultados
    finally:
        db.close()

if __name__ == "__main__":
    print("\n testando")
    
    perguntas_teste = [
        "Tem algum contrato sobre crianças ou escolas?",
        "Gastos com shows, palcos e festas",
        "Obras de infraestrutura urbana"
    ]
    
    for pergunta in perguntas_teste:
        print(f"\n\n Pergunta: '{pergunta}'")
        resultados = search_similar_contracts(pergunta, top_k=2)
        
        for i, contrato in enumerate(resultados, 1):
            print(f"  [{i}] Categoria: {contrato.categoria} (Processo: {contrato.numero_processo or 'N/A'})")
            print(f"      Trecho: {contrato.texto_contexto[:150].strip()}...")