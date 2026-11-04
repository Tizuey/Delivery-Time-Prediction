from fastapi.testclient import TestClient
from app import app

import app as app_module
from geocoding import EnderecoNaoEncontrado, GeocodificadorIndisponivel, Local

client = TestClient(app)

#Testa se a rota de saúde está funcionando corretamente
def test_health():
    assert client.get("/health").json() == {"status": "ok"}

#Testa se a rota de predição está funcionando corretamente
def test_predict():
    body = {    "Type_of_vehicle": "Motorcycle",
    "Type_of_order": "Delivery",
    "Delivery_person_Age": 25,
    "Delivery_person_Ratings": 4.5,
    "Restaurant_latitude": -23.550520,
    "Restaurant_longitude": -46.633308,
    "Delivery_location_latitude": -23.550520,
    "Delivery_location_longitude": -46.633308
}
   
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    assert r.json()["predicted_minutes"] > 0

#--- Testes da nova rota /estimate (página com restaurante + endereço) ---

#Coordenadas de teste para os restaurantes (as reais ficam em app.py)
RESTAURANTES_TESTE = {
    "subway": {"nome": "Subway", "latitude": -23.5613, "longitude": -46.6563},
    "mcdonalds": {"nome": "McDonald's", "latitude": None, "longitude": None},
}

PEDIDO = {"restaurant_id": "subway", "street": "Avenida Paulista", "number": "1000", "cep": "01310100"}

#Troca a busca no mapa e os restaurantes por versões de teste (sem internet)
def prepara(monkeypatch, local=None, erro=None):
    monkeypatch.setattr(app_module, "RESTAURANTES", RESTAURANTES_TESTE)

    def geocodifica_falso(*args):
        if erro:
            raise erro
        return local

    monkeypatch.setattr(app_module, "geocodifica", geocodifica_falso)

LOCAL_PERTO = Local(-23.5650, -46.6520, "Avenida Paulista, 1000, São Paulo", "numero")

#Testa se a rota de restaurantes devolve os três do dropdown
def test_restaurants():
    r = client.get("/restaurants")
    assert r.status_code == 200
    assert [x["name"] for x in r.json()] == ["Subway", "Burger King", "McDonald's"]

#Testa o fluxo completo: restaurante + endereço -> coordenadas -> modelo -> minutos
def test_estimate(monkeypatch):
    prepara(monkeypatch, local=LOCAL_PERTO)
    r = client.post("/estimate", json=PEDIDO)
    assert r.status_code == 200
    dados = r.json()
    assert dados["minutes"] > 0
    assert dados["restaurant"] == "Subway"
    assert dados["precision"] == "numero"

#Testa a mensagem quando o endereço não é encontrado
def test_estimate_endereco_nao_encontrado(monkeypatch):
    prepara(monkeypatch, erro=EnderecoNaoEncontrado("Não encontramos esse endereço."))
    r = client.post("/estimate", json=PEDIDO)
    assert r.status_code == 404
    assert "Não encontramos" in r.json()["detail"]

#Testa a mensagem quando o serviço de mapas está fora do ar
def test_estimate_mapa_indisponivel(monkeypatch):
    prepara(monkeypatch, erro=GeocodificadorIndisponivel("O serviço de mapas não respondeu."))
    r = client.post("/estimate", json=PEDIDO)
    assert r.status_code == 502

#Testa CEP e número inválidos
def test_estimate_entradas_invalidas(monkeypatch):
    prepara(monkeypatch, local=LOCAL_PERTO)
    assert client.post("/estimate", json={**PEDIDO, "cep": "123"}).status_code == 422
    assert client.post("/estimate", json={**PEDIDO, "number": "abc"}).status_code == 422
    assert client.post("/estimate", json={**PEDIDO, "street": " "}).status_code == 422
    assert client.post("/estimate", json={**PEDIDO, "restaurant_id": "outro"}).status_code == 422

#Testa o aviso de restaurante sem coordenadas configuradas
def test_estimate_restaurante_sem_coordenadas(monkeypatch):
    prepara(monkeypatch, local=LOCAL_PERTO)
    r = client.post("/estimate", json={**PEDIDO, "restaurant_id": "mcdonalds"})
    assert r.status_code == 503

#Testa a recusa de endereços muito distantes do restaurante
def test_estimate_fora_da_area(monkeypatch):
    longe = Local(-22.9, -43.2, "Rio de Janeiro", "numero")
    prepara(monkeypatch, local=longe)
    r = client.post("/estimate", json=PEDIDO)
    assert r.status_code == 422
    assert "fora da área" in r.json()["detail"]
