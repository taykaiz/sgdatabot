import requests, zipfile, io

DATAGOV_DIR = "."

url = "https://data.gov.sg/dataset/1a60dcc1-8c9f-450e-ab6f-6d7a03228bfa/download"
r = requests.get(url)
z = zipfile.ZipFile(io.BytesIO(r.content))
z.extractall(DATAGOV_DIR)

print ("Data Gov HDB Carpark cache updated!")
