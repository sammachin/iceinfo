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

		
def append(msisdn, field, value):
	conn = pymongo.Connection()
	db = conn.iceinfo
	users = db.users
	countstr = field + "count"
	res = users.find_one({'msisdn' : msisdn})
	if res[countstr] == 0:
		newvalue = []
		newvalue.append(value)
	else:
		newvalue = res[field]
		newvalue.append(value)
	users.update( {'_id' : res['_id']}, { '$inc' : { field+"count" : 1 } })	
	users.update( {'_id' : res['_id']}, { '$set' : { field : newvalue } })
			

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
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Next record your date of birth. After the beep say your date of birth clearly")
		r.record(action="/iceinfo/register/adddob", maxLength=5, method="GET")
		return str(r)
	def adddob(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		update(msisdn, 'dob', RecordingUrl)
		update(msisdn, 'condcount', 0)
		update(msisdn, 'drugcount', 0)
		update(msisdn, 'alergycount', 0)
		update(msisdn, 'nokcount', 0)
		r = twiml.Response()
		r.say("Thankyou")
		r.redirect("/iceinfo/patient/startcondition")
		return str(r)
	start.exposed = True
	addname.exposed = True
	dob.exposed = True
	adddob.exposed = True

	

class patient(object):
	def start(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Press 1 if you want to add an item to your record. Press 2 if you want to review your record")
		r.gather(action="/iceinfo/patient/menu", numDigits=1, method="GET")
		return str(r)
	def menu(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startcondition")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/playbackcond")
		return str(r)
	def startcondition(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Do you have any ongoing medical problems, previous illness or operations you want to record?  Press 1 to add a medical problem, or Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/hascondition", numDigits=1, method="GET")
		return str(r)
	def hascondition(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/askcondition")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startdrugs")
		return str(r)
	def askcondition(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("After the beep please give the name of your 1st  condition, Give the name clearly and briefly - if you don't know the correct name give a very brief description - for example gall bladder operation or  back pain.")
		r.record(action="/iceinfo/patient/addcondition", maxLength=15, method="GET")
		return str(r)
	def addcondition(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		append(msisdn, 'cond', RecordingUrl)
		r = twiml.Response()
		r.say("Thankyou, Press 1 to add another condition, Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/morecondition", numDigits=1, method="GET")
		return str(r)
	def morecondition(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/asknextcondition")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startdrugs")
		return str(r)	
	def asknextcondition(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("After the beep please give the name of your  medical condition, illness or operation. ")
		r.record(action="/iceinfo/patient/addcondition", maxLength=15, method="GET")
		return str(r)
	def startdrugs(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Do you take any medicines you want to record? This could include any tablets, eye drops, injected medicines, inhalers or creams you use.  ICE Info will ask you for the drug name, spelling, dose and how often you take the medication so it may be useful for you to have the boxes in front of you. Press 1 to add a medication or press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/hasdrugs", numDigits=1, method="GET")
		return str(r)
	def hasdrugs(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/askdrugname")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startalergy")
		return str(r)
	def askdrugname(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("After the beep please give the name of your medication. Say the name clearly")
		r.record(action="/iceinfo/patient/adddrugname", maxLength=5, method="GET")
		return str(r)
	def adddrugname(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		r = twiml.Response()
		r.say("Drug names are often similar to each other and can be difficult to distinguish over the phone so after the bleep please spell the name of your medication slowly and clearly")
		r.record(action="/iceinfo/patient/adddrugspelling?drugname=" + RecordingUrl, maxLength=10, method="GET")
		return str(r)
	def adddrugspelling(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		drugname = urllib.quote(cherrypy.request.params['drugname'])
		r = twiml.Response()
		r.say("After the next bleep please say the dose you take of your medication, please give as much detail as possible, for example 2 tablets each containing 5mg")
		r.record(action="/iceinfo/patient/adddrugdose?drugname=" + drugname + "&drugspelling=" + RecordingUrl, maxLength=5, method="GET")
		return str(r)
	def adddrugdose(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		drugname = urllib.quote(cherrypy.request.params['drugname'])
		drugspelling = urllib.quote(cherrypy.request.params['drugspelling'])
		r = twiml.Response()
		r.say("After the next beep please say how often you take your  medication")
		r.record(action="/iceinfo/patient/adddrugfreq?drugname=" + drugname + "&drugspelling=" + drugspelling + "&drugdose=" + RecordingUrl, maxLength=5, method="GET")
		return str(r)
	def adddrugfreq(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		drugfreq = urllib.quote(cherrypy.request.params['RecordingUrl'])
		drugname = urllib.quote(cherrypy.request.params['drugname'])
		drugspelling = urllib.quote(cherrypy.request.params['drugspelling'])
		drugdose = urllib.quote(cherrypy.request.params['drugdose'])
		drug = {}
		drug['name'] = drugname
		drug['spelling'] = drugspelling
		drug['dose'] = drugdose
		drug['freq'] = drugfreq
		append(msisdn, 'drug', drug)
		r = twiml.Response()
		r.say("Thankyou, Press 1 to add another medication, Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/moredrugs", numDigits=1, method="GET")
		return str(r)
	def moredrugs(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/askdrugname")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startalergy")
		return str(r)
	def startalergy(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Do you have any allergies you want to record? Press 1 to add an allergy or Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/hasalergy", numDigits=1, method="GET")
		return str(r)
	def hasalergy(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/askalergy")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startnok")
		return str(r)
	def askalergy(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("After the beep please give the name of the drug, food or substance you are allergic to.")
		r.record(action="/iceinfo/patient/addalergy", maxLength=10, method="GET")
		return str(r)
	def addalergy(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		r = twiml.Response()
		r.say("After the beep give a very brief description of the reaction you have for example rash, nausea, facial swelling.")
		r.record(action="/iceinfo/patient/addreaction?alergy=" + RecordingUrl, maxLength=10, method="GET")
		return str(r)
	def addreaction(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		reaction = urllib.quote(cherrypy.request.params['RecordingUrl'])
		name = urllib.quote(cherrypy.request.params['alergy'])
		alergy = {}
		alergy['name'] = name
		alergy['reaction'] = reaction
		append(msisdn, 'alergy', alergy)
		r = twiml.Response()
		r.say("Thankyou, Press 1 to add another alergy, Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/morealergy", numDigits=1, method="GET")
		return str(r)
	def morealergy(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/askalergy")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/startnok")
		return str(r)
	def startnok(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("Do you wish to record a next-of-kin or emergency contact? In the event of an emergency ICE Info may be used to contact the people you enter in this section so only include people who you would want to be contacted  Press 1 to add a contact, or Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/hasnok", numDigits=1, method="GET")
		return str(r)
	def hasnok(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/asknok")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/complete")
		return str(r)
	def asknok(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("After the beep say the name of your contact. ")
		r.record(action="/iceinfo/patient/addnokname", maxLength=10, method="GET")
		return str(r)
	def addnokname(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		RecordingUrl = urllib.quote(cherrypy.request.params['RecordingUrl'])
		r = twiml.Response()
		r.say("After the beep key in the phone number for your contact")
		r.gather(action="/iceinfo/patient/addnoknum?name=" + RecordingUrl, numDigits=11, method="GET")
		return str(r)
	def addnoknum(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		name = urllib.quote(cherrypy.request.params['name'])
		number = urllib.quote(cherrypy.request.params['Digits'])
		nok = {}
		nok['name'] = name
		nok['number'] = number
		append(msisdn, 'nok', nok)
		r = twiml.Response()
		r.say("Thankyou, Press 1 to add another contact, Press 2 to skip to the next section")
		r.gather(action="/iceinfo/patient/morenok", numDigits=1, method="GET")
		return str(r)
	def morenok(self, var=None, **params):
		callerid = urllib.quote(cherrypy.request.params['From'])
		digit = urllib.quote(cherrypy.request.params['Digits'])
		if digit == "1":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/asknok")
		elif digit == "2":
			r = twiml.Response()
			r.say("thankyou")
			r.redirect("/iceinfo/patient/complete")
		return str(r)
	def complete(self, var=None, **params):
		r = twiml.Response()
		r.say("Thank you for using ICE Info. Make sure ICE Info is saved in your phone address book so that healthcare workers can find and access your record in the event of an emergancy. You can phone the ICE Info number at any time to listen to, add to or delete any part of your entry.")
		r.hangup()
		return str(r)
	start.exposed = True
	menu.exposed = True
	startcondition.exposed = True
	hascondition.exposed = True
	askcondition.exposed = True
	addcondition.exposed = True
	morecondition.exposed = True
	asknextcondition.exposed = True
	startdrugs.exposed = True
	hasdrugs.exposed = True
	askdrugname.exposed = True
	adddrugname.exposed = True
	adddrugspelling.exposed = True
	adddrugdose.exposed = True
	adddrugfreq.exposed = True
	moredrugs.exposed = True
	startalergy.exposed = True
	hasalergy.exposed = True
	askalergy.exposed = True
	addalergy.exposed = True
	addreaction.exposed = True
	morealergy.exposed = True
	startnok.exposed = True
	hasnok.exposed = True
	asknok.exposed = True
	addnokname.exposed = True
	addnoknum.exposed = True
	morenok.exposed = True
	complete.exposed = True
	

class clinician(object):		
	def start(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("You have accessed the ICE record for")
		r.play(find(msisdn, 'name'))
		r.say("Date of Birth") 
		r.play(find(msisdn, 'dob'))
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
			num = ""
			noks = find(msisdn, 'nok')
			for nok in noks:
				num += nok['number']
			r.dial(number=num)
		return str(r)
	def history(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		r = twiml.Response()
		r.say("ICE Info will play back each entry on record for")
		r.play(find(msisdn, 'name'))
		r.say("Past Medical History: There are %s entries in this section" % find(msisdn, 'condcount'))
		r.redirect("/iceinfo/clinician/playcond?item=0")
		return str(r)
	def playcond(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		conds = find(msisdn, 'cond')
		r = twiml.Response()
		r.play(conds[item])
		if find(msisdn, 'condcount') == item +1:
			r.say("end of medical history")
			r.say("Press 1 to replay this entry, Press 3 to move to the next section")
		else:
			r.say("Press 1 to replay this entry, Press 2 to move to the next entry, Press 3 to move to the next section")
		r.gather(action="/iceinfo/clinician/condmenu?item=" + item, numDigits=1, method="GET")
		return str(r)
	def condmenu(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		digit = urllib.quote(cherrypy.request.params['Digits'])
		r.twiml.Response()
		r.say('thankyou')
		if digit == "1":
			r.redirect("/iceinfo/clinician/playcond?item=" + str(item))
		elif digit == "2":
			r.redirect("/iceinfo/clinician/playcond?item=" + str(item +1 ))
		elif digit == "3":
			r.say("Drug History: There are %s entries in this section" % find(msisdn, 'drugcount'))
			r.redirect("/iceinfo/clinician/playdrug?item=0")
		return str(r)
	def playdrug(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		drugs = find(msisdn, 'drug')
		r = twiml.Response()
		r.play(drugs[item]['name'])
		r.play(drugs[item]['spelling'])
		r.play(drugs[item]['dose'])
		r.play(drugs[item]['freq'])
		if find(msisdn, 'drugcount') == item +1:
			r.say("end of drug history")
			r.say("Press 1 to replay this entry, Press 3 to move to the next section")
		else:
			r.say("Press 1 to replay this entry, Press 2 to move to the next entry, Press 3 to move to the next section")
		r.gather(action="/iceinfo/clinician/drugmenu?item=" + item, numDigits=1, method="GET")
		return str(r)
	def drugmenu(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		digit = urllib.quote(cherrypy.request.params['Digits'])
		r.twiml.Response()
		r.say('thankyou')
		if digit == "1":
			r.redirect("/iceinfo/clinician/playdrug?item=" + str(item))
		elif digit == "2":
			r.redirect("/iceinfo/clinician/playdrug?item=" + str(item +1 ))
		elif digit == "3":
			r.say("Alergies: There are %s entries in this section" % find(msisdn, 'alergycount'))
			r.redirect("/iceinfo/clinician/playalergy?item=0")
		return str(r)
	def playalergy(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		alergies = find(msisdn, 'alergy')
		r = twiml.Response()
		r.play(alergies[item]['name'])
		r.play(alergies[item]['reaction'])
		if find(msisdn, 'alergycount') == item +1:
			r.say("end of alergy history")
			r.say("Press 1 to replay this entry, Press 3 to move to the next section")
		else:
			r.say("Press 1 to replay this entry, Press 2 to move to the next entry, Press 3 to move to the next section")
		r.gather(action="/iceinfo/clinician/alergymenu?item=" + item, numDigits=1, method="GET")
		return str(r)
	def alergymenu(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		digit = urllib.quote(cherrypy.request.params['Digits'])
		r.twiml.Response()
		r.say('thankyou')
		if digit == "1":
			r.redirect("/iceinfo/clinician/playalergy?item=" + str(item))
		elif digit == "2":
			r.redirect("/iceinfo/clinician/playalergy?item=" + str(item +1 ))
		elif digit == "3":
			r.say("Next of Kin: There are %s entries in this section" % find(msisdn, 'nokcount'))
			r.redirect("/iceinfo/clinician/playnok?item=0")
		return str(r)
	def playnok(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		noks = find(msisdn, 'nok')
		r = twiml.Response()
		r.play(noks[item]['name'])
		r.say(noks[item]['number'])
		if find(msisdn, 'nokcount')) == item +1:
			r.say("end of Next of Kin list")
			r.say("Press 1 to replay this entry, Press 4 to phone this contact, Press 5 to phone all contacts and speak to the first to answer.")
		else:
			r.say("Press 1 to replay this entry, Press 2 to move to the next entry, Press 3 to move to the next section, Press 4 to phone this contact, Press 5 to phone all contacts and speak to the first to answer.")
		r.gather(action="/iceinfo/clinician/nokmenu?item=" + item, numDigits=1, method="GET")
		return str(r)
	def nokmenu(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		digit = urllib.quote(cherrypy.request.params['Digits'])
		r.twiml.Response()
		r.say('thankyou')
		if digit == "1":
			r.redirect("/iceinfo/clinician/playnok?item=" + str(item))
		elif digit == "2":
			r.redirect("/iceinfo/clinician/playnok?item=" + str(item +1 ))
		elif digit == "3":
			r.say("You have reached the end of this entry. Press 1 to return to the beginning or hang up now.")
			r.gather(action="/iceinfo/clinician/completemenu", numDigits=1, method="GET")
		elif digit == "4":
			noks = find(msisdn, 'nok')
			num = noks[item]['number']
			r.dial(number=num)
		elif digit == "5":
			num = ""
			noks = find(msisdn, 'nok')
			for nok in noks:
				num += nok['number']
			r.dial(number=num)
		return str(r)
	def completemenu(self, var=None, **params):
		msisdn = urllib.quote(cherrypy.request.params['From'])
		item = int(urllib.quote(cherrypy.request.params['item']))
		digit = urllib.quote(cherrypy.request.params['Digits'])
		r.twiml.Response()
		r.say('thankyou')
		if digit == "1":
			r.redirect("/iceinfo/clinician/start")
		else:
			r.hangup()
		return str(r)	
	start.exposed = True
	menu.exposed = True
	history.exposed = True
	playcond.exposed  = True
	condmenu.exposed = True
	playdrug.exposed = True
	drugmenu.exposed = True
	playalergy.exposed = True
	alergymenu.exposed = True
	playnok.exposed = True
	nokmenu.exposed = True
	completemenu.exposed = True


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

