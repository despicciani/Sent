import os
import re
import pdfplumber
import requests
from database import engine, SessionLocal, Base
from models import DiarioOficial, ContratoAuditado
from classifier import classify_text

# se nao existir, cria as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# padroes de regex
PATTERNS = {
    "cnpj": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
    "valor": r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}",
    "processo": r"\b\d{2}/\d{3,6}/\d{4}\b" 
}

def download_diario(edicao_id: int) -> str:
    """Baixa o PDF do DO-RIO a partir do ID da edição.""" # o mais recente eh o do dia 31/07, com o id 14887
    url = f"https://doweb.rio.rj.gov.br/portal/edicoes/download/{edicao_id}"
    file_path = os.path.join(DOWNLOAD_DIR, f"rio_de_janeiro_edicao_{edicao_id}.pdf")
    
    print(f"Baixando Diário Oficial (Edição #{edicao_id}) de: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Download concluído: '{file_path}'")
        return file_path
    else:
        raise Exception(f"Falha ao baixar PDF. Código HTTP: {response.status_code}")

def extract_entities_from_text(text: str) -> dict:
    """extrai CNPJs, valores financeiros e numeros de processo usando regex"""
    extracted = {
        "cnpjs": list(set(re.findall(PATTERNS["cnpj"], text))),
        "valores": list(set(re.findall(PATTERNS["valor"], text))),
        "processos": list(set(re.findall(PATTERNS["processo"], text)))
    }
    return extracted

def parse_valor_float(valor_str: str) -> float:
    """Converte 'R$ 450.000,00' para 450000.0 (Float)."""
    clean_str = valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
    return float(clean_str)

def extract_text_from_pdf(pdf_path: str) -> str:
    full_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # ignora a capa (primeira página) se for apenas cabeçalho de capa
            if page_num == 0:
                text_capa = page.extract_text() or ""
                if "Prefeito" in text_capa and "Gabinete do Prefeito" in text_capa:
                    continue

            width = page.width
            height = page.height
            
            # divide a página no meio exato (2 colunas)
            col_esquerda = page.crop((0, 0, width / 2, height)).extract_text()
            col_direita = page.crop((width / 2, 0, width, height)).extract_text()
            
            if col_esquerda:
                full_text.append(col_esquerda)
            if col_direita:
                full_text.append(col_direita)
                
    texto_completo = "\n".join(full_text)
    return texto_completo

def split_into_contract_blocks(text: str) -> list:
    """Quebra o diário em extratos usando o delimitador genérico EXTRATO DE."""
    delimiter_pattern = r"(?=\bEXTRATO\s+DE\b)"
    blocks = re.split(delimiter_pattern, text, flags=re.IGNORECASE)
    
    relevant_blocks = []
    for block in blocks:
        # garante que o bloco é um extrato e contém uma menção a Objeto ou Partes
        is_extrato = re.match(r"^\s*EXTRATO\s+DE", block, re.IGNORECASE)
        has_objeto_or_partes = bool(re.search(r"\b(?:OBJETO|PARTES)\b", block, re.IGNORECASE))
        
        if is_extrato and has_objeto_or_partes:
            clean_block = re.sub(r"\s+", " ", block).strip()
            relevant_blocks.append(clean_block)
            
    print(f"extratos individuais identificados: {len(relevant_blocks)}")
    return relevant_blocks


def processar_diario_real(edicao_id: int):
    """Pipeline completo de ingestão de um Diário Oficial real."""
    db = SessionLocal()
    try:
        # download do PDF
        pdf_path = download_diario(edicao_id)
        nome_arquivo = os.path.basename(pdf_path)
        
        # registro do diário na tabela pai
        novo_diario = DiarioOficial(nome_arquivo=nome_arquivo)
        db.add(novo_diario)
        db.commit()
        db.refresh(novo_diario)
        
        # leitura e Chunking
        texto_completo = extract_text_from_pdf(pdf_path)
        blocos_contratos = split_into_contract_blocks(texto_completo)
        
        contratos_salvos = 0
        for bloco in blocos_contratos:
            cnpjs = re.findall(PATTERNS["cnpj"], bloco)
            valores = re.findall(PATTERNS["valor"], bloco)
            processos = re.findall(PATTERNS["processo"], bloco)
            
            cnpj = cnpjs[0] if cnpjs else None
            num_processo = processos[0] if processos else None
            valor_num = parse_valor_float(valores[0]) if valores else None
            
            # Classificação por IA
            categoria_ia = classify_text(bloco)
            
            contrato = ContratoAuditado(
                diario_id=novo_diario.id,
                cnpj_empresa=cnpj,
                valor=valor_num,
                numero_processo=num_processo,
                categoria=categoria_ia,
                texto_contexto=bloco[:1000] # Salva os primeiros 1000 caracteres como amostra
            )
            db.add(contrato)
            contratos_salvos += 1
            
        db.commit()
        print(f"Finalizado! {contratos_salvos} contratos extraídos e salvos no Postgres")
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao processar diário oficial: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    EDICAO_TESTE = 14887
    processar_diario_real(EDICAO_TESTE)