from flask import Flask, request, jsonify
import json
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import re
from flask_cors import CORS
import pymongo
from datetime import datetime, timedelta
from functools import wraps
import config
from bson.objectid import ObjectId
from pymongo import ReturnDocument
import numpy as np
from algorithm import algoKelelawar, fpaAlgorithm, baFpa

application = Flask(__name__)
CORS(application)

conn = pymongo.MongoClient(config.MONGO_ADDR)
db = conn[config.MONGO_AUTH]


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return 'Unauthorized Access!', 401

        try:
            data = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
            current_user = db['users'].find_one({'user_id': data['user_id']})
            if not current_user:
                return 'Unauthorized Access!', 401
        except Exception as e:
            print(e)
            return 'Unauthorized Access!', 401
        return f(current_user, *args, **kwargs)

    return decorated


@application.route('/test', methods=['GET'])
@token_required
def test(current_user):
    return "Authorized"


@application.route('/login', methods=['POST'])
def login():
    response = {
        "success": False,
        "message": "Invalid parameters",
        "token": ""
    }
    try:
        auth = request.form

        if not auth or not auth.get('email') or not auth.get('password'):
            response["message"] = 'Invalid data'
            return response, 422

        user = db['users'].find_one({'email': auth['email']})

        if not user:
            response["message"] = "Unauthorized Access!"
            return response, 401

        user['_id'] = str(user['_id'])

        if check_password_hash(user['password'], auth['password']):
            token = jwt.encode({
                'user_id': user['user_id'],
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, config.SECRET_KEY, algorithm="HS256")
            refreshToken = jwt.encode({
                'user_id': user['user_id'],
                'exp': datetime.utcnow() + timedelta(hours=23)
            }, config.SECRET_KEY, algorithm="HS256")

            response["message"] = "token generated"
            response["token"] = token
            response["refreshToken"] = refreshToken
            response["data"] = user
            response["success"] = True
            return response, 200
        response["message"] = 'Invalid emailid or password'
        return response, 403
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/refreshToken', methods=['POST'])
@token_required
def refreshToken(current_user):
    response = {
        "success": False,
        "message": "Invalid parameters",
        "token": ""
    }

    try:
        token = jwt.encode({'user_id': current_user['user_id'],
                            'exp': datetime.utcnow() + timedelta(minutes=1)
                            }, config.SECRET_KEY, algorithm="HS256")

        response["message"] = "token generated"
        response["token"] = token
        response["success"] = True

        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/signup', methods=['POST'])
def signup():
    auth = request.authorization

    response = {
        "success": False,
        "message": "Invalid parameters"
    }

    if not auth or not auth.username or not auth.password:
        response["message"] = 'No Basic Authentication Username or Password'
        return response, 401

    if auth.username != config.USERNAME_BASIC or auth.password != config.PASSWORD_BASIC:
        response["message"] = 'Wrong Basic Authentication Username or Password'
        return response, 401

    try:
        data = request.form
        name, email = data.get('name'), data.get('email')
        password = data.get('password')
        if name == None or email == None or password == None:
            return response, 202
        if check_email(email) == False:
            response["message"] = "Invalid email id"
            return response, 202
        if check_password(password) == False:
            response["message"] = "Password requirement not fullfilled"
            return response, 202
        user = db['users'].find_one({'email': email})
        if not user:
            db['users'].insert_one({'user_id': str(uuid.uuid4()), 'user_name': name,
                                    'email': email, 'password': generate_password_hash(password), 'admin': True})
            response["success"] = True
            response["message"] = 'Successfully registered'
            return response, 200
        else:
            response["message"] = 'User already exists. Please Log in'
            return response, 202
    except Exception as ex:
        print(str(ex))
        return response, 422

# ============================================USER API=======================================
@application.route('/users', methods=['POST'])
@token_required
def create_user(current_user):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to create!'
        return response, 403

    try:
        data = request.form
        name, email = data.get('name'), data.get('email')
        password = data.get('password')
        if name == None or email == None or password == None:
            return response, 202
        if check_email(email) == False:
            response["message"] = "Invalid email id"
            return response, 202
        if check_password(password) == False:
            response["message"] = "Password requirement not fullfilled"
            return response, 202
        user = db['users'].find_one({'email': email})
        if not user:
            db['users'].insert_one({'user_id': str(uuid.uuid4()), 'user_name': name,
                                    'email': email, 'password': generate_password_hash(password), 'admin': False})
            response["success"] = True
            response["message"] = 'New user created!'
            return response, 200
        else:
            response["message"] = 'User already exists. Please Log in'
            return response, 202
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/users/<user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to update!'
        return response, 403

    try:
        data = request.form
        name, email = data.get('name'), data.get('email')

        if name == None or email == None:
            return response, 202

        payload = {
            'user_name': name,
            'email': email,
        }

        password = data.get('password')
        if password != None:
            payload['password'] = generate_password_hash(password)
            if check_password(password) == False:
                response["message"] = "Password requirement not fullfilled"
                return response, 202

        if check_email(email) == False:
            response["message"] = "Invalid email id"
            return response, 202

        result = db['users'].update_one(
            {'user_id': user_id}, {'$set': payload})
        if result.modified_count > 0:
            response["success"] = True
            response["message"] = 'User Updated !'
            return response, 200
        else:
            response["success"] = False
            response["message"] = 'User Failed Updated !'
            return response, 500
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/users/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to delete!'
        return response, 403

    try:
        result = db['users'].delete_one({'user_id': user_id})
        if result.deleted_count > 0:
            response["success"] = True
            response["message"] = 'User Deleted !'
            return response, 200
        else:
            response["success"] = False
            response["message"] = 'User Failed Deleted !'
            return response, 500
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/users', methods=['GET'])
@token_required
def get_all_user(current_user):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to Get All User!'
        return response, 403

    try:
        results = []
        users = db['users'].find({})

        for user in users:
            user['_id'] = str(user['_id'])
            results.append(user)

        response["success"] = True
        response["message"] = 'Get All Users'
        response["data"] = results
        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 500


@application.route('/users/<user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to Get User!'
        return response, 403

    try:
        results = []
        users = db['users'].find({'user_id': user_id})

        for user in users:
            user['_id'] = str(user['_id'])
            results.append(user)

        response["success"] = True
        response["message"] = 'Get Users'
        response["data"] = results
        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 500
# ============================================END USER API===================================
# ============================================START PARAMETER AP==============================
@application.route('/parameters', methods=['POST'])
@token_required
def insert_param(current_user):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to insert !'
        return response, 403

    try:
        data = request.form
        param_a, param_b, param_c, param_d= data.get('param_a'), data.get('param_b'), data.get('param_c'), data.get('param_d')

        if param_a == None or param_b == None or param_c == None or param_d == None:
            return response, 400

        param = db['cocomo_param'].find_one({'param_a': float(param_a), 'param_b': float(param_b), 'param_c': float(param_c), 'param_d': float(param_d)})
        if not param:
            db['cocomo_param'].insert_one({'param_a': float(param_a), 'param_b': float(param_b), 'param_c': float(param_c), 'param_d': float(param_d), 'default': False})
            response["success"] = True
            response["message"] = 'New parameter inserted !'
            return response, 200
        else:
            response["message"] = 'Parameter already exists.'
            return response, 202
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/parameters/<parameter_id>', methods=['PUT'])
@token_required
def update_parameter(current_user, parameter_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }

    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to update!'
        return response, 403

    try:
        data = request.form
        param_a, param_b, param_c, param_d= data.get('param_a'), data.get('param_b'), data.get('param_c'), data.get('param_d')
        default = data.get('default')

        if param_a == None or param_b == None or param_c == None or param_d == None or default == None:
            return response, 202

        payload = {
            'param_a': float(param_a),
            'param_b': float(param_b),
            'param_c': float(param_c),
            'param_d': float(param_d),
            'default': bool(default)
        }


        result = db['cocomo_param'].update_one(
            {'_id': ObjectId(parameter_id)}, {'$set': payload})
        if result.modified_count > 0:
            response["success"] = True
            response["message"] = 'Parameter Updated !'
            return response, 200
        else:
            response["success"] = False
            response["message"] = 'Parameter Failed Updated !'
            return response, 500
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/parameters/<parameter_id>', methods=['DELETE'])
@token_required
def delete_parameter(current_user, parameter_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to delete!'
        return response, 403

    try:
        result = db['cocomo_param'].delete_one({'_id': ObjectId(parameter_id)})
        if result.deleted_count > 0:
            response["success"] = True
            response["message"] = 'Parameter Deleted !'
            return response, 200
        else:
            response["success"] = False
            response["message"] = 'Parameter Failed Deleted !'
            return response, 500
    except Exception as ex:
        print(str(ex))
        return response, 422


@application.route('/parameters', methods=['GET'])
@token_required
def get_all_parameter(current_user):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to Get All User!'
        return response, 403

    try:
        results = []
        parameters = db['cocomo_param'].find({})

        for param in parameters:
            param['_id'] = str(param['_id'])
            results.append(param)

        response["success"] = True
        response["message"] = 'Get All Parameter'
        response["data"] = results
        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 500


@application.route('/parameters/<parameter_id>', methods=['GET'])
@token_required
def get_parameter(current_user, parameter_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to Get Parameter!'
        return response, 403

    try:
        results = []
        parameters = db['cocomo_param'].find({'_id': ObjectId(parameter_id)})

        for param in parameters:
            param['_id'] = str(param['_id'])
            results.append(param)

        response["success"] = True
        response["message"] = 'Get Parameter'
        response["data"] = results
        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 500

@application.route('/parameters/default/<parameter_id>', methods=['PUT'])
@token_required
def set_default(current_user, parameter_id):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to Set Default!'
        return response, 403

    try:
        results = []
        currentParam = db['cocomo_param'].find_one_and_update({'default': True }, {'$set': {'default': False}})
        parameters = db['cocomo_param'].find_one_and_update({'_id': ObjectId(parameter_id)}, {'$set': { 'default' : True}}, return_document=ReturnDocument.AFTER)

        parameters['_id'] = str(parameters['_id'])

        response["success"] = True
        response["message"] = 'Set Default Parameter'
        response["data"] = parameters
        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 500

# ============================================END PARAMETER AP==============================
# ============================================ DATASETS =====================================
@application.route('/datasets/<page>', methods=['GET'])
@token_required
def get_all_dataset(current_user, page):
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    if not current_user['admin']:
        response["success"] = False
        response["message"] = 'You are not allowed to Get All Datasets!'
        return response, 403
    

    try:
        per_page = 5
        results = []
        datasets = db["datasets"].find({'name': 'nasa93'}).skip((int(page)-1)*per_page).limit(per_page)
        datasetsCount = db["datasets"].count_documents({'name': 'nasa93'})

        for dataset in datasets:
            dataset["_id"] = str(dataset["_id"])
            results.append(dataset)
        
        response["success"] = True
        response["message"] = 'Get All Datasets'
        response["data"] = results
        response["max_page"] = int(np.ceil(datasetsCount / per_page))
        return response, 200
    except Exception as ex:
        print(str(ex))
        return response, 500
# ============================================ END DATASETS API =============================
@application.route('/estimation', methods=['POST'])
def estimation():
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    data = request.form
    loc, em, umr = data.get('loc'), data.get('em'), data.get('umr')

    if loc == None or em == None or umr == None:
        return response, 400
    
    const = db['cocomo_param'].find_one({'default': True})
    if not const:
        response["message"] = "Error no parameter cocomo found !"  
        return response, 500
    constant = [const["param_a"], const["param_b"], const["param_c"], const["param_d"]]

    monthly_cost, total_cost, Tdev, num_of_staff = hitungBiaya(constant, float(loc), float(em), int(umr))

    result = {
        "monthly_cost": monthly_cost,
        "total_cost": total_cost,
        "TDEV": Tdev,
        "num_of_staff": num_of_staff,
    }
    response["success"] = True
    response["message"] = 'Estimation Success'
    response["data"] = result
    return response, 200

# ====================================================Estimation Parameter Success======================
@application.route('/estimation-parameter', methods=['POST'])
def estimation_parameter():
    response = {
        "success": False,
        "message": "Invalid parameters"
    }
    data = request.form
    n_population, max_iteration, algorithm = int(data.get('n_population')), int(data.get('max_iteration')), data.get('algorithm')

    if n_population == None or max_iteration == None or algorithm == None:
        return response, 400

    if algorithm == "bat":
        param, mmre = algoKelelawar(n_population, 4, max_iteration)
    if algorithm == "fpa":
        param, mmre= fpaAlgorithm(n_population, 4, max_iteration)
    if algorithm == "hybrid":
        param, mmre= baFpa(n_population, 4, max_iteration)

    mmre_tdev = mmre[0]
    mmre_effort = mmre[1]

    result = {
        "parameter": param.tolist(),
        "mmre_tdev": mmre_tdev,
        "mmre_effort": mmre_effort,
    }
    response["success"] = True
    response["message"] = 'Estimation Parameter Success'
    response["data"] = result
    return response, 200

# Utils


def check_email(email):
    if(re.search(config.EMAIL_REGEX, email)):
        return True
    else:
        return False


def check_password(password):
    if len(password) >= 6 and len(password) <= 20 and any(char.isdigit() for char in password) \
            and any(char.isupper() for char in password) and any(char.islower() for char in password):
        return True
    else:
        return False

def hitungBiaya(constant, LOC, EM, UMR):
    a = constant[0]
    b = constant[1]
    c = constant[2]
    d = constant[3]
    
    PM = a * (LOC**b) * EM
    TDEV = round(c * (PM**d))
    num_of_staff = round((PM / TDEV))
    monthly_cost = num_of_staff * UMR
    total_cost = monthly_cost * TDEV
    
    return monthly_cost, total_cost, TDEV, num_of_staff


if __name__ == "__main__":
    application.run(host='0.0.0.0', port=1234)
