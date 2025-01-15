#!/usr/bin/env python3

import requests
import pandas as pd
from pprint import pprint
import json
import os

URL = "https://connect.pharmac.govt.nz/apptracker/s/sfsites/aura"

resp = requests.post(URL, headers={
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
  },
  data="message=%7B%22actions%22%3A%5B%7B%22id%22%3A%22100%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.force.components.controllers.recordGlobalValueProvider.RecordGvpController%2FACTION%24getRecord%22%2C%22callingDescriptor%22%3A%22UNKNOWN%22%2C%22params%22%3A%7B%22recordDescriptor%22%3A%22a102P00000BS6MzQAL.undefined.FULL.null.null.null.VIEW.true.null.null.null%22%7D%7D%2C%7B%22id%22%3A%22101%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.communities.components.aura.components.forceCommunity.seoAssistant.SeoAssistantController%2FACTION%24getRecordAndTranslationData%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2FforceCommunity%3AseoAssistant%22%2C%22params%22%3A%7B%22recordId%22%3A%22a102P00000BS6Mz%22%2C%22fields%22%3A%5B%5D%2C%22activeLanguageCodes%22%3A%5B%5D%7D%2C%22version%22%3A%2262.0%22%7D%2C%7B%22id%22%3A%22108%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerController%2FACTION%24getStateJson%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_List%22%2C%22params%22%3A%7B%22applicationId%22%3A%22a102P00000BS6Mz%22%2C%22expandAll%22%3Afalse%7D%7D%2C%7B%22id%22%3A%22111%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.communities.components.aura.components.forceCommunity.richText.RichTextController%2FACTION%24getParsedRichTextValue%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2FforceCommunity%3ArichText%22%2C%22params%22%3A%7B%22html%22%3A%22%3Cp%3E%3Cb%20style%3D%5C%22font-size%3A%2036px%3B%20color%3A%20rgb(0%2C%200%2C%200)%3B%5C%22%3EApplication%20Tracker%3C%2Fb%3E%3C%2Fp%3E%22%7D%2C%22version%22%3A%2262.0%22%2C%22storable%22%3Atrue%7D%2C%7B%22id%22%3A%22115%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerController%2FACTION%24getStages%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_Path%22%2C%22params%22%3A%7B%7D%7D%2C%7B%22id%22%3A%22116%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerController%2FACTION%24getPathInfo%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_Path%22%2C%22params%22%3A%7B%22appId%22%3A%22a102P00000BS6Mz%22%7D%7D%2C%7B%22id%22%3A%22124%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.force.components.controllers.recordGlobalValueProvider.RecordGvpController%2FACTION%24getRecord%22%2C%22callingDescriptor%22%3A%22UNKNOWN%22%2C%22params%22%3A%7B%22recordDescriptor%22%3A%22a102P00000BS6MzQAL.undefined.null.null.null.Chemical_Name__c%2CPharmaceutical__c%2CApplicants__c%2CSchedules__c%2CFunding_requested_for__c%2CTherapeutic_group__c.VIEW.true.null.null.null%22%7D%7D%2C%7B%22id%22%3A%22150%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerController%2FACTION%24getAppInfo%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_Info%22%2C%22params%22%3A%7B%22appId%22%3A%22a102P00000BS6Mz%22%7D%7D%2C%7B%22id%22%3A%22157%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.comm.runtime.components.aura.components.siteforce.qb.QuarterbackController%2FACTION%24validateRoute%22%2C%22callingDescriptor%22%3A%22UNKNOWN%22%2C%22params%22%3A%7B%22routeId%22%3A%2245790ed5-8659-49b9-9c85-1f63a167a9cb%22%2C%22viewParams%22%3A%7B%22viewid%22%3A%22443dfa1e-fd27-4627-aa7b-b7996e700b44%22%2C%22view_uddid%22%3A%220I32P0000000M8F%22%2C%22entity_name%22%3A%22Application_Public__c%22%2C%22audience_name%22%3A%22Default%22%2C%22recordId%22%3A%22a102P00000BS6Mz%22%2C%22recordName%22%3A%22p001791%22%2C%22picasso_id%22%3A%2245790ed5-8659-49b9-9c85-1f63a167a9cb%22%2C%22routeId%22%3A%2245790ed5-8659-49b9-9c85-1f63a167a9cb%22%7D%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22eUNJbjV5czdoejBvRlA5OHpDU1dPd1pMVExBQkpJSlVFU29Ba3lmcUNLWlE5LjMyMC4y%22%2C%22app%22%3A%22siteforce%3AcommunityApp%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AcommunityApp%22%3A%221184_AgcTXn_6dZSShHXZ2PZsug%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.pageURI=%2Fapptracker%2Fs%2Fapplication-public%2Fa102P00000BS6Mz%2Fp001791&aura.token=null"
).json()
by_id = {}
for a in resp["actions"]:
  by_id[a["id"]] = a
meta = by_id["150;a"]["returnValue"]
meta = pd.DataFrame(meta).head(1)
print(meta)
os.makedirs("applications", exist_ok=True)
meta.to_csv("applications/p001791_meta.csv", index=False)
df = pd.DataFrame(json.loads(by_id["108;a"]["returnValue"]))
print(df)
df.to_csv("applications/p001791.csv")
