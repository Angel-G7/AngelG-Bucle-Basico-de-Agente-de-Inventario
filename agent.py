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