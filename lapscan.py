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
import subprocess

FIRST_COL_WIDTH = 16  # Character width of first column when printing a build sheet to the console..


class Subfield:
    def __init__(self, subfieldName):
        self.name = subfieldName
        self.data = []

    def addData(self, val, source):
        self.data.append((val, source))

    def value(self):
        if len(self.data) == 0:
            return "<" + self.name + ">"
        else:
            val, source = self.data[0]
            return val

    def isEmpty(self):
        return len(self.data) == 0


class Machine:
    def __init__(self):
        # Name the fields and subfields.
        self.subfieldNames = {
            "model": ['machine make', 'machine model'],
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
                self.subfieldData[subfieldName] = Subfield(subfieldName)

    def checkAndLowerFieldName(self, callingMethod, fieldName):
        fieldName = fieldName.lower()
        if fieldName not in self.rawFieldData:
            print 'ERROR: Machine.' + callingMethod + ' says "' + fieldName + '" is not a recognized build sheet field.'
            exit(1)
        else:
            return fieldName

    def checkAndLowerSubfieldName(self, callingMethod, subfieldName):
        subfieldName = subfieldName.lower()
        if subfieldName not in self.subfieldData:
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
        subfieldName = self.checkAndLowerSubfieldName("subfield()", subfieldName)
        return self.subfieldData[subfieldName].value()

    def setSubfield(self, subfieldName, value, source):
        subfieldName = self.checkAndLowerSubfieldName("setSubfield()", subfieldName)
        self.subfieldData[subfieldName].addData(value, source)

    # Construct a formatted field from known subfield data.
    def field(s, fieldName):
        fieldName = s.checkAndLowerFieldName("field()", fieldName)
        line = ""
        if fieldName == "cpu":
            line = s.subfield("cpu make") + " " + s.subfield("cpu model") + " @ " + s.subfield("cpu ghz") + " GHZ"
        return line

    def fieldIsIncomplete(self, fieldName):
        fieldName = self.checkAndLowerFieldName("fieldIsIncomplete()", fieldName)
        for subfieldName in self.subfieldNames[fieldName]:
            if self.subfieldData[subfieldName].isEmpty():
                return True
        return False

    def rawLinesIfIncomplete(self, fieldName):
        fieldName = self.checkAndLowerFieldName("rawLinesIfIncomplete()", fieldName)
        if self.fieldIsIncomplete(fieldName):
            rawLines = []
            for line in self.rawFieldData[fieldName]:
                rawLines.append("".ljust(FIRST_COL_WIDTH-9) + "raw data:   " + line)
            return rawLines
        else:
            return []

    def printBuild(self):
        output = list()
        buildSheetOrder = ["Model", "CPU", "RAM", "HDD", "CD/DVD", "Wifi", "Battery ", "Webcam", "Bluetooth",
                           "BIOS entry key", "Video", "Network", "Audio", "USB", "VGA port", "Wifi on/off",
                           "Volume control", "Headphone jack", "Microphone", "Media controls", "When lid closed"]
        for fieldName in buildSheetOrder:
            output.append(fieldName.ljust(FIRST_COL_WIDTH) + self.field(fieldName))
            output += self.rawLinesIfIncomplete(fieldName)

        for line in output:
            print line


class DataProviderLSHWShort:
    def __init__(self, fileName=None):
        self.name = "lshw-short"
        if fileName:
            self.lines = open(fileName).readlines()
        else:
            process = subprocess.Popen("lshw -short".split(), stdout=subprocess.PIPE)
            textOutput, _ = process.communicate()
            self.lines = textOutput.splitlines()

    # Fill the given machine with raw data and subfield data.
    def populate(self, machine):
        def setSubfield(subfieldName, subfieldVal):
            machine.setSubfield(subfieldName, subfieldVal, self.name)

        # Determine the column widths from the column headers.
        deviceColumn = self.lines[0].find("Device")
        classColumn = self.lines[0].find("Class")
        descColumn = self.lines[0].find("Description")

        # Helper variables for skipping redundant data.
        displayAlreadyKnown = False

        # Process output to add data to the machine dictionary.
        for i in range(2, len(self.lines)):
            # Extract the four fields of a lshw-short entry.
            hwpathField = self.lines[i][0:deviceColumn].strip()
            deviceField = self.lines[i][deviceColumn:classColumn].strip()
            classField = self.lines[i][classColumn:descColumn].strip()
            desc = self.lines[i][descColumn:].strip()

            # Process the data in the fields.
            if classField == "disk":
                if deviceField == "/dev/sda":
                    machine.addRawField("hdd", desc)
                if deviceField == "/dev/cdrom":
                    machine.addRawField("cd/dvd", desc)

            elif classField == "display" and not displayAlreadyKnown:
                machine.addRawField("Video", desc)
                displayAlreadyKnown = True  # Skip further (redundant) entries about the video hardware.

            elif classField == "memory":
                if desc.find("System Memory") != -1:
                    machine.addRawField("RAM", desc)
                elif desc.find("DIMM") != -1 and desc.find("GiB") != -1:
                    machine.addRawField("RAM", desc)

            elif classField == "multimedia":
                machine.addRawField("Audio", desc)

            elif classField == "network":
                descLow = desc.lower()
                if descLow.find("ethernet") != -1:
                    machine.addRawField("Network", desc)
                elif descLow.find("wifi") != -1 or descLow.find("wireless") != -1:
                    machine.addRawField("Wifi", desc)
                else:
                    machine.addRawField("Network", desc)
                    machine.addRawField("Wifi", desc)

            elif classField == "processor":
                machine.addRawField("cpu", desc)
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
                machine.addRawField("Model", desc)


# Regex Substring: A simple wrapper to extract the first substring a regex matches (or return "" if not found).
def rsub(reg, string):
    substring = re.search(reg, string)
    if substring:
        return substring.group(0)
    else:
        return ""

# ***************************************************************************************
# *******************************  START OF MAIN ****************************************
# ***************************************************************************************

machine = Machine()
# lshwshort = DataProviderLSHWShort("../lapscanData/asus_1018p/lshw_short.out")
lshwshort = DataProviderLSHWShort()
lshwshort.populate(machine)
machine.printBuild()

