"""ATT&CK framework API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException
import logging

from services.database_data_service import DatabaseDataService

router = APIRouter()
logger = logging.getLogger(__name__)
data_service = DatabaseDataService()


@router.get("/layer")
async def get_attack_layer():
    """
    Get ATT&CK Navigator layer data.
    
    Builds an ATT&CK Navigator layer from findings technique predictions.
    
    Returns:
        ATT&CK layer JSON
    """
    try:
        findings = data_service.get_findings()
        
        # Build technique scores from findings
        technique_scores = {}
        for finding in findings:
            predicted_techniques = finding.get('predicted_techniques', [])
            for tech in predicted_techniques:
                tid = tech.get('technique_id')
                confidence = tech.get('confidence', 0)
                if tid:
                    # Track max confidence per technique
                    technique_scores[tid] = max(technique_scores.get(tid, 0), confidence)
        
        techniques = [
            {
                "techniqueID": tid,
                "score": round(score * 100),
                "color": "",
                "comment": "",
                "enabled": True,
            }
            for tid, score in technique_scores.items()
        ]
        
        layer = {
            "name": "DeepTempo Findings",
            "version": "4.5",
            "domain": "enterprise-attack",
            "description": "ATT&CK techniques detected in findings",
            "techniques": techniques,
        }
        
        return layer
    except Exception as e:
        logger.error(f"Error building ATT&CK layer: {e}")
        return {
            "name": "DeepTempo Findings",
            "version": "4.5",
            "domain": "enterprise-attack",
            "description": "ATT&CK techniques detected in findings",
            "techniques": []
        }


@router.get("/techniques/rollup")
async def get_technique_rollup(min_confidence: float = 0.0):
    """
    Get rollup of ATT&CK techniques across all findings.
    
    Args:
        min_confidence: Minimum confidence threshold
    
    Returns:
        Technique statistics
    """
    findings = data_service.get_findings()
    
    technique_counts = {}
    technique_severities = {}
    
    for finding in findings:
        predicted_techniques = finding.get('predicted_techniques', [])
        severity = finding.get('severity', 'unknown')
        
        for tech in predicted_techniques:
            technique_id = tech.get('technique_id')
            confidence = tech.get('confidence', 0)
            
            if confidence < min_confidence:
                continue
            
            if not technique_id:
                continue
            
            # Count occurrences
            technique_counts[technique_id] = technique_counts.get(technique_id, 0) + 1
            
            # Track severities
            if technique_id not in technique_severities:
                technique_severities[technique_id] = {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                }
            
            technique_severities[technique_id][severity] = \
                technique_severities[technique_id].get(severity, 0) + 1
    
    # Build result
    techniques = []
    for technique_id, count in technique_counts.items():
        techniques.append({
            "technique_id": technique_id,
            "count": count,
            "severities": technique_severities[technique_id]
        })
    
    # Sort by count
    techniques.sort(key=lambda x: x['count'], reverse=True)
    
    return {
        "total_techniques": len(techniques),
        "techniques": techniques
    }


@router.get("/techniques/{technique_id}/findings")
async def get_findings_by_technique(technique_id: str):
    """
    Get all findings associated with a specific technique.
    
    Args:
        technique_id: MITRE ATT&CK technique ID
    
    Returns:
        List of findings
    """
    findings = data_service.get_findings()
    
    matching_findings = []
    
    for finding in findings:
        predicted_techniques = finding.get('predicted_techniques', [])
        
        for tech in predicted_techniques:
            if tech.get('technique_id') == technique_id:
                matching_findings.append(finding)
                break
    
    return {
        "technique_id": technique_id,
        "findings": matching_findings,
        "total": len(matching_findings)
    }


@router.get("/tactics/summary")
async def get_tactics_summary():
    """
    Get summary of tactics across all findings.
    
    Returns:
        Tactics summary
    """
    findings = data_service.get_findings()
    
    # Map techniques to tactics (simplified - in production, use ATT&CK data)
    technique_to_tactic = {
        'T1071': 'Command and Control',
        'T1573': 'Command and Control',
        'T1059': 'Execution',
        'T1055': 'Defense Evasion',
        'T1036': 'Defense Evasion',
        # Add more mappings as needed
    }
    
    tactic_counts = {}
    
    for finding in findings:
        predicted_techniques = finding.get('predicted_techniques', [])
        
        for tech in predicted_techniques:
            technique_id = tech.get('technique_id', '')
            
            # Extract base technique (without sub-technique)
            base_technique = technique_id.split('.')[0]
            
            # Get tactic
            tactic = technique_to_tactic.get(base_technique, 'Unknown')
            tactic_counts[tactic] = tactic_counts.get(tactic, 0) + 1
    
    return {
        "tactics": [
            {"tactic": tactic, "count": count}
            for tactic, count in sorted(
                tactic_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]
    }

