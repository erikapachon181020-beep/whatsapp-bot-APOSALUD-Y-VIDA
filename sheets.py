import httpx
import csv
import io
import json
from datetime import datetime
from products import get_duracion

SHEET_ID = "1N3xGYFlSsKrUFV6JtrkeBQ_Acc-9ypXlNc9H74qT7N8"

BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzGc7CTExPbsk5zNx-kZ_NqLLhVbPaH_eGDanl_JYaBANLXUwIbZAadlcgj5vVOZo2F/exec"

_catalogo_cache = None


# =============================
# 📦 CATALOGO
# =============================
async def get_catalogo() -> str:
    try:
        url = BASE_URL + "&sheet=Catalogo"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)

        productos = []

        for row in rows:
            if len(row) < 11:
                continue

            if not row[0].startswith("R"):
                continue

            estado = row[10].strip().lower()

            if estado not in ["activo", "disponible"]:
                continue

            if not row[2]:
                continue

            precio_raw = (
                row[6]
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
                .strip()
            )

            try:
                precio = int(precio_raw)
                precio_fmt = "${:,}".format(precio).replace(",", ".")
            except:
                precio_fmt = row[6]

            producto = (
                "- " + row[2]
                + " | Presentación: " + row[3]
                + " | Marca: " + row[4]
                + " | Sabor: " + row[5]
                + " | Precio: " + precio_fmt
                + " | Stock: " + row[7] + " uds"
                + " | Ref: " + row[8]
            )

            productos.append(producto)

        if not productos:
            return "⚠️ No hay productos activos."

        print(f"[CATALOGO OK] {len(productos)} productos")
        return "\n".join(productos)

    except Exception as e:
        print("[ERROR CATALOGO]", str(e))
        return "⚠️ Error catálogo"


async def get_catalogo_cached() -> str:
    global _catalogo_cache

    if _catalogo_cache:
        return _catalogo_cache

    _catalogo_cache = await get_catalogo()
    return _catalogo_cache


# =============================
# 🧾 REGISTRAR PEDIDO
# =============================
async def registrar_pedido(
    telefono,
    nombre,
    referencia,
    producto,
    presentacion,
    marca,
    sabor,
    cantidad,
    precio,
    ubicacion,
):
    try:
        dias = get_duracion(producto)

        now = datetime.now()

        data = {
            "telefono": telefono,
            "nombre": nombre,
            "referencia": referencia,
            "producto": producto,
            "presentacion": presentacion,
            "marca": marca,
            "sabor": sabor,
            "cantidad": cantidad,
            "precio": precio,
            "ubicacion": ubicacion,
            "fecha": now.strftime("%Y-%m-%d"),
            "hora": now.strftime("%H:%M:%S"),
            "dias_duracion": dias,
        }

        async with httpx.AsyncClient() as client:
            await client.post(
                APPS_SCRIPT_URL,
                content=json.dumps(data),
                headers={"Content-Type": "application/json"},
            )

        print("[PEDIDO OK]")
        return True

    except Exception as e:
        print("[ERROR PEDIDO]", str(e))
        return False


# =============================
# 🔁 LEER PEDIDOS (FOLLOW-UP PRO)
# =============================
async def get_pedidos():
    try:
        url = BASE_URL + "&sheet=Pedidos"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)

        pedidos = []

        for row in rows:

            # Validación mínima
            if len(row) < 7:
                continue

            # Saltar encabezado
            if row[0].strip() == "# Pedido":
                continue

            try:
                fecha_str = row[1].strip()
                hora_str = row[2].strip()

                if not fecha_str or not hora_str:
                    continue

                # 🔥 Convertir a ISO
                fecha_iso = f"{fecha_str}T{hora_str}"

                producto = row[6].strip()
                telefono = row[3].strip()
                nombre = row[4].strip()

                dias = get_duracion(producto)

                pedido = {
                    "telefono": telefono,
                    "nombre": nombre,
                    "producto": producto,
                    "fecha": fecha_iso,
                    "dias_duracion": dias,

                    # 🔥 FOLLOWUPS (SEGÚN TU SHEET REAL)
                    "f3": row[15].strip() if len(row) > 15 else "",
                    "f_final": row[16].strip() if len(row) > 16 else "",
                    "f_extra": row[17].strip() if len(row) > 17 else "",
                }

                pedidos.append(pedido)

            except Exception as e:
                print("[ERROR FILA]", row, e)
                continue

        print(f"[PEDIDOS OK] {len(pedidos)} pedidos")
        return pedidos

    except Exception as e:
        print("[ERROR GET PEDIDOS]", str(e))
        return []