import pymongo  # Ensure pymongo is imported at the top of your file
from pymongo import MongoClient
from dotenv import load_dotenv
from pymongo.server_api import ServerApi
import os
from bson.objectid import ObjectId
import math

load_dotenv()


def connect_to_db():
    # return client if successful.
    # if failed, return None

    client = None  # Initialize client to None

    try:
        uri = os.getenv("MONGO_URL")
        # print("Connecting to MongoDB at:", uri)  # Debugging line
        client = MongoClient(uri, server_api=ServerApi(
            version="1", strict=True, deprecation_errors=True), serverSelectionTimeoutMS=5000)

        # print("Testing connection...")
        client.admin.command("ping")
        # print("Connected successfully")

    except Exception as e:
        print("The following error occurred:", e)

    return client


def close_client(client):
    if client:
        client.close()


def create_user(username, password):
    # create user with curr_talk_id = None
    # return user_id
    user = {
        "username": username,
        "password": password,
        "curr_talk_id": None,
        "loc": [None, None]
    }

    client = connect_to_db()
    users = client["QuikTokDB"]["users"]

    # Attempt to insert the document
    result = users.insert_one(user)
    inserted_id = result.inserted_id

    # Return the user's unique ID on success
    close_client(client)
    return inserted_id


def find_user_id_by_name(username):
    # return user_id if user exists, otherwise return None
    # Search for the user by username
    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    user = users.find_one({"username": username})

    # Check if user was found and return the user ID
    if user:
        result = str(user["_id"])
    else:
        print("User not found.")
        result = None
    close_client(client)
    return result


def find_user_name_by_id(user_id):
    # receives an object id
    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    user = users.find_one({"_id": ObjectId(user_id)})

    # Check if user was found and return the user ID
    if user:
        result = user["username"]
    else:
        print("User not found.")
        result = None
    close_client(client)
    return result


def check_password(user_id, password):
    # return True if and only if the user_id matches the password

    client = connect_to_db()
    users = client["QuikTokDB"]["users"]

    query = {
        '_id': ObjectId(user_id),
        'password': password
    }

    # Check if the document exists
    document = users.find_one(query)
    result = document is not None

    close_client(client)
    return result


def create_talk(topic, max_size, host_id, loc):
    client = connect_to_db()

    talk = {
        "topic": topic,
        "max_size": max_size,
        "host_id": ObjectId(host_id),
        "loc": loc,
        "attendees": [],
        "status": "looking"
    }

    talks = client["QuikTokDB"]["talks"]
    result = talks.insert_one(talk)
    talk_id = result.inserted_id

    # make sure host is in the attendees list and is arrived
    user_join_talk(talk_id, host_id)
    attendee_arrive(talk_id, host_id)

    close_client(client)
    return talk_id


def talk_is_full(talk_id):
    # precondition: the document exists
    # return True if and only if len(attendees) == max_size
    client = connect_to_db()
    # Adjust the collection name as needed
    talks = client["QuikTokDB"]["talks"]

    query = {'_id': ObjectId(talk_id)}
    talk = talks.find_one(query)

    attendees_length = len(talk['attendees'])
    max_size = int(talk['max_size'])
    is_full = attendees_length == max_size

    return is_full


# precondition: talk is not full
def user_join_talk(talk_id, user_id):
    client = connect_to_db()

    talks = client["QuikTokDB"]["talks"]
    users = client["QuikTokDB"]["users"]

    # if user already in attendees, do nothing
    user = users.find_one({ "_id": ObjectId(user_id) })
    if str(user["curr_talk_id"]) == talk_id:
        return None 
    
    # make sure the attendees are lower than max_size, and that the host is still looking for people
    talk = talks.find_one({ "_id": ObjectId(talk_id)})
    attendees = talk["attendees"]
    max_size = talk["max_size"]
    if len(attendees) >= int(max_size):
        return None
    
    # set the user's talk_id to talk_id
    users.update_one({"_id": ObjectId(user_id)}, {
                     "$set": {"curr_talk_id": ObjectId(talk_id)}})

    # # add user_id to the talk's attendees
    # talks.update_one({"_id": ObjectId(talk_id)}, {"$addToSet": {"attendees": ObjectId(user_id)}})

    attendee_object = {
        "user_id": ObjectId(user_id),
        "status": "on_the_way",
        "message": ""
    }

    talk_update_result = talks.update_one(
        {"_id": ObjectId(talk_id)},
        {"$addToSet": {"attendees": attendee_object}}
    )

    close_client(client)
    return talk_update_result


def attendee_update_message(talk_id, user_id, message):
    client = connect_to_db()
    talks = client["QuikTokDB"]["talks"]

    # Update the talk with the new message
    result = talks.update_one(
        {"_id": ObjectId(talk_id), "attendees.user_id": ObjectId(user_id)},
        # Use the $ operator to update the message for the matched user_id
        {"$set": {"attendees.$.message": message}}
    )
    print(result)

    close_client(client)
    return result


def attendee_arrive(talk_id, user_id):
    # update talk-user-status to "arrived"
    client = connect_to_db()
    talks = client["QuikTokDB"]["talks"]

    # Convert string IDs to ObjectId
    talk_id = ObjectId(talk_id)
    user_id = ObjectId(user_id)

    # Define the query and update operation
    query = {
        "_id": talk_id,                        # Find the talk by its ID
        "attendees.user_id": user_id          # Find the attendee by their user_id
    }
    update_operation = {
        "$set": {
            "attendees.$.status": "arrived"  # Update the status of the found attendee
        }
    }

    # Execute the update
    update_result = talks.update_one(query, update_operation)

    close_client(client)
    return update_result


def attendee_cancel(talk_id, user_id):
    # update the user's curr_talk_id to None
    # remove user from talk

    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    talks = client["QuikTokDB"]["talks"]

    # Convert string IDs to ObjectId
    talk_id = ObjectId(talk_id)
    user_id = ObjectId(user_id)

    # update the user's curr_talk_id to None
    query = {"_id": user_id}
    update_operation = {"$set": {"curr_talk_id": None}}
    user_update_result = users.update_one(query, update_operation)

    # remove user from talk
    query = {"_id": talk_id}
    update_operation = {"$pull": {"attendees": {"user_id": user_id}}}
    talk_update_result = talks.update_one(query, update_operation)

    close_client(client)
    return (user_update_result, talk_update_result)


def host_cancel(talk_id):
    # update all users' curr_talk_id to None
    # remove talk

    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    talks = client["QuikTokDB"]["talks"]
    talk_id = ObjectId(talk_id)

    # update all users' curr_talk_id to None
    talk = talks.find_one({"_id": talk_id})
    for attendee in talk.get("attendees", []):
        user_id = attendee["user_id"]
        update_result = users.update_one(
            {"_id": user_id},
            {"$set": {"curr_talk_id": None}}
        )

    # remove talk
    delete_result = talks.delete_one({"_id": talk_id})
    close_client(client)
    return delete_result


def host_done(talk_id):
    # update talk status to Done
    # update all attendees' curr_talk_id to None
    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    talks = client["QuikTokDB"]["talks"]
    talk_id = ObjectId(talk_id)

    update_result = talks.update_one(
        {"_id": talk_id},
        {"$set": {"status": "Done"}}
    )

    talk = talks.find_one({"_id": talk_id})

    if talk:
        attendee_ids = [attendee['user_id'] for attendee in talk.get('attendees', [])]
        for user_id in attendee_ids:
            result = users.update_one(
                {"_id": ObjectId(user_id)},  # Filter by specific user ID
                {"$set": {"curr_talk_id": None}}      # Set curr_talk_id to None
            )

    close_client(client)
    return update_result


def haversine(lat1, lon1, lat2, lon2, unit='miles'):
    # Radius of the Earth
    R_km = 6371.0  # in kilometers
    R_mi = 3958.8  # in miles

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * \
        math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Distance in selected unit
    distance = (R_mi if unit == 'miles' else R_km) * c
    return distance


def find_nearest_talks(user_lat, user_lon):
    # return the 100 talks whose location is near the user's loc
    # return all information of the talks, and the distance
    client = connect_to_db()
    talks = client["QuikTokDB"]["talks"]
    talk_list = talks.find({"status": "looking"})        

    nearest_talks = []

    for talk in talk_list:
        attendees = talk["attendees"]
        max_size = int(talk["max_size"])
        if len(attendees) >= max_size:
            continue

        talk_lat = talk['loc']["lat"]  # Latitude
        talk_lon = talk['loc']["lon"]  # Longitude

        distance = haversine(user_lat, user_lon, talk_lat, talk_lon, unit="miles")
        nearest_talks.append((talk, distance))

    # Sort talks by distance and get the 5 nearest
    nearest_talks.sort(key=lambda x: x[1])
    nearest_talks = nearest_talks[:100]

    result = []
    for talk, distance in nearest_talks:
        topic = talk["topic"]
        status = talk["status"]
        lat = talk["loc"]["lat"]
        lon = talk["loc"]["lon"]
        host_name = find_user_name_by_id(talk["host_id"])
        talk_id = str(talk["_id"])
        result.append({"talk_id": talk_id, "topic": topic, "status": status, "latitude": lat,
                      "longitude": lon, "host_name": host_name, "distance": distance})

    close_client(client)
    return result


def get_all_attendees(talk_id):
    # return a list of attendees objects

    client = connect_to_db()
    talks = client["QuikTokDB"]["talks"]
    talk_id = ObjectId(talk_id)
    talk = talks.find_one({"_id": talk_id})

    result = []

    if talk and "attendees" in talk:
        # Extract the attendees
        attendees = talk["attendees"]
        attendee_list = []
        for i, attendee in enumerate(attendees):
            username = find_user_name_by_id(attendee["user_id"])
            attendee_list.append(
                {'username': username, 'status': attendee["status"], 'message': attendee["message"]})
        result = attendee_list
    else:
        result = []  # Return an empty dict if no talk is found
    close_client(client)
    return result


def get_talk_by_user(user_id):
    # return talk_id by user_id

    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    user = users.find_one({"_id": ObjectId(user_id)})

    if user and "curr_talk_id" in user:
        # Return the curr_talk_id
        result = user["curr_talk_id"]
    else:
        result = None  # Return None if no user is found

    close_client(client)
    return result


def get_talk_status(talk_id):

    client = connect_to_db()
    talks = client["QuikTokDB"]["talks"]
    # Find the talk document by its ID
    talk = talks.find_one({"_id": ObjectId(talk_id)})

    if talk and "status" in talk:
        result = talk["status"]  # Return the status of the talk
    else:
        result = None  # Return None if no talk is found

    close_client(client)
    return result

def get_talk_topic(talk_id):

    client = connect_to_db()
    talks = client["QuikTokDB"]["talks"]
    # Find the talk document by its ID
    talk = talks.find_one({"_id": ObjectId(talk_id)})

    if talk and "topic" in talk:
        result = talk["topic"]  # Return the topic of the talk
    else:
        result = None  # Return None if no talk is found

    close_client(client)
    return result


def set_location(user_id, lat, long):
    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    result = users.update_one(
        {"_id": ObjectId(user_id)},  # Filter by user ID
        {"$set": {"loc": [lat, long]}}   # Set the new location
    )
    close_client(client)
    return result


def get_location(user_id):
    client = connect_to_db()
    users = client["QuikTokDB"]["users"]
    user = users.find_one({"_id": ObjectId(user_id)})
    if user and "loc" in user:
        loc = user["loc"]  # Return the location of the user
    else:
        loc = None  # Return None if no user is found or no location is available
    close_client(client)
    return {'lat': loc[0], 'lon': loc[1]} if loc else None


# print(get_talk_by_user('671d820825d9ddb6bf6ad45a'))

# print(get_all_attendees('671d820925d9ddb6bf6ad45e'))
# topic = "football"
# max_size = "2"
# loc = (0, 0)

# host_id = create_user("aaron", "abc123")
# user_id = create_user("alan", "def456")
# print("user_id: " + str(user_id))
# talk_id = create_talk(topic, max_size, host_id, loc)

# user_join_talk(talk_id, user_id)
# print("Talk is full: " + str(talk_is_full(talk_id)))


# message = "hello!"
# attendee_update_message(talk_id, user_id, message)

# attendee_arrive(talk_id, user_id)

# user_id = "671d820825d9ddb6bf6ad45c"
# talk_id = "671d820925d9ddb6bf6ad45e"
# attendee_cancel(talk_id, user_id)
