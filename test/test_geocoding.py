from urllib.parse import parse_qs, urlparse

import geocoding
from geocoding import EnderecoNaoEncontrado, GeocodificadorIndisponivel, geocodifica

#Resposta de exemplo no formato do Nominatim
ITEM = {
    "lat": "-23.5613",
    "lon": "-46.6563",
    "display_name": "Avenida Paulista, 1000, Bela Vista, São Paulo, SP, Brasil",
    "address": {"house_number": "1000", "road": "Avenida Paulista"},
}

#Troca a chamada real à internet por uma função de teste e restaura no final
def com_busca_falsa(falsa, funcao_de_teste):
    original_busca = geocoding.buscar_json
    original_intervalo = geocoding.INTERVALO_MINIMO
    geocoding.buscar_json = falsa
    geocoding.INTERVALO_MINIMO = 0
    geocodifica.cache_clear()
    try:
        funcao_de_teste()
    finally:
        geocoding.buscar_json = original_busca
        geocoding.INTERVALO_MINIMO = original_intervalo
        geocodifica.cache_clear()

#Testa se a cidade e o estado são acrescentados e se só latitude e longitude são extraídas
def test_enriquece_endereco_e_extrai_coordenadas():
    urls = []

    def falsa(url, user_agent, timeout=8):
        urls.append(url)
        return [ITEM]

    def teste():
        local = geocodifica("Avenida Paulista", "1000", "01310-100", "São Paulo", "SP", "teste")
        assert (local.latitude, local.longitude) == (-23.5613, -46.6563)
        assert isinstance(local.latitude, float)
        assert local.precisao == "numero"
        q = parse_qs(urlparse(urls[0]).query)
        assert q["street"] == ["1000 Avenida Paulista"]
        assert q["city"] == ["São Paulo"]
        assert q["state"] == ["São Paulo"]
        assert q["postalcode"] == ["01310-100"]

    com_busca_falsa(falsa, teste)

#Testa se, quando o CEP não existe no mapa, a busca é repetida sem ele
def test_tenta_sem_cep_se_o_mapa_nao_conhece_o_cep():
    chamadas = []

    def falsa(url, user_agent, timeout=8):
        q = parse_qs(urlparse(url).query)
        chamadas.append(q)
        return [] if "postalcode" in q else [ITEM]

    def teste():
        local = geocodifica("Avenida Paulista", "1000", "99999-999", "São Paulo", "SP", "teste")
        assert len(chamadas) == 2
        assert "postalcode" not in chamadas[1]
        assert local.latitude == -23.5613

    com_busca_falsa(falsa, teste)

#Testa se avisa quando só a rua foi encontrada (sem o número do imóvel)
def test_precisao_rua_quando_nao_acha_o_numero():
    item = {"lat": "-23.5", "lon": "-46.6", "display_name": "Rua X", "address": {"road": "Rua X"}}

    def teste():
        local = geocodifica("Rua X", "10", "01000-000", "São Paulo", "SP", "teste")
        assert local.precisao == "rua"

    com_busca_falsa(lambda url, user_agent, timeout=8: [item], teste)

#Testa o erro quando o endereço não existe
def test_endereco_nao_encontrado():
    def teste():
        try:
            geocodifica("Rua Que Nao Existe", "1", "01000-000", "São Paulo", "SP", "teste")
        except EnderecoNaoEncontrado as erro:
            assert "São Paulo, SP" in str(erro)
        else:
            raise AssertionError("era esperado EnderecoNaoEncontrado")

    com_busca_falsa(lambda url, user_agent, timeout=8: [], teste)

#Testa o erro quando o serviço de mapas devolve algo inesperado
def test_resposta_inesperada_do_mapa():
    def teste():
        try:
            geocodifica("Rua A", "1", "01000-000", "São Paulo", "SP", "teste")
        except GeocodificadorIndisponivel:
            pass
        else:
            raise AssertionError("era esperado GeocodificadorIndisponivel")

    com_busca_falsa(lambda url, user_agent, timeout=8: [{"lat": "abc", "lon": "-46"}], teste)

#Testa se o mesmo endereço não consulta o mapa duas vezes (cache)
def test_cache_evita_nova_consulta():
    contador = {"n": 0}

    def falsa(url, user_agent, timeout=8):
        contador["n"] += 1
        return [ITEM]

    def teste():
        geocodifica("Avenida Paulista", "1000", "01310-100", "São Paulo", "SP", "teste")
        geocodifica("Avenida Paulista", "1000", "01310-100", "São Paulo", "SP", "teste")
        assert contador["n"] == 1

    com_busca_falsa(falsa, teste)

#Testa o limite de 1 busca por segundo
def test_espera_entre_buscas():
    class RelogioFalso:
        def __init__(self):
            self.agora = 100.0
            self.esperas = []

        def monotonic(self):
            return self.agora

        def sleep(self, segundos):
            self.esperas.append(segundos)
            self.agora += segundos

    relogio = RelogioFalso()
    original_time = geocoding.time
    original_ultima = geocoding._ultima_busca
    geocoding.time = relogio
    geocoding._ultima_busca = None
    try:
        geocoding.espera_intervalo()
        geocoding.espera_intervalo()
        assert len(relogio.esperas) == 1
        assert abs(relogio.esperas[0] - 1.0) < 1e-9
    finally:
        geocoding.time = original_time
        geocoding._ultima_busca = original_ultima

#Testa a normalização do CEP
def test_normaliza_cep():
    assert geocoding.normaliza_cep("01310100") == "01310-100"
    assert geocoding.normaliza_cep("01310-100") == "01310-100"
    for invalido in ["", "123", "0131010", "abcdefgh", "013101000"]:
        try:
            geocoding.normaliza_cep(invalido)
        except ValueError:
            continue
        raise AssertionError(f"CEP inválido aceito: {invalido!r}")

#Testa o cálculo de distância
def test_distancia_km():
    assert geocoding.distancia_km(-23.55, -46.63, -23.55, -46.63) < 1e-6
    assert abs(geocoding.distancia_km(0, 0, 1, 0) - 111.19) < 0.5
