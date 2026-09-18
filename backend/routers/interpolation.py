from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

class InterpolationInput(BaseModel):
    x_vals: List[float]
    y_vals: List[float]
    target: float

def forward_diff_table(y):
    n = len(y)
    table = [y[:]]
    for k in range(1, n):
        row = [table[k-1][i+1] - table[k-1][i] for i in range(n-k)]
        table.append(row)
    return table

@router.post("/newton_forward")
def newton_forward(data: InterpolationInput):
    try:
        x, y, xt = data.x_vals, data.y_vals, data.target
        n = len(x)
        h = x[1] - x[0]
        table = forward_diff_table(y)
        s = (xt - x[0]) / h
        result = y[0]
        s_term = 1
        steps = [{"term": 0, "value": y[0], "cumulative": y[0]}]
        for k in range(1, n):
            s_term *= (s - (k-1)) / k
            term = s_term * table[k][0]
            result += term
            steps.append({"term": k, "delta": table[k][0], "s_term": s_term, "contribution": term, "cumulative": result})
        diff_table = [[table[i][j] if j < len(table[i]) else None for i in range(n)] for j in range(n)]
        return {"result": result, "steps": steps, "diff_table": table, "s": s}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/newton_backward")
def newton_backward(data: InterpolationInput):
    try:
        x, y, xt = data.x_vals, data.y_vals, data.target
        n = len(x)
        h = x[1] - x[0]
        table = forward_diff_table(y)
        s = (xt - x[-1]) / h
        result = y[-1]
        s_term = 1
        steps = [{"term": 0, "value": y[-1], "cumulative": y[-1]}]
        for k in range(1, n):
            s_term *= (s + (k-1)) / k
            delta_val = table[k][-1] if k < len(table) and len(table[k]) > 0 else 0
            term = s_term * delta_val
            result += term
            steps.append({"term": k, "delta": delta_val, "s_term": s_term, "contribution": term, "cumulative": result})
        return {"result": result, "steps": steps, "s": s}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/divided_difference")
def divided_difference(data: InterpolationInput):
    try:
        x, y, xt = data.x_vals, data.y_vals, data.target
        n = len(x)
        coef = y[:]
        table = [y[:]]
        for k in range(1, n):
            new_row = []
            for i in range(n - k):
                val = (coef[i+1] - coef[i]) / (x[i+k] - x[i])
                new_row.append(val)
            table.append(new_row[:])
            coef = new_row
        # evaluate
        result = table[0][0]
        steps = [{"term": 0, "coef": table[0][0], "product": 1, "cumulative": result}]
        product = 1
        for k in range(1, n):
            product *= (xt - x[k-1])
            term = table[k][0] * product
            result += term
            steps.append({"term": k, "coef": table[k][0], "product": product, "contribution": term, "cumulative": result})
        return {"result": result, "steps": steps, "table": table}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/lagrange")
def lagrange(data: InterpolationInput):
    try:
        x, y, xt = data.x_vals, data.y_vals, data.target
        n = len(x)
        result = 0
        basis_values = []
        for i in range(n):
            num = 1
            den = 1
            for j in range(n):
                if j != i:
                    num *= (xt - x[j])
                    den *= (x[i] - x[j])
            L = num / den
            contrib = L * y[i]
            result += contrib
            basis_values.append({"i": i, "xi": x[i], "yi": y[i], "L": L, "contribution": contrib})
        return {"result": result, "basis_values": basis_values}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
