from typing import List, Optional
from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import ContratoAuditado, DiarioOficial

app = FastAPI(
    title="Sent - API de Auditoria Digital",
    description="API REST para consulta e filtragem de contratos auditados nos Diários Oficiais do Rio de Janeiro.",
    version="1.0.0"
)

# esquema de saída (Pydantic Schema) 
# define exatamente qual formato JSON a API enviará de resposta
class ContratoResponse(BaseModel):
    id: int
    diario_id: int
    cnpj_empresa: Optional[str] = None
    valor: Optional[float] = None
    numero_processo: Optional[str] = None
    categoria: str
    texto_contexto: Optional[str] = None
    criado_em: datetime

    class Config:
        from_attributes = True


# endpoints

@app.get("/", tags=["Status"])
def root():
    return {
        "sistema": "Sent - Auditor Digital",
        "status": "online",
        "documentacao": "/docs"
    }


@app.get("/contratos", response_model=List[ContratoResponse], tags=["Contratos"])
def listar_contratos(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria (ex: Saúde, Educação, Infraestrutura)"),
    limit: int = Query(20, description="Quantidade máxima de registros a retornar"),
    db: Session = Depends(get_db)
):
    """Retorna a lista de contratos auditados, permitindo filtro opcional por categoria."""
    query = db.query(ContratoAuditado)
    
    if categoria:
        query = query.filter(ContratoAuditado.categoria.ilike(f"%{categoria}%"))
        
    contratos = query.order_by(ContratoAuditado.id.desc()).limit(limit).all()
    return contratos


@app.get("/estatisticas", tags=["Estatísticas"])
def obter_estatisticas(db: Session = Depends(get_db)):
    """Gera um resumo de gastos totais acumulados e quantidade de auditorias por categoria."""
    resultado = (
        db.query(
            ContratoAuditado.categoria,
            func.sum(ContratoAuditado.valor).label("total_gasto"),
            func.count(ContratoAuditado.id).label("total_contratos")
        )
        .group_by(ContratoAuditado.categoria)
        .all()
    )
    
    estatisticas = {}
    for cat, total, count in resultado:
        estatisticas[cat] = {
            "total_gasto_brl": round(total, 2) if total else 0.0,
            "quantidade_contratos": count
        }
        
    return {"resumo_por_categoria": estatisticas}