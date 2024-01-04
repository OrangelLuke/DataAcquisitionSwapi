import requests

URL_BASE = "https://swapi.co/api/"
r = requests.get(URL_BASE + 'people/')
if r.status_code == 200:
	doc = r.text
	print(doc)
	print("Número de personajes:", doc["count"])
	for resultado in doc["results"]:
		print(resultado["name"])
		pagina = 2
		tecla = input("Pulsa espacio para continuar o otra tecla para salir...")
		while doc["next"] is not None and tecla == " ":
			payload = {"page": pagina}
			r = requests.get(URL_BASE + 'people/', params=payload)
			if r.status_code == 200:
				doc = r.json()
				for resultado in doc["results"]:
					print(resultado["name"])
					pagina = pagina + 1
					tecla = input("Pulsa espacio para continuar o otra tecla para salir...")
else:
	print("Error en la API")
