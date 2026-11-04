import json
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

#1. Identificamos o que quero prever e os dados que vou usar para isso. 
TARGET = "Time_taken(min)"
CAT = ["Type_of_vehicle", "Type_of_order"]
NUM = ["Delivery_person_Age", "Delivery_person_Ratings", "Restaurant_latitude", "Restaurant_longitude","Delivery_location_latitude","Delivery_location_longitude" ]

#2. Tratamento dos dados 

#Limpeza 
#pd.read_excel: Lê o arquivo de dados e remove (dropna) qualquer linha que tenha valores nulos (vazios) nas colunas
df = pd.read_excel("data/Food Delivery Time Prediction Case Study.xlsx").dropna(subset=[TARGET] + CAT + NUM)

#Tratamento 1 
#X, y = ...: Separa o dataset. X são as características usadas para prever (features) e y é a resposta correta (target).
X, y = df[CAT + NUM], df[TARGET]

#Separação treino e teste
#train_test_split: Divide o dataset em dois conjuntos: treino (train) e teste (test). O conjunto de treino é usado para treinar o modelo, enquanto o conjunto de teste é usado para avaliar a performance do modelo.
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)


#Tratamento 2 : Modelos matemáticos não entendem texto (como "chovendo" ou "trânsito pesado").
#O OneHotEncoder transforma as colunas categóricas (CAT) em colunas binárias (0 ou 1). O handle_unknown="ignore" evita erros caso apareça um clima novo no futuro que não existia no treino.
pre = ColumnTransformer(
    [("cat", OneHotEncoder(handle_unknown="ignore"), CAT)],
    remainder="passthrough",
)

#3. Treinamento do modelo

#Pipeline: Cria uma "linha de montagem". Quando dados novos chegam, eles passam primeiro pelo pré-processamento (pre) e depois vão para o modelo (rf).
model = Pipeline([
    ("pre", pre),
    #andomForestRegressor: É o cérebro da operação. Uma "Floresta Aleatória" que cria 100 árvores de decisão (n_estimators=100), limitadas a 12 níveis de profundidade (max_depth=12) para não ficarem complexas demais. O n_jobs=-1 manda o computador usar todos os núcleos do processador para treinar mais rápido.
    ("rf", RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)),
])
#model.fit(X_tr, y_tr): É aqui que o aprendizado acontece. O modelo analisa os dados de treino para encontrar os padrões matemáticos.
model.fit(X_tr, y_tr)


#4. Avaliação do modelo
#DummyRegressor: Cria um modelo "burro" que sempre prevê a média do conjunto de treino. Serve como referência para ver se o modelo treinado é realmente bom.
baseline = DummyRegressor(strategy="mean").fit(X_tr, y_tr)
metrics = {
    #mean_absolute_error (MAE): Calcula o Erro Médio Absoluto. Se o MAE do modelo der 5.0, significa que as previsões erram por 5 minutos, em média, para mais ou para menos
    "mae_model": round(mean_absolute_error(y_te, model.predict(X_te)), 2),
    "mae_baseline": round(mean_absolute_error(y_te, baseline.predict(X_te)), 2),
    "n_train": len(X_tr),
    "n_test": len(X_te),
}

#Salva a "linha de montagem" completa (pré-processamento + modelo treinado) em um arquivo model.joblib
joblib.dump(model, "model.joblib")

#json.dump: Salva um relatório (metrics.json) mostrando o erro do seu modelo, o erro do modelo bobo, e quantas linhas de dados foram usadas.
json.dump(metrics, open("metrics.json", "w"), indent=2)
print(metrics)