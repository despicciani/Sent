import os
import re
import numpy as np
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

MODEL_FILE = "sent_classifier.joblib"
DATASET_FILE = "contratos_prefeitura_ruido.csv"

def extrair_apenas_objeto(texto: str) -> str:
    """
    Filtra o texto para extrair a cláusula de OBJETO do contrato, removendo ruídos de cabeçalhos (partes, números de processo, secretarias).
    """
    match = re.search(
        r"OBJETO(?:\s+DO\s+CONTRATO)?:\s*(.*?)(?=\s*(?:VALOR|DOTAÇÃO|PRAZO|FUNDAMENTO|ASSINATURA|$))",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return texto.strip()


def train_and_save_model():
    """
    Carrega o dataset CSV com ruído administrativo, pré-processa o texto
    e treina o modelo de Regressão Logística com TF-IDF.
    """
    if not os.path.exists(DATASET_FILE):
        raise FileNotFoundError(
            f"Arquivo '{DATASET_FILE}' não encontrado na raiz do projeto!"
        )

    df = pd.read_csv(DATASET_FILE, encoding="utf-8-sig")

    if "texto" not in df.columns or "area" not in df.columns:
        raise ValueError("O CSV deve conter as colunas 'texto' e 'area'.")

    # aplica o pré-processamento no dataset
    X = df["texto"].astype(str).apply(extrair_apenas_objeto)
    y = df["area"]

    # vetorizador TF-IDF + Regressão Logística
    pipeline = make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 2), strip_accents="unicode", lowercase=True
        ),
        LogisticRegression(max_iter=1000, random_state=42),
    )

    print(f"treinando modelo NLP com {len(df)} exemplos de contratos...")
    pipeline.fit(X, y)

    # salva o pipeline completo treinado em disco
    joblib.dump(pipeline, MODEL_FILE)
    print(f"modelo treinado com sucesso e salvo em '{MODEL_FILE}'")
    return pipeline

def load_or_train_model():
    """Carrega o modelo do disco ou treina um novo caso não exista."""
    if os.path.exists(MODEL_FILE):
        return joblib.load(MODEL_FILE)
    return train_and_save_model()

def classify_text(text: str) -> str:
    """Classifica o contexto do contrato em uma categoria."""
    model = load_or_train_model()
    prediction = model.predict([text])
    return prediction[0]

def explain_classification(text: str) -> dict:
    """
    Além de prever a categoria, extrai a probabilidade matemática 
    (confidence score) gerada pela Regressão Logística do Scikit-Learn.
    """
    model = load_or_train_model()
    texto_processado = extrair_apenas_objeto(text)
    
    # pega predição normal
    predicao = model.predict([texto_processado])[0]
    
    # pega as probabilidades matematicas de todas as classes
    probs = model.predict_proba([texto_processado])[0]
    
    # descobre o indice matematico da classe vencedora (a que tem maior probabilidade)
    classes = model.classes_
    indice_vencedor = np.where(classes == predicao)[0][0]
    
    # pega o grau de certeza
    confidence = probs[indice_vencedor]
    
    return {
        "categoria": predicao,
        "confidence": float(confidence),
        "texto_analisado": texto_processado
    }