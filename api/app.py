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