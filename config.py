from datetime import date, timedelta

# --- Search Matrix (shared by Alaska + AA) ---
ORIGINS = ["SEA"]
DESTINATIONS = ["NRT"]   # example: Seattle → Tokyo
DATE_RANGE_DAYS = 3           # search the next N days starting today (Alaska)

# --- Alaska Output ---
ALASKA_DB_PATH = "output/alaska_awards.db"

# --- American Airlines ---
AA_DB_PATH = "output/aa_awards.db"
# Cabin class for AA award search: "BUSINESS,FIRST" | "COACH" | "PREMIUM_ECONOMY"
AA_CABIN = "BUSINESS,FIRST"
# Number of calendar months to search ahead (1 = current month only, 2 = this + next, etc.)
AA_SEARCH_MONTHS = 2

# ── AA Session Credentials ────────────────────────────────────────────────────
# The AA booking API is protected by Akamai and requires real browser session
# cookies. Refresh these whenever you start getting HTTP 403 errors (sessions
# typically last 15–60 minutes).
#
# How to get them:
#   1. Open https://www.aa.com in Chrome and run an award search.
#   2. Open DevTools → Network → filter by "calendar".
#   3. Right-click the POST /booking/api/search/calendar request → Copy → Copy as cURL.
#   4. Paste the cURL into https://curlconverter.com (or read it manually).
#   5. Copy the full value of the -b '...' Cookie header → AA_COOKIE_STRING below.
#   6. Copy the value of the x-xsrf-token header → AA_XSRF_TOKEN below.

AA_COOKIE_STRING = """bm_ss=ab8e18ef4e; aka_state_code=WA; aka_cr_code=US-WA; AKA_A2=A; XSRF-TOKEN=a8fad1cf-cd43-4707-9e12-b32aa92050c9; UAC=01129bdf50ba479f8b7855d1dd259b7b; sessionLocale=en_US; al=0; rxVisitor=1780902161248N6BGBCHKLDK58MBI1L5R24HNECOOIH6M; at_check=true; OPTOUTMULTI=0:0%7Cc1:0%7Cc3:0; OPTOUTMULTI=0:0%7Cc1:0%7Cc3:0; AMCVS_025C69945392449B0A490D4C%40AdobeOrg=1; one_trust_id=mq4v5yio-JW1Ls41hUsQgstLplvrw6PtknZp1kf; s_ecid=MCMID%7C81330029609179156774309981170431948719; AMCV_025C69945392449B0A490D4C%40AdobeOrg=1585540135%7CMCIDTS%7C20613%7CMCMID%7C81330029609179156774309981170431948719%7CMCAAMLH-1781506961%7C9%7CMCAAMB-1781506961%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1780909362s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C4.4.0; utag_main_v_id=019ea60a72f60022ce1c50bee4e205075001e06d00942; utag_main__sn=1; utag_main_ses_id=1780902163190%3Bexp-session; utag_main_loytir=Guest%3Bexp-session; utag_main_lid=Guest%3Bexp-session; browserGpc=0; utag_main_vapi_domain=aa.com; aacsaP3P=optedIn; s_cc=true; aacsapersisted=_aec26ed5501f4890a74bcc074e378564db333bc10c1147d6abaa0a0eff5f8cca_84293776e6234317bccf21b516a3eaea_1780902163654_9007199592651359_1780902163654_1; COUNTRY_CODE=ETMsDgAAAZ6mCmjdABRBRVMvQ0JDL1BLQ1M1UGFkZGluZwCAABAAEDTtOx0KRcb%2BN4%2B2%2FD6VUmcAAAAQFssXHfcHZGlqJQ41hTUEKAAUJWBtl6onY344LhlrWC%2FMxZVKzUg%3D; homeAirport=ETMsDgAAAZ6mCmjeABRBRVMvQ0JDL1BLQ1M1UGFkZGluZwCAABAAEI6lfUvwQV%2BYJZ7bq%2FLIJnAAAAAQGuqpsVwY9dhjLSEsMhAd%2FQAUDFwRRDDJxUI%2BKh0mLLfZBcMRo94%3D; saleCity=ETMsDgAAAZ6mCmjfABRBRVMvQ0JDL1BLQ1M1UGFkZGluZwCAABAAEHMhXw%2F1KW3O6lfVHPmMY%2FwAAAAQ1UQI1JWoCJbMARsayzqgUgAUos%2F48FnMmr9muxgdbCqyUS7PcsQ%3D; _gcl_au=1.1.401675692.1780902164; cookie_banner=closed; QuantumMetricSessionID=aae56891e7cae3b6cf8098f44347bfb3; QuantumMetricUserID=5d72987e436b1333ceca3878bacc6d27; _lr_geo_location_state=WA; _lr_geo_location=US; x-aka-exp=ssr-v10; spa_session_id=924d1e5d-d891-4bdc-a4bc-d95d5bb10f87; OPT0566-Prod={"activity":"OPT0566-AB-BE-FSMW-CF-NPL-PROD","experience":"B","experienceName":"B_OPT0566_NPL_Exp","version":"3","expiration":"14","location":"OPT0566-Prod","active":true}; dtCookie=v_4_srv_1_sn_7624A83CA80C65F36998AB1E29F46E1B_perc_100000_ol_0_mul_1_app-3A8b2a7e44ceb3fcd4_1_app-3A4aaa3de5a7188090_1_rcs-3Acss_0; utag_main__ss=0%3Bexp-session; utag_main_schmet=Lowest Fare%3Bexp-session; ROUTEID=IKSE.blue; JSESSIONID=BF8CD0832A84C8B4AD5453D57E65B481; akavpau_www_aahomepage=1780905113~id=fd1cad95e544a753e291a1770a46a9f8; mboxEdgeCluster=35; dtsrVID=1780904816472; bm_sz=55B7CDAFE210A03AAF26449C2FD1BB6E~YAAQaNAuFzcoQp+eAQAAZFozpgDdVWC/9Or6SOeOLV+zod81HD1N3MEukBdRKdcFumY/O4rPGQjElv7gvtQCQzgGjQDTmdeynm9KsJhaw1dMCtz4vP/Pv3O8sJhwyb6YkS8b51tREwNLqdQbLqAI62xvsernGZJ/q6usbNdwW8LLZxPN27QPcqwqSKKiSTfJW/UycHvygiit8tz0cnXUQcepmZoDC8+EPyqIDAQDqnVMnUadJvPUPgfHGbLhQJFJjy9K5f4DFJHBE25C0oy1DkSqAyHZUUR/jLf6IXbvUe56kQOxop0Dp23CSLPWZzvVpraFpuw6e9PxaWE3OlUhuBEuXagyphSewvokeBu351s9PjQqrRWHH0E8CKI/ejNpsW5xZub3I2284uVv3N+ZzgaAdow5L51j7b/Ak/75/p4cmiHaFqae3lffbd4K/tmzMlj++rEQ0cyApuqW+4fuU86HCUZGMoMtpljwPmox8h6ONj0BkOK/ytR4U9L1wjYODQl0YMAyAbNcFZcWkri49MqsAbY=~4342837~3290690; dtSa=-; aka_lc_code=ML; bm_lso=B5E6F8912CDCC7EE3950539045CA18EC26A5EB13BF454AE6EE105947DE3B8681~YAAQaNAuFxskQp+eAQAAlkszpgddY/vc2rbN+3uJZ1iDLW5f5jwAud9/SHytOI0kwlY1f8P3lLqdCeI040dOn/mfbrDDoXMOP41GkFIL9axUCFJcR8NvndIZtwAQJp7LHutdKAMvxAR37EIWAUEIjvbRmnOHexw/137/fydR1WKzgNSZThzJjGPQ3kN0q8JQJ2bVlcb9dcW/st+sJ8DD0VZOEQ5Z8VG02Xj64Ocs6iOK7jnpdWhyLtOS4JGYmclM+82belT9rfdf0SFFi//PJvj5SVKg8GCzWyHrb6edWQQEHXtBlJ9KdpQYKdIDOJ5qirJov+xYjfxXG/gzdy2qrhBz6nvV1dE/OUDlIKAIUqdlfFgCsHgFrjsiqN9Xi4+00jrKrNTA8SWR1GI9Y1oafVOd6FQFXzLxQzeq9TdGSKC5i2fdKyPrKF/MfReSn3brsCY2z3zzafk65OE9KcQ=~1780904847393; utag_main__pn=11%3Bexp-session; utag_main__se=16%3Bexp-session; utag_main__st=1780906647960%3Bexp-session; utag_main_sr_tt=A%3Bexp-1780908448117; s_sq=%5B%5BB%5D%5D; OptanonAlertBoxClosed=2026-06-08T07:47:28.856Z; aacsasession=9007199592651359_1780904848517_1780902163654_3725_96f2a03105b84d18bbca7e8b869f9555; mbox=PC#420dae532d234387adf194a7386fa4d4.35_0#1844149650|session#aa2f2fa4d0e4442683c816cd3a808ac7#1780906710; OptanonConsent=isGpcEnabled=0&datestamp=Mon+Jun+08+2026+00%3A47%3A29+GMT-0700+(Pacific+Daylight+Time)&version=202504.1.0&browserGpcFlag=0&isIABGlobal=false&consentId=mq4v5yio-JW1Ls41hUsQgstLplvrw6PtknZp1kf&isAnonUser=0&identifierType=Cookie+Unique+Id&hosts=&interactionCount=11&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false&geolocation=US%3BWA; KROUTEID=7b9b0bd599d3735a724dea8684f54160|b1f37ed7f54333e7fed5541bf6553ced; RT="z=1&dm=www.aa.com&si=9993a549-7ad4-4a4f-a4a2-aad0edcbf091&ss=mq4v5wx7&sl=b&tt=139k&bcn=%2F%2F17de4c1a.akstat.io%2F&obo=2"; s_tp=4496; s_ppv=Choose%2520Flights%2C20%2C15%2C914; _abck=4856669952F35D9FC567285DA70FCFE6~0~YAAQaNAuF4XSQ5+eAQAAzOM5phCfvhjkAaoX7znWZci9GaECiL3QxyL4lN7Ptue2BrvoiBRCStG1wZr+GL1Sgs1Z9sX7LtiVGKE0owHwpkXEUSMisju26p2xFZVAKXcOH8MZZJoP5KgtYpzzIqP8gSGdGOM23vQp28lowReb5dRl5lGpU3R3dRGuruHcjL1q6o6/pxwHpA+hTMosSb98gElJmbJVYHqVr2VO109FLmATz1WSIcmnio/ReLtkVMBPKhpiDXqgGlnYh3QMMPq6V6r5EhXDn3PqRlwlesM3wb+5YhEcWkyS1kZPKao9wNFehpsu3Ml8uWItLCgMikKxxCpOaihX3m/IIBs0P32clz3ZG86qwRWf1dWCyQbShnHqE3IMdczK7Zr8hJJY0ANE7/5W8Q/4S+ePAoK4R3P3lD+sjo4QTSx1K9XoGqfZ1jxNu4yDpTmGj0O2rVLVf1eFJtv8LFQi7WiINStIvM1vckcs0hDdo3Q0RWR3oPs1dr3z1FZZf5FLkxCtgRoM0UMPsUOZ0n7w84V2J0pIkyZewZogUg3u/Ezv79j+JH0OD3jduQfruYq4TjOD4JkMgT2efUM8t/38oTO2YzYzBFEC6fzHIcEbxr5Crzn7t+wiU0/6KEgfP8ONQbsysK1B55o3wCTG/4YHlvdekbFqHex06V13sV5wDJLLYN9c79TGcvppeSbaRjk2EAYGkFMCm3swfXhbK/jwvSe3vng0URdyt1BZgR0eXZG1I2gekHunwGGU1kF+oeHSk0gwQ9gd+a4oQ2yX0Wwddj+ANShX1RxhrciHQyCKMI2BEJ02rFAgtaKUDR9AQDqNzio36LXsRCYWxDjGthiITBX6uaNC2n7IWJfP0YWh+AphKYbs2Xrw+sFjmFBl3TTR5OVqkN4ZjPSzmnhG64qiLpamE8tZGe2xe0yq1LUSQ0RndqWnzOHUOct/neNNSnPihUc0IiDYSGJ9jG2wU91mMY4vA8jsWox+FFhmm3aBJP67MbHKx4uWggvaigRRFDseohk=~-1~-1~1780908428~AAQAAAAF%2f%2f%2f%2f%2fwUCmc9UsnfCiBOGkRk6Iaqzpl%2fnLy0TTeTAmaG93Br1RI2Joah7BR+u3DgDl0lJjZGBtk%2fDp1oB0sHZL529DLaC2Pja38ZXWEz+pb+I5iuNuUg1fXqE4fI4cbsuUV2fYpsR8oKhdsIMOmj0AQlnALyCPly80KQltAZo7MqCzA%3d%3d~1780905692; akavpau_www_aafullsite=1780905574~id=72b8ab1bf9e64ca892ea4fd07e93a427; bm_s=YAAQaNAuF2XVQ5+eAQAAPe45pgVYy0umIsXWIHhTUr4tcbLHU0JeL2ID/Hy0BPKDCar5kMvSIUSXlGo1H/nbqbIpJOMW7LRTN+ljEPGjrWoNd/QIClULGyZQx36zKVLDJ3AX5iSrPbZBAgnLa/aBdQSgscQAHunXiFaB591lbJQ7G1r8gSK/uhTpo0c7Xyzx6DUXb80IbRb8C7h9et9QJT5HgHfPclRGef463SMrChNfbZXoLsRfdXWzXCAunXsoQlKuncP54RMgeV/T7MI7OibVvjqZe4YSrQXL4V8CLWdejZtbX0jY667Vted6QlXhwDgoJQaZ5vwO/OZ84++v6uT8uvz9c2UTwnvEoSzRHUTRf8pMvyIkKpzani12xo1joZzXa7G/kHoIkxAmjf+fBlzsaR7b3wKznjuVcel8txeL51zG615U3hdZdMTJ2IE20ojaJw6djLC6ZeuYXg/Z8Jsn1iJfaQW2BZB8j8Yjbf0AtboiUF+GMRrdtLk6ByeWhhv+qsMz03vuDSYlUBlZW6slbmhQnkCXvlwQ+tPOsXAKmNqhMG+nqjEmZjS3Nhuxt/lGei3aXj2PTPqeROLdxrIuS8YgOecLazapgiaWFf1ya2TIeqU628uKTxJgMZDhhAOsSQB/mWANBi+h9outze4UKiiNrQte7bPwYDRgcKcUzGOULxygjXg2MjGnEMmK4XpOtuOpc92vmaEy3KfwMgaqUqj/ydSXqxe+oKXBOPrtp1pSTek58YYZfaFP2cfquV/VfoUNknDwTOIKihqnWs9jZmLdpyQqzixm0msUjZz/vr33PVVvUb/paTWSJ5ZfKRfEMZu1N2QXRtnSNj5vz1fgo/1fGzh1OeooMZrvJFWQ4441mSL747xxEX/WcLXVcvi5lqYAQMPm3nj129xssv5WtPweeTyxTLMNj92tl+y7JaSkQ1Li; bm_so=10756E1DF9438779C452786D54F45B91500EDBB8CBE6E2CF69601EFA27CFBB67~YAAQaNAuF2bVQ5+eAQAAPe45pgeAZXgNNc4/0M5pDvCzx3Vqevz6x7Hmx08EqjsXiZJwanWuAbj/KmKhu8sA6ssol2hTjZsXZUEXZ2LJjOJbLELf7rLFNcLemi6ZX2JnuOij6vrCnQ5nK/V74Yu8udtRWiBUuiVnfXX/v3TDJ0Hhedek/GI8G0FMfn+ViQHg5LoQhV1S/wUeplj/0MzA2+DGsoAeOIhMzENvQr2puU1X7AH+xM0bie+iexYF8+0lmY5mpaHYPh2a5qTSdQoXpszbqLLhT1wGTe5KF18MR1KmNrq/OSK/xKezum7WnZ1u7IVgIFXyMYupMKtjfgW/+GUM/8cVTefieaqnyxpsJyvWXHp8oANwNMHIeKTVYQwwgADQo85FYOlcKe11+d0KP3lgJIjXb+gjzwupFcoAtf4zFZNdoQ/2IancUuPRxP/7MAD7kwlrn57ZMZ5Wv6s=; rxvt=1780907074977|1780902161249; dtPC=1$104843906_222h188vHRAFCKEUFSKHRDUJTFHFHWUUJSHWHMHT-0e0"""   # e.g. "XSRF-TOKEN=abc123; JSESSIONID=xyz; _abck=..."
AA_XSRF_TOKEN    = "a8fad1cf-cd43-4707-9e12-b32aa92050c9"   # e.g. "a8fad1cf-cd43-4707-9e12-b32aa92050c9"

# Delay range (seconds) between page loads to avoid bot detection
DELAY_MIN = 8
DELAY_MAX = 15


def get_date_range() -> list[str]:
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(DATE_RANGE_DAYS)]


def get_aa_month_starts() -> list[str]:
    """
    Return the first day of each calendar month to search for AA awards.
    The AA calendar API returns all available days in a month from a single call,
    so we only need one date per month (the 1st).

    Example with AA_SEARCH_MONTHS = 2 and today = 2026-06-08:
        ["2026-06-01", "2026-07-01"]
    """
    today = date.today()
    starts = []
    for i in range(AA_SEARCH_MONTHS):
        # Advance month by i — handle December → January rollover
        month = today.month + i
        year = today.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        starts.append(date(year, month, 1).isoformat())
    return starts

