# PLANNING.md - Planificación del Proyecto API Scraping Google News (NVP)

**Propósito:** Este documento describe el *qué* y el *cómo* del proyecto: objetivos, arquitectura, stack tecnológico, modelos de datos, APIs y restricciones clave. Sirve como la referencia principal para entender el producto a construir.

---

**1. Resumen del Proyecto y Objetivos:**

*   **Producto:** API RESTful en Python para scrapear periódicamente Google News.
*   **Objetivo NVP:** Implementar la funcionalidad básica de scraping programado de Google News, almacenamiento de artículos *nuevos* (metadata) en Firestore y un endpoint para consultar los artículos recientes.
*   **Enfoque:** NVP funcional, rápido de implementar, escalable y **extremadamente consciente de los costos**.

**2. Restricción Crítica Obligatoria:**

*   **GCP Free Tier:** **Todas las decisiones de diseño e implementación deben priorizar mantenerse dentro de los límites gratuitos de Google Cloud Platform (Cloud Run, Cloud Scheduler, Firestore, Logging).** Monitorizar activamente el consumo.

**3. Stack Tecnológico Obligatorio:**

*   **API:** Python + **Flask**
*   **Base de Datos:** **Firestore (Modo Nativo)**
*   **Entorno de Ejecución:** Google Cloud Run (contenedorizado)
*   **Programación:** Google Cloud Scheduler
*   **Contenerización:** Docker
*   **Scraping:** `requests` (o `httpx`), `beautifulsoup4`
*   **GCP SDK:** `google-cloud-firestore`

**4. Arquitectura Propuesta:**

*   **Cloud Run Service (Flask App):**
    *   Contiene la API Flask.
    *   Recibe llamadas API públicas (GET /news/google).
    *   Recibe llamadas internas del Scheduler (POST /tasks/scrape/google-news).
    *   Configuración: Min Instances = 0, recursos mínimos, timeout adecuado.
*   **Cloud Scheduler Job:**
    *   Disparador: Cron (ej. `0 * * * *` - cada hora).
    *   Target: HTTP POST al endpoint `/tasks/scrape/google-news` del servicio Cloud Run.
    *   Autenticación: Verificar header `X-CloudScheduler` o usar OIDC.
*   **Firestore Database:**
    *   Almacena metadata de artículos scrapeados.
    *   Requiere configuración de **Firestore Security Rules**.

**5. Modelo de Datos Firestore:**

*   **Colección: `google_news_articles`**
    *   **Document ID:** Derivado del `article_url` (hasheado/transformado) o UUID. Clave para check de duplicados.
    *   **Campos:**
        *   `article_url`: string (URL original, indexado).
        *   `title`: string.
        *   `source_name`: string.
        *   `snippet`: string (nullable).
        *   `google_news_url`: string (nullable).
        *   `scraped_at`: timestamp (indexado para ordenar).
*   **Índices Necesarios:**
    *   Para check de existencia por `article_url`.
    *   Para ordenar/filtrar por `scraped_at` (descendente).
*   **Reglas de Seguridad (Firestore Security Rules):** Definir para permitir lecturas (públicas o autenticadas) y escrituras solo desde el servicio Cloud Run.

**6. API Endpoints (Flask):**

*   **`POST /tasks/scrape/google-news`**
    *   **Lógica:** Valida origen (Scheduler), ejecuta scraping de Google News, parsea HTML, verifica existencia de cada artículo en Firestore (por `article_url`), escribe documento en Firestore **solo si es nuevo**.
    *   **Seguridad:** Requiere validación de origen (Cloud Scheduler).
*   **`GET /news/google`**
    *   **Lógica:** Consulta Firestore (`google_news_articles`), ordena por `scraped_at` desc, aplica paginación (opcional), devuelve lista de artículos (metadata).
    *   **Seguridad:** Accesible públicamente (o según se defina en Security Rules).

**7. Lógica de Scraping (Detalles):**

*   Realizar GET a Google News (URL específica).
*   Usar BeautifulSoup para parsear. **Identificar selectores CSS robustos** para títulos, enlaces, fuentes, snippets (sujeto a cambios por parte de Google).
*   Extraer datos limpios.
*   **Verificación de Duplicados:** Antes de escribir en Firestore, hacer una consulta (`.where('article_url', '==', url).limit(1).get()`) para ver si ya existe. **Esto es crucial.**
*   Manejar errores de red, parsing y base de datos.
*   Ser respetuoso (delays si es necesario, ajustar frecuencia scheduler).

**8. Consideraciones Free Tier (Recordatorio):**

*   **Firestore:** Principal punto de consumo (lecturas para check, escrituras para nuevos). Optimizar consulta de existencia. Limitar frecuencia de scrapeo.
*   **Cloud Run:** CPU/Memoria durante ejecución del scraper y atención de API. Mantener `min-instances=0`.
*   **Scheduler:** 1 job entra en el límite gratuito.
*   **Logging:** Ser consciente del volumen de logs generados.