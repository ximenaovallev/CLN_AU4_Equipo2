"""Pruebas del dominio TechStore. Estructura: preparar -> ejecutar -> comprobar."""
from decimal import Decimal

import pytest

from app.domain import (Customer, DomainEvent, InvalidOrderData,
                        InvalidOrderTransition, Money, Order, OrderItem,
                        OrderItemLimitExceeded, OrderStatus)
from app.specifications import (ANY_DISCOUNT, FIVE_PERCENT, TEN_PERCENT,
                                ActivePromotionSpec, DiscountPolicy,
                                MinimumAmountSpec, MinimumUnitsSpec,
                                VIPCustomerSpec)
from cargar_csv import load_fixture

GUIA = "GUIA-MX-0001"


@pytest.fixture
def orders():
    """Copia nueva de los fixtures en cada prueba (no se comparten cambios)."""
    return load_fixture()


def snapshot(order):
    return order.status, len(order.events), order.units, order.total


def item(sku="SKU001", qty=1, price="600.00"):
    return OrderItem(sku, qty, Money(Decimal(price)))


# ---------------------------------------------------------------------------
# Ejemplos de la sección 12
# ---------------------------------------------------------------------------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


def test_pedido_o001_inicia_draft():
    orders = load_fixture()
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
def test_carga_16_pedidos_todos_draft(orders):
    assert len(orders) == 16
    assert all(o.status is OrderStatus.DRAFT for o in orders.values())
    assert all(o.events == [] for o in orders.values())
    assert sum(len(o.items) for o in orders.values()) == 21


@pytest.mark.parametrize("oid, cliente, unidades, total", [
    ("O001", "C001", 4, "2100.00"),
    ("O006", "C006", 1, "18000.00"),
    ("O010", "C010", 2, "500.00"),
])
def test_tabla_calculo_manual(orders, oid, cliente, unidades, total):
    o = orders[oid]
    assert (o.customer.id, o.units, o.total.amount) == (cliente, unidades, Decimal(total))


# ---------------------------------------------------------------------------
# Value Objects e invariantes
# ---------------------------------------------------------------------------
def test_money_rechaza_float():
    with pytest.raises(InvalidOrderData):
        Money(600.00)


def test_money_rechaza_no_finito():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("NaN"))


def test_money_es_inmutable_y_add_crea_objeto_nuevo():
    a, b = Money(Decimal("100")), Money(Decimal("50"))
    c = a.add(b)
    assert c == Money(Decimal("150")) and a.amount == Decimal("100")
    with pytest.raises(Exception):
        a.amount = Decimal("1")


def test_money_rechaza_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1")).add(Money(Decimal("1"), "USD"))


@pytest.mark.parametrize("qty", [0, -1])
def test_order_item_cantidad_invalida(qty):
    with pytest.raises(InvalidOrderData):
        item(qty=qty)


def test_order_item_sku_vacio():
    with pytest.raises(InvalidOrderData):
        item(sku="  ")


def test_subtotal_calculado():
    assert item(qty=2).subtotal.amount == Decimal("1200.00")


def test_solo_mxn():
    o = Order(customer=Customer("CX"), id="OX")
    with pytest.raises(InvalidOrderData):
        o.add_item(OrderItem("SKU001", 1, Money(Decimal("10"), "USD")))
    assert o.items == []


# ---------------------------------------------------------------------------
# Límite de 20 unidades (suma de unidades, no renglones)
# ---------------------------------------------------------------------------
def test_21_unidades_rechazado_sin_modificar(orders):
    o = orders["O008"]  # ya tiene 20
    before = snapshot(o)
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(item("SKU003", 1, "120.00"))
    assert snapshot(o) == before


def test_limite_es_por_unidades_no_por_renglones():
    o = Order(customer=Customer("CX"), id="OX")
    for _ in range(20):                       # 20 renglones de 1 unidad: OK
        o.add_item(item(qty=1))
    assert o.units == 20 and len(o.items) == 20
    o2 = Order(customer=Customer("CY"), id="OY")
    with pytest.raises(OrderItemLimitExceeded):  # 1 renglón de 21: rechazo
        o2.add_item(item(qty=21))


def test_no_agrega_articulos_fuera_de_draft(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.add_item(item())
    assert o.units == 1


# ---------------------------------------------------------------------------
# Specifications
# ---------------------------------------------------------------------------
def test_specs_individuales(orders):
    o1 = orders["O001"]
    assert MinimumAmountSpec(Decimal("500")).is_satisfied_by(o1)
    assert VIPCustomerSpec().is_satisfied_by(o1)
    assert MinimumUnitsSpec(4).is_satisfied_by(o1)
    assert not ActivePromotionSpec().is_satisfied_by(o1)
    assert ActivePromotionSpec().is_satisfied_by(orders["O005"])


def test_minimum_amount_es_estricto(orders):
    assert not MinimumAmountSpec(Decimal("500")).is_satisfied_by(orders["O010"])


def test_composicion_and_or_not(orders):
    vip, promo = VIPCustomerSpec(), ActivePromotionSpec()
    o5 = orders["O005"]                       # VIP con promoción
    assert (vip & promo).is_satisfied_by(o5)
    assert not (vip & ~promo).is_satisfied_by(o5)
    assert (promo | vip).is_satisfied_by(orders["O001"])
    assert not (promo | vip).is_satisfied_by(orders["O002"])
    assert (~promo).is_satisfied_by(orders["O002"])


def test_specification_no_modifica_pedido(orders):
    o = orders["O001"]
    before = snapshot(o)
    ANY_DISCOUNT.is_satisfied_by(o)
    DiscountPolicy().evaluate(o)
    assert snapshot(o) == before


def test_descuento_vip(orders):
    r = DiscountPolicy().evaluate(orders["O001"])
    assert (r.rule, r.discount.amount, r.total.amount) == (
        "VIP_10", Decimal("210.00"), Decimal("1890.00"))


def test_promocion_activa_sin_descuento(orders):
    o = orders["O005"]
    assert not ANY_DISCOUNT.is_satisfied_by(o)
    assert DiscountPolicy().evaluate(o).rate == 0


def test_prioridad_10_sobre_5():
    vip = Customer("CV", is_vip=True)
    o = Order(customer=vip, id="OP")
    o.add_item(OrderItem("SKU008", 1, Money(Decimal("18000.00"))))
    o.add_item(OrderItem("SKU003", 3, Money(Decimal("120.00"))))
    assert TEN_PERCENT.is_satisfied_by(o) and FIVE_PERCENT.is_satisfied_by(o)
    assert DiscountPolicy().evaluate(o).rule == "VIP_10"


def test_cinco_por_ciento_umbral_estricto():
    o = Order(customer=Customer("CN"), id="O5")
    o.add_item(OrderItem("SKU005", 1, Money(Decimal("5000.00"))))
    assert not FIVE_PERCENT.is_satisfied_by(o)


# ---------------------------------------------------------------------------
# Máquina de estados y eventos
# ---------------------------------------------------------------------------
def test_cliente_inactivo_no_confirma(orders):
    o = orders["O004"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status is OrderStatus.DRAFT and o.events == []


def test_pedido_vacio_no_confirma(orders):
    o = orders["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status is OrderStatus.DRAFT and o.events == []


def test_envio_sin_guia(orders):
    o = orders["O012"]
    o.confirm()
    for guia in ["", "   "]:
        with pytest.raises(InvalidOrderData):
            o.ship(guia)
    assert o.status is OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_confirmacion_doble(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_cancelacion_desde_shipped(orders):
    o = orders["O014"]
    o.confirm()
    o.ship(GUIA)
    with pytest.raises(InvalidOrderTransition):
        o.cancel("motivo")
    assert o.status is OrderStatus.SHIPPED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"]


def test_cancelacion_valida_requiere_motivo(orders):
    o = orders["O014"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.cancel(" ")
    o.cancel("Cliente solicitó la cancelación")
    assert o.status is OrderStatus.CANCELLED
    assert o.events[-1].name == "OrderCancelled"
    assert o.events[-1].details["reason"] == "Cliente solicitó la cancelación"


def test_no_cancelar_desde_draft(orders):
    with pytest.raises(InvalidOrderTransition):
        orders["O013"].cancel("motivo")


@pytest.mark.parametrize("op", ["deliver", "return_order"])
def test_entregar_o_devolver_requiere_shipped(orders, op):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        getattr(o, op)()
    assert o.status is OrderStatus.CONFIRMED and len(o.events) == 1


def test_estados_finales_no_admiten_transiciones(orders):
    o = orders["O016"]
    o.confirm(); o.ship(GUIA); o.deliver()
    for op in (o.confirm, o.deliver, o.return_order, lambda: o.ship(GUIA),
               lambda: o.cancel("x")):
        with pytest.raises(InvalidOrderTransition):
            op()
    assert len(o.events) == 3


def test_evento_es_inmutable_y_contiene_datos(orders):
    o = orders["O001"]
    o.confirm()
    ev = o.events[0]
    assert isinstance(ev, DomainEvent) and ev.order_id == "O001"
    assert ev.details == {"customer_id": "C001", "total": "2100.00", "units": 4}
    assert ev.occurred_at.tzinfo is not None
    with pytest.raises(Exception):
        ev.name = "Otro"


# ---------------------------------------------------------------------------
# Escenarios E01–E15 (datos/escenarios.csv)
# ---------------------------------------------------------------------------
def test_e01_vip_4_unidades_descuento_10(orders):
    assert DiscountPolicy().evaluate(orders["O001"]).percent == "10%"


def test_e02_no_vip_sin_descuento(orders):
    assert DiscountPolicy().evaluate(orders["O002"]).percent == "0%"


def test_e03_cliente_inactivo_no_confirma(orders):
    o = orders["O003"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status is OrderStatus.DRAFT and o.events == []


def test_e04_promocion_activa_bloquea_descuento(orders):
    assert DiscountPolicy().evaluate(orders["O005"]).percent == "0%"


def test_e05_total_mayor_5000_descuento_5(orders):
    r = DiscountPolicy().evaluate(orders["O006"])
    assert r.percent == "5%" and r.total.amount == Decimal("17100.00")


def test_e06_pedido_vacio_no_confirma(orders):
    o = orders["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status is OrderStatus.DRAFT and o.events == []


def test_e07_20_unidades_exactas_confirma(orders):
    o = orders["O008"]
    assert o.units == 20
    o.confirm()
    assert o.status is OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_e08_agregar_hasta_21_unidades_rechazado(orders):
    o = orders["O009"]
    before = snapshot(o)
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))
    assert snapshot(o) == before and o.units == 19


def test_e09_total_exacto_500_sin_descuento(orders):
    o = orders["O010"]
    assert o.total.amount == Decimal("500.00")
    assert DiscountPolicy().evaluate(o).percent == "0%"


def test_e10_vip_3_unidades_sin_descuento(orders):
    o = orders["O011"]
    assert o.customer.is_vip and o.units == 3
    assert DiscountPolicy().evaluate(o).percent == "0%"


def test_e11_envio_sin_guia_rechazado(orders):
    o = orders["O012"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship("")
    assert o.status is OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_e12_confirmacion_doble_rechazada(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_e13_cancelar_desde_shipped_rechazado(orders):
    o = orders["O014"]
    o.confirm(); o.ship(GUIA)
    with pytest.raises(InvalidOrderTransition):
        o.cancel("Cliente solicitó la cancelación")
    assert o.status is OrderStatus.SHIPPED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"]


def test_e14_devolucion_desde_shipped(orders):
    o = orders["O015"]
    o.confirm(); o.ship(GUIA); o.return_order()
    assert o.status is OrderStatus.RETURNED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped", "OrderReturned"]


def test_e15_entrega_desde_shipped(orders):
    o = orders["O016"]
    o.confirm(); o.ship(GUIA); o.deliver()
    assert o.status is OrderStatus.DELIVERED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_ejecutor_de_escenarios_cumple_15_de_15():
    from ejecutar_escenarios import run_all
    results = run_all()
    assert len(results) == 15 and all(r["cumple"] for r in results)
