import os
from classifier import explain_classification
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
def tool_estatisticas_por_categoria(categoria: str) -> str:
    """
    ÚTIL PARA: Obter a quantidade de contratos E o valor total gasto de uma categoria.
    Exemplo: 'Quantos contratos de Infraestrutura e qual o total gasto?'
    """
    print(f"\n[Agente usou a ferramenta: SQL Estatísticas] -> Categoria: '{categoria}'")
    db: Session = SessionLocal()
    try:
        contratos = db.query(ContratoAuditado).filter(ContratoAuditado.categoria.ilike(f"%{categoria}%")).all()
        total = sum(float(c.valor) for c in contratos if c.valor)
        quantidade = len(contratos)
        return f"A categoria '{categoria}' possui {quantidade} contratos registrados. O valor total exato gasto é de R$ {total:,.2f}."
    except Exception as e:
        return f"Erro no banco de dados: {str(e)}"
    finally:
        db.close()

@tool
def tool_auditar_classificacao(texto_do_contrato: str) -> str:
    """
    ÚTIL PARA: Explicar o POR QUÊ um contrato recebeu determinada categoria. 
    Use isso quando o usuário perguntar o motivo ou a explicação de uma classificação.
    """
    print("\n[Agente usou a ferramenta: Auditoria Híbrida (Scikit-Learn -> LLM)]")
    
        # chama a Inteligência Antiga (O Scikit-Learn determinístico)
    try:
        explicacao_ml = explain_classification(texto_do_contrato)
        
        # passa a matemática seca para o LLM explicar
        return f"""
        O classificador matemático analisou o texto: '{explicacao_ml["texto_analisado"]}'.
        O modelo concluiu matematicamente que pertence à categoria: '{explicacao_ml["categoria"]}'.
        O grau de certeza matemática (confidence score) do algoritmo foi de {explicacao_ml["confidence"] * 100:.2f}%.
        """

    except Exception as e:
        # Blindagem: Se o CSV/Joblib não estiver no Docker, o Agente não crasha a API.
        # Ele recebe este erro e formula uma desculpa educada para o usuário.
        return f"Falha no sistema de Machine Learning legado: Arquivo de modelo ou dataset não encontrado no servidor. Erro técnico: {str(e)}"

# lista de ferramentas disponíveis
tools = [tool_busca_semantica, tool_estatisticas_por_categoria, tool_auditar_classificacao]

# cria o grafo de raciocínio do Agente
agente_auditor = create_agent(llm, tools)

def fazer_pergunta_ao_agente(pergunta: str):
    print(f"\n{'='*50}\nUsuario: {pergunta}")
    
    # Envia a mensagem para o agente
    resultado = agente_auditor.invoke(
        {"messages": [HumanMessage(content=pergunta)]}
    )
    
    # o langgraph devolve o historico de msgs, sendo a última a final
    resposta_final = resultado["messages"][-1].content
    print(f"\nSent: {resposta_final}\n{'='*50}")


if __name__ == "__main__":
    contrato_exemplo = "OBJETO: Prorrogação de contratação temporária de Médicos para atender necessidade de excepcional interesse público identificada em unidades hospitalares da Secretaria Municipal de Saúde"
    
    fazer_pergunta_ao_agente(f"Por que o seguinte contrato foi classificado dessa forma? Contrato: '{contrato_exemplo}'")