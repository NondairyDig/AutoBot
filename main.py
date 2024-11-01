from fastapi import FastAPI
from fastapi.responses import RedirectResponse, FileResponse
from .routers import automations as automations_router
from .utils import auth
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from .automations import automations # Important for automations to be able run


disable_warnings()
disable_warnings(InsecureRequestWarning)
app = FastAPI(redoc_url=None, swagger_ui_parameters={
                                "tagsSorter": "alpha",
                                "deepLinking": True
                                })
app.include_router(automations_router.router)
app.include_router(auth.router)


@app.get('/', tags=["Main"])
async def index():
    return RedirectResponse(url="/docs")

@app.get("/assets/{file:path}", tags=["Main"])
async def favicon(file):
    file - file.split("/*")[-1]
    return FileResponse(f"AutoBot/assets/{file}")


@app.get("/health", tags=["Main"])
async def health_checks():
    return {"health": "ok!"}