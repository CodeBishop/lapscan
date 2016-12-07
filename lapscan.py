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
import sys
import os

FIRST_COL_WIDTH = 19  # Character width of first column when printing a build sheet to the console..
COLOR_PRINTING = True
FIELD_NOT_INITIALIZED, FIELD_NO_DATA_FOUND, FIELD_HAS_DATA = range(3)

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


class Field:
    def __init__(self, subfieldName):
        self.name = subfieldName
        self.m_value = ""
        self.m_status = FIELD_NOT_INITIALIZED

    def setValue(self, val):
        self.m_value = val
        self.m_status = FIELD_HAS_DATA

    def value(self):
        if self.status() == FIELD_NO_DATA_FOUND:
            return "not present"
        else:
            return self.m_value

    def setStatus(self, status):
        self.m_status = status

    def status(self):
        return self.m_status


fieldNames = 'machine make', 'machine model', 'cpu make', 'cpu model', 'cpu ghz', 'ram total', \
             'dimm0 size', 'dimm1 size', 'ddr', 'ram mhz', 'hdd gb', 'hdd make', 'cd r/w', \
             'dvd r/w', 'optical make', 'dvdram', 'wifi make', 'wifi model', 'wifi modes', \
             'batt present', 'batt max', 'batt orig', 'batt percent', 'webcam manufacturer', \
             'bluetooth make', 'bluetooth model', 'bios key', 'video make', 'video model', \
             'ethernet make', 'ethernet model', 'audio make', 'audio model', 'usb left', 'usb right', \
             'usb front', 'usb back', 'vga ok', 'vga toggle ok', 'vga keys', 'wifi ok', 'wifi keys', \
             'volume ok', 'volume keys', 'headphone jack ok', 'microphone ok', 'microphone jacks', \
             'media controls ok', 'media keys', 'lid closed description'


def printBuildSheet(machine):
    if COLOR_PRINTING:
        sys.stdout.write('\033[1m')

    print "Model".ljust(FIRST_COL_WIDTH) + machine['machine make'].value() + ' ' + machine['machine model'].value()
    print "CPU".ljust(FIRST_COL_WIDTH) + machine['cpu make'].value() + ' '+ machine['cpu model'].value()
    print "RAM".ljust(FIRST_COL_WIDTH) + machine['ram total'].value() + 'Gb = ' + \
          machine['dimm0 size'].value() + ' + ' + machine['dimm1 size'].value() + "Gb " + \
          machine['ddr'].value() + " @ " + machine['ram mhz'].value() + " Mhz"
    #             "hdd": "<hdd gb>Gb SATA <hdd make>",
    #             "cd/dvd": "<cd r/w> <dvd r/w> <optical make> <dvdram>",
    #             "wifi": "<wifi make> <wifi model> 802.11 <wifi modes>",
    #             "battery": "Capacity= <batt max>/<batt orig>Wh = <batt percent>%",
    #             "webcam": "<webcam manufacturer>",
    #             "bluetooth": "<bluetooth make> <bluetooth model>",
    #             "bios entry key": "<bios key>",
    #             "video": "<video make> <video model>",
    #             "network": "<ethernet make> <ethernet model> Gigabit",
    #             "audio": "<audio make> <audio model>",
    #             "usb": "<usb left> LEFT, <usb right> RIGHT, <usb front> FRONT, <usb back> BACK",
    #             "vga port": "<vga ok> <vga toggle ok> <vga keys>",
    #             "wifi on/off": "<wifi ok> <wifi keys>",
    #             "volume control": "<volume ok> <volume keys>",
    #             "headphone jack": "<headphone jack ok>",
    #             "microphone": "<microphone ok> <microphone jacks>",
    #             "media controls": "<media controls ok> <media keys>",
    #             "when lid closed": "<lid closed description>"

    if COLOR_PRINTING:
        sys.stdout.write('\033[0m')
        sys.stdout.flush()


# Read and interpret lshw output.
def readLSHW(machine):
    lshwData = open("testdata/lshw.test").read()
    # lshwData = subprocess.Popen("lshw".split(), stdout=subprocess.PIPE).communicate()

    # Get machine make and model.
    machineMake = re.search(r"vendor: ([\w\-]+)", lshwData).groups()[0]
    machine['machine make'].setValue(machineMake)
    if machineMake == "LENOVO":
        machine['machine model'].setValue(re.search(r"version: ([\w ]+)", lshwData).groups()[0])
    else:
        machine['machine model'].setValue(re.search(r"product: ([\w ]+)", lshwData).groups()[0])

    # Find start of LSHW section on CPU description.
    cpuSectionStart = lshwData[re.search(r"\*-cpu", lshwData).start():]

    # Get CPU manufacturer.
    cpuDesc = re.search(r"vendor: (.*)\n", cpuSectionStart).groups()[0]
    machine['cpu make'].setValue(re.search(r"(Intel|AMD)", cpuDesc).groups()[0])

    # Get CPU model description.
    model = re.search(r"product: (.*)\n", cpuSectionStart).groups()[0]

    # Extract CPU model from CPU model description by deleting undesired substrings.
    model = re.sub(r"\(tm\)|\(r\)|Intel|AMD|CPU|Processor", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\s*@.*", "", model, flags=re.IGNORECASE)  # Remove everything after an @
    model = re.sub(r"\s\s+", " ", model, flags=re.IGNORECASE)  # Replace multiple spaces with just one.
    model = re.search(r"\s*(\w.*)", model).groups()[0]  # Keep what's left, minus any front spacing.
    machine['cpu model'].setValue(model)

    # Get RAM description
    ramSectionStart = lshwData[re.search(r"\*-memory", lshwData).start():]
    machine['ram total'].setValue(re.search(r"size: (\d*)", ramSectionStart).groups()[0])
    machine['ddr'].setValue(re.search(r"(DDR\d)", ramSectionStart).groups()[0])
    dimm0Section = lshwData[re.search(r"\*-bank:0", lshwData).start():]
    machine['dimm0 size'].setValue(re.search(r"size: (\d*)", dimm0Section).groups()[0])
    machine['ram mhz'].setValue(re.search(r"clock: (\d*)", dimm0Section).groups()[0])
    dimm1Section = lshwData[re.search(r"\*-bank:1", lshwData).start():]
    machine['dimm1 size'].setValue(re.search(r"size: (\d*)", dimm1Section).groups()[0])

        # # Get HDD description.
        # hddSectionStart = lshwData[re.search(r"ATA Disk", lshwData).start():]
        # machine['hdd make", re.search(r"product: ([\w ]*)", hddSectionStart).groups()[0])
        # machine['hdd gb", re.search(r"size: \d+GiB \((\d*)", hddSectionStart).groups()[0])
        #
        # # Get optical drive description.
        # cdromSearch = re.search(r"\*-cdrom", lshwData)
        # if cdromSearch:
        #     opticalSectionStart = lshwData[cdromSearch.start():]
        #     if re.search(r"cd-rw", opticalSectionStart):
        #         machine['cd r/w", "CD R/W")
        #     if re.search(r"dvd-r", opticalSectionStart):
        #         machine['dvd r/w", "DVD R/W")
        #     if re.search(r"dvd-ram", opticalSectionStart):
        #         machine['dvdram", "DVDRAM")
        #     machine['optical make", re.search(r"vendor: ([\w\- ]*)", opticalSectionStart).groups()[0])

        # wifiSectionStart = re.search(r"Wireless interface")

# # ***************************************************************************************
# # *******************************  START OF MAIN ****************************************
# # ***************************************************************************************
# Initialize machine description with blank fields.
machine = dict()
for fieldName in fieldNames:
    machine[fieldName] = Field(fieldName)

readLSHW(machine)
printBuildSheet(machine)

# class Machine:
#     def __init__(self):
#         # The regex describing subfield markers.
#         self.SUBFIELD_REGEX = r"<([\w\s/]+)>"
#
#         # An array to list the fields in order of appearance and link their dictionary keys to their capitalized
#         # appearance on the build sheet.
#         self.buildSheetAppearance = [("model", "Model"), ("cpu", "CPU"), ("ram", "RAM"), ("hdd", "HDD"),
#                                      ("cd/dvd", "CD/DVD"), ("wifi", "Wifi"), ("battery", "Battery"), ("webcam", "Webcam"),
#                                      ("bluetooth", "Bluetooth"), ("bios entry key", "BIOS entry key"), ("video", "Video"),
#                                      ("network", "Network"), ("audio", "Audio"), ("usb", "USB"), ("vga port", "VGA port"),
#                                      ("wifi on/off", "Wifi on/off"), ("volume control", "Volume control"),
#                                      ("headphone jack", "Headphone jack"), ("microphone", "Microphone"),
#                                      ("media controls", "Media controls"), ("when lid closed", "When lid closed")]
#
#         # List the subfields and link them to their associated field.
#         self.subfieldNames = {
#             "model": ['machine make', 'machine model'],
#             "cpu": ['cpu make', 'cpu model', 'cpu ghz'],
#             "ram": ['ram total', 'dimm0 size', 'dimm1 size', 'ddr', 'ram mhz'],
#             "hdd": ['hdd gb', 'hdd make'],
#             "cd/dvd": ['cd r/w', 'dvd r/w', 'optical make', 'dvdram'],
#             "wifi": ['wifi make', 'wifi model', 'wifi modes'],
#             "battery": ['batt present', 'batt max', 'batt orig', 'batt percent'],
#             "webcam": ['webcam manufacturer'],
#             "bluetooth": ['bluetooth make', 'bluetooth model'],
#             "bios entry key": ['bios key'],
#             "video": ['video make', 'video model'],
#             "network": ['ethernet make', 'ethernet model'],
#             "audio": ['audio make', 'audio model'],
#             "usb": ['usb left', 'usb right', 'usb front', 'usb back'],
#             "vga port": ['vga ok', 'vga toggle ok', 'vga keys'],
#             "wifi on/off": ['wifi ok', 'wifi keys'],
#             "volume control": ['volume ok', 'volume keys'],
#             "headphone jack": ['headphone jack ok'],
#             "microphone": ['microphone ok', 'microphone jacks'],
#             "media controls": ['media controls ok', 'media keys'],
#             "when lid closed": ['lid closed description']
#         }
#
#         self.fieldFormat = {
#             "model": "<machine make> <machine model>",
#             "cpu": "<cpu make> <cpu model> @ <cpu ghz> GHZ",
#             "ram": "<ram total>Gb = <dimm0 size> + <dimm1 size>Gb <ddr> @ <ram mhz> MHZ",
#             "hdd": "<hdd gb>Gb SATA <hdd make>",
#             "cd/dvd": "<cd r/w> <dvd r/w> <optical make> <dvdram>",
#             "wifi": "<wifi make> <wifi model> 802.11 <wifi modes>",
#             "battery": "Capacity= <batt max>/<batt orig>Wh = <batt percent>%",
#             "webcam": "<webcam manufacturer>",
#             "bluetooth": "<bluetooth make> <bluetooth model>",
#             "bios entry key": "<bios key>",
#             "video": "<video make> <video model>",
#             "network": "<ethernet make> <ethernet model> Gigabit",
#             "audio": "<audio make> <audio model>",
#             "usb": "<usb left> LEFT, <usb right> RIGHT, <usb front> FRONT, <usb back> BACK",
#             "vga port": "<vga ok> <vga toggle ok> <vga keys>",
#             "wifi on/off": "<wifi ok> <wifi keys>",
#             "volume control": "<volume ok> <volume keys>",
#             "headphone jack": "<headphone jack ok>",
#             "microphone": "<microphone ok> <microphone jacks>",
#             "media controls": "<media controls ok> <media keys>",
#             "when lid closed": "<lid closed description>"
#         }
#
#         # Initialize the subfields and the lists of raw fields.
#         self.rawFieldData = dict()
#         self.subfieldData = dict()
#         for fieldName in self.subfieldNames.keys():
#             self.rawFieldData[fieldName.lower()] = []
#             for subfieldName in self.subfieldNames[fieldName]:
#                 self.subfieldData[subfieldName] = Subfield(subfieldName)
#
#     def addRawField(self, fieldName, line, source):
#         # fieldName = self.checkAndLowerFieldName("addRawField()", fieldName)
#         self.rawFieldData[fieldName].append((line, source))
#
#     def rawFields(self, fieldName):
#         return self.rawFieldData[fieldName]
#
#     # Return the value of a subfield or a placeholder string of "<subfield name>".
#     def subfield(self, subfieldName):
#         return self.subfieldData[subfieldName].value()
#
#     def setSubfield(self, subfieldName, value, source):
#         self.subfieldData[subfieldName].addData(value, source)
#
#     # Construct a formatted field from known subfield data.
#     def field(self, fieldName):
#         if fieldName in self.fieldFormat:
#             line = self.fieldFormat[fieldName]
#             subfieldNamesFound = re.findall(self.SUBFIELD_REGEX, self.fieldFormat[fieldName])
#             for subfieldName in subfieldNamesFound:
#                 line = re.sub("<" + subfieldName + ">", self.subfield(subfieldName), line)
#         else:
#             line = "?"
#
#         return line
#
#     def fieldIsEmpty(self, fieldName):
#         for subfieldName in self.subfieldNames[fieldName]:
#             if not self.subfieldData[subfieldName].isEmpty():
#                 return False
#         return True
#
#     def fieldIsIncomplete(self, fieldName):
#         for subfieldName in self.subfieldNames[fieldName]:
#             if self.subfieldData[subfieldName].isEmpty():
#                 return True
#         return False
#
#     def rawLinesIfIncomplete(self, fieldName):
#         if self.fieldIsIncomplete(fieldName):
#             rawLines = []
#             for line, source in self.rawFieldData[fieldName]:
#                 rawLines.append(source.rjust(FIRST_COL_WIDTH-2) + ": " + line)
#             return rawLines
#         else:
#             return []
#
#     def printBuild(self):
#         if COLOR_PRINTING:
#             templateColor = '\033[0m'  # Grey
#             highlightColor = '\033[1m' + "\033[92m"  # Green and bold.
#         else:
#             templateColor, highlightColor = '', ''
#
#         # For each line on the build sheet.
#         for (fieldKey, fieldAppearance) in self.buildSheetAppearance:
#             # Check for special cases of field presentation.
#             if fieldKey == "battery" and not self.subfieldData["batt present"].isEmpty():
#                 print fieldAppearance.ljust(FIRST_COL_WIDTH) + highlightColor +\
#                       self.subfield("batt present") + templateColor
#
#             # If the field is empty then print the fieldFormat as is.
#             elif self.fieldIsEmpty(fieldKey):
#                 print fieldAppearance.ljust(FIRST_COL_WIDTH) + self.field(fieldKey)
#
#             # If the field is not empty.
#             else:
#                 # Print the field name highlighted.
#                 line = highlightColor + fieldAppearance.ljust(FIRST_COL_WIDTH) + templateColor + self.fieldFormat[fieldKey]
#
#                 # Find all subfields tags listed in field format.
#                 regexMatchesFound = re.findall(self.SUBFIELD_REGEX, self.fieldFormat[fieldKey])
#
#                 # For each subfield mentioned.
#                 for regexMatch in regexMatchesFound:
#                     # If that subfield has data then substitute it for the subfield tag.
#                     if not self.subfieldData[regexMatch].isEmpty():
#                         fieldText = highlightColor + self.subfield(regexMatch) + templateColor
#                         line = re.sub("<" + regexMatch + ">", fieldText, line)
#                 print line
#
#             if self.rawLinesIfIncomplete(fieldKey):
#                 print self.rawLinesIfIncomplete(fieldKey)
#
#
# class DataProviderLSHW:
#     def __init__(self, fileName=None):
#         self.name = "lshw"
#         if fileName:
#             self.data = open(fileName).read()
#         else:
#             process = subprocess.Popen("lshw".split(), stdout=subprocess.PIPE)
#             self.data, _ = process.communicate()
#
#     def populate(self, machine):
#         def setSubfield(subfieldName, subfieldVal):
#             machine.setSubfield(subfieldName, subfieldVal, self.name)
#
#         # Get machine make and model by finding first mention of 'product'.
#         machineMake = re.search(r"vendor: ([\w\-]+)", self.data).groups()[0]
#         setSubfield("machine make", machineMake)
#         if machineMake == "LENOVO":
#             setSubfield("machine model", re.search(r"version: ([\w ]+)", self.data).groups()[0])
#         else:
#             setSubfield("machine model", re.search(r"product: ([\w ]+)", self.data).groups()[0])
#
#         # Find start of LSHW section on CPU description.
#         cpuSectionStart = self.data[re.search(r"\*-cpu", self.data).start():]
#
#         # Get CPU manufacturer.
#         cpuDesc = re.search(r"vendor: (.*)\n", cpuSectionStart).groups()[0]
#         setSubfield("cpu make", re.search(r"(Intel|AMD)", cpuDesc).groups()[0])
#
#         # Get CPU model description.
#         model = re.search(r"product: (.*)\n", cpuSectionStart).groups()[0]
#         machine.addRawField("cpu", model, self.name)
#
#         # Extract CPU model from CPU model description by deleting undesired substrings.
#         model = re.sub(r"\(tm\)|\(r\)|Intel|AMD|CPU|Processor", "", model, flags=re.IGNORECASE)
#         model = re.sub(r"\s*@.*", "", model, flags=re.IGNORECASE)  # Remove everything after an @
#         model = re.sub(r"\s\s+", " ", model, flags=re.IGNORECASE)  # Replace multiple spaces with just one.
#         model = re.search(r"\s*(\w.*)", model).groups()[0]  # Keep what's left, minus any front spacing.
#         setSubfield("cpu model", model)
#
#         # Get RAM description
#         ramSectionStart = self.data[re.search(r"\*-memory", self.data).start():]
#         setSubfield("ram total", re.search(r"size: (\d*)", ramSectionStart).groups()[0])
#         setSubfield("ddr", re.search(r"(DDR\d)", ramSectionStart).groups()[0])
#         dimm0Section = self.data[re.search(r"\*-bank:0", self.data).start():]
#         setSubfield("dimm0 size", re.search(r"size: (\d*)", dimm0Section).groups()[0])
#         setSubfield("ram mhz", re.search(r"clock: (\d*)", dimm0Section).groups()[0])
#         dimm1Section = self.data[re.search(r"\*-bank:1", self.data).start():]
#         setSubfield("dimm1 size", re.search(r"size: (\d*)", dimm1Section).groups()[0])
#
#         # Get HDD description.
#         hddSectionStart = self.data[re.search(r"ATA Disk", self.data).start():]
#         setSubfield("hdd make", re.search(r"product: ([\w ]*)", hddSectionStart).groups()[0])
#         setSubfield("hdd gb", re.search(r"size: \d+GiB \((\d*)", hddSectionStart).groups()[0])
#
#         # Get optical drive description.
#         cdromSearch = re.search(r"\*-cdrom", self.data)
#         if cdromSearch:
#             opticalSectionStart = self.data[cdromSearch.start():]
#             if re.search(r"cd-rw", opticalSectionStart):
#                 setSubfield("cd r/w", "CD R/W")
#             if re.search(r"dvd-r", opticalSectionStart):
#                 setSubfield("dvd r/w", "DVD R/W")
#             if re.search(r"dvd-ram", opticalSectionStart):
#                 setSubfield("dvdram", "DVDRAM")
#             setSubfield("optical make", re.search(r"vendor: ([\w\- ]*)", opticalSectionStart).groups()[0])
#
#         # wifiSectionStart = re.search(r"Wireless interface")
#
#
# class DataProviderLSHWShort:
#     def __init__(self, fileName=None):
#         self.name = "lshw-short"
#         if fileName:
#             self.lines = open(fileName).readlines()
#         else:
#             process = subprocess.Popen("lshw -short".split(), stdout=subprocess.PIPE)
#             textOutput, _ = process.communicate()
#             self.lines = textOutput.splitlines()
#
#     # Fill the given machine with raw data and subfield data.
#     def populate(self, machine):
#         def setSubfield(subfieldName, subfieldVal):
#             machine.setSubfield(subfieldName, subfieldVal, self.name)
#
#         # Determine the column widths from the column headers.
#         deviceColumn = self.lines[0].find("Device")
#         classColumn = self.lines[0].find("Class")
#         descColumn = self.lines[0].find("Description")
#
#         # Helper variables for skipping redundant data.
#         displayAlreadyKnown = False
#
#         # Process output to add data to the machine dictionary.
#         for i in range(2, len(self.lines)):
#             # Extract the four fields of an lshw-short entry.
#             hwpathField = self.lines[i][0:deviceColumn].strip()
#             deviceField = self.lines[i][deviceColumn:classColumn].strip()
#             classField = self.lines[i][classColumn:descColumn].strip()
#             desc = self.lines[i][descColumn:].strip()
#
#             # Process the data in the fields.
#             if classField == "disk":
#                 if deviceField == "/dev/sda":
#                     machine.addRawField("hdd", desc, self.name)
#                 if deviceField == "/dev/cdrom":
#                     machine.addRawField("cd/dvd", desc, self.name)
#
#             elif classField == "display" and not displayAlreadyKnown:
#                 machine.addRawField("video", desc, self.name)
#                 displayAlreadyKnown = True  # Skip further (redundant) entries about the video hardware.
#
#             elif classField == "multimedia":
#                 machine.addRawField("audio", desc, self.name)
#
#             elif classField == "network":
#                 descLow = desc.lower()
#                 if descLow.find("ethernet") != -1:
#                     machine.addRawField("network", desc, self.name)
#                 elif descLow.find("wifi") != -1 or descLow.find("wireless") != -1:
#                     machine.addRawField("wifi", desc, self.name)
#                 else:
#                     machine.addRawField("network", desc, self.name)
#                     machine.addRawField("wifi", desc, self.name)
#
#             elif classField == "system":
#                 machine.addRawField("model", desc, self.name)
#
#
# class DataProviderCPUFreq:
#     def __init__(self, fileName=None):
#         self.name = "cpufreq"
#         self.output = float(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").readlines()[0])
#
#     def populate(self, machine):
#         machine.setSubfield("cpu ghz", "%.1f" % (self.output / 1000000.0), self.name)
#
#
# class DataProviderLSUSB:
#     def __init__(self, fileName=None):
#         self.name = "lsusb"
#         if fileName:
#             self.data = open(fileName).read()
#         else:
#             process = subprocess.Popen("lsusb", stdout=subprocess.PIPE)
#             self.data, _ = process.communicate()
#
#     def populate(self, machine):
#         # Scan the lsusb output for identifiable devices.
#         if re.search("Chicony", self.data):
#             machine.setSubfield("webcam manufacturer", "Chicony", self.name)
#         else:
#             webcamLine = regGetWholeLine("ebcam", self.data)
#             if webcamLine != "":
#                 webcamInfo = rmatch(re.search("ID ....:.... (.*)$", webcamLine))
#                 machine.setSubfield("webcam manufacturer", webcamInfo, self.name)
#             else:
#                 machine.setSubfield("webcam manufacturer", "(not present)", self.name)
#
#
# class DataProviderUPower:
#     def __init__(self):
#         self.name = "upower"
#         process = subprocess.Popen("upower --dump".split(), stdout=subprocess.PIPE)
#         self.data, _ = process.communicate()
#
#     def populate(self, machine):
#         if re.search("power supply.*no", self.data):
#             machine.setSubfield("batt present", "(no battery found)", self.data)
#         else:
#             battMax = rmatch(re.search(r"energy-full:\s*(\d+)\.", self.data))
#             machine.setSubfield("batt max", battMax, self.name)
#             battOrig = rmatch(re.search(r"energy-full-design:\s*(\d+)\.", self.data))
#             machine.setSubfield("batt orig", battOrig, self.name)
#             battPercent = rmatch(re.search(r"capacity:\s*(\d+)\.", self.data))
#             machine.setSubfield("batt percent", battPercent, self.name)
#
# # DEBUG: OTHER POSSIBLE DATA PROVIDERS: dmidecode, /dev, /sys
#
#
# def processCommandLineArguments():
#     global COLOR_PRINTING
#     for item in sys.argv[1:]:
#         if item == '-nc':
#             COLOR_PRINTING = False
#
#
# # Return the first capture group from regex Match object if a match was found.
# def rmatch(match):
#     if match:
#         return match.groups()[0]
#     else:
#         return ""  # Return empty string if no match was found.
#
#
# # Return the entire line where the first regex match was found if it was found.
# def regGetWholeLine(reg, textData):
#     lines = textData.splitlines()
#     for line in lines:
#         if re.search(reg, line):
#             return line
#
#     return ""  # Return empty string if regex never matched anything.
#
#
# def rsub(reg, string):
#     m = re.search(reg, string)
#     if m:
#         return m.groups()[0]
#     else:
#         return ""
#
# # ***************************************************************************************
# # *******************************  START OF MAIN ****************************************
# # ***************************************************************************************
# if os.geteuid() != 0:
#     print "This program requires root privilege to run correctly. Use sudo.\n"
#     exit(1)
#
# processCommandLineArguments()
# machine = Machine()
# # DataProviderLSHWShort("testdata/lshw_short.test").populate(machine)  # DEBUG
# # DataProviderLSHWShort().populate(machine)
# # DataProviderLSHW("testdata/lshwzenbook.test").populate(machine)
# # DataProviderLSHW("testdata/lshwthinkpadr400.test").populate(machine)
# # DataProviderLSHW("../lapscanData/hp_g60/lshw.out").populate(machine)
# DataProviderLSHW().populate(machine)
# DataProviderCPUFreq().populate(machine)
# DataProviderLSUSB().populate(machine)
# # DataProviderLSUSB("testdata/lsusb_chicony.out").populate(machine)
# DataProviderUPower().populate(machine)
# machine.printBuild()
