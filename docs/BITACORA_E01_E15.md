# Bitácora de escenarios E01–E15

Generada por `python ejecutar_escenarios.py`. Cada caso usa un `load_fixture()` nuevo; no se editaron los pedidos.

## Resumen

| Caso | Pedido | Estado inicial | Operación | Objetivo | Resultado real | Evento(s) | ✓ |
|---|---|---|---|---|---|---|---|
| E01 | O001 | DRAFT | evaluar_descuento() | 10% | Descuento 10%; total final 1890.00 MXN | (ninguno) | ✅ |
| E02 | O002 | DRAFT | evaluar_descuento() | 0% | Descuento 0%; total final 1050.00 MXN | (ninguno) | ✅ |
| E03 | O003 | DRAFT | confirm() | rechazo | Rechazado (InvalidOrderData); estado final DRAFT | (ninguno) | ✅ |
| E04 | O005 | DRAFT | evaluar_descuento() | 0% | Descuento 0%; total final 2100.00 MXN | (ninguno) | ✅ |
| E05 | O006 | DRAFT | evaluar_descuento() | 5% | Descuento 5%; total final 17100.00 MXN | (ninguno) | ✅ |
| E06 | O007 | DRAFT | confirm() | rechazo | Rechazado (InvalidOrderData); estado final DRAFT | (ninguno) | ✅ |
| E07 | O008 | DRAFT | confirm() | exito | Éxito; estado final CONFIRMED | OrderConfirmed | ✅ |
| E08 | O009 | DRAFT | add_item(SKU003 x2) | rechazo | Rechazado (OrderItemLimitExceeded); estado final DRAFT | (ninguno) | ✅ |
| E09 | O010 | DRAFT | evaluar_descuento() | 0% | Descuento 0%; total final 500.00 MXN | (ninguno) | ✅ |
| E10 | O011 | DRAFT | evaluar_descuento() | 0% | Descuento 0%; total final 1500.00 MXN | (ninguno) | ✅ |
| E11 | O012 | DRAFT | confirm() → ship("") | rechazo envio | Rechazado (InvalidOrderData); estado final CONFIRMED | OrderConfirmed | ✅ |
| E12 | O013 | DRAFT | confirm() → confirm() | rechazo segunda | Rechazado (InvalidOrderTransition); estado final CONFIRMED | OrderConfirmed | ✅ |
| E13 | O014 | DRAFT | confirm() → ship("GUIA-MX-0001") → cancel("Cliente solicitó la cancelación") | rechazo cancelacion | Rechazado (InvalidOrderTransition); estado final SHIPPED | OrderConfirmed, OrderShipped | ✅ |
| E14 | O015 | DRAFT | confirm() → ship("GUIA-MX-0001") → return_order() | exito | Éxito; estado final RETURNED | OrderConfirmed, OrderShipped, OrderReturned | ✅ |
| E15 | O016 | DRAFT | confirm() → ship("GUIA-MX-0001") → deliver() | exito | Éxito; estado final DELIVERED | OrderConfirmed, OrderShipped, OrderDelivered | ✅ |

## Detalle por escenario

### E01 · O001 · evaluar_descuento

- **Precondiciones:** DRAFT; cliente C001 (Ana Torres) VIP=sí, activo=sí; promoción=no; 2 renglón(es), 4 unidades, total 2100.00 MXN
- **Operación:** evaluar_descuento()
- **Ejecución paso a paso:**
  - evaluar_descuento(): 10%=True, 5%=False, OR=True → 10% (2100.00 − 210.00 = 1890.00 MXN)
- **Resultado:** Descuento 10%; total final 1890.00 MXN (objetivo: 10%) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** AND VIP + monto >500 + unidades >=4 + NOT promo
- **Prueba:** `tests/test_domain.py::test_e01_vip_4_unidades_descuento_10`

### E02 · O002 · evaluar_descuento

- **Precondiciones:** DRAFT; cliente C002 (Luis Medina) VIP=no, activo=sí; promoción=no; 2 renglón(es), 2 unidades, total 1050.00 MXN
- **Operación:** evaluar_descuento()
- **Ejecución paso a paso:**
  - evaluar_descuento(): 10%=False, 5%=False, OR=False → 0% (1050.00 − 0.00 = 1050.00 MXN)
- **Resultado:** Descuento 0%; total final 1050.00 MXN (objetivo: 0%) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** No VIP, total menor a 5000
- **Prueba:** `tests/test_domain.py::test_e02_no_vip_sin_descuento`

### E03 · O003 · confirmar

- **Precondiciones:** DRAFT; cliente C003 (Carla Ruiz) VIP=sí, activo=no; promoción=no; 2 renglón(es), 4 unidades, total 2100.00 MXN
- **Operación:** confirm()
- **Ejecución paso a paso:**
  - confirm(): RECHAZO InvalidOrderData: Requiere artículos y cliente activo [sin evento; estado DRAFT, sin cambios]
- **Resultado:** Rechazado (InvalidOrderData); estado final DRAFT (objetivo: rechazo) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** Cliente inactivo
- **Prueba:** `tests/test_domain.py::test_e03_cliente_inactivo_no_confirma`

### E04 · O005 · evaluar_descuento

- **Precondiciones:** DRAFT; cliente C005 (Sofia Lara) VIP=sí, activo=sí; promoción=sí; 2 renglón(es), 4 unidades, total 2100.00 MXN
- **Operación:** evaluar_descuento()
- **Ejecución paso a paso:**
  - evaluar_descuento(): 10%=False, 5%=False, OR=False → 0% (2100.00 − 0.00 = 2100.00 MXN)
- **Resultado:** Descuento 0%; total final 2100.00 MXN (objetivo: 0%) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** Promocion activa bloquea descuento
- **Prueba:** `tests/test_domain.py::test_e04_promocion_activa_bloquea_descuento`

### E05 · O006 · evaluar_descuento

- **Precondiciones:** DRAFT; cliente C006 (Pedro Soto) VIP=no, activo=sí; promoción=no; 1 renglón(es), 1 unidades, total 18000.00 MXN
- **Operación:** evaluar_descuento()
- **Ejecución paso a paso:**
  - evaluar_descuento(): 10%=False, 5%=True, OR=True → 5% (18000.00 − 900.00 = 17100.00 MXN)
- **Resultado:** Descuento 5%; total final 17100.00 MXN (objetivo: 5%) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** OR total >5000 y sin promocion
- **Prueba:** `tests/test_domain.py::test_e05_total_mayor_5000_descuento_5`

### E06 · O007 · confirmar

- **Precondiciones:** DRAFT; cliente C007 (Mariana Gil) VIP=sí, activo=sí; promoción=no; 0 renglón(es), 0 unidades, total 0.00 MXN
- **Operación:** confirm()
- **Ejecución paso a paso:**
  - confirm(): RECHAZO InvalidOrderData: Requiere artículos y cliente activo [sin evento; estado DRAFT, sin cambios]
- **Resultado:** Rechazado (InvalidOrderData); estado final DRAFT (objetivo: rechazo) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** Pedido sin articulos
- **Prueba:** `tests/test_domain.py::test_e06_pedido_vacio_no_confirma`

### E07 · O008 · confirmar

- **Precondiciones:** DRAFT; cliente C008 (Raul Vega) VIP=no, activo=sí; promoción=no; 1 renglón(es), 20 unidades, total 2400.00 MXN
- **Operación:** confirm()
- **Ejecución paso a paso:**
  - confirm(): OK DRAFT→CONFIRMED [evento OrderConfirmed]
- **Resultado:** Éxito; estado final CONFIRMED (objetivo: exito) ✅
- **Evento(s) registrados:** OrderConfirmed
- **Explicación:** 20 unidades permitidas
- **Prueba:** `tests/test_domain.py::test_e07_20_unidades_exactas_confirma`

### E08 · O009 · agregar SKU003 x2

- **Precondiciones:** DRAFT; cliente C009 (Elena Mora) VIP=sí, activo=sí; promoción=no; 1 renglón(es), 19 unidades, total 2280.00 MXN
- **Operación:** add_item(SKU003 x2)
- **Ejecución paso a paso:**
  - add_item(SKU003 x2): RECHAZO OrderItemLimitExceeded: Máximo 20 unidades (actual 19, se intentó agregar 2) [sin evento; estado DRAFT, sin cambios]
- **Resultado:** Rechazado (OrderItemLimitExceeded); estado final DRAFT (objetivo: rechazo) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** 21 unidades excede limite
- **Prueba:** `tests/test_domain.py::test_e08_agregar_hasta_21_unidades_rechazado`

### E09 · O010 · evaluar_descuento

- **Precondiciones:** DRAFT; cliente C010 (Jorge Luna) VIP=no, activo=sí; promoción=no; 2 renglón(es), 2 unidades, total 500.00 MXN
- **Operación:** evaluar_descuento()
- **Ejecución paso a paso:**
  - evaluar_descuento(): 10%=False, 5%=False, OR=False → 0% (500.00 − 0.00 = 500.00 MXN)
- **Resultado:** Descuento 0%; total final 500.00 MXN (objetivo: 0%) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** Umbral estricto >500
- **Prueba:** `tests/test_domain.py::test_e09_total_exacto_500_sin_descuento`

### E10 · O011 · evaluar_descuento

- **Precondiciones:** DRAFT; cliente C011 (Valeria Rios) VIP=sí, activo=sí; promoción=no; 2 renglón(es), 3 unidades, total 1500.00 MXN
- **Operación:** evaluar_descuento()
- **Ejecución paso a paso:**
  - evaluar_descuento(): 10%=False, 5%=False, OR=False → 0% (1500.00 − 0.00 = 1500.00 MXN)
- **Resultado:** Descuento 0%; total final 1500.00 MXN (objetivo: 0%) ✅
- **Evento(s) registrados:** (ninguno)
- **Explicación:** Solo 3 unidades, requiere 4
- **Prueba:** `tests/test_domain.py::test_e10_vip_3_unidades_sin_descuento`

### E11 · O012 · confirmar y enviar sin guia

- **Precondiciones:** DRAFT; cliente C012 (Oscar Nieto) VIP=no, activo=sí; promoción=no; 1 renglón(es), 1 unidades, total 850.00 MXN
- **Operación:** confirm() → ship("")
- **Ejecución paso a paso:**
  - confirm(): OK DRAFT→CONFIRMED [evento OrderConfirmed]
  - ship(""): RECHAZO InvalidOrderData: El envío requiere número de guía [sin evento; estado CONFIRMED, sin cambios]
- **Resultado:** Rechazado (InvalidOrderData); estado final CONFIRMED (objetivo: rechazo envio) ✅
- **Evento(s) registrados:** OrderConfirmed
- **Explicación:** La confirmacion es valida pero falta guia
- **Prueba:** `tests/test_domain.py::test_e11_envio_sin_guia_rechazado`

### E12 · O013 · confirmar dos veces

- **Precondiciones:** DRAFT; cliente C001 (Ana Torres) VIP=sí, activo=sí; promoción=no; 1 renglón(es), 1 unidades, total 600.00 MXN
- **Operación:** confirm() → confirm()
- **Ejecución paso a paso:**
  - confirm(): OK DRAFT→CONFIRMED [evento OrderConfirmed]
  - confirm(): RECHAZO InvalidOrderTransition: Solo DRAFT puede confirmarse (estado actual: CONFIRMED) [sin evento; estado CONFIRMED, sin cambios]
- **Resultado:** Rechazado (InvalidOrderTransition); estado final CONFIRMED (objetivo: rechazo segunda) ✅
- **Evento(s) registrados:** OrderConfirmed
- **Explicación:** No permite confirmar desde CONFIRMED
- **Prueba:** `tests/test_domain.py::test_e12_confirmacion_doble_rechazada`

### E13 · O014 · confirmar, enviar y cancelar

- **Precondiciones:** DRAFT; cliente C002 (Luis Medina) VIP=no, activo=sí; promoción=no; 1 renglón(es), 1 unidades, total 600.00 MXN
- **Operación:** confirm() → ship("GUIA-MX-0001") → cancel("Cliente solicitó la cancelación")
- **Ejecución paso a paso:**
  - confirm(): OK DRAFT→CONFIRMED [evento OrderConfirmed]
  - ship("GUIA-MX-0001"): OK CONFIRMED→SHIPPED [evento OrderShipped]
  - cancel("Cliente solicitó la cancelación"): RECHAZO InvalidOrderTransition: Solo CONFIRMED puede cancelarse (estado actual: SHIPPED) [sin evento; estado SHIPPED, sin cambios]
- **Resultado:** Rechazado (InvalidOrderTransition); estado final SHIPPED (objetivo: rechazo cancelacion) ✅
- **Evento(s) registrados:** OrderConfirmed, OrderShipped
- **Explicación:** No permite cancelar desde SHIPPED
- **Prueba:** `tests/test_domain.py::test_e13_cancelar_desde_shipped_rechazado`

### E14 · O015 · confirmar, enviar y devolver

- **Precondiciones:** DRAFT; cliente C005 (Sofia Lara) VIP=sí, activo=sí; promoción=no; 1 renglón(es), 1 unidades, total 450.00 MXN
- **Operación:** confirm() → ship("GUIA-MX-0001") → return_order()
- **Ejecución paso a paso:**
  - confirm(): OK DRAFT→CONFIRMED [evento OrderConfirmed]
  - ship("GUIA-MX-0001"): OK CONFIRMED→SHIPPED [evento OrderShipped]
  - return_order(): OK SHIPPED→RETURNED [evento OrderReturned]
- **Resultado:** Éxito; estado final RETURNED (objetivo: exito) ✅
- **Evento(s) registrados:** OrderConfirmed, OrderShipped, OrderReturned
- **Explicación:** Termina en RETURNED
- **Prueba:** `tests/test_domain.py::test_e14_devolucion_desde_shipped`

### E15 · O016 · confirmar, enviar y entregar

- **Precondiciones:** DRAFT; cliente C007 (Mariana Gil) VIP=sí, activo=sí; promoción=no; 1 renglón(es), 1 unidades, total 2100.00 MXN
- **Operación:** confirm() → ship("GUIA-MX-0001") → deliver()
- **Ejecución paso a paso:**
  - confirm(): OK DRAFT→CONFIRMED [evento OrderConfirmed]
  - ship("GUIA-MX-0001"): OK CONFIRMED→SHIPPED [evento OrderShipped]
  - deliver(): OK SHIPPED→DELIVERED [evento OrderDelivered]
- **Resultado:** Éxito; estado final DELIVERED (objetivo: exito) ✅
- **Evento(s) registrados:** OrderConfirmed, OrderShipped, OrderDelivered
- **Explicación:** Termina en DELIVERED
- **Prueba:** `tests/test_domain.py::test_e15_entrega_desde_shipped`
