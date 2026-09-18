from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import math

router = APIRouter()

def safe_eval(expr: str, x: float) -> float:
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
    allowed['x'] = x
    allowed['e'] = math.e
    return eval(expr, {"__builtins__": {}}, allowed)

class BisectionInput(BaseModel):
    fx: str
    a: float
    b: float
    tol: float = 1e-6
    max_iter: int = 50

class NewtonInput(BaseModel):
    fx: str
    dfx: str
    x0: float
    tol: float = 1e-6
    max_iter: int = 50

class FixedPointInput(BaseModel):
    gx: str
    x0: float
    tol: float = 1e-6
    max_iter: int = 50

@router.post("/bisection")
def bisection(data: BisectionInput):
    try:
        a, b = data.a, data.b
        fa = safe_eval(data.fx, a)
        fb = safe_eval(data.fx, b)
        if fa * fb > 0:
            raise HTTPException(status_code=400, detail="f(a) and f(b) must have opposite signs")
        iterations = []
        for i in range(data.max_iter):
            c = (a + b) / 2
            fc = safe_eval(data.fx, c)
            ea = abs(b - a) / 2
            iterations.append({"iter": i+1, "a": a, "b": b, "c": c, "fa": safe_eval(data.fx,a), "fb": safe_eval(data.fx,b), "fc": fc, "error": ea})
            if ea < data.tol or fc == 0:
                break
            if fa * fc < 0:
                b = c
                fb = fc
            else:
                a = c
                fa = fc
        return {"root": c, "iterations": iterations, "converged": ea < data.tol}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/false_position")
def false_position(data: BisectionInput):
    try:
        a, b = data.a, data.b
        fa = safe_eval(data.fx, a)
        fb = safe_eval(data.fx, b)
        if fa * fb > 0:
            raise HTTPException(status_code=400, detail="f(a) and f(b) must have opposite signs")
        iterations = []
        c_prev = None
        for i in range(data.max_iter):
            fa = safe_eval(data.fx, a)
            fb = safe_eval(data.fx, b)
            c = b - fb * (b - a) / (fb - fa)
            fc = safe_eval(data.fx, c)
            ea = abs(c - c_prev) / abs(c) * 100 if c_prev is not None and c != 0 else 100
            iterations.append({"iter": i+1, "a": a, "b": b, "c": c, "fa": fa, "fb": fb, "fc": fc, "error": ea})
            if abs(fc) < data.tol:
                break
            if fa * fc < 0:
                b = c
            else:
                a = c
            c_prev = c
        return {"root": c, "iterations": iterations, "converged": abs(fc) < data.tol}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/newton_raphson")
def newton_raphson(data: NewtonInput):
    try:
        x = data.x0
        iterations = []
        for i in range(data.max_iter):
            fx = safe_eval(data.fx, x)
            dfx = safe_eval(data.dfx, x)
            if dfx == 0:
                raise HTTPException(status_code=400, detail="Derivative is zero")
            x_new = x - fx / dfx
            ea = abs(x_new - x) / abs(x_new) * 100 if x_new != 0 else 100
            iterations.append({"iter": i+1, "x": x, "fx": fx, "dfx": dfx, "x_new": x_new, "error": ea})
            x = x_new
            if ea < data.tol * 100:
                break
        return {"root": x, "iterations": iterations, "converged": ea < data.tol * 100}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/fixed_point")
def fixed_point(data: FixedPointInput):
    try:
        x = data.x0
        iterations = []
        for i in range(data.max_iter):
            x_new = safe_eval(data.gx, x)
            ea = abs(x_new - x) / abs(x_new) * 100 if x_new != 0 else 100
            iterations.append({"iter": i+1, "x": x, "x_new": x_new, "gx": x_new, "error": ea})
            x = x_new
            if ea < data.tol * 100:
                break
        return {"root": x, "iterations": iterations, "converged": ea < data.tol * 100}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
