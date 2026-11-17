# Proyecto 3: Interfaz web con Streamlit

Aplicación web en Streamlit que funciona como capa visual sobre el grafo y el algoritmo de Dijkstra (Proyecto 1) y la persistencia en CSV (Proyecto 2).

El ejemplo es una red metabólica de Nutrición: cada nodo es un metabolito, cada conexión una conversión metabólica y el peso es el número de reacciones enzimáticas (valores aproximados, con fines didácticos). El grafo es dirigido: la fila `A,B,4` significa A → B.

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz visual en Streamlit |
| `visualizacion.py` | Escena animada de moléculas y rutas (componente Streamlit v2) |
| `main.py` | Programa de consola del Proyecto 2 |
| `grafo.py` | Clases `Nodo` y `Grafo`, y el algoritmo de Dijkstra |
| `io_handler.py` | Lectura y escritura de `nodos.csv` |
| `nodos.csv` | Conexiones de la red (`Origen,Destino,Peso`) |
| `requirements.txt` | Dependencias: `streamlit` (1.57 o superior), `pandas` y `flake8` |

## Cómo ejecutar

Requiere Python 3.10 o superior.

```
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app.py
```

La aplicación se abre en el navegador, en `http://localhost:8501`.

El programa de consola del Proyecto 2 sigue disponible con `py -3 main.py`.

## Qué hace la aplicación

- **Calcular ruta**: se eligen el sustrato inicial y el metabolito destino. La escena anima una representación conceptual de las moléculas y la ruta mínima; muestra el costo total, el recorrido y el detalle de cada tramo. El costo sigue siendo el número de reacciones enzimáticas, no una medida energética real.
- **Registrar conexión**: guarda una conexión nueva en `nodos.csv` y la agrega al grafo en memoria. Si la conexión ya existe con otro peso, lo actualiza.
- **Red actual**: tablas de conexiones y de nodos, construidas con pandas.
- **Barra lateral**: número de nodos y conexiones, y la hora en que se leyó el archivo.
- **Diseño**: tema oscuro, acentos inspirados en bioluminiscencia y partículas interactivas. Las esferas de la animación son simbólicas y no representan fórmulas químicas exactas.

Los nombres de nodos se reconocen sin distinguir mayúsculas ni acentos (`acido palmitico` = `Ácido palmítico`).

## Gestión de estado

`nodos.csv` se lee una sola vez por sesión. El grafo se guarda en `st.session_state` y las siguientes interacciones trabajan con ese objeto en memoria; el archivo solo se vuelve a abrir para agregar una conexión nueva.

## Tolerancia a fallos

Los errores se muestran con `st.error` o `st.warning`, sin detener la aplicación:

- **Peso inválido** (texto, negativo, cero o vacío) o **nombre vacío**: `ValueError`.
- **Nodo inexistente** al calcular una ruta: `NodoNoEncontradoError`, que es un `KeyError`.
- **`nodos.csv` inexistente**: `FileNotFoundError`; la aplicación inicia con la red vacía.
- **Filas corruptas o encabezados faltantes** en el CSV: `ValueError` y `KeyError`; se omiten y se avisa cuáles.
- **Archivo bloqueado** al guardar (por ejemplo, abierto en Excel): `PermissionError`.

## Validación con Flake8

```
py -3 -m flake8 .
```

No debe mostrar ningún mensaje.
