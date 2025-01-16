#!/usr/bin/env python3

import requests
import pandas as pd

URL = "https://connect.pharmac.govt.nz/apptracker/s/sfsites/aura"

resp = requests.post(
    URL,
    headers={
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    },
    data="message=%7B%22actions%22%3A%5B%7B%22id%22%3A%2299%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.communities.components.aura.components.forceCommunity.richText.RichTextController%2FACTION%24getParsedRichTextValue%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2FforceCommunity%3ArichText%22%2C%22params%22%3A%7B%22html%22%3A%22%3Ch2%3E%3Cspan%20style%3D%5C%22font-size%3A%2048px%3B%5C%22%3EPriority%20lists%20for%20funding%20applications%3C%2Fspan%3E%3C%2Fh2%3E%3Cp%3E%3Cbr%3E%3C%2Fp%3E%3Cp%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3EView%20each%20of%20our%20priority%20lists%20using%20the%20dropdown%20menu.%20These%20are%20presented%20in%20alphabetical%20order%20and%20updated%20automatically%20so%20they%20always%20show%20current%20information.%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%3Cp%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3E%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%3Cp%3E%3Ca%20href%3D%5C%22https%3A%2F%2Fpharmac.govt.nz%2Fpriority-lists%5C%22%20rel%3D%5C%22noopener%20noreferrer%5C%22%20target%3D%5C%22_blank%5C%22%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3EAbout%20the%26nbsp%3Blists%20%E2%80%93%20Pharmac%E2%80%99s%20website%3C%2Fa%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3E%26nbsp%3B%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%22%7D%2C%22version%22%3A%2262.0%22%2C%22storable%22%3Atrue%7D%2C%7B%22id%22%3A%22104%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerReportController%2FACTION%24getRankedProposalReportList%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_RankedReport%22%2C%22params%22%3A%7B%22latestRankedCategory%22%3A%22OFI%22%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22eUNJbjV5czdoejBvRlA5OHpDU1dPd1pMVExBQkpJSlVFU29Ba3lmcUNLWlE5LjMyMC4y%22%2C%22app%22%3A%22siteforce%3AcommunityApp%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AcommunityApp%22%3A%221183_iYPVTlE11xgUFVH2RcHXYA%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.pageURI=%2Fapptracker%2Fs%2Franking-lists-for-funding-applications%3FreportType%3DOFI&aura.token=null",
).json()["actions"][1]["returnValue"]

df = pd.DataFrame(resp)
df.sort_values(df.columns.tolist(), inplace=True)
print(df)
df.to_csv("OFI.csv", index=False)

resp = requests.post(
    URL,
    headers={
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    },
    data="message=%7B%22actions%22%3A%5B%7B%22id%22%3A%2299%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.communities.components.aura.components.forceCommunity.richText.RichTextController%2FACTION%24getParsedRichTextValue%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2FforceCommunity%3ArichText%22%2C%22params%22%3A%7B%22html%22%3A%22%3Ch2%3E%3Cspan%20style%3D%5C%22font-size%3A%2048px%3B%5C%22%3EPriority%20lists%20for%20funding%20applications%3C%2Fspan%3E%3C%2Fh2%3E%3Cp%3E%3Cbr%3E%3C%2Fp%3E%3Cp%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3EView%20each%20of%20our%20priority%20lists%20using%20the%20dropdown%20menu.%20These%20are%20presented%20in%20alphabetical%20order%20and%20updated%20automatically%20so%20they%20always%20show%20current%20information.%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%3Cp%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3E%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%3Cp%3E%3Ca%20href%3D%5C%22https%3A%2F%2Fpharmac.govt.nz%2Fpriority-lists%5C%22%20rel%3D%5C%22noopener%20noreferrer%5C%22%20target%3D%5C%22_blank%5C%22%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3EAbout%20the%26nbsp%3Blists%20%E2%80%93%20Pharmac%E2%80%99s%20website%3C%2Fa%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3E%26nbsp%3B%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%22%7D%2C%22version%22%3A%2262.0%22%2C%22storable%22%3Atrue%7D%2C%7B%22id%22%3A%22104%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerReportController%2FACTION%24getRankedProposalReportList%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_RankedReport%22%2C%22params%22%3A%7B%22latestRankedCategory%22%3A%22CS%2FCN%22%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22eUNJbjV5czdoejBvRlA5OHpDU1dPd1pMVExBQkpJSlVFU29Ba3lmcUNLWlE5LjMyMC4y%22%2C%22app%22%3A%22siteforce%3AcommunityApp%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AcommunityApp%22%3A%221183_iYPVTlE11xgUFVH2RcHXYA%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.pageURI=%2Fapptracker%2Fs%2Franking-lists-for-funding-applications%3FreportType%3DCS%252FCN&aura.token=null",
)
df = pd.DataFrame(resp.json()["actions"][1]["returnValue"])
df.sort_values(df.columns.tolist(), inplace=True)
print(df)
df.to_csv("CS_CN.csv", index=False)

resp = requests.post(
    URL,
    headers={
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    },
    data="message=%7B%22actions%22%3A%5B%7B%22id%22%3A%22161%3Ba%22%2C%22descriptor%22%3A%22serviceComponent%3A%2F%2Fui.communities.components.aura.components.forceCommunity.richText.RichTextController%2FACTION%24getParsedRichTextValue%22%2C%22callingDescriptor%22%3A%22UNKNOWN%22%2C%22params%22%3A%7B%22html%22%3A%22%3Ch2%3E%3Cspan%20style%3D%5C%22font-size%3A%2048px%3B%5C%22%3EPriority%20lists%20for%20funding%20applications%3C%2Fspan%3E%3C%2Fh2%3E%3Cp%3E%3Cbr%3E%3C%2Fp%3E%3Cp%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3EView%20each%20of%20our%20priority%20lists%20using%20the%20dropdown%20menu.%20These%20are%20presented%20in%20alphabetical%20order%20and%20updated%20automatically%20so%20they%20always%20show%20current%20information.%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%3Cp%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3E%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%3Cp%3E%3Ca%20href%3D%5C%22https%3A%2F%2Fpharmac.govt.nz%2Fpriority-lists%5C%22%20rel%3D%5C%22noopener%20noreferrer%5C%22%20target%3D%5C%22_blank%5C%22%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3EAbout%20the%26nbsp%3Blists%20%E2%80%93%20Pharmac%E2%80%99s%20website%3C%2Fa%3E%3Cspan%20style%3D%5C%22font-size%3A%2016px%3B%5C%22%3E%26nbsp%3B%26nbsp%3B%3C%2Fspan%3E%3C%2Fp%3E%22%7D%2C%22version%22%3A%2262.0%22%2C%22storable%22%3Atrue%7D%2C%7B%22id%22%3A%22157%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FAppTrackerReportController%2FACTION%24getRankedProposalReportList%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AAppTracker_RankedReport%22%2C%22params%22%3A%7B%22latestRankedCategory%22%3A%22DECLINE%22%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22eUNJbjV5czdoejBvRlA5OHpDU1dPd1pMVExBQkpJSlVFU29Ba3lmcUNLWlE5LjMyMC4y%22%2C%22app%22%3A%22siteforce%3AcommunityApp%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AcommunityApp%22%3A%221183_iYPVTlE11xgUFVH2RcHXYA%22%2C%22MODULE%40markup%3A%2F%2Flightning%3Af6Controller%22%3A%22299_KnLaqShH2xCBVYsJK-AI7g%22%2C%22COMPONENT%40markup%3A%2F%2Finstrumentation%3Ao11ySecondaryLoader%22%3A%22342_x7Ue1Ecg1Vom9Mcos08ZPw%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.pageURI=%2Fapptracker%2Fs%2Franking-lists-for-funding-applications%3FreportType%3DDecline&aura.token=null",
)
df = pd.DataFrame(resp.json()["actions"][1]["returnValue"])
df.sort_values(df.columns.tolist(), inplace=True)
print(df)
df.to_csv("Decline.csv", index=False)
