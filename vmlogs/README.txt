monitorLogs.py is a python script that will use the inotify python package
to watch a file (specified with the -f option) and run a command (given with 
-c) on new lines as they are added. The new line will be added (in quotations) 
to the end of the command, or will replace {} if used in the command. 

A regex can be used with -r (entered at the commandline) or -R (read from a 
file) to ony run the command on new lines that match.

If the regex contains groupings, a string will be composed of these groups, 
separated by spaces, or by some user-scpecidied delimiter, using -s <delimiter>.
The command will then be run on this new string.

The script will create and maintain a pickled dictionary in the same directory, 
holding the last line looked at in all files it has been called on. A listing 
of these files/lines can be obtained using "./monitorLogs.py -l". An entry for 
any given file can be deleted from this dictionary using "./monitorLogs.py -d <file>".

The default name for the pickle file is lastLog.p and a backup lastLog.p.bak. These
names may be changed by using the -p <picklename> option. 
