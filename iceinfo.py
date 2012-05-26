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
		r.say("First of all please record your name,")
		r.record(action="/iceinfo/register/addname", maxLength=10, method="GET")
		r.redirect("/iceinfo/regsiter/dob")
		return str(r)
	def addname(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		update(msisdn, 'name', RecordingUrl)
	def dob(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Thank you, now please tell me your date of birth,")
		r.record(action="/iceinfo/register/adddob", maxLength=6, method="GET")
		r.redirect("/iceinfo/regsiter/dob")
		return str(r)
	def adddob(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		update(msisdn, 'dob', RecordingUrl)
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
		r.say("This record was last checked and up-dated") 
		r.say(updated(msisdn))
		r.say("Press 1 to access the record or Press 2 to phone the patients next of kin")
		r.gather(action="/iceinfo/clincian/menu", numDigits=1, method="GET")
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
			r.say("Welcome to Ice Info, Press 1 if your are a clinician, Press 2 if you are the patient")
			r.gather(action="/iceinfo/mainmenu", numDigits=1, method="GET")
		else:
			r = twiml.Response()
			r.say("Welcome to Ice Info, This phone number is not yet registered, to learn more about the service press 1 or to get started press 2")
			r.gather(action="/iceinfo/newuser", numDigits=1, method="GET")
		return str(r)
	def newuser(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("Ice info allows you to record information useful to your Doctors if you are admitted to hospital")
		elif digit == "2":
			print "SENDING REDIRECT"
			r = twiml.Response()
			r.say("Thankyou")
			r.redirect("/iceinfo/register/start")
		return str(r)
	def mainmenu(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.redirect("/iceinfo/clinician/start")
		elif digit == "2":
			r = twiml.Response()
			r.redirect("/iceinfo/patient/start")
		return str(r)
	mainmenu.exposed = True
	start.exposed = True
	newuser.exposed = True			
			
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

