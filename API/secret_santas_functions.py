import logging
import random
import os
import json
from bson import ObjectId
import random
import smtplib
from email.message import EmailMessage
import os
import re
from pymongo import MongoClient


SENDER_EMAIL = os.getenv('SMTP_SENDER_EMAIL')
EMAIL_SUBJECT = os.getenv('SMTP_SUBJECT')
SMTP_SERVER = os.getenv('SMTP_URL')  # Replace with your SMTP server
SMTP_PORT = int(os.getenv('SMTP_PORT'))  # Replace with your SMTP server's port
SMTP_USERNAME = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASW')
MONGO_HOST = os.getenv('MONGODB_HOST')
MONGO_PORT = int(os.getenv('MONGODB_PORT'))
MONGO_DB = os.getenv('MONGODB_DB')
MONGO_USER = os.getenv('MONGODB_USER')
MONGO_PASS = os.getenv('MONGODB_PASS')

client = MongoClient(f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}")
db = client[MONGO_DB]


#print(f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}")

def send_email(SENDER_EMAIL, receiver_email, subject, body, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#            server.connect()
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
#            server.close()
        logging.info("Email sent successfully!")
        return "Email sent successfully!"
    except Exception as e:
        logging.info(f"Error sending email: {e}")
        return f"Error sending email: {e}"

def get_participant_details(collection, participant_id):
    participant_details = collection.find_one({"_id": ObjectId(participant_id)})
    if not participant_details:
        raise ValueError(f"Participant details not found for ID: {participant_id}")
    return participant_details  

def send_secret_santa(collection, assignments):
    for santa, recipient in assignments.items():
        santa_details = get_participant_details(collection, santa)
        recipient_details = get_participant_details(collection, recipient)

        receiver_email = f"{santa_details['email']}"
        email_body = f"Congratulations {santa_details['Name']} {santa_details['Surname']}, you are Secret Santa for {recipient_details['Name']} {recipient_details['Surname']}"
        send_email(SENDER_EMAIL, receiver_email, EMAIL_SUBJECT, email_body, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)

def secret_santa(ids):
    shuffled_ids = list(ids)
    random.shuffle(shuffled_ids)
    assignments = {}
    for i in range(len(ids)):
        while True:
            recipient = random.choice(shuffled_ids)
            if recipient != ids[i]:
                break
        assignments[ids[i]] = recipient
        shuffled_ids.remove(recipient)
    return assignments

def print_secret_santa(collection, assignments):
    secret_santa_data = []

    for santa, recipient in assignments.items():
        santa_details = get_participant_details(collection, santa)
        recipient_details = get_participant_details(collection, recipient)

        santa_info = {
            "santa_name": f"{santa_details['Name']} {santa_details['Surname']}",
            "santa_email": santa_details['email'],
            "recipient_name": f"{recipient_details['Name']} {recipient_details['Surname']}",
            "recipient_email": recipient_details['email']
        }
        secret_santa_data.append(santa_info)

    return secret_santa_data



def db_healthcheck():
    try:
        db_ping = db.command('ping')
        if db_ping:
            return "Healthy"
    except db.command.ConnectionFailure:
        logging.info("Could Not Connect To DB")
        return "Unhealthy"
    




def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def insert_user(collection, user_data):
    try:
        if not validate_email(user_data["email"]):
            logging.info("Invalid email. Not inserting.")
            return "Invalid email. Not inserting."

        # Check for existing user with the same email
        existing_email = collection.find_one({"email": user_data["email"]})
        if existing_email:
            logging.info("User with this email already exists. Not inserting.")
            return "User with this email already exists. Not inserting."

        # Check for existing user with same details
        existing_user = collection.find_one({
            "Name": user_data["Name"],
            "Surname": user_data["Surname"],
            "email": user_data["email"]
        })

        if existing_user:
            logging.info("User with same name, surname, and email already exists. Not inserting.")
            return "User with same name, surname, and email already exists. Not inserting."
        user_data.pop('group')
        result = collection.insert_one(user_data)
        if result.inserted_id:
            logging.info('Data stored in MongoDB successfully!')
            update_pipeline(collection.database, collection.name)  
            return "Data stored in MongoDB successfully!"
        else:
            logging.info('Failed to store data in MongoDB.')
            return "Failed to store data in MongoDB."
    except Exception as e:
        logging.info(f"Error inserting user data: {e}")
        return f"Error inserting user data: {e}"
        

def get_rooms_with_object_ids(object_id=None):
    try:
        rooms_collection = db["rooms"]

        if object_id:
            room = rooms_collection.find_one({"_id": ObjectId(object_id)})
            if room:
                return {"room": room["collection_name"]}
            else:
                logging.info(f"No room found with ObjectId: {object_id}")
                return None
        else:
            rooms = rooms_collection.find({}, {"_id": 1, "collection_name": 1})
            rooms_data = []
            for room in rooms:
                room_data = {
                    "room_id": str(room["_id"]),
                    "room": room["collection_name"]
                }
                rooms_data.append(room_data)
            return rooms_data
    except Exception as e:
        logging.info(f"Error retrieving rooms with ObjectIDs: {e}")
        return None


        
def update_pipeline(database, collection_name):
    try:
        pipeline_collection = database["rooms"]
        existing_collection = pipeline_collection.find_one({"collection_name": collection_name})
        if not existing_collection:
            pipeline_collection.insert_one({"collection_name": collection_name})
            logging.info(f"Pipeline updated with collection: {collection_name}")
        else:
            logging.info(f"Collection '{collection_name}' already exists in 'rooms'. Skipping update.")
    except Exception as e:
        logging.info(f"Error updating pipeline: {e}")