import json
import sys
import os
import importlib
import subprocess
from typing import Any, Dict, Optional, TypeVar
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from .config_utils import generate_config, get_settings_cls, merge_defaults_into_config
from .environment_manager import prepare_venv, load_env
from .default_settings import DefaultSettings

T = TypeVar("U", bound=DefaultSettings)

# TODO: Make return value a pydantic model
def run_job(job_name: str, payload: dict = {}) -> dict:
  # Sanity check
  merge_defaults_into_config()

  load_env(job_name)

  # Install dependencies
  req_file = Path("jobs") / job_name / "requirements.txt"

  if req_file.exists():
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], check=True)

  settings_class = get_settings_cls(job_name)
  config: DefaultSettings = generate_config(settings_class, job_name)

  if not config.enabled:
    return {"message": "Job is disabled in config."}

  venv_path = prepare_venv(job_name)

  module_path = "core.job_runner"

  if os.name == "nt":
    python_path = venv_path / "Scripts" / "python.exe"
    if not python_path.exists(): # fallback for MSYS2 layout (bash for windows python3 alias)
      python_path = venv_path / "bin" / "python.exe"
  else:
    python_path = venv_path / "bin" / "python"

  stdin_data = {
    "job_name": job_name,
    "config": config.model_dump(),
    "payload": payload or {}
  }

  result = subprocess.run(
    [str(python_path), "-m", module_path],
    input=json.dumps(stdin_data).encode(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )

  if result.returncode != 0:
    raise Exception("Job failed\n" + result.stderr.decode())
  
  try:
    result = json.loads(result.stdout.decode())
  except json.JSONDecodeError:
    result = {}

  return result

def _extract_payload(
  request: Request,
  body: Optional[Dict[str, Any]] = Body(default=None),
) -> Dict[str, Any]:
  payload: Dict[str, Any] = {}

  if body:
    payload.update(body)

  # `request.query_params` is ImmutableMultiDict ‑> cast to plain dict
  if request.query_params:
    payload.update(request.query_params.multi_items())

  # normalise booleans that came in as strings
  for k, v in payload.items():
    if isinstance(v, str) and v.lower() in {"true", "false"}:
      payload[k] = v.lower() == "true"

  return payload

router = APIRouter(prefix="/run", tags=["jobs"])
@router.api_route(
  "/{job_name}",
  methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
  status_code=status.HTTP_200_OK,
)
async def run_job_endpoint(
  job_name: str,
  background: BackgroundTasks,
  request: Request,
  payload: Dict[str, Any] = Depends(_extract_payload),
):
  ack = bool(payload.pop("acknowledgment", False))

  if not ack:
    # fire‑and‑forget
    background.add_task(run_job, job_name, payload=payload)
    return Response(status_code=status.HTTP_200_OK)
  else:
    try:
      result = run_job(job_name, payload=payload)
    except Exception as exc:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
      ) from exc

    return JSONResponse(content={"acknowledgment": "completed", "result": result})

def main():
  raw = sys.stdin.read()
  try:
    data = json.loads(raw)
  except json.JSONDecodeError:
    print("Invalid JSON on stdin", file=sys.stderr)
    sys.exit(1)

  job_name: str = data["job_name"]
  config_dict = data["config"]
  payload = data.get("payload", {})

  if not job_name:
    print("Job name missing from input", file=sys.stderr)
    sys.exit(1)

  if not config_dict:
    print("Config missing from input", file=sys.stderr)
    sys.exit(1)

  SettingsCls = get_settings_cls(job_name)
  try:
    config = SettingsCls(**config_dict)
  except Exception as e:
    print(f"Config validation failed: {e}", file=sys.stderr)
    sys.exit(1)

  # Import job module and call run()
  job_mod = importlib.import_module(f"jobs.{job_name}.job")
  if not hasattr(job_mod, "run"):
    print(f"'run' function missing in jobs.{job_name}.job", file=sys.stderr)
    sys.exit(1)

  try:
    job_mod.run(config=config, payload=payload)
  except Exception as e:
    print(f"Job runtime error: {e}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
  main()
