# Título: Interfaz web de la red metabólica
# Autor: Kevin Bautista
# Fecha: 16/11/2026
# Descripción: Vista en Streamlit para registrar conexiones y calcular rutas.
"""Interfaz gráfica (frontend) del proyecto, hecha con Streamlit.

Este archivo solo contiene la vista. El algoritmo de Dijkstra vive en
``grafo.py`` y la lectura y escritura de archivos en ``io_handler.py``.

Uso:
    py -3 -m streamlit run app.py
"""

from __future__ import annotations

import difflib
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import io_handler
from grafo import Grafo, NodoNoEncontradoError, ResultadoRuta

RUTA_CSV = Path(__file__).resolve().parent / "nodos.csv"

# Claves de st.session_state.
CLAVE_GRAFO = "grafo"
CLAVE_ADVERTENCIAS = "advertencias_de_carga"
CLAVE_HORA_DE_CARGA = "hora_de_carga"
CLAVE_AVISO = "aviso_de_registro"
CLAVE_NUEVO_ORIGEN = "nuevo_origen"
CLAVE_NUEVO_DESTINO = "nuevo_destino"
CLAVE_NUEVO_PESO = "nuevo_peso"
CAMPOS_DE_REGISTRO = (
    CLAVE_NUEVO_ORIGEN,
    CLAVE_NUEVO_DESTINO,
    CLAVE_NUEVO_PESO,
)

ETIQUETA_ORIGEN = "Nodo origen"
ETIQUETA_DESTINO = "Nodo destino"
COLUMNAS_DE_CONEXIONES = list(io_handler.ENCABEZADOS)
SEPARADOR_DE_RUTA = " → "
MAXIMO_DE_SUGERENCIAS = 3
CARACTERES_DE_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$:])")

AVISO_ERROR = "error"
AVISO_ADVERTENCIA = "advertencia"
AVISO_EXITO = "exito"


def inicializar_estado() -> None:
    """Carga el grafo desde ``nodos.csv`` una sola vez por sesión.

    Streamlit vuelve a ejecutar todo el script en cada interacción. El
    grafo se guarda en ``st.session_state`` para que el archivo solo se
    lea la primera vez y después se trabaje con el objeto en memoria.
    """
    if CLAVE_GRAFO not in st.session_state:
        carga = io_handler.cargar_grafo(RUTA_CSV)
        st.session_state[CLAVE_GRAFO] = carga.grafo
        st.session_state[CLAVE_ADVERTENCIAS] = carga.advertencias
        st.session_state[CLAVE_HORA_DE_CARGA] = datetime.now().strftime(
            "%H:%M:%S"
        )


def escapar_markdown(texto: str) -> str:
    """Escapa los símbolos de Markdown para mostrar el texto tal cual."""
    return CARACTERES_DE_MARKDOWN.sub(r"\\\1", texto)


def leer_nombre(texto: str, etiqueta: str) -> str:
    """Devuelve el nombre de nodo escrito en un campo de texto.

    Raises:
        ValueError: Si el campo quedó vacío.
    """
    try:
        return io_handler.validar_nombre(texto)
    except ValueError:
        raise ValueError(
            f"el campo «{etiqueta}» no puede quedar vacío"
        ) from None


def guardar_aviso(tipo: str, texto: str) -> None:
    """Deja un mensaje para mostrarlo en la siguiente ejecución."""
    st.session_state[CLAVE_AVISO] = (tipo, texto)


def registrar_conexion() -> None:
    """Valida el formulario, guarda la conexión y actualiza el grafo.

    Se ejecuta como callback del botón, antes de redibujar la página, para
    que las tablas y los totales ya muestren la conexión nueva.
    """
    grafo: Grafo = st.session_state[CLAVE_GRAFO]
    try:
        origen = leer_nombre(
            st.session_state[CLAVE_NUEVO_ORIGEN], ETIQUETA_ORIGEN
        )
        destino = leer_nombre(
            st.session_state[CLAVE_NUEVO_DESTINO], ETIQUETA_DESTINO
        )
        peso = io_handler.convertir_peso(st.session_state[CLAVE_NUEVO_PESO])
    except ValueError as error:
        guardar_aviso(
            AVISO_ERROR,
            f"No se registró la conexión: {escapar_markdown(str(error))}.",
        )
        return

    # Reutiliza el nombre ya registrado para no duplicar nodos por una
    # diferencia de mayúsculas o acentos.
    origen = grafo.buscar_nodo(origen) or origen
    destino = grafo.buscar_nodo(destino) or destino
    conexion = (
        f"{escapar_markdown(origen)}{SEPARADOR_DE_RUTA}"
        f"{escapar_markdown(destino)}"
    )
    if origen == destino:
        guardar_aviso(
            AVISO_ERROR,
            "No se registró la conexión: el origen y el destino deben ser "
            "distintos.",
        )
        return

    pesos = {(desde, hacia): valor for desde, hacia, valor in grafo.aristas}
    peso_anterior = pesos.get((origen, destino))
    if peso_anterior == peso:
        guardar_aviso(
            AVISO_ADVERTENCIA,
            f"La conexión {conexion} ya existe con peso {peso:g}; no se "
            "guardó de nuevo.",
        )
        return

    try:
        io_handler.guardar_conexion(RUTA_CSV, origen, destino, peso)
    except PermissionError:
        guardar_aviso(
            AVISO_ERROR,
            f"No se pudo escribir en {RUTA_CSV.name}. Si está abierto en "
            "Excel, ciérralo e intenta de nuevo.",
        )
        return
    except OSError as error:
        guardar_aviso(
            AVISO_ERROR,
            f"No se pudo guardar en {RUTA_CSV.name}: {error.strerror}.",
        )
        return

    # Solo se actualiza la memoria si el archivo se escribió bien.
    grafo.agregar_arista(origen, destino, peso)
    if peso_anterior is None:
        mensaje = f"Conexión guardada: {conexion} (peso {peso:g})."
    else:
        mensaje = (
            f"Peso actualizado: {conexion} pasó de {peso_anterior:g} a "
            f"{peso:g}."
        )
    guardar_aviso(AVISO_EXITO, mensaje)
    for campo in CAMPOS_DE_REGISTRO:
        st.session_state[campo] = ""


def mostrar_aviso_de_registro() -> None:
    """Muestra una sola vez el resultado del último registro."""
    aviso = st.session_state.pop(CLAVE_AVISO, None)
    if aviso is None:
        return
    tipo, texto = aviso
    if tipo == AVISO_ERROR:
        st.error(texto, icon=":material/error:")
    elif tipo == AVISO_ADVERTENCIA:
        st.warning(texto, icon=":material/warning:")
    else:
        st.success(texto, icon=":material/check_circle:")


def mostrar_advertencias_de_carga() -> None:
    """Muestra los problemas encontrados al leer el CSV al inicio."""
    advertencias = st.session_state[CLAVE_ADVERTENCIAS]
    if not advertencias:
        return
    lineas = "\n".join(
        f"- {escapar_markdown(advertencia)}" for advertencia in advertencias
    )
    st.warning(
        f"Al cargar {RUTA_CSV.name} al inicio de la sesión:\n\n{lineas}",
        icon=":material/warning:",
    )


def mostrar_barra_lateral(grafo: Grafo) -> None:
    """Muestra en la barra lateral el estado de la red en memoria."""
    with st.sidebar:
        st.header("Estado de la red")
        st.metric("Nodos", len(grafo.nombres_de_nodos))
        st.metric("Conexiones", len(grafo.aristas))
        st.caption(
            f"{RUTA_CSV.name} se leyó una sola vez, a las "
            f"{st.session_state[CLAVE_HORA_DE_CARGA]}. Desde entonces la "
            "red se consulta en memoria."
        )


def mensaje_de_nodo_inexistente(grafo: Grafo, nombre: str) -> str:
    """Devuelve el aviso de nodo inexistente, con nombres parecidos."""
    mensaje = f"El nodo «{escapar_markdown(nombre)}» no existe en la red."
    parecidos = difflib.get_close_matches(
        nombre, grafo.nombres_de_nodos, n=MAXIMO_DE_SUGERENCIAS
    )
    if parecidos:
        sugerencias = ", ".join(escapar_markdown(p) for p in parecidos)
        mensaje += f" ¿Quisiste decir: {sugerencias}?"
    return mensaje


def construir_tabla_de_tramos(
    grafo: Grafo, nodos: tuple[str, ...]
) -> pd.DataFrame:
    """Devuelve cada tramo del recorrido con su peso y el acumulado."""
    pesos = {(desde, hacia): valor for desde, hacia, valor in grafo.aristas}
    tramos = pd.DataFrame(
        {
            "Paso": range(1, len(nodos)),
            "Desde": nodos[:-1],
            "Hacia": nodos[1:],
            "Peso": [pesos[tramo] for tramo in zip(nodos, nodos[1:])],
        }
    )
    tramos["Acumulado"] = tramos["Peso"].cumsum()
    return tramos


def mostrar_resultado(
    grafo: Grafo, origen: str, destino: str, resultado: ResultadoRuta
) -> None:
    """Muestra el costo total y el recorrido, o avisa que no hay ruta."""
    if not resultado.existe:
        st.warning(
            f"No existe una ruta posible de **{escapar_markdown(origen)}** "
            f"a **{escapar_markdown(destino)}**. Las conexiones tienen un "
            "solo sentido, así que no siempre hay camino de regreso.",
            icon=":material/block:",
        )
        return
    if origen == destino:
        st.info("El origen y el destino son el mismo nodo: el costo es 0.")
        return

    columna_costo, columna_tramos = st.columns(2)
    columna_costo.metric(
        "Costo total mínimo", f"{resultado.costo:g} reacciones"
    )
    columna_tramos.metric("Conversiones", len(resultado.nodos) - 1)
    recorrido = SEPARADOR_DE_RUTA.join(
        escapar_markdown(nodo) for nodo in resultado.nodos
    )
    with st.container(border=True):
        st.markdown(f"**Recorrido:** {recorrido}")
    with st.expander("Detalle del recorrido"):
        st.dataframe(
            construir_tabla_de_tramos(grafo, resultado.nodos),
            hide_index=True,
        )


def calcular_ruta(grafo: Grafo, texto_origen: str, texto_destino: str) -> None:
    """Valida los nodos escritos y muestra la ruta más corta entre ellos."""
    try:
        origen = leer_nombre(texto_origen, ETIQUETA_ORIGEN)
        destino = leer_nombre(texto_destino, ETIQUETA_DESTINO)
        origen = grafo.buscar_nodo(origen) or origen
        destino = grafo.buscar_nodo(destino) or destino
        resultado = grafo.ruta_mas_corta(origen, destino)
    except ValueError as error:
        st.error(
            f"Entrada inválida: {escapar_markdown(str(error))}.",
            icon=":material/error:",
        )
        return
    except NodoNoEncontradoError as error:
        # NodoNoEncontradoError es un KeyError: el nodo no está en el grafo.
        st.error(
            mensaje_de_nodo_inexistente(grafo, error.nombre),
            icon=":material/error:",
        )
        return
    mostrar_resultado(grafo, origen, destino, resultado)


def mostrar_calculadora(grafo: Grafo) -> None:
    """Pestaña para calcular la ruta más corta entre dos nodos."""
    if not grafo.nombres_de_nodos:
        st.info("La red está vacía: registra primero una conexión.")
        return

    with st.form("formulario_de_ruta"):
        columna_origen, columna_destino = st.columns(2)
        texto_origen = columna_origen.text_input(
            ETIQUETA_ORIGEN, placeholder="Ej. Glucosa"
        )
        texto_destino = columna_destino.text_input(
            ETIQUETA_DESTINO, placeholder="Ej. Colesterol"
        )
        enviado = st.form_submit_button(
            "Calcular ruta", type="primary", icon=":material/route:"
        )
    if enviado:
        calcular_ruta(grafo, texto_origen, texto_destino)

    with st.expander("Nodos disponibles"):
        nombres = sorted(grafo.nombres_de_nodos, key=str.casefold)
        st.markdown(" · ".join(escapar_markdown(n) for n in nombres))


def mostrar_registro() -> None:
    """Pestaña para registrar una conexión nueva en el CSV y en el grafo."""
    st.markdown(
        "Cada conexión va del origen al destino y se guarda en "
        f"`{RUTA_CSV.name}`. Si el nodo no existe, se crea."
    )
    with st.form("formulario_de_registro"):
        columna_origen, columna_destino, columna_peso = st.columns([2, 2, 1])
        columna_origen.text_input(ETIQUETA_ORIGEN, key=CLAVE_NUEVO_ORIGEN)
        columna_destino.text_input(ETIQUETA_DESTINO, key=CLAVE_NUEVO_DESTINO)
        columna_peso.text_input(
            "Peso",
            key=CLAVE_NUEVO_PESO,
            help="Número de reacciones; debe ser mayor que cero.",
        )
        st.form_submit_button(
            "Guardar conexión",
            type="primary",
            icon=":material/add_link:",
            on_click=registrar_conexion,
        )
    mostrar_aviso_de_registro()


def construir_tabla_de_conexiones(grafo: Grafo) -> pd.DataFrame:
    """Devuelve las conexiones del grafo en memoria como DataFrame."""
    return pd.DataFrame(grafo.aristas, columns=COLUMNAS_DE_CONEXIONES)


def construir_tabla_de_nodos(
    grafo: Grafo, conexiones: pd.DataFrame
) -> pd.DataFrame:
    """Devuelve el catálogo de nodos con su número de conexiones."""
    nombres = sorted(grafo.nombres_de_nodos, key=str.casefold)
    nodos = pd.DataFrame({"Nodo": nombres})
    salidas = conexiones[io_handler.COLUMNA_ORIGEN].value_counts()
    entradas = conexiones[io_handler.COLUMNA_DESTINO].value_counts()
    nodos["Conexiones de salida"] = (
        nodos["Nodo"].map(salidas).fillna(0).astype(int)
    )
    nodos["Conexiones de entrada"] = (
        nodos["Nodo"].map(entradas).fillna(0).astype(int)
    )
    return nodos


def filtrar_conexiones(conexiones: pd.DataFrame, texto: str) -> pd.DataFrame:
    """Devuelve las conexiones cuyo origen o destino contiene el texto."""
    texto = texto.strip()
    if not texto:
        return conexiones
    en_origen = conexiones[io_handler.COLUMNA_ORIGEN].str.contains(
        texto, case=False, regex=False
    )
    en_destino = conexiones[io_handler.COLUMNA_DESTINO].str.contains(
        texto, case=False, regex=False
    )
    return conexiones[en_origen | en_destino]


def mostrar_red(grafo: Grafo) -> None:
    """Pestaña con las tablas de conexiones y de nodos de la red."""
    conexiones = construir_tabla_de_conexiones(grafo)
    if conexiones.empty:
        st.info("La red está vacía: aún no hay conexiones que mostrar.")
        return

    st.subheader("Conexiones")
    filtro = st.text_input("Filtrar por nodo", placeholder="Ej. Piruvato")
    visibles = filtrar_conexiones(conexiones, filtro)
    st.dataframe(visibles, hide_index=True)
    st.caption(f"{len(visibles)} de {len(conexiones)} conexiones.")

    st.subheader("Nodos")
    st.dataframe(construir_tabla_de_nodos(grafo, conexiones), hide_index=True)


def main() -> None:
    """Dibuja la página completa."""
    st.set_page_config(
        page_title="Red metabólica", page_icon=":material/hub:"
    )
    inicializar_estado()
    grafo: Grafo = st.session_state[CLAVE_GRAFO]

    st.title("Red metabólica: ruta más corta")
    st.caption(
        "Encuentra con el algoritmo de Dijkstra la vía con menos reacciones "
        "enzimáticas para convertir un metabolito en otro."
    )
    mostrar_advertencias_de_carga()
    mostrar_barra_lateral(grafo)

    pestana_ruta, pestana_registro, pestana_red = st.tabs(
        [
            ":material/route: Calcular ruta",
            ":material/add_link: Registrar conexión",
            ":material/table: Red actual",
        ]
    )
    with pestana_ruta:
        mostrar_calculadora(grafo)
    with pestana_registro:
        mostrar_registro()
    with pestana_red:
        mostrar_red(grafo)


if __name__ == "__main__":
    main()
