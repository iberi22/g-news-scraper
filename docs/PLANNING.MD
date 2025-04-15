# PLANNING.md - Planificación del Proyecto API Scraping RSS Feeds (NVP)

**Propósito:** Este documento describe el *qué* y el *cómo* del proyecto: objetivos, arquitectura, stack tecnológico, modelos de datos, APIs y restricciones clave. Sirve como la referencia principal para entender el producto a construir.

---

**1. Resumen del Proyecto y Objetivos:**

*   **Producto:** API RESTful in Python for scraping RSS Feeds.
*   **Objetivo NVP:** Implement the basic functionality of scheduled scraping of RSS Feeds, storing article (metadata) in Firestore, and an endpoint to query the recent articles.
*   **Enfoque:** Functional NVP, fast to implement, scalable, and **extremely cost-conscious**.

**2. Crítica Obligatoria de Restricción:**

*   **GCP Free Tier:** **All design and implementation decisions should prioritize staying within the free limits of Google Cloud Platform (Cloud Run, Cloud Scheduler, Firestore, Logging).** Actively monitor consumption.

**3. Stack Tecnológico Obligatorio:**

*   **API:** Python + **Flask**
*   **Base de Datos:** **Firestore (Native Mode)**
*   **Entorno de Ejecución:** Google Cloud Run (Containerized)
*   **Programación:** Google Cloud Scheduler (Potentially)
*   **Contenerización:** Docker
*   **Scraping:** `feedparser`
*   **GCP SDK:** `google-cloud-firestore`

**4. Arquitectura Propuesta:**

*   **Cloud Run Service (Flask App):**
    *   Contains the Flask API.
    *   Receives public API calls (POST /scrape).
    *   Configuration: Min Instances = 0, minimum resources, appropriate timeout.
*   **Firestore Database:**
    *   Stores scraped article metadata.
    *   Requires Firestore Security Rules configuration.

**5. Modelo de Datos Firestore:**

*   **Collection:** `articles`
    *   **Document ID:** Derived from `article_url` (hashed/transformed) or UUID. Key for duplicate checking.
    *   **Fields:**
        *   `article_url`: string (original URL, indexed).
        *   `title`: string.
        *   `source_name`: string.
        *   `summary`: string (nullable).
        *   `scraped_at`: timestamp (indexed for ordering).
*   **Índices Necesarios:**
    *   For existence check by `article_url`.
    *   To order/filter by `scraped_at` (descending).
*   **Reglas de Seguridad (Firestore Security Rules):** Define to allow reads (public or authenticated) and writes only from the Cloud Run service.

**6. API Endpoints (Flask):**

*   **`POST /scrape`**
    *   **Logic:** Receives an array of RSS Feed URLs, iterates over each URL, parses the RSS feed, extracts the metadata of each article, verifies the existence of the article in Firestore (by `article_url`), and writes a document to Firestore only if it is new.
    *   **Security:** Publicly accessible (or as defined in Security Rules).

**7. Logic de Scraping (Details):**

*   Use `feedparser` to parse RSS feeds.
*   Extract clean data (title, link, description, etc.).
*   **Duplicate Check:** Before writing to Firestore, make a query to see if it already exists.
*   Handle network, parsing, and database errors.

**8. Free Tier Considerations (Reminder):**

*   **Firestore:** Main point of consumption (reads for checking, writes for new ones). Optimize existence query. Limit frequency of scraping.
*   **Cloud Run:** CPU/Memory during scraper execution and API attention. Keep `min-instances=0`.
*   **Logging:** Be aware of the volume of logs generated.