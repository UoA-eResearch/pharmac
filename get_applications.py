#!/usr/bin/env python3
import requests
import pandas as pd
import json
from tqdm import tqdm

terms = requests.post("https://connect.pharmac.govt.nz/apptracker/s/sfsites/aura?r=2&other.AppTracker.getAutocompleteList=1", headers={
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,en-NZ;q=0.8",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Microsoft Edge\";v=\"144\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-b3-sampled": "0",
    "x-b3-spanid": "8a9df0cc8628823c",
    "x-b3-traceid": "6e194624388efafa",
    "x-sfdc-page-cache": "4a632cedf21b4d25",
    "x-sfdc-page-scope-id": "5abb70bb-5d78-41e4-a465-b72120dea91c",
    "x-sfdc-request-id": "10987000005b12c9da"
  },
  data="message=%7B%22actions%22%3A%5B%7B%22id%22%3A%2269%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerController%2FACTION%24getAutocompleteList%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_SearchBar%22%2C%22params%22%3A%7B%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22REdtNUF5ejJUNWxpdVllUjQtUzV4UTFLcUUxeUY3ZVB6dE9hR0VheDVpb2cxMy4zMzU1NDQzMi41MDMzMTY0OA%22%2C%22app%22%3A%22siteforce%3AcommunityApp%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AcommunityApp%22%3A%221422_wotCJi-4iLy4EgTPC6RQ4g%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Atrue%7D&aura.pageURI=%2Fapptracker%2Fs%2Fglobal-search%2Fket&aura.token=null",
).json()["actions"][0]["returnValue"]
print(len(terms))

applications = {}
for term in tqdm(terms):
  r = requests.post("https://connect.pharmac.govt.nz/apptracker/s/sfsites/aura?r=6&other.AppTracker.searchApplications=1", data={
      "message": json.dumps({"actions":[{"id":"108;a","descriptor":"apex://AppTrackerController/ACTION$searchApplications","callingDescriptor":"markup://c:AppTracker_SearchResults","params":{"searchTerm":term,"numberOfRecords":10000}}]}),
      "aura.context": '{"mode":"PROD","fwuid":"REdtNUF5ejJUNWxpdVllUjQtUzV4UTFLcUUxeUY3ZVB6dE9hR0VheDVpb2cxMy4zMzU1NDQzMi41MDMzMTY0OA","app":"siteforce:communityApp","loaded":{"APPLICATION@markup://siteforce:communityApp":"1422_wotCJi-4iLy4EgTPC6RQ4g"},"dn":[],"globals":{},"uad":true}',
      "aura.pageURI": "/apptracker/s/global-search/",
      "aura.token": "null"
    }
  )
  for a in r.json()["actions"][0]["returnValue"]:
    applications[a["Id"]] = a

df = pd.DataFrame(applications.values())
print(df)
df.to_csv("applications.csv", index=False)