# RULES.md - Reglas de Desarrollo para Proyecto API Scraping Google News

**Propósito:** Este documento define las reglas, convenciones y buenas prácticas que **deben** seguirse durante el desarrollo de este proyecto. Sirve como guía constante para mantener la calidad, consistencia y eficiencia del código.

---

**1. Conciencia del Proyecto y Contexto:**

*   **Leer Contexto Siempre:** **Siempre lee `PLANNING.md` y `RULES.md` (este archivo)** al inicio de una nueva conversación o tarea para entender la arquitectura, objetivos, estilo y restricciones.
*   **Revisar Tareas:** **Comprueba `TASK.md` antes de empezar una nueva tarea.** Asegúrate de que la tarea esté definida.

**2. Estructura del Código y Modularidad:**

*   **Límite de Longitud:** **Nunca crear un archivo `.py` más largo de ~500 líneas.** Refactorizar dividiendo en módulos, blueprints o helpers si se acerca al límite.
*   **Organización Modular:** Organizar el código en módulos claramente separados (`/app`, `/services`, `/models`, etc.) y usar **Blueprints** de Flask para agrupar endpoints por funcionalidad.
*   **Importaciones Claras:** Usar importaciones absolutas o relativas consistentes dentro del proyecto.

**3. Pruebas y Fiabilidad:**

*   **Crear Tests (`pytest`):** **Siempre crear tests unitarios/integración** para nuevas funcionalidades o lógica compleja (endpoints Flask, lógica de scraping, servicios de interacción con Firestore). Usar el cliente de prueba de Flask (`app.test_client()`) y mocks cuando sea necesario.
*   **Actualizar Tests:** Al modificar lógica, **verificar y actualizar los tests existentes.**
*   **Ubicación Tests:** Tests deben residir en un directorio `/tests` que refleje la estructura principal.
*   **Cobertura Mínima por Test:** Incluir casos de uso esperado, casos límite y casos de fallo.

**4. Estilo y Convenciones:**

*   **Lenguaje:** Python (última versión estable compatible con dependencias).
*   **Formato/Linting:** Usar **`black`** para formateo y **`flake8`** (o `ruff`) para linting. Configurar y seguir sus reglas.
*   **Type Hints:** **Obligatorio** usar type hints en todas las definiciones de funciones y variables importantes.
*   **Documentación Funciones (Docstrings):** Escribir **docstrings estilo Google** para todas las funciones/métodos exportados o complejos.

**5. Documentación y Explicabilidad:**

*   **Actualizar `README.md`:** Mantener el `README.md` actualizado con instrucciones de setup, configuración (variables de entorno), ejecución y despliegue.
*   **Comentar Código No Obvio:** Añadir comentarios claros para lógica compleja, workarounds o decisiones importantes.
*   **Comentarios de Razón:** Para lógica compleja, usar `# Reason:` para explicar el *por qué*.

**6. Gestión de Tareas (`TASK.md`):**

*   **Actualizar `TASK.md`:** Marcar tareas como completadas (`- [x]`) **inmediatamente** después de finalizarlas. Añadir fecha si es relevante.
*   **Añadir Nuevas Tareas:** Si se descubren nuevas tareas o subtareas durante el desarrollo, añadirlas a `TASK.md` bajo una sección "Tareas Descubiertas".

**7. Manejo de Secretos:**

*   **Variables de Entorno:** **Nunca hardcodear secretos** (claves API, credenciales DB). Usar variables de entorno leídas por la configuración de Flask (`app.config.from_prefixed_env()` o similar) y configuradas en el entorno de ejecución (Cloud Run).

**8. Reglas de Comportamiento para la IA:**

*   **No Asumir Contexto:** Preguntar si algo no está claro.
*   **No Alucinar:** No inventar librerías/funciones. Usar solo paquetes conocidos y verificar APIs.
*   **Confirmar Rutas:** Verificar nombres de archivo/módulo antes de usarlos.
*   **No Sobrescribir/Eliminar:** No modificar/borrar código existente sin instrucción clara o como parte definida de una tarea en `TASK.md`.

**9. Enfoque NVP:**

*   **Priorizar Funcionalidad Central:** Enfocarse estrictamente en el NVP definido en `PLANNING.md`. Evitar complejidad innecesaria.
*   **Velocidad:** Optimizar para un desarrollo rápido y funcional.