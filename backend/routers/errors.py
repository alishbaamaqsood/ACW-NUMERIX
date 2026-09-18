from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ErrorInput(BaseModel):
    true_value: float
    approx_value: float
    previous_approx: Optional[float] = None

@router.post("/analyze")
def analyze_errors(data: ErrorInput):
    tv = data.true_value
    av = data.approx_value

    absolute_error = abs(tv - av)
    relative_error = abs((tv - av) / tv) if tv != 0 else None
    percent_relative_error = relative_error * 100 if relative_error is not None else None

    true_percent_relative_error = abs((tv - av) / tv) * 100 if tv != 0 else None
    approx_percent_relative_error = None
    if data.previous_approx is not None:
        denom = av if av != 0 else 1
        approx_percent_relative_error = abs((av - data.previous_approx) / denom) * 100

    # Round-off demo: show float precision loss
    roundoff_demo = []
    x = 1.0
    for i in range(10):
        x = x / 3.0 * 3.0
        roundoff_demo.append({"step": i + 1, "value": x, "error": abs(x - 1.0)})

    # Truncation demo: e^x Taylor series
    import math
    x_val = 1.0
    exact = math.exp(x_val)
    truncation_demo = []
    approx = 0
    for n in range(8):
        approx += (x_val ** n) / math.factorial(n)
        truncation_demo.append({
            "terms": n + 1,
            "approx": approx,
            "exact": exact,
            "truncation_error": abs(exact - approx)
        })

    return {
        "true_value": tv,
        "approx_value": av,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "percent_relative_error": percent_relative_error,
        "true_percent_relative_error": true_percent_relative_error,
        "approx_percent_relative_error": approx_percent_relative_error,
        "roundoff_demo": roundoff_demo,
        "truncation_demo": truncation_demo
    }
