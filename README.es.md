# Agent Loop Básico de Inventario con IA

Sistema de inventario para una pequeña empresa que permite a Carla interactuar
con el inventario mediante lenguaje natural a través de un agente de IA.

## Arquitectura

El sistema tiene dos componentes que se ejecutan simultáneamente:

1. **API REST** — Construida con FastAPI, administra el inventario y persiste
   los productos en `products.csv`.
2. **Agente de IA** — Agente manual en Python puro (sin frameworks de agentes)
   que se conecta a un LLM (OpenAI-compatible), expone los endpoints de la API
   como tools y ejecuta el ciclo **Observa → Piensa → Actúa → Actualiza → Repite**.

## Requisitos

- **Python 3.10+** (recomendado 3.12+)
- Dependencias listadas en la sección de instalación
- Una **API key de OpenAI** (o de cualquier proveedor compatible con la API de OpenAI)

## Instalación

```bash
pip install fastapi uvicorn httpx openai
```

## Configuración

Configura tu API key del LLM mediante una variable de entorno:

```bash
export OPENAI_API_KEY='tu-api-key-aqui'
```

Opcionalmente, puedes configurar:

```bash
# URL base de la API del inventario (por defecto: http://localhost:8000)
export API_BASE_URL='http://localhost:8000'

# Modelo del LLM (por defecto: gpt-4o-mini)
export OPENAI_MODEL='gpt-4o-mini'

# URL base personalizada para el LLM (útil para proveedores compatibles con OpenAI)
export OPENAI_BASE_URL='https://api.openai.com/v1'
```

Nunca escribas tu API key directamente en el código o en el README.

## Ejecución de la API

Inicia primero el servidor FastAPI:

```bash
uvicorn api.app:app --reload --port 8000
```

La API estará disponible en `http://localhost:8000`.

Documentación interactiva en `http://localhost:8000/docs`.

## Ejecución del Agente

Asegúrate de que la API esté corriendo y después inicia el agente:

```bash
python agent.py
```

El agente comenzará una sesión interactiva en la terminal.

Escribe `exit`, `quit` o `salir` para finalizar la sesión.

## Orden de ejecución

**IMPORTANTE:** La API debe iniciarse **antes** que el agente.

```bash
# Terminal 1 — Iniciar la API
uvicorn api.app:app --reload --port 8000

# Terminal 2 — Iniciar el agente
python agent.py
```

El agente se conecta a la API a través de HTTP en `http://localhost:8000`.

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/inventory` | Lista completa de productos |
| `POST` | `/inventory` | Crear un nuevo producto |
| `PATCH` | `/inventory/{product_id}` | Actualizar stock (delta) |
| `GET` | `/inventory/alerts?threshold=10` | Productos con stock bajo |

## Ejemplos de conversación

### Ejemplo 1 — Añadir producto

```
Tú: Acaban de llegar 30 unidades de leche de avena.
Agente: He actualizado el inventario. Se añadieron 30 unidades de leche de avena.
```

### Ejemplo 2 — Consultar stock bajo

```
Tú: ¿Qué productos están por agotarse?
Agente: Estos son los productos con stock bajo:
1. leche de avena — solo 5 unidades
```

### Ejemplo 3 — Interacción multipaso

```
Tú: Acaban de llegar 30 unidades de leche de avena.
Agente: He actualizado el inventario. Ahora hay 30 unidades de leche de avena.

Tú: ¿Qué productos están por agotarse?
Agente: Estos son los productos con stock bajo:
1. leche de avena — solo 5 unidades

Tú: Llegaron 20 más de leche de avena.
Agente: Se añadieron 20 unidades. Ahora hay 25 unidades de leche de avena.

Tú: ¿Y ahora?
Agente: Ya no hay productos con stock bajo. Todos los niveles están bien.
```

## Logging

El agente registra todos los eventos en `conversation_log.csv` con el formato:

```
actor,message,tool_call,timestamp
user,"Acaban de llegar 30 unidades de leche de avena",,"2026-08-19T20:30:00"
agent,"Se añadieron 30 unidades de leche de avena.",,"2026-08-19T20:30:01"
tool,"Stock actualizado correctamente",update_inventory,"2026-08-19T20:30:02"
```

El archivo es **append-only**: nunca sobrescribe sesiones anteriores.

## Ejecución de pruebas

```bash
pip install pytest
python -m pytest tests/ -v
```

## Estructura del proyecto

```
├── api/
│   ├── __init__.py
│   └── app.py          # FastAPI: 4 endpoints + CSV persistence
├── tests/
│   ├── __init__.py
│   └── test_api.py     # Tests para la API
├── agent.py            # Agente de IA manual (sin frameworks)
├── products.csv        # Persistencia del inventario (se crea automáticamente)
├── conversation_log.csv # Log de conversación (se crea automáticamente)
├── main.py             # Archivo original (sin cambios)
├── server.py           # Archivo original (sin cambios)
└── README.md
```
