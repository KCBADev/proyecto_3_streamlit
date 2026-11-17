# Título: Programa de consola de la red metabólica
# Autor: Kevin Bautista
# Fecha: 16/11/2026
# Descripción: Menú interactivo para agregar conexiones y calcular rutas.
"""Programa interactivo: red metabólica persistente y ruta más corta.

Permite agregar conversiones metabólicas (origen, destino, número de
reacciones), las guarda en ``nodos.csv`` y calcula con Dijkstra la ruta con
menos reacciones entre dos metabolitos.

Uso:
    py -3 main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import io_handler
from grafo import Grafo, NodoNoEncontradoError, ResultadoRuta

CARPETA_DEL_PROYECTO = Path(__file__).resolve().parent
RUTA_CSV = CARPETA_DEL_PROYECTO / "nodos.csv"
RUTA_HISTORIAL = CARPETA_DEL_PROYECTO / "historial.json"

OPCION_AGREGAR = "1"
OPCION_RUTA = "2"
OPCION_NODOS = "3"
OPCION_HISTORIAL = "4"
OPCION_SALIR = "5"
MENU = f"""
--- Menú ---
{OPCION_AGREGAR}. Agregar conexión
{OPCION_RUTA}. Calcular ruta más corta
{OPCION_NODOS}. Ver nodos disponibles
{OPCION_HISTORIAL}. Ver historial de consultas
{OPCION_SALIR}. Salir"""
OPCIONES_VALIDAS = (
    OPCION_AGREGAR,
    OPCION_RUTA,
    OPCION_NODOS,
    OPCION_HISTORIAL,
    OPCION_SALIR,
)
SEPARADOR_DE_RUTA = " -> "


def pedir_nombre(mensaje: str, grafo: Grafo) -> str:
    """Pide un nombre de nodo hasta que no esté vacío.

    Si coincide con un nodo existente sin distinguir mayúsculas ni acentos,
    devuelve el nombre tal como está en el grafo.
    """
    while True:
        try:
            nombre = io_handler.validar_nombre(input(mensaje))
        except ValueError as error:
            print(f"  Entrada inválida: {error}. Intenta de nuevo.")
            continue
        return grafo.buscar_nodo(nombre) or nombre


def pedir_peso(mensaje: str) -> float:
    """Pide el peso de una arista hasta que sea un número mayor que cero."""
    while True:
        try:
            return io_handler.convertir_peso(input(mensaje))
        except ValueError as error:
            print(f"  Entrada inválida: {error}. Intenta de nuevo.")


def pedir_opcion() -> str:
    """Pide una opción del menú hasta que sea válida."""
    while True:
        opcion = input("Elige una opción: ").strip()
        if opcion in OPCIONES_VALIDAS:
            return opcion
        print(
            f"  Opción inválida: escribe un número del {OPCIONES_VALIDAS[0]} "
            f"al {OPCIONES_VALIDAS[-1]}."
        )


def agregar_conexion(grafo: Grafo, ruta_csv: Path) -> None:
    """Pide una conexión, la guarda en el CSV y la agrega al grafo."""
    origen = pedir_nombre("Nodo origen: ", grafo)
    destino = pedir_nombre("Nodo destino: ", grafo)
    if origen == destino:
        print("  No se guardó: el origen y el destino deben ser distintos.")
        return
    peso = pedir_peso("Peso (número de reacciones): ")

    try:
        io_handler.guardar_conexion(ruta_csv, origen, destino, peso)
    except PermissionError:
        print(
            f"  No se pudo escribir en '{ruta_csv.name}'. "
            "Si está abierto en Excel, ciérralo e intenta de nuevo."
        )
        return
    grafo.agregar_arista(origen, destino, peso)
    print(f"  Conexión guardada: {origen} -> {destino} (peso {peso:g}).")


def calcular_ruta(grafo: Grafo, ruta_historial: Path) -> None:
    """Pide inicio y destino, y muestra la ruta más corta entre ellos."""
    if not grafo.nombres_de_nodos:
        print("  El grafo está vacío: agrega primero una conexión.")
        return
    origen = pedir_nombre("Nodo de inicio: ", grafo)
    destino = pedir_nombre("Nodo de destino: ", grafo)

    try:
        resultado = grafo.ruta_mas_corta(origen, destino)
    except NodoNoEncontradoError as error:
        print(f"  {error}. Usa la opción {OPCION_NODOS} para ver los nodos.")
        return
    print(formatear_resultado(resultado))

    try:
        io_handler.guardar_consulta_json(
            ruta_historial, origen, destino, resultado
        )
    except PermissionError:
        print(f"  Aviso: no se pudo guardar en '{ruta_historial.name}'.")


def formatear_resultado(resultado: ResultadoRuta) -> str:
    """Devuelve el texto con la ruta más corta y su peso total."""
    if not resultado.existe:
        return "  No existe una ruta entre esos nodos."
    return (
        f"  Ruta más corta: {SEPARADOR_DE_RUTA.join(resultado.nodos)}\n"
        f"  Peso total: {resultado.costo:g} reacciones"
    )


def mostrar_nodos(grafo: Grafo) -> None:
    """Imprime los nombres de los nodos cargados, en orden alfabético."""
    nombres = sorted(grafo.nombres_de_nodos, key=str.casefold)
    if not nombres:
        print("  El grafo está vacío.")
        return
    print(f"  {len(nombres)} nodos: {', '.join(nombres)}")


def mostrar_historial(ruta_historial: Path) -> None:
    """Imprime las consultas guardadas en el historial JSON."""
    historial = io_handler.cargar_historial_json(ruta_historial)
    if not historial:
        print("  Aún no hay consultas guardadas.")
        return
    for numero, consulta in enumerate(historial, start=1):
        origen = consulta.get("origen", "?")
        destino = consulta.get("destino", "?")
        peso = consulta.get("peso_total")
        if isinstance(peso, (int, float)):
            detalle = f"peso {peso:g}"
        else:
            detalle = "sin ruta"
        print(f"  {numero}. {origen} -> {destino}: {detalle}")


def mostrar_resumen_de_carga(carga: io_handler.ResultadoCarga) -> None:
    """Imprime cuántas conexiones se cargaron y las filas omitidas."""
    print(f"Conexiones cargadas desde el archivo: {carga.filas_validas}")
    for advertencia in carga.advertencias:
        print(f"  Aviso: {advertencia}")


def ejecutar_menu(grafo: Grafo, ruta_csv: Path, ruta_historial: Path) -> None:
    """Atiende las opciones del menú hasta que el usuario elige salir."""
    while True:
        print(MENU)
        opcion = pedir_opcion()
        if opcion == OPCION_AGREGAR:
            agregar_conexion(grafo, ruta_csv)
        elif opcion == OPCION_RUTA:
            calcular_ruta(grafo, ruta_historial)
        elif opcion == OPCION_NODOS:
            mostrar_nodos(grafo)
        elif opcion == OPCION_HISTORIAL:
            mostrar_historial(ruta_historial)
        else:
            return


def main(
    ruta_csv: Path = RUTA_CSV, ruta_historial: Path = RUTA_HISTORIAL
) -> int:
    """Punto de entrada del programa; devuelve el código de salida."""
    # La consola de Windows no siempre usa UTF-8 y deformaría los acentos.
    sys.stdout.reconfigure(encoding="utf-8")

    print("=== Red metabólica: ruta más corta (Dijkstra) ===")
    carga = io_handler.cargar_grafo(ruta_csv)
    mostrar_resumen_de_carga(carga)
    try:
        ejecutar_menu(carga.grafo, ruta_csv, ruta_historial)
    except (EOFError, KeyboardInterrupt):
        # Ctrl+C, Ctrl+Z o fin de la entrada: se sale sin mostrar un error.
        print()
    print("Hasta luego.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
