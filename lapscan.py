#!/usr/bin/env python

FIRST_COL_WIDTH = 15

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
                machDict["hdd"].append(descField)
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


def printField(machDict, preface, key):
    print preface.ljust(FIRST_COL_WIDTH),
    if machDict[key] is None:
        print "<ERROR: machDict key not found>"
    elif len(machDict[key]) == 0:
        print
    elif len(machDict[key]) == 1:
        print machDict[key][0]
    else:
        print
        for entry in machDict[key]:
            print "".ljust(FIRST_COL_WIDTH) + entry

# ***************************************************************************************
# *******************************  START OF MAIN ****************************************
# ***************************************************************************************

# Prep the machine dictionary
machDict = {}
machDict["ram"] = []
machDict["hdd"] = []
machDict["video"] = []
machDict["cdDvd"] = []
machDict["cpu"] = []

lshwshort_lines = linesFromFile("thinkpad_t61/lshw_short.out")
lshwshortData = readLSHWShort(machDict, lshwshort_lines)

# Print the Build Sheet.
printField(machDict, "CPU", "cpu")
printField(machDict, "HDD", "hdd")

