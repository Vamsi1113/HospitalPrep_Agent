import requests

url = "https://api.geoapify.com/v2/places"
params = {
    "categories": "healthcare.hospital,healthcare.clinic_or_praxis",
    "filter": "circle:73.883,18.5344,10000",
    "bias": "proximity:73.883,18.5344",
    "limit": 20,
    "apiKey": "d866449d920e404fb4895f53d8f30a1f"
}

response = requests.get(url, params=params)
print("Status:", response.status_code)
try:
    print(response.json())
except:
    print(response.text)
