from dagster import ScheduleDefinition, define_asset_job, AssetSelection
from .assets import SITES

# 1. Define a master job that runs the entire pipeline
full_etl_job = define_asset_job(
    name="full_etl_pipeline",
    selection=AssetSelection.all(),
    description="Runs the full ETL pipeline for all configured sites and merges them."
)

# Schedule the master job to run every day at 3:00 AM Amsterdam Time
full_etl_schedule = ScheduleDefinition(
    job=full_etl_job,
    cron_schedule="0 3 * * *", # Every day at 3:00 AM
    execution_timezone="Europe/Amsterdam"
)

# 2. Optional: Create specific jobs for each site (useful for manual triggers)
site_jobs = []
for site_key in SITES.keys():
    job = define_asset_job(
        name=f"etl_{site_key}_job",
        selection=AssetSelection.assets(f"extract_{site_key}", f"transform_{site_key}", f"load_{site_key}"),
        description=f"Runs the full ETL pipeline exclusively for {site_key}"
    )
    site_jobs.append(job)

all_jobs = [full_etl_job] + site_jobs
all_schedules = [full_etl_schedule]