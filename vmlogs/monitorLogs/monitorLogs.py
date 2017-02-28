#!/usr/bin/env python

# Dylan Telford
# July 26, 2016
# monitorLogs.py

# Python script to set up inotify to watch a file, specified with -f.
# Upon modification, it will open pickled dictionary of filenames:last 
# line looked at, open the  file and move to that line, then 
# look at all subsequent lines, updatng the pickle dictionary each
# time it looks at a line. It will run a command (from -c) on each line,  
# unless a regex is specified using -r or -R (from a file), in which case 
# it wil only run the command on matches. -l will list all pickle entries 
# and -d <filename> will delete the entry for that file from the pickle.


### Regex to match vm state changes in euca logs and get time, id, new state
# ^([0-9-]+ [0-9:]+)  INFO \| (i-[0-9a-fA-F]{8}) state change: [A-Z_]+ -> ([A-Z_]+) .+$


######################### Imports ##########################
import time
import os
import sys
import re
import getopt
import subprocess
import cPickle as pickle
from os.path import exists
try:
    import inotify.adapters
except:
    print 'This script requires the inotify module. Install with pip'
    sys.exit(1)

######################## Variables #########################
logName = ''
pickleName = 'lastLog.p'
command = ''
regex = ''
delimiter = ' '
verbose = False
deletePickle = ''
listPickle = False

shortHelp = 'Usage: response.py -f <filename -c <command>\nTry "response.py \
--help" for more'
longHelp = 'Usage: response.py -f <filename> -c <command>\n\
Optional Arguments:\n\
 -p (--picklename) <picklename>   Set the pickle file (default lastLog.p)\n\
 -d (--delete) <filename>         Delete a file from the pickle dictionary\n\
 -r (--regex) <reg expression>    Regular expression to match in the log\n\
 -R (--regfile) <filename>        Specify a file containing the regex to use\n\
 -s (--seperator) <delimiter>     Specify a delimiter for listing regex groups\n\
 -l (--list)                      List all key : value pairs in pickle dict\n\
 -v (--verbose)                   Print info about processes as they happen\n\
 -h (--help)                      Print this screen\n\
Note: When using a regex with groups, the groups will be extracted and listed\n\
      seperated by spaces, unless another delimiter is specified with -s \n'

######################## Functions #########################
def main():
    """main method will set up inotify to watch the file passed
    by the user with -f. If the file is modified, it will call 
    the check_modified_file() method to get new lines."""
    i = inotify.adapters.Inotify()
    i.add_watch(logName)
    try:
        for event in i.event_gen():
            if event is not None:
                (header, type_names, watch_path, filename) = event
                if 'IN_MODIFY' in type_names:
                    check_modified_file()
    finally:
        i.remove_watch(logName)


def check_modified_file():
    """load dictionary from pickle and open the -f file.
    Starting from the end, it will work its way back to the line from the 
    dictionary, pushing each line along the way to a stack. When it reaches
    the line, It will begin popping the stack and processing lines, updating
    the pickle file each time a line is looked at."""
    if exists(pickleName):    
        if verbose:
            print 'Loading the dictionary from ' + pickleName
        try:
            with open(pickleName, 'rb') as f:
                lineDict = pickle.load(f)
        except:
            if exists(pickleName + '.bak'):
                try:
                    with open(pickleName + '.bak', 'rb') as f:
                        lineDict = pickle.load(f)
                except:
                    lineDict = {}
            else:
                lineDict = {}
    else:
        lineDict = {}
        
    if logName in lineDict:
        lastLine = lineDict[logName]
    else:
        lastLine = 'xXx dummy line */*/*'
    
    if verbose:
        print 'Reading the file ' + logName + ' and building stack'
    lineStack = []  # simulate Stack by appending to and popping list
    for line in reversed(open(logName).readlines()):
        line = line.rstrip()
        if line == lastLine:
            break
        lineStack.append(line)
    
    if verbose:
        print 'Moving through stack and processing lines 1 at a time'
    while lineStack:
        newLastLine = lineStack[-1]
        check_log(lineStack.pop())
        lineDict[logName] = newLastLine
        # Create backup of pickle
        if exists(pickleName):
            backupName = pickleName + '.bak'
            if exists(backupName):
                os.remove(backupName)
            os.rename(pickleName, backupName)
        # Update pickle
        with open(pickleName, 'wb') as f:
            pickle.dump(lineDict, f)
    if verbose: 
        print 'Finished... Goodbye'


def check_log(myLog):
    """takes a command from -c and runs it on the line passed to the function, 
    either replacing {} or appending to the end of the command."""
    myStr = ''
    if regex:
        match = re.search(regex, myLog)
        if match:
            if len(match.groups()) > 0:
                for group in match.groups():
                    myStr += group + delimiter
                choplen = -1 * len(delimiter)
                myStr = myStr[:choplen]
            else:
                myStr = myLog
    else:
        myStr = myLog
    if '{}' in command:
        mycmd = command.replace('{}', '"' + myStr + '"')
    else:
        mycmd = command + ' "' + myStr + '"'
    if regex:
        match = re.search(regex, myLog)
        if match:
            os.system(mycmd)
    else:
        os.system(mycmd)


def delete_pickle_entry(entry):
    """loads the pickle dictionary and deletes the entry passed in by the 
    user with -d. Also deletes the entry from the backup file."""
    if exists(pickleName):
        try:
            with open(pickleName, 'rb') as f:
                myDict = pickle.load(f)
            if entry in myDict:
                del myDict[entry]
            with open(pickleName, 'wb') as f:
                pickle.dump(myDict, f)
            print '"' + entry + '" was deleted from the file ' + pickleName
        except:
            print 'Could not load ' + pickleName
    else:
        print 'The file ' + pickleName + ' does not exist.'
    # delete entry from backup file as well
    backupName = pickleName + '.bak'
    if exists(backupName):
        try:
            with open(backupName, 'rb') as f:
                myDict = pickle.load(f)
            if entry in myDict:
                del myDict[entry]
            with open(backupName, 'wb') as f:
                pickle.dump(myDict, f)
            print '"' + entry + '" was deleted from the file ' + backupName
        except:
            print 'Could not load ' + backupName
            

def list_pickle_entries():
    """lists all of the key:value pairs in both the pickle file and 
    the backup pickle file."""
    if exists(pickleName):
        try:
            with open(pickleName, 'rb') as f:
                myDict = pickle.load(f)
            print '\nContents of ' + pickleName + ':'
            for key in myDict:
                print 'Last line processed in ' + key + ':\n' + myDict[key] + '\n'
            print ''
        except:
            print 'Could not load ' + pickleName
    else:
        print 'The file ' + pickleName + ' does not exist.'
    # list backups too
    backupName = pickleName + '.bak'
    if exists(backupName):
        try:
            with open(backupName, 'rb') as f:
                myDict = pickle.load(f)
            print '\nContents of ' + backupName + ':'
            for key in myDict:
                print 'Last line processed in ' + key + ':\n' + myDict[key] + '\n'
            print ''
        except:
            print 'Could not load ' + backupName


def set_vars(args):
    """uses the getopt module to set command line arguments passed
    in by the user. Asserts that the user gives arguments for 
    -f <filename> and -c <command>"""
    try:
        opts, args = getopt.getopt(args, 'c:d:p:f:r:R:s:lvh', ['command=',
                                   'delete=', 'picklename=', 'filename=',
                                   'regex=', 'regfile=', 'seperator=', 'list', 
                                   'verbose', 'help'])
    except getopt.GetoptError:
        print shortHelp
        sys.exit(2)
    global regex
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print longHelp
            sys.exit(0)
        elif opt in ('-f', '--filename'):
            global logName
            logName = arg
        elif opt in ('-c', '--command'):
            global command
            command = arg
        elif opt in ('-d', '--delete'):
            global deletePickle
            deletePickle = arg
        elif opt in ('-l', '--list'):
            global listPickle
            listPickle = True
        elif opt in ('-r', '--regex'):
            regex = arg
        elif opt in ('-R', '--regfile'):
            try:
                with open(arg, 'r') as fh:
                    lines = fh.readlines()
                if len(lines) == 1:
                    regex = lines[0].rstrip()
                else:
                    for line in lines:
                        if line[0] != '#' and len(line) > 1:
                            regex = line.rstrip()
                            break
            except:
                print 'Unable to open ' + arg
                sys.exit(1)
        elif opt in ('-s', '--seperator'):
            global delimiter
            delimiter = arg
        elif opt in ('-p', '--picklename'):
            if arg[-2:] != '.p':
                arg += '.p'
            global pickleName
            pickleName = arg
        elif opt in ('-v', '--verbose'):
            global verbose
            verbose = True
    if logName == '' and not listPickle and not deletePickle:
        print 'You must provide a file name using -f <filename>'
        print shortHelp
        sys.exit(2)
    if command == '' and not listPickle and not deletePickle:
        print 'You must provide a command using -c <command>'
        print shortHelp
        sys.exit(2)
    if not regex and delimiter != ' ':
        print 'You must use a regex with groups in order to use the -s option.'
        sys.exit(2)


######################## Main Call #########################
if __name__ == "__main__":
    set_vars(sys.argv[1:])
    if deletePickle:
        delete_pickle_entry(deletePickle)
        sys.exit(0)
    if listPickle:
        list_pickle_entries()
        sys.exit(0)
    try:
        main()
    except KeyboardInterrupt:
        print 'Goodbye.'
        sys.exit(0)
