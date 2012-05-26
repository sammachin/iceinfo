#! /usr/bin/env python

import pymongo

conn = pymongo.Connection()
db = conn.iceinfo
users = db.users
resp = users.find()
for user in resp:
	print user