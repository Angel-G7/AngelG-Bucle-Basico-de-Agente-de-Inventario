# Proyecto: Agent Loop Básico de Inventario con IA

## Objetivo

En este proyecto vamos a construir dos cosas que trabajan juntas:

1. Una API con **FastAPI** que guarda un inventario en `products.csv`.
2. Un **agente con IA** que recibe mensajes escritos en lenguaje natural, decide qué tool necesita usar, llama a la API y responde al usuario.

El flujo general será:

```text
Usuario
   ↓
agent.py
   ↓
LLM
   ↓
elige una tool
   ↓
API FastAPI
   ↓
products.csv
   ↓
resultado vuelve al agente
   ↓
LLM responde al usuario
```

Además, cada evento de la conversación se guardará en:

```text
conversation_log.csv
```

El agente va a implementar manualmente este ciclo:

```text
Observar
→ Pensar
→ Actuar
→ Actualizar
→ Repetir
```

No vamos a usar LangChain, LangGraph, AutoGen ni ningún framework de agentes.

---

# 1. Crear el proyecto

La consigna propone comenzar desde:

```text
https://github.com/4GeeksAcademy/python-hello
```

Podés hacer un fork y abrirlo con GitHub Codespaces o clonarlo en tu computadora.

Si lo clonás localmente:

```bash
git clone https://github.com/4GeeksAcademy/python-hello.git inventory-agent
```

Entramos en la carpeta:

```bash
cd inventory-agent
```

Abrimos el proyecto en VS Code:

```bash
code .
```

---

# 2. Crear y activar el entorno virtual

Para este proyecto vamos a usar el método clásico con `venv`.

Desde la raíz del proyecto creamos el entorno virtual:

```bash
python -m venv myenv
```

Esto crea una carpeta llamada:

```text
myenv
```

Esa carpeta contiene un Python separado para este proyecto y evita instalar las librerías globalmente en la computadora.

Ahora tenemos que activar el entorno.

## En Windows

```bash
myenv\Scripts\activate
```

Si se activó correctamente, la terminal debería mostrar algo parecido a:

```text
(myenv)
```

al principio de la línea.

Por ejemplo:

```text
(myenv) C:\Users\David\inventory-agent>
```

## En GitHub Codespaces, Linux o macOS

```bash
source myenv/bin/activate
```

Una vez activado el entorno instalamos las dependencias:

```bash
pip install fastapi uvicorn openai python-dotenv
```

Vamos a usar:

- `fastapi`: para crear la API.
- `uvicorn`: para ejecutar la API.
- `openai`: para conectarnos al LLM usando una API compatible con OpenAI.
- `python-dotenv`: para leer la API key desde `.env`.

Para llamar desde el agente a nuestra propia API vamos a usar módulos que ya vienen con Python, así que no necesitamos instalar `requests`.

Podemos comprobar que las librerías quedaron instaladas con:

```bash
pip list
```

IMPORTANTE: cada vez que abramos una terminal nueva para trabajar con el proyecto, tenemos que volver a activar `myenv`.

En Windows:

```bash
myenv\Scripts\activate
```

En Codespaces, Linux o macOS:

```bash
source myenv/bin/activate
```

---

# 3. Crear la estructura de archivos

El proyecto va a quedar así:

```text
inventory-agent/
│
├── api/
│   ├── __init__.py
│   └── app.py
│
├── agent.py
├── products.csv
├── conversation_log.csv
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

`conversation_log.csv` puede no existir inicialmente porque nuestro programa también sabe crearlo automáticamente.

---

# 4. Crear la carpeta `api`

En la raíz del proyecto creamos:

```text
api
```

Adentro creamos:

```text
__init__.py
app.py
```

El archivo:

```text
api/__init__.py
```

puede quedar completamente vacío.

Su única función en este proyecto es hacer que Python trate a `api` como un paquete.

---

# 5. Crear `products.csv`

En la raíz del proyecto creamos:

```text
products.csv
```

Podemos arrancar con algunos productos para poder probar el sistema: ( editalo con boton derecho / text editor )

```csv
id,name,quantity,unit
1,Leche de avena,18,unidades
2,Café arábica,40,bolsas
3,Vasos térmicos,7,paquetes
```

Los campos son:

```text
id
name
quantity
unit
```

Por ejemplo:

```text
1,Leche de avena,18,unidades
```

significa:

```text
Producto: Leche de avena
Cantidad: 18
Unidad de medida: unidades
```

---

# 6. Crear la API en `api/app.py`

Abrimos:

```text
api/app.py
```

y colocamos:

```python
import csv
import os

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


app = FastAPI()


PRODUCTS_FILE = "products.csv"


class ProductCreate(BaseModel):
    name: str
    quantity: float
    unit: str


class StockUpdate(BaseModel):
    delta: float


def ensure_products_file():
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["id", "name", "quantity", "unit"]
            )
            writer.writeheader()


def read_products():
    ensure_products_file()

    products = []

    with open(PRODUCTS_FILE, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            products.append({
                "id": int(row["id"]),
                "name": row["name"],
                "quantity": float(row["quantity"]),
                "unit": row["unit"]
            })

    return products


def write_products(products):
    with open(PRODUCTS_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["id", "name", "quantity", "unit"]
        )

        writer.writeheader()

        for product in products:
            writer.writerow(product)


@app.get("/inventory")
def get_inventory():
    return read_products()


@app.post("/inventory", status_code=201)
def create_product(product: ProductCreate):
    products = read_products()

    for existing_product in products:
        if existing_product["name"].lower() == product.name.lower():
            raise HTTPException(
                status_code=409,
                detail="Ya existe un producto con ese nombre"
            )

    if product.quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="La cantidad inicial no puede ser negativa"
        )

    new_id = 1

    if products:
        new_id = max(product["id"] for product in products) + 1

    new_product = {
        "id": new_id,
        "name": product.name,
        "quantity": product.quantity,
        "unit": product.unit
    }

    products.append(new_product)
    write_products(products)

    return new_product


@app.patch("/inventory/{product_id}")
def update_stock(product_id: int, stock_update: StockUpdate):
    products = read_products()

    for product in products:
        if product["id"] == product_id:
            new_quantity = product["quantity"] + stock_update.delta

            if new_quantity < 0:
                raise HTTPException(
                    status_code=400,
                    detail="La operación dejaría el stock en negativo"
                )

            product["quantity"] = new_quantity
            write_products(products)

            return product

    raise HTTPException(
        status_code=404,
        detail="Producto no encontrado"
    )


@app.get("/inventory/alerts")
def get_inventory_alerts(
    threshold: float = Query(default=10, ge=0)
):
    products = read_products()

    alerts = [
        product
        for product in products
        if product["quantity"] < threshold
    ]

    return alerts
```

---

# 7. Entender qué hace esta API

Tenemos exactamente los cuatro endpoints pedidos.

## GET `/inventory`

Devuelve todos los productos.

Ejemplo:

```http
GET /inventory
```

Respuesta:

```json
[
    {
        "id": 1,
        "name": "Leche de avena",
        "quantity": 18,
        "unit": "unidades"
    },
    {
        "id": 2,
        "name": "Café arábica",
        "quantity": 40,
        "unit": "bolsas"
    }
]
```

---

## POST `/inventory`

Crea un producto nuevo.

Ejemplo:

```http
POST /inventory
```

Body:

```json
{
    "name": "Jarabe de vainilla",
    "quantity": 8,
    "unit": "botellas"
}
```

La API genera automáticamente el `id`.

---

## PATCH `/inventory/{product_id}`

Modifica el stock usando un `delta`.

Ejemplo:

```http
PATCH /inventory/1
```

Body:

```json
{
    "delta": 30
}
```

Si el producto tenía:

```text
18
```

ahora tendrá:

```text
48
```

Un `delta` positivo significa entrada de mercadería.

```json
{
    "delta": 30
}
```

Un `delta` negativo significa salida o venta.

```json
{
    "delta": -12
}
```

Por ejemplo:

```text
40 - 12 = 28
```

---

## GET `/inventory/alerts`

Devuelve los productos cuyo stock sea menor que un límite.

Por defecto el límite es:

```text
10
```

Entonces:

```http
GET /inventory/alerts
```

devuelve todo producto cuya cantidad sea menor que `10`.

También podemos elegir otro límite:

```http
GET /inventory/alerts?threshold=20
```

---

# 8. Probar primero la API

Antes de crear el agente conviene comprobar que la API funciona sola.

Abrimos una terminal y ejecutamos:

```bash
uvicorn api.app:app --reload
```

Deberíamos ver algo parecido a:

```text
Uvicorn running on http://127.0.0.1:8000
```

Ahora abrimos:

```text
http://127.0.0.1:8000/docs
```

FastAPI nos muestra Swagger.

Desde ahí podemos probar los cuatro endpoints.

---

# 9. Probar `GET /inventory`

En Swagger buscamos:

```text
GET /inventory
```

presionamos:

```text
Try it out
```

y luego:

```text
Execute
```

Deberíamos obtener los productos guardados en:

```text
products.csv
```

---

# 10. Probar `POST /inventory`

Probamos:

```text
POST /inventory
```

con:

```json
{
    "name": "Filtros de café",
    "quantity": 25,
    "unit": "cajas"
}
```

Después volvemos a ejecutar:

```text
GET /inventory
```

y deberíamos ver el producto nuevo.

También podemos abrir directamente:

```text
products.csv
```

y comprobar que apareció una fila nueva.

Esto demuestra que el dato fue realmente guardado en el archivo.

---

# 11. Probar `PATCH /inventory/{product_id}`

Supongamos que queremos sumar stock al producto con ID `1`.

Ejecutamos:

```text
PATCH /inventory/1
```

con:

```json
{
    "delta": 30
}
```

La cantidad aumenta en 30.

Ahora probamos una salida de stock:

```json
{
    "delta": -5
}
```

La cantidad disminuye en 5.

---

# 12. Probar las alertas

Ejecutamos:

```text
GET /inventory/alerts
```

Con nuestros datos iniciales:

```text
Vasos térmicos = 7
```

debería aparecer porque:

```text
7 < 10
```

También podemos probar:

```text
GET /inventory/alerts?threshold=20
```

---

# 13. Comprobar la persistencia

Este punto es importante porque aparece expresamente en la evaluación.

Detenemos la API:

```text
Ctrl + C
```

La volvemos a levantar:

```bash
uvicorn api.app:app --reload
```

Ejecutamos otra vez:

```text
GET /inventory
```

Los productos deberían seguir ahí.

Eso ocurre porque no guardamos el inventario solamente en una variable de Python.

Lo guardamos físicamente en:

```text
products.csv
```

---

# 14. Crear `.env`

En la raíz del proyecto creamos:

```text
.env
```

Adentro colocamos:

```env
GROQ_API_KEY=tu_clave_aqui
```

Reemplazamos:

```text
tu_clave_aqui
```

por nuestra clave real.

Nunca subimos esta clave a GitHub.

---

# 15. Crear `.gitignore`

Abrimos o creamos:

```text
.gitignore
```

y verificamos que tenga:

```gitignore
.env
myenv/
__pycache__/
*.pyc
```

Así Git no sube nuestra API key.

---

# 16. Crear `agent.py`

Ahora viene la segunda parte del proyecto.

Creamos en la raíz:

```text
agent.py
```

Vamos a construir manualmente:

```text
input del usuario
→ LLM
→ tool
→ API
→ resultado
→ LLM
→ respuesta
```

Pegamos este código:

```python
import csv
import json
import os

from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


API_BASE_URL = "http://127.0.0.1:8000"
LOG_FILE = "conversation_log.csv"

MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_inventory",
            "description": (
                "Devuelve todos los productos del inventario. "
                "Usala también cuando necesites descubrir el ID "
                "de un producto antes de modificar su stock."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_product",
            "description": (
                "Crea un producto nuevo en el inventario."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nombre del producto"
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Cantidad inicial"
                    },
                    "unit": {
                        "type": "string",
                        "description": (
                            "Unidad de medida, por ejemplo unidades, "
                            "bolsas, kg o litros"
                        )
                    }
                },
                "required": [
                    "name",
                    "quantity",
                    "unit"
                ],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_stock",
            "description": (
                "Actualiza la cantidad de un producto usando su ID. "
                "delta positivo significa entrada de stock y "
                "delta negativo significa salida o venta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "ID del producto"
                    },
                    "delta": {
                        "type": "number",
                        "description": (
                            "Cantidad que se suma o resta del stock"
                        )
                    }
                },
                "required": [
                    "product_id",
                    "delta"
                ],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_alerts",
            "description": (
                "Devuelve los productos con stock menor que un "
                "umbral. Si el usuario no indica un límite, usar 10."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "description": (
                            "Cantidad mínima considerada segura"
                        )
                    }
                },
                "additionalProperties": False
            }
        }
    }
]


def log_event(actor, message, tool_call=""):
    file_exists = os.path.exists(LOG_FILE)
    file_is_empty = (
        not file_exists
        or os.path.getsize(LOG_FILE) == 0
    )

    with open(
        LOG_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "actor",
                "message",
                "tool_call",
                "timestamp"
            ]
        )

        if file_is_empty:
            writer.writeheader()

        writer.writerow({
            "actor": actor,
            "message": message,
            "tool_call": tool_call,
            "timestamp": datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        })


def api_request(method, path, data=None):
    url = f"{API_BASE_URL}{path}"

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json"
        }
    )

    try:
        with urlopen(request) as response:
            response_text = response.read().decode("utf-8")

            if not response_text:
                return {}

            return json.loads(response_text)

    except HTTPError as error:
        response_text = error.read().decode("utf-8")

        try:
            detail = json.loads(response_text)
        except json.JSONDecodeError:
            detail = response_text

        return {
            "error": True,
            "status": error.code,
            "detail": detail
        }

    except URLError:
        return {
            "error": True,
            "detail": (
                "No se pudo conectar con la API. "
                "Comprobá que FastAPI esté ejecutándose."
            )
        }


def execute_tool(tool_name, arguments):
    if tool_name == "list_inventory":
        return api_request(
            "GET",
            "/inventory"
        )

    if tool_name == "create_product":
        return api_request(
            "POST",
            "/inventory",
            {
                "name": arguments["name"],
                "quantity": arguments["quantity"],
                "unit": arguments["unit"]
            }
        )

    if tool_name == "update_stock":
        product_id = arguments["product_id"]

        return api_request(
            "PATCH",
            f"/inventory/{product_id}",
            {
                "delta": arguments["delta"]
            }
        )

    if tool_name == "get_low_stock_alerts":
        threshold = arguments.get(
            "threshold",
            10
        )

        query = urlencode({
            "threshold": threshold
        })

        return api_request(
            "GET",
            f"/inventory/alerts?{query}"
        )

    return {
        "error": True,
        "detail": f"Tool desconocida: {tool_name}"
    }


def call_llm(memory):
    system_prompt = """
Sos un asistente de inventario para una tienda
de suministros de cafetería.

Tu trabajo es responder preguntas sobre el inventario
y realizar cambios usando las tools disponibles.

Reglas:

- Nunca inventes cantidades.
- Cuando necesites información real del inventario,
  usá una tool.
- Para crear productos usá create_product.
- Para consultar productos usá list_inventory.
- Para consultar faltantes usá get_low_stock_alerts.
- Para modificar stock usá update_stock.
- update_stock necesita el ID del producto.
- Si el usuario menciona un producto por nombre y
  no conocés su ID, primero usá list_inventory.
- Un ingreso de mercadería usa delta positivo.
- Una venta o salida de mercadería usa delta negativo.
- Después de recibir el resultado de una tool,
  analizalo y decidí si necesitás otra tool.
- Cuando ya tengas suficiente información,
  respondé directamente al usuario.
- Respondé de forma clara y breve.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ] + memory

    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )


def run_agent():
    memory = []

    print("Agente de inventario iniciado.")
    print("Escribí 'salir' para terminar.\n")

    while True:
        user_input = input("Vos: ").strip()

        if not user_input:
            continue

        if user_input.lower() in [
            "salir",
            "exit",
            "quit"
        ]:
            print("Agente finalizado.")
            break

        memory.append({
            "role": "user",
            "content": user_input
        })

        log_event(
            actor="user",
            message=user_input
        )

        while True:
            response = call_llm(memory)

            assistant_message = (
                response.choices[0].message
            )

            memory.append(
                assistant_message.model_dump(
                    exclude_none=True
                )
            )

            if assistant_message.tool_calls:
                for tool_call in (
                    assistant_message.tool_calls
                ):
                    tool_name = (
                        tool_call.function.name
                    )

                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                    log_event(
                        actor="agent",
                        message=json.dumps(
                            arguments,
                            ensure_ascii=False
                        ),
                        tool_call=tool_name
                    )

                    result = execute_tool(
                        tool_name,
                        arguments
                    )

                    result_text = json.dumps(
                        result,
                        ensure_ascii=False
                    )

                    log_event(
                        actor="tool",
                        message=result_text,
                        tool_call=tool_name
                    )

                    memory.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text
                    })

                continue

            final_answer = (
                assistant_message.content
                or "No pude generar una respuesta."
            )

            print(
                f"\nAgente: {final_answer}\n"
            )

            log_event(
                actor="agent",
                message=final_answer
            )

            break


if __name__ == "__main__":
    run_agent()
```

---

# 17. Entender las partes importantes de `agent.py`

No hace falta memorizar todo el archivo de golpe.

Hay seis partes importantes.

---

## Parte 1: configuración

```python
load_dotenv()
```

lee:

```text
.env
```

Después creamos el cliente:

```python
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)
```

El agente usa la API compatible con OpenAI de Groq.

---

## Parte 2: las tools

La variable:

```python
TOOLS
```

describe lo que el LLM puede hacer.

Por ejemplo:

```python
{
    "name": "update_stock",
    "description": "...",
    "parameters": {...}
}
```

Esto no ejecuta todavía ninguna función.

Solamente le explica al LLM:

```text
Existe una herramienta llamada update_stock.
Necesita product_id y delta.
Sirve para modificar el stock.
```

El modelo decide cuándo pedirnos que la ejecutemos.

---

# 18. Diferencia entre tool y endpoint

Tenemos esta tool:

```text
update_stock
```

y esta tool termina llamando a este endpoint:

```text
PATCH /inventory/{product_id}
```

El LLM no llama directamente a FastAPI.

El flujo es:

```text
LLM
↓
pide ejecutar update_stock
↓
agent.py recibe esa decisión
↓
execute_tool()
↓
PATCH /inventory/{product_id}
↓
FastAPI modifica products.csv
```

---

# 19. La función `execute_tool()`

Esta función funciona como puente entre:

```text
nombre de tool
```

y:

```text
endpoint real de FastAPI
```

Por ejemplo:

```python
if tool_name == "update_stock":
```

termina ejecutando:

```python
api_request(
    "PATCH",
    f"/inventory/{product_id}",
    {
        "delta": arguments["delta"]
    }
)
```

Ahí ocurre la llamada real a nuestra API.

---

# 20. La memoria

Al comenzar:

```python
memory = []
```

Cuando el usuario escribe algo:

```python
memory.append({
    "role": "user",
    "content": user_input
})
```

Cuando el LLM responde:

```python
memory.append(
    assistant_message.model_dump(
        exclude_none=True
    )
)
```

Cuando una tool devuelve un resultado:

```python
memory.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": result_text
})
```

Entonces durante la sesión la memoria puede terminar teniendo algo así:

```text
usuario
↓
agente pidió list_inventory
↓
resultado de list_inventory
↓
agente pidió update_stock
↓
resultado de update_stock
↓
respuesta final
↓
nuevo mensaje del usuario
```

Ese historial completo vuelve a enviarse al LLM en la siguiente interacción.

Por eso el agente puede mantener contexto durante la sesión.

Cuando cerramos `agent.py`, esta memoria en RAM desaparece.

Eso está bien.

La consigna solamente pide mantenerla durante la sesión.

El historial permanente queda guardado aparte en:

```text
conversation_log.csv
```

---

# 21. El loop del agente

La parte central es:

```python
while True:
    response = call_llm(memory)
```

El LLM puede devolver dos tipos de respuesta.

## Caso A: quiere usar una tool

```python
if assistant_message.tool_calls:
```

Entonces:

```text
1. Detectamos la tool.
2. Leemos sus argumentos.
3. Ejecutamos la tool.
4. Guardamos el resultado en memoria.
5. Volvemos al comienzo del while.
6. Mandamos nuevamente todo al LLM.
```

Eso representa:

```text
Pensar
→ Actuar
→ Actualizar
→ Repetir
```

---

## Caso B: ya tiene una respuesta final

Si:

```python
assistant_message.tool_calls
```

no tiene llamadas pendientes, entonces hacemos:

```python
final_answer = assistant_message.content
```

La mostramos:

```python
print(f"\nAgente: {final_answer}\n")
```

y terminamos ese ciclo:

```python
break
```

Después el usuario puede escribir otro mensaje.

---

# 22. Ejemplo real del loop

Supongamos que escribimos:

```text
Acaban de llegar 30 unidades de leche de avena
```

El LLM sabe el nombre del producto, pero no necesariamente su ID.

Entonces puede decidir:

```text
list_inventory
```

El agente llama:

```text
GET /inventory
```

y recibe algo parecido a:

```json
[
    {
        "id": 1,
        "name": "Leche de avena",
        "quantity": 18,
        "unit": "unidades"
    }
]
```

Ese resultado vuelve a entrar en `memory`.

El agente consulta nuevamente al LLM.

Ahora el LLM sabe:

```text
Leche de avena
ID = 1
```

Entonces pide:

```text
update_stock
```

con:

```json
{
    "product_id": 1,
    "delta": 30
}
```

El agente llama:

```text
PATCH /inventory/1
```

FastAPI actualiza:

```text
18 + 30 = 48
```

El resultado vuelve al LLM.

Finalmente el LLM puede responder:

```text
Listo. La leche de avena quedó con 48 unidades.
```

Ese es exactamente el comportamiento:

```text
Observar
→ Pensar
→ Actuar
→ Actualizar
→ Repetir
```

---

# 23. Crear `conversation_log.csv`

No es obligatorio crearlo manualmente porque `log_event()` sabe generarlo.

Pero si queremos dejarlo creado desde el principio podemos poner:

```csv
actor,message,tool_call,timestamp
```

Nada más.

Nuestro código lo abre siempre con:

```python
"a"
```

que significa:

```text
append
```

Es decir:

```text
agregar al final
```

Nunca usamos:

```python
"w"
```

para este archivo.

Por eso las conversaciones anteriores no se borran.

---

# 24. Qué registra `conversation_log.csv`

Si escribimos:

```text
Acaban de llegar 30 unidades de leche de avena
```

podemos terminar con filas parecidas a estas:

```csv
actor,message,tool_call,timestamp
user,Acaban de llegar 30 unidades de leche de avena,,2026-08-19T14:00:00-03:00
agent,"{}",list_inventory,2026-08-19T14:00:01-03:00
tool,"[{...}]",list_inventory,2026-08-19T14:00:01-03:00
agent,"{""product_id"": 1, ""delta"": 30}",update_stock,2026-08-19T14:00:02-03:00
tool,"{...}",update_stock,2026-08-19T14:00:02-03:00
agent,Listo. La leche de avena quedó actualizada.,,2026-08-19T14:00:03-03:00
```

Tenemos exactamente los cuatro campos pedidos:

```text
actor
message
tool_call
timestamp
```

---

# 25. Ejecutar el proyecto completo

Necesitamos dos terminales.

---

## Terminal 1: API

Desde la raíz:

```bash
uvicorn api.app:app --reload
```

La dejamos ejecutándose.

---

## Terminal 2: agente

Abrimos otra terminal en la misma carpeta:

```bash
python agent.py
```

Deberíamos ver:

```text
Agente de inventario iniciado.
Escribí 'salir' para terminar.

Vos:
```

---

# 26. Primera prueba del agente

Escribimos de la siguiente forma:


1. En una terminal levantás la API:

<pre class="overflow-visible! px-0!" data-start="287" data-end="350"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="relative h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class=""><div class="relative"><div class=""><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:0:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código" data-language="shell"><div class="cm-line">myenv\Scripts\activate</div><div class="cm-line">uvicorn api.app:app <span class="ͼ12">--reload</span></div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></div></div></pre>

Eso deja FastAPI corriendo en:

<pre class="overflow-visible! px-0!" data-start="384" data-end="417"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute end-1.5 top-1 z-2 md:end-2 md:top-1"></div><div class="relative"><div class="pe-11 pt-3"><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:1:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código"><div class="cm-line">http://127.0.0.1:8000</div></div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></pre>

2. Abrís **otra terminal** y ejecutás el agente:

<pre class="overflow-visible! px-0!" data-start="469" data-end="519"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="relative h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class=""><div class="relative"><div class=""><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:2:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código" data-language="shell"><div class="cm-line">myenv\Scripts\activate</div><div class="cm-line">python agent.py</div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></div></div></pre>

3. Ahí vas a ver algo parecido a:

<pre class="overflow-visible! px-0!" data-start="556" data-end="635"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute end-1.5 top-1 z-2 md:end-2 md:top-1"></div><div class="relative"><div class="pe-11 pt-3"><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:3:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código"><div class="cm-line">Agente de inventario iniciado.</div><div class="cm-line">Escribí 'salir' para terminar.</div><div class="cm-line"><br/></div><div class="cm-line">Vos:</div></div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></pre>

**Ese `Vos:` es donde le escribís al agente.**

Por ejemplo:

<pre class="overflow-visible! px-0!" data-start="699" data-end="739"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute end-1.5 top-1 z-2 md:end-2 md:top-1"></div><div class="relative"><div class="pe-11 pt-3"><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:4:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código"><div class="cm-line">Vos: ¿Qué productos tenemos?</div></div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></pre>

Enter.

Después:

<pre class="overflow-visible! px-0!" data-start="759" data-end="818"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute end-1.5 top-1 z-2 md:end-2 md:top-1"></div><div class="relative"><div class="pe-11 pt-3"><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:5:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código"><div class="cm-line">Agente: Tenemos leche de avena, café arábica...</div></div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></pre>

Y podés seguir:

<pre class="overflow-visible! px-0!" data-start="837" data-end="888"><div class="relative w-full mt-4 mb-1"><div class=""><div class="contents"><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border border-token-border-light border-radius-3xl corner-superellipse/1.1 rounded-3xl"><div class="h-full w-full border-radius-3xl bg-(--code-block-surface) corner-superellipse/1.1 overflow-clip rounded-3xl [--code-block-surface:var(--bg-elevated-secondary)] dark:[--code-block-surface:var(--composer-surface-primary)] lxnfua_clipPathFallback"><div class="pointer-events-none absolute end-1.5 top-1 z-2 md:end-2 md:top-1"></div><div class="relative"><div class="pe-11 pt-3"><div class="relative z-0 flex h-full min-h-0 max-w-full"><div id="65198eb8-ff95-4309-bd97-8d074974ed5e:6:editor" dir="ltr" class="Rx43rG_codemirror z-10 flex h-full min-h-0 w-full flex-col items-stretch"><div class="cm-editor ͼ1 ͼ3 ͼs ͼ16"><div class="cm-announced" aria-live="polite"></div><div tabindex="-1" class="cm-scroller"><div spellcheck="false" autocorrect="off" autocapitalize="off" writingsuggestions="false" translate="no" contenteditable="false" class="cm-content" role="textbox" aria-multiline="true" aria-readonly="true" aria-label="Editar código"><div class="cm-line">Vos: Vendimos 12 bolsas de café arábica</div></div></div></div></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></div></pre>

Enter.

Entonces vamos con : 

```text
¿Qué productos tenemos?
```

El agente debería usar:

```text
list_inventory
```

y responder usando la información real de:

```text
products.csv
```

---

# 27. Probar una entrada de stock

Escribimos:

```text
Acaban de llegar 30 unidades de leche de avena
```

El agente debería:

```text
1. Buscar el inventario.
2. Encontrar el ID de Leche de avena.
3. Ejecutar update_stock.
4. Usar delta = 30.
5. Responder con el nuevo stock.
```

Después podemos abrir:

```text
products.csv
```

y comprobar que cambió realmente.

---

# 28. Probar una venta

Escribimos:

```text
Vendimos 12 bolsas de café arábica
```

El agente debería terminar ejecutando algo equivalente a:

```json
{
    "product_id": 2,
    "delta": -12
}
```

El signo negativo es importante porque estamos sacando stock.

---

# 29. Probar alertas

Escribimos:

```text
¿Qué productos están por agotarse?
```

El agente debería elegir:

```text
get_low_stock_alerts
```

sin que nosotros tengamos que escribir manualmente:

```text
GET /inventory/alerts
```

Ese es justamente el objetivo del proyecto.

El usuario habla normalmente y el LLM decide qué endpoint necesita utilizar.

---

# 30. Probar la creación de un producto

Escribimos:

```text
Agregá jarabe de caramelo, tenemos 15 botellas
```

El LLM debería usar:

```text
create_product
```

con algo parecido a:

```json
{
    "name": "Jarabe de caramelo",
    "quantity": 15,
    "unit": "botellas"
}
```

El producto debería aparecer luego en:

```text
products.csv
```

---

# 31. Probar que existe memoria durante la sesión

Podemos escribir:

```text
¿Cuánto café arábica tenemos?
```

y después:

```text
Restale otras 3 bolsas
```

Como el historial permanece en:

```python
memory
```

el LLM tiene acceso a los mensajes anteriores de esa sesión y puede interpretar mejor referencias como:

```text
otras 3 bolsas
```

La información real siempre debe confirmarse usando las tools.

---

# 32. Probar que el log no se sobreescribe

Usamos el agente un rato.

Después escribimos:

```text
salir
```

Volvemos a ejecutarlo:

```bash
python agent.py
```

Hacemos una consulta nueva.

Después abrimos:

```text
conversation_log.csv
```

Las filas anteriores deberían seguir ahí y las nuevas deberían haberse agregado debajo.

Eso demuestra que el archivo es:

```text
append-only
```

---

# 33. Comprobar códigos de error de la API

También conviene probar algunos errores.

## Producto inexistente

Ejemplo:

```text
PATCH /inventory/9999
```

Respuesta esperada:

```text
404
```

con un mensaje descriptivo.

---

## Intentar dejar stock negativo

Si tenemos:

```text
5 unidades
```

y mandamos:

```json
{
    "delta": -20
}
```

la API debe responder:

```text
400
```

porque el resultado sería negativo.

---

## Producto duplicado

Si intentamos crear dos veces:

```text
Leche de avena
```

la API responde:

```text
409
```

porque ese nombre ya existe.

---

# 34. Crear `requirements.txt`

Con `myenv` activado ejecutamos:

```bash
pip freeze > requirements.txt
```

Esto guarda las dependencias instaladas en un archivo.

El contenido puede verse parecido a:

```text
fastapi==...
openai==...
python-dotenv==...
uvicorn==...
```

Los números de versión pueden ser distintos y está bien.

Este archivo permite que otra persona pueda instalar las mismas dependencias ejecutando:

```bash
pip install -r requirements.txt
```

---

# 35. Crear o actualizar `README.md`

El proyecto entregado tiene que explicar cómo arrancar ambos procesos.

Podemos dejar un `README.md` sencillo como este:

```markdown
# Agent Loop Básico de Inventario con IA

Proyecto compuesto por:

- API REST con FastAPI.
- Persistencia del inventario en `products.csv`.
- Agente con LLM y tool calling.
- Registro append-only en `conversation_log.csv`.

## Crear el entorno virtual

```bash
python -m venv myenv
```

Activar en Windows:

```bash
myenv\Scripts\activate
```

Activar en Codespaces, Linux o macOS:

```bash
source myenv/bin/activate
```

## Instalar dependencias

```bash
pip install -r requirements.txt
```

## Variables de entorno

Crear `.env`:

```env
GROQ_API_KEY=tu_clave_aqui
```

## Ejecutar la API

Terminal 1:

```bash
uvicorn api.app:app --reload
```

## Ejecutar el agente

Terminal 2:

```bash
python agent.py
```

## Detener

Presionar:

```text
Ctrl + C
```

Primero en el agente y después en la API.

```

---

# 36. Revisar que `.env` no se vaya a subir

Antes de hacer commit ejecutamos:

```bash
git status
```

No debería aparecer:

```text
.env
```

Si aparece, revisamos:

```text
.gitignore
```

y confirmamos que tenga:

```gitignore
.env
```

---

# 37. Checklist contra la consigna

Antes de entregar revisamos punto por punto.

## API

- [ ] Existe `api/app.py`.
- [ ] FastAPI arranca correctamente.
- [ ] Existe `GET /inventory`.
- [ ] Existe `POST /inventory`.
- [ ] Existe `PATCH /inventory/{product_id}`.
- [ ] Existe `GET /inventory/alerts`.
- [ ] `PATCH` recibe `delta`.
- [ ] `delta` positivo suma stock.
- [ ] `delta` negativo resta stock.
- [ ] Los errores usan códigos HTTP apropiados.
- [ ] Los productos se guardan en `products.csv`.
- [ ] Los productos sobreviven a un reinicio de la API.

## Agente

- [ ] Existe `agent.py`.
- [ ] El agente recibe texto desde la terminal.
- [ ] El agente mantiene `memory` durante la sesión.
- [ ] Las cuatro operaciones de la API están descriptas como tools.
- [ ] Cada tool tiene `name`.
- [ ] Cada tool tiene `description`.
- [ ] Cada tool tiene `parameters`.
- [ ] Los parámetros están tipados.
- [ ] El LLM puede seleccionar una tool.
- [ ] El agente ejecuta manualmente la tool elegida.
- [ ] La tool llama al endpoint correcto de FastAPI.
- [ ] El resultado de la tool vuelve a agregarse a `memory`.
- [ ] El LLM recibe ese resultado en la siguiente iteración.
- [ ] El loop continúa mientras existan tool calls.
- [ ] El loop termina cuando llega una respuesta final.
- [ ] No usamos LangChain.
- [ ] No usamos LangGraph.
- [ ] No usamos AutoGen.
- [ ] El loop está escrito manualmente en Python.

## Registro de conversación

- [ ] Existe `conversation_log.csv`.
- [ ] Tiene el campo `actor`.
- [ ] Tiene el campo `message`.
- [ ] Tiene el campo `tool_call`.
- [ ] Tiene el campo `timestamp`.
- [ ] Se registra el mensaje del usuario.
- [ ] Se registra la llamada a una tool.
- [ ] Se registra el resultado de una tool.
- [ ] Se registra la respuesta final del agente.
- [ ] El archivo usa append.
- [ ] Reiniciar el agente no borra conversaciones anteriores.

## Prueba de varios pasos

- [ ] Probamos una operación donde el LLM necesite más de una iteración.

Por ejemplo:

```text
Acaban de llegar 30 unidades de leche de avena.
```

Un flujo válido sería:

```text
Usuario
↓
LLM
↓
list_inventory
↓
resultado
↓
LLM
↓
update_stock
↓
resultado
↓
LLM
↓
respuesta final
```

Después podemos preguntar:

```text
¿Qué productos están por agotarse?
```

El agente debería seguir funcionando con el historial de la sesión.

---

# 38. Revisar los archivos finales

Antes de entregar deberíamos tener como mínimo:

```text
api/app.py
agent.py
products.csv
README.md
.gitignore
requirements.txt
```

`conversation_log.csv` también debería aparecer después de haber probado el agente.

El `.env` debe existir localmente pero NO debe subirse al repositorio.

---

# 39. Hacer commit

Revisamos:

```bash
git status
```

Agregamos los archivos:

```bash
git add .
```

Creamos el commit:

```bash
git commit -m "Finish inventory AI agent project"
```

---

# 40. Subir a GitHub

Si el remote ya está correctamente configurado:

```bash
git push
```

Si estamos trabajando sobre una rama específica:

```bash
git push origin main
```

o el nombre de la rama que corresponda.

---

# 41. Entrega

La entrega final consiste en compartir el enlace del repositorio de GitHub siguiendo las instrucciones del instructor.

Antes de copiar el enlace hacemos una última comprobación visual en GitHub.

El repositorio debería mostrar:

```text
api/
    __init__.py
    app.py

agent.py
products.csv
conversation_log.csv
README.md
.gitignore
requirements.txt
```

No debería aparecer:

```text
.env
```

Finalmente verificamos que el `README.md` explique cómo ejecutar:

```text
Terminal 1 → API
Terminal 2 → agente
```

Con eso el proyecto cubre los requisitos pedidos sin agregar una arquitectura innecesariamente complicada.
