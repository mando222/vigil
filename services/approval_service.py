"""Approval service for managing pending autonomous actions."""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import sys

# Add path for database imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.config_service import get_config_service

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can be approved."""
    ISOLATE_HOST = "isolate_host"
    BLOCK_IP = "block_ip"
    BLOCK_DOMAIN = "block_domain"
    QUARANTINE_FILE = "quarantine_file"
    DISABLE_USER = "disable_user"
    EXECUTE_SPL_QUERY = "execute_spl_query"
    CUSTOM = "custom"


class ActionStatus(Enum):
    """Status of pending actions."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class PendingAction:
    """Represents a pending action awaiting approval."""
    action_id: str
    action_type: str  # ActionType value
    title: str
    description: str
    target: str  # IP, hostname, username, etc.
    confidence: float
    reason: str
    evidence: List[str]  # Finding IDs or evidence references
    created_at: str
    created_by: str  # "auto_responder", "investigator", etc.
    requires_approval: bool
    status: str  # ActionStatus value
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    executed_at: Optional[str] = None
    execution_result: Optional[Dict] = None
    rejection_reason: Optional[str] = None
    
    # Action-specific parameters
    parameters: Optional[Dict] = None


class ApprovalService:
    """Service for managing approval workflow for autonomous actions."""
    
    def __init__(self, data_dir: Optional[Path] = None, dry_run: bool = False):
        """
        Initialize approval service.
        
        Args:
            data_dir: Directory for storing pending actions (default: ./data)
            dry_run: If True, don't execute actions, just log them
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.actions_file = self.data_dir / "pending_actions.json"
        self.config_file = self.data_dir / "approval_config.json"
        self.dry_run = dry_run
        
        # Create file if it doesn't exist
        if not self.actions_file.exists():
            self._save_actions([])
        
        # Load configuration
        self._load_config()
    
    def _load_actions(self) -> List[PendingAction]:
        """Load all actions from file."""
        try:
            with open(self.actions_file, 'r') as f:
                data = json.load(f)
                return [PendingAction(**action) for action in data]
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error loading actions: {e}")
            return []
    
    def _save_actions(self, actions: List[PendingAction]):
        """Save all actions to file."""
        try:
            with open(self.actions_file, 'w') as f:
                json.dump([asdict(action) for action in actions], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving actions: {e}")
    
    def _load_config(self):
        """Load approval configuration from database with file fallback."""
        try:
            # Try database first
            config_service = get_config_service()
            config_value = config_service.get_system_config('approval.force_manual_approval')
            
            if config_value:
                self.force_manual_approval = config_value.get('enabled', False)
                logger.debug(f"Loaded approval config from database: force_manual_approval={self.force_manual_approval}")
                return
            
            # Fallback to file-based config
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.force_manual_approval = config.get("force_manual_approval", False)
                    logger.debug(f"Loaded approval config from file: force_manual_approval={self.force_manual_approval}")
            else:
                self.force_manual_approval = False
                self._save_config()
        except Exception as e:
            logger.error(f"Error loading approval config: {e}")
            self.force_manual_approval = False
    
    def _save_config(self):
        """Save approval configuration to database and file."""
        try:
            config_value = {
                "enabled": self.force_manual_approval
            }
            
            # Save to database
            config_service = get_config_service(user_id='approval_service')
            success = config_service.set_system_config(
                key='approval.force_manual_approval',
                value=config_value,
                description='Force manual approval for all actions',
                config_type='approval',
                change_reason='Updated by approval service'
            )
            
            if success:
                logger.debug("Saved approval config to database")
            else:
                logger.warning("Failed to save approval config to database")
            
            # Also save to file for backward compatibility
            config = {
                "force_manual_approval": self.force_manual_approval
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                logger.debug("Saved approval config to file")
                
        except Exception as e:
            logger.error(f"Error saving approval config: {e}")
    
    def set_force_manual_approval(self, force: bool):
        """
        Set whether to force manual approval for all actions.
        
        Args:
            force: If True, all actions require approval regardless of confidence
        """
        self.force_manual_approval = force
        self._save_config()
        logger.info(f"Force manual approval set to: {force}")
    
    def get_force_manual_approval(self) -> bool:
        """Get the current force manual approval setting."""
        return self.force_manual_approval
    
    def should_auto_approve(
        self, 
        action: Dict, 
        threshold: float = 0.90, 
        force_manual: bool = False
    ) -> bool:
        """
        Determine if an action should be auto-approved based on confidence.
        
        Args:
            action: Action dict with 'confidence' key
            threshold: Confidence threshold for auto-approval (default 0.90)
            force_manual: If True, never auto-approve
            
        Returns:
            True if action should be auto-approved, False otherwise
        """
        if force_manual or self.get_force_manual_approval():
            return False
        
        confidence = action.get("confidence", 0.0)
        
        # Auto-approve if confidence >= threshold
        if confidence >= threshold:
            return True
        
        # Auto-approve with flag if confidence between 0.85-0.89
        if confidence >= 0.85:
            return True
        
        # Require manual approval for confidence < 0.85
        return False
    
    def needs_flag(self, confidence: float) -> bool:
        """
        Check if an action needs a flag (confidence 0.85-0.89).
        
        Args:
            confidence: Confidence score
            
        Returns:
            True if action needs a flag, False otherwise
        """
        return 0.85 <= confidence < 0.90
    
    def get_action_decision(self, action: Dict, threshold: float = 0.90) -> str:
        """
        Get the decision for an action based on confidence.
        
        Args:
            action: Action dict with 'confidence' key
            threshold: Confidence threshold
            
        Returns:
            Decision string: "auto_approve", "manual_approval", or "monitor_only"
        """
        confidence = action.get("confidence", 0.0)
        
        if confidence < 0.70:
            return "monitor_only"
        elif confidence < 0.85:
            return "manual_approval"
        else:
            return "auto_approve"
    
    def is_valid_action_type(self, action_type: str) -> bool:
        """
        Check if an action type is valid.
        
        Args:
            action_type: Action type string
            
        Returns:
            True if valid, False otherwise
        """
        try:
            ActionType(action_type)
            return True
        except ValueError:
            return False
    
    def validate_action(self, action: Dict) -> tuple[bool, List[str]]:
        """
        Validate an action payload.
        
        Args:
            action: Action dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ["type", "target", "confidence"]
        for field in required_fields:
            if field not in action:
                errors.append(f"Missing required field: {field}")
        
        # Validate action type
        if "type" in action and not self.is_valid_action_type(action["type"]):
            errors.append(f"Invalid action type: {action['type']}")
        
        # Validate confidence range
        if "confidence" in action:
            confidence = action.get("confidence", 0.0)
            if not (0.0 <= confidence <= 1.0):
                errors.append(f"Confidence must be between 0.0 and 1.0, got {confidence}")
        
        return (len(errors) == 0, errors)
    
    def create_action(
        self,
        action_type: ActionType,
        title: str,
        description: str,
        target: str,
        confidence: float,
        reason: str,
        evidence: List[str],
        created_by: str = "system",
        parameters: Optional[Dict] = None
    ) -> PendingAction:
        """
        Create a new pending action.
        
        Args:
            action_type: Type of action
            title: Short title
            description: Detailed description
            target: Target (IP, hostname, etc.)
            confidence: Confidence score (0.0-1.0)
            reason: Reason for action
            evidence: List of evidence/finding IDs
            created_by: Who created the action
            parameters: Action-specific parameters
        
        Returns:
            Created PendingAction
        """
        # Determine if approval is required based on confidence and override setting
        if self.force_manual_approval:
            # Override: Force all actions to require approval
            requires_approval = True
        else:
            # Normal behavior: Auto-execute if >= 0.90
            requires_approval = confidence < 0.90
        
        action = PendingAction(
            action_id=f"action-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
            action_type=action_type.value,
            title=title,
            description=description,
            target=target,
            confidence=confidence,
            reason=reason,
            evidence=evidence,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
            requires_approval=requires_approval,
            status=ActionStatus.PENDING.value if requires_approval else ActionStatus.APPROVED.value,
            parameters=parameters or {}
        )
        
        # Save
        actions = self._load_actions()
        actions.append(action)
        self._save_actions(actions)
        
        logger.info(f"Created action {action.action_id}: {title} (confidence: {confidence})")
        return action
    
    def get_action(self, action_id: str) -> Optional[PendingAction]:
        """Get a specific action by ID."""
        actions = self._load_actions()
        for action in actions:
            if action.action_id == action_id:
                return action
        return None
    
    def list_actions(
        self,
        status: Optional[ActionStatus] = None,
        action_type: Optional[ActionType] = None,
        requires_approval: Optional[bool] = None
    ) -> List[PendingAction]:
        """
        List actions with optional filters.
        
        Args:
            status: Filter by status
            action_type: Filter by action type
            requires_approval: Filter by approval requirement
        
        Returns:
            List of matching actions
        """
        actions = self._load_actions()
        
        # Apply filters
        if status:
            actions = [a for a in actions if a.status == status.value]
        if action_type:
            actions = [a for a in actions if a.action_type == action_type.value]
        if requires_approval is not None:
            actions = [a for a in actions if a.requires_approval == requires_approval]
        
        # Sort by created_at descending
        actions.sort(key=lambda x: x.created_at, reverse=True)
        
        return actions
    
    def approve_action(
        self,
        action_id: str,
        approved_by: str = "analyst"
    ) -> Optional[PendingAction]:
        """
        Approve a pending action.
        
        Args:
            action_id: Action ID to approve
            approved_by: Who approved it
        
        Returns:
            Updated action or None if not found
        """
        actions = self._load_actions()
        
        for action in actions:
            if action.action_id == action_id:
                if action.status == ActionStatus.PENDING.value:
                    action.status = ActionStatus.APPROVED.value
                    action.approved_at = datetime.now().isoformat()
                    action.approved_by = approved_by
                    self._save_actions(actions)
                    logger.info(f"Action {action_id} approved by {approved_by}")
                    return action
                else:
                    logger.warning(f"Action {action_id} is not pending (status: {action.status})")
                    return action
        
        logger.warning(f"Action {action_id} not found")
        return None
    
    def reject_action(
        self,
        action_id: str,
        reason: str,
        rejected_by: str = "analyst"
    ) -> Optional[PendingAction]:
        """
        Reject a pending action.
        
        Args:
            action_id: Action ID to reject
            reason: Reason for rejection
            rejected_by: Who rejected it
        
        Returns:
            Updated action or None if not found
        """
        actions = self._load_actions()
        
        for action in actions:
            if action.action_id == action_id:
                if action.status == ActionStatus.PENDING.value:
                    action.status = ActionStatus.REJECTED.value
                    action.rejection_reason = reason
                    action.approved_by = rejected_by  # Track who rejected
                    action.approved_at = datetime.now().isoformat()
                    self._save_actions(actions)
                    logger.info(f"Action {action_id} rejected by {rejected_by}: {reason}")
                    return action
                else:
                    logger.warning(f"Action {action_id} is not pending (status: {action.status})")
                    return action
        
        logger.warning(f"Action {action_id} not found")
        return None
    
    def mark_executed(
        self,
        action_id: str,
        result: Dict
    ) -> Optional[PendingAction]:
        """
        Mark an action as executed.
        
        Args:
            action_id: Action ID
            result: Execution result
        
        Returns:
            Updated action or None if not found
        """
        actions = self._load_actions()
        
        for action in actions:
            if action.action_id == action_id:
                if action.status == ActionStatus.APPROVED.value:
                    action.status = ActionStatus.EXECUTED.value
                    action.executed_at = datetime.now().isoformat()
                    action.execution_result = result
                    self._save_actions(actions)
                    logger.info(f"Action {action_id} marked as executed")
                    return action
                else:
                    logger.warning(f"Action {action_id} is not approved (status: {action.status})")
                    return None
        
        logger.warning(f"Action {action_id} not found")
        return None
    
    def mark_failed(
        self,
        action_id: str,
        error: str
    ) -> Optional[PendingAction]:
        """
        Mark an action as failed.
        
        Args:
            action_id: Action ID
            error: Error message
        
        Returns:
            Updated action or None if not found
        """
        actions = self._load_actions()
        
        for action in actions:
            if action.action_id == action_id:
                action.status = ActionStatus.FAILED.value
                action.executed_at = datetime.now().isoformat()
                action.execution_result = {"error": error}
                self._save_actions(actions)
                logger.error(f"Action {action_id} failed: {error}")
                return action
        
        return None
    
    def get_pending_count(self) -> int:
        """Get count of pending actions requiring approval."""
        actions = self.list_actions(status=ActionStatus.PENDING)
        return len([a for a in actions if a.requires_approval])
    
    def get_stats(self) -> Dict:
        """Get statistics about actions."""
        actions = self._load_actions()
        
        return {
            "total": len(actions),
            "pending": len([a for a in actions if a.status == ActionStatus.PENDING.value]),
            "approved": len([a for a in actions if a.status == ActionStatus.APPROVED.value]),
            "rejected": len([a for a in actions if a.status == ActionStatus.REJECTED.value]),
            "executed": len([a for a in actions if a.status == ActionStatus.EXECUTED.value]),
            "failed": len([a for a in actions if a.status == ActionStatus.FAILED.value]),
            "requires_approval": len([a for a in actions if a.requires_approval]),
            "by_type": self._count_by_type(actions)
        }
    
    def _count_by_type(self, actions: List[PendingAction]) -> Dict[str, int]:
        """Count actions by type."""
        counts = {}
        for action in actions:
            counts[action.action_type] = counts.get(action.action_type, 0) + 1
        return counts
    
    def list_pending_approvals(self) -> List[PendingAction]:
        """
        List all pending actions requiring approval.
        
        Returns:
            List of pending actions
        """
        return self.list_actions(status=ActionStatus.PENDING, requires_approval=True)
    
    def get_audit_trail(self, action_id: str) -> List[Dict]:
        """
        Get audit trail for a specific action.
        
        Args:
            action_id: Action ID to get audit trail for
            
        Returns:
            List of audit events for the action
        """
        action = self.get_action(action_id)
        if not action:
            return []
        
        # Build audit trail from action lifecycle
        trail = []
        
        # Created event
        trail.append({
            "event": "created",
            "timestamp": action.created_at,
            "user": action.created_by,
            "details": {
                "action_type": action.action_type,
                "target": action.target,
                "confidence": action.confidence
            }
        })
        
        # Approval/rejection event - check if approved_at exists AND if status was changed
        if action.approved_at:
            if action.status in [ActionStatus.APPROVED.value, ActionStatus.EXECUTED.value]:
                trail.append({
                    "event": "approved",
                    "timestamp": action.approved_at,
                    "user": action.approved_by,
                    "details": {}
                })
            elif action.status == ActionStatus.REJECTED.value:
                trail.append({
                    "event": "rejected",
                    "timestamp": action.approved_at,
                    "user": action.approved_by,
                    "details": {
                        "reason": action.rejection_reason
                    }
                })
        
        # Execution event
        if action.executed_at:
            trail.append({
                "event": "executed" if action.status == ActionStatus.EXECUTED.value else "failed",
                "timestamp": action.executed_at,
                "user": "system",
                "details": {
                    "result": action.execution_result
                }
            })
        
        return trail
    
    def execute_action(self, action: Dict) -> Dict:
        """
        Execute an action (with dry run support).
        
        Args:
            action: Action dictionary with type, target, etc.
            
        Returns:
            Execution result dictionary
        """
        if self.dry_run:
            # In dry run mode, just log and return mock result
            logger.info(f"DRY RUN: Would execute {action.get('type')} on {action.get('target')}")
            return {
                "status": "dry_run",
                "would_execute": True,
                "action": action
            }
        
        # In real execution mode, this would call actual service integrations
        # For now, return a mock result indicating execution is not yet implemented
        logger.warning(f"Action execution not yet fully implemented: {action.get('type')}")
        return {
            "status": "not_implemented",
            "message": "Action execution requires service integration",
            "action": action
        }
    
    def execute_approved_action(self, action_id: str) -> Dict:
        """
        Execute an approved action by ID.
        
        Args:
            action_id: Action ID to execute
            
        Returns:
            Execution result
        """
        action = self.get_action(action_id)
        if not action:
            return {"error": f"Action {action_id} not found"}
        
        if action.status != ActionStatus.APPROVED.value:
            return {"error": f"Action {action_id} is not approved (status: {action.status})"}
        
        # Convert PendingAction to dict for execute_action
        action_dict = {
            "type": action.action_type,
            "target": action.target,
            "confidence": action.confidence,
            "parameters": action.parameters
        }
        
        # Execute the action
        result = self.execute_action(action_dict)
        
        # Update action status based on result
        if result.get("status") == "success":
            self.mark_executed(action_id, result)
        elif result.get("status") not in ["dry_run", "not_implemented"]:
            self.mark_failed(action_id, result.get("error", "Unknown error"))
        
        return result
    
    def add_to_queue(self, action: Dict) -> str:
        """
        Add an action to the approval queue. Wrapper for create_action().
        
        Args:
            action: Action dictionary with type, target, confidence, etc.
            
        Returns:
            Action ID
        """
        # Validate action
        is_valid, errors = self.validate_action(action)
        if not is_valid:
            raise ValueError(f"Invalid action: {', '.join(errors)}")
        
        # Create the action
        pending_action = self.create_action(
            action_type=ActionType(action["type"]),
            title=action.get("title", f"{action['type']}: {action['target']}"),
            description=action.get("description", action.get("reasoning", "")),
            target=action["target"],
            confidence=action["confidence"],
            reason=action.get("reasoning", action.get("reason", "")),
            evidence=action.get("evidence", []),
            created_by=action.get("created_by", "system"),
            parameters=action.get("parameters")
        )
        
        return pending_action.action_id
    
    def log_approval_decision(
        self,
        action: Dict,
        decision: str,
        user: str,
        reasoning: Optional[str] = None
    ) -> Dict:
        """
        Log an approval decision.
        
        Args:
            action: Action dictionary
            decision: Decision made ("auto_approved", "approved", "rejected")
            user: User who made the decision
            reasoning: Optional reasoning for the decision
            
        Returns:
            Log entry dictionary
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action.get("type"),
            "target": action.get("target"),
            "confidence": action.get("confidence"),
            "decision": decision,
            "user": user,
            "reasoning": reasoning or action.get("reasoning", ""),
            "dry_run": self.dry_run
        }
        
        logger.info(f"Approval decision logged: {decision} by {user} for {action.get('type')}")
        
        return log_entry
    
    def log_execution(
        self,
        action_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> Dict:
        """
        Log action execution result.
        
        Args:
            action_id: Action ID
            status: Execution status ("success", "failed", "skipped")
            result: Execution result data
            error: Error message if failed
            
        Returns:
            Log entry dictionary
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action_id,
            "status": status,
            "result": result,
            "error": error,
            "dry_run": self.dry_run
        }
        
        if status == "success":
            logger.info(f"Action {action_id} executed successfully")
            if not self.dry_run:
                # Update action status
                self.mark_executed(action_id, result or {})
        elif status == "failed":
            logger.error(f"Action {action_id} failed: {error}")
            if not self.dry_run:
                # Update action status
                self.mark_failed(action_id, error or "Unknown error")
        else:
            logger.info(f"Action {action_id} execution skipped (dry run or other reason)")
        
        return log_entry


# Singleton instance
_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    """Get singleton ApprovalService instance."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service

