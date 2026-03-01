"""
Heuristic logic for determining if a connection is testable.
"""

import json
import logging

logger = logging.getLogger(__name__)

class ConnectionTestHeuristic:
    """
    Heuristic to determine if a connection is likely testable via GraphQL ping.
    JDBC connections are always testable. 
    GENERIC connections are testable if they have certain 'target' parameters.
    """
    
    # Known problematic types/names that hang or aren't real data sources
    BLACKLIST = ["tech-lineage", "technical lineage", "techlinadmin", "azure", "powerbi"]
    
    # Heuristic: testable connections usually have one of these keys in their parameters
    DATA_SOURCE_KEYS = [
        "connection-string", "driver-class", "url", "host", "server",
        "account", "clientid", "tenantid", "powerbi", "api-key"
    ]

    @classmethod
    def is_testable(cls, detail: dict) -> bool:
        """
        Evaluate if a connection is testable based on its metadata.
        
        Args:
            detail: Dictionary containing connection metadata (id, name, connectionTypeId, family, parameters).
            
        Returns:
            True if the connection is likely testable, False otherwise.
        """
        name = str(detail.get("name", "")).lower()
        type_id = str(detail.get("connectionTypeId", "")).lower()
        family = str(detail.get("family", "")).upper()
        
        # JDBC is always a standard data source
        if family == "JDBC":
            return True
        
        # Check blacklist for known non-testable or problematic types
        if any(b in name or b in type_id for b in cls.BLACKLIST):
            return False

        params_str = detail.get("parameters", "{}").lower()
        try:
            params = json.loads(params_str)
        except Exception:
            params = {}
            
        # Check for presence of identifying data source keys in parameters string
        if any(k in params_str for k in cls.DATA_SOURCE_KEYS):
            return True
            
        # Default to testable if it has more than just authType configuration
        # Simple OAuth-only shells usually have exactly 1 parameter (authType)
        return len(params) > 1
