from pprint import pprint
import requests, json, itertools
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import time

from config import FLARESOLVERR_URL
from G import MAPPING

datadome_cookies = []


def gen_new_datadome_cookie():
    data = {
        "cmd": "request.get",
        "url": "https://www.maxjeune-tgvinoui.sncf/sncf-connect/",
        "maxTimeout": 60000,
        "returnOnlyCookies": "true",
    }
    response = requests.post(
        FLARESOLVERR_URL, headers={"Content-Type": "application/json"}, json=data
    )
    rj = response.json()

    for cookie in rj["solution"]["cookies"]:
        if cookie["name"] == "datadome":
            return cookie["value"]

    print("Error : datadome cookie couldnt be fetched.")
    pprint(response)


# Round robin sale
def get_datadome_cookie():
    # Garbage collector fait main
    for cookie in datadome_cookies.copy():
        # Si le cookie a déjà été utilisé plus de 30 fois ou qu'il est plus vieux que de 10min
        if cookie["usages"] > 30 or time.time() - cookie["tstamp"] > 600:
            print("retirement of cookie :")
            pprint(cookie)
            datadome_cookies.remove(cookie)

    # On veut toujours avoir 3 cookies pour round robin
    while len(datadome_cookies) < 3:
        print("requesting new cookie")
        cookie = {
            "value": gen_new_datadome_cookie(),
            "usages": 0,
            "tstamp": time.time(),
        }
        datadome_cookies.append(cookie)
    print("cookies list")
    pprint(datadome_cookies)

    elected_cookie_index = random.randrange(len(datadome_cookies))
    datadome_cookies[elected_cookie_index]["usages"] += 1
    return datadome_cookies[elected_cookie_index]["value"]


def lookup_one_day(orig: list, dest: list, day: str) -> pd.DataFrame:
    results = []
    for station_tuple in itertools.product(*[orig, dest]):
        datadome = get_datadome_cookie()
        r = requests.post(
            "https://www.maxjeune-tgvinoui.sncf/api/public/refdata/search-freeplaces-proposals",
            json={
                "departureDateTime": day,
                "destination": station_tuple[1],
                "origin": station_tuple[0],
            },
            headers={
                "authority": "www.maxjeune-tgvinoui.sncf",
                "accept": "application/json",
                "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                "content-type": "application/json",
                "Cookie": f"datadome={datadome};",
                "origin": "https://www.maxjeune-tgvinoui.sncf",
                "referer": "https://www.maxjeune-tgvinoui.sncf/sncf-connect/max-planner",
                "sec-ch-ua": '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                "x-client-app": "MAX_JEUNE",
                "x-client-app-version": "1.46.1",
            },
            timeout=30,
        )
        try:
            for proposal in r.json()["proposals"]:
                result = {}
                result["start_time"] = datetime.strptime(
                    proposal["departureDate"], "%Y-%m-%dT%H:%M"
                )
                result["date"] = result["start_time"].date()
                result["day"] = result["start_time"].strftime("%A")
                result["hour"] = result["start_time"].hour
                result["number"] = proposal["trainNumber"]
                result["orig"] = proposal["origin"]["label"]
                result["dest"] = proposal["destination"]["label"]
                result["end_time"] = datetime.strptime(
                    proposal["arrivalDate"], "%Y-%m-%dT%H:%M"
                )
                result["seats"] = proposal["freePlaces"]
                result["type"] = proposal["trainEquipment"]
                result["duration"] = round(
                    (result["end_time"].timestamp() - result["start_time"].timestamp())
                    / 3600,
                    2,
                )
                result["ts_start"] = result["start_time"].timestamp() * 1000
                result["ts_end"] = result["end_time"].timestamp() * 1000
                results.append(result)
        except:
            print(r)
            pass
    return pd.DataFrame.from_dict(results)


def lookup_date_range_one_way(origs, dests, start, end):
    start = datetime.strptime(start, "%Y-%m-%d").date()
    end = datetime.strptime(end, "%Y-%m-%d").date()

    results = []
    current_date = start
    while current_date <= end:
        results.append(
            lookup_one_day(origs, dests, current_date.strftime("%Y-%m-%d"))
        )
        current_date += timedelta(days=1)

    return pd.concat(results)  # .sort_values(by="start_time")


def lookup_date_range_both_ways(stationsA, stationsB, start, end):
    a_to_b = lookup_date_range_one_way(stationsA, stationsB, start, end)
    a_to_b.insert(0, "direction", "outbound")
    b_to_a = lookup_date_range_one_way(stationsB, stationsA, start, end)
    b_to_a.insert(0, "direction", "inbound")
    return pd.concat([a_to_b, b_to_a])  # .sort_values(by="start_time")


# print(lookup_date_range_both_ways(['FRDJU'], ['FRNTE'], '2023-06-04', '2023-06-04').reset_index().drop('index', axis=1).head())
