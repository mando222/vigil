"""API endpoints for integration compatibility checking and management."""

from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from services.integration_compatibility_service import get_compatibility_service

router = APIRouter()
logger = logging.getLogger(__name__)


class PackageInstallRequest(BaseModel):
    """Request to install a package."""
    package_name: str
    version: Optional[str] = None


class PackageActionRequest(BaseModel):
    """Request to perform an action on a package."""
    package_name: str


@router.get("/compatibility/status")
async def get_compatibility_status():
    """
    Get compatibility status for all integrations.
    
    Returns:
        Dictionary of integration statuses
    """
    try:
        service = get_compatibility_service()
        statuses = service.get_all_statuses()
        system_info = service.get_system_info()
        
        return {
            "system": system_info,
            "integrations": statuses
        }
    except Exception as e:
        logger.error(f"Error getting compatibility status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compatibility/status/{integration_id}")
async def get_integration_compatibility(integration_id: str):
    """
    Get compatibility status for a specific integration.
    
    Args:
        integration_id: Integration identifier
    
    Returns:
        Integration status
    """
    try:
        service = get_compatibility_service()
        status = service.get_integration_status(integration_id)
        
        if status.get('status') == 'unknown':
            raise HTTPException(status_code=404, detail=f"Integration '{integration_id}' not found")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration compatibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compatibility/install")
async def install_package(request: PackageInstallRequest):
    """
    Install or upgrade a package.
    
    Args:
        request: Package install request
    
    Returns:
        Installation result
    """
    try:
        service = get_compatibility_service()
        success, message = service.install_package(
            request.package_name,
            request.version
        )
        
        if success:
            return {
                "success": True,
                "message": message,
                "package": request.package_name
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compatibility/upgrade")
async def upgrade_package(request: PackageActionRequest):
    """
    Upgrade a package to the latest version.
    
    Args:
        request: Package action request
    
    Returns:
        Upgrade result
    """
    try:
        service = get_compatibility_service()
        success, message = service.upgrade_package(request.package_name)
        
        if success:
            return {
                "success": True,
                "message": message,
                "package": request.package_name
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compatibility/uninstall")
async def uninstall_package(request: PackageActionRequest):
    """
    Uninstall a package.
    
    Args:
        request: Package action request
    
    Returns:
        Uninstallation result
    """
    try:
        service = get_compatibility_service()
        success, message = service.uninstall_package(request.package_name)
        
        if success:
            return {
                "success": True,
                "message": message,
                "package": request.package_name
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compatibility/system")
async def get_system_info():
    """
    Get system information.
    
    Returns:
        System information including Python version
    """
    try:
        service = get_compatibility_service()
        return service.get_system_info()
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

