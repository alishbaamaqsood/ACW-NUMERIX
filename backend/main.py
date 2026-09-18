from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import errors, rootfinder, interpolation, differentiation, integration, ode, linear, chatbot

app = FastAPI(title="NumeriX API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(errors.router, prefix="/api/errors", tags=["Error Analysis"])
app.include_router(rootfinder.router, prefix="/api/roots", tags=["Root Finding"])
app.include_router(interpolation.router, prefix="/api/interpolation", tags=["Interpolation"])
app.include_router(differentiation.router, prefix="/api/differentiation", tags=["Differentiation"])
app.include_router(integration.router, prefix="/api/integration", tags=["Integration"])
app.include_router(ode.router, prefix="/api/ode", tags=["ODE Solver"])
app.include_router(linear.router, prefix="/api/linear", tags=["Linear Systems"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["AI Assistant"])

@app.get("/")
def root():
    return {"message": "NumeriX API is running"}
