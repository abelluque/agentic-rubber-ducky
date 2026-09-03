.PHONY: ast-selftest pytest-sample

ast-selftest:
	bash scripts/ast-selftest.sh

pytest-sample:
	PYTHONPATH=sample-app/src python3 -m pytest sample-app/src/orders/tests -q
