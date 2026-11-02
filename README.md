# BairroIQ | Atlas Sampa

Protótipo Streamlit com navegação superior para explorar o mapa, comparar regiões, consultar perfis urbanos e entender as fontes. A aplicação inicia com dados demonstrativos locais; nenhuma conta ou credencial Databricks é necessária para testar a interface.

## Executar localmente (Windows)

No PowerShell, a partir da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Acesse `http://localhost:8501`. Para servir a página a outros dispositivos na rede local, use `python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501` e libere essa porta no firewall apenas em uma rede confiável.

Para instalar as ferramentas de desenvolvimento e verificar erros estáticos:

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check app.py bairroiq pages tests
```

## Publicar no GitHub e no Streamlit Community Cloud

Esta versão usa os dados demonstrativos locais e não precisa de secrets nem de configuração do Databricks.

O repositório local já está inicializado na branch `main`, com o remoto `origin` apontando para o repositório pessoal. Confira o que será publicado antes de criar o primeiro commit:

```powershell
git status
git add .gitignore README.md app.py bairroiq pages tests requirements.txt requirements-databricks.txt .streamlit/secrets.toml.example
git diff --cached --stat
git commit -m "Prepare BairroIQ Streamlit app for deployment"
git push -u origin main
```

O `.gitignore` exclui o ambiente local, caches, secrets reais, configurações do VS Code e a captura de tela `current-page.png`. Revise `git status` e a lista preparada com `git diff --cached --stat` antes do commit. O push não usa force; se o GitHub receber algum commit antes do envio e o push for recusado, não force a publicação: sincronize os históricos primeiro.

Para publicar, entre no [Streamlit Community Cloud](https://share.streamlit.io/) com a conta GitHub que tem acesso ao repositório e crie um app a partir de um repositório existente. Selecione:

- Repositório: `LaisHatsumiSato/bairroiq-streamlit`
- Branch: `main`
- Arquivo principal: `app.py`

O Community Cloud instalará as dependências de `requirements.txt` na raiz e iniciará a aplicação. Não configure secrets para esta versão mockada. Depois do deploy, confira as quatro páginas, os dados demonstrativos e o mapa.

O projeto permanece na raiz deste repositório pessoal para que o caminho de publicação seja `app.py`. A futura mudança para `streamlit/` deve ser feita junto com a integração ao repositório do grupo; nesse caso, o arquivo principal da publicação passará a ser `streamlit/app.py`.

## Conectar ao Databricks depois

A integração fica isolada em `bairroiq/databricks.py`; os dados demonstrativos ficam em `bairroiq/sample_data.py`. Para habilitar o conector:

1. Instale as dependências específicas: `python -m pip install -r requirements-databricks.txt`.
2. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha os valores do SQL Warehouse. Esse arquivo real está no `.gitignore`.
3. Configure as tabelas para seguirem o contrato abaixo e selecione o provedor: `$env:BAIRROIQ_DATA_PROVIDER = "databricks"`.
4. Inicie novamente: `python -m streamlit run app.py`.

O conector usa o Databricks SQL Connector for Python, com `server_hostname`, `http_path` e token em secrets locais ou nas variáveis `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH` e `DATABRICKS_ACCESS_TOKEN`. `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`, `DATABRICKS_METRICS_TABLE` e `DATABRICKS_HISTORY_TABLE` também podem substituir os valores do arquivo de secrets.

### Contrato mínimo das tabelas

`neighborhood_metrics`: `neighborhood`, `latitude`, `longitude`, `formal_jobs_score`, `robbery_index`, `lighting_led`, `trees_score`, `mobility_score`, `affordability_score`.

`neighborhood_history`: `neighborhood`, `year`, `formal_jobs_score`, `lighting_led`, `safety_score`.

As escalas dos indicadores são de 0 a 100, exceto `robbery_index` (0 a 10). A interface calcula segurança como `100 - 10 × robbery_index`. Ajuste nomes ou transformações no adaptador antes de conectar uma base com outro formato.

## Limites geográficos do mapa

`bairroiq/district_boundaries.geojson` contém os limites reais dos sete distritos de demonstração, derivados dos dados do [GeoSampa](https://geosampa.prefeitura.sp.gov.br/) e distribuídos no repositório [codigourbano/distritos-sp](https://github.com/codigourbano/distritos-sp). O mapa desenha somente os polígonos que continuam selecionados após a busca e os filtros; a tonalidade laranja representa a aderência às prioridades. Passe o cursor sobre uma região para consultar seus indicadores.

Se a base do Databricks incluir outros distritos, acrescente seus polígonos à coleção GeoJSON em `bairroiq/district_boundaries.geojson`. A aplicação informa quais limites faltam, em vez de desenhar uma forma aproximada.
