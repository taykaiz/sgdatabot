import requests
import json
import time

DATAMALL_TOKEN = "YOUR_DATAMALL_TOKEN"
headers = {
    'AccountKey': DATAMALL_TOKEN,
    'accept': 'application/json'
}
uri = 'http://datamall2.mytransport.sg/ltaodataservice/'  # Resource URL


def fetch_all(url):
    results = []
    while True:
        new_results = requests.get(
            url,
            headers=headers,
            params={'$skip': len(results)}
        ).json()['value']
        if not new_results:
            break
        else:
            results += new_results
        time.sleep(1)
    return results


# function to cache data mall responses
def update_data_cache_all():
    # bus stops
    url = uri + "BusStops"
    stops = fetch_all(url)
    file = "stops.json"
    with open(file, "w") as f:
        f.write(json.dumps(stops))

    # bus services
    url = uri + "BusServices"
    services = fetch_all(url)
    file = "services.json"
    with open(file, "w") as f:
        f.write(json.dumps(services))

    # bus routes
    url = uri + "BusRoutes"
    routes = fetch_all(url)
    file = "routes.json"
    with open(file, "w") as f:
        f.write(json.dumps(routes))

    print("LTA Data Mall cache updated!")


update_data_cache_all()
