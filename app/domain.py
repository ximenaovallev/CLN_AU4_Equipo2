"""Núcleo de dominio TechStore (Actividad 4, Unidad 4).

Contiene:
- Excepciones de dominio (jerarquía DomainException -> OrderException -> ...).
- Value Objects inmutables: Money y OrderItem.
- Entidad Customer.
- Aggregate Root Order con su máquina de estados y Domain Events.

El dominio NO depende de FastAPI ni de los CSV: puede ejecutarse y probarse en memoria.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

MAX_UNITS_PER_ORDER = 20  # Suma de unidades, NO número de renglones.
CURRENCY = "MXN"


# ---------------------------------------------------------------------------
# Excepciones de dominio
# ---------------------------------------------------------------------------
class DomainException(Exception):
    """Una operación viola una política del negocio (no es un error técnico)."""


class OrderException(DomainException):
    """Errores propios del agregado Order."""


class InvalidOrderData(OrderException):
    """Datos inválidos: monto negativo, artículo sin SKU, pedido vacío, guía vacía..."""


class InvalidOrderTransition(OrderException):
    """Transición no permitida por la máquina de estados."""


class OrderItemLimitExceeded(OrderException):
    """El pedido superaría el máximo de 20 unidades."""


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Money:
    """Importe inmutable en MXN. Se compara por valor."""

    amount: Decimal
    currency: str = CURRENCY

    def __post_init__(self):
        # Decimal obligatorio: un float (0.1 + 0.2) acumula errores de redondeo.
        if not isinstance(self.amount, Decimal):
            raise InvalidOrderData("El monto debe ser Decimal, no float/int")
        if not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData("Monto inválido")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise InvalidOrderData("Moneda inválida")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, factor) -> "Money":
        """Devuelve un Money nuevo; factor puede ser int (cantidad) o Decimal (tasa)."""
        if isinstance(factor, float):
            raise InvalidOrderData("El factor no puede ser float")
        return Money(self.amount * factor, self.currency)

    def rounded(self) -> "Money":
        return Money(self.amount.quantize(Decimal("0.01")), self.currency)


@dataclass(frozen=True)
class Customer:
    id: str
    is_vip: bool = False
    active: bool = True

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise InvalidOrderData("Cliente sin identificador")


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if (not isinstance(self.sku, str) or not self.sku.strip()
                or isinstance(self.quantity, bool)
                or not isinstance(self.quantity, int)
                or self.quantity <= 0):
            raise InvalidOrderData("Artículo inválido")
        if not isinstance(self.unit_price, Money):
            raise InvalidOrderData("El precio debe ser Money")

    @property
    def subtotal(self) -> Money:
        # Se calcula, nunca se captura a mano: evita discrepancias.
        return self.unit_price.multiply(self.quantity)


# ---------------------------------------------------------------------------
# Domain Events
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DomainEvent:
    """Hecho que YA ocurrió. Inmutable; nombre en pasado."""

    name: str
    order_id: str
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: dict = field(default_factory=dict, compare=False)


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------
class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


@dataclass
class Order:
    """Aggregate Root: única puerta para modificar items y status.

    Regla de cada transición: 1) validar, 2) cambiar status, 3) registrar evento.
    Si la validación falla, el pedido queda exactamente igual (sin evento).
    """

    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: list[OrderItem] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)
    tracking_number: str | None = None
    cancel_reason: str | None = None

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise InvalidOrderData("Pedido sin identificador")
        if not isinstance(self.customer, Customer):
            raise InvalidOrderData("El pedido requiere un Customer")

    # --- Consultas ---------------------------------------------------------
    @property
    def units(self) -> int:
        """Suma de cantidades (no cuenta renglones)."""
        return sum(item.quantity for item in self.items)

    @property
    def total(self) -> Money:
        amount = sum((x.subtotal.amount for x in self.items), Decimal("0.00"))
        return Money(amount)

    # --- Comandos ----------------------------------------------------------
    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT admite artículos")
        if self.units + item.quantity > MAX_UNITS_PER_ORDER:
            raise OrderItemLimitExceeded(
                f"Máximo {MAX_UNITS_PER_ORDER} unidades "
                f"(actual {self.units}, se intentó agregar {item.quantity})"
            )
        if item.unit_price.currency != CURRENCY:
            raise InvalidOrderData("Solo MXN")
        self.items.append(item)

    def confirm(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition(
                f"Solo DRAFT puede confirmarse (estado actual: {self.status.value})"
            )
        if not self.items or not self.customer.active:
            raise InvalidOrderData("Requiere artículos y cliente activo")
        self.status = OrderStatus.CONFIRMED
        self._record("OrderConfirmed", total=str(self.total.amount),
                     units=self.units)

    def ship(self, tracking_number: str) -> None:
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition(
                f"Solo CONFIRMED puede enviarse (estado actual: {self.status.value})"
            )
        if not isinstance(tracking_number, str) or not tracking_number.strip():
            raise InvalidOrderData("El envío requiere número de guía")
        self.status = OrderStatus.SHIPPED
        self.tracking_number = tracking_number.strip()
        self._record("OrderShipped", tracking_number=self.tracking_number)

    def cancel(self, reason: str) -> None:
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition(
                f"Solo CONFIRMED puede cancelarse (estado actual: {self.status.value})"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidOrderData("La cancelación requiere motivo")
        self.status = OrderStatus.CANCELLED
        self.cancel_reason = reason.strip()
        self._record("OrderCancelled", reason=self.cancel_reason)

    def deliver(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition(
                f"Solo SHIPPED puede entregarse (estado actual: {self.status.value})"
            )
        self.status = OrderStatus.DELIVERED
        self._record("OrderDelivered")

    def return_order(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition(
                f"Solo SHIPPED puede devolverse (estado actual: {self.status.value})"
            )
        self.status = OrderStatus.RETURNED
        self._record("OrderReturned")

    # --- Interno -----------------------------------------------------------
    def _record(self, name: str, **details) -> None:
        """Se llama SOLO al final de una transición válida."""
        self.events.append(
            DomainEvent(name, self.id,
                        details={"customer_id": self.customer.id, **details})
        )
