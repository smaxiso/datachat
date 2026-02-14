"""
FastAPI application - REST API interface.

This module provides HTTP endpoints for the GenAI data platform.
"""

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
from loguru import logger
from datetime import timedelta
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv(override=True)

from src.connectors.factory import ConnectorFactory
from src.llm.factory import LLMFactory
from src.llm.base import LLMConfig
from src.orchestration.query_orchestrator import QueryOrchestrator
from src.auth.schemas import Token, User
from src.auth.service import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.auth.dependencies import get_current_active_user

# ... (existing imports)

# Pydantic models for API
class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    question: str = Field(..., description="Natural language question")
    data_source: Optional[str] = Field(None, description="Data source name (future use)")


class QueryResponseModel(BaseModel):
    """Response model for query endpoint."""
    success: bool
    question: str
    sql_generated: Optional[str] = None
    row_count: Optional[int] = None
    data: Optional[List[Dict[str, Any]]] = None
    interpretation: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database_connected: bool
    llm_configured: bool


class SchemaResponse(BaseModel):
    """Schema information response."""
    source_name: str
    tables: List[str]
    schema_summary: str

# Global orchestrator instance
orchestrator: Optional[QueryOrchestrator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    # Startup
    global orchestrator
    logger.info("Initializing GenAI Data Platform...")
    
    try:
        # Initialize database connector
        connector = ConnectorFactory.create_connector()
        if not connector.connect():
            logger.error(f"Failed to connect to database using factory")
            # We continue to allow API to start, but it will be degraded
        
        # Initialize LLM provider
        try:
            llm = LLMFactory.create_provider()
            logger.info(f"LLM Provider initialized: {llm.config.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            llm = None
        
        # Initialize orchestrator
        if llm and connector:
            orchestrator = QueryOrchestrator(
                connector=connector,
                llm_provider=llm,
                max_retries=int(os.getenv('MAX_RETRIES', 3))
            )
        else:
            logger.warning("Orchestrator not initialized due to component failure")
            
        logger.info("Platform initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Don't raise, let app start in degraded mode
    
    yield
    
    # Shutdown
    logger.info("Shutting down GenAI Data Platform...")
    if orchestrator and orchestrator.connector:
        orchestrator.connector.disconnect()

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="DataChat",
    description="Natural language interface for data querying",
    version="1.0.0",
    lifespan=lifespan
)

# Instrument Prometheus
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth Router (can be moved to src/api/auth.py later if it grows)
@app.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real app, verify against DB. For now, hardcoded mock.
    # We will implement DB lookup in the next step.
    # Mock user for testing
    if form_data.username != "admin": # Mock check
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Mock password check (in real app, use verify_password(form_data.password, user.hashed_password))
    if form_data.password != "admin": 
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=User, tags=["Authentication"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "DataChat API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns system health status including database and LLM connectivity.
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not initialized"
        )
    
    db_connected = orchestrator.connector.test_connection()
    llm_configured = orchestrator.llm is not None
    
    return HealthResponse(
        status="healthy" if db_connected and llm_configured else "degraded",
        database_connected=db_connected,
        llm_configured=llm_configured
    )


@app.get("/api/schema", response_model=SchemaResponse, tags=["Schema"])
async def get_schema(current_user: User = Depends(get_current_active_user)):
    """
    Get database schema information.
    
    Returns list of tables and detailed schema summary.
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not initialized"
        )
    
    try:
        schema = orchestrator.connector.get_schema()
        schema_summary = orchestrator.get_schema_summary()
        
        return SchemaResponse(
            source_name=schema.source_name,
            tables=[table.name for table in schema.tables],
            schema_summary=schema_summary
        )
    except Exception as e:
        logger.error(f"Error retrieving schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/query", response_model=QueryResponseModel, tags=["Query"])
async def execute_query(request: QueryRequest, current_user: User = Depends(get_current_active_user)):
    """
    Execute a natural language query.
    
    Takes a natural language question, generates SQL, executes it,
    and returns results with interpretation.
    
    Args:
        request: Query request with natural language question
        
    Returns:
        Query results with SQL, data, and interpretation
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not initialized"
        )
    
    try:
        # Process the question
        response = orchestrator.process_question(request.question)
        
        # Convert DataFrame to list of dicts if present
        data_list = None
        if response.data is not None and not response.data.empty:
            data_list = response.data.to_dict('records')
        
        return QueryResponseModel(
            success=response.success,
            question=response.question,
            sql_generated=response.sql_generated,
            row_count=len(response.data) if response.data is not None else None,
            data=data_list,
            interpretation=response.interpretation,
            error_message=response.error_message,
            metadata=response.metadata
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/sources", tags=["Sources"])
async def list_sources():
    """
    List configured data sources.
    
    Currently returns single configured source.
    Future: Support multiple sources.
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not initialized"
        )
    
    schema = orchestrator.connector.get_schema()
    
    return {
        "sources": [
            {
                "name": schema.source_name,
                "type": schema.source_type,
                "status": orchestrator.connector.get_status().value,
                "table_count": len(schema.tables)
            }
        ]
    }


@app.get("/api/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Get system performance metrics.
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not initialized"
        )
    
    return orchestrator.metrics.get_summary()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
