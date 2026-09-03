# Sample app: orders-qa

Microservicio mínimo usado como **carga de trabajo de QA** en la demo. Contiene un hotspot deliberado en `src/orders/pricing.py` (`calculate_order_total` con bucle anidado O(n²) para contar SKUs duplicados).

El Code Agent reescribe esa función. El GitHub Agent abre el PR contra este árbol (o el remoto que se allowliste). Argo CD en el clúster de destino sincroniza `gitops/` hacia el namespace `orders-qa`.

```bash
pip install -r requirements.txt pytest
PYTHONPATH=src pytest src/orders/tests
```

Tras el refactor, los tests deben seguir pasando: el descuento del 5 % por SKU duplicado se conserva.
