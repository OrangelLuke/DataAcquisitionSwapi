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


# get all possible fields in one entity (genericity)
def get_fields(data):
    fields = set(data[0].keys())
    for d in data[1:]:
        fields = fields.union(set(d.keys()))
    return fields


# check field doesn't exist, is unknown or is empty
def is_invalid(f, d):
    return f not in d or (isinstance(d[f], str) and d[f] == "unknown") or (isinstance(d[f], list) and d[f] == [])


# for each field, create list of ids with that field correct and list of ids with that field incorrect
def validate_fields(data):
    fields = get_fields(data)
    analysis = {}
    for f in fields:
        analysis[f] = {"correct_ids": [], "incorrect_ids": []}
    for d in data:
        for f in fields:
            if is_invalid(f, d):
                analysis[f]["incorrect_ids"].append(d["id"])
            else:
                analysis[f]["correct_ids"].append(d["id"])
    return analysis


# if value is reference to other entity, returns that entity name; otherwise returns ""
def is_reference(value, resources):
    if isinstance(value, list) and len(value) > 0:
        value = value[0]

    if not isinstance(value, str):
        return ""

    for r in resources:
        if value.startswith(r):
            return r
    return ""


def get_value(data, id, field):
    for d in data:
        if d["id"] == id:
            return d[field]
    return ""


# get name or title from id
def get_name_field(data):
    name_resource = "name"
    if name_resource not in data:
        name_resource = "title"
    return name_resource


def generate_prompt(analysis, data, field, resource, resources):
    name_resource = get_name_field(data[resource][0])
    incorrect_list = []

    for id in analysis["incorrect_ids"]:
        incorrect_list.append(get_value(data[resource], id, name_resource))

    field_name = field.replace("_", " ").strip()

    prompt = f"Please provide the {field_name} of Star Wars {resource}: {', '.join(incorrect_list)}. "
    prompt += "Only returns a JSON document with the information. The JSON format should be like: "
    ref = is_reference(get_value(data[resource], analysis["correct_ids"][0], field), resources)
    if ref:
        name_ref = get_name_field(data[ref][0])
        all_refs = []
        for r in data[ref]:
            all_refs.append(r[name_ref])
        example = {}
        for id in analysis["correct_ids"][:3]:
            data_ref = get_value(data[resource], id, field)
            if isinstance(data_ref, list):
                data_ref_list = []
                for d in data_ref:
                    data_ref_list.append(get_value(data[ref], d, name_ref))
                data_ref = data_ref_list
            else:
                data_ref = get_value(data[ref], data_ref, name_ref)
            example[get_value(data[resource], id, name_resource)] = data_ref
        prompt += f"{example}."
        prompt += f" The {field_name} should be selected from: {all_refs}. If the correct value of {field_name} is not in that list, indicate Other. "
    else:
        example = {}
        for id in analysis["correct_ids"][:3]:
            example[get_value(data[resource], id, name_resource)] = get_value(data[resource], id, field)
        prompt += str(example) + ". "
    prompt += "If you don't know the answer, please indicate Unknown."
    return prompt


# for each entity, checks all fields, and generate prompts to complete invalid fields
def generate_all_prompts(data, resources):
    prompts = []
    for r in resources:
        analysis = validate_fields(data[r])
        for f in analysis:
            print(f"\t{r} - {f} ... ", end="")
            # We only ask for information in data with some correct and incorrect information
            if analysis[f]["correct_ids"] != [] and analysis[f]["incorrect_ids"] != []:
                prompts.append(generate_prompt(analysis[f], data, f, r, resources))
            print("done")
    return prompts


def get_id(data, name, field):
    for d in data:
        if d[field] == name:
            return d["id"]
    return ""


def add_chatgpt_information(data, information, field, resource, resources):
    analysis = validate_fields(data[resource])
    name = get_name_field(data[resource][0])
    ref = is_reference(get_value(data[resource], analysis[field]["correct_ids"][0], field), resources)
    if ref:
        name_ref = get_name_field(data[ref][0])
        for d in data[resource]:
            if is_invalid(field, d) and information[d[name]]:
                if isinstance(information[d[name]], list):
                    d[field] = []
                    for i in information[d[name]]:
                        id = get_id(data[ref], i, name_ref)
                        if id and i.upper() != "UNKNOWN":
                            d[field].append(id)
                else:
                    id = get_id(data[ref], information[d[name]], name_ref)
                    if id and information[d[name]].upper() != "UNKNOWN":
                        d[field] = id
    else:
        for d in data[resource]:
            if is_invalid(field, d) and information[d[name]] and information[d[name]].upper() != "UNKNOWN":
                d[field] = information[d[name]]

def data_to_json(my_dict, file_path):
	with open(file_path, 'w') as json_file:
		json.dump(my_dict, json_file)

if __name__ == "__main__":
    resources: list = ["people", "planets", "vehicles", "species", "films", "starships"]

    print("Getting data from API ...")
    data = {}
    for r in resources:
        print(f"\t{r} ... ", end="")
        data[r] = getResource(r)
        print("done")
    print("All data was downloaded")
    print(data)

    # Export all original data to json
    data_to_json(data, "original_data")

    # We can use the data from the file to avoid downloading it again
    f = open('original_data')
    data = json.load(f)
    print("Loaded data")
    #data = DATA

    print("Generating prompts")
    prompts = generate_all_prompts(data, resources)
    print("All prompts were generated")
    print(len(prompts))

    with open('prompts.txt', 'w') as f:
        for prompt in prompts:
            f.write(prompt + '\n')

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
    Please provide the eye color of Star Wars people: Ratts Tyerel, Wat Tambor. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': 'blue', 'C-3PO': 'yellow', 'R2-D2': 'red'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
    "Ratts Tyerel": "Unknown",
    "Wat Tambor": "Unknown"
}
    add_chatgpt_information(data, information, "eye_color", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
    Please provide the birth year of Star Wars people: R5-D4, Jek Tono Porkins, Arvel Crynyd, Nien Nunb, Nute Gunray, Roos Tarpals, Rugor Nass, Ric Oli�, Watto, Sebulba, Bib Fortuna, Ratts Tyerel, Dud Bolt, Gasgano, Ben Quadinaros, Kit Fisto, Eeth Koth, Adi Gallia, Saesee Tiin, Yarael Poof, Mas Amedda, Gregar Typho, Cord�, Poggle the Lesser, Dorm�, Zam Wesell, Dexter Jettster, Lama Su, Taun We, Jocasta Nu, R4-P17, Wat Tambor, San Hill, Shaak Ti, Grievous, Tarfful, Raymus Antilles, Sly Moore, Tion Medon. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': '19BBY', 'C-3PO': '112BBY', 'R2-D2': '33BBY'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "R5-D4": "Unknown",
  "Jek Tono Porkins": "Unknown",
  "Arvel Crynyd": "Unknown",
  "Nien Nunb": "Unknown",
  "Nute Gunray": "Unknown",
  "Roos Tarpals": "Unknown",
  "Rugor Nass": "Unknown",
  "Ric Olié": "Unknown",
  "Watto": "Unknown",
  "Sebulba": "Unknown",
  "Bib Fortuna": "Unknown",
  "Ratts Tyerel": "Unknown",
  "Dud Bolt": "Unknown",
  "Gasgano": "Unknown",
  "Ben Quadinaros": "Unknown",
  "Kit Fisto": "Unknown",
  "Eeth Koth": "Unknown",
  "Adi Gallia": "Unknown",
  "Saesee Tiin": "Unknown",
  "Yarael Poof": "Unknown",
  "Mas Amedda": "Unknown",
  "Gregar Typho": "Unknown",
  "Cordé": "Unknown",
  "Poggle the Lesser": "Unknown",
  "Dormé": "Unknown",
  "Zam Wesell": "Unknown",
  "Dexter Jettster": "Unknown",
  "Lama Su": "Unknown",
  "Taun We": "Unknown",
  "Jocasta Nu": "Unknown",
  "R4-P17": "Unknown",
  "Wat Tambor": "Unknown",
  "San Hill": "Unknown",
  "Shaak Ti": "Unknown",
  "Grievous": "Unknown",
  "Tarfful": "Unknown",
  "Raymus Antilles": "Unknown",
  "Sly Moore": "Unknown",
  "Tion Medon": "Unknown"
}
    add_chatgpt_information(data, information, "birth_year", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the height of Star Wars people: Arvel Crynyd. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': 172, 'C-3PO': 167, 'R2-D2': 96}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    add_chatgpt_information(data, information, "height", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the species of Star Wars people: Luke Skywalker, Darth Vader, Leia Organa, Owen Lars, Beru Whitesun lars, Biggs Darklighter, Obi-Wan Kenobi, Anakin Skywalker, Wilhuff Tarkin, Han Solo, Wedge Antilles, Jek Tono Porkins, Palpatine, Boba Fett, Lando Calrissian, Lobot, Mon Mothma, Arvel Crynyd, Qui-Gon Jinn, Finis Valorum, Padm� Amidala, Ric Oli�, Quarsh Panaka, Shmi Skywalker, Mace Windu, Gregar Typho, Cord�, Cliegg Lars, Jango Fett, R4-P17, Raymus Antilles, Sly Moore. Only returns a JSON document with the information. The JSON format should be like: {'C-3PO': ['Droid'], 'R2-D2': ['Droid'], 'R5-D4': ['Droid']}. The species should be selected from: ['Human', 'Droid', 'Wookie', 'Rodian', 'Hutt', "Yoda's species", 'Trandoshan', 'Mon Calamari', 'Ewok', 'Sullustan', 'Neimodian', 'Gungan', 'Toydarian', 'Dug', "Twi'lek", 'Aleena', 'Vulptereen', 'Xexto', 'Toong', 'Cerean', 'Nautolan', 'Zabrak', 'Tholothian', 'Iktotchi', 'Quermian', 'Kel Dor', 'Chagrian', 'Geonosian', 'Mirialan', 'Clawdite', 'Besalisk', 'Kaminoan', 'Skakoan', 'Muun', 'Togruta', 'Kaleesh', "Pau'an"]. If the correct value of species is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Luke Skywalker": "Human",
  "Darth Vader": "Human",
  "Leia Organa": "Human",
  "Owen Lars": "Human",
  "Beru Whitesun lars": "Human",
  "Biggs Darklighter": "Human",
  "Obi-Wan Kenobi": "Human",
  "Anakin Skywalker": "Human",
  "Wilhuff Tarkin": "Human",
  "Han Solo": "Human",
  "Wedge Antilles": "Human",
  "Jek Tono Porkins": "Human",
  "Palpatine": "Human",
  "Boba Fett": "Human",
  "Lando Calrissian": "Human",
  "Lobot": "Human",
  "Mon Mothma": "Human",
  "Arvel Crynyd": "Unknown",
  "Qui-Gon Jinn": "Human",
  "Finis Valorum": "Human",
  "Padmé Amidala": "Human",
  "Ric Olié": "Human",
  "Quarsh Panaka": "Human",
  "Shmi Skywalker": "Human",
  "Mace Windu": "Human",
  "Gregar Typho": "Human",
  "Cordé": "Human",
  "Cliegg Lars": "Human",
  "Jango Fett": "Human",
  "R4-P17": "Droid",
  "Raymus Antilles": "Human",
  "Sly Moore": "Umbaran"
}

    add_chatgpt_information(data, information, "species", "people", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the starships of Star Wars people: C-3PO, R2-D2, Leia Organa, Owen Lars, Beru Whitesun lars, R5-D4, Wilhuff Tarkin, Greedo, Jabba Desilijic Tiure, Yoda, Palpatine, IG-88, Bossk, Lobot, Ackbar, Mon Mothma, Wicket Systri Warrick, Qui-Gon Jinn, Nute Gunray, Finis Valorum, Jar Jar Binks, Roos Tarpals, Rugor Nass, Watto, Sebulba, Quarsh Panaka, Shmi Skywalker, Bib Fortuna, Ayla Secura, Ratts Tyerel, Dud Bolt, Gasgano, Ben Quadinaros, Mace Windu, Ki-Adi-Mundi, Kit Fisto, Eeth Koth, Adi Gallia, Saesee Tiin, Yarael Poof, Mas Amedda, Cord�, Cliegg Lars, Poggle the Lesser, Luminara Unduli, Barriss Offee, Dorm�, Dooku, Bail Prestor Organa, Jango Fett, Zam Wesell, Dexter Jettster, Lama Su, Taun We, Jocasta Nu, R4-P17, Wat Tambor, San Hill, Shaak Ti, Tarfful, Raymus Antilles, Sly Moore, Tion Medon. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': ['X-wing', 'Imperial shuttle'], 'Darth Vader': ['TIE Advanced x1'], 'Biggs Darklighter': ['X-wing']}. The starships should be selected from: ['CR90 corvette', 'Star Destroyer', 'Sentinel-class landing craft', 'Death Star', 'Millennium Falcon', 'Y-wing', 'X-wing', 'TIE Advanced x1', 'Executor', 'Rebel transport', 'Slave 1', 'Imperial shuttle', 'EF76 Nebulon-B escort frigate', 'Calamari Cruiser', 'A-wing', 'B-wing', 'Republic Cruiser', 'Droid control ship', 'Naboo fighter', 'Naboo Royal Starship', 'Scimitar', 'J-type diplomatic barge', 'AA-9 Coruscant freighter', 'Jedi starfighter', 'H-type Nubian yacht', 'Republic Assault ship', 'Solar Sailer', 'Trade Federation cruiser', 'Theta-class T-2c shuttle', 'Republic attack cruiser', 'Naboo star skiff', 'Jedi Interceptor', 'arc-170', 'Banking clan frigte', 'Belbullab-22 starfighter', 'V-wing']. If the correct value of starships is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "C-3PO": ["Other"],
  "R2-D2": ["Other"],
  "Leia Organa": ["Tantive IV", "Millennium Falcon"],
  "Owen Lars": ["Other"],
  "Beru Whitesun lars": ["Other"],
  "R5-D4": ["Other"],
  "Wilhuff Tarkin": ["Other"],
  "Greedo": ["Other"],
  "Jabba Desilijic Tiure": ["Other"],
  "Yoda": ["Other"],
  "Palpatine": ["Executor"],
  "IG-88": ["Other"],
  "Bossk": ["Other"],
  "Lobot": ["Other"],
  "Ackbar": ["Home One"],
  "Mon Mothma": ["Home One"],
  "Wicket Systri Warrick": ["Other"],
  "Qui-Gon Jinn": ["Starfreighter"],
  "Nute Gunray": ["Other"],
  "Finis Valorum": ["Other"],
  "Jar Jar Binks": ["Other"],
  "Roos Tarpals": ["Other"],
  "Rugor Nass": ["Other"],
  "Watto": ["Other"],
  "Sebulba": ["Other"],
  "Quarsh Panaka": ["Other"],
  "Shmi Skywalker": ["Other"],
  "Bib Fortuna": ["Other"],
  "Ayla Secura": ["Jedi starfighter"],
  "Ratts Tyerel": ["Other"],
  "Dud Bolt": ["Other"],
  "Gasgano": ["Other"],
  "Ben Quadinaros": ["Other"],
  "Mace Windu": ["Jedi starfighter"],
  "Ki-Adi-Mundi": ["Jedi starfighter"],
  "Kit Fisto": ["Jedi starfighter"],
  "Eeth Koth": ["Other"],
  "Adi Gallia": ["Jedi starfighter"],
  "Saesee Tiin": ["Jedi starfighter"],
  "Yarael Poof": ["Other"],
  "Mas Amedda": ["Other"],
  "Cordé": ["Other"],
  "Cliegg Lars": ["Other"],
  "Poggle the Lesser": ["Other"],
  "Luminara Unduli": ["Other"],
  "Barriss Offee": ["Other"],
  "Dormé": ["Other"],
  "Dooku": ["Solar Sailer"],
  "Bail Prestor Organa": ["Tantive IV"],
  "Jango Fett": ["Slave 1"],
  "Zam Wesell": ["Other"],
  "Dexter Jettster": ["Other"],
  "Lama Su": ["Other"],
  "Taun We": ["Other"],
  "Jocasta Nu": ["Other"],
  "R4-P17": ["Other"],
  "Wat Tambor": ["Other"],
  "San Hill": ["Other"],
  "Shaak Ti": ["Jedi Interceptor"],
  "Tarfful": ["Other"],
  "Raymus Antilles": ["Tantive IV"],
  "Sly Moore": ["Other"],
  "Tion Medon": ["Other"]
}


    add_chatgpt_information(data, information, "starships", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the mass of Star Wars people: Wilhuff Tarkin, Mon Mothma, Arvel Crynyd, Finis Valorum, Rugor Nass, Ric Oli�, Watto, Quarsh Panaka, Shmi Skywalker, Bib Fortuna, Gasgano, Eeth Koth, Saesee Tiin, Yarael Poof, Mas Amedda, Cord�, Cliegg Lars, Dorm�, Bail Prestor Organa, Taun We, Jocasta Nu, R4-P17, San Hill. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': 77, 'C-3PO': 75, 'R2-D2': 32}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Wilhuff Tarkin": "Unknown",
  "Mon Mothma": "Unknown",
  "Arvel Crynyd": "Unknown",
  "Finis Valorum": "Unknown",
  "Rugor Nass": "Unknown",
  "Ric Olié": "Unknown",
  "Watto": "Unknown",
  "Quarsh Panaka": "Unknown",
  "Shmi Skywalker": "Unknown",
  "Bib Fortuna": "Unknown",
  "Gasgano": "Unknown",
  "Eeth Koth": "Unknown",
  "Saesee Tiin": "Unknown",
  "Yarael Poof": "Unknown",
  "Mas Amedda": "Unknown",
  "Cordé": "Unknown",
  "Cliegg Lars": "Unknown",
  "Dormé": "Unknown",
  "Bail Prestor Organa": "Unknown",
  "Taun We": "Unknown",
  "Jocasta Nu": "Unknown",
  "R4-P17": "Unknown",
  "San Hill": "Unknown"
}

    add_chatgpt_information(data, information, "mass", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the skin color of Star Wars people: Chewbacca. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': 'fair', 'C-3PO': 'gold', 'R2-D2': 'white, blue'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Chewbacca": "brown"
}

    add_chatgpt_information(data, information, "skin_color", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the vehicles of Star Wars people: C-3PO, R2-D2, Darth Vader, Owen Lars, Beru Whitesun lars, R5-D4, Biggs Darklighter, Wilhuff Tarkin, Han Solo, Greedo, Jabba Desilijic Tiure, Jek Tono Porkins, Yoda, Palpatine, Boba Fett, IG-88, Bossk, Lando Calrissian, Lobot, Ackbar, Mon Mothma, Arvel Crynyd, Wicket Systri Warrick, Nien Nunb, Nute Gunray, Finis Valorum, Padm� Amidala, Jar Jar Binks, Roos Tarpals, Rugor Nass, Ric Oli�, Watto, Sebulba, Quarsh Panaka, Shmi Skywalker, Bib Fortuna, Ayla Secura, Ratts Tyerel, Dud Bolt, Gasgano, Ben Quadinaros, Mace Windu, Ki-Adi-Mundi, Kit Fisto, Eeth Koth, Adi Gallia, Saesee Tiin, Yarael Poof, Plo Koon, Mas Amedda, Gregar Typho, Cord�, Cliegg Lars, Poggle the Lesser, Luminara Unduli, Barriss Offee, Dorm�, Bail Prestor Organa, Jango Fett, Dexter Jettster, Lama Su, Taun We, Jocasta Nu, R4-P17, Wat Tambor, San Hill, Shaak Ti, Tarfful, Raymus Antilles, Sly Moore, Tion Medon. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': ['Snowspeeder', 'Imperial Speeder Bike'], 'Leia Organa': ['Imperial Speeder Bike'], 'Obi-Wan Kenobi': ['Tribubble bongo']}. The vehicles should be selected from: ['Sand Crawler', 'T-16 skyhopper', 'X-34 landspeeder', 'TIE/LN starfighter', 'Snowspeeder', 'TIE bomber', 'AT-AT', 'AT-ST', 'Storm IV Twin-Pod cloud car', 'Sail barge', 'Bantha-II cargo skiff', 'TIE/IN interceptor', 'Imperial Speeder Bike', 'Vulture Droid', 'Multi-Troop Transport', 'Armored Assault Tank', 'Single Trooper Aerial Platform', 'C-9979 landing craft', 'Tribubble bongo', 'Sith speeder', 'Zephyr-G swoop bike', 'Koro-2 Exodrive airspeeder', 'XJ-6 airspeeder', 'LAAT/i', 'LAAT/c', 'AT-TE', 'SPHA', 'Flitknot speeder', 'Neimoidian shuttle', 'Geonosian starfighter', 'Tsmeu-6 personal wheel bike', 'Emergency Firespeeder', 'Droid tri-fighter', 'Oevvaor jet catamaran', 'Raddaugh Gnasp fluttercraft', 'Clone turbo tank', 'Corporate Alliance tank droid', 'Droid gunship', 'AT-RT']. If the correct value of vehicles is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "C-3PO": ["Other"],
  "R2-D2": ["Other"],
  "Darth Vader": ["TIE Advanced x1", "Imperial shuttle"],
  "Owen Lars": ["Other"],
  "Beru Whitesun lars": ["Other"],
  "R5-D4": ["Other"],
  "Biggs Darklighter": ["Other"],
  "Wilhuff Tarkin": ["Other"],
  "Han Solo": ["Other"],
  "Greedo": ["Other"],
  "Jabba Desilijic Tiure": ["Other"],
  "Yoda": ["Other"],
  "Palpatine": ["Other"],
  "IG-88": ["Other"],
  "Bossk": ["Other"],
  "Lobot": ["Other"],
  "Ackbar": ["Other"],
  "Mon Mothma": ["Other"],
  "Arvel Crynyd": ["Other"],
  "Wicket Systri Warrick": ["Other"],
  "Qui-Gon Jinn": ["Other"],
  "Nute Gunray": ["Other"],
  "Finis Valorum": ["Other"],
  "Jar Jar Binks": ["Other"],
  "Roos Tarpals": ["Other"],
  "Rugor Nass": ["Other"],
  "Watto": ["Other"],
  "Sebulba": ["Other"],
  "Quarsh Panaka": ["Other"],
  "Shmi Skywalker": ["Other"],
  "Bib Fortuna": ["Other"],
  "Ayla Secura": ["Other"],
  "Ratts Tyerel": ["Other"],
  "Dud Bolt": ["Other"],
  "Gasgano": ["Other"],
  "Ben Quadinaros": ["Other"],
  "Mace Windu": ["Other"],
  "Ki-Adi-Mundi": ["Other"],
  "Kit Fisto": ["Other"],
  "Eeth Koth": ["Other"],
  "Adi Gallia": ["Other"],
  "Saesee Tiin": ["Other"],
  "Yarael Poof": ["Other"],
  "Mas Amedda": ["Other"],
  "Cordé": ["Other"],
  "Cliegg Lars": ["Other"],
  "Poggle the Lesser": ["Other"],
  "Luminara Unduli": ["Other"],
  "Barriss Offee": ["Other"],
  "Dormé": ["Other"],
  "Dooku": ["Other"],
  "Bail Prestor Organa": ["Other"],
  "Jango Fett": ["Other"],
  "Zam Wesell": ["Other"],
  "Dexter Jettster": ["Other"],
  "Lama Su": ["Other"],
  "Taun We": ["Other"],
  "Jocasta Nu": ["Other"],
  "R4-P17": ["Other"],
  "Wat Tambor": ["Other"],
  "San Hill": ["Other"],
  "Shaak Ti": ["Other"],
  "Tarfful": ["Other"],
  "Raymus Antilles": ["Other"],
  "Sly Moore": ["Other"],
  "Tion Medon": ["Other"],
  "Jek Tono Porkins": ["Other"],
  "Boba Fett": ["Other"],
  "Lando Calrissian": ["Other"],
  "Nien Nunb": ["Other"],
  "Padmé Amidala": ["Other"],
  "Ric Olié": ["Other"],
  "Plo Koon": ["Other"],
  "Gregar Typho": ["Other"]
}

    add_chatgpt_information(data, information, "vehicles", "people", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the gravity of Star Wars planets: Saleucami, Bestine IV, unknown, Aleen Minor, Troiken, Tund, Iridonia, Tholoth, Quermia, Mirial, Serenno, Concord Dawn, Zolan, Ojom, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': '1 standard', 'Alderaan': '1 standard', 'Yavin IV': '1 standard'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Saleucami": "unknown",
  "Bestine IV": "unknown",
  "unknown": "unknown",
  "Aleen Minor": "unknown",
  "Troiken": "unknown",
  "Tund": "unknown",
  "Iridonia": "unknown",
  "Tholoth": "unknown",
  "Quermia": "unknown",
  "Mirial": "unknown",
  "Serenno": "unknown",
  "Concord Dawn": "unknown",
  "Zolan": "unknown",
  "Ojom": "unknown",
  "Umbara": "unknown"
}

    add_chatgpt_information(data, information, "gravity", "planets", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the surface water of Star Wars planets: Coruscant, Mygeeto, Felucia, Cato Neimoidia, Saleucami, Stewjon, Eriadu, Nal Hutta, Dantooine, unknown, Trandosha, Socorro, Toydaria, Malastare, Dathomir, Aleen Minor, Vulpter, Troiken, Tund, Haruun Kal, Iridonia, Tholoth, Iktotch, Quermia, Dorin, Champala, Mirial, Serenno, Concord Dawn, Zolan, Skako, Shili, Kalee, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 1, 'Alderaan': 40, 'Yavin IV': 8}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Coruscant": "unknown",
  "Mygeeto": "unknown",
  "Felucia": "unknown",
  "Cato Neimoidia": "unknown",
  "Saleucami": "unknown",
  "Stewjon": "unknown",
  "Eriadu": "unknown",
  "Nal Hutta": "unknown",
  "Dantooine": "unknown",
  "unknown": "unknown",
  "Trandosha": "unknown",
  "Socorro": "unknown",
  "Toydaria": "unknown",
  "Malastare": "unknown",
  "Dathomir": "unknown",
  "Aleen Minor": "unknown",
  "Vulpter": "unknown",
  "Troiken": "unknown",
  "Tund": "unknown",
  "Haruun Kal": "unknown",
  "Iridonia": "unknown",
  "Tholoth": "unknown",
  "Iktotch": "unknown",
  "Quermia": "unknown",
  "Dorin": "unknown",
  "Champala": "unknown",
  "Mirial": "unknown",
  "Serenno": "unknown",
  "Concord Dawn": "unknown",
  "Zolan": "unknown",
  "Skako": "unknown",
  "Shili": "unknown",
  "Kalee": "unknown",
  "Umbara": "unknown"
}

    add_chatgpt_information(data, information, "surface_water", "planets", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the climate of Star Wars planets: unknown, Aleen Minor, Troiken, Tund, Iridonia, Tholoth, Quermia, Mirial, Serenno, Concord Dawn, Zolan, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 'arid', 'Alderaan': 'temperate', 'Yavin IV': 'temperate, tropical'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "unknown": "unknown",
  "Aleen Minor": "unknown",
  "Troiken": "unknown",
  "Tund": "unknown",
  "Iridonia": "unknown",
  "Tholoth": "unknown",
  "Quermia": "unknown",
  "Mirial": "unknown",
  "Serenno": "unknown",
  "Concord Dawn": "unknown",
  "Zolan": "unknown",
  "Umbara": "unknown"
}

    add_chatgpt_information(data, information, "climate", "planets", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the residents of Star Wars planets: Yavin IV, Hoth, Dagobah, Mustafar, Polis Massa, Mygeeto, Felucia, Saleucami, Dantooine, Ord Mantell, Tholoth. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': ['Luke Skywalker', 'C-3PO', 'Darth Vader', 'Owen Lars', 'Beru Whitesun lars', 'R5-D4', 'Biggs Darklighter', 'Anakin Skywalker', 'Shmi Skywalker', 'Cliegg Lars'], 'Alderaan': ['Leia Organa', 'Bail Prestor Organa', 'Raymus Antilles'], 'Bespin': ['Lobot']}. The residents should be selected from: ['Luke Skywalker', 'C-3PO', 'R2-D2', 'Darth Vader', 'Leia Organa', 'Owen Lars', 'Beru Whitesun lars', 'R5-D4', 'Biggs Darklighter', 'Obi-Wan Kenobi', 'Anakin Skywalker', 'Wilhuff Tarkin', 'Chewbacca', 'Han Solo', 'Greedo', 'Jabba Desilijic Tiure', 'Wedge Antilles', 'Jek Tono Porkins', 'Yoda', 'Palpatine', 'Boba Fett', 'IG-88', 'Bossk', 'Lando Calrissian', 'Lobot', 'Ackbar', 'Mon Mothma', 'Arvel Crynyd', 'Wicket Systri Warrick', 'Nien Nunb', 'Qui-Gon Jinn', 'Nute Gunray', 'Finis Valorum', 'Padm� Amidala', 'Jar Jar Binks', 'Roos Tarpals', 'Rugor Nass', 'Ric Oli�', 'Watto', 'Sebulba', 'Quarsh Panaka', 'Shmi Skywalker', 'Darth Maul', 'Bib Fortuna', 'Ayla Secura', 'Ratts Tyerel', 'Dud Bolt', 'Gasgano', 'Ben Quadinaros', 'Mace Windu', 'Ki-Adi-Mundi', 'Kit Fisto', 'Eeth Koth', 'Adi Gallia', 'Saesee Tiin', 'Yarael Poof', 'Plo Koon', 'Mas Amedda', 'Gregar Typho', 'Cord�', 'Cliegg Lars', 'Poggle the Lesser', 'Luminara Unduli', 'Barriss Offee', 'Dorm�', 'Dooku', 'Bail Prestor Organa', 'Jango Fett', 'Zam Wesell', 'Dexter Jettster', 'Lama Su', 'Taun We', 'Jocasta Nu', 'R4-P17', 'Wat Tambor', 'San Hill', 'Shaak Ti', 'Grievous', 'Tarfful', 'Raymus Antilles', 'Sly Moore', 'Tion Medon']. If the correct value of residents is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}   
    #ChatGPT cannot answer
    #add_chatgpt_information(data, information, "residents", "planets", resources)
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """PROMPT
Please provide the orbital period of Star Wars planets: Stewjon, Aleen Minor, Troiken, Tholoth, Quermia, Mirial, Serenno, Concord Dawn, Zolan, Ojom, Shili, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 304, 'Alderaan': 364, 'Yavin IV': 4818}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}   
    #No answer
    #add_chatgpt_information(data, information, "orbital_period", "planets", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the diameter of Star Wars planets: Aleen Minor, Troiken, Cerea, Iridonia, Tholoth, Iktotch, Quermia, Champala, Mirial, Serenno, Concord Dawn, Zolan, Ojom, Skako, Shili, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 10465, 'Alderaan': 12500, 'Yavin IV': 10200}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}   
    #No answer
    #add_chatgpt_information(data, information, "diameter", "planets", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the population of Star Wars planets: Hoth, Dagobah, Stewjon, unknown, Aleen Minor, Troiken, Iridonia, Tholoth, Iktotch, Quermia, Dorin, Mirial, Serenno, Concord Dawn, Zolan, Shili, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 200000, 'Alderaan': 2000000000, 'Yavin IV': 1000}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "population", "planets", resources)
    
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the films of Star Wars planets: Stewjon, Eriadu, Corellia, Rodia, Nal Hutta, Dantooine, Bestine IV, unknown, Trandosha, Socorro, Mon Cala, Chandrila, Sullust, Toydaria, Malastare, Dathomir, Ryloth, Aleen Minor, Vulpter, Troiken, Tund, Haruun Kal, Cerea, Glee Anselm, Iridonia, Tholoth, Iktotch, Quermia, Dorin, Champala, Mirial, Serenno, Concord Dawn, Zolan, Ojom, Skako, Muunilinst, Shili, Kalee, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': ['A New Hope', 'Return of the Jedi', 'The Phantom Menace', 'Attack of the Clones', 'Revenge of the Sith'], 'Alderaan': ['A New Hope', 'Revenge of the Sith'], 'Yavin IV': ['A New Hope']}. The films should be selected from: ['A New Hope', 'The Empire Strikes Back', 'Return of the Jedi', 'The Phantom Menace', 'Attack of the Clones', 'Revenge of the Sith']. If the correct value of films is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "films", "planets", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the terrain of Star Wars planets: unknown, Aleen Minor, Tholoth, Quermia, Dorin, Zolan, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 'desert', 'Alderaan': 'grasslands, mountains', 'Yavin IV': 'jungle, rainforests'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Aleen Minor": "unknown",
  "Tholoth": "unknown",
  "Quermia": "unknown",
  "Dorin": "unknown",
  "Zolan": "unknown",
  "Umbara": "unknown",
  "unknown": "unknown"
}

    add_chatgpt_information(data, information, "terrain", "planets", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the rotation period of Star Wars planets: Stewjon, Aleen Minor, Troiken, Tholoth, Quermia, Mirial, Serenno, Concord Dawn, Zolan, Ojom, Shili, Umbara. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': 23, 'Alderaan': 24, 'Yavin IV': 24}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "rotation_period", "planets", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the manufacturer of Star Wars vehicles: Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': 'Corellia Mining Corporation', 'T-16 skyhopper': 'Incom Corporation', 'X-34 landspeeder': 'SoroSuub Corporation'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Emergency Firespeeder": "Unknown"
}

    add_chatgpt_information(data, information, "manufacturer", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the passengers of Star Wars vehicles: Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': 30, 'T-16 skyhopper': 1, 'X-34 landspeeder': 1}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Emergency Firespeeder": "Unknown"
}

    add_chatgpt_information(data, information, "passengers", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the pilots of Star Wars vehicles: Sand Crawler, T-16 skyhopper, X-34 landspeeder, TIE/LN starfighter, TIE bomber, AT-AT, Storm IV Twin-Pod cloud car, Sail barge, Bantha-II cargo skiff, TIE/IN interceptor, Vulture Droid, Multi-Troop Transport, Armored Assault Tank, Single Trooper Aerial Platform, C-9979 landing craft, LAAT/i, LAAT/c, AT-TE, SPHA, Neimoidian shuttle, Geonosian starfighter, Emergency Firespeeder, Droid tri-fighter, Oevvaor jet catamaran, Raddaugh Gnasp fluttercraft, Clone turbo tank, Corporate Alliance tank droid, Droid gunship, AT-RT. Only returns a JSON document with the information. The JSON format should be like: {'Snowspeeder': ['Luke Skywalker', 'Wedge Antilles'], 'AT-ST': ['Chewbacca'], 'Imperial Speeder Bike': ['Luke Skywalker', 'Leia Organa']}. The pilots should be selected from: ['Luke Skywalker', 'C-3PO', 'R2-D2', 'Darth Vader', 'Leia Organa', 'Owen Lars', 'Beru Whitesun lars', 'R5-D4', 'Biggs Darklighter', 'Obi-Wan Kenobi', 'Anakin Skywalker', 'Wilhuff Tarkin', 'Chewbacca', 'Han Solo', 'Greedo', 'Jabba Desilijic Tiure', 'Wedge Antilles', 'Jek Tono Porkins', 'Yoda', 'Palpatine', 'Boba Fett', 'IG-88', 'Bossk', 'Lando Calrissian', 'Lobot', 'Ackbar', 'Mon Mothma', 'Arvel Crynyd', 'Wicket Systri Warrick', 'Nien Nunb', 'Qui-Gon Jinn', 'Nute Gunray', 'Finis Valorum', 'Padm� Amidala', 'Jar Jar Binks', 'Roos Tarpals', 'Rugor Nass', 'Ric Oli�', 'Watto', 'Sebulba', 'Quarsh Panaka', 'Shmi Skywalker', 'Darth Maul', 'Bib Fortuna', 'Ayla Secura', 'Ratts Tyerel', 'Dud Bolt', 'Gasgano', 'Ben Quadinaros', 'Mace Windu', 'Ki-Adi-Mundi', 'Kit Fisto', 'Eeth Koth', 'Adi Gallia', 'Saesee Tiin', 'Yarael Poof', 'Plo Koon', 'Mas Amedda', 'Gregar Typho', 'Cord�', 'Cliegg Lars', 'Poggle the Lesser', 'Luminara Unduli', 'Barriss Offee', 'Dorm�', 'Dooku', 'Bail Prestor Organa', 'Jango Fett', 'Zam Wesell', 'Dexter Jettster', 'Lama Su', 'Taun We', 'Jocasta Nu', 'R4-P17', 'Wat Tambor', 'San Hill', 'Shaak Ti', 'Grievous', 'Tarfful', 'Raymus Antilles', 'Sly Moore', 'Tion Medon']. If the correct value of pilots is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Sand Crawler": "Unknown",
  "T-16 skyhopper": "Unknown",
  "X-34 landspeeder": "Unknown",
  "TIE/LN starfighter": "Unknown",
  "TIE bomber": "Unknown",
  "AT-AT": "Unknown",
  "Storm IV Twin-Pod cloud car": "Unknown",
  "Sail barge": "Unknown",
  "Bantha-II cargo skiff": "Unknown",
  "TIE/IN interceptor": "Unknown",
  "Vulture Droid": "Unknown",
  "Multi-Troop Transport": "Unknown",
  "Armored Assault Tank": "Unknown",
  "Single Trooper Aerial Platform": "Unknown",
  "C-9979 landing craft": "Unknown",
  "LAAT/i": "Unknown",
  "LAAT/c": "Unknown",
  "AT-TE": "Unknown",
  "SPHA": "Unknown",
  "Neimoidian shuttle": "Unknown",
  "Geonosian starfighter": "Unknown",
  "Emergency Firespeeder": "Unknown",
  "Droid tri-fighter": "Unknown",
  "Oevvaor jet catamaran": "Unknown",
  "Raddaugh Gnasp fluttercraft": "Unknown",
  "Clone turbo tank": "Unknown",
  "Corporate Alliance tank droid": "Unknown",
  "Droid gunship": "Unknown",
  "AT-RT": "Unknown"
}

    add_chatgpt_information(data, information, "pilots", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the max atmosphering speed of Star Wars vehicles: Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': 30, 'T-16 skyhopper': 1200, 'X-34 landspeeder': 250}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}   
    #No answer
    #add_chatgpt_information(data, information, "max_atmosphering_speed", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the consumables of Star Wars vehicles: X-34 landspeeder, AT-AT, Multi-Troop Transport, Armored Assault Tank, Tribubble bongo, Sith speeder, Koro-2 Exodrive airspeeder, XJ-6 airspeeder, LAAT/i, LAAT/c, Flitknot speeder, Geonosian starfighter, Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': '2 months', 'T-16 skyhopper': 0, 'TIE/LN starfighter': '2 days'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "consumables", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the cost in credits of Star Wars vehicles: TIE/LN starfighter, Snowspeeder, TIE bomber, AT-AT, AT-ST, TIE/IN interceptor, Vulture Droid, Armored Assault Tank, Tribubble bongo, Koro-2 Exodrive airspeeder, XJ-6 airspeeder, LAAT/i, LAAT/c, AT-TE, SPHA, Neimoidian shuttle, Geonosian starfighter, Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': 150000, 'T-16 skyhopper': 14500, 'X-34 landspeeder': 10550}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "cost", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the cargo capacity of Star Wars vehicles: Armored Assault Tank, XJ-6 airspeeder, Flitknot speeder, Geonosian starfighter, Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': 50000, 'T-16 skyhopper': 50, 'X-34 landspeeder': 5}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "cargo_capacity", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the length of Star Wars vehicles: Emergency Firespeeder. Only returns a JSON document with the information. The JSON format should be like: {'Sand Crawler': 36.8, 'T-16 skyhopper': 10.4, 'X-34 landspeeder': 3.4}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "length", "vehicles", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the eye colors of Star Wars species: Aleena, Skakoan. Only returns a JSON document with the information. The JSON format should be like: {'Human': 'brown, blue, green, hazel, grey, amber', 'Droid': 'n/a', 'Wookie': 'blue, green, yellow, brown, golden, red'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "eye_colors", "species", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the average lifespan of Star Wars species: Rodian, Trandoshan, Mon Calamari, Ewok, Sullustan, Neimodian, Gungan, Dug, Twi'lek, Vulptereen, Xexto, Toong, Cerean, Zabrak, Tholothian, Iktotchi, Chagrian, Geonosian, Mirialan, Skakoan. Only returns a JSON document with the information. The JSON format should be like: {'Human': 120, 'Droid': 'indefinite', 'Wookie': 400}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "average_lifespan", "species", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the classification of Star Wars species: Neimodian, Vulptereen, Xexto, Toong, Iktotchi, Kel Dor. Only returns a JSON document with the information. The JSON format should be like: {'Human': 'mammal', 'Droid': 'artificial', 'Wookie': 'mammal'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "classification", "species", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the hair colors of Star Wars species: Tholothian. Only returns a JSON document with the information. The JSON format should be like: {'Human': 'blonde, brown, black, red', 'Droid': 'n/a', 'Wookie': 'black, brown'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "hair_colors", "species", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the average height of Star Wars species: Tholothian, Skakoan. Only returns a JSON document with the information. The JSON format should be like: {'Human': 180, 'Droid': 'n/a', 'Wookie': 210}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "average_height", "species", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the language of Star Wars species: Tholothian. Only returns a JSON document with the information. The JSON format should be like: {'Human': 'Galactic Basic', 'Droid': 'n/a', 'Wookie': 'Shyriiwook'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "language", "species", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the hyperdrive rating of Star Wars starships: AA-9 Coruscant freighter. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': 2.0, 'Star Destroyer': 2.0, 'Sentinel-class landing craft': 1.0}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "hyperdirve_rating", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the passengers of Star Wars starships: Naboo Royal Starship, H-type Nubian yacht, Banking clan frigte. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': 600, 'Star Destroyer': 'n/a', 'Sentinel-class landing craft': 75}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "passengers", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the pilots of Star Wars starships: CR90 corvette, Star Destroyer, Sentinel-class landing craft, Death Star, Y-wing, Executor, Rebel transport, EF76 Nebulon-B escort frigate, Calamari Cruiser, B-wing, Republic Cruiser, Droid control ship, J-type diplomatic barge, AA-9 Coruscant freighter, Republic Assault ship, Solar Sailer, Theta-class T-2c shuttle, Republic attack cruiser, arc-170, Banking clan frigte, V-wing. Only returns a JSON document with the information. The JSON format should be like: {'Millennium Falcon': ['Chewbacca', 'Han Solo', 'Lando Calrissian', 'Nien Nunb'], 'X-wing': ['Luke Skywalker', 'Biggs Darklighter', 'Wedge Antilles', 'Jek Tono Porkins'], 'TIE Advanced x1': ['Darth Vader']}. The pilots should be selected from: ['Luke Skywalker', 'C-3PO', 'R2-D2', 'Darth Vader', 'Leia Organa', 'Owen Lars', 'Beru Whitesun lars', 'R5-D4', 'Biggs Darklighter', 'Obi-Wan Kenobi', 'Anakin Skywalker', 'Wilhuff Tarkin', 'Chewbacca', 'Han Solo', 'Greedo', 'Jabba Desilijic Tiure', 'Wedge Antilles', 'Jek Tono Porkins', 'Yoda', 'Palpatine', 'Boba Fett', 'IG-88', 'Bossk', 'Lando Calrissian', 'Lobot', 'Ackbar', 'Mon Mothma', 'Arvel Crynyd', 'Wicket Systri Warrick', 'Nien Nunb', 'Qui-Gon Jinn', 'Nute Gunray', 'Finis Valorum', 'Padm� Amidala', 'Jar Jar Binks', 'Roos Tarpals', 'Rugor Nass', 'Ric Oli�', 'Watto', 'Sebulba', 'Quarsh Panaka', 'Shmi Skywalker', 'Darth Maul', 'Bib Fortuna', 'Ayla Secura', 'Ratts Tyerel', 'Dud Bolt', 'Gasgano', 'Ben Quadinaros', 'Mace Windu', 'Ki-Adi-Mundi', 'Kit Fisto', 'Eeth Koth', 'Adi Gallia', 'Saesee Tiin', 'Yarael Poof', 'Plo Koon', 'Mas Amedda', 'Gregar Typho', 'Cord�', 'Cliegg Lars', 'Poggle the Lesser', 'Luminara Unduli', 'Barriss Offee', 'Dorm�', 'Dooku', 'Bail Prestor Organa', 'Jango Fett', 'Zam Wesell', 'Dexter Jettster', 'Lama Su', 'Taun We', 'Jocasta Nu', 'R4-P17', 'Wat Tambor', 'San Hill', 'Shaak Ti', 'Grievous', 'Tarfful', 'Raymus Antilles', 'Sly Moore', 'Tion Medon']. If the correct value of pilots is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "pilots", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the crew of Star Wars starships: AA-9 Coruscant freighter. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': '30-165', 'Star Destroyer': '47,060', 'Sentinel-class landing craft': 5}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "crew", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the max atmosphering speed of Star Wars starships: AA-9 Coruscant freighter, Republic Assault ship, Banking clan frigte. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': 950, 'Star Destroyer': 975, 'Sentinel-class landing craft': 1000}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "max_atmosphering_speed", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the MGLT of Star Wars starships: Republic Cruiser, Droid control ship, Naboo fighter, Naboo Royal Starship, Scimitar, J-type diplomatic barge, AA-9 Coruscant freighter, Jedi starfighter, H-type Nubian yacht, Republic Assault ship, Solar Sailer, Trade Federation cruiser, Theta-class T-2c shuttle, Republic attack cruiser, Naboo star skiff, Jedi Interceptor, Banking clan frigte, Belbullab-22 starfighter, V-wing. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': 60, 'Star Destroyer': 60, 'Sentinel-class landing craft': 70}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "MGLT", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the consumables of Star Wars starships: Republic Cruiser, Naboo Royal Starship, AA-9 Coruscant freighter, H-type Nubian yacht, Naboo star skiff. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': '1 year', 'Star Destroyer': '2 years', 'Sentinel-class landing craft': '1 month'}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "consumables", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the cost in credits of Star Wars starships: TIE Advanced x1, Rebel transport, Slave 1, Republic Cruiser, Droid control ship, Naboo Royal Starship, AA-9 Coruscant freighter, H-type Nubian yacht, Republic Assault ship, Naboo star skiff. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': 3500000, 'Star Destroyer': 150000000, 'Sentinel-class landing craft': 240000}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "cost", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """PROMPT
Please provide the cargo capacity of Star Wars starships: Calamari Cruiser, Republic Cruiser, Naboo Royal Starship, J-type diplomatic barge, AA-9 Coruscant freighter, H-type Nubian yacht, Naboo star skiff. Only returns a JSON document with the information. The JSON format should be like: {'CR90 corvette': 3000000, 'Star Destroyer': 36000000, 'Sentinel-class landing craft': 180000}. If you don't know the answer, please indicate Unknown.
    """
    information = {
  "Arvel Crynyd": "Unknown"
}
    #No answer
    #add_chatgpt_information(data, information, "cargo_capacity", "starships", resources)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    # Export all corrected data to json
    data_to_json(data, "corrected_data")

    # Export each corrected entity to a single json
    data_to_json(data["people"], "people")
    data_to_json(data["starships"], "starships")
    data_to_json(data["films"], "films")
    data_to_json(data["species"], "species")
    data_to_json(data["planets"], "planets")
    data_to_json(data["vehicles"], "vehicles")