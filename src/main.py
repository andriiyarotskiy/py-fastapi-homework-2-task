from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import PlainTextResponse, JSONResponse

from routes import movie_router

app = FastAPI(title="Movies homework", description="Description of project")

api_version_prefix = "/api/v1"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if (
            (request.method == "POST" or request.method == "PATCH")
            and request.url.path.startswith("/api/v1/theater/movies")
    ):
        return JSONResponse(status_code=400, content={"detail": "Invalid input data."})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


app.include_router(
    movie_router, prefix=f"{api_version_prefix}/theater", tags=["theater"]
)
