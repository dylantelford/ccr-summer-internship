#!/usr/bin/env python

# Dylan Telford
# June 2, 2016
# availableNodes.py

#A Python script that utilizes Elasticsearch to show how many of each
# type of node exist, are in use, and are available. It will return a
# JSON document containing a record for each node type either to std output
# (default) or to an output file if -o is used.
#Command line arguents:
#   -t <time>
#   -o <output_file>
#   -a <ip_address>
#   -p <port>
#   -v (verbose)
#   -h (help)

################## Import Packages #####################
import json, sys, getopt, time
from datetime import datetime, timedelta
from dateutil import tz
from dateutil.parser import parse
try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import *
except ImportError:
    print "This script requires the elasticsearch python module. \n\
    install with \"pip install elasticsearch\""
    sys.exit(1)
try:
    import pytz
except ImportError:
    print "This script requires the pytz python module, \
    install with \"pip install  pytz\""

################### Variables ##########################
myTime = ''
outFile = ''
address = '10.63.41.114'
port = 9200
verbose = False
#dictionary for tag names
tagDict = {"vmTypesAvailable": "\"euca_vmtypeavailability\""}
#query for node info logs
q = "tags: " + tagDict["vmTypesAvailable"]
indexName = "logstash-" #beginning of index names, followed by YYYY.MM.DD
maxHits = 10000 #if no max is set in query, Elasticsearch defaults to 10 results
indent = 2 #formatting for JSON output

#help strings
shortHelp = "Usage: availableNodes.py -t <date_time>\nType \"availaleNodes.py\
 -h\" for more info"
longHelp = "Usage: availableNodes.py -t <date_time>\nMandatory Arguments:\n\
 -t (--time) <date_time>       Time at which you want to describe nodes.\n\
 (Time may be in any format supported by Python)\n\n\
 Optional Arguments:\n\
 -o (--outFile) <output_file>  Name of file to write outup to. If left out, \
 result will be sent to std output.\n\
 -a (--address) <ip_address>   ip address of the server hosting Elasticsearch\n\
 -p (--port) <port>            Port to connect to, default to 9200\n\
 -v (--verbose)                Print info about operations as they happen\n\
 -h (--help)                   Print out this screen\n\n\
 -r (--reqs)                   Prints info about required tags in Elasticsearch\n\
Dependencies:\nThis script requires the elasticsearch python module as \
well as the pytz module.\nBoth can be installed with pip install <module_name>"
reqHelp = "\nThe default index name is \"%sYYYY.MM.DD\"\n\
In your Elasticsearch, logs containing info about available vm \n\
types should have the tag(s):\n" % (indexName)


################### Functions ##########################
def main(argv):
    """Main method will connect to Elasticsearch, create necessary
    datetime objects, then call methods to search a range of time
    (from one minute before to one minute after the user's time) for
    ResourceSate logs, Find the closest timestamp, and extract node
    info from that log- outputting it in a JSON record."""
    set_vars(argv)
    if verbose:
        print "Connecting to Elasticsearch..."
    global es
    try:
        es = Elasticsearch([{'host': address, 'port': port}])
    except ElasticsearchException:
        print "Unable to connect to the Elasticsearch server."
        sys.exit(1)
    try:
        es.ping()
    except:
        print "Unable to connect to the Elasticsearch server."
        sys.exit(1)
    if verbose:
        print "Connected."
    #create daetime object from user inputted time
    global myDt
    try:
        myDt = parse(myTime)
    except ValueError:
        print "Python did not recognize your time format. Please try again\n"
        sys.exit(2)
    #Convert myDt to utc here
    if myDt.tzinfo != tz.tzutc():
        myDt = convert_to_utc(myDt)
    #Check to see if time is in future
    now = convert_to_utc(datetime.now())
    if myDt > now:
        print "The time entered has not happened yet. Please try again."
        sys.exit(2)
    #create less than and greater than datetime objects for range query
    ltDt = myDt + timedelta(minutes=1)
    gtDt = myDt - timedelta(minutes=1)
    index = index_from_date(myDt)
    if verbose:
        print "Searching the index \"", index, "\" for ResourceState logs..."
    idArr = search_index(index, ltDt, gtDt) #array of tuples (id, timestamp)
    if verbose:
        print "Finding the log closest to your time..."
    bestId = find_closest(idArr) #id of closest timestamp
    searchResDict = search_for_id(bestId, index) #dict returned by Elasticsearch
    if verbose:
        print "Pulling node info from system log..."
    finalDict = populate_node_info(searchResDict) #dict of dicts (1 per node type)
    if verbose:
        print "Outputting result..."
    print_result(finalDict)
    if verbose:
        print "Finished, Goodbye."


def set_vars(myArgs):
    """Uses getopt module to parse command line arguments (from sys.argv)
    param args- (array) sys.argv[1:]"""
    try:
        opts, args = getopt.getopt(myArgs, "t:o:a:p:vhr", ["time=", "outFile=", \
        "address=", "port=", "verbose", "help", "reqs"])
    except getopt.GetoptError:
        print shortHelp
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print longHelp
            sys.exit(2)
        elif opt in ("-t", "--time"):
            global myTime
            myTime = arg
        elif opt in ("-o", "--outFile"):
            global outFile
            outFile = arg
        elif opt in ("-a", "--address"):
            global address
            address = arg
        elif opt in ("-p", "--port"):
            global port
            port = arg
        elif opt in ("-v", "--verbose"):
            global verbose
            verbose = True
        elif opt in ("-r", "--reqs"):
            print reqHelp
            for i in tagDict:
                print "\t%s\n" % (tagDict[i])
            sys.exit(2)
        else:
            print shortHelp
            sys.exit(2)
    if myTime == "":
        print shortHelp
        sys.exit(2)

def index_from_date(dt):
    """Takes in a datetime object and constructs the name of the index in the
    Elasticsearch for that day. Returns a string of this index.
    param dt- (datetime) the day for which we want an index of."""
    year = str(dt.year)
    month = str(dt.month)
    if len(month) == 1:
        month = '0' + month
    day = str(dt.day)
    if len(day) == 1:
        day = '0' + day
    index = indexName + year + '.' + month + '.' + day
    return index


def search_index(ind, lt, gt):
    """Takes in an index to search, and two datetime objects, lt is one second
    later than the user's inputted time, gt is one second earlier. Elasticsearch
    is queried using a range of these two times. The id and timestamp are
    extracted from each hit and stored in an array of tuples, which is returned"""
    ltstr = lt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    gtstr = gt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    print "Searching from ", gtstr, " to ", ltstr, " (UTC Time)"
    try:
        sDict = es.search(index=ind, body={ "from": 0, "size": maxHits, \
        "query": { "query_string": { "query": q } }, "filter": { \
        "range": {"@timestamp": { "lte": ltstr, "gte": \
        gtstr } } } })
    except NotFoundError:
        print "The index \"" + ind + "\" does not exist."
        sys.exit(1)
    except RequestError:
        print "There was a problem with your query, check query syntax."
    except:
        print "Unexpected Error:\n", sys.exc_info()[0]
        sys.exit(1)

    idArr = [] #array to hold tuples of (id, timestamp) reulting from seach
    hits = sDict['hits']['hits'] #array of dictionaries
    for hit in hits:
        myId = hit["_id"]
        myDict = hit["_source"] #smaller dictionary holding timestamp
        myStamp = myDict["@timestamp"]
        idArr.append((myId, myStamp))
    return idArr


def find_closest(ids):
    """Will take in an array of tupes holding (id, timestamp) of hits from
    the first Elasticsearch query. It will calculate the differences between
    each time and the user inputted time, and store them in an array along with
    their id. Then iterates over the array, finding the smallest difference,
    and returns the corresponding id"""
    best = ''
    smallest = sys.maxint
    difs = [] #array of tuples holding (time_difference, id)
    for tup in ids:
        timestamp = parse(tup[1])
        dif = ((myDt - timestamp).total_seconds())
        if dif < 0:
            dif = ((timestamp - myDt).total_seconds())
        difs.append((dif, tup[0]))
    for dif, myId in difs:
        if dif < smallest:
            smallest = dif
            best = myId
    return best


def search_for_id(myId, ind):
    """Takes a logstash id and index as parameters and uses Elasticsearch
    to search that index for the log with myId. Returns the dictionary
    resulting from the search."""
    try:
        sDict = es.search(index=ind, body={ "query": { "query_string": { \
        "query": "_id: " + myId } } } )
    except NotFoundError:
        print "The index \"" + ind + "\" does not exist."
        sys.exit(1)
    except RequestError:
        print "There was a problem with your query, check query syntax."
    except:
        print "Unexpected Error:\n", sys.exc_info()[0]
        sys.exit(1)
    return sDict


def populate_node_info(searchDict):
    """Creates a dictionary nodeTypes where keys are node types and values
    are sub dictionaries holding values for available, used, and total
    for that type of node. This info is pulled from the dictionary
    returned from the Elasticsearch query for the best id."""
    nodeInfo = {} #dictionary of dictionaries (1 per node type)
    myD = searchDict["hits"]["hits"][0]["_source"] #dict from Elasticsearch
    nodeTypes = ["c1_medium", "c1_xlarge", "cc1_4xlarge", "cc2_8xlarge", \
    "cg1_4xlarge", "cr1_8xlarge", "hi1_4xlarge", "hs1_8xlarge", \
    "m1_large", "m1_medium", "m1_small", "m1_xlarge", "m2_2xlarge", \
    "m2_4xlarge", "m2_xlarge", "m3_2xlarge", "m3_xlarge", "t1_micro"]

    for node in nodeTypes:
        total = myD[node+"_total"]
        avail = myD[node+"_available"]
        used = str((int(total)-int(avail)))
        nodeInfo[node] = {"total":total, "available":avail, "in_use":used}
    return nodeInfo


def convert_to_utc(origDt):
    """Will take in a datetime object and convert it to UTC time. Assume that
    a naive time is local to New York."""
    if origDt.tzinfo == None:
        if time.daylight:
            offsetHour = time.altzone / 3600
        else:
            offsetHour = time.timezone / 3600
        zone = 'Etc/GMT%+d' % offsetHour
        local = pytz.timezone(zone)
        localDt = local.localize(origDt, is_dst=None)
        utcDt = localDt.astimezone(tz.tzutc())
    else:
        utcDt = origDt.astimezone(tz.tzutc())
    return utcDt


def print_result(myDict):
    """Converts the dicionary passed to it into a JSON object. If there is
    a user-specified output file, the output will be written to it,
    otherwise, it will go to std out."""
    jsonDict = json.dumps(myDict, indent=indent, separators=(',', ': '), sort_keys=True)
    if outFile == '':
        print jsonDict
    else:
        try:
            f = open(outFile, 'w')
            f.write(jsonDict)
            f.close()
        except IOError:
            print "Unable to write to " + outFile + "...\n" + e.strerror
            sys.exit(1)


################# Main Call #####################
if __name__ == "__main__":
    main(sys.argv[1:])
