#!/usr/bin/env python3

import requests
import pandas as pd
from pprint import pprint
import json
import os
from tqdm.auto import tqdm
import os

URL = "https://connect.pharmac.govt.nz/apptracker/s/sfsites/aura"

df = pd.read_csv("applications.csv")
print(df)

for record_id in tqdm(df.Id):
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
                        }
                    ]
                }
            ),
            "aura.context": '{"mode":"PROD","fwuid":"eUNJbjV5czdoejBvRlA5OHpDU1dPd1pMVExBQkpJSlVFU29Ba3lmcUNLWlE5LjMyMC4y","app":"siteforce:communityApp","loaded":{"APPLICATION@markup://siteforce:communityApp":"1184_AgcTXn_6dZSShHXZ2PZsug"},"dn":[],"globals":{},"uad":false}',
            "aura.token": "null",
        },
    ).json()
    os.makedirs("applications", exist_ok=True)
    try:
        with open(f"applications/{record_id}.json", "w") as f:
            data = json.loads(resp["actions"][0]["returnValue"])
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error for {record_id}: {e}")
