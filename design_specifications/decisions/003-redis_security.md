# Decision 003 – Redis Security Model

## Options Evaluated
1. **No authentication** (open within network)
2. **Password authentication**
3. **TLS encryption**

## Decision
Use **no authentication** with strict network isolation.

## Why no auth fits
- All containers run in isolated Podman network
- Redis not exposed to host
- No external access possible
- Simplicity for development and sandbox

## Security constraint
The entire application must run within an isolated Podman network. Do not publish Redis port to host (`ports: - "6379:6379"`). This ensures Redis is only accessible to containers within the same compose project.

## Why password/TLS not chosen
- Adds complexity without security benefit for isolated network
- No external threat model for localhost-only deployment

## When to reconsider
If deploying to shared infrastructure or exposing services externally, add password authentication and TLS.
