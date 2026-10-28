# CLN_AU4_Equipo2 · TechStore U4 — Núcleo de negocio de pedidos

Actividad 4 · Implementación del núcleo de negocio TechStore

Componentes de Lógica de Negocio · Unidad 4 · FIME · UANL

Profesor: Miguel Ángel Gómez Marroquín · Fecha: 28/10/2026

| Integrante | Matrícula |
|---|---|
| Ximena Montserrat Ovalle Vallejo | 1999238 |
| Santiago Almanza Moreno | 2001903 |
| Javier Hernández Huerta | 2089204 |

📄 **Reporte completo:** [docs/CLN_AU4_Equipo2_REPORTE.pdf](docs/CLN_AU4_Equipo2_REPORTE.pdf) · Bitácora: [docs/BITACORA_E01_E15.md](docs/BITACORA_E01_E15.md) · Resumen técnico: [docs/REPORTE.md](docs/REPORTE.md)

Programa para administrar pedidos de una tienda ficticia. Lee clientes, productos y
pedidos de archivos CSV, los convierte en objetos de dominio, aplica reglas de descuento
con el **Specification Pattern**, controla el ciclo de vida de cada pedido con una
**máquina de estados** que emite **Domain Events** y expone las operaciones mediante una
**API REST con FastAPI**. Todo trabaja en memoria: al cerrar el programa, los cambios se pierden.

| Resultado | Evidencia |
|---|---|
| `python cargar_csv.py` | 16 pedidos en DRAFT, O001 = 4 unidades / 2100.00 MXN |
| `python ejecutar_escenarios.py` | 15/15 escenarios E01–E15 cumplen su objetivo |
| `python -m pytest -q` | 69 pruebas, 0 fallos |
| `/docs` | Swagger con respuestas 200, 404, 409 y 422 |

## Estructura

```
CLN_AU4_Equipo2/
  datos/                    # CSV del paquete (sin modificar)
    clientes.csv  productos.csv  pedidos.csv  detalle_pedidos.csv  escenarios.csv
  cargar_csv.py             # cargador del paquete (sin modificar)
  README.txt                # reglas del paquete
  ejecutar_escenarios.py    # ejecuta E01–E15 y genera la bitácora
  app/
    __init__.py
    domain.py               # Money, Customer, OrderItem, Order, eventos, excepciones
    specifications.py       # Specifications AND/OR/NOT y DiscountPolicy
    services.py             # repositorio en memoria + OrderService (capa de aplicación)
    api.py                  # controladores FastAPI
  tests/
    conftest.py
    test_domain.py          # dominio, Specifications, estados y E01–E15
    test_api.py             # API REST (TestClient)
  docs/
    CLN_AU4_Equipo2_REPORTE.pdf  # reporte entregado (portada, desarrollo, evidencias, conclusiones)
    BITACORA_E01_E15.md     # bitácora resuelta
    REPORTE.md              # cálculo manual, diagrama de estados, eventos, reflexión, preguntas
    openapi.json            # contrato OpenAPI exportado
  evidencias/               # capturas (PNG) y salidas de terminal (TXT)
```

## Instalación

Requiere Python 3.11 o superior.

```bash
python --version
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD:        .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate
python -m pip install -r requirements.txt   # fastapi uvicorn pytest httpx
```

Si no puedes activar el entorno, usa su ejecutable directamente
(`.venv\Scripts\python.exe` en Windows, `.venv/bin/python` en macOS/Linux).

## Ejecución

```bash
python cargar_csv.py                                # punto de control: 16 pedidos DRAFT
python ejecutar_escenarios.py                       # E01–E15 en consola
python ejecutar_escenarios.py --md docs/BITACORA_E01_E15.md   # regenera la bitácora
python -m pytest -q                                 # pruebas
uvicorn app.api:app --reload                        # API
```

- Swagger: <http://127.0.0.1:8000/docs>
- Contrato OpenAPI: <http://127.0.0.1:8000/openapi.json>

## Reglas de negocio implementadas

| Regla | Dónde vive |
|---|---|
| `Money` usa `Decimal` (rechaza `float`), no admite negativos ni valores no finitos, es inmutable y `add()` rechaza monedas distintas | `Money.__post_init__`, `Money.add` |
| `OrderItem` exige SKU no vacío y cantidad entera > 0; el subtotal se calcula | `OrderItem` |
| Máximo **20 unidades** por pedido (suma de cantidades, no renglones); solo MXN; solo en DRAFT | `Order.add_item` |
| Confirmar: solo desde DRAFT, con artículos y cliente activo | `Order.confirm` |
| Enviar: solo desde CONFIRMED y con número de guía no vacío | `Order.ship` |
| Cancelar: solo desde CONFIRMED y con motivo no vacío | `Order.cancel` |
| Entregar / devolver: solo desde SHIPPED | `Order.deliver`, `Order.return_order` |
| Descuento **10 %**: VIP **AND** total **> 500** **AND** unidades **≥ 4** **AND NOT** promoción | `TEN_PERCENT` |
| Descuento **5 %**: total **> 5000** **AND NOT** promoción | `FIVE_PERCENT` |
| Si ambos aplican, gana el 10 %; elegibilidad general = `TEN_PERCENT \| FIVE_PERCENT` | `DiscountPolicy`, `ANY_DISCOUNT` |
| Una operación inválida no cambia el estado ni registra eventos | validar → cambiar estado → registrar evento |

El campo `existencia` de productos es solo información de catálogo: no se descuenta inventario.

## Máquina de estados

```
DRAFT --confirm--> CONFIRMED --ship--> SHIPPED --deliver--> DELIVERED
                       |                  |
                    cancel             return
                       |                  |
                   CANCELLED           RETURNED
```

Eventos: `OrderConfirmed`, `OrderShipped`, `OrderCancelled`, `OrderDelivered`, `OrderReturned`.
Detalle en [docs/REPORTE.md](docs/REPORTE.md).

## Endpoints

| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| GET | `/orders` | Lista los pedidos | 200 |
| GET | `/orders/{id}` | Detalle: estado, unidades, total, artículos y eventos | 200, 404 |
| GET | `/orders/{id}/discount` | Evalúa el descuento (no modifica el pedido) | 200, 404 |
| POST | `/orders` | Crea un pedido DRAFT `{"customer_id": "C002", "has_promotion": false}` | 201, 404 |
| POST | `/orders/{id}/items` | Agrega artículo `{"sku": "SKU003", "quantity": 2}` | 200, 404, 409, 422 |
| POST | `/orders/{id}/confirm` | Confirma | 200, 404, 409, 422 |
| POST | `/orders/{id}/ship` | Envía `{"tracking_number": "GUIA-MX-0001"}` | 200, 404, 409, 422 |
| POST | `/orders/{id}/cancel` | Cancela `{"reason": "..."}` | 200, 404, 409, 422 |
| POST | `/orders/{id}/deliver` | Entrega | 200, 404, 409 |
| POST | `/orders/{id}/return` | Devuelve | 200, 404, 409 |
| POST | `/reset` | Recarga los fixtures CSV (probar casos separados) | 200 |

Traducción de errores: `NotFound` → **404**, `InvalidOrderTransition` → **409**,
`InvalidOrderData` / `OrderItemLimitExceeded` → **422**. Los controladores no
contienen reglas: llaman a `OrderService`, que llama a `Order`.

Pruebas sugeridas en Swagger: confirmar `O999` (404), confirmar `O013` dos veces (200 y 409),
confirmar `O007` sin artículos (422).

## Evidencias

Capturas tomadas en el equipo de trabajo (Windows · PowerShell · Python 3.14), salvo donde se indica.

| Archivo | Contenido |
|---|---|
| [`00_entorno_y_dependencias.png`](evidencias/00_entorno_y_dependencias.png) | Creación del entorno virtual e instalación de dependencias |
| [`01_carga_16_pedidos.png`](evidencias/01_carga_16_pedidos.png) | `python cargar_csv.py`: carga exitosa de los 16 pedidos en DRAFT |
| [`03_escenarios_E01_E15.png`](evidencias/03_escenarios_E01_E15.png) | `python ejecutar_escenarios.py`: 15/15 escenarios |
| [`05_pytest.png`](evidencias/05_pytest.png) | `python -m pytest -q`: 69 passed |
| [`05_pytest_detalle.png`](evidencias/05_pytest_detalle.png) | `python -m pytest -v`: detalle de cada prueba |
| [`11_uvicorn_inicio_app.png`](evidencias/11_uvicorn_inicio_app.png) | Arranque del servidor con `uvicorn app.api:app --reload` |
| [`12_uvicorn_log_200_409_422_404.png`](evidencias/12_uvicorn_log_200_409_422_404.png) | Registro del servidor durante las pruebas en Swagger: O013 → 200, O013 → 409, O007 → 422, O999 → 404 |
| [`06_swagger_docs.png`](evidencias/06_swagger_docs.png) | Vista general de `/docs` (captura de referencia) |
| [`07_swagger_confirm_200_exito.png`](evidencias/07_swagger_confirm_200_exito.png) | Operación exitosa: confirmar O013 → 200 (captura de referencia) |
| [`08_swagger_confirm_409_rechazo.png`](evidencias/08_swagger_confirm_409_rechazo.png) | Operación rechazada: segundo confirm de O013 → 409 (captura de referencia) |
| [`09_swagger_confirm_422_sin_articulos.png`](evidencias/09_swagger_confirm_422_sin_articulos.png) | Operación rechazada: O007 sin artículos → 422 (captura de referencia) |
| [`10_swagger_confirm_404_inexistente.png`](evidencias/10_swagger_confirm_404_inexistente.png) | Operación rechazada: O999 inexistente → 404 (captura de referencia) |

Salidas de texto complementarias: `01_carga_16_pedidos.txt`, `02_verificacion_orientativa.txt`
(O001 10 %, O006 5 %, O005 y O010 sin descuento; ejercicio O013), `03_escenarios_E01_E15.txt`,
`04_api_curl.txt` (respuestas HTTP 200/404/409/422), `05_pytest.txt` y `05_pytest_detalle.txt`.
