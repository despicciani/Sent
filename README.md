<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/Llama_3.3_70B-0467DF?style=for-the-badge&logo=meta&logoColor=white" />
  <img src="https://img.shields.io/badge/pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
</p>

# 🛡️ Sent — Auditor Inteligente de Diários Oficiais

> **Pipeline autônomo de auditoria de gastos públicos** que raspa, extrai, classifica e audita contratos publicados no Diário Oficial do Município do Rio de Janeiro (DO-RIO), combinando **NLP clássico**, **busca vetorial semântica** e um **agente de IA com LLM** para responder perguntas em linguagem natural sobre o dinheiro público.

---

## 🎯 O Problema

O Diário Oficial do Rio de Janeiro publica diariamente dezenas de extratos contratuais em **PDFs de layout complexo** — múltiplas colunas, formatação inconsistente e linguagem burocrática densa. Auditar manualmente esses documentos é inviável. O Sentinela automatiza esse processo de ponta a ponta.

---

## 🏛️ Arquitetura

O sistema opera em dois estágios: **ingestão de dados** e **consulta inteligente**.

```
                           ┌─────────────────────────────────────────────────────┐
                           │              ESTÁGIO 1 — INGESTÃO                   │
                           │                                                     │
  ┌──────────────┐    ┌────┴──────┐    ┌──────────────┐    ┌──────────────────┐  │
  │   DO-RIO     │───▶│  Crop     │───▶│  Extrator    │───▶│  Classificador   │  │
  │   (PDF)      │    │  Vertical │    │  RegEx       │    │  4 Camadas       │  │
  │              │    │  2 cols   │    │  CNPJ/R$/    │    │  (KW → Orçamento │  │
  │  pdfplumber  │    │           │    │  Processo    │    │   → Órgão → ML)  │  │
  └──────────────┘    └───────────┘    └──────────────┘    └────────┬─────────┘  │
                                                                    │            │
                                                                    ▼            │
                           ┌────────────────────────────────────────────────┐     │
                           │             PostgreSQL + pgvector              │     │
                           │  ┌─────────────────┐  ┌────────────────────┐  │     │
                           │  │ contratos_       │  │ embeddings         │  │     │
                           │  │ auditados        │  │ Vector(384)        │  │     │
                           │  │ (CNPJ, R$, cat)  │  │ cosine_distance    │  │     │
                           │  └─────────────────┘  └────────────────────┘  │     │
                           └──────────────────────────┬─────────────────────┘     │
                                                      │                          │
                           └──────────────────────────┼──────────────────────────┘
                                                      │
                           ┌──────────────────────────┼──────────────────────────┐
                           │         ESTÁGIO 2 — CONSULTA INTELIGENTE            │
                           │                          │                          │
                           │    ┌─────────────────────▼──────────────────────┐   │
                           │    │       Agente LangGraph (Llama 3.3 70B)     │   │
                           │    │                                            │   │
                           │    │  🔧 tool_busca_semantica (RAG)             │   │
                           │    │  🔧 tool_estatisticas_por_categoria (SQL)  │   │
                           │    │  🔧 tool_auditar_classificacao (XAI)       │   │
                           │    └────────────────────────────────────────────┘   │
                           │                          │                          │
                           │                ┌─────────▼──────────┐               │
                           │                │   FastAPI REST API  │               │
                           │                │   /api/v2/ask       │               │
                           │                │   /api/v2/search    │               │
                           │                └────────────────────┘               │
                           └─────────────────────────────────────────────────────┘
```

---

## ⚙️ Pipeline de Ingestão (Detalhado)

### 1. Download & Parsing com Crop Vertical

O PDF do DO-RIO possui layout de **duas colunas**. Bibliotecas de extração de texto leem da esquerda para a direita, fundindo linhas de colunas distintas. A solução é fatiar cada página ao meio antes da extração:

```python
col_esquerda = page.crop((0, 0, width / 2, height)).extract_text()
col_direita  = page.crop((width / 2, 0, width, height)).extract_text()
```

### 2. Chunking Determinístico por Delimitador

Os blocos são segmentados via **regex case-sensitive** no padrão `EXTRATO DE [TIPO]`, onde `TIPO` abrange contratos, termos, convênios, patrocínios, apostilamentos, etc. Cada bloco é validado com filtros rígidos que exigem a presença das cláusulas `OBJETO` e `PARTES`/`INSTRUMENTO`, descartando automaticamente tabelas de preço e avisos de publicação.

### 3. Extração de Entidades (RegEx)

| Entidade           | Padrão                                      |
|--------------------|---------------------------------------------|
| CNPJ               | `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`          |
| Valor Financeiro   | `R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}`          |
| Nº de Processo     | `\d{2}/\d{3,6}/\d{4}`                      |

### 4. Classificação Híbrida em 4 Camadas

O classificador opera em cascata — cada camada é acionada apenas se a anterior não resolveu:

| Camada | Método                          | Exemplo                                                        |
|--------|---------------------------------|----------------------------------------------------------------|
| **1**  | Palavras-chave no OBJETO        | `"obra"` → Infraestrutura, `"carnaval"` → Cultura             |
| **2**  | Função Orçamentária (PT)        | Código `10` → Saúde, `12` → Educação (Portaria STN nº 42/99)  |
| **3**  | Órgão Contratante               | SMS → Saúde, COMLURB → Infraestrutura, RIOTUR → Cultura       |
| **4**  | **ML (Fallback)**               | `LogisticRegression` + `TF-IDF` via scikit-learn               |

> A Camada 4 é acionada para órgãos centralizadores (Casa Civil, Gabinete do Prefeito) onde o contratante não revela a área temática. O modelo foi treinado com um dataset de contratos reais contendo ruído burocrático intencional para robustez.

### 5. Geração de Embeddings

Após a classificação, o campo `OBJETO` de cada contrato é extraído via regex e convertido em um vetor de **384 dimensões** pelo modelo `paraphrase-multilingual-MiniLM-L12-v2`, armazenado diretamente no PostgreSQL via **pgvector**.

---

## 🤖 RAG & Agente de IA

### Busca Semântica Vetorial

O endpoint `/api/v2/search` transforma a pergunta do usuário em um embedding e busca os contratos mais similares via **distância do cosseno** nativamente no PostgreSQL:

```python
resultados = db.query(ContratoAuditado).order_by(
    ContratoAuditado.embedding.cosine_distance(query_vector)
).limit(top_k).all()
```

### Agente Autônomo (LangGraph + Llama 3.3 70B)

O endpoint `/api/v2/ask` inicializa um **agente LangGraph** que decide autonomamente qual ferramenta usar para responder:

| Ferramenta                       | Quando usa                                                         |
|----------------------------------|--------------------------------------------------------------------|
| `tool_busca_semantica`           | Perguntas abertas sobre temas/assuntos de contratos                |
| `tool_estatisticas_por_categoria`| Consultas quantitativas (total gasto, quantidade por categoria)    |
| `tool_auditar_classificacao`     | Explicar **por que** um contrato recebeu determinada categoria     |

### Explicabilidade (XAI) — NLP Clássico + LLM

A ferramenta de auditoria combina as duas inteligências:

1. O **scikit-learn** classifica o texto e extrai o *confidence score* probabilístico
2. O **LLM** recebe a matemática bruta e sintetiza uma explicação compreensível em linguagem natural

```
Scikit-Learn (LogisticRegression)          LLM (Llama 3.3 70B)
┌──────────────────────────────┐     ┌──────────────────────────────────┐
│ Categoria: "Saúde"           │────▶│ "O contrato foi classificado     │
│ Confidence: 94.32%           │     │  como Saúde porque menciona      │
│ Texto: "contratação de       │     │  contratação de médicos para     │
│         médicos..."          │     │  unidades hospitalares da SMS."  │
└──────────────────────────────┘     └──────────────────────────────────┘
```

### Prompt Anti-Alucinação

O pipeline RAG utiliza um prompt de sistema com **diretrizes rígidas de grounding**: a LLM responde exclusivamente com base nos contratos recuperados do banco. Se nenhum contrato for relevante, ela declara explicitamente a ausência de evidências.

---

## 🌐 Endpoints da API

### v1.0 — Consulta Relacional

| Método | Rota             | Descrição                                                   |
|--------|------------------|-------------------------------------------------------------|
| `GET`  | `/`              | Health check                                                |
| `GET`  | `/contratos`     | Lista contratos com filtro por `categoria` e `limit`        |
| `GET`  | `/estatisticas`  | Total gasto acumulado e distribuição por categoria           |

### v2.0 — Inteligência Artificial

| Método | Rota               | Descrição                                                                |
|--------|---------------------|-------------------------------------------------------------------------|
| `POST` | `/api/v2/search`   | Busca semântica vetorial por similaridade de cosseno                     |
| `POST` | `/api/v2/ask`      | Agente autônomo — decide entre RAG, SQL e XAI para responder             |

> 📖 Documentação interativa (Swagger UI) disponível em `http://localhost:8000/docs`

---

## 🗄️ Banco de Dados

PostgreSQL 16 com extensão **pgvector** para busca vetorial nativa.

### Tabela `diarios_oficiais`

| Coluna                  | Tipo          | Descrição                           |
|-------------------------|---------------|-------------------------------------|
| `id`                    | Integer (PK)  | Identificador único                 |
| `nome_arquivo`          | String(255)   | Nome do PDF baixado                 |
| `data_publicacao`       | DateTime      | Data de publicação                  |
| `status_processamento`  | String(50)    | Status do pipeline                  |

### Tabela `contratos_auditados`

| Coluna            | Tipo          | Descrição                                          |
|-------------------|---------------|-----------------------------------------------------|
| `id`              | Integer (PK)  | Identificador único                                 |
| `diario_id`       | Integer (FK)  | Referência ao diário de origem                      |
| `cnpj_empresa`    | String(20)    | CNPJ extraído via regex                             |
| `valor`           | Float         | Valor financeiro do contrato                        |
| `numero_processo` | String(50)    | Número do processo administrativo                   |
| `categoria`       | String(50)    | Setor classificado (Saúde, Educação, etc.)          |
| `texto_contexto`  | Text          | Trecho limpo do extrato contratual                  |
| `embedding`       | Vector(384)   | Vetor semântico para busca por similaridade         |

---

## 🛠️ Tech Stack

| Camada              | Tecnologia                                                                     |
|---------------------|--------------------------------------------------------------------------------|
| **API**             | FastAPI, Pydantic v2, Uvicorn                                                  |
| **LLM**             | Llama 3.3 70B (Groq), LangChain, LangGraph                                    |
| **Embeddings**      | Sentence-Transformers (`paraphrase-multilingual-MiniLM-L12-v2`)                |
| **NLP Clássico**    | scikit-learn (TF-IDF + Logistic Regression), joblib                            |
| **Vector DB**       | PostgreSQL 16 + pgvector (busca por distância do cosseno)                      |
| **Scraping & PDF**  | pdfplumber (crop vertical), requests                                           |
| **Infra**           | Docker, Docker Compose, WSL2                                                   |

---

## 📁 Estrutura do Projeto

```
sent/
├── main.py                          # API REST (FastAPI) — endpoints v1 e v2
├── agent.py                         # Agente LangGraph com tool-calling (Llama 3.3 70B)
├── rag.py                           # Pipeline RAG com prompt anti-alucinação
├── retrieval.py                     # Busca vetorial via cosine_distance (pgvector)
├── embeddings.py                    # Geração de embeddings (SentenceTransformers)
├── classifier.py                    # NLP clássico (TF-IDF + LogisticRegression)
├── scraper.py                       # Pipeline de ingestão: download → crop → regex → classificação
├── database.py                      # Engine SQLAlchemy + pgvector extension
├── models.py                        # ORM: DiarioOficial, ContratoAuditado (com Vector)
├── contratos_prefeitura_ruido.csv   # Dataset de treino com ruído burocrático
├── sent_classifier.joblib           # Modelo scikit-learn serializado
├── Dockerfile                       # Imagem Python 3.12-slim
├── docker-compose.yml               # API + PostgreSQL/pgvector
├── requirements.txt                 # Dependências do projeto
├── downloads/                       # PDFs baixados do DO-RIO
└── tests/                           # Testes
```

---

## 🚀 Executando o Projeto

### Pré-requisitos

- **Docker** e **Docker Compose**
- **Chave da API Groq** (gratuita em [console.groq.com](https://console.groq.com))

### 1. Clonar e configurar

```bash
git clone https://github.com/despicciani/Sent.git
cd Sent
```

Crie um arquivo `.env` na raiz:

```env
GROQ_API_KEY=gsk_sua_chave_aqui
```

### 2. Subir os serviços

```bash
docker compose up --build -d
```

Isso inicializa:
- **PostgreSQL 16** com pgvector na porta `5432`
- **API FastAPI** na porta `8000`

### 3. Ingerir um Diário Oficial

```bash
# Dentro do container
docker exec -it sent_api python scraper.py

# Ou localmente com venv
source venv/bin/activate
python scraper.py
```

### 4. Gerar embeddings dos contratos

```bash
docker exec -it sent_api python embeddings.py
```

### 5. Consultar

```bash
# Busca semântica
curl -X POST http://localhost:8000/api/v2/search \
  -H "Content-Type: application/json" \
  -d '{"query": "gastos com shows e festas", "top_k": 3}'

# Pergunta ao agente
curl -X POST http://localhost:8000/api/v2/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quanto foi gasto com contratos de Saúde?"}'
```

---

## 📈 Evolução do Projeto

O histórico de commits documenta a evolução arquitetural:

```
v1.0 — NLP Clássico
  ├── Extrator PDF com pdfplumber + regex
  ├── Classificador scikit-learn (TF-IDF + LogisticRegression)
  ├── API REST com FastAPI
  └── PostgreSQL relacional via Docker Compose

v2.0 — RAG + Agente de IA
  ├── pgvector para busca vetorial nativa
  ├── Sentence-Transformers para embeddings multilíngues
  ├── Pipeline RAG com Llama 3.3 70B (Groq)
  ├── Agente LangGraph com tool-calling autônomo
  └── Explicabilidade (XAI): scikit-learn + LLM
```