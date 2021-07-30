import pymongo
import config
import pandas as pd

conn = pymongo.MongoClient(config.MONGO_ADDR)
db = conn[config.MONGO_AUTH]

def insert():
    nasa_93 = pd.read_csv("E:/KULIAH/Semester 8/Skripsi/Dokuments/NASA93.csv", sep=';', decimal=',')
    del nasa_93["id"]
    nasa_93["name"] = "nasa93"
    datasets = nasa_93.to_dict('records')

    results = db["datasets"].insert_many(datasets)
    return results.inserted_ids

def pagination(page):
    per_page = 5
    results = []
    datasets = db["datasets"].find({}).skip((page-1)*per_page).limit(per_page)

    for dataset in datasets:
        dataset["_id"] = str(dataset["_id"])
        results.append(dataset)
    
    print(results[0])

# pagination(2)
insert()