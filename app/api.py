"""API REST TechStore (FastAPI).

El Controller: recibe la petición -> llama a OrderService -> devuelve un DTO.
No contiene reglas de negocio. Las excepciones del dominio se traducen a HTTP:
    NotFound                     -> 404 Not Found
    InvalidOrderTransition       -> 409 Conflict
    InvalidOrderData             -> 422 Unprocessable Content
    OrderItemLimitExceeded       -> 422 Unprocessable Content

Ejecutar:  uvicorn app.api:app --reload   ->   http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.domain import (DomainException, InvalidOrderData,
                        InvalidOrderTransition, Order, OrderItemLimitExceeded)
from app.services import InMemoryOrderRepository, NotFound, OrderService

app = FastAPI(
    title="TechStore U4",
    version="1.0.0",
    description=(
        "Administración de pedidos TechStore. Las reglas viven en el dominio "
        "(Order, Money, Specifications); la API solo las expone. "
        "Repositorio en memoria: reinicie el servidor o use POST /reset para "
        "volver a cargar los fixtures CSV."
    ),
)
repository = InMemoryOrderRepository()   # carga los fixtures al iniciar
service = OrderService(repository)
orders = repository._orders              # diccionario en memoria (sección 11)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    detail: str


class ItemDTO(BaseModel):
    sku: str
    quantity: int
    unit_price: str
    subtotal: str


class EventDTO(BaseModel):
    name: str
    order_id: str
    occurred_at: str
    details: dict


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    customer_vip: bool
    customer_active: bool
    has_promotion: bool
    status: str
    units: int
    total: str
    currency: str = "MXN"
    tracking_number: str | None = None
    cancel_reason: str | None = None
    items: list[ItemDTO]
    events: list[EventDTO]


class StatusResponse(BaseModel):
    id: str
    status: str
    events: list[str]


class DiscountResponse(BaseModel):
    id: str
    rule: str
    percent: str
    subtotal: str
    discount: str
    total: str


class CreateOrderRequest(BaseModel):
    customer_id: str = Field(examples=["C001"])
    has_promotion: bool = False


class AddItemRequest(BaseModel):
    sku: str = Field(examples=["SKU003"])
    quantity: int = Field(examples=[2])


class ShipRequest(BaseModel):
    # Sin validación aquí: la regla "guía obligatoria" la decide Order.ship().
    tracking_number: str = Field(default="", examples=["GUIA-MX-0001"])


class CancelRequest(BaseModel):
    reason: str = Field(default="", examples=["Cliente solicitó la cancelación"])


def to_dto(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id, customer_id=order.customer.id,
        customer_vip=order.customer.is_vip, customer_active=order.customer.active,
        has_promotion=order.has_promotion, status=order.status.value,
        units=order.units, total=str(order.total.amount),
        tracking_number=order.tracking_number, cancel_reason=order.cancel_reason,
        items=[ItemDTO(sku=i.sku, quantity=i.quantity,
                       unit_price=str(i.unit_price.amount),
                       subtotal=str(i.subtotal.amount)) for i in order.items],
        events=[EventDTO(name=e.name, order_id=e.order_id,
                         occurred_at=e.occurred_at.isoformat(),
                         details=e.details) for e in order.events],
    )


def to_status(order: Order) -> StatusResponse:
    return StatusResponse(id=order.id, status=order.status.value,
                          events=[e.name for e in order.events])


def execute(operation):
    """Traduce excepciones de aplicación/dominio a códigos HTTP semánticos."""
    try:
        return operation()
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except DomainException as exc:
        raise HTTPException(status_code=422, detail=str(exc))


R404 = {404: {"model": ErrorResponse, "description": "Pedido o recurso inexistente"}}
R409 = {409: {"model": ErrorResponse, "description": "Transición de estado no permitida"}}
R422 = {422: {"description": "Datos inválidos según las reglas del dominio"}}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/orders", response_model=list[OrderResponse], tags=["Consultas"])
def list_orders():
    return [to_dto(o) for o in service.list()]


@app.get("/orders/{order_id}", response_model=OrderResponse,
         responses=R404, tags=["Consultas"])
def get_order(order_id: str):
    return execute(lambda: to_dto(service.get(order_id)))


@app.get("/orders/{order_id}/discount", response_model=DiscountResponse,
         responses=R404, tags=["Consultas"])
def get_discount(order_id: str):
    def op():
        r = service.discount(order_id)
        return DiscountResponse(id=order_id, rule=r.rule, percent=r.percent,
                                subtotal=str(r.subtotal.amount),
                                discount=str(r.discount.amount),
                                total=str(r.total.amount))
    return execute(op)


@app.post("/orders", response_model=OrderResponse, status_code=201,
          responses={**R404, **R422}, tags=["Pedidos"])
def create_order(body: CreateOrderRequest):
    return execute(lambda: to_dto(service.create(body.customer_id, body.has_promotion)))


@app.post("/orders/{order_id}/items", response_model=OrderResponse,
          responses={**R404, **R409, **R422}, tags=["Pedidos"])
def add_item(order_id: str, body: AddItemRequest):
    return execute(lambda: to_dto(service.add_item(order_id, body.sku, body.quantity)))


@app.post("/orders/{order_id}/confirm", response_model=StatusResponse,
          responses={**R404, **R409, **R422}, tags=["Transiciones"])
def confirm_order(order_id: str):
    return execute(lambda: to_status(service.confirm(order_id)))


@app.post("/orders/{order_id}/ship", response_model=StatusResponse,
          responses={**R404, **R409, **R422}, tags=["Transiciones"])
def ship_order(order_id: str, body: ShipRequest | None = None):
    tracking = body.tracking_number if body else ""
    return execute(lambda: to_status(service.ship(order_id, tracking)))


@app.post("/orders/{order_id}/cancel", response_model=StatusResponse,
          responses={**R404, **R409, **R422}, tags=["Transiciones"])
def cancel_order(order_id: str, body: CancelRequest | None = None):
    reason = body.reason if body else ""
    return execute(lambda: to_status(service.cancel(order_id, reason)))


@app.post("/orders/{order_id}/deliver", response_model=StatusResponse,
          responses={**R404, **R409}, tags=["Transiciones"])
def deliver_order(order_id: str):
    return execute(lambda: to_status(service.deliver(order_id)))


@app.post("/orders/{order_id}/return", response_model=StatusResponse,
          responses={**R404, **R409}, tags=["Transiciones"])
def return_order(order_id: str):
    return execute(lambda: to_status(service.return_order(order_id)))


@app.post("/reset", tags=["Laboratorio"])
def reset_fixtures():
    """Vuelve a cargar los CSV (para probar casos separados sin reiniciar)."""
    global orders
    repository.reset()
    orders = repository._orders
    return {"detail": "Fixtures recargados", "orders": len(orders)}
