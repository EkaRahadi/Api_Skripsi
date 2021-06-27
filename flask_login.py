from flask import Flask, request, jsonify
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import re

import pymongo
from datetime import datetime, timedelta
from functools import wraps
import config

application = Flask(__name__)
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
                'exp': datetime.utcnow() + timedelta(minutes=59)
            }, config.SECRET_KEY, algorithm="HS256")
            response["message"] = "token generated"
            response["token"] = token
            response["data"] = user
            response["success"] = True
            return response, 200
        response["message"] = 'Invalid emailid or password'
        return response, 403
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
        password = data.get('password')

        if name == None or email == None or password == None:
            return response, 202
        if check_email(email) == False:
            response["message"] = "Invalid email id"
            return response, 202
        if check_password(password) == False:
            response["message"] = "Password requirement not fullfilled"
            return response, 202

        result = db['users'].update_one({'user_id': user_id}, {'$set': {'user_name': name,
                                                               'email': email, 'password': generate_password_hash(password)}})
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


if __name__ == "__main__":
    application.run(host='0.0.0.0', port=1234)
