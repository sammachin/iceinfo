import pymongo

def check(callerid):
	conn = pymongo.Connection()
	db = conn.test
	numbers = db.numbers
	data = numbers.find_one({"msisdn" : callerid})
	if data:
		return True
	else:
		return False
	

	
def add(msisdn):
	data = {}
	data['msisdn'] = msisdn
	conn = pymongo.Connection()
	db = conn.test
	users = db.users
	users.insert(data)
	
	
def append(msisdn, field, value):
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	res = users.find_one({'msisdn' : msisdn})
	if res[field+"count"] == 0:
		newvalue = []
		newvalue.append(value)
	else:
		newvalue = res[field]
		newvalue.append(value)
	users.update( {'_id' : res['_id']}, { '$inc' : { field+"count" : 1 } })	
	users.update( {'_id' : res['_id']}, { '$set' : { field : newvalue } })

	

def show():
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	resp = users.find()
	for user in resp:
		print user

def update(msisdn, field, value):
	conn = pymongo.Connection()
	db = conn.test
	users = db.users
	res = users.find_one({'msisdn' : msisdn})
	users.update( {'_id' : res['_id']}, { '$set' : { field : value } })
		
def find(msisdn, field):
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	data = users.find_one({'msisdn' : msisdn})
	return data[field]
	
def drop():
	conn = pymongo.Connection()
	db = conn.test
	users = db.users
	users.drop()