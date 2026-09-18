from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

class DiffInput(BaseModel):
    x_vals: List[float]
    y_vals: List[float]
    target: float
    order: int = 1  # 1 or 2

def forward_diff_table(y):
    n = len(y)
    table = [y[:]]
    for k in range(1, n):
        row = [table[k-1][i+1] - table[k-1][i] for i in range(n-k)]
        table.append(row)
    return table

@router.post("/forward")
def forward_differentiation(data: DiffInput):
    try:
        x, y = data.x_vals, data.y_vals
        h = x[1] - x[0]
        table = forward_diff_table(y)
        s = (data.target - x[0]) / h
        # First derivative using Newton's forward formula
        dy = table[1][0]
        for k in range(2, len(table)):
            if len(table[k]) == 0: break
            coeff = 0
            if k == 2: coeff = (2*s - 1) / 2
            elif k == 3: coeff = (3*s**2 - 6*s + 2) / 6
            elif k == 4: coeff = (4*s**3 - 18*s**2 + 22*s - 6) / 24
            dy += coeff * table[k][0]
        dy /= h
        # Second derivative
        d2y = table[2][0] if len(table) > 2 else 0
        for k in range(3, len(table)):
            if len(table[k]) == 0: break
            coeff = 0
            if k == 3: coeff = s - 1
            elif k == 4: coeff = (6*s**2 - 18*s + 11) / 12
            d2y += coeff * table[k][0]
        d2y /= h**2

        return {
            "first_derivative": dy,
            "second_derivative": d2y,
            "h": h,
            "s": s,
            "diff_table": table,
            "x_vals": x,
            "y_vals": y
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/backward")
def backward_differentiation(data: DiffInput):
    try:
        x, y = data.x_vals, data.y_vals
        h = x[1] - x[0]
        table = forward_diff_table(y)
        s = (data.target - x[-1]) / h
        # First derivative using backward formula
        dy = table[1][-1]
        for k in range(2, len(table)):
            if len(table[k]) == 0: break
            coeff = 0
            if k == 2: coeff = (2*s + 1) / 2
            elif k == 3: coeff = (3*s**2 + 6*s + 2) / 6
            elif k == 4: coeff = (4*s**3 + 18*s**2 + 22*s + 6) / 24
            dy += coeff * table[k][-1]
        dy /= h
        # Second derivative
        d2y = table[2][-1] if len(table) > 2 else 0
        for k in range(3, len(table)):
            if len(table[k]) == 0: break
            coeff = 0
            if k == 3: coeff = s + 1
            d2y += coeff * table[k][-1]
        d2y /= h**2

        return {
            "first_derivative": dy,
            "second_derivative": d2y,
            "h": h,
            "s": s,
            "diff_table": table,
            "x_vals": x,
            "y_vals": y
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
