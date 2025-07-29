import typer
import re
from pathlib import Path
from core.config_utils import save_configs, merge_defaults_into_config, load_config
from core.job_runner import run_job as core_run_job
from core.cron import update_cron
# Should I update cron the moment a setting changes?

# TODO: Add custom logging
# TODO: Support system level task scheduling on Windows

CONFIGS_PATH = Path("configs.toml")

app = typer.Typer()

def _toggle_job(job_name: str, toggle: bool):
  config = load_config()
  if job_name not in config or not isinstance(config[job_name], dict):
    raise typer.Exit(f"Configuration for job '{job_name}' not found or invalid (has to be a dictionary)")
  config[job_name]["enabled"] = toggle
  save_configs(config)

@app.command()
def enable(job_name: str):
  _toggle_job(job_name, True)
  typer.echo(f"Enabled job: {job_name}")

@app.command()
def create_config():
  merge_defaults_into_config()
  typer.echo(f"Created config file: {CONFIGS_PATH}")

@app.command()
def disable(job_name: str):
  _toggle_job(job_name, False)
  typer.echo(f"Disabled job: {job_name}")

def _set_nested_value(data: dict, dotted_key: str, value):
  keys = dotted_key.split(".")
  current = data
  for key in keys[:-1]:
    current = current.setdefault(key, {})
  if value is None:
    del current[keys[-1]]
  else:
    current[keys[-1]] = value


@app.command("set")
def set_config(kv_pairs: list[str]):
  # Sanity check
  merge_defaults_into_config()

  typer.echo("Note: If a key is not defined in the job's settings model, it will be ignored.", color=True)

  config = load_config()

  for pair in kv_pairs:
    match = re.match(r"^([\w\.]+)=(.*)$", pair)
    if not match:
      typer.echo(f"Invalid format: {pair} (expected key=value)")
      continue
    key, raw_value = match.groups()

    # Parse value to other supported styles
    value = raw_value.strip()
    if value.lower() == "true":
      value = True
    elif value.lower() == "false":
      value = False
    elif re.fullmatch(r"-?\d+", value):
      value = int(value)
    elif re.fullmatch(r"-?\d+\.\d+", value):
      value = float(value)
    elif value.startswith('"') and value.endswith('"'):
      value = value[1:-1]
    elif value.startswith("'") and value.endswith("'"):
      value = value[1:-1]
    elif value.lower() == "none":
      value = None

    _set_nested_value(config, key, value)
    typer.echo(f"Set {key} = {value!r}")
  save_configs(config)

# maybe implement the acknowledgement logic here too?
@app.command()
def run_job(job_name: str):
  typer.echo(f"Running job: {job_name}")
  result = core_run_job(job_name)
  typer.echo(f"Job finished: {job_name}\nResult: {result}")

@app.command()
def setup_scheduler():
  config = load_config()
  for job_name, data in config.items():
    update_cron(job_name, data)

if __name__ == "__main__":
  app()
