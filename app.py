import os
import re
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from categorias import ajusta_categoria
from geocoding import (
    EnderecoNaoEncontrado,
    GeocodificadorIndisponivel,
    distancia_km,
    geocodifica,
    normaliza_cep,
)

#1. Cria o aplicativo do servidor web
app = FastAPI(title="Delivery Time API")

#Libera as origens (CORS) para o front-end no GitHub Pages conseguir chamar a API que roda na EC2
#Por padrão libera todas ("*"). Para restringir só ao seu site, defina CORS_ORIGINS=https://seuusuario.github.io
ORIGENS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS,
    allow_methods=["*"],
    allow_headers=["*"],
)

#2. Traz o modelo treinado
model = joblib.load("model.joblib")

#3. Define exatamente o que a API aceita receber
class Features(BaseModel):
    Type_of_vehicle: str
    Type_of_order: str
    Delivery_person_Age: int
    Delivery_person_Ratings: float
    Restaurant_latitude: float
    Restaurant_longitude: float
    Delivery_location_latitude: float
    Delivery_location_longitude: float

#Define o que o formulário da página envia: restaurante escolhido, rua, número e CEP
class Pedido(BaseModel):
    restaurant_id: str
    street: str
    number: str
    cep: str

#4. Restaurantes do dropdown. Preencha a latitude e a longitude de cada um 
RESTAURANTES = {
    # Burger King
    "bk-salvador-shopping": {"nome": "Burger King Salvador Shopping", "latitude": -12.9789, "longitude": -38.4551},
    "bk-shopping-da-bahia": {"nome": "Burger King Shopping da Bahia", "latitude": -12.9804, "longitude": -38.4646},
    "bk-paralela": {"nome": "Burger King Shopping Paralela", "latitude": -12.9384, "longitude": -38.4044},
    "bk-salvador-norte": {"nome": "Burger King Salvador Norte Shopping", "latitude": -12.9107, "longitude": -38.3483},
    "bk-bela-vista": {"nome": "Burger King Shopping Bela Vista", "latitude": -12.9723, "longitude": -38.4839},
    "bk-barra": {"nome": "Burger King Shopping Barra", "latitude": -13.0076, "longitude": -38.5283},
    "bk-rio-vermelho": {"nome": "Burger King Rio Vermelho", "latitude": -13.0142, "longitude": -38.4908},

    # Subway
    "subway-stella-maris": {"nome": "Subway Stella Maris", "latitude": -12.9293, "longitude": -38.3293},
    "subway-sao-cristovao": {"nome": "Subway São Cristóvão (Salvador Norte)", "latitude": -12.9107, "longitude": -38.3483},
    "subway-itapua": {"nome": "Subway Itapuã", "latitude": -12.9424, "longitude": -38.3587},
    "subway-paralela": {"nome": "Subway Paralela", "latitude": -12.9384, "longitude": -38.4044},
    "subway-praca-da-se": {"nome": "Subway Praça da Sé", "latitude": -12.9737, "longitude": -38.5114},
    "subway-sete-de-setembro": {"nome": "Subway Av. Sete de Setembro", "latitude": -12.9823, "longitude": -38.5155},
    "subway-salvador-shopping": {"nome": "Subway Salvador Shopping", "latitude": -12.9789, "longitude": -38.4551},
    "subway-shopping-da-bahia": {"nome": "Subway Shopping da Bahia (ACM)", "latitude": -12.9804, "longitude": -38.4646},
    "subway-campinas-de-piraja": {"nome": "Subway Campinas de Pirajá", "latitude": -12.9231, "longitude": -38.4832},

    # McDonald's
    "mcdonalds-rio-vermelho": {"nome": "McDonald's Rio Vermelho", "latitude": -13.0142, "longitude": -38.4908},
    "mcdonalds-pituba": {"nome": "McDonald's Pituba", "latitude": -13.0039, "longitude": -38.4607},
    "mcdonalds-barra": {"nome": "McDonald's Barra", "latitude": -13.0076, "longitude": -38.5283},
    "mcdonalds-caminho-das-arvores": {"nome": "McDonald's Caminho das Árvores", "latitude": -12.9788, "longitude": -38.4552},
    "mcdonalds-paralela": {"nome": "McDonald's Paralela", "latitude": -12.9384, "longitude": -38.4044},
    "mcdonalds-graca": {"nome": "McDonald's Graça", "latitude": -12.9961, "longitude": -38.5208},
    "mcdonalds-nazare": {"nome": "McDonald's Nazaré", "latitude": -12.9772, "longitude": -38.5103},
    "mcdonalds-sao-cristovao": {"nome": "McDonald's São Cristóvão", "latitude": -12.8988, "longitude": -38.3444},
    "mcdonalds-cabula": {"nome": "McDonald's Cabula", "latitude": -12.9757, "longitude": -38.4735},
    "mcdonalds-piata": {"nome": "McDonald's Piatã", "latitude": -12.9461, "longitude": -38.3804},
}

#5. Configurações: cidade e estado de operação (acrescentados ao endereço antes da busca no mapa)
CIDADE = os.getenv("CIDADE", "Salvador")
ESTADO = os.getenv("ESTADO", "BA")
#O Nominatim pede que você se identifique: coloque seu e-mail ou o link do repositório
USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "delivery-time-demo/1.0 (defina GEOCODER_USER_AGENT)")
#Endereços mais distantes que isso do restaurante são recusados
DISTANCIA_MAXIMA_KM = float(os.getenv("DISTANCIA_MAXIMA_KM", "30"))

#6. Parâmetros fixos da previsão
PADRAO = {
    "Type_of_vehicle": "motorcycle",
    "Type_of_order": "Snack",
    "Delivery_person_Age": 25,
    "Delivery_person_Ratings": 4.5,
}

#Verifica se a rota está ok
@app.get("/health")
def health():
    return {"status": "ok"}

#7. Cria a rota de predição (a original, sem alterações)
@app.post("/predict")
def predict(f: Features):
    df = pd.DataFrame([f.model_dump()])
    return {"predicted_minutes": round(float(model.predict(df)[0]), 1)}

#8. Lista os restaurantes para o dropdown da página
@app.get("/restaurants")
def restaurants():
    return [{"id": id_, "name": r["nome"]} for id_, r in RESTAURANTES.items()]

#9. Rota usada pela página: recebe restaurante + endereço e devolve o tempo estimado
@app.post("/estimate")
def estimate(p: Pedido):
    #9.1 Confere o restaurante escolhido
    restaurante = RESTAURANTES.get(p.restaurant_id)
    if restaurante is None:
        raise HTTPException(status_code=422, detail="Escolha um restaurante da lista.")
    if restaurante["latitude"] is None or restaurante["longitude"] is None:
        raise HTTPException(
            status_code=503,
            detail=f"As coordenadas de {restaurante['nome']} ainda não foram configuradas.",
        )

    #9.2 Confere rua, número e CEP
    rua = p.street.strip()
    if len(rua) < 2:
        raise HTTPException(status_code=422, detail="Informe o nome da rua.")
    numero = p.number.strip()
    if not re.fullmatch(r"\d{1,6}[A-Za-z]?", numero):
        raise HTTPException(
            status_code=422,
            detail="Informe o número do imóvel (apenas dígitos, com uma letra opcional).",
        )
    try:
        cep = normaliza_cep(p.cep)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))

    #9.3 Geocodificação: transforma o endereço em latitude e longitude
    try:
        local = geocodifica(rua, numero, cep, CIDADE, ESTADO, USER_AGENT)
    except EnderecoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro))
    except GeocodificadorIndisponivel as erro:
        raise HTTPException(status_code=502, detail=str(erro))

    #9.4 Recusa endereços fora da área de entrega
    distancia = distancia_km(
        restaurante["latitude"], restaurante["longitude"], local.latitude, local.longitude
    )
    if distancia > DISTANCIA_MAXIMA_KM:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Esse endereço fica a {distancia:.0f} km de {restaurante['nome']}, "
                f"fora da área de entrega (máximo de {DISTANCIA_MAXIMA_KM:.0f} km)."
            ),
        )

    #9.5 Monta a entrada no mesmo formato do /predict (mesmos nomes de variáveis do schema)
    try:
        veiculo = ajusta_categoria(model, "Type_of_vehicle", PADRAO["Type_of_vehicle"])
        tipo_de_pedido = ajusta_categoria(model, "Type_of_order", PADRAO["Type_of_order"])
    except ValueError as erro:
        raise HTTPException(status_code=500, detail=str(erro))

    entrada = Features(
        Type_of_vehicle=veiculo,
        Type_of_order=tipo_de_pedido,
        Delivery_person_Age=PADRAO["Delivery_person_Age"],
        Delivery_person_Ratings=PADRAO["Delivery_person_Ratings"],
        Restaurant_latitude=restaurante["latitude"],
        Restaurant_longitude=restaurante["longitude"],
        Delivery_location_latitude=local.latitude,
        Delivery_location_longitude=local.longitude,
    )

    #9.6 Previsão do modelo
    df = pd.DataFrame([entrada.model_dump()])
    minutos = max(float(model.predict(df)[0]), 1.0)

    return {
        "minutes": round(minutos),
        "minutes_exact": round(minutos, 1),
        "restaurant": restaurante["nome"],
        "address": local.endereco,
        "precision": local.precisao,
    }

#10. Serve a página (pasta static). Fica por último para não cobrir as rotas acima
#Serve para testar localmente; no GitHub Pages a página é publicada separadamente
if Path("static").exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
