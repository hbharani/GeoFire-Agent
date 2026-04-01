import os
import httpx
import logging
from pathlib import Path

logger = logging.getLogger("geofire.services.dagster")

class DagsterService:
    DAGSTER_HOST = os.getenv("DAGSTER_HOST", "dagster")
    DAGSTER_PORT = os.getenv("DAGSTER_PORT", "3000")
    DAGSTER_URL = f"http://{DAGSTER_HOST}:{DAGSTER_PORT}/graphql"

    LAUNCH_RUN_MUTATION = """
    mutation LaunchRun($config: RunConfigData!, $jobName: String!, $repositoryLocationName: String!, $repositoryName: String!) {
      launchRun(
        executionParams: {
          selector: {
            jobName: $jobName
            repositoryLocationName: $repositoryLocationName
            repositoryName: $repositoryName
          }
          runConfigData: $config
        }
      ) {
        __typename
        ... on LaunchRunSuccess { run { runId } }
        ... on PythonError { message }
      }
    }
    """

    RUN_STATUS_QUERY = """
    query GetRunStatus($runId: ID!) {
      pipelineRunOrError(runId: $runId) {
        ... on Run { status }
      }
    }
    """

    @staticmethod
    async def trigger_job(red_path: str, nir_path: str, utility_path: str, canopy_path: str, project_id: str, run_id: str) -> dict:
        run_config = {
            "ops": {
                "ingest_red_band": {"config": {"file_path": red_path}},
                "ingest_nir_band": {"config": {"file_path": nir_path}},
                "ingest_utility_lines": {"config": {"file_path": utility_path}},
                "ingest_canopy_height": {"config": {"file_path": canopy_path}},
                "mask_and_calculate_risk": {"config": {"project_id": project_id, "run_id": run_id}},
            }
        }
        variables = {
            "config": run_config,
            "jobName": "fire_risk_pipeline",
            "repositoryLocationName": "pipeline.py",
            "repositoryName": "__repository__",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                DagsterService.DAGSTER_URL, json={"query": DagsterService.LAUNCH_RUN_MUTATION, "variables": variables},
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_run_status(run_id: str) -> str:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                DagsterService.DAGSTER_URL, 
                json={"query": DagsterService.RUN_STATUS_QUERY, "variables": {"runId": run_id}}
            )
            data = response.json()
            return data.get("data", {}).get("pipelineRunOrError", {}).get("status", "UNKNOWN")
