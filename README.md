# Sent - Auditor Digital de Diários Oficiais

O **Sent** é um pipeline autônomo de auditoria de gastos públicos a partir da raspagem, extração de entidades e classificação dos diários oficiais do município do Rio de Janeiro.

## Tech Stack
- **Linguagem:** Python
- **Banco de Dados:** PostgreSQL
- **Infraestrutura:** Docker & WSL2
- **Framework Web:** FastAPI
- **Machine Learning:** Scikit-Learn
# Sent - Auditor Digital de Diários Oficiais (DO-RIO)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-NLP-F7931E.svg)](https://scikit-learn.org/)

O **Sent** é um pipeline autônomo e auditor digital projetado para monitorar, extrair, higienizar e categorizar contratos públicos publicados no Diário Oficial do Município do Rio de Janeiro (DO-RIO). 

A ferramenta resolve o desafio de estruturar dados brutos contidos em arquivos PDF de layout complexo (múltiplas colunas, ruídos burocráticos e formatação não padronizada), disponibilizando os extratos auditados por meio de uma API REST performática, limpa e documentada.

---

## 📐 Arquitetura & Fluxo de Dados

O pipeline do **Sent** é executado em 5 etapas principais:

```text
[ DO-RIO PDF ] ──> [ Crop Vertical ] ──> [ Extrator RegEx ] ──> [ Classificador ] ──> [ PostgreSQL ] ──> [ FastAPI ]
 (Download)         (2 Colunas)          (CNPJ / R$ / Proc)    (4 Camadas / IA)    (SQLAlchemy)      (REST API)
```

1. **Inspecção & Coleta:** Download automatizado do caderno do dia via ID de edição do portal `doweb.rio.rj.gov.br`.
2. **Parsing com Crop Vertical:** Fatiamento das páginas do PDF ao meio para impedir a fusão horizontal de linhas de colunas vizinhas durante a extração de texto via `pdfplumber`.
3. **Delimitação & Higienização de Blocos:**
   * **Delimitador Estrito Case-Sensitive:** Quebra de extratos baseada no padrão `EXTRATO DE [TIPO]` em caixa alta.
   * **Filtro de Validação de Extrato:** Descarte automático de tabelas de preços de publicação e expedições do jornal (exige explicitamente as cláusulas `OBJETO` e `PARTES`/`INSTRUMENTO`).
   * **Limpador de Rodapé:** Remoção de títulos de secretarias pendurados ao final de blocos.
4. **Extração Determinística (RegEx):** Rastreamento de CNPJs, valores financeiros em reais (`R$`) e números de processo (padrões `Processo.Rio`, `SEI` e legado).
5. **Classificação Híbrida em 4 Camadas:**
   * **Camada 1 (Palavras-Chave no OBJETO):** Identificação de termos explícitos como *obra*, *médico*, *creche*, *carnaval*.
   * **Camada 2 (Programa de Trabalho / Orçamento):** Mapeamento do código funcional-programático orçamentário (Portaria STN nº 42/1999) extraindo funções como `12` (Educação), `13` (Cultura), `10` (Saúde), `08` (Assistência Social) e `15` (Infraestrutura).
   * **Camada 3 (Órgão Específico):** Mapeamento determinístico de secretarias contratantes (SMS, SME, SMI, SMC, SMAS, COMLURB, RIOSAÚDE, RIOTUR).
   * **Camada 4 (Fallback para Casa Civil / IA):** Roteamento de órgãos centralizadores para o modelo de Machine Learning (`LogisticRegression` + `TF-IDF`) treinado com vocabulário burocrático real.
6. **Persistência & Exposição:** Armazenamento relacional no PostgreSQL e disponibilização via FastAPI.

---

## 🛠️ Tech Stack

* **Linguagem:** Python 3.12
* **Extração & Parse de PDF:** `pdfplumber` (com técnica de crop vertical por coordenada)
* **Processamento de Texto & RegEx:** Módulo nativo `re`
* **Machine Learning & NLP:** `scikit-learn` (TF-IDF Vectorizer + Logistic Regression) e `pandas`
* **Banco de Dados & ORM:** PostgreSQL 16 + `SQLAlchemy`
* **API Framework:** `FastAPI` + `Pydantic` + `Uvicorn`
* **Infraestrutura & Conteinerização:** Docker, Docker Compose e WSL2 (Ubuntu)

---

## 📁 Estrutura do Projeto

```text
sent/
├── downloads/                  # Pasta local para armazenamento dos PDFs baixados
├── classifier.py               # Módulo de NLP (Treino e inferência com Scikit-Learn)
├── contratos_prefeitura_ruido.csv # Dataset sintético/real para treino da IA
├── database.py                 # Configuração da piscina de conexões do SQLAlchemy
├── Dockerfile                  # Imagem Docker da aplicação Python
├── docker-compose.yml          # Orquestrador dos serviços (API + PostgreSQL)
├── main.py                     # API REST FastAPI e endpoints de consulta
├── models.py                   # Mapeamento de tabelas (DiarioOficial, ContratoAuditado)
├── README.md                   # Documentação do projeto
├── requirements.txt            # Dependências e bibliotecas Python
└── scraper.py                  # Pipeline de ingestão, chunking, extração e classificação
```

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
* **Docker** e **Docker Compose** instalados (com suporte ao WSL2 ativado no Windows).
* **Git**.

### 1. Clonar o Repositório
```bash
git clone [https://github.com/despicciani/Sent.git](https://github.com/despicciani/Sent.git)
cd Sent
```

### 2. Executar via Docker Compose (Recomendado)
Suba o banco PostgreSQL e a API com um único comando:

```bash
docker compose up --build -d
```

O Docker criará e iniciará os serviços automaticamente:
* **PostgreSQL:** Escutando na porta `5432`.
* **API FastAPI:** Escutando na porta `8000`.

---

## 🧪 Rodando o Pipeline de Ingestão do Diário Oficial

Para rodar a raspagem e processar uma edição real do Diário Oficial dentro do ambiente:

```bash
# Executando dentro do container da API (recomendado)
docker exec -it sent_api python scraper.py

# Ou se estiver usando ambiente virtual local (venv)
source venv/bin/activate
python scraper.py
```

---

## 🌐 Endpoints da API REST

Com a aplicação rodando, acesse a **Documentação Interativa (Swagger UI)** em:
👉 `http://localhost:8000/docs`

### Principais Rotas:

* `GET /`
  * **Descrição:** Status da API.
* `GET /contratos`
  * **Descrição:** Retorna a lista de contratos auditados e extraídos.
  * **Parâmetros de Busca:** `categoria` (ex: `?categoria=Saúde`), `limit` (padrão: 20).
* `GET /estatisticas`
  * **Descrição:** Retorna métricas agregadas diretamente do banco de dados (total investido acumulado em R$ e quantidade de contratos por categoria).

---

## 🗄️ Esquema do Banco de Dados

### Tabela `diarios_oficiais`
* `id`: Chave primária (Integer, Auto-incremento).
* `nome_arquivo`: Nome do arquivo PDF baixado (String).
* `data_publicacao`: Data de publicação do diário (DateTime).
* `status_processamento`: Status da ingestão (String).

### Tabela `contratos_auditados`
* `id`: Chave primária (Integer, Auto-incremento).
* `diario_id`: Chave estrangeira para `diarios_oficiais.id`.
* `cnpj_empresa`: CNPJ da empresa contratada extraído via RegEx (String).
* `valor`: Valor monetário do contrato em Float (Numeric).
* `numero_processo`: Número do processo administrativo (String).
* `categoria`: Setor classificado (Saúde, Educação, Infraestrutura, Cultura, etc.).
* `texto_contexto`: Trecho limpo do extrato auditado (Text).
* `criado_em`: Timestamp do registro (DateTime).