"""Create/update the serving endpoint for one model version. Used by the deployment job and rollback."""

from __future__ import annotations

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.serving import (
    AiGatewayConfig,
    AiGatewayInferenceTableConfig,
    EndpointCoreConfigInput,
    EndpointTag,
    Route,
    ServedEntityInput,
    TrafficConfig,
)

SERVED_ENTITY = "champion"


def deploy_version(
    w: WorkspaceClient,
    endpoint: str,
    model_name: str,
    version: str,
    env: str,
    catalog: str,
    schema: str,
) -> None:
    entity = ServedEntityInput(
        name=SERVED_ENTITY,
        entity_name=model_name,
        entity_version=str(version),
        workload_size="Small",
        scale_to_zero_enabled=True,
    )
    traffic = TrafficConfig(
        routes=[Route(served_entity_name=SERVED_ENTITY, traffic_percentage=100)]
    )

    try:
        w.serving_endpoints.get(endpoint)
    except NotFound:
        print(f"creating endpoint {endpoint}")
        config = EndpointCoreConfigInput(served_entities=[entity], traffic_config=traffic)
        tags = [EndpointTag(key="env", value=env), EndpointTag(key="project", value="taxi-mlops")]
        # Inference table = request/response log for monitoring. Best effort: may be
        # unavailable on Free Edition, and serving must still work without it.
        gateway = AiGatewayConfig(
            inference_table_config=AiGatewayInferenceTableConfig(
                catalog_name=catalog,
                schema_name=schema,
                table_name_prefix="taxi_fare",
                enabled=True,
            )
        )
        try:
            w.serving_endpoints.create_and_wait(
                name=endpoint, config=config, ai_gateway=gateway, tags=tags
            )
        except Exception as e:
            print(f"WARN: create with inference table failed ({e}); retrying without it")
            w.serving_endpoints.create_and_wait(name=endpoint, config=config, tags=tags)
        return

    print(f"updating endpoint {endpoint} -> {model_name} v{version}")
    w.serving_endpoints.update_config_and_wait(
        name=endpoint, served_entities=[entity], traffic_config=traffic
    )
