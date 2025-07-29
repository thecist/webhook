# TheCist Webhook

This project provides a flexible webhook and job runner system for background and synchronous jobs. It supports CLI and HTTP API interaction, dynamic configuration, and CRON-based scheduling.

## Features

- **Webhook API**: Trigger jobs via HTTP requests using FastAPI.
- **CLI**: Run and manage jobs and configuration from the command line.
- **CRON Scheduling**: Schedule jobs using cron expressions.
- **Dynamic Configuration**: Update job settings via CLI, API or TOML.
- **Virtual Environments**: Isolated Python environments per job.

## Folder Structure

- `app.py` — FastAPI server entrypoint.
- `cli.py` — Command-line interface for job management.
- `core/` — Core logic (config, cron, environment, job runner...).
- `jobs/` — Contains all job modules. See [Jobs](#jobs) for detail.
- `defaults.toml` — Default configuration.
- `configs.toml` — User configuration.
- `.env` / `.env.example` — Environment variables.

## Getting Started

### 0. (Optional) Create and Activate a Virtual Environment

It is recommended to use a virtual environment to isolate your dependencies.

On Windows:
```sh
python.exe -m venv .venv
.venv\Scripts\activate
```

On macOS/Linux:
```sh
python -m venv .venv
source .venv/bin/activate
```

### 1. Install Dependencies

```sh
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in required secrets.

```sh
cp .env.example .env
```

Edit `configs.toml` to enable jobs and set scheduling.

## Interacting with WebHook

### Using CLI

Create `configs.toml` 
```sh
python -m cli create-config
```
`configs.toml` can be edited manually afterwards or with
CLI/API

Enable or disable jobs:
```sh
python -m cli enable notion_rss
python -m cli disable notion_rss
```

Set configuration values:
```sh
python -m cli set notion_rss.enabled=true notion_rss.defaults.view_id_title=ID
```

Run a job manually:
```sh
python -m cli.py run-job notion_rss
```

Test a job locally:
```sh
python -m jobs.<job_name>
```
Update `__main__.py` for testing

### Using API Server

```sh
python -m app
```

- Health Check: `GET /`
- Run Job: `GET|POST|PUT|PATCH|DELETE| /run/{job_name}` (with optional payload)

### Using CRON

Set up cron jobs for enabled jobs:

```sh
python -m cli.py setup-scheduler
```

## Jobs

All jobs are located in the `jobs/` directory. Each job is a self-contained module with the following structure:

- `job.py`: Main entrypoint for the job. Must define:
  - `run(config, payload)`: Executes the job logic using configuration and payload.
  - `JOB_SETTINGS_CLASS`: Pydantic or custom settings class for job configuration.
- `__main__.py`: Allows testing the job directly via `python -m jobs.<job_name>`.
- `README.md`: In-depth documentation for the job.
- `requirements.txt`: Job-specific dependencies.
- `.env.example` / `.env`: Job-specific environment variables.

*Note: You can add your environment variables in the root `.env` too*

Example job structure:

```
jobs/
  └── example_job/
      ├── __init__.py
      ├── __main__.py
      ├── .env
      ├── .env.example
      ├── job.py
      ├── README.md
      └── requirements.txt
```

### Contributing to Jobs

To add a new job:

1. **Create a new folder** in `jobs/` with your job name.
2. **Implement `job.py`** with a `run(config, payload)` function and a `JOB_SETTINGS_CLASS`.
3. **Define configuration** that inherits fron `DefaultSettings` using Pydantic.
4. **Add `__main__.py`** for standalone testing (`python -m jobs.<job_name>`).
5. **Document your job** in `README.md` (purpose, config, usage, environment variables).
6. **Provide `.env.example` and `.env`** for secrets and environment variables.
7. **List dependencies** in `requirements.txt`.
8. **Update `defaults.toml`** with your job's default configurations

Each job should be independent, with its own config, environment, and documentation. For more details, see the job’s individual `README.md`.

## Development

- Python 3.11+
- See `requirements.txt` for dependencies.
- Use `.venvs/` for per-job virtual environments.

## Future Goals

- 95% Test Coverage
- UI for job management
- Multi-Platform CRON support (+Windows)
- API-based configuration updates
- Github workflows integration
- CLI payload support
