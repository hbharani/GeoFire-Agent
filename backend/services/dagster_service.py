import httpx
from core.config import settings

class DagsterService:
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
        __typename
        ... on Run { status }
        ... on RunNotFoundError { message }
        ... on PythonError { message }
      }
    }
    """

    @staticmethod
    async def trigger_job(red_path: str, nir_path: str, utility_path: str, canopy_path: str, swir_path: str, project_id: str, run_id: str) -> dict:
        run_config = {
            "ops": {
                "ingest_red_band": {"config": {"file_path": red_path}},
                "ingest_nir_band": {"config": {"file_path": nir_path}},
                "ingest_utility_lines": {"config": {"file_path": utility_path}},
                "ingest_canopy_height": {"config": {"file_path": canopy_path}},
                "ingest_swir_band": {"config": {"file_path": swir_path}},
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
                settings.DAGSTER_URL, json={"query": DagsterService.LAUNCH_RUN_MUTATION, "variables": variables},
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_run_status(run_id: str) -> str:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                settings.DAGSTER_URL, 
                json={"query": DagsterService.RUN_STATUS_QUERY, "variables": {"runId": run_id}}
            )
            response.raise_for_status()
            payload = response.json()
            
            if "errors" in payload:
                raise Exception(f"Dagster GraphQL Error: {payload['errors']}")
            
            data = payload.get("data")
            if not data or "pipelineRunOrError" not in data:
                raise Exception(f"Malformed Dagster response: missing expected data for run {run_id}")

            result = data["pipelineRunOrError"]
            typename = result.get("__typename")

            if typename == "Run":
                return result.get("status", "UNKNOWN").upper()
            elif typename == "RunNotFoundError":
                raise Exception(f"Dagster Run Not Found: {result.get('message')}")
            elif typename == "PythonError":
                raise Exception(f"Dagster Python Error: {result.get('message')}")
            else:
                raise Exception(f"Unexpected Dagster response type: {typename}")
