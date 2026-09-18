from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

class LinearInput(BaseModel):
    matrix: List[List[float]]  # A
    vector: List[float]         # b

def forward_substitution(L, b):
    n = len(b)
    y = [0.0] * n
    for i in range(n):
        s = sum(L[i][j] * y[j] for j in range(i))
        y[i] = (b[i] - s) / L[i][i]
    return y

def backward_substitution(U, y):
    n = len(y)
    x = [0.0] * n
    for i in range(n-1, -1, -1):
        s = sum(U[i][j] * x[j] for j in range(i+1, n))
        x[i] = (y[i] - s) / U[i][i]
    return x

@router.post("/doolittle")
def doolittle(data: LinearInput):
    try:
        A = [row[:] for row in data.matrix]
        b = data.vector[:]
        n = len(A)
        L = [[0.0]*n for _ in range(n)]
        U = [[0.0]*n for _ in range(n)]
        steps = []

        for i in range(n):
            L[i][i] = 1.0  # Doolittle: diagonal of L = 1

        for k in range(n):
            for j in range(k, n):
                U[k][j] = A[k][j] - sum(L[k][r] * U[r][j] for r in range(k))
            for i in range(k+1, n):
                if U[k][k] == 0:
                    raise HTTPException(status_code=400, detail="Zero pivot encountered")
                L[i][k] = (A[i][k] - sum(L[i][r] * U[r][k] for r in range(k))) / U[k][k]
            steps.append({
                "step": k+1,
                "L_state": [row[:] for row in L],
                "U_state": [row[:] for row in U]
            })

        y = forward_substitution(L, b)
        x = backward_substitution(U, y)
        return {"L": L, "U": U, "y": y, "x": x, "steps": steps, "method": "Doolittle"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/crout")
def crout(data: LinearInput):
    try:
        A = [row[:] for row in data.matrix]
        b = data.vector[:]
        n = len(A)
        L = [[0.0]*n for _ in range(n)]
        U = [[0.0]*n for _ in range(n)]
        steps = []

        for i in range(n):
            U[i][i] = 1.0  # Crout: diagonal of U = 1

        for k in range(n):
            for i in range(k, n):
                L[i][k] = A[i][k] - sum(L[i][r] * U[r][k] for r in range(k))
            for j in range(k+1, n):
                if L[k][k] == 0:
                    raise HTTPException(status_code=400, detail="Zero pivot encountered")
                U[k][j] = (A[k][j] - sum(L[k][r] * U[r][j] for r in range(k))) / L[k][k]
            steps.append({
                "step": k+1,
                "L_state": [row[:] for row in L],
                "U_state": [row[:] for row in U]
            })

        y = forward_substitution(L, b)
        x = backward_substitution(U, y)
        return {"L": L, "U": U, "y": y, "x": x, "steps": steps, "method": "Crout"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
