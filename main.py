from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
from collections import defaultdict

app = FastAPI()

# === Middleware 1: Request Context ===
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Reuse inbound X-Request-ID or generate new UUID4
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        # Do not set response header here — handled in endpoint
        response = await call_next(request)
        return response

# === Middleware 2: Scoped CORS ===
allowed_origins = [
    "https://app-7tq7pw.example.com",      # your assigned origin
    "https://exam.sanand.workers.dev"      # exam page origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Middleware 3: Per-client Rate Limiting ===
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit=12, window=10):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            # prune old requests outside window
            self.clients[client_id] = [t for t in self.clients[client_id] if now - t < self.window]
            if len(self.clients[client_id]) >= self.limit:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            self.clients[client_id].append(now)
        return await call_next(request)

# Attach middlewares
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware, limit=12, window=10)

# === Endpoint: GET /ping ===
@app.get("/ping")
def ping(request: Request):
    # Reuse inbound X-Request-ID if present, otherwise generate new
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = JSONResponse(
        content={
            "email": "24f2004508@ds.study.iitm.ac.in",
            "request_id": request_id,
        }
    )
    # Echo the same ID back in the header with exact casing
    response.headers["X-Request-ID"] = request_id
    return response
