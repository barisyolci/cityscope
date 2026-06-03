from dagster import Definitions

from automize_etl_dagster.assets import all_assets
from automize_etl_dagster.schedules import all_jobs, all_schedules

defs = Definitions(
    assets=all_assets,
    jobs=all_jobs,
    schedules=all_schedules,
)