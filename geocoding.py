import json
import math
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

#1. Endereço do serviço de geocodificação (Nominatim, do OpenStreetMap). Não precisa de chave de API
URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"

#Nomes completos dos estados: o Nominatim entende melhor "São Paulo" do que "SP"
ESTADOS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

#2. Erros específicos da geocodificação (a API transforma cada um em uma resposta HTTP)
class EnderecoNaoEncontrado(Exception):
    pass

class GeocodificadorIndisponivel(Exception):
    pass

#3. O que a busca devolve: só números de latitude/longitude, o texto do endereço achado e a precisão
@dataclass(frozen=True)
class Local:
    latitude: float
    longitude: float
    endereco: str
    precisao: str  # "numero" se achou o número do imóvel, "rua" se achou só a rua

#4. O Nominatim permite no máximo 1 busca por segundo, então esperamos entre uma busca e outra
INTERVALO_MINIMO = 1.0
_trava = threading.Lock()
_ultima_busca = None

def espera_intervalo():
    global _ultima_busca
    with _trava:
        if _ultima_busca is not None:
            falta = INTERVALO_MINIMO - (time.monotonic() - _ultima_busca)
            if falta > 0:
                time.sleep(falta)
        _ultima_busca = time.monotonic()

#5. Faz a chamada HTTP e devolve a lista de resultados em JSON
def buscar_json(url, user_agent, timeout=8):
    #O Nominatim exige um User-Agent que identifique quem está usando
    pedido = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json", "Accept-Language": "pt-BR"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as erro:
        raise GeocodificadorIndisponivel(
            "O serviço de mapas não respondeu. Tente de novo em instantes."
        ) from erro

#6. Enriquecimento: o usuário só digita rua e número. Aqui acrescentamos a cidade e o estado de operação
#(ex.: São Paulo, SP) para o mapa não escolher uma rua com o mesmo nome em outra cidade
def monta_url(rua, numero, cep, cidade, estado):
    parametros = {
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": "1",
        "countrycodes": "br",
        "street": f"{numero} {rua}".strip(),
        "city": cidade,
        "state": ESTADOS.get(estado.upper(), estado),
    }
    if cep:
        parametros["postalcode"] = cep
    return f"{URL_NOMINATIM}?{urllib.parse.urlencode(parametros)}"

#7. Geocodificação: devolve a latitude e a longitude do endereço
#lru_cache guarda os últimos endereços buscados e evita repetir chamadas ao serviço de mapas
@lru_cache(maxsize=256)
def geocodifica(rua, numero, cep, cidade, estado, user_agent):
    #Primeiro tenta com o CEP; se o mapa não conhecer esse CEP, tenta de novo sem ele
    resultados = None
    for cep_da_busca in (cep, None):
        url = monta_url(rua, numero, cep_da_busca, cidade, estado)
        espera_intervalo()
        resultados = buscar_json(url, user_agent)
        if resultados:
            break

    if not resultados:
        raise EnderecoNaoEncontrado(
            f"Não encontramos esse endereço em {cidade}, {estado}. Confira o nome da rua, o número e o CEP."
        )

    #Isola exclusivamente os valores numéricos de latitude e longitude
    item = resultados[0]
    try:
        latitude = float(item["lat"])
        longitude = float(item["lon"])
    except (KeyError, TypeError, ValueError) as erro:
        raise GeocodificadorIndisponivel("O serviço de mapas devolveu uma resposta inesperada.") from erro

    achou_numero = bool((item.get("address") or {}).get("house_number"))
    return Local(
        latitude=latitude,
        longitude=longitude,
        endereco=str(item.get("display_name", "")),
        precisao="numero" if achou_numero else "rua",
    )

#8. Aceita "01310100" ou "01310-100" e devolve "01310-100"
def normaliza_cep(cep):
    digitos = re.sub(r"\D", "", cep or "")
    if len(digitos) != 8:
        raise ValueError("Informe um CEP com 8 dígitos.")
    return f"{digitos[:5]}-{digitos[5:]}"

#9. Distância em km entre dois pontos (fórmula de Haversine)
def distancia_km(lat1, lon1, lat2, lon2):
    raio_da_terra = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * raio_da_terra * math.asin(math.sqrt(a))
