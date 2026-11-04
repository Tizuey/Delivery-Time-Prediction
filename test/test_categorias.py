import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from categorias import ajusta_categoria, categorias_do_treino

CAT = ["Type_of_vehicle", "Type_of_order"]
NUM = ["Delivery_person_Age", "Delivery_person_Ratings", "Restaurant_latitude", "Restaurant_longitude", "Delivery_location_latitude", "Delivery_location_longitude"]

#Treina um modelo pequeno com o MESMO pipeline do train.py, só para testar (dados inventados)
def modelo_de_teste(veiculos, pedidos):
    rng = np.random.default_rng(0)
    n = 120
    df = pd.DataFrame({
        "Type_of_vehicle": rng.choice(veiculos, n),
        "Type_of_order": rng.choice(pedidos, n),
        "Delivery_person_Age": rng.integers(20, 40, n),
        "Delivery_person_Ratings": rng.uniform(3.5, 5, n),
        "Restaurant_latitude": rng.uniform(-23.6, -23.5, n),
        "Restaurant_longitude": rng.uniform(-46.7, -46.6, n),
        "Delivery_location_latitude": rng.uniform(-23.6, -23.5, n),
        "Delivery_location_longitude": rng.uniform(-46.7, -46.6, n),
    })
    y = rng.uniform(15, 50, n)
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT)], remainder="passthrough")
    model = Pipeline([("pre", pre), ("rf", RandomForestRegressor(n_estimators=5, random_state=0))])
    return model.fit(df[CAT + NUM], y)

#Testa se lê as categorias que o modelo viu no treino
def test_categorias_do_treino():
    modelo = modelo_de_teste(["motorcycle", "scooter"], ["Snack", "Meal"])
    cats = categorias_do_treino(modelo)
    assert list(cats) == CAT
    assert sorted(cats["Type_of_vehicle"]) == ["motorcycle", "scooter"]

#Testa se o valor padrão é ajustado para o formato exato do treino (espaço no fim e maiúsculas)
def test_ajusta_espaco_e_maiusculas():
    modelo = modelo_de_teste(["motorcycle ", "scooter "], ["Snack ", "Meal "])
    assert ajusta_categoria(modelo, "Type_of_vehicle", "motorcycle") == "motorcycle "
    assert ajusta_categoria(modelo, "Type_of_order", "snack") == "Snack "

#Testa se avisa quando o valor não existe no treino, listando as categorias
def test_valor_inexistente_avisa():
    modelo = modelo_de_teste(["motorcycle", "scooter"], ["Snack", "Meal"])
    try:
        ajusta_categoria(modelo, "Type_of_order", "Delivery")
    except ValueError as erro:
        assert "Delivery" in str(erro)
        assert "Snack" in str(erro)
    else:
        raise AssertionError("era esperado ValueError")
