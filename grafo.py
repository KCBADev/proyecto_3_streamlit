# Título: Grafo ponderado y algoritmo de Dijkstra
# Autor: Kevin Bautista
# Fecha: 16/11/2026
# Descripción: Clases Nodo y Grafo, y cálculo de la ruta de menor costo.
"""Grafo ponderado y algoritmo de Dijkstra, implementados con POO.

Este módulo es genérico: no sabe nada del dominio (nutrición, transporte,
redes...) ni de archivos. Solo modela nodos, aristas con peso y la búsqueda
de la ruta de menor costo entre dos nodos.
"""

from __future__ import annotations

import heapq
import math
import unicodedata
from dataclasses import dataclass


def _normalizar(texto: str) -> str:
    """Devuelve el texto en minúsculas y sin acentos, para compararlo."""
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(
        letra for letra in descompuesto if not unicodedata.combining(letra)
    )


class NodoNoEncontradoError(KeyError):
    """Se consultó un nodo que no existe en el grafo."""

    def __init__(self, nombre: str) -> None:
        """Guarda el nombre del nodo que no se encontró."""
        super().__init__(nombre)
        self.nombre = nombre

    def __str__(self) -> str:
        """Devuelve un mensaje legible para mostrar al usuario."""
        return f"El nodo '{self.nombre}' no existe en el grafo"


class PesoNegativoError(ValueError):
    """Se intentó crear una arista con peso negativo."""


@dataclass(frozen=True)
class ResultadoRuta:
    """Resultado de una búsqueda de ruta más corta.

    Attributes:
        costo: Suma de los pesos del recorrido; infinito si no hay ruta.
        nodos: Nombres de los nodos del recorrido, de origen a destino;
            vacío si no hay ruta.
    """

    costo: float
    nodos: tuple[str, ...]

    @property
    def existe(self) -> bool:
        """Indica si se encontró una ruta entre origen y destino."""
        return bool(self.nodos)


class Nodo:
    """Nodo del grafo, con sus aristas salientes."""

    def __init__(self, nombre: str) -> None:
        """Crea un nodo sin conexiones."""
        self.nombre = nombre
        self._vecinos: dict[Nodo, float] = {}

    @property
    def vecinos(self) -> dict[Nodo, float]:
        """Copia de las aristas salientes: nodo vecino -> peso."""
        return dict(self._vecinos)

    def conectar(self, vecino: Nodo, peso: float) -> None:
        """Crea (o actualiza) la arista saliente hacia ``vecino``."""
        self._vecinos[vecino] = peso

    def __repr__(self) -> str:
        """Devuelve una representación útil para depurar."""
        return f"Nodo({self.nombre!r})"


class Grafo:
    """Grafo ponderado, dirigido o no dirigido."""

    def __init__(self, dirigido: bool = False) -> None:
        """Crea un grafo vacío."""
        self.dirigido = dirigido
        self._nodos: dict[str, Nodo] = {}

    @property
    def nombres_de_nodos(self) -> list[str]:
        """Nombres de todos los nodos, en orden de inserción."""
        return list(self._nodos)

    @property
    def aristas(self) -> list[tuple[str, str, float]]:
        """Conexiones del grafo como tuplas (origen, destino, peso).

        En un grafo no dirigido cada conexión aparece en ambos sentidos.
        """
        return [
            (nodo.nombre, vecino.nombre, peso)
            for nodo in self._nodos.values()
            for vecino, peso in nodo.vecinos.items()
        ]

    def buscar_nodo(self, nombre: str) -> str | None:
        """Devuelve el nombre registrado del nodo que coincide con ``nombre``.

        Prefiere la coincidencia exacta; si no la hay, compara sin
        distinguir mayúsculas ni acentos. Devuelve None si no existe.
        """
        if nombre in self._nodos:
            return nombre
        buscado = _normalizar(nombre)
        for existente in self._nodos:
            if _normalizar(existente) == buscado:
                return existente
        return None

    def agregar_nodo(self, nombre: str) -> Nodo:
        """Devuelve el nodo con ese nombre, creándolo si no existía."""
        if nombre not in self._nodos:
            self._nodos[nombre] = Nodo(nombre)
        return self._nodos[nombre]

    def agregar_arista(self, origen: str, destino: str, peso: float) -> None:
        """Conecta dos nodos, creándolos si hace falta.

        En un grafo no dirigido la arista se registra en ambos sentidos.

        Raises:
            PesoNegativoError: Si ``peso`` es negativo.
        """
        if peso < 0:
            raise PesoNegativoError(
                f"Peso inválido ({peso}) en {origen} -> {destino}: "
                "Dijkstra no admite pesos negativos"
            )
        nodo_origen = self.agregar_nodo(origen)
        nodo_destino = self.agregar_nodo(destino)
        nodo_origen.conectar(nodo_destino, peso)
        if not self.dirigido:
            nodo_destino.conectar(nodo_origen, peso)

    def ruta_mas_corta(self, origen: str, destino: str) -> ResultadoRuta:
        """Calcula la ruta de menor costo con el algoritmo de Dijkstra.

        Usa una cola de prioridad (montículo binario), por lo que su
        complejidad es O((V + E) log V).

        Raises:
            NodoNoEncontradoError: Si ``origen`` o ``destino`` no existen.
        """
        inicio = self._obtener_nodo(origen)
        fin = self._obtener_nodo(destino)

        distancias: dict[Nodo, float] = {inicio: 0}
        anteriores: dict[Nodo, Nodo] = {}
        visitados: set[Nodo] = set()
        # El contador desempata entradas con el mismo costo, porque los
        # objetos Nodo no son comparables entre sí.
        contador = 0
        cola: list[tuple[float, int, Nodo]] = [(0, contador, inicio)]

        while cola:
            costo, _, actual = heapq.heappop(cola)
            if actual in visitados:
                continue  # Entrada obsoleta: ya se procesó con menor costo.
            visitados.add(actual)
            if actual is fin:
                break  # El primer costo definitivo del destino es el mínimo.

            for vecino, peso in actual.vecinos.items():
                nuevo_costo = costo + peso
                if nuevo_costo < distancias.get(vecino, math.inf):
                    distancias[vecino] = nuevo_costo
                    anteriores[vecino] = actual
                    contador += 1
                    heapq.heappush(cola, (nuevo_costo, contador, vecino))

        if fin not in distancias:
            return ResultadoRuta(costo=math.inf, nodos=())
        return ResultadoRuta(
            costo=distancias[fin],
            nodos=self._reconstruir_ruta(anteriores, inicio, fin),
        )

    def _obtener_nodo(self, nombre: str) -> Nodo:
        """Devuelve el nodo con ese nombre o lanza NodoNoEncontradoError."""
        try:
            return self._nodos[nombre]
        except KeyError:
            raise NodoNoEncontradoError(nombre) from None

    @staticmethod
    def _reconstruir_ruta(
        anteriores: dict[Nodo, Nodo], inicio: Nodo, fin: Nodo
    ) -> tuple[str, ...]:
        """Recorre los predecesores desde el destino hasta el origen."""
        ruta = [fin]
        while ruta[-1] is not inicio:
            ruta.append(anteriores[ruta[-1]])
        return tuple(nodo.nombre for nodo in reversed(ruta))
