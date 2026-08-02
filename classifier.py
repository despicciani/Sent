import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

MODEL_FILE = "sent_classifier.joblib"

# dataset de treino sintético com padrões comuns de diários oficiais
TRAIN_DATA = [
    # educação 
    ("Aquisição de notebooks, Chromebooks e computadores para os professores do ensino fundamental", "Educação"),
    ("Fornecimento de merenda escolar, leite, pães e alimentos para escolas e creches municipais", "Educação"),
    ("Contratação de empresa para reforma, pintura e manutenção de escolas da rede pública de ensino", "Educação"),
    ("Aquisição de livros didáticos, cadernos, lápis e kits escolares para alunos da rede municipal", "Educação"),
    ("Serviço de transporte escolar para estudantes da zona rural e rede pública municipal", "Educação"),
    ("Instalação de lousas digitais, projetores e equipamentos pedagógicos para salas de aula", "Educação"),
    ("Treinamento, capacitação pedagógica e cursos para professores e educadores infantis", "Educação"),
    ("Compra de carteiras escolares, mesas e mobiliário para turmas de ensino infantil e fundamental", "Educação"),
    
    # saúde
    ("Aquisição de medicamentos, insumos hospitalares, seringas e ataduras para postos de saúde", "Saúde"),
    ("Compra de vacinas contra gripe, dengue e covid para imunização da população nas UPAs", "Saúde"),
    ("Manutenção preventiva de aparelhos de raio-x, ultrassom e equipamentos médicos hospitalares", "Saúde"),
    ("Contratação de serviços médicos especializados, enfermeiros e plantonistas para urgência", "Saúde"),
    ("Locação e manutenção de ambulâncias de suporte avançado e UTI móvel para o SAMU", "Saúde"),
    ("Aquisição de equipamentos de proteção individual EPI como luvas e máscaras cirúrgicas para saúde", "Saúde"),
    ("Fornecimento de oxigênio medicinal e gases hospitalares para unidades básicas de saúde", "Saúde"),
    ("Reforma, ampliação e pintura de Unidades Básicas de Saúde (UBS) e postos de atendimento", "Saúde"),

    # infraestrutura
    ("Serviços de pavimentação asfáltica, recapeamento e operação tapa-buraco em avenidas e ruas", "Infraestrutura"),
    ("Asfaltamento da Avenida Principal, drenagem e instalação de meio-fio e sarjetas", "Infraestrutura"),
    ("Construção de ponte de concreto, galerias de águas pluviais e obras de contenção de enchentes", "Infraestrutura"),
    ("Reforma de praças públicas, instalação de iluminação em LED e manutenção de calçadas", "Infraestrutura"),
    ("Locação de retroescavadeiras, tratores, caminhões caçamba e máquinas pesadas para obras", "Infraestrutura"),
    ("Serviços de limpeza urbana, coleta de lixo domiciliar, varrição de ruas e capina", "Infraestrutura"),
    ("Canalização de córregos, dragagem de rios e contenção de encostas e desbarrancamentos", "Infraestrutura"),
    
    # tecnologia
    ("Licenciamento de sistemas de gestão pública, folha de pagamento e hospedagem em nuvem", "Tecnologia"),
    ("Aquisição de servidores de grande porte, nobreaks e equipamentos de rede para o datacenter", "Tecnologia"),
    ("Contratação de link de internet dedicada via fibra óptica para prédios e secretarias da prefeitura", "Tecnologia"),
    ("Serviços de desenvolvimento de software, manutenção do portal da transparência e bancos de dados", "Tecnologia"),
    ("Locação de impressoras multifuncionais, scanners e computadores de mesa para uso corporativo", "Tecnologia"),
    ("Serviços de segurança da informação, firewall e proteção contra ataques cibernéticos", "Tecnologia"),

    # gestão administrativa
    ("Aquisição de papel A4, canetas, grampeadores e materiais de escritório para as secretarias", "Gestão Administrativa"),
    ("Contratação de serviços de vigilância patrimonial armada e desarmada para prédios públicos", "Gestão Administrativa"),
    ("Serviços de publicação de atos oficiais, avisos de licitação e impressão do Diário Oficial", "Gestão Administrativa"),
    ("Contratação de consultoria jurídica, auditoria contábil e assessoria para a administração pública", "Gestão Administrativa")
]

def train_and_save_model():
    """Treina o modelo NLP com TF-IDF + Naive Bayes e salva em disco."""
    texts, labels = zip(*TRAIN_DATA)
    
    # pipeline que junta a vetorização de texto e o classificador
    pipeline = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2)), # considera palavras isoladas e pares de palavras
        MultinomialNB()
    )
    
    pipeline.fit(texts, labels)
    joblib.dump(pipeline, MODEL_FILE)
    print(f" Modelo de IA treinado e salvo em '{MODEL_FILE}'!")
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

if __name__ == "__main__":
    print("testando o classificador de IA do Sent")
    
    # frases inéditas que não estavam no dataset de treino
    test_cases = [
        "Compra de 50.000 doses de vacina contra gripe para postos de atendimento",
        "Asfaltamento da Avenida Principal e instalação de meio-fio",
        "Aquisição de notebooks para os professores do ensino fundamental"
    ]
    
    for sample in test_cases:
        categoria = classify_text(sample)
        print(f"\nTexto: '{sample}'")
        print(f"🏷️ Categoria Prevista: {categoria}")