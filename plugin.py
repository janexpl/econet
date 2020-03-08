# Basic Python Plugin Example
#
# Author: JanexPL
#
"""
<plugin key="EcoNetPlug" name="Plum Econet Plugin" author="janexpl" version="0.0.1" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://www.google.com/">
    <description>
        <h2>Plum Econet Plugin</h2><br/>
        This plugin reads information such as boiler temperature from Plum Econet Module
        <h3>Configuration</h3>
        See domoticz wiki above.<br/>
    </description>
    <params>
        <param field="Address" label="Domoticz IP Address" width="200px" required="true" default="localhost"/>
        <param field="Port" label="Port" width="40px" required="true" default="8080"/>
        <param field="Username" label="Username" width="200px" required="false" default=""/>
        <param field="Password" label="Password" width="200px" required="false" default=""/>
        <param field="Mode1" label="Econet username" width="200px" required="true" default=""/>
        <param field="Mode2" label="Econet password" width="200px" required="true" default=""/>
        <param field="Mode3" label="UID" width="200px" required="true" default=""/>
        <param field="Mode4" label="Heartbeat" width="200px" required="true" default="30"/>
        <param field="Mode6" label="Logging Level" width="200px">
            <options>
                <option label="Normal" value="Normal"  default="true"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug - Python Only" value="2"/>
                <option label="Debug - Basic" value="62"/>
                <option label="Debug - Basic+Messages" value="126"/>
                <option label="Debug - Connections Only" value="16"/>
                <option label="Debug - Connections+Queue" value="144"/>
                <option label="Debug - All" value="-1"/>
            </options>
        </param>

    </params>
</plugin>
"""
import Domoticz
import requests
import json
from urllib import parse, request
import base64
from datetime import datetime, timedelta
import time

class deviceparam:

    def __init__(self, unit, nvalue, svalue):
        self.unit = unit
        self.nvalue = nvalue
        self.svalue = svalue


class BasePlugin:
    enabled = False
    def __init__(self):
        self.debug = False
        self.heaterTemp = 50
        self.csrftoken = None
        self.expiry = time.time()
        self.uid = None
        self.cwuTemp = None
        self.CWUPump = None
        self.sessionId = None
        self.loglevel = None
        return

    def saveUserVar(self):
        variables = DomoticzAPI("type=command&param=getuservariables")
        varname = Parameters["Name"] + "- CWUPumpWork"
        if variables:
            # there is a valid response from the API but we do not know if our variable exists yet
            novar = True
            valuestring = ""
            if "result" in variables:
                for variable in variables["result"]:
                    if variable["Name"] == varname:
                        valuestring = variable["Value"]
                        novar = False
                        break
            if novar:
                Domoticz.Debug("User Variable {} does not exist. Creation requested".format(varname), "Verbose")
                DomoticzAPI("type=command&param=saveuservariable&vname={}&vtype=2&vvalue={}".format(varname, str(
                    self.CWUPump)))
            else:
                DomoticzAPI("type=command&param=updateuservariable&vname={}&vtype=2&vvalue={}".format(varname, str(
                    self.CWUPump)))



    def login(self):

        try:
            r = requests.get('https://www.econet24.com')
            payload = {'username': Parameters["Mode1"], 'password': Parameters["Mode2"],
                     'csrfmiddlewaretoken': r.cookies['csrftoken']}
            url = "https://www.econet24.com/login/?next=main/"
            rx = requests.post(url, data=payload)
            self.csrftoken = rx.history[0].cookies['csrftoken']
            self.sessionId = rx.history[0].cookies['sessionid']
            for cookie in rx.history[0].cookies:
               if cookie.name == 'csrftoken':
                  self.expiry = cookie.expires
            Domoticz.Debug("Login successfully")
            return True
        except ConnectionError:
            Domoticz.Debug("Unable to connect")
            return False

    def getParams(self):

        try:
            if (self.expiry - time.time()) < 0:
                self.login()
            cookies = {'language': 'pl', 'csrftoken': self.csrftoken,
                    'sessionid': self.sessionId}
            req = "https://www.econet24.com/service/getDeviceParams?uid=" + self.uid
            ry = requests.get(req, cookies=cookies)
            if "error" in ry.json():
                self.login()
            else:
                self.heaterTemp = ry.json()['curr']['tempCO']
                self.cwuTemp = ry.json()['curr']['tempCWU']
                self.CWUPump = ry.json()['curr']['pumpCWUWorks']
            return True
        except ConnectionError:
            Domoticz.Debug("Unable to get temperature")
            return False

    def onStart(self):
        self.uid = Parameters["Mode3"]
        # If poll interval between 10 and 60 sec.
        if 10 <= int(Parameters["Mode4"]) <= 60:
            Domoticz.Log("Update interval set to " + Parameters["Mode4"])
            Domoticz.Heartbeat(int(Parameters["Mode4"]))
        else:
            # If not, set to 20 sec.
            Domoticz.Heartbeat(30)
        # setup the appropriate logging level
        try:
            debuglevel = int(Parameters["Mode6"])
        except ValueError:
            debuglevel = 0
            self.loglevel = Parameters["Mode6"]
        if debuglevel != 0:
            self.debug = True
            Domoticz.Debugging(debuglevel)
            DumpConfigToLog()
            self.loglevel = "Verbose"
        else:
            self.debug = False
            Domoticz.Debugging(0)

        # check if the host domoticz version supports the Domoticz.Status() python framework function
        try:
            Domoticz.Status("This version of domoticz allows status logging by the plugin (in verbose mode)")
        except Exception:
            self.statussupported = False
        # create the child devices if these do not exist yet

        devicecreated = []
        if 1 not in Devices:
            Domoticz.Device(Name="Heater Temperature", Unit=1, TypeName="Temperature").Create()
            devicecreated.append(deviceparam(1, 0, "50"))  # default is 20 degrees

        for device in devicecreated:
            Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)

    def onStop(self):
        Domoticz.Debugging(0)

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        if self.getParams():
            Devices[1].Update(nValue=0, sValue=str(round(self.heaterTemp,2)), TimedOut=False)
            self.saveUserVar()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DomoticzAPI(APICall):

    resultJson = None
    url = "http://{}:{}/json.htm?{}".format(Parameters["Address"], Parameters["Port"], parse.quote(APICall, safe="&="))
    Domoticz.Debug("Calling domoticz API: {}".format(url))
    try:
        req = request.Request(url)
        if Parameters["Username"] != "":
            Domoticz.Debug("Add authentification for user {}".format(Parameters["Username"]))
            credentials = ('%s:%s' % (Parameters["Username"], Parameters["Password"]))
            encoded_credentials = base64.b64encode(credentials.encode('ascii'))
            req.add_header('Authorization', 'Basic %s' % encoded_credentials.decode("ascii"))

        response = request.urlopen(req)
        if response.status == 200:
            resultJson = json.loads(response.read().decode('utf-8'))
            if resultJson["status"] != "OK":
                Domoticz.Error("Domoticz API returned an error: status = {}".format(resultJson["status"]))
                resultJson = None
        else:
            Domoticz.Error("Domoticz API: http error = {}".format(response.status))
    except:
        Domoticz.Error("Error calling '{}'".format(url))
    return resultJson





