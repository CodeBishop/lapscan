#!/usr/bin/env python

# TO DO
#   Make the wifi section append something like "a/b/g/n" to show wifi available modes.
#   Run this on a MacBook and MacBook Pro with Ubuntu to get raw data and test functionality.
#   Test the program with blank input files to simulate all the different ways that re.search() might fail.
#   Add functionality to store the raw console outputs as strings, ask the user at the end if everything was
#   correct. If the user says no then ask them for an explanation and email it along with the raw data to myself.
#   Add a function for extracting lshw sections so that I don't risk having re.search pull unfound fields from
#   later sections thereby producing garbage data for fields.
#   Make the program able to gracefully handle machines that have only one RAM slot and machines that four.
#   Come up with a solution to the problem of fields that go past the column width of their ODS entry.
#   Determine if there's a way to get the Bluetooth data. If not then eliminate the field.
#   Make the program prompt for the admin password rather than complain that it's not in sudo mode.
#   Rewrite the LSHW reading code to pull data off in sections so that it cannot accidentally read the vendor
#       for a product from the later section of a different product.
#   Change the program so that it reads all it's data into the raw file before processing it. That way if the
#       processing crashes then you have the RAW file to use for recreating the problem and don't need the machine.
#   Make sure the program handles it gracefully if:
#       The template file is not found.
#       The raw file already exists and needs to be overwritten (not appended).
#       The ods file already exists and needs to be overwritten (not appended).
#   Check that you are differentiating IDE from SATA hard drives. Try "hdparm -I /dev/sd?" (replace ? with letter).
#   Make sure it can identify when a hard drive is an SSD. That info needs to be highlighted, particularly when a
#       machine has two hard drives like the Zenbooks do. It needs to distinguish an SSD from an SD card or USB drive.
#   Suppress all warning messages produced by not being sudo.
#   See if lsusb -v can give you more info about a webcam such as its resolution.
#   Consider using lscpu and putting info about number of cores and threads into the CPU description.
#   Add a feature to ask the user if they would like to see the generated spreadsheet, if so then open it for them.
#   Consider adding a stress test option.
#   See if you can disable the screensaver and password automatically (for the store's convenience).
#   Add the code to identify SSD drivers when present and rotational speed when not. Test it on the Optiplex data
#       which seems to be missing the rpm data.
#   Check that the hdd code is correctly describing a dual-hard drive machine.
#   Clean out all the cruft marked DEBUG in this code.
#   Reconsider having hdparm check for /dev/hda. Does this ever show up?
#   Add the output from "ls /dev" to you raw data so you can potentially track which devices show up in there.
#   Start thinking about how to make the program upload the raw text files to a repository where I can collect them.
#


# Evaluations to be Made
#   Run the stress test.
#   Update the OS thereby confirming that the wifi works.
#   Disable wifi, confirming that the wifi on/off button/switch works and preparing to test ethernet.
#   Plug in ethernet (wifi still off) and install Synaptic and LXDE, confirming that ethernet works.
#   Play optical discs to confirm the drive works, test the media controls, volume controls and headphone jack.
#   Run Cheese to confirm webcam works.
#   Test the ethernet jack.
#   Test USB ports (don't miss the eSATA ones).
#   Test the video ports: DVI, VGA, HDMI, Display port.
#   Test the microphone.
#   Close the lid to see what happens.
#   Disable the screen saver and password (for the store's convenience).
#   Power down and check that the RAM has green stickers.
#   Clean the laptop, put FreeGeek logo sticker and ID sticker on it. Record it in the build book.


# Color codes for printing in color to the terminal.
#   default color \033[00m
#   red \033[91m   green \033[92m   yellow \033[93m   magenta \033[94m   purple \033[95m   cyan \033[96m   gray \033[97m


import re
import subprocess
import sys
import os
import inspect
import math
import zipfile

FIRST_COL_WIDTH = 19  # Character width of first column when printing a build sheet to the console.
COLOR_TO_USE = '\033[1m'
COLOR_TO_REVERT_TO = '\033[0m'
FIELD_NOT_INITIALIZED, FIELD_NO_DATA_FOUND, FIELD_HAS_DATA = range(3)
DEFAULT_SYSTEM_ID = "unidentified_system"
MISSING_FIELD = '_'
RECORD_CAPTURE_FAILURE, IGNORE_CAPTURE_FAILURE = 1, 2

debugMode = False
skipLSHW = False

# Fetch the null device for routing error messages to so they don't clutter the console output.
DEVNULL = open(os.devnull, 'w')


class Field:
    def __init__(self, subfieldName):
        self.name = subfieldName
        if subfieldName == "system id":
            self.m_value = DEFAULT_SYSTEM_ID
        else:
            self.m_value = ""
        self.m_status = FIELD_NOT_INITIALIZED

    def setValue(self, val):
        assert type(val) == str, "Field.setValue() given non-string for field \"" + self.name + "\""
        self.m_value = sanitizeString(val)
        self.m_status = FIELD_HAS_DATA

    def setRawValue(self, val):
        assert type(val) == str, "Field.setRawValue() given non-string for field \"" + self.name + "\""
        self.m_value = val
        self.m_status = FIELD_HAS_DATA

    def value(self):
        return self.m_value

    def setStatus(self, status):
        self.m_status = status

    def status(self):
        return self.m_status


# Words that should be stripped out of hardware fields before displaying them.
junkWords = 'corporation', 'electronics', 'ltd', 'chipset', 'graphics', 'controller', 'processor', '\(tm\)',\
            '\(r\)', 'cmos', 'co\.', 'cpu', 'inc.', 'network', 'connection', 'computer'

# Words that should be swapped out with tidier words (sometimes just better capitalization). Keys are case-insensitive.
correctableWords = {"lenovo": "Lenovo", "asustek": "Asus", "toshiba": "Toshiba", "wdc": "Western Digital",
                    "genuineintel": "Intel", "sony": "Sony"}

# Define a partial list of the fields available (further ones may get appended elsewhere in the code).
fieldNames = ['os version', 'os bit depth', 'system make', 'system model', 'system version', 'system serial',
              'system id', 'cpu make', 'cpu model', 'cpu ghz', 'ram mb total', 'ram type', 'ram mhz', 'ram desc',
              'hdd1 rpm', 'hdd1 mb', 'hdd1 model', 'hdd1 connector',
              'hdd2 rpm', 'hdd2 mb', 'hdd2 model', 'hdd2 connector', 'hdd desc',
# EXAMPLE:    'SSD',      '20000'    'Sandisk'     'SATA'
              'cd type', 'dvd type', 'optical make', 'dvdram', 'wifi make',
              'wifi model', 'wifi modes', 'batt present', 'batt max', 'batt orig', 'batt percent', 'webcam make',
              'bluetooth make', 'bluetooth model', 'video make', 'video model', 'ethernet make', 'ethernet model',
              'audio make', 'audio model']

rawDataSectionNames = [
    "getconf",
    "cpuinfo_max_freq",
    "dmidecode_memory",
    "dmidecode_processor",
    "dmidecode_system_make",
    "dmidecode_system_model",
    "dmidecode_system_serial",
    "dmidecode_system_version",
    "lsb_release",
    "lshw",
    "lsusb",
    "hdparm_sda",
    "hdparm_sdb",
    "hdparm_sdc",
    "upower",
]

captureFailures = list()


# Use a regular expression to capture part of a string or return MISSING_FIELD if unable.
def capture(pattern, text, failureAction=RECORD_CAPTURE_FAILURE):
    result = re.search(pattern, text)
    if result and result.group(1):
        return result.group(1)
    else:
        if failureAction == RECORD_CAPTURE_FAILURE:
            caller = inspect.stack()[1][3]
            captureFailures.append((caller, pattern, text))
        return MISSING_FIELD


def dumpCaptureFailures():
    for (caller, pattern, text) in captureFailures:
        # Eliminate excess whitespace and newlines from descriptions of searched text.
        text = re.sub(r"\s{2,}|\n", " ", text)
        # Concatenate excessively long searched text strings.
        if len(text) > 100:
            text = text[:100] + " ..."
        print "capture() failed to match: r\"" + pattern + "\""
        print "   in string: " + text
        print "   when called by: " + caller + "()" + "\n"


# Interpret the CPU frequency if the raw data is present.
def interpretCPUFreq(rawDict, mach):
    if "cpuinfo_max_freq" in rawDict:
        try:
            cpuFreq = float(rawDict["cpuinfo_max_freq"])
            mach['cpu ghz'].setValue("%.1f" % (cpuFreq / 1000000.0))
        except ValueError:
            mach['cpu ghz'].setValue(MISSING_FIELD)


# Interpret the RAM information from dmidecode type 17 output.
def interpretDmidecodeMemory(rawDict, mach):
    if rawDict["dmidecode_memory"] == "":
        return

    # Build array of entries, one per RAM slot.
    ramSlotDescs = re.findall(r"(Handle [\s\S]*?)(?:(?:\n\n)|(?:$))", rawDict["dmidecode_memory"])

    # Build array of RAM module descriptions (discard empty slots).
    ramDescs = list()
    for slotDesc in ramSlotDescs:
        if not re.search(r"Size: No Module Installed", slotDesc):
            ramDescs.append(slotDesc)

    # Take the memory type and speed from the first slot (since all slots should be identical anyways).
    mach["ram type"].setValue(capture(r"Type: (\w+)", ramDescs[0]))
    mach["ram mhz"].setValue(capture(r"Speed: (\d+) MHz", ramDescs[0]))

    # Compile a list of RAM sizes in megabytes.
    ramSizes = list()
    for ramDesc in ramDescs:
        size = capture(r"(?i)size:\s*(\d+)\s*mb", ramDesc, IGNORE_CAPTURE_FAILURE)
        # If any RAM slot has a module but not a discernible size then just give up.
        if size == MISSING_FIELD:
            mach["ram desc"].setRawValue("(Unable to determine RAM layout)")
            return
        # If any RAM has a module < 1 gb in size then give up (the layout work isn't worth it).
        if int(size) < 1024:
            mach["ram desc"].setRawValue("(Describing RAM modules less than 1GB isn't handled)")
            return
        else:
            ramSizes.append(int(size))

    # Tally and record the ram sizes while checking for a common size.
    totalRam = 0
    NO_COMMON_SIZE = -1
    commonSize = ramSizes[0]
    for i in range(len(ramSizes)):
        totalRam += ramSizes[i]

        # Create fields for each ram module to record the module's size.
        ramSizeFieldName = "ram" + str(i) + " mb"
        mach[ramSizeFieldName] = Field(ramSizeFieldName)
        mach[ramSizeFieldName].setValue(str(ramSizes[i]))

        if ramSizes[i] != commonSize:
            commonSize = NO_COMMON_SIZE

    # Start building the RAM description field.
    ramDesc = str("%.0f" % (totalRam / 1024.0)) + " Gb = "

    # If the RAM is not all the same size then describe it by summation.
    if commonSize == NO_COMMON_SIZE:
        ramDesc += str("%.0f" % (ramSizes[0] / 1024.0))
        for i in range(1, len(ramSizes)):
            ramDesc += " + " + str("%.0f" % (ramSizes[i] / 1024.0))
        ramDesc += " Gb"

    # If all the RAM is the same size then describe it as a multiple.
    else:
        ramDesc += str(len(ramSizes)) + " x " + str("%.0f" % (commonSize / 1024.0)) + " Gb"

    mach["ram desc"].setRawValue(ramDesc)


# Interpret the processor information from dmidecode output.
def interpretDmidecodeProcessor(rawDict, mach):
    if "dmidecode_processor" not in rawDict:
        print "Missing raw data for dmidecode_processor"
        return

    mach['cpu make'].setValue(capture(r"Manufacturer:[\s\t]*(.*)\n", rawDict['dmidecode_processor']))
    model = capture(r"Version:[\s\t]*(.*?)(?:@|\n)", rawDict['dmidecode_processor'])
    mach["cpu model"].setValue(re.sub(r"(?i)intel|amd", "", model))


# Interpret the identifying information of the system using the dmidecode output.
def interpretDmidecodeSystem(rawDict, mach):
    assert 'dmidecode_system_make' in rawDict and \
           'dmidecode_system_model' in rawDict and \
           'dmidecode_system_serial' in rawDict, \
        "dmidecode data is missing. A unique system ID cannot be formed without the system make, model and serial."

    # Get system make, model and serial number.
    systemMake = sanitizeString(rawDict['dmidecode_system_make'])
    systemModel = sanitizeString(rawDict['dmidecode_system_model'])
    systemSerial = stripExcessWhitespace(rawDict['dmidecode_system_serial'])

    # Correct for Lenovo putting their system model under 'version'.
    if systemMake.lower() == "lenovo":
        systemModel = sanitizeString(rawDict['dmidecode_system_version'])

    # Correct for the ugly name of Asus.
    if systemMake.lower() == 'asustek':
        systemMake = 'Asus'

    # Construct a system identifier from the make, model and serial number.
    systemID = (systemMake + '_' + systemModel + '__' + systemSerial).replace(' ', '_')

    # Store the values (unsanitized because they were already sanitized above).
    mach['system make'].setRawValue(systemMake)
    mach['system model'].setRawValue(systemModel)
    mach['system serial'].setRawValue(systemSerial)
    mach['system id'].setRawValue(systemID)


# Interpret the getconf data specifying whether this is a 32-bit or 64-bit OS.
def interpretGetconf(rawDict, mach):
    mach['os bit depth'].setValue(capture(r"(\d*)\n", rawDict['getconf']))


# Interpret the hard drive info given by hdparm.
def interpretHdparm(rawDict, mach):
    driveNumber = 1
    # Look for an IDE drive and one or two SATA drives.
    for devName in ['hdparm_sda', 'hdparm_sdb', 'hdparm_sdc']:
        if rawDict[devName] != "":
            # If a found drive is a fixed drive (and not a removable USB drive).
            if re.search(r"\n[\s\t]*frozen", rawDict[devName]):
                name = "hdd" + str(driveNumber)
                # Get the size of the hard drive.
                mach[name + " mb"].setValue(capture(r"1000\*1000:[\s\t]*(\d+)", rawDict[devName]))
                # Get the model of the hard drive.
                model = capture(r"Model Number:[\s\t]*(.+)\n", rawDict[devName])
                model = re.sub(r"(?i)\W+(\d+\s*GB)", "", model)  # Remove redundant capacity info.
                mach[name + " model"].setValue(model)
            # Prepare to look for another drive.
            driveNumber += 1

    # Construct the hard drive description field.
    hddDesc = ""
    for driveNumber in [1, 2]:
        name = "hdd" + str(driveNumber)
        # Check if hdd exists by checking for a connector value (since that entry is guaranteed to be present).
        if mach[name + " connector"].value() != "":
            # If there's a second drive then put a plus in the description.
            if driveNumber == 2:
                hddDesc += " + "
            # Pull together various fields of hard drive description.
            size = str(int(mach[name + " mb"].value()) / 1000)
            model = mach[name + " model"].value()
            hddDesc += size + "GB " + model
    mach["hdd desc"].setValue(hddDesc)


# Interpret the lsb_release output to determine OS version.
def interpretLSBRelease(rawDict, mach):
    mach['os version'].setValue(capture(r"Description:[\s\t]*(.*)\n", rawDict['lsb_release']))


# Interpret the lshw output if the raw data is present.
def interpretLSHW(rawDict, mach):
    if "lshw" in rawDict:
        lshwData = rawDict["lshw"]
        # Get optical drive description.
        cdromSearch = re.search(r"\*-cdrom", lshwData)
        if cdromSearch:
            opticalSectionStart = lshwData[cdromSearch.start():]
            if re.search(r"cd-rw", opticalSectionStart):
                mach['cd type'].setValue('CD R/W')
            if re.search(r"dvd-r", opticalSectionStart):
                mach['dvd type'].setValue('DVD R/W')
            if re.search(r"dvd-ram", opticalSectionStart):
                mach['dvdram'].setValue('DVDRAM')
            mach['optical make'].setValue(capture(r"vendor: ([\w\- ]*)", opticalSectionStart))
        else:
            mach['optical make'].setStatus(FIELD_NO_DATA_FOUND)

        # Get wifi hardware description.
        wifiSearch = re.search(r"Wireless interface", lshwData)
        if wifiSearch:
            wifiSectionStart = lshwData[wifiSearch.start():]
            mach['wifi make'].setValue(capture(r"product:\s*(.*)\s*\n", wifiSectionStart))

        # Get video hardware description (3D hardware if found, integrated hardware if not).
        videoSearch = re.search(r"3D controller", lshwData)
        if not videoSearch:
            videoSearch = re.search(r"VGA compatible controller", lshwData)
        if videoSearch:
            videoSection = lshwData[videoSearch.start():]
            # Get the video make and model.
            mach['video make'].setValue(capture(r"vendor: (.*)\n", videoSection))
            mach['video model'].setValue(capture(r"product: (.*)\n", videoSection))

        # Get Ethernet hardware description.
        ethernetSearch = re.search(r"Ethernet interface", lshwData)
        if ethernetSearch:
            ethernetSection = lshwData[ethernetSearch.start():]
            # Get the ethernet make and model.
            mach['ethernet make'].setValue(capture(r"vendor: (.*)\n", ethernetSection))
            mach['ethernet model'].setValue(capture(r"product: (.*)\n", ethernetSection))

        # Get Audio hardware description.
        audioSearch = re.search(r"\*-multimedia", lshwData)
        if audioSearch:
            audioSection = lshwData[audioSearch.start():]
            # Get the audio make and model.
            mach['audio make'].setValue(capture(r"vendor: (.*)\n", audioSection))
            mach['audio model'].setValue(capture(r"product: (.*)\n", audioSection))


# Read and interpret lsusb output.
def interpretLSUSB(rawDict, mach):
    # Grab the description from any lsusb line with "webcam" in it
    webcamMake = capture(r"(?i)Bus.*[0-9a-f]{4}:[0-9a-f]{4} (webcam.*)\n", rawDict['lsusb'], IGNORE_CAPTURE_FAILURE)

    # If "webcam" wasn't found then try for "Chicony".
    if webcamMake == MISSING_FIELD:
        webcamMake = capture(r"(?i)Bus.*[0-9a-f]{4}:[0-9a-f]{4} (chicony.*)\n", rawDict['lsusb'], IGNORE_CAPTURE_FAILURE)

    # If any match was found then use it.
    if not webcamMake == MISSING_FIELD:
        webcamMake = re.sub(',', '', webcamMake)  # Strip out commas.
        mach['webcam make'].setValue(webcamMake)


# Interpret "upower --dump" output.
def interpretUPower(rawDict, mach):
    mach['batt max'].setValue(capture(r"energy-full:\s*(\d+)\.", rawDict['upower']))
    mach['batt orig'].setValue(capture(r"energy-full-design:\s*(\d+)\.", rawDict['upower']))
    # The capacity value given by upower won't match match the energy-full / energy-full-design. Calculate manually.
    try:
        percentage = float(mach['batt max'].value()) / float(mach['batt orig'].value())
        percentage = int(math.ceil(percentage * 100.0))
        # Upower's numbers sometimes show values > 100% and FreeGeek limits these to 100% in writing.
        if percentage > 100:
            percentage = 100
        mach['batt percent'].setValue(str(percentage))
    except ValueError:
        mach['batt percent'].setValue(MISSING_FIELD)


# Print a machine's info to the terminal
def printBuildSheet(mach):
    sys.stdout.write(COLOR_TO_USE)

    osVersion = mach['os version'].value() + " " + mach['os bit depth'].value() + "-Bit"

    # Construct the strings that describe the machine in VCN Build Sheet format.
    modelDescription = mach['system make'].value() + ' ' + mach['system model'].value()

    cpuDescription = ''
    if mach['cpu make'].status() == FIELD_HAS_DATA:
        cpuDescription = mach['cpu make'].value() + ' ' + mach['cpu model'].value()
    else:
        cpuDescription += 'unknown cpu'

    if mach['cpu ghz'].status() == FIELD_HAS_DATA:
        cpuDescription += ' @ ' + mach['cpu ghz'].value() + ' Ghz'

    ramDescription = mach['ram desc'].value() + ' ' + mach['ram type'].value() + " @ " + mach['ram mhz'].value() + " Mhz"

    hddDescription = mach["hdd desc"].value()

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

    if mach['video make'].status() == FIELD_HAS_DATA:
        videoDescription = mach['video make'].value() + ' ' + mach['video model'].value()
    else:
        videoDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    # DEBUG: This should confirm Gigabit.
    if mach['ethernet make'].status() == FIELD_HAS_DATA:
        ethernetDescription = mach['ethernet make'].value() + ' ' + mach['ethernet model'].value()
    else:
        ethernetDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

    if mach['audio make'].status() == FIELD_HAS_DATA:
        audioDescription = mach['audio make'].value() + ' ' + mach['audio model'].value()
    else:
        audioDescription = COLOR_TO_REVERT_TO + 'not found' + COLOR_TO_USE

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
    print "Video".ljust(FIRST_COL_WIDTH) + videoDescription
    print "Network".ljust(FIRST_COL_WIDTH) + ethernetDescription
    print "Audio".ljust(FIRST_COL_WIDTH) + audioDescription
    sys.stdout.write(COLOR_TO_REVERT_TO)


def processCommandLineArguments():
    global debugMode, skipLSHW
    rawFileToLoad = ""

    for item in sys.argv[1:]:
        if item == '-d' or item == '--debug':
            debugMode = True
        if item == '-s':
            skipLSHW = True
        elif item[0] == '-':
            assert False, "Unrecognized command option: " + item
        else:
            rawFileToLoad = item

    return rawFileToLoad


# Read in all the raw data from the various data sources.
def readRawData(rawFilePath=None):
    if rawFilePath and not rawFilePath == "":
        rawDict = readRawDataFromFile(rawFilePath)

    else:
        rawDict = dict()

        # Get dmidecode info describing the system's make and model and such.
        print "Reading system make and model."
        try:
            rawDict['dmidecode_system_make'] = terminalCommand("dmidecode -s system-manufacturer")
            rawDict['dmidecode_system_model'] = terminalCommand("dmidecode -s system-product-name")
            rawDict['dmidecode_system_version'] = terminalCommand("dmidecode -s system-version")
            rawDict['dmidecode_system_serial'] = terminalCommand("dmidecode -s system-serial-number")
        except OSError as errMsg:
            print "WARNING: System make and model could not be determined. Execution of dmidecode failed " \
                  "with message: " + str(errMsg)

        # Get dmidecode info describing the system's RAM slots and their contents.
        print "Reading RAM information."
        try:
            rawDict['dmidecode_memory'] = terminalCommand("dmidecode -t 17")  # Type 17 is RAM.
        except OSError as errMsg:
            print "WARNING: System RAM could not be determined. Execution of dmidecode failed " \
                  "with message: " + str(errMsg)

        # Get CPU speed.
        print "Determining maximum CPU frequency."
        try:
            rawDict['cpuinfo_max_freq'] = open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read()
        except IOError as errMsg:
            print "WARNING: CPU frequency could not be determined. Unable to access the cpuinfo_max_freq " \
                  "system file because: " + str(errMsg)

        # Get OS bit depth.
        print "Checking OS bit depth."
        try:
            rawDict['getconf'] = str(terminalCommand("getconf LONG_BIT"))
        except OSError as errMsg:
            print "WARNING: OS bit-depth could not be determined. Execution of getconf failed " \
                  "with message: " + str(errMsg)

        # Get information about all hard drives.
        print "Getting internal hard drive information."
        try:
            rawDict['hdparm_sda'] = str(terminalCommand("hdparm -I /dev/sda"))
            rawDict['hdparm_sdb'] = str(terminalCommand("hdparm -I /dev/sdb"))
            rawDict['hdparm_sdc'] = str(terminalCommand("hdparm -I /dev/sdc"))
        except OSError as errMsg:
            print "WARNING: Some hard drive information may unavailable. Execution of hdparm command " \
                  "failed with message: " + str(errMsg)

        # Get Linux version information.
        print "Checking OS version."
        try:
            rawDict['lsb_release'] = str(terminalCommand("lsb_release -d"))
        except OSError as errMsg:
            print "WARNING: Linux version could not be determined. Execution of lsb_release failed " \
                  "with message: " + str(errMsg)

        # Get CPU make and model.
        print "Reading processor information."
        try:
            rawDict['dmidecode_processor'] = str(terminalCommand("dmidecode -t processor"))
        except OSError as errMsg:
            print "WARNING: CPU model could not be determined. Execution of dmidecode failed " \
                  "with message: " + str(errMsg)

        # Get bulk information about all hardware.
        print "Reading misc hardware info."
        try:
            if not skipLSHW:
                rawDict['lshw'] = str(terminalCommand("lshw"))
        except OSError as errMsg:
            print "WARNING: Most hardware information could not be obtained. Execution of lshw command " \
                  "failed with message: " + str(errMsg)

        # Get information about internal and external USB devices.
        print "Reading USB device info."
        try:
            rawDict['lsusb'] = str(terminalCommand("lsusb"))
        except OSError as errMsg:
            print "WARNING: USB device info unavailable (including webcam). Execution of lsusb command " \
                  "failed with message: " + str(errMsg)

        # Get power supply (battery) information from upower.
        print "Looking for battery."
        try:
            rawDict['upower'] = str(terminalCommand("upower --dump"))
        except OSError as errMsg:
            print "WARNING: Battery information unavailable. Execution of upower command failed with " \
                  "message: " + str(errMsg)

    return rawDict


# Read in all the raw data from a pre-made raw data file.
def readRawDataFromFile(rawFilePath):
    # Create the raw dictionary.
    rawDict = dict()
    rawDict['raw_file_source'] = rawFilePath

    # Load the previously written raw file.
    data = open(rawFilePath).read()

    # Restore the raw file into the dictionary.
    keySearch = re.findall(r"{{{(.*)}}}", data)
    valSearch = re.findall(r"}}}\n([\s\S]*?)\n\n(?:(?:{{{)|(?:$))", data)
    if keySearch and valSearch and len(keySearch) == len(valSearch):
        for i in range(len(keySearch)):
            rawDict[keySearch[i]] = valSearch[i]
    else:
        errMsg = str(len(keySearch)) + " {{{headers}}} and " + str(len(valSearch)) + " " \
                 "bodies were found in raw data file: " + rawFilePath
        assert False, errMsg

    return rawDict


# Remove junk words, irrelevant punctuation and multiple spaces from a field string.
def sanitizeString(string):
    # Remove junk words like "corporation", "ltd", etc
    for word in junkWords:
        string = re.sub('(?i)' + word, '', string)
    # Fix words that can be written more neatly.
    for badWord in correctableWords.keys():
        goodWord = correctableWords[badWord]
        string = re.sub('(?i)' + badWord, goodWord, string)
    # Remove junk punctuation.
    string = re.sub(',', '', string)
    string = re.sub('\[', '', string)
    string = re.sub('\]', '', string)
    return stripExcessWhitespace(string)


# Reduce multiple whitespaces to a single space and eliminate leading and trailing whitespace.
def stripExcessWhitespace(string):
    # Reduce multiple whitespace sections to a single space.
    string = re.sub('\s\s+', ' ', string)
    # Remove leading and trailing whitespace.
    string = re.sub('^\s*', '', string)
    string = re.sub('\s*$', '', string)
    return string


# Get the output from a terminal command.
def terminalCommand(command):
    output, _ = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=DEVNULL).communicate()
    return output


# Fill-in a build sheet given a template.
def writeODSFile(mach, templateFilename, outputFilename=None):
    if not outputFilename:
        outputFilename = mach['system id'].value() + '.ods'
    odsInput = zipfile.ZipFile(templateFilename, 'r')
    odsOutput = zipfile.ZipFile(outputFilename, 'w')
    for fileHandle in odsInput.infolist():
        fileData = odsInput.read(fileHandle.filename)
        if fileHandle.filename == 'content.xml':
            for fieldName in fieldNames:
                field = mach[fieldName]
                fileData = fileData.replace('{' + fieldName + '}', field.value())
        odsOutput.writestr(fileHandle, fileData)
    odsOutput.close()
    odsInput.close()
    os.chmod(outputFilename, 0777)  # Make the ODS file writeable.


def writeRawData(rawDict, filePath):
    if "raw_file_source" in rawDict:
        print "Raw file not created because raw data was loaded from: " + rawDict["raw_file_source"]
        return

    # Initialize the string that will contain all the raw data.
    rawFileContents = ''

    # Construct a long string of all raw data text.
    for key in sorted(rawDict.keys()):
        rawFileContents += '{{{' + key + '}}}\n' + rawDict[key] + '\n\n'

    # Write the raw data to file.
    rawFile = open(filePath, 'w')
    rawFile.write(rawFileContents)
    rawFile.close()


# # ***************************************************************************************
# # *******************************  START OF MAIN ****************************************
# # ***************************************************************************************
def main():
    rawFileToLoad = processCommandLineArguments()

    # Initialize an empty machine description.
    machine = dict()
    for fieldName in fieldNames:
        machine[fieldName] = Field(fieldName)

    # Fetch all the raw data describing the machine.
    if not rawFileToLoad == "":
        rawDict = readRawData(rawFileToLoad)
    else:
        rawDict = readRawData(None)

    # Notify for unrecognized raw data sections that were found.
    for rawDataName in rawDict.keys():
        if rawDataName not in rawDataSectionNames:
            print "Unrecognized raw data section named \"" + rawDataName + "\""

    # Check for missing raw data.
    for rawDataName in rawDataSectionNames:
        if rawDataName not in rawDict.keys():
            print "Missing raw data section for \"" + rawDataName + "\""
            rawDict[rawDataName] = ""

    # Interpret dmidecode first so the system will have a proper id.
    interpretDmidecodeSystem(rawDict, machine)

    # Save a copy of all the raw data.
    writeRawData(rawDict, machine['system id'].value() + '.txt')

    # Interpret all the rest of the raw data.
    interpretCPUFreq(rawDict, machine)
    interpretDmidecodeMemory(rawDict, machine)
    interpretDmidecodeProcessor(rawDict, machine)
    interpretGetconf(rawDict, machine)
    interpretHdparm(rawDict, machine)
    interpretLSBRelease(rawDict, machine)
    interpretLSHW(rawDict, machine)
    interpretLSUSB(rawDict, machine)
    interpretUPower(rawDict, machine)

    # If debugging then dump info about failed regex matches.
    if debugMode:
        dumpCaptureFailures()

    # Output our program's findings.
    print  # Blank line
    printBuildSheet(machine)
    writeODSFile(machine, 'template.ods')


try:
    main()

# Catch-and-release assertion errors.
except AssertionError as errMsg:
    print "ERROR: " + str(errMsg) + '\n'

# Catch all other exceptions so the user won't see traceback dump.
except:
    etype, evalue, etrace = sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
    if debugMode:
        # If debug mode is active then dump the traceback.
        sys.excepthook(etype, evalue, etrace)
    print "ERROR: " + str(etype)
    print "MESSAGE: " + str(evalue) + "\n"
