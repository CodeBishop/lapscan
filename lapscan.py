#!/usr/bin/env python

# Terminology
#   Field:
#       A box on the build sheet consisting of an case-insensitive ID string and a data string. For example:
#           "Volume control", "OK (   )  Fn + F10  F11  F12"
#           The ID string is case-insensitive but should otherwise precisely match the name on the printed build sheets.
#   Sub-field:
#       A piece of data about a machine such as cpu speed in GHZ or the size of the second DIMM in GB.
#       A sub-field is a list of pairs of strings, each pair is (value, source).
#       The name of a sub-field should include its units-type (GB, mhz, etc), its value should not.
#   Machine:
#       Encapsulation of a dictionary of sub-fields keyed on a case-insensitive string.
#       Manufactures Fields on-the-fly.
#       Prints a build sheet to console by calling its field(id) methods.
#       Constructs a build spreadsheet by calling its field(id) methods.
#   DataProvider:
#       Encapsulation of a date source such a /etc/release or the lspci utility.
#       The populate(machine) method adds (value, source) pairs to a the sub-fields of a machine.

FIRST_COL_WIDTH = 16  # Character width of first column when printing a build sheet to the console..
EMPTY_SUBFIELD = "____"


class Subfield:
    def __init__(self):
        self.data = []

    def addData(self, val, source):
        self.data.append((val, source))

    def value(self):
        if len(self.data) == 0:
            return EMPTY_SUBFIELD
        else:
            val, source = self.data[0]
            return val


class Machine:
    def __init__(self):
        self.subfieldData = {}

    def subfield(self, name):
        name = name.lower()
        if name not in self.subfieldData:
            return EMPTY_SUBFIELD
        else:
            return self.subfieldData[name].value()

    def setSubfield(self, name, value, source):
        name = name.lower()
        if name not in self.subfieldData:
            self.subfieldData[name] = Subfield()
        self.subfieldData[name].addData(value, source)

    def field(s, name):
        name = name.lower()
        line = ""
        if name == "cpu":
            line = s.subfield("cpu make") + " " + s.subfield("cpu model") + " @ " + s.subfield("cpu ghz") + " GHZ"
        return line

    def printBuild(self):
        print "CPU".ljust(FIRST_COL_WIDTH) + self.field("CPU")


class DataProviderLSHWShort:
    def __init__(self):
        self.sourceID = "lshw-short"
        self.lines = open("../lapscanData/thinkpad_t61/lshw_short.out").readlines()

    def populate(self, machine):
        # Determine the column widths from the column headers.
        deviceColumn = self.lines[0].find("Device")
        classColumn = self.lines[0].find("Class")
        descColumn = self.lines[0].find("Description")

        # Process output to add data to the machine dictionary.
        for i in range(2, len(self.lines)):
            # Extract the four fields of a lshw-short entry.
            hwpathField = self.lines[i][0:deviceColumn].strip()
            deviceField = self.lines[i][deviceColumn:classColumn].strip()
            classField = self.lines[i][classColumn:descColumn].strip()
            descField = self.lines[i][descColumn:].strip()

            # Help variables for skipping redundant data.
            displayAlreadyKnown = False

            # Process the data in the fields.
            if classField == "disk":
                if deviceField == "/dev/sda":
                    pass
                if deviceField == "/dev/cdrom":
                    pass

            elif classField == "display" and not displayAlreadyKnown:
                pass
                displayAlreadyKnown = True  # Skip further (redundant) entries about the video hardware.

            elif classField == "memory":
                sysMemColumn = descField.find("System Memory")
                if sysMemColumn != -1:
                    pass
                elif descField.find("DIMM") != -1:
                    pass

            elif classField == "multimedia":
                pass

            elif classField == "network":
                descFieldLow = descField.lower()
                if descFieldLow.find("ethernet") != -1:
                    pass
                elif descFieldLow.find("wifi") != -1 or descFieldLow.find("wireless") != -1:
                    pass
                else:
                    pass

            elif classField == "processor":
                machine.setSubfield("cpu ghz", "77.7", self.sourceID)  # DEBUG: test value

            elif classField == "system":
                pass


# Extract information from "lshw -short" output and add it to the machine dictionary.
def readLSHWShort(machDict, lines):
    # Determine the column widths from the column headers.
    deviceColumn = lines[0].find("Device")
    classColumn = lines[0].find("Class")
    descColumn = lines[0].find("Description")

    # Helper variables.
    displayFieldTaken = False

    # Process output to add data to the machine dictionary.
    for i in range(2, len(lines)):
        # Extract the four fields of a lshw-short entry.
        hwpathField = lines[i][0:deviceColumn].strip()
        deviceField = lines[i][deviceColumn:classColumn].strip()
        classField = lines[i][classColumn:descColumn].strip()
        descField = lines[i][descColumn:].strip()

        # Process the data in the fields.
        if classField == "disk":
            if deviceField == "/dev/sda":
                machDict["hdd"].append(descField.strip())
            if deviceField == "/dev/cdrom":
                machDict["cdDvd"].append(descField)

        elif classField == "display" and not displayFieldTaken:
            machDict["video"].append(descField)
            displayFieldTaken = True  # Skip further (redundant) entries about the video hardware.

        elif classField == "memory":
            sysMemColumn = descField.find("System Memory")
            if sysMemColumn != -1:
                machDict["ram.total"] = descField[0:sysMemColumn - 1]
            elif descField.find("DIMM") != -1:
                machDict["ram"].append(descField)

        elif classField == "multimedia":
            machDict["audio"].append(descField)

        elif classField == "network":
            descFieldLow = descField.lower()
            if descFieldLow.find("ethernet") != -1:
                machDict["network"].append(descField)
            elif descFieldLow.find("wifi") != -1 or descFieldLow.find("wireless") != -1:
                machDict["wifi"].append(descField)
            else:
                machDict["network"].append(descField)
                machDict["wifi"].append(descField)

        elif classField == "processor":
            machDict["cpu"].append(descField)

        elif classField == "system":
            machDict["model"].append(descField)


def printField(machDict, preface, key):
    print preface.ljust(FIRST_COL_WIDTH),
    if key not in machDict:
        print "<ERROR: machDict key not found>"
    elif len(machDict[key]) == 0:
        print
    elif len(machDict[key]) == 1:
        print machDict[key][0]
    else:
        print "[                                         ]"
        for entry in machDict[key]:
            print "".ljust(FIRST_COL_WIDTH + 5) + entry

# ***************************************************************************************
# *******************************  START OF MAIN ****************************************
# ***************************************************************************************

machine = Machine()
lshwshort = DataProviderLSHWShort()
lshwshort.populate(machine)
machine.printBuild()

exit(0)

# Prep the machine dictionary.
machDict = {}
machDict["os"] = []
machDict["model"] = []
machDict["cpu"] = []
machDict["ram"] = []
machDict["hdd"] = []
machDict["cdDvd"] = []
machDict["wifi"] = []
machDict["battery"] = []
machDict["webcam"] = []
machDict["bluetooth"] = []
machDict["updates"] = []
machDict["biosEntryKey"] = []
machDict["video"] = []
machDict["network"] = []
machDict["audio"] = []
machDict["usb"] = []
machDict["vgaPort"] = []
machDict["wifiOnOff"] = []
machDict["volumeControl"] = []
machDict["headphoneJack"] = []
machDict["microphone"] = []
machDict["mediaControls"] = []
machDict["whenLidClosed"] = []

# Get the lshw-short data and process it.
lshwshort_lines = open("../lapscanData/thinkpad_t61/lshw_short.out").readlines()
readLSHWShort(machDict, lshwshort_lines)

# Print the Build Sheet.
print "           ",
printField(machDict, "OS", "os")
print "           ",
printField(machDict, "Model", "model")
printField(machDict, "CPU", "cpu")
printField(machDict, "RAM", "ram")
printField(machDict, "HDD", "hdd")
printField(machDict, "CD/DVD", "cdDvd")
printField(machDict, "Wifi", "wifi")
printField(machDict, "Battery", "battery")
printField(machDict, "Webcam", "webcam")
printField(machDict, "Bluetooth", "bluetooth")
print
printField(machDict, "Updates", "updates")
printField(machDict, "BIOS entry key", "biosEntryKey")
printField(machDict, "Video", "video")
printField(machDict, "Network", "network")
printField(machDict, "Audio", "audio")
printField(machDict, "USB", "usb")
printField(machDict, "VGA port", "vgaPort")
printField(machDict, "Wifi on/off", "wifiOnOff")
printField(machDict, "Volume control", "volumeControl")
printField(machDict, "Headphone jack", "headphoneJack")
printField(machDict, "Microphone", "microphone")
printField(machDict, "Media controls", "mediaControls")
printField(machDict, "When lid closed", "whenLidClosed")

