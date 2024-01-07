# DataAcquisitionSwapi

## Authors:
- Ángel Luque Lázaro
- Gabriel Ravelomanana Nampoina

## About the code:

In order to show the process of our work, we have decided to keep intermediary code in the repository. Hence, here's a little explanation as to what each of the files contains:

- ExtractData.py: first approach to extracting data through API. Contains the data extraction, its validation/analysis (number of items, and invalid/incomplete values) and its export to json files.
- swapi.py: includes most of what the previous file had, but also adds all the process of data correction with chatGPT (as well as reading the data from its response). Only contains some examples of this process.
- correct_data.py: same as previous file, but instead of only some examples, contains all possible prompts and responses from the data correction process (entire process).
- create_intermediate_table.py: handles the many-to-many interactions using pandas library, and create intermediate tables.
- create_table.sql: sqlite queries that store all original tables and intermediate tables into a db file.

Being strict, the entire project can be followed only by the last 3 files (first 2 are intermediary code).
