import requests
import json

URL_BASE = "https://swapi.dev/api/"


def getResource(RESOURCE: str):
	r = requests.get(URL_BASE + RESOURCE + '/')
	data = []
	if r.status_code == 200:
		doc = r.json()
		total = doc["count"]
		data += doc["results"]
		while doc["next"]:
			r = requests.get(doc["next"])
			if r.status_code == 200:
				doc = r.json()
				data += doc["results"]
		for i in range(len(data)):
			data[i]["id"] = data[i]["url"]
			del (data[i]["url"])
			for k in data[i]:
				if isinstance(data[i][k], str) and data[i][k].startswith(URL_BASE):
					data[i][k] = data[i][k].replace(URL_BASE, "")
					data[i][k] = data[i][k].replace("/", "")
				elif isinstance(data[i][k], list):
					for j in range(len(data[i][k])):
						if isinstance(data[i][k][j], str) and data[i][k][j].startswith(URL_BASE):
							data[i][k][j] = data[i][k][j].replace(URL_BASE, "")
							data[i][k][j] = data[i][k][j].replace("/", "")
				else:
					try:
						data[i][k] = int(data[i][k])
					except:
						try:
							data[i][k] = float(data[i][k])
						except:
							continue

		if len(data) != total:
			print("Data is missing")
	else:
		print("API error")
	return data


def get_fields(data):
	fields = set(data[0].keys())
	for d in data[1:]:
		fields = fields.union(set(d.keys()))
	return fields


def validate_fields(data):
	fields = get_fields(vehicles)
	analysis = {}
	for d in data:
		for f in fields:
			if f not in d or (isinstance(d[f], str) and d[f] == "unknown") or (isinstance(d[f], list) and d[f] == []):
				if d["id"] not in analysis:
					analysis[d["id"]] = []
				analysis[d["id"]].append(f)
	return analysis

def data_to_json(my_dict, file_path):
	with open(file_path, 'w') as json_file:
		json.dump(my_dict, json_file)

if __name__ == "__main__":
	# Get data from all entities (and test printing last vehicle obtained)
	people = getResource("people")
	starships = getResource("starships")
	films = getResource("films")
	species = getResource("species")
	planets = getResource("planets")
	vehicles = getResource("vehicles")
	print(vehicles[-1])

	# Test analysis with vehicles
	v_analysis = validate_fields(vehicles)
	print(v_analysis)

	# Export all entities into different json files
	data_to_json(people, "people")
	data_to_json(starships, "starships")
	data_to_json(films, "films")
	data_to_json(species, "species")
	data_to_json(planets, "planets")
	data_to_json(vehicles, "vehicles")
