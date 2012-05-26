import cherrypy
import memcache
import random
import simplejson
import pymongo
import urllib2
import urllib
import re
from django.template import Template, Context, loader
from django.conf import settings
from twilio import twiml
from twilio.rest import TwilioRestClient
import creds


#Twilio Details
account = creds.twilio_account
token = creds.twilio_token

mc = memcache.Client(['127.0.0.1:11211'], debug=0)

settings.configure(TEMPLATE_DIRS = ( "/server/iceinfo/static",))

	
def sendsms(dest, msg):
	print dest
	print msg
	client = TwilioRestClient(account, token)
	client.sms.messages.create(to=dest, body=msg)


def registered(callerid):
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	data = users.find_one({"msisdn" : callerid})
	if data:
		return True
	else:
		return False

def update(msisdn, field, value):
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	res = users.find_one({'msisdn' : msisdn})
	users.update( {'_id' : res['_id']}, { '$set' : { field : value } })

def find(msisdn, field):
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	data = users.find_one({'msisdn' : msisdn})
	return data[field]

		

			

class register(object):		
	def start(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		data = {}
		data['msisdn'] = msisdn
		conn = pymongo.Connection()
		db = conn.iceinfo
		users = db.users
		users.insert(data)
		r = twiml.Response()
		r.say("First record your name. After the beep say your name clearly")
		r.record(action="/iceinfo/register/addname", maxLength=5, method="GET")
		return str(r)
	def addname(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		update(msisdn, 'name', RecordingUrl)
		r = twiml.Response()
		r.say("Thankyou")
		r.redirect("/iceinfo/register/dob")
		return str(r)
	def dob(self, var=None, **params):
		print "ASKING FOR DOB"
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Next record your date of birth. After the beep say your date of birth clearly")
		r.record(action="/iceinfo/register/adddob", maxLength=5, method="GET")
		return str(r)
	def adddob(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		update(msisdn, 'dob', RecordingUrl)
		r = twiml.Response()
		r.say("Thankyou")
		r.redirect("/iceinfo/start")
		return str(r)
	start.exposed = True
	addname.exposed = True
	dob.exposed = True
	adddob.exposed = True

	

class patient(object):
	def start(self, var=None, **params):
		return "Patient"
	start.exposed = True
	

class clinician(object):		
	def start(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("You have accessed the ICE record for")
		r.play(find(msisdn, 'name'))
		r.say("Date of Birth") 
		r.play(find(msisnd, 'dob'))
		r.say("Press 1 to access the record or Press 2 to phone the patients next of kin")
		r.gather(action="/iceinfo/clinician/menu", numDigits=1, method="GET")
		return str(r)
	def menu(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		digits = urllib.quote(cherrypy.request.params['digits'])
		if digits == "1":
			r = twiml.Response()
			r.redirect("/iceinfo/clinician/history")
		elif digits == "2":
			r = twiml.Response()
			r.play(find(msisdn, 'name'))
			r.say("has registered" + str(len(find(msisdn, 'noks'))) + "contacts, ICE Info will now ring these contacts and connect you to the first to answer.")
			r.dial(number=str(",".join((find(msisdn, 'noks')))))
		return str(r)
								


class start(object):
	register = register()
	patient = patient()
	clinician = clinician()
	def start(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		if registered(callerid):
			r = twiml.Response()
			r.say("Welcome to ICE Info, Press 1 if you are a clinician and need to access a record, Press 2 if you are a patient and need to listen to,  add or delete a record")
			r.gather(action="/iceinfo/mainmenu", numDigits=1, method="GET")
		else:
			r = twiml.Response()
			r.say("Welcome to ICE Info, Each ICE record is linked to a mobile phone number.  Once you've set up a record it will only be able to be accessed from this mobile. You can choose how much to include or not include on your record and who you allow to use your mobile phone. If you lose your phone you will need to contact your phone company to disable your phone and if you change your phone number you will need to delete your record first.")
			r.redirect("/iceinfo/register/start")
		return str(r)
	def mainmenu(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/clinician/start")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/start")
		return str(r)
	mainmenu.exposed = True
	start.exposed = True
				
cherrypy.config.update('app.cfg')
app = cherrypy.tree.mount(start(), '/', 'app.cfg')
cherrypy.config.update({'server.socket_host': '0.0.0.0',
                        'server.socket_port': 9032})

if hasattr(cherrypy.engine, "signal_handler"):
    cherrypy.engine.signal_handler.subscribe()
if hasattr(cherrypy.engine, "console_control_handler"):
    cherrypy.engine.console_control_handler.subscribe()
cherrypy.engine.start()
cherrypy.engine.block()

