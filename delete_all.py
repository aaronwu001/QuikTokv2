import db
client = db.connect_to_db()

users = client['QuikTokDB']['users']
talks = client['QuikTokDB']['talks']

user_result = users.delete_many({})
talk_result = talks.delete_many({})
print(f"Deleted {user_result.deleted_count} user documents.")
print(f"Deleted {talk_result.deleted_count} talk documents.")

db.close_client(client)