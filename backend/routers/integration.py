from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import math

router = APIRouter()

def safe_eval(expr: str, x: float) -> float:
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
    allowed['x'] = x
    return eval(expr, {"__builtins__": {}}, allowed)

class IntegrationInput(BaseModel):
    fx: Optional[str] = None
    x_vals: Optional[List[float]] = None
    y_vals: Optional[List[float]] = None
    a: Optional[float] = None
    b: Optional[float] = None
    n: int = 4

def get_xy(data: IntegrationInput):
    if data.fx and data.a is not None and data.b is not None:
        n = data.n
        h = (data.b - data.a) / n
        xs = [data.a + i * h for i in range(n + 1)]
        ys = [safe_eval(data.fx, xi) for xi in xs]
        return xs, ys, h
    elif data.x_vals and data.y_vals:
        xs = data.x_vals
        ys = data.y_vals
        h = xs[1] - xs[0]
        return xs, ys, h
    else:
        raise ValueError("Provide either fx with a,b or x_vals with y_vals")

@router.post("/trapezoidal")
def trapezoidal(data: IntegrationInput):
    try:
        xs, ys, h = get_xy(data)
        n = len(xs) - 1
        result = ys[0] + ys[-1]
        for i in range(1, n):
            result += 2 * ys[i]
        result *= h / 2
        segments = [{"x0": xs[i], "x1": xs[i+1], "y0": ys[i], "y1": ys[i+1],
                     "area": h * (ys[i] + ys[i+1]) / 2} for i in range(n)]
        return {"result": result, "h": h, "n": n, "x_vals": xs, "y_vals": ys, "segments": segments}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/simpson_third")
def simpson_third(data: IntegrationInput):
    try:
        xs, ys, h = get_xy(data)
        n = len(xs) - 1
        if n % 2 != 0:
            raise HTTPException(status_code=400, detail="n must be even for Simpson's 1/3 rule")
        result = ys[0] + ys[-1]
        for i in range(1, n):
            result += (4 if i % 2 == 1 else 2) * ys[i]
        result *= h / 3
        return {"result": result, "h": h, "n": n, "x_vals": xs, "y_vals": ys}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/simpson_three_eighth")
def simpson_three_eighth(data: IntegrationInput):
    try:
        xs, ys, h = get_xy(data)
        n = len(xs) - 1
        if n % 3 != 0:
            raise HTTPException(status_code=400, detail="n must be multiple of 3 for Simpson's 3/8 rule")
        result = ys[0] + ys[-1]
        for i in range(1, n):
            result += (2 if i % 3 == 0 else 3) * ys[i]
        result *= 3 * h / 8
        return {"result": result, "h": h, "n": n, "x_vals": xs, "y_vals": ys}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/unequal_segments")
def unequal_segments(data: IntegrationInput):
    try:
        if not data.x_vals or not data.y_vals:
            raise HTTPException(status_code=400, detail="x_vals and y_vals required for unequal segments")
        xs, ys = data.x_vals, data.y_vals
        result = 0
        segments = []
        for i in range(len(xs) - 1):
            hi = xs[i+1] - xs[i]
            area = hi * (ys[i] + ys[i+1]) / 2
            result += area
            segments.append({"x0": xs[i], "x1": xs[i+1], "h": hi, "y0": ys[i], "y1": ys[i+1], "area": area})
        return {"result": result, "x_vals": xs, "y_vals": ys, "segments": segments}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
