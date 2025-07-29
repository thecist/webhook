from typing import Type, TypeVar, Any
from pathlib import Path
import tomllib
import tomli_w
import importlib
import os
from pydantic import BaseModel, ValidationError, create_model
from pydantic.fields import PydanticUndefined
from .default_settings import DefaultSettings
from .cron import update_cron

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=DefaultSettings)
CONFIGS_PATH = Path("configs.toml")
DEFAULTS_PATH = Path("defaults.toml")

class ConfigError(RuntimeError):
  """Raised when user-editable keys are missing in config,
  or env-only keys are missing in the environment."""
  pass

def _deep_merge_defaults(default: dict, config: dict) -> None:
  for key, value in default.items():
    if isinstance(value, dict):
      if key not in config or not isinstance(config[key], dict):
        config[key] = {}
      _deep_merge_defaults(value, config[key])
    else:
      if key not in config:
        config[key] = value

# Maybe type check before merging
# TODO: Create a test to ensure defaults.toml is up-to-date
# And doesn't have extra keys
def merge_defaults_into_config() -> None:
  with DEFAULTS_PATH.open("rb") as f:
    default_data = tomllib.load(f)

  if CONFIGS_PATH.exists():
    with CONFIGS_PATH.open("rb") as f:
      config_data = tomllib.load(f)
  else:
    config_data = {}

  _deep_merge_defaults(default_data, config_data)

  with CONFIGS_PATH.open("wb") as f:
    f.write(tomli_w.dumps(config_data).encode("utf-8"))

def _populate_and_validate(
  model: Type[BaseModel],
  data: dict[str, Any],
  prefix: str,
  path: str = ""
) -> None:
  for name, field in model.model_fields.items():
    full_path = f"{path}.{name}" if path else name
    extra = field.json_schema_extra or {}

    user_editable = extra.get("user_editable", False)
    no_default = (field.default is PydanticUndefined) and (
      field.default_factory is None or field.default_factory is PydanticUndefined
    )

    if isinstance(field.annotation, type) and issubclass(
      field.annotation, BaseModel
    ):
      # nested Pydantic model
      data.setdefault(name, {})
      _populate_and_validate(
        field.annotation,
        data[name],
        prefix,
        full_path
      )
      continue
    

    if user_editable:
      if name not in data and no_default:
        raise ConfigError(
          f"Missing key '{full_path}' "
          f"in {DEFAULTS_PATH} and {CONFIGS_PATH} for job '{prefix.lower()}'"
          f".\n Add it to {CONFIGS_PATH} to prevent git congflicts."
        )
    else:
      env_key = f"{prefix}{name.upper()}"
      if name not in data:
        env_val = os.getenv(env_key)
        if env_val is None and no_default:
          raise ConfigError(
            f"Missing env var '{env_key}' for job '{prefix.lower()}'"
            f".\n Add env var to .env or jobs/${prefix.lower()[:-1]}/.env."
          )
        if env_val:
          data[name] = env_val

def generate_config(
  cls: Type[T],
  job_name: str
) -> T:
  """
  Load and validate config for a job.
  Priority: TOML > prefixed environment variables
  """
  job_name_upper = job_name.upper()

  if CONFIGS_PATH.exists():
    with CONFIGS_PATH.open("rb") as f:
      full_data = tomllib.load(f)
  else:
    full_data = {}

  if job_name not in full_data:
    raise KeyError(f"Configuration for job '{job_name}' not found")

  job_data = full_data[job_name]

  _populate_and_validate(cls, job_data, f"{job_name_upper}_")

  try:
    return cls(**job_data)
  except ValidationError as e:
    raise ConfigError(
      f"Pydantic validation failed for job '{job_name}':\n{e}"
    ) from e

def get_settings_cls(job_name: str) -> U:
  job_dir = Path(f"jobs/{job_name}")
  job_path = job_dir / "job.py"

  if not job_path.exists():
    raise FileNotFoundError(
      f"Settings file not found for job '{job_name}'.\n"
      f"Ensure you have a 'job.py' file in {job_dir}."
    )
  module_path = f"jobs.{job_name}.job"

  module = importlib.import_module(module_path)

  if not hasattr(module, "JOB_SETTINGS_CLASS"):
    raise RuntimeError(f"'JOB_SETTINGS_CLASS' not found in {job_path}")

  cls = getattr(module, "JOB_SETTINGS_CLASS")

  if not issubclass(cls, DefaultSettings):
    raise TypeError(f"JOB_SETTINGS_CLASS must be a subclass of DefaultSettings")

  return cls

def _extract_user_editable(model: Type[DefaultSettings]) -> Type[BaseModel]:
  fields: dict[str, tuple[Any, Any]] = {}

  for name, field in model.model_fields.items():
    extra = field.json_schema_extra or {}
    user_editable = extra.get("user_editable", False)

    annotation = field.annotation

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
      # Recurse into nested model
      nested_model = _extract_user_editable(annotation)
      if nested_model.model_fields:
        # fields[name] = (nested_model, ...)
        fields[name] = (nested_model, field)
    elif user_editable:
      # Include field as-is
      # fields[name] = (annotation, field.default if field.default is not None else ...)
      fields[name] = (annotation, field)

  return create_model(f"{model.__name__}EditableOnly", **fields)

# TODO: Update this to throw errors instead of print them
# That way other guys can catch it and handle it
def save_configs(config: dict):
  final_config = {}
  for job_name, value in config.items():
    if isinstance(value, dict):
      # Validate
      SettingsClass = get_settings_cls(job_name)
      EditableSettings = _extract_user_editable(SettingsClass)
      settings = EditableSettings(**value)

      final_config[job_name] = settings.model_dump(exclude_none=True)
      update_cron(job_name, final_config[job_name])
    else:
      # raise? Do I need to make it atomic?
      print(f"Error: Configuration has to be a dictionary\n\n job: {job_name}\n value: {value}")

  with CONFIGS_PATH.open("wb") as f:
    f.write(tomli_w.dumps(final_config).encode("utf-8"))

def load_config() -> dict:
  if CONFIGS_PATH.exists():
    with CONFIGS_PATH.open("rb") as f:
      full_data = tomllib.load(f)
  else:
    full_data = {}
  return full_data