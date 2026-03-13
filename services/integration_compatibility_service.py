"""Service for checking integration compatibility and managing upgrades."""

import sys
import logging
import subprocess
import importlib.metadata
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class IntegrationCompatibilityService:
    """Service for checking integration package compatibility with current Python version."""
    
    def __init__(self):
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.python_major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        # Integration package mappings
        self.integrations = {
            # Threat Intelligence
            'misp': {
                'package': 'pymisp',
                'min_version': '2.4.170',
                'display_name': 'MISP',
                'category': 'Threat Intelligence'
            },
            'opencti': {
                'package': 'pycti',
                'min_version': '5.12.0',
                'display_name': 'OpenCTI',
                'category': 'Threat Intelligence'
            },
            'shodan': {
                'package': 'shodan',
                'min_version': '1.30.1',
                'display_name': 'Shodan',
                'category': 'Threat Intelligence'
            },
            'virustotal': {
                'package': None,  # Uses API directly
                'display_name': 'VirusTotal',
                'category': 'Threat Intelligence'
            },
            
            # Incident Management & Ticketing
            'jira': {
                'package': 'jira',
                'min_version': '3.5.0',
                'display_name': 'Jira',
                'category': 'Incident Management'
            },
            'pagerduty': {
                'package': 'pdpyras',
                'min_version': '5.1.0',
                'display_name': 'PagerDuty',
                'category': 'Incident Management'
            },
            'servicenow': {
                'package': 'pysnow',
                'min_version': '0.7.17',
                'display_name': 'ServiceNow',
                'category': 'Incident Management',
                'compatibility_note': 'Conflicts with pandas 2.2.0+ (requires old pytz version). Incompatible with Python 3.13.'
            },
            
            # Communications
            'slack': {
                'package': 'slack_sdk',
                'min_version': '3.23.0',
                'display_name': 'Slack',
                'category': 'Communications'
            },
            'microsoft-teams': {
                'package': 'msal',
                'min_version': '1.24.1',
                'display_name': 'Microsoft Teams',
                'category': 'Communications'
            },
            
            # EDR/XDR Platforms
            'microsoft-defender': {
                'package': 'azure-mgmt-security',
                'min_version': '5.0.0',
                'display_name': 'Microsoft Defender',
                'category': 'EDR/XDR',
                'dependencies': ['azure-identity']
            },
            'crowdstrike': {
                'package': None,  # Uses API directly
                'display_name': 'CrowdStrike',
                'category': 'EDR/XDR'
            },
            'sentinelone': {
                'package': None,  # Uses API directly
                'display_name': 'SentinelOne',
                'category': 'EDR/XDR'
            },
            'carbon-black': {
                'package': None,  # Uses API directly
                'display_name': 'Carbon Black',
                'category': 'EDR/XDR'
            },
            
            # Cloud Security
            'azure-sentinel': {
                'package': 'azure-mgmt-sentinel',
                'min_version': '1.0.0',
                'display_name': 'Azure Sentinel',
                'category': 'Cloud Security',
                'compatibility_note': 'Package not available on PyPI. Use azure-monitor-query and azure-mgmt-securityinsight instead.'
            },
            'gcp-security': {
                'package': 'google-cloud-security-command-center',
                'min_version': '1.23.0',
                'display_name': 'GCP Security Command Center',
                'category': 'Cloud Security',
                'compatibility_note': 'Not compatible with Python 3.13 (max Python 3.12)'
            },
            
            # Network Security
            'palo-alto': {
                'package': 'pan-os-python',
                'min_version': '1.11.0',
                'display_name': 'Palo Alto Networks',
                'category': 'Network Security'
            },
            
            # Vulnerability Management
            'tenable': {
                'package': 'tenable-io',
                'min_version': '1.16.0',
                'display_name': 'Tenable.io',
                'category': 'Vulnerability Management',
                'compatibility_note': 'Not compatible with Python 3.13 yet'
            },
            
            # Data Storage
            'elasticsearch': {
                'package': 'elasticsearch',
                'min_version': '8.10.0',
                'display_name': 'Elasticsearch',
                'category': 'Data Storage'
            },
            'postgresql': {
                'package': 'psycopg2-binary',
                'min_version': '2.9.9',
                'display_name': 'PostgreSQL',
                'category': 'Data Storage'
            },
            
            # Core
            'claude-agent-sdk': {
                'package': 'claude-agent-sdk',
                'min_version': '0.1.0',
                'display_name': 'Claude Agent SDK',
                'category': 'Core',
                'python_min_version': '3.10'
            }
        }
    
    def check_package_installed(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a package is installed and return its version.
        
        Returns:
            (is_installed, version)
        """
        if not package_name:
            return (True, None)  # API-only integration
        
        try:
            version = importlib.metadata.version(package_name)
            return (True, version)
        except importlib.metadata.PackageNotFoundError:
            return (False, None)
    
    def check_python_compatibility(self, integration_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if current Python version is compatible with the integration.
        
        Returns:
            (is_compatible, reason)
        """
        integration = self.integrations.get(integration_id, {})
        
        # Check Python minimum version requirement
        if 'python_min_version' in integration:
            min_version = integration['python_min_version']
            if sys.version_info < tuple(map(int, min_version.split('.'))):
                return (False, f"Requires Python {min_version}+, you have {self.python_version}")
        
        # Check specific compatibility notes
        if 'compatibility_note' in integration:
            note = integration['compatibility_note']
            
            # Check if note mentions Python version incompatibility
            if 'Python 3.13' in note and sys.version_info >= (3, 13):
                return (False, note)
            elif 'Python 3.12' in note and sys.version_info >= (3, 13):
                return (False, note)
        
        return (True, None)
    
    def get_integration_status(self, integration_id: str) -> Dict:
        """
        Get complete status for an integration.
        
        Returns:
            Dictionary with status information
        """
        integration = self.integrations.get(integration_id, {})
        
        if not integration:
            return {
                'integration_id': integration_id,
                'status': 'unknown',
                'message': 'Integration not found'
            }
        
        package_name = integration.get('package')
        display_name = integration.get('display_name', integration_id)
        
        # Check Python compatibility first
        python_compatible, python_reason = self.check_python_compatibility(integration_id)
        
        if not python_compatible:
            return {
                'integration_id': integration_id,
                'display_name': display_name,
                'status': 'incompatible',
                'message': python_reason,
                'installed': False,
                'can_install': False,
                'compatibility_note': integration.get('compatibility_note')
            }
        
        # Check if package is installed
        if package_name:
            is_installed, current_version = self.check_package_installed(package_name)
            
            if is_installed:
                return {
                    'integration_id': integration_id,
                    'display_name': display_name,
                    'status': 'installed',
                    'message': f'Installed (v{current_version})',
                    'installed': True,
                    'version': current_version,
                    'can_install': False,
                    'can_upgrade': True,
                    'package': package_name
                }
            else:
                return {
                    'integration_id': integration_id,
                    'display_name': display_name,
                    'status': 'not_installed',
                    'message': 'Not installed',
                    'installed': False,
                    'can_install': True,
                    'package': package_name,
                    'min_version': integration.get('min_version')
                }
        else:
            # API-only integration
            return {
                'integration_id': integration_id,
                'display_name': display_name,
                'status': 'available',
                'message': 'API-based (no package required)',
                'installed': True,
                'can_install': False
            }
    
    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get status for all integrations."""
        statuses = {}
        for integration_id in self.integrations.keys():
            statuses[integration_id] = self.get_integration_status(integration_id)
        return statuses
    
    def install_package(self, package_name: str, version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Install or upgrade a package.
        
        Returns:
            (success, message)
        """
        try:
            if version:
                package_spec = f"{package_name}>={version}"
            else:
                package_spec = package_name
            
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', package_spec],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            
            if result.returncode == 0:
                return (True, f"Successfully installed {package_name}")
            else:
                return (False, f"Installation failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            return (False, "Installation timed out")
        except Exception as e:
            return (False, f"Installation error: {str(e)}")
    
    def upgrade_package(self, package_name: str) -> Tuple[bool, str]:
        """
        Upgrade a package to the latest version.
        
        Returns:
            (success, message)
        """
        return self.install_package(package_name, version=None)
    
    def uninstall_package(self, package_name: str) -> Tuple[bool, str]:
        """
        Uninstall a package.
        
        Returns:
            (success, message)
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'uninstall', '-y', package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return (True, f"Successfully uninstalled {package_name}")
            else:
                return (False, f"Uninstallation failed: {result.stderr}")
        
        except Exception as e:
            return (False, f"Uninstallation error: {str(e)}")
    
    def get_system_info(self) -> Dict:
        """Get system information."""
        return {
            'python_version': self.python_version,
            'python_major_minor': self.python_major_minor,
            'python_implementation': sys.implementation.name,
            'platform': sys.platform,
            'pip_version': self._get_pip_version()
        }
    
    def _get_pip_version(self) -> Optional[str]:
        """Get pip version."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse "pip X.Y.Z from ..."
                parts = result.stdout.split()
                if len(parts) >= 2:
                    return parts[1]
        except Exception:
            pass
        return None


# Singleton instance
_compatibility_service = None

def get_compatibility_service() -> IntegrationCompatibilityService:
    """Get singleton compatibility service instance."""
    global _compatibility_service
    if _compatibility_service is None:
        _compatibility_service = IntegrationCompatibilityService()
    return _compatibility_service

