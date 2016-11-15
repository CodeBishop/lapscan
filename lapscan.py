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

import re

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
        # Name the fields and subfields.
        self.subfieldNames = {
            "cpu": ['cpu make', 'cpu model', 'cpu ghz'],
            "ram": ['ram total', 'dimm1 size', 'dimm2 size', 'ddr', 'ram mhz'],
            "hdd": ['hdd gb', 'hdd make'],
            "cd/dvd": ['cd r/w', 'dvd r/w', 'optical make', 'optical model'],
            "wifi": ['wifi make', 'wifi model', 'wifi modes'],
            "battery ": ['batt max', 'batt orig', 'batt percent'],
            "webcam": ['webcam make', 'webcam model'],
            "bluetooth": ['bluetooth make', 'bluetooth model'],
            "bios entry key": ['bios key'],
            "video": ['video make', 'video model'],
            "network": ['ethernet make', 'ethernet model'],
            "audio": ['audio make', 'audio model'],
            "usb": ['usb left', 'usb right', 'usb front', 'usb back'],
            "vga port": ['vga ok', 'vga toggle'],
            "wifi on/off": ['wifi ok', 'wifi toggle'],
            "volume control": ['volume ok', 'volume controls'],
            "headphone jack": ['headphone jack ok'],
            "microphone": ['microphone ok', 'microphone description'],
            "media controls": ['media controls ok', 'media keys'],
            "when lid closed": ['lid closed description']
        }

        # Initialize the subfields and the lists of raw fields.
        self.rawFieldData = dict()
        self.subfieldData = dict()
        for fieldName in self.subfieldNames.keys():
            self.rawFieldData[fieldName] = []
            for subfieldName in self.subfieldNames[fieldName]:
                self.subfieldData[subfieldName] = Subfield()

    def checkAndLowerFieldName(self, callingMethod, fieldName):
        fieldName = fieldName.lower()
        if fieldName not in self.rawFieldData:
            print 'ERROR: Machine.' + callingMethod + ' says "' + fieldName + '" is not a recognized build sheet field.'
            exit(1)
        else:
            return fieldName

    def checkAndLowerSubfieldName(self, callingMethod, subfieldName):
        subfieldName = subfieldName.lower()
        if subfieldName not in self.subfieldDataData:
            print 'ERROR: Machine.' + callingMethod + ' says "' + subfieldName + \
                  '" is not a recognized subfield of any field on the build sheet.'
            exit(1)
        else:
            return subfieldName

    def addRawField(self, fieldName, line):
        fieldName = self.checkAndLowerFieldName("addRawField()", fieldName)
        self.rawFieldData[fieldName].append(line)

    def rawFields(self, fieldName):
        fieldName = self.checkAndLowerFieldName("rawFields()", fieldName)
        return self.rawFieldData[fieldName]

    # Return the value of a subfield or a placeholder string of "<subfield name>".
    def subfield(self, subfieldName):
        subfieldName = self.checkAndLowerSubfieldName(subfieldName)
        return self.subfieldData[subfieldName].value()

    def setSubfield(self, subfieldName, value, source):
        subfieldName = self.checkAndLowerSubfieldName(subfieldName)
        self.subfieldData[subfieldName].addData(value, source)

    # Construct a formatted field from known subfield data.
    def field(s, fieldName):
        fieldName = s.checkAndLowerFieldName("field()", fieldName)
        line = ""
        if fieldName == "cpu":
            line = s.subfield("cpu make") + " " + s.subfield("cpu model") + " @ " + s.subfield("cpu ghz") + " GHZ"
        return line

    def printBuild(self):
        output = list()
        output.append("CPU".ljust(FIRST_COL_WIDTH) + self.field("CPU"))

        for line in output:
            print line


class DataProviderLSHWShort:
    def __init__(self):
        self.name = "lshw-short"
        self.lines = open("../lapscanData/thinkpad_t61/lshw_short.out").readlines()

    # Fill the given machine with raw data and subfield data.
    def populate(self, machine):
        def setSubfield(subfieldName, subfieldVal):
            machine.setSubfield(subfieldName, subfieldVal, self.name)

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
            desc = self.lines[i][descColumn:].strip()

            # Helper variables for skipping redundant data.
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
                sysMemColumn = desc.find("System Memory")
                if sysMemColumn != -1:
                    pass
                elif desc.find("DIMM") != -1:
                    pass

            elif classField == "multimedia":
                pass

            elif classField == "network":
                descLow = desc.lower()
                if descLow.find("ethernet") != -1:
                    pass
                elif descLow.find("wifi") != -1 or descLow.find("wireless") != -1:
                    pass
                else:
                    pass

            elif classField == "processor":
                # EXAMPLE:  Intel(R) Core(TM)2 Duo CPU     T9300  @ 2.50GHz
                setSubfield("cpu make", rsub(r"Intel|AMD", desc))
                # substring = rsub(r"\s\S*\s*@", desc)
                # setSubfield("cpu model", rsub(r"\S+", substring))
                # setSubfield("cpu type", substring)
                substring = rsub(r"(?:Intel|AMD)[\(R\)]+\s(\w+)", desc)
                # setSubfield("cpu model", rsub(r"(?:Intel|AMD)(?:\(R\))?\s+(\w+)", desc))
                # setSubfield("cpu model", substring)
                setSubfield("cpu ghz", rsub(r"[0-9]+\.[0-9]+", desc))

            elif classField == "system":
                pass


# Regex Substring: A simple wrapper for using regexs to pull substrings (or return "" if not found).
def rsub(reg, string):
    substring = re.search(reg, string)
    if substring:
        return substring.group(0)
    else:
        return ""

# # Extract information from "lshw -short" output and add it to the machine dictionary.
# def readLSHWShort(machDict, lines):
#     # Determine the column widths from the column headers.
#     deviceColumn = lines[0].find("Device")
#     classColumn = lines[0].find("Class")
#     descColumn = lines[0].find("Description")
#
#     # Helper variables.
#     displayFieldTaken = False
#
#     # Process output to add data to the machine dictionary.
#     for i in range(2, len(lines)):
#         # Extract the four fields of a lshw-short entry.
#         hwpathField = lines[i][0:deviceColumn].strip()
#         deviceField = lines[i][deviceColumn:classColumn].strip()
#         classField = lines[i][classColumn:descColumn].strip()
#         descField = lines[i][descColumn:].strip()
#
#         # Process the data in the fields.
#         if classField == "disk":
#             if deviceField == "/dev/sda":
#                 machDict["hdd"].append(descField.strip())
#             if deviceField == "/dev/cdrom":
#                 machDict["cdDvd"].append(descField)
#
#         elif classField == "display" and not displayFieldTaken:
#             machDict["video"].append(descField)
#             displayFieldTaken = True  # Skip further (redundant) entries about the video hardware.
#
#         elif classField == "memory":
#             sysMemColumn = descField.find("System Memory")
#             if sysMemColumn != -1:
#                 machDict["ram.total"] = descField[0:sysMemColumn - 1]
#             elif descField.find("DIMM") != -1:
#                 machDict["ram"].append(descField)
#
#         elif classField == "multimedia":
#             machDict["audio"].append(descField)
#
#         elif classField == "network":
#             descFieldLow = descField.lower()
#             if descFieldLow.find("ethernet") != -1:
#                 machDict["network"].append(descField)
#             elif descFieldLow.find("wifi") != -1 or descFieldLow.find("wireless") != -1:
#                 machDict["wifi"].append(descField)
#             else:
#                 machDict["network"].append(descField)
#                 machDict["wifi"].append(descField)
#
#         elif classField == "processor":
#             machDict["cpu"].append(descField)
#
#         elif classField == "system":
#             machDict["model"].append(descField)
#
#
# def printField(machDict, preface, key):
#     print preface.ljust(FIRST_COL_WIDTH),
#     if key not in machDict:
#         print "<ERROR: machDict key not found>"
#     elif len(machDict[key]) == 0:
#         print
#     elif len(machDict[key]) == 1:
#         print machDict[key][0]
#     else:
#         print "[                                         ]"
#         for entry in machDict[key]:
#             print "".ljust(FIRST_COL_WIDTH + 5) + entry

# ***************************************************************************************
# *******************************  START OF MAIN ****************************************
# ***************************************************************************************

machine = Machine()
lshwshort = DataProviderLSHWShort()
lshwshort.populate(machine)
machine.printBuild()

# # Prep the machine dictionary.
# machDict = {}
# machDict["os"] = []
# machDict["model"] = []
# machDict["cpu"] = []
# machDict["ram"] = []
# machDict["hdd"] = []
# machDict["cdDvd"] = []
# machDict["wifi"] = []
# machDict["battery"] = []
# machDict["webcam"] = []
# machDict["bluetooth"] = []
# machDict["updates"] = []
# machDict["biosEntryKey"] = []
# machDict["video"] = []
# machDict["network"] = []
# machDict["audio"] = []
# machDict["usb"] = []
# machDict["vgaPort"] = []
# machDict["wifiOnOff"] = []
# machDict["volumeControl"] = []
# machDict["headphoneJack"] = []
# machDict["microphone"] = []
# machDict["mediaControls"] = []
# machDict["whenLidClosed"] = []
#
# # Get the lshw-short data and process it.
# lshwshort_lines = open("../lapscanData/thinkpad_t61/lshw_short.out").readlines()
# readLSHWShort(machDict, lshwshort_lines)
#
# # Print the Build Sheet.
# print "           ",
# printField(machDict, "OS", "os")
# print "           ",
# printField(machDict, "Model", "model")
# printField(machDict, "CPU", "cpu")
# printField(machDict, "RAM", "ram")
# printField(machDict, "HDD", "hdd")
# printField(machDict, "CD/DVD", "cdDvd")
# printField(machDict, "Wifi", "wifi")
# printField(machDict, "Battery", "battery")
# printField(machDict, "Webcam", "webcam")
# printField(machDict, "Bluetooth", "bluetooth")
# print
# printField(machDict, "Updates", "updates")
# printField(machDict, "BIOS entry key", "biosEntryKey")
# printField(machDict, "Video", "video")
# printField(machDict, "Network", "network")
# printField(machDict, "Audio", "audio")
# printField(machDict, "USB", "usb")
# printField(machDict, "VGA port", "vgaPort")
# printField(machDict, "Wifi on/off", "wifiOnOff")
# printField(machDict, "Volume control", "volumeControl")
# printField(machDict, "Headphone jack", "headphoneJack")
# printField(machDict, "Microphone", "microphone")
# printField(machDict, "Media controls", "mediaControls")
# printField(machDict, "When lid closed", "whenLidClosed")
#
