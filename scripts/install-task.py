#!/usr/bin/env python3
"""Register an idempotent DSM Task Scheduler job, without editing system cron."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
API = "/usr/syno/bin/synowebapi"
NAME = "Orca image auto-update"

def call(method, **params):
    args = [API, "--exec", "api=SYNO.Core.TaskScheduler", "version=1", "method=" + method]
    args += [key + "=" + (json.dumps(value) if not isinstance(value, str) else value) for key, value in params.items()]
    result = json.loads(subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL))
    if not result.get("success"):
        raise RuntimeError("DSM task API rejected request: " + json.dumps(result.get("error")))
    return result.get("data", {})

for task in call("list").get("tasks", []):
    if task.get("name") == NAME:
        print("Task already exists, id=" + str(task["id"]))
        break
else:
    result = call("create", name=NAME, owner="root", type="script", enable=True,
        schedule={"date": time.strftime("%Y/%m/%d"), "date_type": 0, "hour": 5, "minute": 30,
                  "last_work_hour": 23, "repeat_date": 0,
                  "repeat_hour": 0, "week_day": "0,1,2,3,4,5,6"},
        extra={"notify_enable": False, "notify_if_error": False, "notify_mail": "",
               "script": '/usr/bin/python3 "' + str(ROOT / "scripts/auto-update.py") + '"'})
    print("Created task: " + json.dumps(result))
