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
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default=""/>
        <param field="UID" label="UID" width="200px" required="true" default=""/>
        <param field="Mode1" label="Logging Level" width="200px">
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
        self.sessionId = None
        self.loglevel = None
        return
    def login(self):
        noerror = True
        try:
            r = requests.get('https://www.econet24.com')
            payload = {'username': Parameters["Username"], 'password': Parameters["Password"],
                     'csrfmiddlewaretoken': r.cookies['csrftoken']}
            url = "https://www.econet24.com/login/?next=main/"
            rx = requests.post(url, data=payload)
            self.csrftoken = rx.history[0].cookies['csrftoken']
            self.sessionId = rx.history[0].cookies['sessionid']
            for cookie in rx.history[0].cookies:
               if cookie.name == 'csrftoken':
                  self.expiry = cookie.expires
        except ConnectionError:
            Domoticz.Debug("Unable to connect")
            noerror = False

        return noerror

    def getTemp(self):
        noerror = True
        try:
            cookies = {'language': 'pl', 'csrftoken': self.csrftoken,
                    'sessionid': self.sessionId}
            req = "https://www.econet24.com/service/getDeviceRegParams?uid=" + self.uid
            ry = requests.get(req, cookies=cookies)
            self.heaterTemp = ry.json()['data']['1024']
        except ConnectionError:
            Domoticz.Debug("Unable to get temperature")
            noerror = False
        return noerror

    def onStart(self):
        self.uid = Parameters["UID"]

        # setup the appropriate logging level
        try:
            debuglevel = int(Parameters["Mode1"])
        except ValueError:
            debuglevel = 0
            self.loglevel = Parameters["Mode1"]
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
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat called")

        if (self.expiry - datetime.now) < 0:
            self.login()

        self.getTemp()
        Devices[1].Update(nValue=0, sValue=str(self.heaterTemp), TimedOut=False)

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





