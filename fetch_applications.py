#!/usr/bin/env python3

import requests
import pandas as pd
from pprint import pprint
import json
import os
from tqdm.auto import tqdm
import os

URL = "https://connect.pharmac.govt.nz/apptracker/s/sfsites/aura"

df = pd.concat(pd.read_csv(f) for f in ["CS_CN.csv", "Decline.csv", "OFI.csv"])
print(df)
record_ids = set(df.Community_URL.str.replace("/apptracker/s/application-public/", ""))
set_of_existing = set([f.replace("_meta.csv", "") for f in os.listdir("applications") if f.endswith("_meta.csv")])
record_ids = record_ids.union(set_of_existing)
print(record_ids)

for record_id in tqdm(record_ids):
    resp = requests.post(
        URL,
        data={
            "message": json.dumps(
                {
                    "actions": [
                        {
                            "id": "108;a",
                            "descriptor": "apex://AppTrackerController/ACTION$getStateJson",
                            "callingDescriptor": "markup://c:AppTracker_List",
                            "params": {
                                "applicationId": record_id,
                                "expandAll": True,
                            },
                        },
                        {
                            "id": "150;a",
                            "descriptor": "apex://AppTrackerController/ACTION$getAppInfo",
                            "callingDescriptor": "markup://c:AppTracker_Info",
                            "params": {"appId": record_id},
                        },
                    ]
                }
            ),
            "aura.context": '{"mode":"PROD","fwuid":"eUNJbjV5czdoejBvRlA5OHpDU1dPd1pMVExBQkpJSlVFU29Ba3lmcUNLWlE5LjMyMC4y","app":"siteforce:communityApp","loaded":{"APPLICATION@markup://siteforce:communityApp":"1184_AgcTXn_6dZSShHXZ2PZsug"},"dn":[],"globals":{},"uad":false}',
            "aura.token": "null",
        },
    ).json()
    by_id = {}
    for a in resp["actions"]:
        by_id[a["id"]] = a
    meta = by_id["150;a"]["returnValue"]
    meta = pd.DataFrame(meta).head(1)
    os.makedirs("applications", exist_ok=True)
    meta.to_csv(f"applications/{record_id}_meta.csv", index=False)
    try:
        df = pd.DataFrame(json.loads(by_id["108;a"]["returnValue"]))
        df.to_csv(f"applications/{record_id}.csv")
    except Exception as e:
        print(f"Error for {record_id}: {e}")
