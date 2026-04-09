import os
import json
import difflib
import gspread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ["BOT_TOKEN"]

gc = gspread.service_account_from_dict(
    json.loads(os.environ["GOOGLE_CREDENTIALS"])
)
sh = gc.open("STOCK ONLINE X DEPOSITO ACTUAL 2026")
ws = sh.worksheet("python")


def obtener_datos():
    return ws.get_all_values()


def obtener_encabezados():
    datos = obtener_datos()
    return [h.strip() for h in datos[2]]


def obtener_productos():
    encabezados = obtener_encabezados()
    return [h.strip() for h in encabezados[2:]]


def obtener_productos_lower():
    return [p.lower() for p in obtener_productos()]


def obtener_depositos():
    datos = obtener_datos()
    depositos = []

    for fila in datos[3:]:
        deposito = fila[1].strip()
        if deposito.lower() == "total stocks":
            break
        depositos.append(deposito)

    return depositos


def obtener_depositos_lower():
    return [d.lower() for d in obtener_depositos()]


def es_menu(texto):
    opciones_menu = [
        "hola",
        "buen dia",
        "buen día",
        "buenas",
        "buenas tardes",
        "buenas noches",
        "hey",
        "holi",
        "que tal",
        "qué tal",
        "stock",
        "menu",
        "menú",
        "ayuda",
    ]
    return texto.lower().strip() in opciones_menu


def sugerir_opciones(texto, opciones, n=3, cutoff=0.5):
    opciones_lower = [o.lower() for o in opciones]
    return difflib.get_close_matches(texto.lower(), opciones_lower, n=n, cutoff=cutoff)


def buscar_producto(nombre_producto):
    datos = obtener_datos()
    encabezados = [h.strip().lower() for h in datos[2]]

    nombre_producto = nombre_producto.strip().lower()

    if nombre_producto not in encabezados:
        return None

    idx = encabezados.index(nombre_producto)
    resultado = []

    for fila in datos[3:]:
        deposito = fila[1].strip()

        if deposito.lower() == "total stocks":
            break

        stock = fila[idx].strip()
        resultado.append(f"• {deposito}: {stock}")

    return resultado


def buscar_deposito(nombre_deposito):
    datos = obtener_datos()
    encabezados = [h.strip() for h in datos[2]]

    nombre_deposito = nombre_deposito.strip().lower()

    for fila in datos[3:]:
        deposito = fila[1].strip()

        if deposito.lower() == "total stocks":
            break

        if deposito.lower() == nombre_deposito:
            resultado = []

            for i in range(2, len(encabezados)):
                producto = encabezados[i].strip()
                stock = fila[i].strip()
                resultado.append(f"• {producto}: {stock}")

            return resultado

    return None


def buscar_producto_en_deposito(nombre_producto, nombre_deposito):
    datos = obtener_datos()
    encabezados = [h.strip().lower() for h in datos[2]]

    nombre_producto = nombre_producto.strip().lower()
    nombre_deposito = nombre_deposito.strip().lower()

    if nombre_producto not in encabezados:
        return None

    idx = encabezados.index(nombre_producto)

    for fila in datos[3:]:
        deposito = fila[1].strip()

        if deposito.lower() == "total stocks":
            break

        if deposito.lower() == nombre_deposito:
            return fila[idx].strip()

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "Hola 👋\n\n"
        "¿Qué querés consultar?\n\n"
        "• Stock general\n"
        "• Stock por depósito\n"
        "• Stock por producto\n\n"
        "Podés escribir directamente, por ejemplo:\n"
        "• harrier\n"
        "• crespo\n"
        "• harrier crespo"
    )
    await update.message.reply_text(mensaje)


async def texto_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().lower()

    if texto.startswith("/"):
        return

    productos = obtener_productos_lower()
    depositos = obtener_depositos_lower()

    if es_menu(texto):
        await update.message.reply_text(
            "Hola 👋\n\n"
            "¿Qué querés consultar?\n\n"
            "• Stock general\n"
            "• Stock por depósito\n"
            "• Stock por producto\n\n"
            "Podés escribir directamente, por ejemplo:\n"
            "• harrier\n"
            "• crespo\n"
            "• harrier crespo"
        )
        return

    palabras = texto.split()

    producto = None
    deposito = None

    for palabra in palabras:
        if palabra in productos:
            producto = palabra
        if palabra in depositos:
            deposito = palabra

    # Caso 1: producto + deposito
    if producto and deposito:
        stock = buscar_producto_en_deposito(producto, deposito)

        if stock is not None:
            mensaje = f"📦 {producto.upper()} en {deposito.upper()}:\n\n• {stock}"
            await update.message.reply_text(mensaje)
            return

    # Caso 2: solo producto
    if texto in productos:
        resultado = buscar_producto(texto)

        if resultado:
            mensaje = f"📦 Stock de {texto.upper()}:\n\n" + "\n".join(resultado)
            await update.message.reply_text(mensaje)
            return

    # Caso 3: solo deposito
    if texto in depositos:
        resultado = buscar_deposito(texto)

        if resultado:
            mensaje = f"🏬 Stock en {texto.upper()}:\n\n" + "\n".join(resultado)
            await update.message.reply_text(mensaje)
            return

    # Caso 4: sugerencias
    sugerencias_producto = sugerir_opciones(texto, productos)
    sugerencias_deposito = sugerir_opciones(texto, depositos)

    mensaje = "No encontré eso.\n\n"

    if sugerencias_producto:
        mensaje += "¿Quisiste decir este producto?\n"
        for s in sugerencias_producto:
            mensaje += f"• {s}\n"
        mensaje += "\n"

    if sugerencias_deposito:
        mensaje += "¿Quisiste decir este depósito?\n"
        for s in sugerencias_deposito:
            mensaje += f"• {s}\n"
        mensaje += "\n"

    if not sugerencias_producto and not sugerencias_deposito:
        mensaje += (
            "Probá con alguno de estos formatos:\n"
            "• harrier\n"
            "• crespo\n"
            "• harrier crespo"
        )

    await update.message.reply_text(mensaje)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_libre))

    app.run_polling()


if __name__ == "__main__":
    main()
