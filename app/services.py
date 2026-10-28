"""Capa de aplicación: repositorio en memoria y OrderService.

El servicio coordina el caso de uso (buscar -> invocar dominio -> guardar).
NO decide si una transición es válida: eso lo hace Order.
Esta capa es reutilizable con cualquier interfaz (FastAPI, CLI, proceso batch).
"""
from decimal import Decimal

from app.domain import Customer, Money, Order, OrderItem
from app.specifications import DiscountPolicy, DiscountResult
from cargar_csv import load_fixture, rows


class NotFound(Exception):
    """Recurso inexistente (error de aplicación, no de dominio)."""


class InMemoryOrderRepository:
    """Diccionario en memoria. Los cambios se pierden al cerrar el programa."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self._orders: dict[str, Order] = load_fixture()
        self.customers: dict[str, Customer] = {
            o.customer.id: o.customer for o in self._orders.values()
        }
        for x in rows("clientes.csv"):  # incluye clientes sin pedidos
            self.customers.setdefault(
                x["cliente_id"],
                Customer(x["cliente_id"], bool(int(x["es_vip"])), bool(int(x["activo"]))),
            )
        self.prices: dict[str, Decimal] = {
            x["sku"]: Decimal(x["precio_mxn"]) for x in rows("productos.csv")
        }

    def get(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise NotFound(f"No existe el pedido {order_id}")
        return order

    def list(self) -> list[Order]:
        return list(self._orders.values())

    def save(self, order: Order) -> None:
        self._orders[order.id] = order

    def next_id(self) -> str:
        n = max(int(k[1:]) for k in self._orders if k[1:].isdigit()) + 1
        return f"O{n:03d}"


class OrderService:
    def __init__(self, repository: InMemoryOrderRepository,
                 policy: DiscountPolicy | None = None):
        self.repo = repository
        self.policy = policy or DiscountPolicy()

    def get(self, order_id: str) -> Order:
        return self.repo.get(order_id)

    def list(self) -> list[Order]:
        return self.repo.list()

    def create(self, customer_id: str, has_promotion: bool = False) -> Order:
        customer = self.repo.customers.get(customer_id)
        if customer is None:
            raise NotFound(f"No existe el cliente {customer_id}")
        order = Order(customer=customer, id=self.repo.next_id(),
                      has_promotion=has_promotion)
        self.repo.save(order)
        return order

    def add_item(self, order_id: str, sku: str, quantity: int) -> Order:
        order = self.repo.get(order_id)
        price = self.repo.prices.get(sku)
        if price is None:
            raise NotFound(f"No existe el producto {sku}")
        order.add_item(OrderItem(sku, quantity, Money(price)))
        self.repo.save(order)
        return order

    def confirm(self, order_id: str) -> Order:
        order = self.repo.get(order_id)
        order.confirm()
        self.repo.save(order)
        return order

    def ship(self, order_id: str, tracking_number: str) -> Order:
        order = self.repo.get(order_id)
        order.ship(tracking_number)
        self.repo.save(order)
        return order

    def cancel(self, order_id: str, reason: str) -> Order:
        order = self.repo.get(order_id)
        order.cancel(reason)
        self.repo.save(order)
        return order

    def deliver(self, order_id: str) -> Order:
        order = self.repo.get(order_id)
        order.deliver()
        self.repo.save(order)
        return order

    def return_order(self, order_id: str) -> Order:
        order = self.repo.get(order_id)
        order.return_order()
        self.repo.save(order)
        return order

    def discount(self, order_id: str) -> DiscountResult:
        return self.policy.evaluate(self.repo.get(order_id))
