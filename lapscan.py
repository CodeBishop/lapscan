#!/usr/bin/env python

FIRST_COL_WIDTH = 16


def linesFromFile(filepath):
    with open(filepath) as f:
        content = f.readlines()
    return content


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
            if descField.find("ethernet") != -1:
                machDict["network"].append(descField)
            elif descField.find("wifi") != -1 or descField.find("wireless") != -1:
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
lshwshort_lines = linesFromFile("../lapscanData/thinkpad_t61/lshw_short.out")
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

