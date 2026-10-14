from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: str = Field(description="Component status: 'up' or 'down'.")
    latency_ms: float | None = Field(
        default=None,
        description="Time taken to check the component, in milliseconds.",
    )


class HealthData(BaseModel):
    status: str = Field(description="Overall status: 'healthy' or 'unhealthy'.")
    version: str = Field(description="Running application version.")
    checks: dict[str, ComponentHealth] = Field(
        default_factory=dict,
        description="Per-dependency health results keyed by component name.",
    )
