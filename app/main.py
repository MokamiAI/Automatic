from fastapi import FastAPI
from app.api.routes import router
from app.services.auto_processor import process_clients
import threading

app = FastAPI(title="Nerve Engine")

app.include_router(router)


# Run automatic processor in background
@app.on_event("startup")
def start_background_processor():
    thread = threading.Thread(target=process_clients, daemon=True)
    thread.start()
