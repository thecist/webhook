# Think of this as mini orchestrators for testing
from .job import run
from core.config_utils import generate_config, merge_defaults_into_config, get_settings_cls
from dotenv import load_dotenv

JOB_NAME="notion_rss"

# For testing, that way python -m jobs.notion_rss works
load_dotenv(dotenv_path=f"jobs/{JOB_NAME}/.env")

if __name__ == "__main__":
  # Sanity check, incase new defaults come in
  merge_defaults_into_config()

  # Load config
  settings_class = get_settings_cls(JOB_NAME)
  config = generate_config(settings_class, JOB_NAME)

  run(config=config)