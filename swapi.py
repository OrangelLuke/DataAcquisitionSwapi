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
    #data = DATA

    print("Generating prompts")
    prompts = generate_all_prompts(data, resources)
    print("All prompts were generated")
    print(prompts)

    """
    PROMPT:
    Please provide the residents of Star Wars planets: Yavin IV, Hoth, Dagobah, Mustafar, Polis Massa, Mygeeto, Felucia, Saleucami, Dantooine, Ord Mantell, Tholoth. Only returns a JSON document with the information. The JSON format should be like: {'Tatooine': ['Luke Skywalker', 'C-3PO', 'Darth Vader', 'Owen Lars', 'Beru Whitesun lars', 'R5-D4', 'Biggs Darklighter', 'Anakin Skywalker', 'Shmi Skywalker', 'Cliegg Lars'], 'Alderaan': ['Leia Organa', 'Bail Prestor Organa', 'Raymus Antilles'], 'Bespin': ['Lobot']}. The residents should be selected from: ['Luke Skywalker', 'C-3PO', 'R2-D2', 'Darth Vader', 'Leia Organa', 'Owen Lars', 'Beru Whitesun lars', 'R5-D4', 'Biggs Darklighter', 'Obi-Wan Kenobi', 'Anakin Skywalker', 'Wilhuff Tarkin', 'Chewbacca', 'Han Solo', 'Greedo', 'Jabba Desilijic Tiure', 'Wedge Antilles', 'Jek Tono Porkins', 'Yoda', 'Palpatine', 'Boba Fett', 'IG-88', 'Bossk', 'Lando Calrissian', 'Lobot', 'Ackbar', 'Mon Mothma', 'Arvel Crynyd', 'Wicket Systri Warrick', 'Nien Nunb', 'Qui-Gon Jinn', 'Nute Gunray', 'Finis Valorum', 'Padmé Amidala', 'Jar Jar Binks', 'Roos Tarpals', 'Rugor Nass', 'Ric Olié', 'Watto', 'Sebulba', 'Quarsh Panaka', 'Shmi Skywalker', 'Darth Maul', 'Bib Fortuna', 'Ayla Secura', 'Ratts Tyerel', 'Dud Bolt', 'Gasgano', 'Ben Quadinaros', 'Mace Windu', 'Ki-Adi-Mundi', 'Kit Fisto', 'Eeth Koth', 'Adi Gallia', 'Saesee Tiin', 'Yarael Poof', 'Plo Koon', 'Mas Amedda', 'Gregar Typho', 'Cordé', 'Cliegg Lars', 'Poggle the Lesser', 'Luminara Unduli', 'Barriss Offee', 'Dormé', 'Dooku', 'Bail Prestor Organa', 'Jango Fett', 'Zam Wesell', 'Dexter Jettster', 'Lama Su', 'Taun We', 'Jocasta Nu', 'R4-P17', 'Wat Tambor', 'San Hill', 'Shaak Ti', 'Grievous', 'Tarfful', 'Raymus Antilles', 'Sly Moore', 'Tion Medon']. If the correct value of residents is not in that list, indicate Other. If you don't know the answer, please indicate Unknown.
    """
    # ChatGPT information example
    information = {
        "Yavin IV": ["Luke Skywalker", "Leia Organa", "Wedge Antilles", "Jek Tono Porkins"],
        "Hoth": ["Leia Organa", "Han Solo"],
        "Dagobah": ["Yoda"],
        "Mustafar": ["Darth Vader", "Obi-Wan Kenobi"],
        "Polis Massa": ["Obi-Wan Kenobi"],
        "Mygeeto": ["Ki-Adi-Mundi"],
        "Felucia": ["Aayla Secura"],
        "Saleucami": ["Stass Allie"],
        "Dantooine": ["Obi-Wan Kenobi"],
        "Ord Mantell": ["Other"],
        "Tholoth": ["Unknown"]
    }
    add_chatgpt_information(data, information, "residents", "planets", resources)
    print(data["planets"])

    """
    PROMPT:
    Please provide the skin color of Star Wars people: Chewbacca. Only returns a JSON document with the information. The JSON format should be like: {'Luke Skywalker': 'fair', 'C-3PO': 'gold', 'R2-D2': 'white, blue'}. If you don't know the answer, please indicate Unknown.
    """
    information2 = {
        "Chewbacca": "brown",
        "Luke Skywalker": "fair",
        "C-3PO": "gold",
        "R2-D2": "white, blue"
    }
    add_chatgpt_information(data, information2, "skin_color", "people", resources)
    print(data["people"])

    # Export all corrected data to json
    data_to_json(data, "corrected_data")

    # Export each corrected entity to a single json
    data_to_json(data["people"], "people")
    data_to_json(data["starships"], "starships")
    data_to_json(data["films"], "films")
    data_to_json(data["species"], "species")
    data_to_json(data["planets"], "planets")
    data_to_json(data["vehicles"], "vehicles")