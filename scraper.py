import re
import pdfplumber
import requests

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

def parse_pdf(pdf_path: str):
    """le o arquivo PDF pagina por pagina e extrai os dados"""
    print(f"lendo o arquivo: {pdf_path}...")
    full_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text += text + "\n"
                
    print(f"leitura feita!!! total de caracteres lidos: {len(full_text)}")
    
    # processa a extraçao
    entities = extract_entities_from_text(full_text)
    
    print(f" CNPJs Encontrados ({len(entities['cnpjs'])}): {entities['cnpjs']}")
    print(f" Valores Encontrados ({len(entities['valores'])}): {entities['valores']}")
    print(f" Processos Encontrados ({len(entities['processos'])}): {entities['processos']}")
    
    return entities

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
    
    print("testando com textos de exemplo:")
    res = extract_entities_from_text(sample_text)
    print("CNPJs:", res["cnpjs"])
    print("Valores:", res["valores"])
    print("Processos:", res["processos"])