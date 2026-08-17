from typing import List, Optional
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime
from intelligence.retrieval import search_similar_contracts
from intelligence.agent import agente_auditor, HumanMessage
from db.database import get_db
from db.models import ContratoAuditado, DiarioOficial

app = FastAPI(
    title="Sent - API de Auditoria Digital",
    description="API REST para consulta e filtragem de contratos auditados nos Diários Oficiais do Rio de Janeiro.",
    version="2.0.0"
)

# esquema de saída (Pydantic Schema) 
# define exatamente qual formato JSON a API enviará de resposta
class ContratoResponse(BaseModel):
    id: int
    cnpj_empresa: Optional[str]
    valor: Optional[float]
    categoria: str
    texto_contexto: str

    class Config:
        from_attributes = True

class EstatisticasResponse(BaseModel):
    total_contratos: int
    total_gasto: float
    distribuicao_categorias: dict

class SearchRequest(BaseModel):
    query: str
    top_k: int = 3

class AgentRequest(BaseModel):
    question: str

# endpoints

# rotas versao 1.0.0
@app.get("/")
def read_root():
    return {"status": "Sent API online"}

@app.get("/contratos", response_model=List[ContratoResponse])
def get_contratos(categoria: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(ContratoAuditado)
    if categoria:
        query = query.filter(ContratoAuditado.categoria == categoria)
    return query.limit(limit).all()

@app.get("/estatisticas", response_model=EstatisticasResponse)
def get_estatisticas(db: Session = Depends(get_db)):
    total = db.query(func.count(ContratoAuditado.id)).scalar()
    soma_valores = db.query(func.sum(ContratoAuditado.valor)).scalar() or 0.0
    
    distribuicao = db.query(ContratoAuditado.categoria, func.count(ContratoAuditado.id)) \
                     .group_by(ContratoAuditado.categoria).all()
    
    return {
        "total_contratos": total,
        "total_gasto": float(soma_valores),
        "distribuicao_categorias": {cat: count for cat, count in distribuicao}
    }


# rotas versao 2.0.0
@app.post("/api/v2/search")
def busca_semantica_vetorial(request: SearchRequest):
    """encontra contratos pelo significado matemático do texto, usando embeddings locais (SentenceTransformers) e pgvector."""
    
    try:
        resultados = search_similar_contracts(request.query, request.top_k)
        
        if not resultados:
            return {"mensagem": "Nenhum contrato semanticamente próximo encontrado."}
            
        return [
            {
                "id": c.id,
                "categoria": c.categoria,
                "valor": float(c.valor) if c.valor else None,
                "texto": c.texto_contexto[:300] + "..." # retorna apenas um resumo
            }
            for c in resultados
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca vetorial: {str(e)}")

@app.post("/api/v2/ask")
def auditar_com_agente_ia(request: AgentRequest):
    """decide de forma autônoma se deve usar busca vetorial, comandos SQL ou a explicabilidade do Scikit-Learn para responder."""
    try:
        resultado = agente_auditor.invoke(
            {"messages": [HumanMessage(content=request.question)]}
        )
        # retorna a última mensagem gerada pela IA
        resposta_final = resultado["messages"][-1].content
        
        return {
            "pergunta": request.question,
            "resposta_agente": resposta_final
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"erro na execução do agente: {str(e)}")