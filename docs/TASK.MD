# TASK.md - Lista de Tareas para NVP API Scraping Google News

**Propósito:** Seguimiento del trabajo pendiente y completado para la construcción del NVP. Marca las tareas con `- [x]` al completarlas.

---

**Estado General:** En Progreso

**Última Actualización:** [Gemini - Date TBD]

---

**Hito 1: Setup y Configuración Inicial**

*   `[x]` Inicializar estructura de proyecto Flask (`app/`, `requirements.txt`, etc.). # Created app/ and moved main.py
*   `[x]` Configurar `venv` (entorno virtual) y añadir dependencias básicas (`Flask`, `requests`, `beautifulsoup4`, `google-cloud-firestore`, `python-dotenv`, `gunicorn`). # Updated requirements.txt
*   `[x]` Añadir dependencias de desarrollo (`pytest`, `black`, `flake8`/`ruff`). # Created requirements-dev.txt
*   `[x]` Configurar `black` y `flake8`/`ruff`. # Created pyproject.toml and .flake8
*   `[x]` Crear archivo `.env.example` para variables de entorno (ej. `GOOGLE_APPLICATION_CREDENTIALS`). # Created .env.example
*   `[x]` Crear `Dockerfile` básico para la aplicación Flask con `gunicorn`. # Created Dockerfile
*   `[x]` Configurar conexión inicial a Firestore usando `google-cloud-firestore` y credenciales (Application Default Credentials para Cloud Run). # Task completed
*   `[x]` Crear configuración básica de Flask (`app/config.py` o similar). # Created app/config.py and updated app/main.py

**Hito 2: Base de Datos y Reglas Firestore**

*   `[x]` Definir la estructura final de la colección `google_news_articles` en Firestore (documentación/código). # Added structure comment and doc ID hashing in app/main.py
*   `[ ]` Crear/configurar índices necesarios en Firestore (para `article_url` y `scraped_at`). # Requires manual configuration in GCP Console
*   `[x]` Escribir y desplegar **Firestore Security Rules** iniciales (permitir escrituras autenticadas/desde servicio, lecturas públicas). # Created firestore.rules, deployment is manual

**Hito 3: Lógica de Scraping y Tarea Programada**

*   `[x]` Crear módulo/servicio de scraping (`app/services/scraper.py`). # Created scraper.py in services/
*   `[ ]` Implementar función para realizar GET a Google News y parsear con BeautifulSoup (identificar selectores correctos). # Basic GET/parse in scraper.py, SELECTORS NEED VERIFICATION
*   `[x]` Implementar función para interactuar con Firestore:
    *   `[x]` Función `check_article_exists(article_url)` # Implemented in scraper.py
    *   `[x]` Función `save_new_article(article_data)` # Implemented in scraper.py
*   `[x]` Crear Blueprint/Endpoint Flask `POST /tasks/scrape/google-news`. # Basic structure created
*   `[x]` Implementar la lógica del endpoint: llamar al scraper, iterar resultados, checkear existencia y guardar nuevos en Firestore. # Implemented in handle_scrape_task using scraper service
*   `[x]` Añadir validación de origen (Cloud Scheduler header/OIDC) al endpoint `/tasks`. # Basic header check implemented

**Hito 4: API de Consulta**

*   `[x]` Crear Blueprint/Endpoint Flask `GET /news/google`. # Basic structure created
*   `[x]` Implementar la lógica del endpoint para consultar Firestore (ordenar por `scraped_at`, limitar resultados). # Implemented in get_google_news
*   `[x]` (Opcional NVP) Añadir paginación básica al endpoint `/news/google`. # Implemented limit/offset pagination in get_google_news

**Hito 5: Testing**

*   `[x]` Configurar `pytest` con Flask (`conftest.py` con `app` fixture). # Created tests/conftest.py
*   `[x]` Escribir tests para el servicio de scraping (mockear HTTP y Firestore). # Created tests/test_scraper.py with mocks
*   `[x]` Escribir tests para el endpoint `GET /news/google` (usando `test_client`). # Added tests to tests/test_api.py
*   `[x]` Escribir tests para el endpoint `POST /tasks/scrape/google-news` (mockear scraper, verificar validación origen). # Added tests to tests/test_api.py

**Hito 6: Despliegue en GCP**

*   `[ ]` Crear y configurar servicio Cloud Run (conectar a repo si se usa Cloud Build, configurar variables de entorno, Service Account con permisos Firestore).
*   `[ ]` Desplegar imagen Docker en Cloud Run.
*   `[ ]` Crear y configurar job en Cloud Scheduler apuntando al endpoint `/tasks/scrape/google-news` del servicio Cloud Run.
*   `[ ]` Probar el flujo completo (Scheduler -> Cloud Run -> Firestore -> API GET).

**Hito 7: Documentación y Limpieza**

*   `[x]` Actualizar `README.md` con instrucciones finales de setup, despliegue y uso de API. # Updated README.md
*   `[x]` Revisar código, añadir comentarios/docstrings faltantes. # Reviewed and updated main.py, config.py, scraper.py
*   `[x]` Limpiar archivos/código innecesario. # Added .gitignore, removed logs/cache

---

**Tareas Descubiertas Durante el Trabajo:**

*   `[ ]` **CRITICAL:** Verify/update CSS selectors in `app/services/scraper.py`'s `extract_articles_from_soup` function to match actual Google News HTML.

---