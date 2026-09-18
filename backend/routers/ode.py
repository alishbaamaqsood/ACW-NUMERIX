from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import math

router = APIRouter()

def safe_eval(expr: str, x: float, y: float) -> float:
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
    allowed['x'] = x
    allowed['y'] = y
    return eval(expr, {"__builtins__": {}}, allowed)

class ODEInput(BaseModel):
    dydx: str      # expression in x, y
    x0: float
    y0: float
    h: float
    xn: float

@router.post("/euler")
def euler(data: ODEInput):
    try:
        x, y, h = data.x0, data.y0, data.h
        steps = []
        while round(x, 10) < round(data.xn, 10):
            f = safe_eval(data.dydx, x, y)
            y_new = y + h * f
            steps.append({"x": x, "y": y, "f(x,y)": f, "y_new": y_new})
            x = round(x + h, 10)
            y = y_new
        return {"result": y, "steps": steps}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/improved_euler")
def improved_euler(data: ODEInput):
    try:
        x, y, h = data.x0, data.y0, data.h
        steps = []
        while round(x, 10) < round(data.xn, 10):
            k1 = safe_eval(data.dydx, x, y)
            y_pred = y + h * k1
            k2 = safe_eval(data.dydx, x + h, y_pred)
            y_new = y + h * (k1 + k2) / 2
            steps.append({
                "x": x, "y": y,
                "k1": k1, "y_pred": y_pred,
                "k2": k2, "y_new": y_new
            })
            x = round(x + h, 10)
            y = y_new
        return {"result": y, "steps": steps}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rk4")
def runge_kutta_4(data: ODEInput):
    try:
        x, y, h = data.x0, data.y0, data.h
        steps = []
        while round(x, 10) < round(data.xn, 10):
            k1 = safe_eval(data.dydx, x, y)
            k2 = safe_eval(data.dydx, x + h/2, y + h*k1/2)
            k3 = safe_eval(data.dydx, x + h/2, y + h*k2/2)
            k4 = safe_eval(data.dydx, x + h, y + h*k3)
            phi = (k1 + 2*k2 + 2*k3 + k4) / 6
            y_new = y + h * phi
            steps.append({
                "x": x, "y": y,
                "k1": k1, "k2": k2, "k3": k3, "k4": k4,
                "phi": phi, "y_new": y_new
            })
            x = round(x + h, 10)
            y = y_new
        return {"result": y, "steps": steps}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
