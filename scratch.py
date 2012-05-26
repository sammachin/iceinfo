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
	numbers = db.numbers
	numbers.insert(data)
	
	
def update(msisdn, field, value):
	conn = pymongo.Connection()
	db = conn.test
	numbers = db.numbers
	res = numbers.find_one({'msisdn' : msisdn})
	numbers.update( {'_id' : res['_id']}, { '$set' : { field : value } })
	
def find(msisdn, field):
	conn = pymongo.Connection()
	db = conn.test
	numbers = db.numbers
	data = numbers.find_one({'msisdn' : msisdn})
	return data[field]
	