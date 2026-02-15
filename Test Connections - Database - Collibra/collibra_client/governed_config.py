"""
Governed connections configuration loader.

Loads the set of edge_connection_ids (and optional metadata) from a YAML file
used for connection testing (refresh) and filtering. Path is read from
COLLIBRA_GOVERNED_CONNECTIONS_CONFIG or defaults to governed_connections.yaml.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, Union

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def load_governed_config(
    path: Optional[Union[str, Path]] = None,
) -> Tuple[Set[str], Dict[str, Dict[str, Any]]]:
    """
    Load governed edge connection IDs and metadata from YAML.

    The YAML file should have structure:
        governed_connections:
          "<edge_uuid>":
            name: "..."
            description: "..."
            # optional metadata

    Args:
        path: Path to YAML file. If None, uses env
              COLLIBRA_GOVERNED_CONNECTIONS_CONFIG or default
              "governed_connections.yaml" in the current working directory.

    Returns:
        Tuple of (governed_edge_ids, metadata_dict).
        governed_edge_ids: Set of edge connection UUID strings (keys).
        metadata_dict: Full governed_connections dict for logging (e.g. name per id).

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If PyYAML is not installed or file is invalid/empty.
    """
    if yaml is None:
        raise ValueError(
            "PyYAML is required to load governed_connections. "
            "Install with: pip install pyyaml"
        )

    if path is None:
        path = os.getenv("COLLIBRA_GOVERNED_CONNECTIONS_CONFIG", "governed_connections.yaml")
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise FileNotFoundError(f"Governed connections config not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return set(), {}

    governed = data.get("governed_connections")
    if not governed or not isinstance(governed, dict):
        return set(), {}

    edge_ids = set(str(k) for k in governed.keys())
    metadata = {str(k): v if isinstance(v, dict) else {} for k, v in governed.items()}
    return edge_ids, metadata
