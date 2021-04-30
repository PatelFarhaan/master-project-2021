import pymongo
import pandas as pd
from pyBKT.models import Model
from bson.objectid import ObjectId
from flask import Flask, request, jsonify


app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'


def prediction_code():
    data = pd.read_csv('updated_data.csv')
    model = Model(seed=42, num_fits=6)
    data['skill_name'] = data['subCategory']
    model.fit(data=data)
    return model


@app.route("/analytics", methods=["POST"])
def skill_level_prediction():
    input_data = request.get_json()
    test_id = input_data.get("test_id")
    if not test_id:
        return jsonify({
            "result": False,
            "message": "malformed input"
        }), 400

    test_collection = mydb["test"]
    myquery = {"_id": ObjectId(test_id)}
    mydoc = list(test_collection.find(myquery))

    if mydoc:
        data = mydoc[0]
        user_id = str(data.get("userId"))
        interactions = data.get("interactions", [])
        executedDateTime = data.get("executedDateTime")

        if interactions:
            sub_cat = interactions[0].get("categories", {}).get("subCategory")
            user_obj = list(test_collection.find({
                "userId": str(user_id),
                "interactions": {
                    "$elemMatch": {
                        "categories.subCategory": sub_cat
                    }
                }
            }))
            mean_value = helper_function(user_obj, test_id)
            update_skills_db(user_id, test_id, executedDateTime, sub_cat, mean_value)
        return jsonify({
            "result": True
        }), 201
    else:
        return jsonify({
            "result": False,
            "message": "no data found"
        }), 400


@app.route("/skill-level", methods=["POST"])
def get_skill_level():
    input_data = request.get_json()
    user_id = input_data["user_id"]
    skills_collection = mydb["skills"]
    myquery = {"user_id": str(user_id)}
    skills_obj = list(skills_collection.find(myquery))
    if skills_obj:
        skills_obj = skills_obj[0]
        skills = skills_obj.get("skills")

        for k, v in skills.items():
            sorted_value = sorted(v, key=lambda x: [x.get("executed_timestamp")])
            skills[k] = sorted_value
        return jsonify({
            "result": True,
            "data": skills
        })
    else:
        return jsonify({
            "result": False,
            "data": None
        })


def update_skills_db(user_id, test_id, executed_timestamp, topic, mean_value):
    skills_collection = mydb["skills"]
    myquery = {"user_id": str(user_id)}
    skills_obj = list(skills_collection.find(myquery))

    if skills_obj:
        skills_obj = skills_obj[0]
        skills = skills_obj.get("skills")
        if topic in skills:
            _temp = {
                "test_id": test_id,
                "skill_level": str(mean_value),
                "executed_timestamp": str(executed_timestamp)
            }
            skills[topic].append(_temp)
            newvalues = {
                "$set": {
                    "skills": skills
                }
            }
            skills_collection.update_one(myquery, newvalues)
        else:
            skills[topic] = {
                "test_id": test_id,
                "skill_level": mean_value,
                "executed_timestamp": executed_timestamp
            }
            newvalues = {
                "$set": {
                    "skills": skills
                }
            }
            skills_collection.update_one(myquery, newvalues)
    else:
        skills_obj = {
            "user_id": str(user_id),
            "skills": {
                topic: [
                    {
                        "test_id": test_id,
                        "skill_level": mean_value,
                        "executed_timestamp": executed_timestamp
                    }
                ]
            }
        }
        skills_collection.insert_one(skills_obj)


def helper_function(user_obj, test_id):
    res = []
    headers = ["user_id", "test_id", "executed_timestamp", "skill_name", "correct", "categories"]

    for user in user_obj:
        hm = {}
        test_id = str(user.get("_id"))
        executedDateTime = user.get("executedDateTime")
        user_id = str(user.get("userId"))
        interactions = user.get("interactions")

        for test in interactions:
            hm["user_id"] = user_id
            hm["test_id"] = test_id
            hm["executed_timestamp"] = executedDateTime
            hm["skill_name"] = test.get("categories", {}).get("subCategory")
            hm["correct"] = 1 if test.get("correct", {}) else 0
            hm["categories"] = test.get("categories", {}).get("category")
            res.append(hm)

    df_format = [[v for k, v in i.items()] for i in res ]
    df = pd.DataFrame(df_format, columns=headers)
    pred = model.predict(data=df)
    return pred[pred["test_id"] == test_id]["correct_predictions"].mean()


if __name__ == '__main__':
    model = prediction_code()
    database_string = "mongodb+srv://admin:admin@cluster0.e2gpa.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
    myclient = pymongo.MongoClient(database_string)
    mydb = myclient["project"]
    app.run(debug=True, host="0.0.0.0", port=5000)
