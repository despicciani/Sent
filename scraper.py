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

FUNC_ORCAMENTARIA_MAP = {
    "04": "Gestão Administrativa",
    "06": "Segurança",
    "08": "Assistência Social",
    "10": "Saúde",
    "12": "Educação",
    "13": "Cultura",
    "15": "Infraestrutura",
    "16": "Habitação",
    "18": "Meio Ambiente",
    "23": "Cultura",  # Turismo/Eventos
    "27": "Esporte e Lazer",
}
# palavras-chave
OBJETO_KEYWORDS = [
    (r"\b(?:obra|obras|pavimentação|asfaltamento|drenagem|tapa-buraco|revitalização|reforma|construção)\b", "Infraestrutura"),
    (r"\b(?:show|carnaval|feira\s+cultural|dança|apresentação|espetáculo|concerto|arraiá|festa|teatro|exposição)\b", "Cultura"),
    (r"\b(?:médico|médicos|hospital|upa|posto\s+de\s+saúde|vacina|medicamentos|saúde|enfermagem|ambulatorial)\b", "Saúde"),
    (r"\b(?:creche|creches|escola|escolas|alunos|professores|merenda|didático|pedagógico|ensino)\b", "Educação"),
    (r"\b(?:acolhimento|vulnerabilidade|famílias|população\s+em\s+situação\s+de\s+rua|psicossocial|abrigo)\b", "Assistência Social"),
    (r"\b(?:coleta\s+de\s+lixo|varrição|limpeza\s+urbana|aterro|resíduos|comlurb)\b", "Infraestrutura"),
]

SECRETARIA_MAP = {
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+SAÚDE|SECRETARIA\s+DE\s+SAÚDE|SMS|RIOSAÚDE|EMPRESA\s+PÚBLICA\s+DE\s+SAÚDE)\b": "Saúde",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+EDUCAÇÃO|SECRETARIA\s+DE\s+EDUCAÇÃO|SME|COORDENADORIA\s+REGIONAL\s+DE\s+EDUCAÇÃO|CRE|PCRJ/SME)\b": "Educação",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+CULTURA|SECRETARIA\s+DE\s+CULTURA|SMC|RIOTUR|FUNDAÇÃO\s+CULTURAL)\b": "Cultura",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+INFRAESTRUTURA|SECRETARIA\s+DE\s+INFRAESTRUTURA|SMI|SECIS|OBRAS)\b": "Infraestrutura",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+ASSISTÊNCIA\s+SOCIAL|SECRETARIA\s+DE\s+ASSISTÊNCIA\s+SOCIAL|SMAS)\b": "Assistência Social",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+MEIO\s+AMBIENTE|SECRETARIA\s+DE\s+MEIO\s+AMBIENTE|SMAC)\b": "Meio Ambiente",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+TRANSPORTES?|SECRETARIA\s+DE\s+TRANSPORTES?|SMTR)\b": "Transporte",
    r"\b(?:SECRETARIA\s+MUNICIPAL\s+DE\s+ORDEM\s+PÚBLICA|SECRETARIA\s+DE\s+SEGURANÇA|SEOP|GUARDA\s+MUNICIPAL)\b": "Segurança",
    r"\b(?:COMPANHIA\s+MUNICIPAL\s+DE\s+LIMPEZA\s+URBANA|COMLURB)\b": "Infraestrutura",
    r"\b(?:MULTIRIO)\b": "Educação",
}

PATTERNS = {
    "cnpj": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
    "valor": r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}",
    "processo": r"\b\d{2}/\d{3,6}/\d{4}\b" 
}

VALID_ATOS_REGEX = r"(?:CONTRATO|TERMO|INSTRUMENTO|CONVÊNIO|PATROCÍNIO|FOMENTO|COLABORAÇÃO|DISTRATO|APOSTILAMENTO|CANCELAMENTO|REGISTRO)"
STRICT_DELIMITER = r"(?=\bEXTRATO\s+DE\s+" + VALID_ATOS_REGEX + r"\b)"
VALID_HEADER_PATTERN = r"^EXTRATO\s+DE\s+" + VALID_ATOS_REGEX + r"\b"

def clean_trailing_noise(text: str) -> str:
    """
    Remove títulos de secretarias ou avisos que ficaram pendurados no final do bloco devido à quebra de página/coluna.
    """
    header_regex = r"\b(?:SECRETARIA\s+MUNICIPAL\b|EMPRESA\s+PÚBLICA\b|COMPANHIA\s+MUNICIPAL\b|SUBPREFEITURA\b|AVISO\s+DE\b|PREGÃO\s+ELETRÔNICO\b|COMPANHIA\b|FUNDAÇÃO\b|INSTITUTO\b)"
    
    # se houver cabeçalho de seção nos últimos 120 caracteres do bloco, remove do cabeçalho em diante
    if len(text) > 120:
        head_part = text[:-120]
        tail_part = text[-120:]
        
        match = re.search(header_regex, tail_part, re.IGNORECASE)
        if match:
            tail_cleaned = tail_part[:match.start()].strip()
            return (head_part + tail_cleaned).strip()
            
    return text.strip()

def extrair_apenas_objeto(texto: str) -> str:
    match = re.search(
        r"OBJETO(?:\s+DO\s+CONTRATO)?:\s*(.*?)(?=\s*(?:\bVALOR(?:\s+GLOBAL|\s+ESTIMADO|\s+TOTAL)?\b\s*:|\bDOTAÇÃO(?:\s+ORÇAMENTÁRIA)?\b\s*:|\bPRAZO(?:\s+DE\s+VIGÊNCIA|\s+DE\s+CONTRATAÇÃO)?\b\s*:|\bFUNDAMENTO(?:\s+LEGAL)?\b\s*:|\bASSINATURA\b\s*:|\bNATUREZA(?:\s+DA\s+DESPESA)?\b\s*:|\bPROGRAMA(?:\s+DE\s+TRABALHO)?\b\s*:|\bNOTA(?:\s+DE\s+EMPENHO)?\b\s*:|\bPARTES\b\s*:|\bRAZÃO\b\s*:|$))",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return texto.strip()

def parse_programa_trabalho(text: str):
    """Extrai a Função Orçamentária a partir do código do Programa de Trabalho."""
    match = re.search(r"PROGRAMA(?:\s+DE\s+TRABALHO)?(?:\s*Nº)?:?\s*([0-9\.\s]+)", text, re.IGNORECASE)
    if not match:
        return None
    pt_str = match.group(1).replace(" ", "")
    tokens = [t for t in pt_str.split(".") if t.isdigit()]

    for t in tokens[1:]:  # pula o primeiro token, que é o código do órgão
        t_z = t.zfill(2)
        if t_z in FUNC_ORCAMENTARIA_MAP and len(t) <= 2:
            return FUNC_ORCAMENTARIA_MAP[t_z], t_z
    return None

def classificar_extrato(raw_text: str) -> str:
    """Classificador em 4 Camadas de Decisão."""
    cleaned = clean_trailing_noise(raw_text)
    objeto_txt = extrair_apenas_objeto(cleaned)

    # camada 1: Palavras-chave explícitas no OBJETO (Peso Máximo)
    for kw_pattern, cat_kw in OBJETO_KEYWORDS:
        if re.search(kw_pattern, objeto_txt, re.IGNORECASE):
            return cat_kw

    # Identifica o Contratante
    partes_match = re.search(r"(?:PARTES|CONTRATANTE|ÓRGÃO\s+GESTOR):\s*(.*?)(?=\s*(?:OBJETO|VALOR|DOTAÇÃO|PRAZO|$))", cleaned, re.IGNORECASE | re.DOTALL)
    partes_text = partes_match.group(1) if partes_match else cleaned
    is_casa_civil = bool(re.search(r"\b(?:CASA\s+CIVIL|GABINETE\s+DO\s+PREFEITO)\b", partes_text, re.IGNORECASE))

    # camada 2: Programa de Trabalho (Função Orçamentária)
    pt_res = parse_programa_trabalho(cleaned)
    if pt_res:
        cat_pt, cod_pt = pt_res
        if is_casa_civil and cod_pt in ["04", "06"]:
            return "Gestão Administrativa"
        if cat_pt != "Gestão Administrativa":
            return cat_pt

    # camada 3: Órgão Específico contratante
    for pattern, cat_sec in SECRETARIA_MAP.items():
        if re.search(pattern, partes_text, re.IGNORECASE) or re.search(pattern, cleaned[:150], re.IGNORECASE):
            return cat_sec

    # camada 4: Fallback para Casa Civil / IA
    if is_casa_civil:
        return "Gestão Administrativa"

    return classify_text(objeto_txt)


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
    """Converte 'R$ 450.000,00' para 450000.0."""
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

def is_valid_contract_block(block: str) -> bool:
    """garante que APENAS extratos contratuais legítimos entram no banco."""

    clean = block.strip()
    starts_with_extrato = bool(re.match(r"^EXTRATO\s+DE\b", clean, re.IGNORECASE))
    has_objeto = bool(re.search(r"\bOBJETO\b", clean, re.IGNORECASE))

    has_partes_or_inst = bool(re.search(
        r"\b(?:PARTES|PARTICIPANTES|CONTRATANTE|ÓRGÃO\s+GESTOR|INSTRUMENTO|CONTRATO|TERMO|ATA|CONVÊNIO)\b", 
        clean, 
        re.IGNORECASE
    ))
    
    return has_partes_or_inst and has_objeto and starts_with_extrato

def split_into_contract_blocks(text: str) -> list:
    # divisão Case-Sensitive para ignorar "extrato de cordo..." minúsculo
    blocks = re.split(STRICT_DELIMITER, text)

    relevant_blocks = []
    for block in blocks:
        clean_block = re.sub(r"\s+", " ", block).strip()

        if is_valid_contract_block(clean_block):
            relevant_blocks.append(clean_block)

    print(f"extratos válidos identificados: {len(relevant_blocks)}")
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
            bloco_sem_ruido = clean_trailing_noise(bloco)

            cnpjs = re.findall(PATTERNS["cnpj"], bloco_sem_ruido)
            valores = re.findall(PATTERNS["valor"], bloco_sem_ruido)
            processos = re.findall(PATTERNS["processo"], bloco_sem_ruido)

            cnpj = cnpjs[0] if cnpjs else None
            num_processo = processos[0] if processos else None
            valor_num = parse_valor_float(valores[0]) if valores else None
            
            # classificação
            categoria_final = classificar_extrato(bloco_sem_ruido)
            
            contrato = ContratoAuditado(
                diario_id=novo_diario.id,
                cnpj_empresa=cnpj,
                valor=valor_num,
                numero_processo=num_processo,
                categoria=categoria_final,
                texto_contexto=bloco_sem_ruido[:1000] 
            )
            db.add(contrato)
            contratos_salvos += 1
            
        db.commit()
        print(f"{contratos_salvos} contratos extraídos e salvos no Postgres")
        
    except Exception as e:
        db.rollback()
        print(f"erro ao processar diário oficial: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    EDICAO_TESTE = 14887
    processar_diario_real(EDICAO_TESTE)