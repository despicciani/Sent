import os
from openai import OpenAI
from retrieval import search_similar_contracts

client = OpenAI(api_key=os.environ.get("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
MODEL_NAME = "llama-3.1-8b-instant"


def answer_question_with_rag(question: str) -> str:
    print(f"\nbuscando evidências no banco para: '{question}'")
    
    # recupera os documentos semanticamente relevantes do Postgres (os top 3)
    contratos_relevantes = search_similar_contracts(question, top_k=3)
    
    if not contratos_relevantes:
        return "Não há contratos na base de dados para responder a essa pergunta."

    # monta o Contexto injetando os dados reais dos contratos
    contexto = ""
    for i, contrato in enumerate(contratos_relevantes, 1):
        contexto += f"\n--- CONTRATO {i} ---\n"
        contexto += f"Categoria: {contrato.categoria}\n"
        contexto += f"Valor: R$ {contrato.valor}\n"
        contexto += f"Texto Original: {contrato.texto_contexto}\n"

    # cria o Prompt de Sistema com regras rígidas anti-alucinação
    prompt_sistema = """
    Você é um assistente rigoroso de auditoria de contratos públicos do Rio de Janeiro.
    Sua missão é responder à pergunta do usuário baseando-se EXCLUSIVAMENTE nos contratos fornecidos no 'Contexto'.
    
   Diretrizes de Raciocínio:
    1. Interprete os termos do usuário de forma abrangente dentro do contexto público (ex: "festas/eventos" inclui shows de carnaval, feiras culturais, festivais, arraiás, etc.).
    2. Se um contrato no contexto se encaixar na pergunta, extraia quem são as Partes/Contratantes envolvidas, o Objeto (o que vai ser feito) e o Valor financeiro.
    3. Se o contexto tiver mais de um contrato relevante, some os valores ou liste-os separadamente.
    4. Se NENHUM contrato no contexto tiver relação, responda: "Não encontrei evidências suficientes nos contratos recuperados para responder a esta pergunta."
    5. Nunca invente dados. Seja direto e objetivo.
    """

    prompt_usuario = f"Contexto dos contratos extraídos do banco:\n{contexto}\n\nPergunta do usuário: {question}"

    print("enviando contexto para a LLM")
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.0 
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    perguntas_teste = [
        "Quais empresas ou órgãos estão envolvidos em eventos, shows ou festas e quanto isso vai custar no total?",
        "Foi contratado algum tipo de obra ou revitalização de infraestrutura? Descreva o local e o valor.",
        "Existe alguma compra de viaturas ou armas para a polícia?"
    ]
    
    for pergunta in perguntas_teste:
        resposta = answer_question_with_rag(pergunta)
        
        print("\n" + "="*60)
        print(f"Pergunta: {pergunta}")
        print("-" * 60)
        print(f"Sent:\n{resposta}")
        print("="*60)