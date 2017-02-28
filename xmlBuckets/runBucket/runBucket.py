#!/usr/bin/env python

# Dylan Telford
# June 8, 2016
# runBucket.py

# A python script that will take an xml document (either from a file or
# from std input) containing the location of all of the files in the
# bucket. Given a "path" to the tag we want (ie. key) and a command,
# the script will call that command on each file in the bucket. If no
# command is given, it will print a list of the tags it found.

######################## Imports #########################
import getopt
import sys
import subprocess
import re
import xml.etree.ElementTree as ET

####################### Variables ########################
path = 'ListBucketResults/Contents/Key'
cmd = ''
filename = ''
outfile = ''
verbose = False
quiet = False
echo = False
rem = False

shortHelp = '\nUsage: runBucket.py -c <command> -p <path>\n\
For more information, type "runBucket.py -h"'
longHelp = 'Usage: runBucket.py -c <command> -p <path>\n\
This script will take and xml document (either from a file\n\
or from stdin), extract the file key at whatever tag path is\n\
specified, and will run a given command on each value.\n\
Mandatory Arguments:\n\
\t-c (--command) <command>   Command you wish to run on each file\n\
\t                           (file name added at end or replaces {})\n\
\t-p (--path) <path>         Tag path to the value holding filenames\n\
\t                           (may simply be the name of the tag)\n\
Optional Arguments:\n\
\t-f (--filename) <filename> Name of xml file to use, uses stdin if none\n\
\t-o (--outfile) <outfile>   Name of file to put any otput in\n\
\t-v (--verbose)             Print info about processes as they happen\n\
\t-q (--quiet)               Output nothing\n\
\t-e (--echo)                Print Command as it is called\n\
\t-r (--remaining)           Print progress (ie. file 2/10 (10%))\n\
\t-h (--help)                Print this screen'

####################### Functions ########################
def main(argv):
    """Main method will call functions to set variables and get keys,
    then iterate through the keys, calling the command on each key.
    If there s output from the command, it will be sent to the outfile
    or to stdout if no such file exsts."""
    set_vars(argv)
    myKey = path.split('/')[-1] #get last tag in path
    if verbose and not echo:
        print "Grabbing values from xml document..."
    keys = get_keys(myKey) #array of keys in bucket
    total = len(keys)
    counter = 1
    for key in keys:
        if "{}" in cmd:
            myCmd = cmd.replace("{}", key)
        else:
            myCmd = cmd + " " + key
        if verbose or echo:
            print "Running the command: " + myCmd
        if rem:
            percent = (float(counter)/total) * 100
            print "Progress: file %d/%d (%.2f%%)" % (counter, total, percent)
        output = subprocess.check_output(myCmd, shell=True)
        if not quiet and output:
            output_result(output)
        counter += 1


def set_vars(args):
    """Takes sys.argv[1:] as an argument and uses the getopt package to
    parse the user's arguments and assign them to variables."""
    try:
        opts, args = getopt.getopt(args, "p:c:f:o:hvqer", ["path=", \
        "command=", "filename=", "outfile=", "help", "verbose", \
        "quiet", "echo", "remaining"])
    except getopt.GetoptError:
        print shortHelp
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print longHelp
            sys.exit(2)
        elif opt in ("-p", "--path"):
            global path
            path = arg
        elif opt in ("-c", "--command"):
            global cmd
            cmd = arg
        elif opt in ("-f", "--filename"):
            global filename
            filename = arg
        elif opt in ("-o", "--outfile"):
            global outfile
            outfile = arg
        elif opt in ("-v", "--verbose"):
            global verbose
            verbose = True
        elif opt in ("-q", "--quiet"):
            global quiet
            quiet = True
        elif opt in ("-e", "--echo"):
            global echo
            echo = True
        elif opt in ("-r", "--remaining"):
            global rem
            rem = True
        else:
            print shortHelp
            sys.exit(2)
    if path == '' or cmd == '':
        print shortHelp
        sys.exit(2)


def get_keys(myTag):
    """Creates an element tree from the xml document (either from a file
    or from stdin), and searches it for the requested values, appending
    them to a list that is returned at the end."""
    if filename == '':
        tree = ET.parse(sys.stdin)
    else:
        try:
            tree = ET.parse(filename)
        except IOError:
            print "Unable to open %s" % (filename)
    root = tree.getroot()
    rootTag = root.tag
    keys = []
    if rootTag[0] == "{": # Check to see if namespace exists
        m = re.search('^(\{.+\}).+$', rootTag) # use regex to extract namespace
        ns = m.group(1)
        for key in root.iter(ns + myTag):
            keys.append(key.text)
    else:
        for key in root.iter(myTag):
            keys.append(key.text)
    return keys


def output_result(myOutput):
    """If an output file is specified, write output to that, if not,
    print to stdout."""
    if outfile:
        try:
            f = open(outfile, 'a')
            f.write(myOutput)
            f.close()
        except IOError:
            print "Unable to write to " + outFile + "...\n" + e.strerror
            sys.exit(1)
    else:
        sys.stdout.write(myOutput)


####################### Main Call ########################
if __name__ == "__main__":
    main(sys.argv[1:])
