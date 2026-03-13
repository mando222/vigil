"""MCP Server management API endpoints."""

from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.mcp_service import MCPService

router = APIRouter()
mcp_service = MCPService()


class ServerControl(BaseModel):
    """Server control request."""
    action: str  # start or stop


class ServerEnabledRequest(BaseModel):
    """Request body for enabling/disabling a server."""
    enabled: bool


@router.get("/servers")
async def list_servers():
    """
    Get list of all MCP servers.
    
    Returns:
        List of server names
    """
    servers = mcp_service.list_servers()
    return {"servers": servers}


@router.get("/servers/status")
async def get_servers_status():
    """
    Get status of all MCP servers including enabled state.
    
    Returns:
        List of server status objects with enabled flag
    """
    statuses_dict = mcp_service.get_all_statuses()
    enabled_dict = mcp_service.get_all_enabled_states()
    # Convert dict to list of objects for frontend
    statuses_list = [
        {"name": name, "status": status, "enabled": enabled_dict.get(name, False)}
        for name, status in statuses_dict.items()
    ]
    return {"statuses": statuses_list}


@router.get("/servers/enabled")
async def get_enabled_states():
    """
    Get enabled/disabled state for all MCP servers.
    
    Returns:
        Dictionary of server_name -> enabled boolean
    """
    return {"enabled": mcp_service.get_all_enabled_states()}


@router.put("/servers/{server_name}/enabled")
async def set_server_enabled(server_name: str, request: ServerEnabledRequest):
    """
    Enable or disable an MCP server.
    
    When disabled, the server will not start via start-all and
    cannot be started individually. If currently running and being
    disabled, the server will be stopped.
    
    Args:
        server_name: Name of the server
        request: Body with enabled boolean
    
    Returns:
        Success status
    """
    success = mcp_service.set_server_enabled(server_name, request.enabled)
    if not success:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # If disabling a running server, stop it
    if not request.enabled:
        status = mcp_service.get_server_status(server_name)
        if status == "running":
            mcp_service.stop_server(server_name)
    
    return {
        "success": True,
        "server": server_name,
        "enabled": request.enabled,
        "message": f"Server {server_name} {'enabled' if request.enabled else 'disabled'}"
    }


@router.get("/connections/status")
async def get_connections_status():
    """
    Get persistent connection status for all MCP servers.
    
    Returns:
        Connection status for each server
    """
    from services.mcp_client import get_mcp_client
    
    mcp_client = get_mcp_client()
    if not mcp_client:
        return {"error": "MCP client not available", "connections": {}}
    
    status = mcp_client.get_connection_status()
    connections_list = [
        {"name": name, "connected": connected}
        for name, connected in status.items()
    ]
    
    return {
        "connections": connections_list,
        "total": len(status),
        "connected": sum(1 for connected in status.values() if connected)
    }


@router.get("/servers/{server_name}/status")
async def get_server_status(server_name: str):
    """
    Get status of a specific server.
    
    Args:
        server_name: Name of the server
    
    Returns:
        Server status
    """
    status = mcp_service.get_server_status(server_name)
    if status is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    return {"server": server_name, "status": status}


@router.post("/servers/{server_name}/start")
async def start_server(server_name: str):
    """
    Start an MCP server.
    
    Args:
        server_name: Name of the server to start
    
    Returns:
        Success status
    """
    success = mcp_service.start_server(server_name)
    
    if not success:
        # Check if it's a stdio server
        server = mcp_service.servers.get(server_name)
        if server and server.server_type == "stdio":
            return {
                "success": False,
                "message": "This server is stdio-based and designed for advanced MCP integration"
            }
        raise HTTPException(status_code=500, detail="Failed to start server")
    
    return {"success": True, "message": f"Server {server_name} started"}


@router.post("/servers/{server_name}/stop")
async def stop_server(server_name: str):
    """
    Stop an MCP server.
    
    Args:
        server_name: Name of the server to stop
    
    Returns:
        Success status
    """
    success = mcp_service.stop_server(server_name)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop server")
    
    return {"success": True, "message": f"Server {server_name} stopped"}


@router.post("/servers/start-all")
async def start_all_servers():
    """
    Start all MCP servers.
    
    Returns:
        Results for each server
    """
    results = mcp_service.start_all()
    return {"results": results}


@router.post("/servers/stop-all")
async def stop_all_servers():
    """
    Stop all MCP servers.
    
    Returns:
        Results for each server
    """
    results = mcp_service.stop_all()
    return {"results": results}


@router.get("/servers/{server_name}/logs")
async def get_server_logs(server_name: str, lines: int = 100):
    """
    Get logs for a specific server.
    
    Args:
        server_name: Name of the server
        lines: Number of log lines to retrieve
    
    Returns:
        Server logs
    """
    logs = mcp_service.get_server_log(server_name, lines=lines)
    
    if logs == "":
        raise HTTPException(status_code=404, detail="Server not found")
    
    return {"server": server_name, "logs": logs}


@router.get("/servers/{server_name}/test")
async def test_server(server_name: str):
    """
    Test if a server is responding.
    
    Args:
        server_name: Name of the server
    
    Returns:
        Test result
    """
    is_running = mcp_service.test_server(server_name)
    
    return {
        "server": server_name,
        "is_running": is_running,
        "status": "healthy" if is_running else "not responding"
    }


@router.post("/servers/reload")
async def reload_servers():
    """
    Reload MCP server configurations from integrations.
    This picks up newly enabled/disabled integrations without restarting the backend.
    
    Returns:
        Status of reload operation
    """
    global mcp_service
    
    try:
        # Store current running servers
        running_servers = [
            name for name, server in mcp_service.servers.items()
            if server.is_running()
        ]
        
        # Create new MCP service instance (reinitializes with latest config)
        mcp_service = MCPService()
        
        # Try to restart previously running servers
        restarted = []
        for server_name in running_servers:
            if server_name in mcp_service.servers:
                if mcp_service.start_server(server_name):
                    restarted.append(server_name)
        
        new_servers = list(mcp_service.servers.keys())
        
        return {
            "success": True,
            "message": "MCP servers reloaded successfully",
            "total_servers": len(new_servers),
            "restarted_servers": len(restarted),
            "servers": new_servers
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload MCP servers: {str(e)}"
        )

