import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

def gerar_metricas():    
    df = pd.read_csv('contratos_prefeitura_ruido.csv')
    
    X_train, X_test, y_train, y_test = train_test_split(
        df['texto'], df['area'], test_size=0.2, random_state=42
    )
    
    vetorizador = TfidfVectorizer()
    X_train_vec = vetorizador.fit_transform(X_train)
    X_test_vec = vetorizador.transform(X_test)
    
    modelo = LogisticRegression()
    modelo.fit(X_train_vec, y_train)
    
    y_pred = modelo.predict(X_test_vec)
    
    print("Métricas do Classificador (Precision, Recall, F1-Score)")
    print(classification_report(y_test, y_pred))
    
    print("\nMATRIZ DE CONFUSÃO")
    print(confusion_matrix(y_test, y_pred))

if __name__ == "__main__":
    gerar_metricas()