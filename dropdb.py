import pymongo

conn = pymongo.Connection()
db = conn.iceinfo
users = db.users
users.drop