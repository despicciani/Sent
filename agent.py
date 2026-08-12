import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import ContratoAuditado
from retrieval import search_similar_contracts
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# instancia o LLM 
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0
)

@tool
def tool_busca_semantica(pergunta: str) -> str:
    """
    ÚTIL PARA: Perguntas abertas sobre o tema ou assunto dos contratos.
    Exemplo: 'Tem algum contrato sobre crianças?' ou 'Obras no asfalto'
    """
    print(f"\n[Agente usou a ferramenta: Busca Semântica] -> '{pergunta}'")
    resultados = search_similar_contracts(pergunta, top_k=3)
    if not resultados:
        return "Nenhum contrato encontrado com esse tema."
    
    resposta = ""
    for r in resultados:
        resposta += f"- Categoria: {r.categoria} | Valor: R${r.valor} | Objeto: {r.texto_contexto[:100]}...\n"
    return resposta

@tool
def tool_calcula_total_por_categoria(categoria: str) -> str:
    """
    ÚTIL PARA: Calcular a soma financeira exata de gastos de uma categoria específica.
    Exemplo: 'Quanto foi gasto em Saúde?' ou 'Qual o total em Educação?'
    """
    print(f"\n[Agente usou a ferramenta: SQL Soma de Gastos] -> Categoria: '{categoria}'")
    db: Session = SessionLocal()
    
    total = 0
    try:
        # busca exata ignorando maiúsculas/minúsculas
        contratos = db.query(ContratoAuditado).filter(ContratoAuditado.categoria.ilike(f"%{categoria}%")).all()
        for c in contratos:
            if c.valor:
                total += float(c.valor)
        return f"o total exato gasto na categoria '{categoria}' foi de R$ {total:,.2f}."
    finally:
        db.close()

# lista de ferramentas disponíveis
tools = [tool_busca_semantica, tool_calcula_total_por_categoria]

# cria o grafo de raciocínio do Agente
agente_auditor = create_agent(llm, tools)

def fazer_pergunta_ao_agente(pergunta: str):
    print(f"\n{'='*50}\n👤 USUÁRIO: {pergunta}")
    
    # Envia a mensagem para o agente
    resultado = agente_auditor.invoke(
        {"messages": [HumanMessage(content=pergunta)]}
    )
    
    # o langgraph devolve o historico de msgs, sendo a última a final
    resposta_final = resultado["messages"][-1].content
    print(f"\n🤖 AGENTE SENT: {resposta_final}\n{'='*50}")


if __name__ == "__main__":
    # Teste 1: Busca Semântica (Vetor)
    fazer_pergunta_ao_agente("Quais os contratos que falam sobre apresentações musicais e eventos de carnaval?")
    
    # Teste 2: Banco Relacional (SQL)
    fazer_pergunta_ao_agente("Faça a matemática exata de quanto dinheiro foi gasto na categoria Infraestrutura.")