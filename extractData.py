import requests

URL_BASE = "https://swapi.dev/api/"
r = requests.get(URL_BASE + 'people/')
if r.status_code == 200:
	doc = r.json()
	print("Number of characters:", doc["count"])
	for result in doc["results"]:
		print(result["name"])
	page = 2
	while doc["next"] is not None:
		r = requests.get(doc["next"])
		if r.status_code == 200:
			doc = r.json()
			for result in doc["results"]:
				print(result["name"])
			page = page + 1
else:
	print("API error")
