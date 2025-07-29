import sys
from crontab import CronTab
from pathlib import Path

# Replace with your user (or system=True if you want system-level crons)
cron = CronTab(user=True)
root_dir = Path.cwd()

def update_cron(job_name: str, job_config: dict = None):
  from .config_utils import load_config
  if not job_config:
    config = load_config()
    job_config = config[job_name]

  job_exists = False
  for job in cron.find_comment(job_name):
    job_exists = True
    break

  if isinstance(job_config, dict):
    if job_config.get("enabled", False) and job_config.get("cron", None):
      if not job_exists:
        command = f"cd {root_dir} && {sys.executable} -m cli run-job {job_name} >> /var/log/{job_name}.log 2>&1"
        job = cron.new(command=command, comment=job_name)
        job.setall(job_config["cron"])
        if not job.is_valid():
          print(f"Invalid cron schedule: {job_config['cron']}")
        cron.write()
    else:
      # If job is disabled, or cron is not set, remove from cron
      if job_exists:
        for job in cron.find_comment(job_name):
          cron.remove(job)
        cron.write()
