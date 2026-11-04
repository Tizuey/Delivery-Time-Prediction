# Delivery Time Prediction

The user selects a restaurant (Subway, Burger King, or McDonald's), enters their street name, house number, and ZIP code (CEP), and receives an estimated delivery time.

- **Front-end:** `static/index.html`, hosted on GitHub Pages.
- **Back-end:** FastAPI + `model.joblib`, running in Docker on an AWS EC2 instance.
- **Endpoints:** `GET /health`, `POST /predict` (original), `GET /restaurants`, `POST /estimate`.

## 1. Before Getting Started

1. In `app.py`, set the latitude and longitude of each restaurant in `RESTAURANTES` and verify `CIDADE` and `ESTADO`.
2. Check the exact category names for `Type_of_vehicle` and `Type_of_order` in the training dataset. The code handles capitalization and trailing spaces. If the default values (`motorcycle`, `Snack`) are not available in the training data, the `/estimate` endpoint displays the available categories instead of silently returning an unreliable prediction.
3. In `requirements.txt`, pin `scikit-learn` to the same version used during training (`pip show scikit-learn`).
4. In `static/index.html`, replace `SEU_KIT_ID` (Adobe Fonts) and `API_URL` (see the `REPLACE 1 OF 2` and `REPLACE 2 OF 2` sections).

## 2. Run and Test Locally

```bash
pip install -r requirements.txt pytest httpx
pytest
uvicorn app:app --reload
```

Open http://127.0.0.1:8000. With `API_URL = ""`, the API serves the frontend directly.

## 3. Deploy the Back-end on AWS EC2 (Docker)

1. Create an Ubuntu instance. In its Security Group, allow inbound traffic on ports 22 (SSH), 80, and 443.
2. Install Docker:

```bash
sudo apt update && sudo apt install -y docker.io
```

3. Upload `app.py`, `geocoding.py`, `categorias.py`, `model.joblib`, `requirements.txt`, `Dockerfile`, and the `static` folder using `git clone` or `scp`.

4. Build and run the container:

```bash
docker build -t entrega-45 .
docker run -d --restart unless-stopped -p 127.0.0.1:8000:8000 \
  -e GEOCODER_USER_AGENT="45-minutos (your-email@example.com)" \
  -e CORS_ORIGINS="https://YOUR_USERNAME.github.io" \
  entrega-45
```

5. Test the API:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

`CORS_ORIGINS` is optional. Without it, the API accepts requests from any origin (`*`). Restricting it to your website prevents other pages from using your API and consuming your map service quota.

## 4. HTTPS (Required for GitHub Pages)

GitHub Pages uses HTTPS, and browsers block requests from an HTTPS website to an API running over `http://IP_ADDRESS_OF_EC2`.

To avoid this:

1. Point a domain or subdomain (e.g., `api.yourdomain.com`) to your EC2 public IP. Use an Elastic IP to prevent the address from changing.
2. Install Caddy (https://caddyserver.com/docs/install) and edit `/etc/caddy/Caddyfile`:

```text
api.yourdomain.com {
    reverse_proxy localhost:8000
}
```

3. Restart Caddy:

```bash
sudo systemctl restart caddy
```

Caddy automatically obtains and renews the TLS certificate.

4. Test:

```text
https://api.yourdomain.com/health
```

## 5. Deploy the Front-end on GitHub Pages

1. In `static/index.html`, set `API_URL = "https://api.yourdomain.com"`.
2. GitHub Pages can publish from the repository root or the `/docs` folder. Copy `static/index.html` (and `logo.png`, if available) into `docs/`.
3. Commit and push your changes:

```bash
git add .
git commit -m "deploy"
git push
```

4. In your repository, go to **Settings > Pages > Build and deployment**, select branch `main` and folder `/docs`, then click **Save**.
5. In Adobe Fonts, add `YOUR_USERNAME.github.io` to the Web Project's allowed domains. Otherwise, the custom font will not load.

## Notes

- Nominatim limits requests to one per second and requires an identifying User-Agent (`GEOCODER_USER_AGENT`). The code respects this limit and caches results. For production traffic, use another geocoding service.
- The model was trained on a public dataset from a different region. Therefore, its predictions should be considered a demonstration rather than reliable real-world delivery estimates.

# Previsão de tempo de entrega

O usuário escolhe um restaurante (Subway, Burger King ou McDonald's), informa rua, número e CEP, e vê o tempo estimado de entrega.

- **Front-end:** `static/index.html`, publicado no GitHub Pages.
- **Back-end:** FastAPI + `model.joblib`, em Docker numa EC2 da AWS.
- **Rotas:** `GET /health`, `POST /predict` (original), `GET /restaurants`, `POST /estimate`.

## 1. Antes de tudo

1. Em `app.py`, preencha a latitude e a longitude de cada restaurante em `RESTAURANTES` e confira `CIDADE` e `ESTADO`.
2. Confira no dataset as grafias de `Type_of_vehicle` e `Type_of_order`. O código ajusta maiúsculas e espaços no fim; se o valor padrão (`motorcycle`, `Snack`) não existir no treino, a rota `/estimate` avisa quais categorias existem, em vez de errar em silêncio.
3. Em `requirements.txt`, fixe o `scikit-learn` na mesma versão do treino (`pip show scikit-learn`).
4. Em `static/index.html`, troque `SEU_KIT_ID` (Adobe Fonts) e `API_URL` (veja os blocos `SUBSTITUIR 1 DE 2` e `2 DE 2`).

## 2. Rodar e testar localmente

```bash
pip install -r requirements.txt pytest httpx
pytest
uvicorn app:app --reload
```

Abra http://127.0.0.1:8000. Com `API_URL = ""`, a própria API serve a página.

## 3. Back-end na EC2 (Docker)

1. Crie uma instância Ubuntu. No Security Group, libere as portas 22 (SSH), 80 e 443.
2. Instale o Docker: `sudo apt update && sudo apt install -y docker.io`
3. Envie `app.py`, `geocoding.py`, `categorias.py`, `model.joblib`, `requirements.txt`, `Dockerfile` e a pasta `static` (`git clone` ou `scp`).
4. Construa e rode:

```bash
docker build -t entrega-45 .
docker run -d --restart unless-stopped -p 127.0.0.1:8000:8000 \
  -e GEOCODER_USER_AGENT="45-minutos (seu-email@exemplo.com)" \
  -e CORS_ORIGINS="https://SEU_USUARIO.github.io" \
  entrega-45
```

5. Teste: `curl http://localhost:8000/health` deve devolver `{"status":"ok"}`.

`CORS_ORIGINS` é opcional. Sem ele, a API aceita qualquer origem (`*`). Restringir ao seu site evita que outras páginas usem a sua API, e a sua cota do serviço de mapas.

## 4. HTTPS (obrigatório com GitHub Pages)

O GitHub Pages usa HTTPS, e o navegador bloqueia chamadas a uma API em `http://IP_DA_EC2`. Por isso:

1. Aponte um domínio ou subdomínio (ex.: `api.seudominio.com`) para o IP da EC2. Use um Elastic IP para o IP não mudar.
2. Instale o Caddy (https://caddyserver.com/docs/install) e edite `/etc/caddy/Caddyfile`:

```text
api.seudominio.com {
    reverse_proxy localhost:8000
}
```

3. `sudo systemctl restart caddy`. O certificado é emitido sozinho.
4. Teste: `https://api.seudominio.com/health`.

## 5. Front-end no GitHub Pages

1. Em `static/index.html`, use `API_URL = "https://api.seudominio.com"`.
2. O Pages publica a raiz do repositório ou a pasta `/docs`. Copie `static/index.html` (e `logo.png`, se tiver) para `docs/`.
3. `git add . && git commit -m "deploy" && git push`
4. No repositório: Settings > Pages > Branch `main` > pasta `/docs` > Save.
5. Na Adobe Fonts, adicione `SEU_USUARIO.github.io` aos domínios do Web Project, senão a fonte não carrega.

## Observações

- O Nominatim limita a 1 busca por segundo e exige identificação (`GEOCODER_USER_AGENT`). O código respeita o limite e guarda resultados em cache. Para tráfego real, use outro serviço.
- O modelo foi treinado com um dataset público de outra região: o resultado é uma demonstração.
