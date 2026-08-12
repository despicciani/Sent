"""Sentinela — Ponto de entrada da aplicação."""
import uvicorn
from api.routes import app

if __name__ == "__main__":
    uvicorn.run("api.routes:app", host="0.0.0.0", port=8000, reload=True)