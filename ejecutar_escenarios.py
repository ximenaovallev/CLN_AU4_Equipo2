"""Ejecuta los escenarios E01–E15 de datos/escenarios.csv y genera la bitácora.

Cada caso usa un load_fixture() NUEVO: los cambios de un caso no afectan al siguiente.
No se editan pedidos para forzar resultados: solo se invocan métodos del dominio.

Uso:
    python ejecutar_escenarios.py            # imprime la bitácora
    python ejecutar_escenarios.py --md FILE  # además la guarda en Markdown
"""
import sys
from decimal import Decimal

from app.domain import DomainException, Money, OrderItem
from app.specifications import (ANY_DISCOUNT, FIVE_PERCENT, TEN_PERCENT,
                                DiscountPolicy)
from cargar_csv import load_fixture, rows

PRICES = {x["sku"]: Decimal(x["precio_mxn"]) for x in rows("productos.csv")}
CUSTOMERS = {x["cliente_id"]: x["nombre"] for x in rows("clientes.csv")}
TRACKING = "GUIA-MX-0001"
CANCEL_REASON = "Cliente solicitó la cancelación"

# Prueba pytest que cubre cada escenario (tests/test_domain.py).
TESTS = {
    "E01": "test_e01_vip_4_unidades_descuento_10",
    "E02": "test_e02_no_vip_sin_descuento",
    "E03": "test_e03_cliente_inactivo_no_confirma",
    "E04": "test_e04_promocion_activa_bloquea_descuento",
    "E05": "test_e05_total_mayor_5000_descuento_5",
    "E06": "test_e06_pedido_vacio_no_confirma",
    "E07": "test_e07_20_unidades_exactas_confirma",
    "E08": "test_e08_agregar_hasta_21_unidades_rechazado",
    "E09": "test_e09_total_exacto_500_sin_descuento",
    "E10": "test_e10_vip_3_unidades_sin_descuento",
    "E11": "test_e11_envio_sin_guia_rechazado",
    "E12": "test_e12_confirmacion_doble_rechazada",
    "E13": "test_e13_cancelar_desde_shipped_rechazado",
    "E14": "test_e14_devolucion_desde_shipped",
    "E15": "test_e15_entrega_desde_shipped",
}


def preconditions(order):
    c = order.customer
    return (f"{order.status.value}; cliente {c.id} ({CUSTOMERS[c.id]}) "
            f"VIP={'sí' if c.is_vip else 'no'}, activo={'sí' if c.active else 'no'}; "
            f"promoción={'sí' if order.has_promotion else 'no'}; "
            f"{len(order.items)} renglón(es), {order.units} unidades, "
            f"total {order.total.amount} MXN")


def steps_for(action, order):
    """Traduce la columna 'accion' del CSV a llamadas del dominio."""
    a = action.strip().lower()
    if a == "evaluar_descuento":
        return [("evaluar_descuento()", None)]
    if a == "confirmar":
        return [("confirm()", order.confirm)]
    if a.startswith("agregar"):
        _, sku, qty = a.split()  # "agregar SKU003 x2"
        sku, qty = sku.upper(), int(qty.lstrip("x"))
        item = OrderItem(sku, qty, Money(PRICES[sku]))
        return [(f"add_item({sku} x{qty})", lambda: order.add_item(item))]
    if a == "confirmar y enviar sin guia":
        return [("confirm()", order.confirm), ('ship("")', lambda: order.ship(""))]
    if a == "confirmar dos veces":
        return [("confirm()", order.confirm), ("confirm()", order.confirm)]
    ship = (f'ship("{TRACKING}")', lambda: order.ship(TRACKING))
    if a == "confirmar, enviar y cancelar":
        return [("confirm()", order.confirm), ship,
                (f'cancel("{CANCEL_REASON}")', lambda: order.cancel(CANCEL_REASON))]
    if a == "confirmar, enviar y devolver":
        return [("confirm()", order.confirm), ship, ("return_order()", order.return_order)]
    if a == "confirmar, enviar y entregar":
        return [("confirm()", order.confirm), ship, ("deliver()", order.deliver)]
    raise ValueError(f"Acción no reconocida: {action}")


def run_case(case):
    orders = load_fixture()                      # copia independiente
    order = orders[case["pedido_id"]]
    pre = preconditions(order)
    log, error = [], None
    discount = None
    for label, fn in steps_for(case["accion"], order):
        before_status, before_events = order.status, len(order.events)
        before_units = order.units
        if fn is None:
            discount = DiscountPolicy().evaluate(order)
            flags = (f"10%={TEN_PERCENT.is_satisfied_by(order)}, "
                     f"5%={FIVE_PERCENT.is_satisfied_by(order)}, "
                     f"OR={ANY_DISCOUNT.is_satisfied_by(order)}")
            log.append(f"{label}: {flags} → {discount.percent} "
                       f"({discount.subtotal.amount} − {discount.discount.amount} "
                       f"= {discount.total.amount} MXN)")
            continue
        try:
            fn()
            ev = order.events[-1].name if len(order.events) > before_events else "—"
            log.append(f"{label}: OK {before_status.value}→{order.status.value} "
                       f"[evento {ev}]")
        except DomainException as exc:
            error = exc
            unchanged = (order.status == before_status
                         and len(order.events) == before_events
                         and order.units == before_units)
            log.append(f"{label}: RECHAZO {type(exc).__name__}: {exc} "
                       f"[sin evento; estado {order.status.value}"
                       f"{', sin cambios' if unchanged else ', ¡CAMBIÓ!'}]")
            break

    target = case["objetivo"].strip().lower()
    if target.endswith("%"):
        ok = discount is not None and discount.percent == target
        result = f"Descuento {discount.percent}; total final {discount.total.amount} MXN"
    elif target.startswith("rechazo"):
        ok = error is not None
        if target == "rechazo envio":
            ok = ok and "ship" in log[-1]
        elif target == "rechazo segunda":
            ok = ok and len(log) == 2 and "OK" in log[0]
        elif target == "rechazo cancelacion":
            ok = ok and "cancel" in log[-1]
        result = f"Rechazado ({type(error).__name__ if error else 'sin error'}); estado final {order.status.value}"
    else:  # exito
        ok = error is None
        result = f"Éxito; estado final {order.status.value}"

    events = [e.name for e in order.events] or ["(ninguno)"]
    return {
        "caso": case["caso_id"], "pedido": case["pedido_id"],
        "accion": case["accion"], "objetivo": case["objetivo"],
        "pista": case["pista"], "precondiciones": pre,
        "operacion": " → ".join(l.split(":")[0] for l in log),
        "detalle": log, "resultado": result,
        "eventos": events, "estado_final": order.status.value,
        "prueba": TESTS[case["caso_id"]], "cumple": ok,
    }


def run_all():
    return [run_case(c) for c in rows("escenarios.csv")]


def to_markdown(results):
    out = ["# Bitácora de escenarios E01–E15", "",
           "Generada por `python ejecutar_escenarios.py`. Cada caso usa un "
           "`load_fixture()` nuevo; no se editaron los pedidos.", "",
           "## Resumen", "",
           "| Caso | Pedido | Estado inicial | Operación | Objetivo | Resultado real | Evento(s) | ✓ |",
           "|---|---|---|---|---|---|---|---|"]
    for r in results:
        out.append(f"| {r['caso']} | {r['pedido']} | DRAFT | {r['operacion']} | "
                   f"{r['objetivo']} | {r['resultado']} | {', '.join(r['eventos'])} | "
                   f"{'✅' if r['cumple'] else '❌'} |")
    out += ["", "## Detalle por escenario", ""]
    for r in results:
        out += [f"### {r['caso']} · {r['pedido']} · {r['accion']}", "",
                f"- **Precondiciones:** {r['precondiciones']}",
                f"- **Operación:** {r['operacion']}",
                "- **Ejecución paso a paso:**"]
        out += [f"  - {l}" for l in r["detalle"]]
        out += [f"- **Resultado:** {r['resultado']} (objetivo: {r['objetivo']}) "
                f"{'✅' if r['cumple'] else '❌'}",
                f"- **Evento(s) registrados:** {', '.join(r['eventos'])}",
                f"- **Explicación:** {r['pista']}",
                f"- **Prueba:** `tests/test_domain.py::{r['prueba']}`", ""]
    return "\n".join(out)


if __name__ == "__main__":
    results = run_all()
    for r in results:
        print(f"{r['caso']} {r['pedido']} {'OK ' if r['cumple'] else 'FALLA'} "
              f"| {r['operacion']} | {r['resultado']} | eventos: {', '.join(r['eventos'])}")
    passed = sum(r["cumple"] for r in results)
    print(f"\n{passed}/{len(results)} escenarios cumplen su objetivo")
    if "--md" in sys.argv:
        path = sys.argv[sys.argv.index("--md") + 1]
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_markdown(results))
        print(f"Bitácora guardada en {path}")
    sys.exit(0 if passed == len(results) else 1)
