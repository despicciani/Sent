from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from db.database import Base

class DiarioOficial(Base):
    __tablename__ = "diarios_oficiais"

    id = Column(Integer, primary_key=True, index=True)
    data_publicacao = Column(DateTime, default=datetime.utcnow)
    nome_arquivo = Column(String(255), nullable=False)
    status_processamento = Column(String(50), default="PROCESSADO")
    criado_em = Column(DateTime, default=datetime.utcnow)

    # relacionamento com os contratos extraídos dele
    contratos = relationship("ContratoAuditado", back_populates="diario")


class ContratoAuditado(Base):
    __tablename__ = "contratos_auditados"

    id = Column(Integer, primary_key=True, index=True)
    diario_id = Column(Integer, ForeignKey("diarios_oficiais.id"))
    
    cnpj_empresa = Column(String(20), index=True, nullable=True)
    valor = Column(Float, nullable=True)
    numero_processo = Column(String(50), index=True, nullable=True)
    categoria = Column(String(50), default="NAO_CLASSIFICADO") # saúde, educação
    texto_contexto = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    embedding = Column(Vector(384), nullable=True)

    diario = relationship("DiarioOficial", back_populates="contratos")