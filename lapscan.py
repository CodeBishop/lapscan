#!/usr/bin/env python

# TO DO
#   Make the wifi section append something like "a/b/g/n" to show wifi available modes.
#   Write a camelCaseMaker() method that will search for known
#   Add functionality to run Cheese and other tests and query the user how they went.


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
import math

FIRST_COL_WIDTH = 19  # Character width of first column when printing a build sheet to the console..
COLOR_TO_USE = '\033[1m'
COLOR_TO_REVERT_TO = '\033[0m'
FIELD_NOT_INITIALIZED, FIELD_NO_DATA_FOUND, FIELD_HAS_DATA = range(3)

# Color printing functions. DEBUG: THESE CAN BE DELETED.
# def printred(prt): print("\033[91m {}\033[00m" .format(prt)),
# def printgreen(prt): print("\033[92m {}\033[00m" .format(prt)),
# def printyellow(prt): print("\033[93m {}\033[00m" .format(prt)),
# def printmagenta(prt): print("\033[94m {}\033[00m" .format(prt)),
# def printpurple(prt): print("\033[95m {}\033[00m" .format(prt)),
# def printcyan(prt): print("\033[96m {}\033[00m" .format(prt)),
# def printgrey(prt): print("\033[97m {}\033[00m" .format(prt)),
# def redtext(txt): return "\033[91m" + txt + "\033[0m"
# def greentext(txt): return "\033[92m" + txt + "\033[0m"
# def yellowtext(txt): return "\033[93m" + txt + "\033[0m"
# def magentatext(txt): return "\033[94m" + txt + "\033[0m"
# def purpletext(txt): return "\033[95m" + txt + "\033[0m"
# def cyantext(txt): return "\033[96m" + txt + "\033[0m"
# def greytext(txt): return "\033[97m" + txt + "\033[0m"


class Field:
    def __init__(self, subfieldName):
        self.name = subfieldName
        self.m_value = ""
        self.m_status = FIELD_NOT_INITIALIZED

    def setValue(self, val):
        self.m_value = val
        self.m_status = FIELD_HAS_DATA

    def value(self):
        return self.m_value

    def setStatus(self, status):
        self.m_status = status

    def status(self):
        return self.m_status


fieldNames = 'os version', 'os bit depth', 'machine make', 'machine model', 'cpu make', 'cpu model', 'cpu ghz', 'ram total', \
             'dimm0 size', 'dimm1 size', 'ddr', 'ram mhz', 'hdd gb', 'hdd make', 'hdd model', 'hdd connector', 'cd type', \
             'dvd type', 'optical make', 'dvdram', 'wifi make', 'wifi model', 'wifi modes', \
             'batt present', 'batt max', 'batt orig', 'batt percent', 'webcam make', \
             'bluetooth make', 'bluetooth model', 'bios key', 'video make', 'video model', \
             'ethernet make', 'ethernet model', 'audio make', 'audio model', 'usb left', 'usb right', \
             'usb front', 'usb back', 'vga ok', 'vga toggle ok', 'vga keys', 'wifi ok', 'wifi keys', \
             'volume ok', 'volume keys', 'headphone jack ok', 'microphone ok', 'microphone jacks', \
             'media controls ok', 'media keys', 'lid closed description'


def printBuildSheet(mach):
    sys.stdout.write(COLOR_TO_USE)

    osVersion = mach['os version'].value() + " " + mach['os bit depth'].value() + "-Bit"

    # Construct the strings that describe the machine in VCN Build Sheet format.
    modelDescription = mach['machine make'].value() + ' ' + mach['machine model'].value()

    cpuDescription = ''
    if mach['cpu make'].status() == FIELD_HAS_DATA:
        cpuDescription = mach['cpu make'].value() + ' ' + mach['cpu model'].value()
    else:
        cpuDescription += 'unknown cpu'

    if mach['cpu ghz'].status() == FIELD_HAS_DATA:
        cpuDescription += ' @ ' + mach['cpu ghz'].value() + ' Ghz'

    ramDescription = mach['ram total'].value() + 'Gb = ' + mach['dimm0 size'].value() + ' + ' \
        + mach['dimm1 size'].value() + "Gb " + mach['ddr'].value() + " @ " + mach['ram mhz'].value() + " Mhz"

    # DEBUG: This should be confirming SATA is the connection method.
    hddDescription = mach['hdd gb'].value() + 'Gb '
    if mach['hdd connector'].status() == FIELD_HAS_DATA:
        hddDescription += mach['hdd connector'].value() + ' '
    hddDescription += mach['hdd make'].value() + ' ' + mach['hdd model'].value()

    if mach['optical make'].status() == FIELD_NO_DATA_FOUND:
        opticalDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE
    else:
        opticalDescription = ''
        if mach['cd type'].status() == FIELD_HAS_DATA:
            opticalDescription += mach['cd type'].value() + ' '
        if mach['dvd type'].status() == FIELD_HAS_DATA:
            opticalDescription += mach['dvd type'].value() + ' '
        opticalDescription += mach['optical make'].value() + ' '
        if mach['dvdram'].status() == FIELD_HAS_DATA:
            opticalDescription += mach['dvdram'].value() + ' '

    if mach['wifi make'].status() == FIELD_HAS_DATA:
        wifiDescription = mach['wifi make'].value() + ' ' + mach['wifi model'].value() + '802.11 ' \
            + mach['wifi modes'].value()
    else:
        wifiDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    if mach['batt max'].status() == FIELD_HAS_DATA:
        batteryDescription = 'Capacity = ' + mach['batt max'].value() + '/' + mach['batt orig'].value() \
            + 'Wh = ' + mach['batt percent'].value() + '%'
    else:
        batteryDescription = 'not present'

    if mach['webcam make'].status() == FIELD_HAS_DATA:
        webcamDescription = mach['webcam make'].value()
    else:
        webcamDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    if mach['bluetooth make'].status() == FIELD_HAS_DATA:
        bluetoothDescription = mach['bluetooth make'].value() + ' ' + mach['bluetooth model'].value()
    else:
        bluetoothDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    biosEntryKeyDescription = mach['bios key'].value()

    if mach['video make'].status() == FIELD_HAS_DATA:
        videoDescription = mach['video make'].value() + ' ' + mach['video model'].value()
    else:
        videoDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    # DEBUG: This should confirm Gigabit.
    if mach['ethernet make'].status() == FIELD_HAS_DATA:
        ethernetDescription = mach['ethernet make'].value() + ' ' + mach['ethernet model'].value() + ' Gigabit'
    else:
        ethernetDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    if mach['audio make'].status() == FIELD_HAS_DATA:
        audioDescription = mach['audio make'].value() + ' ' + mach['audio model'].value()
    else:
        audioDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    usbDescription = '<#> LEFT, <#> RIGHT, <#> FRONT, <#> BACK'
    vgaPortDescription = '<vga ok> <vga toggle ok> <vga keys>'
    wifiOnOffDescription = '<wifi ok> <wifi keys>'
    volumeControlDescription = '<volume ok> <volume keys>'
    headphoneDescription = '<headphone jack ok>'
    microphoneDescription = '<microphone ok> <microphone types>'
    mediaControlsDescription = '<media controls ok> <media keys>'
    lidActionDescription = '<lid closed description>'

    # Print the VCN Build Sheet to the console.
    print "OS Version".ljust(FIRST_COL_WIDTH) + osVersion
    print "Model".ljust(FIRST_COL_WIDTH) + modelDescription
    print "CPU".ljust(FIRST_COL_WIDTH) + cpuDescription
    print "RAM".ljust(FIRST_COL_WIDTH) + ramDescription
    print "HDD".ljust(FIRST_COL_WIDTH) + hddDescription
    print "CD/DVD".ljust(FIRST_COL_WIDTH) + opticalDescription
    print "Wifi".ljust(FIRST_COL_WIDTH) + wifiDescription
    print "Battery".ljust(FIRST_COL_WIDTH) + batteryDescription
    print "Webcam".ljust(FIRST_COL_WIDTH) + webcamDescription
    print "Bluetooth".ljust(FIRST_COL_WIDTH) + bluetoothDescription
    print "BIOS entry key".ljust(FIRST_COL_WIDTH) + biosEntryKeyDescription
    print "Video".ljust(FIRST_COL_WIDTH) + videoDescription
    print "Network".ljust(FIRST_COL_WIDTH) + ethernetDescription
    print "Audio".ljust(FIRST_COL_WIDTH) + audioDescription
    sys.stdout.write(COLOR_TO_REVERT_TO)
    print "USB".ljust(FIRST_COL_WIDTH) + usbDescription
    print "VGA port".ljust(FIRST_COL_WIDTH) + vgaPortDescription
    print "Wifi on/off".ljust(FIRST_COL_WIDTH) + wifiOnOffDescription
    print "Volume control".ljust(FIRST_COL_WIDTH) + volumeControlDescription
    print "Headphone jack".ljust(FIRST_COL_WIDTH) + headphoneDescription
    print "Microphone".ljust(FIRST_COL_WIDTH) + microphoneDescription
    print "Media controls".ljust(FIRST_COL_WIDTH) + mediaControlsDescription
    print "When lid closed".ljust(FIRST_COL_WIDTH) + lidActionDescription
    print


# def processCommandLineArguments():
#     for item in sys.argv[1:]:
#         if item == '-nc':
#             COLOR_PRINTING = False


def readCPUFreq(mach):
    cpuFreq = float(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").readlines()[0])
    mach['cpu ghz'].setValue("%.1f" % (cpuFreq / 1000000.0))


def readGetconf(machine):
    bitDepth, _ = subprocess.Popen("getconf LONG_BIT".split(), stdout=subprocess.PIPE).communicate()
    machine['os bit depth'].setValue(re.search(r"(\d*)\n", bitDepth).groups()[0])


def readLSBRelease(machine):
    DEVNULL = open(os.devnull, 'wb')
    lsbreleaseData, _ = subprocess.Popen("lsb_release -a".split(), stdout=subprocess.PIPE, stderr=DEVNULL).communicate()
    machine['os version'].setValue(re.search(r"Description:[\t ]*(.*)\n", lsbreleaseData).groups()[0])


# Read and interpret lshw output.
def readLSHW(machine, testFile=None):
    if testFile:
        lshwData = open(testFile).read()
    else:
        lshwData, _ = subprocess.Popen("lshw".split(), stdout=subprocess.PIPE).communicate()  # DEBUG

    # Get machine make and model.
    machineMake = re.search(r"vendor: ([\w\-]+)", lshwData).groups()[0]
    machine['machine make'].setValue(machineMake)
    if machineMake == "LENOVO":
        machine['machine model'].setValue(re.search(r"version: ([\w ]+)", lshwData).groups()[0])
    else:
        machine['machine model'].setValue(re.search(r"product: ([\w ]+)", lshwData).groups()[0])
    if machineMake.lower() == 'asustek':
        machine['machine make'].setValue('Asus')

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

    # Get HDD description.
    hddSectionStart = lshwData[re.search(r"ATA Disk", lshwData).start():]
    lshwHddDdescription = re.search(r"product: ([\w ]*)", hddSectionStart).groups()[0]
    if lshwHddDdescription[:3] == 'WDC':
        machine['hdd make'].setValue("Western Digital")
        machine['hdd model'].setValue(lshwHddDdescription[4:])
    else:
        machine['hdd make'].setValue(lshwHddDdescription)
    machine['hdd connector'].setValue('SATA')
    machine['hdd gb'].setValue(re.search(r"size: \d+GiB \((\d*)", hddSectionStart).groups()[0])

    # Get optical drive description.
    cdromSearch = re.search(r"\*-cdrom", lshwData)
    if cdromSearch:
        opticalSectionStart = lshwData[cdromSearch.start():]
        if re.search(r"cd-rw", opticalSectionStart):
            machine['cd type'].setValue('CD R/W')
        if re.search(r"dvd-r", opticalSectionStart):
            machine['dvd type'].setValue('DVD R/W')
        if re.search(r"dvd-ram", opticalSectionStart):
            machine['dvdram'].setValue('DVDRAM')
        machine['optical make'].setValue(re.search(r"vendor: ([\w\- ]*)", opticalSectionStart).groups()[0])
    else:
        machine['optical make'].setStatus(FIELD_NO_DATA_FOUND)

    # Get wifi hardware description.
    wifiSearch = re.search(r"Wireless interface", lshwData)
    if wifiSearch:
        wifiSectionStart = lshwData[wifiSearch.start():]
        wifiMake = re.search(r"product:\s*(.*)\s*\n", wifiSectionStart).groups()[0]
        machine['wifi make'].setValue(wifiMake)

    # Find video hardware description.
    videoSearch = re.search(r"3D controller", lshwData)
    if not videoSearch:
        videoSearch = re.search(r"VGA compatible controller", lshwData)
    videoSection = lshwData[videoSearch.start():]
    # Pull out the vendor and product strings and append them to each other.
    videoMake = re.search(r"vendor: (.*)\n", videoSection).groups()[0]
    videoModel = re.search(r"product: (.*)\n", videoSection).groups()[0]
    # Strip out junk-words: corporation, chipset, graphics, controller, processor
    for junkWord in ['corporation', 'chipset', 'graphics', 'controller', 'processor']:
        videoMake = re.sub('(?i) ' + junkWord, '', videoMake)
        videoModel = re.sub('(?i) ' + junkWord, '', videoModel)
    machine['video make'].setValue(videoMake)
    machine['video model'].setValue(videoModel)


def readLSUSB(machine, testFile=None):
    if testFile:
        lsusbData = open(testFile).read()
    else:
        lsusbData, _ = subprocess.Popen("lsusb", stdout=subprocess.PIPE).communicate()

    # Grab the description from any lsusb line with "ebcam" in it
    webcamSearchResult = re.search(r"Bus.*[0-9a-fA-F]{4}:[0-9a-fA-F]{4} (.*ebcam.*)\n", lsusbData)

    # If "ebcam" wasn't found then try for "hicony" (ie, the company Chicony).
    if not webcamSearchResult.groups():
        webcamSearchResult = re.search(r"Bus.*[0-9a-fA-F]{4}:[0-9a-fA-F]{4} (.*hicony.*)\n", lsusbData)

    # If a match was found then use it.
    if webcamSearchResult.groups():
        webcamMake = webcamSearchResult.groups()[0]
        for junkWord in ['co.', 'electronics', 'ltd', 'cmos']:
            webcamMake = re.sub('(?i) ' + junkWord, '', webcamMake)
        webcamMake = re.sub(',', '', webcamMake)  # Strip out commas.
        machine['webcam make'].setValue(webcamMake)


def readUPower(machine):
    upowerData, _ = subprocess.Popen("upower --dump".split(), stdout=subprocess.PIPE).communicate()
    if not re.search("power supply.*no", upowerData):
        machine['batt max'].setValue(re.search(r"energy-full:\s*(\d+)\.", upowerData).groups()[0])
        machine['batt orig'].setValue(re.search(r"energy-full-design:\s*(\d+)\.", upowerData).groups()[0])
        # The capacity value given by upower won't match match the energy-full / energy-full-design. Calculate manually.
        percentage = float(machine['batt max'].value()) / float(machine['batt orig'].value())
        percentage = int(math.ceil(percentage * 100.0))
        # Upower's numbers sometimes show values > 100% and FreeGeek limits these to 100% in writing.
        if percentage > 100:
            percentage = 100
        machine['batt percent'].setValue(str(percentage))


# # ***************************************************************************************
# # *******************************  START OF MAIN ****************************************
# # ***************************************************************************************

# DEBUG: currently there are not command-line arguments.
# processCommandLineArguments()

# Initialize machine description with blank fields.
machine = dict()
for fieldName in fieldNames:
    machine[fieldName] = Field(fieldName)

readLSHW(machine, "testdata/lshwthinkpadr400.test")
# readLSHW(machine)
readLSBRelease(machine)
readGetconf(machine)
readUPower(machine)
readCPUFreq(machine)
readLSUSB(machine)
printBuildSheet(machine)


#
#
# # DEBUG: OTHER POSSIBLE DATA PROVIDERS: dmidecode, /dev, /sys, "hdparm -I /dev/sd?" (tells you HDD info, like SATA vs IDE).
#