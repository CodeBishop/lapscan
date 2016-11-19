#!/usr/bin/env python

# TO DO
#   Add the lshw Data Provider and start migrating to getting your data from it instead of lshw-short.


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

FIRST_COL_WIDTH = 19  # Character width of first column when printing a build sheet to the console..

# Color printing functions.
def printred(prt): print("\033[91m {}\033[00m" .format(prt)),
def printgreen(prt): print("\033[92m {}\033[00m" .format(prt)),
def printyellow(prt): print("\033[93m {}\033[00m" .format(prt)),
def printmagenta(prt): print("\033[94m {}\033[00m" .format(prt)),
def printpurple(prt): print("\033[95m {}\033[00m" .format(prt)),
def printcyan(prt): print("\033[96m {}\033[00m" .format(prt)),
def printgrey(prt): print("\033[97m {}\033[00m" .format(prt)),
def redtext(txt): return "\033[91m" + txt + "\033[0m"
def greentext(txt): return "\033[92m" + txt + "\033[0m"
def yellowtext(txt): return "\033[93m" + txt + "\033[0m"
def magentatext(txt): return "\033[94m" + txt + "\033[0m"
def purpletext(txt): return "\033[95m" + txt + "\033[0m"
def cyantext(txt): return "\033[96m" + txt + "\033[0m"
def greytext(txt): return "\033[97m" + txt + "\033[0m"


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
        # The regex describing subfield markers.
        self.SUBFIELD_REGEX = r"<([\w\s]+)>"

        # An array to list the fields in order of appearance and link their dictionary keys to their capitalized
        # appearance on the build sheet.
        self.buildSheetAppearance = [("model", "Model"), ("cpu", "CPU"), ("ram", "RAM"), ("hdd", "HDD"),
                                ("cd/dvd", "CD/DVD"), ("wifi", "Wifi"), ("battery", "Battery"), ("webcam", "Webcam"),
                                ("bluetooth", "Bluetooth"), ("bios entry key", "BIOS entry key"), ("video", "Video"),
                                ("network", "Network"), ("audio", "Audio"), ("usb", "USB"), ("vga port", "VGA port"),
                                ("wifi on/off", "Wifi on/off"), ("volume control", "Volume control"),
                                ("headphone jack", "Headphone jack"), ("microphone", "Microphone"),
                                ("media controls", "Media controls"), ("when lid closed", "When lid closed")]

        # List the subfields and link them to their associated field.
        self.subfieldNames = {
            "model": ['machine make', 'machine model'],
            "cpu": ['cpu make', 'cpu model', 'cpu ghz'],
            "ram": ['ram total', 'dimm1 size', 'dimm2 size', 'ddr', 'ram mhz'],
            "hdd": ['hdd gb', 'hdd make'],
            "cd/dvd": ['cd r/w', 'dvd r/w', 'optical make', 'optical model'],
            "wifi": ['wifi make', 'wifi model', 'wifi modes'],
            "battery": ['batt max', 'batt orig', 'batt percent'],
            "webcam": ['webcam manufacturer'],
            "bluetooth": ['bluetooth make', 'bluetooth model'],
            "bios entry key": ['bios key'],
            "video": ['video make', 'video model'],
            "network": ['ethernet make', 'ethernet model'],
            "audio": ['audio make', 'audio model'],
            "usb": ['usb left', 'usb right', 'usb front', 'usb back'],
            "vga port": ['vga ok', 'vga toggle ok', 'vga keys'],
            "wifi on/off": ['wifi ok', 'wifi keys'],
            "volume control": ['volume ok', 'volume keys'],
            "headphone jack": ['headphone jack ok'],
            "microphone": ['microphone ok', 'microphone jacks'],
            "media controls": ['media controls ok', 'media keys'],
            "when lid closed": ['lid closed description']
        }

        self.fieldFormat = {
            "model": "<machine make> <machine model>",
            "cpu": "<cpu make> <cpu model> @ <cpu ghz> GHZ",
            "ram": "<ram total>Gb = <dimm1 size> + <dimm2 size>Gb  DDR<ddr>  @  <ram mhz> MHZ",
            "hdd": "<hdd gb>Gb SATA <hdd make>",
            "cd/dvd": "<cd r/w> <dvd r/w> <optical make> DVDRAM <optical model>",
            "wifi": "<wifi make> <wifi model> 802.11 <wifi modes>",
            "battery": "Capacity= <batt max> / <batt orig> Wh = <batt percent>%",
            "webcam": "<webcam manufacturer>",
            "bluetooth": "<bluetooth make> <bluetooth model>",
            "bios entry key": "<bios key>",
            "video": "<video make> <video model>",
            "network": "<ethernet make> <ethernet model> Gigabit",
            "audio": "<audio make> <audio model>",
            "usb": "<usb left> LEFT, <usb right> RIGHT, <usb front> FRONT, <usb back> BACK",
            "vga port": "<vga ok> <vga toggle ok> <vga keys>",
            "wifi on/off": "<wifi ok> <wifi keys>",
            "volume control": "<volume ok> <volume keys>",
            "headphone jack": "<headphone jack ok>",
            "microphone": "<microphone ok> <microphone jacks>",
            "media controls": "<media controls ok> <media keys>",
            "when lid closed": "<lid closed description>"
        }

        # Initialize the subfields and the lists of raw fields.
        self.rawFieldData = dict()
        self.subfieldData = dict()
        for fieldName in self.subfieldNames.keys():
            self.rawFieldData[fieldName.lower()] = []
            for subfieldName in self.subfieldNames[fieldName]:
                self.subfieldData[subfieldName] = Subfield(subfieldName)

    def addRawField(self, fieldName, line, source):
        # fieldName = self.checkAndLowerFieldName("addRawField()", fieldName)
        self.rawFieldData[fieldName].append((line, source))

    def rawFields(self, fieldName):
        return self.rawFieldData[fieldName]

    # Return the value of a subfield or a placeholder string of "<subfield name>".
    def subfield(self, subfieldName):
        return self.subfieldData[subfieldName].value()

    def setSubfield(self, subfieldName, value, source):
        self.subfieldData[subfieldName].addData(value, source)

    # Construct a formatted field from known subfield data.
    def field(self, fieldName):
        if fieldName in self.fieldFormat:
            line = self.fieldFormat[fieldName]
            subfieldNamesFound = re.findall(self.SUBFIELD_REGEX, self.fieldFormat[fieldName])
            for subfieldName in subfieldNamesFound:
                line = re.sub("<" + subfieldName + ">", self.subfield(subfieldName), line)
        else:
            line = "?"

        return line

    def fieldIsEmpty(self, fieldName):
        for subfieldName in self.subfieldNames[fieldName]:
            if not self.subfieldData[subfieldName].isEmpty():
                return False
        return True

    def fieldIsIncomplete(self, fieldName):
        for subfieldName in self.subfieldNames[fieldName]:
            if self.subfieldData[subfieldName].isEmpty():
                return True
        return False

    def rawLinesIfIncomplete(self, fieldName):
        if self.fieldIsIncomplete(fieldName):
            rawLines = []
            for line, source in self.rawFieldData[fieldName]:
                rawLines.append(source.rjust(FIRST_COL_WIDTH-2) + ": " + line)
            return rawLines
        else:
            return []

    def printBuild(self):
        output = list()
        for (fieldKey, fieldAppearance) in self.buildSheetAppearance:
            templateColor = '\033[0m'  # Grey
            foundColor = '\033[1m' + "\033[92m"  # Green and bold.
            if self.fieldIsEmpty(fieldKey):
                output.append(fieldAppearance.ljust(FIRST_COL_WIDTH) + self.field(fieldKey))
            else:
                line = foundColor + fieldAppearance.ljust(FIRST_COL_WIDTH) + templateColor + self.fieldFormat[fieldKey]
                if fieldKey in self.fieldFormat:
                    regexMatchesFound = re.findall(self.SUBFIELD_REGEX, self.fieldFormat[fieldKey])
                    for regexMatch in regexMatchesFound:
                        if not self.subfieldData[regexMatch].isEmpty():
                            fieldText = foundColor + self.subfield(regexMatch) + templateColor
                            line = re.sub("<" + regexMatch + ">", fieldText, line)
                output.append(line)

            output += self.rawLinesIfIncomplete(fieldKey)

        for line in output:
            print line


class DataProviderLSHW:
    def __init__(self, fileName=None):
        self.name = "lshw"
        if fileName:
            self.data = open(fileName).read()
        else:
            process = subprocess.Popen("lshw".split(), stdout=subprocess.PIPE)
            self.data, _ = process.communicate()

    def populate(self, machine):

        pass


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
            # Extract the four fields of an lshw-short entry.
            hwpathField = self.lines[i][0:deviceColumn].strip()
            deviceField = self.lines[i][deviceColumn:classColumn].strip()
            classField = self.lines[i][classColumn:descColumn].strip()
            desc = self.lines[i][descColumn:].strip()

            # Process the data in the fields.
            if classField == "disk":
                if deviceField == "/dev/sda":
                    machine.addRawField("hdd", desc, self.name)
                if deviceField == "/dev/cdrom":
                    machine.addRawField("cd/dvd", desc, self.name)

            elif classField == "display" and not displayAlreadyKnown:
                machine.addRawField("video", desc, self.name)
                displayAlreadyKnown = True  # Skip further (redundant) entries about the video hardware.

            elif classField == "memory":
                if desc.find("System Memory") != -1:
                    setSubfield("ram total", re.search("\d+", desc).group(0))
                    print "ljkkkkkkkkkkk" + machine.subfield("ram total")
                    machine.addRawField("ram", desc, self.name)
                elif desc.find("DIMM") != -1 and desc.find("GiB") != -1:
                    machine.addRawField("ram", desc, self.name)

            elif classField == "multimedia":
                machine.addRawField("audio", desc, self.name)

            elif classField == "network":
                descLow = desc.lower()
                if descLow.find("ethernet") != -1:
                    machine.addRawField("network", desc, self.name)
                elif descLow.find("wifi") != -1 or descLow.find("wireless") != -1:
                    machine.addRawField("wifi", desc, self.name)
                else:
                    machine.addRawField("network", desc, self.name)
                    machine.addRawField("wifi", desc, self.name)

            elif classField == "processor":
                machine.addRawField("cpu", desc, self.name)
                # EXAMPLE:  Intel(R) Core(TM)2 Duo CPU     T9300  @ 2.50GHz
                setSubfield("cpu make", rsub(r"Intel|AMD", desc))

            elif classField == "system":
                machine.addRawField("model", desc, self.name)


class DataProviderCPUFreq:
    def __init__(self, fileName=None):
        self.name = "cpufreq"
        self.output = float(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").readlines()[0])

    def populate(self, machine):
        machine.setSubfield("cpu ghz", "%.1f" % (self.output / 1000000.0), self.name)


class DataProviderLSUSB:
    def __init__(self, fileName=None):
        self.name = "lsusb"
        if fileName:
            self.lines = open(fileName).readlines()
        else:
            process = subprocess.Popen("lsusb", stdout=subprocess.PIPE)
            textOutput, _ = process.communicate()
            self.lines = textOutput.splitlines()

    def populate(self, machine):
        # Scan the lsusb output for identifiable devices.
        for line in self.lines:
            if rsub("Chicony|ebcam", line) != "":
                m = re.search(r"ID ....:.... ", line)
                machine.addRawField("webcam", line[m.end():], self.name)
                machine.setSubfield("webcam manufacturer", line[m.end():], self.name)


class DataProviderUPower:
    def __init__(self, fileName=None):
        self.name = "upower"
        if fileName:
            self.lines = open(fileName).readlines()
        else:
            process = subprocess.Popen("upower --dump".split(), stdout=subprocess.PIPE)
            textOutput, _ = process.communicate()
            self.lines = textOutput.splitlines()

    def populate(self, machine):
        for line in self.lines:
            if rsub("energy-full:", line) != "":
                m = re.search(r"\d+\.\d+", line)
                machine.setSubfield("batt max", str(int(float(m.group(0)))), self.name)
                machine.addRawField("battery", line, self.name)
            elif rsub("energy-full-design:", line) != "":
                m = re.search(r"\d+\.\d+", line)
                machine.setSubfield("batt orig", str(int(float(m.group(0)))), self.name)
                machine.addRawField("battery", line, self.name)
            elif rsub("capacity:", line) != "":
                m = re.search(r"\d+\.\d+", line)
                machine.setSubfield("batt percent", str(int(float(m.group(0)))), self.name)
                machine.addRawField("battery", line, self.name)

# OTHER POSSIBLE DATA PROVIDERS: dmidecode, /dev, /sys, lsusb


# Regex Substring: A simple wrapper to extract the first substring a regex matches (or return "" if not found).
def rsub(reg, string):
    m = re.search(reg, string)
    if m:
        return m.group(0)
    else:
        return ""

# ***************************************************************************************
# *******************************  START OF MAIN ****************************************
# ***************************************************************************************

machine = Machine()
DataProviderLSHWShort("testdata/lshw_short.test").populate(machine)  # DEBUG
# DataProviderLSHWShort().populate(machine)
DataProviderLSHW("testdata/lshw.test").populate(machine)
# DataProviderLSHW().populate(machine)
DataProviderCPUFreq().populate(machine)
DataProviderLSUSB().populate(machine)
DataProviderUPower().populate(machine)
machine.printBuild()
