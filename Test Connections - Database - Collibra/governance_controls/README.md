# Governance controls

`governance_controls` contains runnable automations (“controls”) built on top of the SDK in
`collibra_client/`. A control is meant to be executed on a schedule (or on demand) and produces:

- validation results (pass/fail + reason)
- an owner-oriented view of impact (who should fix it)
- audit-friendly logs you can archive

## Available controls

### `test_edge_connections` (connection validation)

Validates Collibra Edge connections and polls the resulting jobs until completion. Failed
connections are mapped to impacted Catalog database assets and their owners.

Documentation and CLI reference: `governance_controls/test_edge_connections/README.md`.

## Run a control

### Running a Control

Each control has its own entry point with multiple enforcement modes. For example, the Connection Validation Control:

```bash
# Targeted enforcement: Validate specific connections within an Edge Site
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id <edge-site-id> --connection-id <conn-id1> --connection-id <conn-id2>

# Direct validation: Test specific connections by ID
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --connection-id <conn-id1> --connection-id <conn-id2>

# Batch enforcement: Validate all connections under Edge Sites
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id <edge-site-id>

# Governed scope: Validate the full governed perimeter from YAML config
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py
```

### Defining the Governed Scope

Controls use YAML configuration files to define which infrastructure falls under governance. This configuration is version-controlled, providing an auditable record of what is governed and who is responsible:

```yaml
# governance_controls/test_edge_connections/governed_connections.yaml
governed_connections:
  "edge-site-id-1":
    name: "Production Edge Site"
    description: "Production Snowflake connections"
    environment: "production"
    owner_team: "Data Platform Team"
```

### Adding New Controls

1. Create a subdirectory under `governance_controls/`
2. Implement the detection, analysis, and mapping logic using the SDK
3. Add a YAML configuration file defining the governed scope
4. Create an entry point script with CLI argument support
5. Document the governance risk, enforcement behavior, and usage in a README

See the [Connection Validation Control](./test_edge_connections/README.md) for a reference implementation.
