from fastapi import FastAPI
from pydantic import BaseModel, Field

from orders.pricing import calculate_order_total

app = FastAPI(title="orders-qa", version="0.1.0")


class QuoteRequest(BaseModel):
    items: list[dict] = Field(default_factory=list)
    tax_rate: float = 0.21


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/quote")
def quote(req: QuoteRequest) -> dict[str, float]:
    return {"total": calculate_order_total(req.items, req.tax_rate)}
