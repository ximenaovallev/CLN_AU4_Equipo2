"""Specification Pattern para las reglas de descuento TechStore.

Una Specification solo RESPONDE (True/False); nunca modifica el pedido.
Operadores:  &  -> AND     |  -> OR     ~  -> NOT
"""
from dataclasses import dataclass
from decimal import Decimal

from app.domain import Money, Order


class Specification:
    def is_satisfied_by(self, order: Order) -> bool:
        raise NotImplementedError

    def __and__(self, other: "Specification") -> "Specification":
        return AndSpec(self, other)

    def __or__(self, other: "Specification") -> "Specification":
        return OrSpec(self, other)

    def __invert__(self) -> "Specification":
        return NotSpec(self)


class AndSpec(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left, self.right = left, right

    def is_satisfied_by(self, order: Order) -> bool:
        return (self.left.is_satisfied_by(order)
                and self.right.is_satisfied_by(order))


class OrSpec(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left, self.right = left, right

    def is_satisfied_by(self, order: Order) -> bool:
        return (self.left.is_satisfied_by(order)
                or self.right.is_satisfied_by(order))


class NotSpec(Specification):
    def __init__(self, spec: Specification):
        self.spec = spec

    def is_satisfied_by(self, order: Order) -> bool:
        return not self.spec.is_satisfied_by(order)


# ---------------------------------------------------------------------------
# Specifications concretas
# ---------------------------------------------------------------------------
class MinimumAmountSpec(Specification):
    """Total ESTRICTAMENTE mayor que el umbral (>, no >=)."""

    def __init__(self, threshold: Decimal):
        if not isinstance(threshold, Decimal):
            raise TypeError("El umbral debe ser Decimal")
        self.threshold = threshold

    def is_satisfied_by(self, order: Order) -> bool:
        return order.total.amount > self.threshold


class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order: Order) -> bool:
        return order.customer.is_vip


class MinimumUnitsSpec(Specification):
    """Al menos N unidades (suma de cantidades)."""

    def __init__(self, minimum: int):
        self.minimum = minimum

    def is_satisfied_by(self, order: Order) -> bool:
        return order.units >= self.minimum


class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order: Order) -> bool:
        return order.has_promotion


# ---------------------------------------------------------------------------
# Reglas compuestas
# ---------------------------------------------------------------------------
# 10 %: VIP AND total > 500 AND unidades >= 4 AND NOT promoción
TEN_PERCENT = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)

# 5 %: total > 5000 AND NOT promoción
FIVE_PERCENT = MinimumAmountSpec(Decimal("5000")) & ~ActivePromotionSpec()

# Elegible a algún descuento: 10 % OR 5 %
ANY_DISCOUNT = TEN_PERCENT | FIVE_PERCENT


@dataclass(frozen=True)
class DiscountResult:
    rule: str          # "VIP_10", "MONTO_5" o "NINGUNO"
    rate: Decimal      # 0.10, 0.05 o 0
    subtotal: Money
    discount: Money
    total: Money

    @property
    def percent(self) -> str:
        return f"{int(self.rate * 100)}%"


class DiscountPolicy:
    """Decide qué descuento aplica. Prioridad: 10 % antes que 5 %.

    No modifica el pedido; devuelve un resultado calculado.
    """

    TEN = Decimal("0.10")
    FIVE = Decimal("0.05")

    def evaluate(self, order: Order) -> DiscountResult:
        if TEN_PERCENT.is_satisfied_by(order):
            rule, rate = "VIP_10", self.TEN
        elif FIVE_PERCENT.is_satisfied_by(order):
            rule, rate = "MONTO_5", self.FIVE
        else:
            rule, rate = "NINGUNO", Decimal("0")
        subtotal = order.total
        discount = subtotal.multiply(rate).rounded()
        total = Money(subtotal.amount - discount.amount).rounded()
        return DiscountResult(rule, rate, subtotal, discount, total)
