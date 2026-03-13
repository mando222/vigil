"""Skills API endpoints for SOC workflow skill management and execution."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class SkillExecuteRequest(BaseModel):
    """Request to execute a skill workflow."""
    finding_id: Optional[str] = None
    case_id: Optional[str] = None
    context: Optional[str] = None
    hypothesis: Optional[str] = None


@router.get("/skills")
async def list_skills():
    """
    List all available skill workflows.
    
    Returns:
        List of skills with metadata (name, description, agents, tools, use-case)
    """
    try:
        from services.skills_service import get_skills_service
        
        service = get_skills_service()
        skills = service.list_skills()
        
        return {
            "skills": skills,
            "count": len(skills),
        }
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Static routes MUST come before parameterized {skill_id} routes
@router.post("/skills/reload")
async def reload_skills():
    """
    Force reload all skills from disk.
    
    Useful after adding or modifying SKILL.md files without restarting the server.
    
    Returns:
        Updated skill count
    """
    try:
        from services.skills_service import get_skills_service
        
        service = get_skills_service()
        service.reload()
        skills = service.list_skills()
        
        return {
            "success": True,
            "message": f"Reloaded {len(skills)} skills",
            "count": len(skills),
        }
    except Exception as e:
        logger.error(f"Error reloading skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    """
    Get full details for a specific skill, including the markdown body.
    
    Args:
        skill_id: The skill ID (directory name, e.g., 'incident-response')
    
    Returns:
        Full skill details with metadata and body
    """
    try:
        from services.skills_service import get_skills_service
        
        service = get_skills_service()
        skill = service.get_skill_dict(skill_id, include_body=True)
        
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
        
        return skill
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill {skill_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills/{skill_id}/execute")
async def execute_skill(skill_id: str, request: SkillExecuteRequest):
    """
    Execute a skill workflow.
    
    Builds a composite prompt from the skill definition and agent methodologies,
    then executes it via ClaudeService.run_agent_task().
    
    Args:
        skill_id: The skill ID to execute
        request: Execution parameters (finding_id, case_id, context, hypothesis)
    
    Returns:
        Execution result with skill output, tool calls, and metadata
    """
    try:
        from services.skills_service import get_skills_service
        
        service = get_skills_service()
        
        # Verify skill exists
        skill = service.get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
        
        # Build parameters dict
        parameters = {
            k: v for k, v in request.model_dump().items() if v is not None
        }
        
        if not parameters:
            raise HTTPException(
                status_code=400,
                detail="At least one parameter required: finding_id, case_id, context, or hypothesis"
            )
        
        # Execute the skill
        result = await service.execute_skill(skill_id, parameters)
        
        if not result.get("success"):
            error = result.get("error", "Unknown error during skill execution")
            raise HTTPException(status_code=500, detail=error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing skill {skill_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
