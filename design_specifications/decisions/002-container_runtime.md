# Decision 002 – Container Runtime

## Options Evaluated
1. **Bare metal** (uv only)
2. **Podman Compose**

## Decision
Use **Podman Compose** as the container runtime.

## Why Podman Compose fits
- Daemonless, rootless by default — more secure
- Each module runs as isolated container — truer to event-driven architecture
