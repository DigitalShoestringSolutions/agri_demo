# Standard library imports
import logging
import datetime

# Internal module imports
import analysis.general
from trigger.engine import TriggerEngine
from pipeline import Pipeline
import analysis.electrical
import query.influx
import config_manager
import output.influx


# Parse command-line arguments and configure logging again based on those
args = config_manager.handle_args()
logging.basicConfig(level=args["log_level"])
logger = logging.getLogger(__name__)

# Load configuration from config files
config = config_manager.get_config(
    args.get("module_config_file"), args.get("user_config_file")
)

# Initialize the trigger engine with loaded configuration
trigger = TriggerEngine(config)

"""
In Chat GPT enter:
    My cron implementation treats day of week and day of month as an AND. 
    I don't want logic in a script. What is the cron tab expression for 
followed by when you want it to run.
it will give you a set of 5 numbers or characters separated by a space. Put that in the task.

For example: every friday at 17:00 gives:
0 18 * * 5 your-command

so we would use: "0 18 * * 5"

Another example: fourth friday of the month at 6pm:
"0 18 22-28 * 5"

Every ten minutes:
"*/10 * * * *"

"""


"""
Explanation of cron syntax for task scheduling using the @trigger.scheduler.task decorator.
Examples:
- Every Friday at 6pm:          "0 18 * * 5"
- Fourth Friday of the month:  "0 18 22-28 * 5"
- Every 10 minutes:            "*/10 * * * *"
"""


# Scheduled task that runs every minute to calculate power usage
@trigger.scheduler.task("* * * * *")  # Cron: every minute
async def calculate_power(last_run=None, execution_time=None, config={}):
    pipeline = Pipeline.start()

    # Use an offset to ensure all necessary data is available (e.g., due to data delays)
    historic_offset = datetime.timedelta(minutes=1)
    window_start = last_run - historic_offset
    window_end = execution_time - historic_offset
    
    logger.info(f"## Calculate power task: {window_start} {window_end}")
    
    if window_end-window_start > datetime.timedelta(days=1):
        logger.error("Power window exceeds a day - skipping")
        return
        

    # Pipeline steps: fetch data -> compute power -> write results
    await pipeline.next(
        query.influx.current_and_voltage(config, window_start, window_end)
    )
    await pipeline.next(analysis.electrical.calculate_power(config))
    await pipeline.next(
        output.influx.write(
            config,
            "equipment_power_usage",
            timestamp_col="_time",
            tag_cols=["machine"],
            field_cols=["power_real", "power_apparent"],
        )
    )


# HTTP endpoint to calculate latest power based on provided timestamp and machine
@trigger.http.response("GET", "/power")
async def calculate_latest_power(request_data, config={}):
    pipeline = Pipeline.start()

    query_params = request_data["query"]
    dt_to_raw = query_params.get("to")[0]
    machine = query_params.get("machine")[0] if "machine" in query_params else None
    dt_to = datetime.datetime.fromisoformat(dt_to_raw)

    # Pipeline steps: fetch latest data -> compute power -> return as JSON
    await pipeline.next(query.influx.latest_current_and_voltage(config, dt_to, machine))
    await pipeline.next(analysis.electrical.calculate_power(config))
    out_df = pipeline.result

    # Convert datetime to string for JSON serialization
    out_df["_time"] = out_df["_time"].map(lambda x: x.isoformat())

    return 200, out_df.to_dict(orient="records")


# Scheduled task every 10 minutes to calculate energy usage from real power
@trigger.scheduler.task("*/10 * * * *")  # Cron: every 10 minutes
async def calculate_energy(last_run=None, execution_time=None, config={}):
    pipeline = Pipeline.start()

    historic_offset = datetime.timedelta(minutes=5)
    window_start = last_run - historic_offset
    window_end = execution_time - historic_offset
    
    logger.info(f"## Calculate energy task: {window_start} {window_end}")
    
    if window_end-window_start > datetime.timedelta(days=1):
        logger.error("Power window exceeds a day - skipping")
        return

    # Pipeline: fetch real power -> compute energy -> write to InfluxDB
    await pipeline.next(
        query.influx.real_power(
            config, window_start, window_end
        )
    )
    await pipeline.next(analysis.electrical.calculate_energy(config))
    await pipeline.next(
        output.influx.write(
            config,
            "energy",
            timestamp_col="_time",
            tag_cols=["machine"],
            field_cols=["energy"],
        )
    )


# HTTP endpoint to aggregate and analyze energy data over a specified period and resolution
@trigger.http.response("GET", "/period")
async def energy_by_period(request_data, config={}):
    pipeline = Pipeline.start()

    query_params = request_data["query"]
    logger.info(query_params)

    dt_to_raw = query_params.get("to")[0]
    dt_from_raw = query_params.get("from")[0]
    window = query_params.get("window")[0]
    machine = query_params.get("machine")[0] if "machine" in query_params else None

    dt_to = datetime.datetime.fromisoformat(dt_to_raw)
    dt_from = datetime.datetime.fromisoformat(dt_from_raw)

    # Step 1: fetch energy data from Influx
    await pipeline.next(query.influx.energy(config, dt_from, dt_to, window, machine))

    # Define bucketing and series grouping logic for different time windows
    settings_collection = {
        "1h": {
            "bucket_function": lambda timestamp: (
                timestamp.hour,
                timestamp.strftime("%H:00"),
            ),
            "series_function": lambda timestamp: (
                timestamp.year * 10000 + timestamp.month * 100 + timestamp.day,
                timestamp.strftime("%d/%m/%Y"),
            ),
        },
        "1d": {
            "bucket_function": lambda timestamp: (
                timestamp.weekday(),
                timestamp.strftime("%A"),
            ),
            "series_function": lambda timestamp: (
                int(timestamp.strftime("%Y%W")),
                timestamp.strftime("Week %W, %Y"),
            ),
        },
        "1w": {
            "bucket_function": lambda timestamp: (
                int(timestamp.strftime("%Y%W")),
                timestamp.strftime("Week %W"),
            ),
            "series_function": lambda timestamp: (
                timestamp.year,
                timestamp.strftime("%Y"),
            ),
        },
    }

    settings = settings_collection[window]

    # Log raw results, then perform period-over-period bucketing analysis
    logger.info(pipeline.result.to_string())
    await pipeline.next(
        analysis.general.period_over_period_buckets(
            settings["series_function"], settings["bucket_function"], value_key="energy"
        )
    )
    logger.info(pipeline.result)

    # Return the processed data
    return 200, pipeline.result


# Start the trigger engine and its scheduler/event loops
trigger.start()
