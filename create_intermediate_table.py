import pandas as pd

resources: list = ["people", "planets", "vehicles", "species", "films", "starships"]

intermediate_table_names = []
list_intermediate_tables = []
for resource in resources:
    df = pd.read_json(resource)
    
    #column "residents" in planets database refers to table people, so let's rename it
    if resource == "planets":
        df = df.rename({"residents" : "people"}, axis = 1)
    #column "pilots" in vehicles and starships database refers to table people, so let's rename it
    elif resource == "vehicles" or resource == "starships":
        df = df.rename({"pilots" : "people"}, axis = 1)
    #column "homeworld" in people and species database refers to table planets, so let's rename it
    elif resource == "people" or resource == "species":
        df = df.rename({"homeworld" : "planets"}, axis = 1)
    #column "characters" in films database refers to table people, so let's rename it
    elif resource == "films":
        df = df.rename({"characters" : "people"}, axis = 1)


    #Check if there is a column named after a ressource in this resource
    for column in df.columns.tolist():
        if column in resources: #Then create intermediate table to handle interaction between these two resources
            name = resource + "_" + column + "_interaction"
            inverse_name = column + "_" + resource + "_interaction"
            if inverse_name in intermediate_table_names: #if intermediate table representing the inverse interaction already exists
                index = intermediate_table_names.index(inverse_name)
                intermediate_df = list_intermediate_tables[index]  #We're going to add these new entries to this table
                new_df = df.loc[:,[column, "id"]].explode(column)
                new_df = new_df.rename({"id" : resource}, axis = 1)

                output = pd.concat([intermediate_df, new_df]).drop_duplicates().dropna()
                list_intermediate_tables[index] = output
            else:
                intermediate_df = df.loc[:,["id", column]]
                intermediate_df = intermediate_df.explode(column)
                intermediate_df = intermediate_df.rename({"id" : resource}, axis = 1).dropna()
                intermediate_table_names.append(name)
                list_intermediate_tables.append(intermediate_df)
            
            #Drop column in the original dataframe, as the interaction is already handled by intermediate table
            df = df.drop(column, axis = 1)

    df.to_csv(resource + ".csv", index=False, header=False)

print(intermediate_table_names, len(intermediate_table_names), len(list_intermediate_tables))
for i in range(len(intermediate_table_names)):
    list_intermediate_tables[i].to_csv(intermediate_table_names[i] + ".csv", index = False, header = False)