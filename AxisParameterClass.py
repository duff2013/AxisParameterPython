#-------------------------------------------------------------------------------
# Name:        Axis Parameter Handler
# Purpose:
#
# Author:      Marcus Follrud
#
# Created:     19-01-2012
# Licence:     MIT
#-------------------------------------------------------------------------------
#!/usr/bin/env python
#!/bin/python
import re
import sys
import pycurl
import cStringIO

class AxisParameterClass:

    def __init__(self,ip="10.13.24.158",username="root",password="pass",vapixversion=None):
        self.vapixversion = vapixversion
        self.vapixurls = {2: "/axis-cgi/admin/param.cgi", 3:"/axis-cgi/param.cgi"}
        self.ip = ip
        self.username = username
        self.password = password



    def setCredentials(self,username,password):
        self.username = username
        self.password = password

    def setIP(self,ip):
        self.ip = ip

    def determineVapixVersion(self):
        try:
            res = self.getVapixResult("http://"+self.ip+self.vapixurls[3])
            if res['statuscode'] == 401:
                print "Bad credentials"
                return -1
            if res['statuscode'] == 200:
                #URL existed. Use vapix 3.
                self.vapixversion = 3
                return 3
            elif res['statuscode'] == 404:
                #try vapix 2
                res = self.getVapixResult("http://"+self.ip+self.vapixurls[2])
                if res['statuscode'] == 404:
                    return "UknownVapixVersion"
                elif res['statuscode'] == 200:
                    self.vapixversion = 2
                    return 2
            else:
                return "UnknownError" #this should never happen.
        except Exception:
            print "Unexpected error:", sys.exc_info()[0], sys.exc_info()[1]


    def getParameters(self,group=None):

        if self.vapixversion == None:
            vapixversion = self.determineVapixVersion()
            if vapixversion == "UknownError" or vapixversion == "UnknownVapixVersion":
                #TODO: Define unknown vapix version exception
                return None

        url = "http://"+self.ip+self.vapixurls[self.vapixversion]
        groupreq = "action=list"
        if group != None:
            #Add postparameter for group.
            groupreq = groupreq + "&group="
            for parameter in group:
                groupreq = groupreq + parameter.name + ","
            req = self.getVapixResult(url,"POST",groupreq[:-1]) #last comma seems to duplicate the response from camera
        else:
            req = self.getVapixResult(url,post)


        #Parse through the answer.
        #Parameters will come as Single lines. If parameter isn't found Line will start with #Error - description.
        parameters = []
        for lines in req['data'].replace("root.","").split('\n'):
            if lines.startswith('# Error') != True:
                parameter = lines.split("=")
                if parameter != ['']: #Last row is always empty
                	parameterclass = AxisParameter(parameter[0],parameter[1])

            else:
                #Parameter didn't exist. Add it to class, set value to None and enter the error message in the class
                if lines.startswith('# Error: Error -1 getting param in group '):
                	lines = lines.replace('# Error: Error -1 getting param in group ','')
                	parameterclass = AxisParameter(lines[1:-1],None) #Should contain the parameter
            parameters.append(parameterclass)
        return parameters


    def updateParameters(self,params):
    	if self.vapixversion == None:
    		vapixversion = self.determineVapixVersion()
	    	if vapixversion == "UnknownError" or vapixversion == "UnknownVapixVersion":
    			#TODO: Define unknown vapix version exception
    			return None

    	url = "http://"+self.ip+self.vapixurls[self.vapixversion]
    	post = "action=update&"

    	if not params:
    		return False
    		#TODO: Raise exception on list required.

    	#assemble parameters
    	for param in params:
    		#All params are sent as strings.
    		post = post + str(param.name)+"="+str(param.value)+","

    	if post.endswith(','):
    		post = post[:-1] #skip last comma

    	req = self.getVapixResult(url,"POST",post)
    	if req['data'].strip() == "OK":
    		#all ok.
    		return param
    	else:
    		#TODO: loop answer. look for errors. match with parameter.
        	for lines in req['data'].replace("root.","").split('\n'):
        		m = re.match(r"# Error: Error setting '(.*?)' to '(.*?)'!",lines,re.DOTALL)
        		print m.group()

    def removeParameters(self,params):
        #Check if we have knowledge of vapix version.
        if self.vapixversion == None:
            vapixversion = self.determineVapixVersion()
            if vapixversion == "UnknownError" or vapixversion == "UnknownVapixVersion":
                #TODO: Define unknown vapix version exception
                return None

        url = "http://"+self.ip+self.vapixurls[self.vapixversion]
        post = "action=remove&group="

        if not params:
           	return False
           	#TODO: Raise exception on list required.

        #assemble the parameters
        for param in params:
        	post = post + param.name

        #Delete the posts
        req = self.getVapixResult(url,"GET",post)
        if req['data'].strip() == "OK":
        	#All parameters got removed.
        	for param in params:
        		param.status = "OK"
        		param.value = None
        else:
        	#We might have an error here.
        	#TODO: Investigate if there can be an exception and still return data.
        	errors = []
        	for lines in req['data'].replace("root.","").split('\n'):
        		if lines.startswith('# Request failed: Error -1'):
        			lines = lines.replace("# Request failed: Error -1 deleting group '","")
        			lines = lines[:-1]
        			errors.append(lines)

        	#If the parameters couldn't be deleted. Add the group back with status=None.
        	for param in params:
        		if param.name in errors:
        			param.status = None
        		else:
        			param.status = "OK"
        			param.value = None

        return params


    def getVapixResult(self,url,httpmethod="GET",params=""):
        #urllib2 didn't work with removing parameters for some reason. Usig pyCurl instead
        p = pycurl.Curl()

        if self.password != None:
        	p.setopt(pycurl.HTTPAUTH,pycurl.HTTPAUTH_BASIC)
        	p.setopt(pycurl.USERPWD,self.username+":"+self.password)


        if httpmethod == "POST":
        	p.setopt(pycurl.POSTFIELDS,params)
        	p.setopt(pycurl.URL,url)
        else: #assume GET
        	p.setopt(pycurl.URL,url+"?"+params)

        buf = cStringIO.StringIO()
        p.setopt(p.WRITEFUNCTION, buf.write)

        p.perform()
        data=buf.getvalue()
        code=p.getinfo(pycurl.RESPONSE_CODE)
        buf.close()
        p.close()
        return {"data": data, "statuscode": code}


class AxisParameter:

    def __init__(self,name=None,value=None):
        self.name=name
        self.value=value
        self.status=None

    def getValue(self):
        return self.name
    def setValue(self,val):
        self.value = val
    def setName(self,val):
        self.name = val