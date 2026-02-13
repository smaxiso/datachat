"""
FastAPI application - REST API interface.

This module provides HTTP endpoints for the GenAI data platform.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv(override=True)

from src.connectors.factory import ConnectorFactory
from src.llm.factory import LLMFactory
from src.llm.base import LLMConfig
from src.orchestration.query_orchestrator import QueryOrchestrator


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


# Initialize FastAPI app
app = FastAPI(
    title="DataChat",
    description="Natural language interface for data querying",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance (will be initialized on startup)
orchestrator: Optional[QueryOrchestrator] = None


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    global orchestrator
    
    logger.info("Initializing GenAI Data Platform...")
    
    try:
        # Initialize database connector using factory
        connector = ConnectorFactory.create_connector()
        if not connector.connect():
            logger.error(f"Failed to connect to database using factory")
            return
        
        # Initialize LLM provider using factory
        # Factory handles loading config from env if not provided
        try:
            llm = LLMFactory.create_provider()
            logger.info(f"LLM Provider initialized: {llm.config.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            # We don't return here to allow API to start even if LLM fails (health check will show degraded)
            llm = None
        
        # Initialize orchestrator
        if llm:
            orchestrator = QueryOrchestrator(
                connector=connector,
                llm_provider=llm,
                max_retries=int(os.getenv('MAX_RETRIES', 3))
            )
        else:
            logger.warning("Orchestrator not initialized due to LLM failure")
        
        logger.info("Platform initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down GenAI Data Platform...")
    if orchestrator and orchestrator.connector:
        orchestrator.connector.disconnect()


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
async def get_schema():
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
async def execute_query(request: QueryRequest):
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
