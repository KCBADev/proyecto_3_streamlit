# Título: Persistencia en archivos CSV y JSON
# Autor: Kevin Bautista
# Fecha: 16/11/2026
# Descripción: Lee y escribe nodos.csv y el historial de consultas en JSON.
"""Lectura y escritura de los archivos del proyecto (CSV y JSON).

- ``nodos.csv`` guarda las conexiones del grafo: Origen, Destino, Peso.
- ``historial.json`` guarda las consultas de ruta más corta realizadas.

Las funciones de este módulo no imprimen ni piden datos: devuelven
resultados y advertencias para que ``main.py`` decida cómo mostrarlos.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from grafo import Grafo, ResultadoRuta

COLUMNA_ORIGEN = "Origen"
COLUMNA_DESTINO = "Destino"
COLUMNA_PESO = "Peso"
ENCABEZADOS = (COLUMNA_ORIGEN, COLUMNA_DESTINO, COLUMNA_PESO)
CODIFICACION = "utf-8"
# "utf-8-sig" lee UTF-8 con o sin la marca BOM que agrega Excel al guardar.
CODIFICACION_DE_LECTURA = "utf-8-sig"
SALTO_DE_LINEA = b"\n"


@dataclass
class ResultadoCarga:
    """Resultado de cargar el grafo desde el archivo CSV.

    Attributes:
        grafo: Grafo construido con las filas válidas.
        filas_validas: Número de conexiones cargadas.
        advertencias: Problemas encontrados (archivo o filas omitidas).
    """

    grafo: Grafo
    filas_validas: int = 0
    advertencias: list[str] = field(default_factory=list)


def convertir_peso(texto: str) -> float:
    """Convierte un texto en un peso válido para una arista.

    Raises:
        ValueError: Si el texto está vacío, no es un número, o el número
            no es finito y mayor que cero.
    """
    texto = texto.strip()
    if not texto:
        raise ValueError("el peso no puede quedar vacío")
    try:
        peso = float(texto)
    except ValueError:
        raise ValueError(f"'{texto}' no es un número") from None
    if not math.isfinite(peso):
        raise ValueError(f"'{texto}' no es un número finito")
    if peso <= 0:
        raise ValueError(
            f"el peso debe ser mayor que cero (se recibió {texto})"
        )
    return peso


def validar_nombre(texto: str) -> str:
    """Devuelve el nombre de nodo sin espacios sobrantes.

    Raises:
        ValueError: Si el nombre está vacío.
    """
    nombre = texto.strip()
    if not nombre:
        raise ValueError("el nombre del nodo no puede quedar vacío")
    return nombre


def guardar_conexion(
    ruta: Path, origen: str, destino: str, peso: float
) -> None:
    """Agrega una conexión al final del archivo CSV (modo append).

    Escribe primero los encabezados si el archivo no existe o está vacío.
    """
    necesita_encabezados = not ruta.exists() or ruta.stat().st_size == 0
    necesita_salto = not necesita_encabezados and not _termina_en_salto(ruta)
    peso_a_escribir = int(peso) if peso.is_integer() else peso

    with open(ruta, "a", newline="", encoding=CODIFICACION) as archivo:
        if necesita_salto:
            # Evita que la fila nueva se pegue a una última línea sin Enter.
            archivo.write("\n")
        escritor = csv.writer(archivo)
        if necesita_encabezados:
            escritor.writerow(ENCABEZADOS)
        escritor.writerow((origen, destino, peso_a_escribir))


def cargar_grafo(ruta: Path) -> ResultadoCarga:
    """Construye el grafo dirigido leyendo el CSV fila por fila.

    Nunca lanza excepciones por problemas del archivo: si no existe, no
    se puede leer o trae filas corruptas, omite lo dañado y lo reporta en
    ``advertencias``.
    """
    resultado = ResultadoCarga(grafo=Grafo(dirigido=True))
    try:
        with open(
            ruta, newline="", encoding=CODIFICACION_DE_LECTURA
        ) as archivo:
            _cargar_filas(csv.DictReader(archivo), resultado)
    except FileNotFoundError:
        resultado.advertencias.append(
            f"No se encontró '{ruta.name}'; se inicia con un grafo vacío."
        )
    except PermissionError:
        resultado.advertencias.append(
            f"No hay permiso para leer '{ruta.name}'; "
            "se inicia con un grafo vacío."
        )
    except UnicodeDecodeError:
        resultado.advertencias.append(
            f"'{ruta.name}' no está guardado en UTF-8; "
            "se cargaron solo las filas anteriores al error."
        )
    return resultado


def guardar_consulta_json(
    ruta: Path, origen: str, destino: str, resultado: ResultadoRuta
) -> None:
    """Agrega una consulta de ruta más corta al historial en JSON."""
    historial = cargar_historial_json(ruta)
    historial.append(
        {
            "origen": origen,
            "destino": destino,
            "existe_ruta": resultado.existe,
            # JSON no admite infinito: sin ruta, el peso se guarda como null.
            "peso_total": resultado.costo if resultado.existe else None,
            "ruta": list(resultado.nodos),
        }
    )
    with open(ruta, "w", encoding=CODIFICACION) as archivo:
        json.dump(historial, archivo, ensure_ascii=False, indent=2)


def cargar_historial_json(ruta: Path) -> list[dict[str, Any]]:
    """Lee el historial de consultas.

    Devuelve una lista vacía si el archivo no existe, está dañado o no
    contiene una lista de consultas.
    """
    try:
        with open(ruta, encoding=CODIFICACION) as archivo:
            contenido = json.load(archivo)
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(contenido, list):
        return []
    return [consulta for consulta in contenido if isinstance(consulta, dict)]


def _cargar_filas(lector: csv.DictReader, resultado: ResultadoCarga) -> None:
    """Agrega al grafo cada fila válida y anota las que se omiten."""
    for fila in lector:
        try:
            origen = validar_nombre(_leer_campo(fila, COLUMNA_ORIGEN))
            destino = validar_nombre(_leer_campo(fila, COLUMNA_DESTINO))
            peso = convertir_peso(_leer_campo(fila, COLUMNA_PESO))
        except KeyError as error:
            # Si falta un encabezado, ninguna fila se puede interpretar.
            resultado.advertencias.append(
                f"Falta el encabezado {error} en el archivo; se esperaba "
                f"'{','.join(ENCABEZADOS)}'. No se cargaron más filas."
            )
            return
        except ValueError as error:
            resultado.advertencias.append(
                f"Línea {lector.line_num} omitida: {error}."
            )
            continue
        resultado.grafo.agregar_arista(origen, destino, peso)
        resultado.filas_validas += 1


def _leer_campo(fila: dict[str, Any], columna: str) -> str:
    """Devuelve el valor de una columna de la fila.

    Raises:
        KeyError: Si la columna no existe en los encabezados del archivo.
        ValueError: Si la fila es más corta y no trae ese valor.
    """
    valor = fila[columna]
    if valor is None:
        raise ValueError(f"fila incompleta, falta el valor de '{columna}'")
    return valor


def _termina_en_salto(ruta: Path) -> bool:
    """Indica si el último byte de un archivo no vacío es un salto de línea."""
    with open(ruta, "rb") as archivo:
        archivo.seek(-1, 2)
        return archivo.read(1) == SALTO_DE_LINEA
