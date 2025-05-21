# backend/mcp/server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.mcp.routes.servers import router as servers_router
from backend.mcp.routes.llm_routes import router as llm_router

from backend.mcp.routes.data_routes import router as data_router
from backend.mcp.routes.model_source_routes import router as model_source_router

from backend.mcp.routes.prompt_routes import router as prompt_router
from backend.mcp.routes.model_prompt_routes import router as model_prompt_router

from backend.mcp.routes.tool_routes import router as tool_router
from backend.mcp.routes.model_tool_routes import router as model_tool_router

from backend.mcp.routes.memory_routes import router as memory_router
from backend.mcp.routes.sampling_routes import router as sampling_router
from backend.mcp.routes.security_routes import router as security_router
from backend.mcp.routes.log_routes import router as log_router

from backend.mcp.routes.llm_load_routes import router as llm_load_router

from backend.mcp.routes.integrations.spotify_routes import router as spotify_router

app = FastAPI(title="Arielle MCP Control Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(servers_router, prefix="/mcp", tags=["MCP"])
app.include_router(llm_router, prefix="/mcp", tags=["LLM"])
app.include_router(data_router, prefix="/mcp", tags=["Data"])
app.include_router(model_source_router, prefix="/mcp", tags=["Model Source"])
app.include_router(prompt_router, prefix="/mcp", tags=["Prompt"])
app.include_router(model_prompt_router, prefix="/mcp", tags=["Model Prompt"])
app.include_router(tool_router, prefix="/mcp", tags=["Tool"])
app.include_router(model_tool_router, prefix="/mcp", tags=["Model Tool"])
app.include_router(memory_router, prefix="/mcp", tags=["Memory"])
app.include_router(sampling_router, prefix="/mcp", tags=["Sampling"])
app.include_router(security_router, prefix="/mcp", tags=["Security"])
app.include_router(log_router, prefix="/mcp", tags=["Logs"])

app.include_router(llm_load_router, prefix="/mcp", tags=["LLM Load"])

app.include_router(spotify_router, prefix="/mcp", tags=["Spotify Integration"])