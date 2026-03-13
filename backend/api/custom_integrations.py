"""Custom Integration Builder API - AI-powered integration generation."""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
import json
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.custom_integration_service import CustomIntegrationService

router = APIRouter()
logger = logging.getLogger(__name__)


class CustomIntegrationRequest(BaseModel):
    """Request to generate a custom integration from documentation."""
    documentation: str
    integration_name: Optional[str] = None
    category: Optional[str] = "Custom"
    conversation_history: Optional[list] = None
    user_response: Optional[str] = None


class CustomIntegrationResponse(BaseModel):
    """Response containing generated integration details."""
    success: bool
    needs_clarification: Optional[bool] = False
    integration_id: Optional[str] = None
    integration_name: Optional[str] = None
    metadata: Optional[dict] = None
    server_code: Optional[str] = None
    message: Optional[str] = None
    conversation_history: Optional[list] = None
    error: Optional[str] = None


@router.post("/generate")
async def generate_custom_integration(request: CustomIntegrationRequest):
    """
    Generate a custom integration from API/MCP documentation using Claude AI.
    
    Args:
        request: Custom integration request containing documentation
    
    Returns:
        Generated integration metadata and server code, or questions if clarification needed
    """
    try:
        service = CustomIntegrationService()
        
        # If there's a user response, add it to the conversation
        conversation_history = request.conversation_history or []
        if request.user_response:
            conversation_history.append({"role": "user", "content": request.user_response})
        
        # Generate the integration
        result = await service.generate_integration(
            documentation=request.documentation,
            integration_name=request.integration_name,
            category=request.category,
            conversation_history=conversation_history if conversation_history else None
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=result.get("error", "Failed to generate integration")
            )
        
        # Return the result as-is (let FastAPI handle the dict -> JSON conversion)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating custom integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/upload")
async def generate_from_file(
    file: UploadFile = File(...),
    integration_name: Optional[str] = Form(None),
    category: Optional[str] = Form("Custom")
):
    """
    Generate a custom integration from an uploaded documentation file.
    
    Args:
        file: Documentation file (txt, md, pdf, etc.)
        integration_name: Optional custom name for the integration
        category: Integration category
    
    Returns:
        Generated integration metadata and server code
    """
    try:
        # Read file content
        content = await file.read()
        
        # Try to decode as text
        try:
            documentation = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                documentation = content.decode('latin-1')
            except Exception as e:
                logger.error(f"Failed to decode uploaded file: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Unable to decode file. Please upload a text-based document."
                )
        
        # Generate integration
        service = CustomIntegrationService()
        result = await service.generate_integration(
            documentation=documentation,
            integration_name=integration_name,
            category=category
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to generate integration")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating integration from file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_custom_integration(
    integration_id: str,
    metadata: dict,
    server_code: str
):
    """
    Save a generated custom integration to the system.
    
    Args:
        integration_id: Unique integration identifier
        metadata: Integration metadata for UI
        server_code: Generated MCP server Python code
    
    Returns:
        Success status
    """
    try:
        service = CustomIntegrationService()
        result = await service.save_integration(
            integration_id=integration_id,
            metadata=metadata,
            server_code=server_code
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to save integration")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving custom integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_custom_integrations():
    """
    List all custom integrations.
    
    Returns:
        List of custom integration metadata
    """
    try:
        service = CustomIntegrationService()
        custom_integrations = service.list_custom_integrations()
        
        return {
            "success": True,
            "integrations": custom_integrations
        }
    
    except Exception as e:
        logger.error(f"Error listing custom integrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{integration_id}")
async def delete_custom_integration(integration_id: str):
    """
    Delete a custom integration.
    
    Args:
        integration_id: Integration identifier to delete
    
    Returns:
        Success status
    """
    try:
        service = CustomIntegrationService()
        result = await service.delete_integration(integration_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Integration not found")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting custom integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{integration_id}/validate")
async def validate_custom_integration(integration_id: str):
    """
    Validate a custom integration's server code.
    
    Args:
        integration_id: Integration identifier
    
    Returns:
        Validation results
    """
    try:
        service = CustomIntegrationService()
        result = await service.validate_integration(integration_id)
        
        return result
    
    except Exception as e:
        logger.error(f"Error validating custom integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

