#!/usr/bin/python
import sys
import copy
import os

from cStringIO import StringIO
import argparse
import errno
import xml.dom.minidom as minidom

class ProcessImage:
    class Variable:
        def __init__(self):
            self.Name = None
            self.Comment = None
            self.DataType = None
            self.BitSize = None
            self.BitOffs = None

    class Interface:
        def __init__(self):
            self.ByteSize = None
            self.variables = None

    def __init__(self):
        self.Inputs = None
        self.Outputs = None

def parseVariable( xml ):
    v = ProcessImage.Variable()

    v.Name = str(xml.getElementsByTagName("Name")[0].childNodes[0].data)

    if len(xml.getElementsByTagName("DataType")) > 0:
        v.DataType = str(xml.getElementsByTagName("DataType")[0].childNodes[0].data)

    if len(xml.getElementsByTagName("Comment")) > 0:
        v.Comment = str(xml.getElementsByTagName("Comment")[0].childNodes[0].data)

    v.BitSize = int(xml.getElementsByTagName("BitSize")[0].childNodes[0].data)

    v.BitOffs = int(xml.getElementsByTagName("BitOffs")[0].childNodes[0].data)

    return v

def parseInterface( xml):
    byteSizeXml = xml.getElementsByTagName("ByteSize")
    i = ProcessImage.Interface()
    i.ByteSize = int(byteSizeXml[0].childNodes[0].data)

    variablesXml = xml.getElementsByTagName("Variable")

    i.variables = []
    for varXml in variablesXml:
        i.variables.append( parseVariable( varXml ) )

    return i

def parseProcessImage( xml ):
    inputsXml = xml.getElementsByTagName("Inputs")
    outputsXml = xml.getElementsByTagName("Inputs")

    pi = ProcessImage()

    pi.Inputs = parseInterface( inputsXml[0] )
    pi.Outputs = parseInterface( outputsXml[0] )

    return pi

class PdoEntry:
    def __init__(self):
        self.index = None
        self.subindex = None
        self.bit_len = None
        self.name = None
        self.data_type = None

class Pdo:
    def __init__(self):
        self.type = None
        self.name = None
        self.Index = None
        self.entries = None

class Slave:
    def __init__(self):
        self.name = None
        self.tx_pdo = []
        self.rx_pdo = []

    def hasPdo(self):
        return len(self.tx_pdo) > 0 or len(self.rx_pdo) > 0

def eprint(s):
    sys.stderr.write(s + '\n')
    sys.stderr.flush()

def parsePdo(pdo):
    p = Pdo()

    if pdo.nodeName == "TxPdo":
        p.type = "tx"
    elif pdo.nodeName == "RxPdo":
        p.type = "rx"
    else:
        raise Exception("wrong pdo type: " + pdo.nodeName)

    Index = pdo.getElementsByTagName("Index")
    p.index = Index[0].childNodes[0].data
    Name = pdo.getElementsByTagName("Name")
    p.name = Name[0].childNodes[0].data

    entries = pdo.getElementsByTagName("Entry")
    p.entries = []
    for e in entries:
        ent = PdoEntry()
        ent.index = e.getElementsByTagName("Index")[0].childNodes[0].data
        if len(e.getElementsByTagName("SubIndex")) > 0:
            ent.subindex = e.getElementsByTagName("SubIndex")[0].childNodes[0].data
        ent.bit_len = e.getElementsByTagName("BitLen")[0].childNodes[0].data
        if len(e.getElementsByTagName("Name")) > 0:
            ent.name = e.getElementsByTagName("Name")[0].childNodes[0].data
        if len(e.getElementsByTagName("DataType")) > 0:
            ent.data_type = e.getElementsByTagName("DataType")[0].childNodes[0].data
        p.entries.append(ent)
    return p
        
def parseSlave(slave):
    sl = Slave()
    Info = slave.getElementsByTagName("Info")
    if len(Info) == 0:
        sl.name = "UNKNOWN"
    elif len(Info[0].getElementsByTagName("Name")) == 0:
        sl.name = "UNKNOWN"
    else:
        Name = Info[0].getElementsByTagName("Name")[0]
        sl.name = Name.childNodes[0].data

    ProcessData = slave.getElementsByTagName("ProcessData")
    if len(ProcessData) > 0:
        TxPdo = ProcessData[0].getElementsByTagName("TxPdo")
        for pdo in TxPdo:
            p = parsePdo(pdo)
            sl.tx_pdo.append(p)

        RxPdo = ProcessData[0].getElementsByTagName("RxPdo")
        for pdo in RxPdo:
            p = parsePdo(pdo)
            sl.rx_pdo.append(p)
    return sl

def recursiveProcessImage(variables, idx, indent, s):
    if len(variables) == 0:
        return

    indent_str = ""
    for i in range(indent):
        indent_str += " "

    vs = copy.copy(variables)
    while len(vs) > 0:
        dot = vs[0].Name.find(".", idx)
        if dot < 0:
            name = vs[0].Name[idx:]
        else:
            name = vs[0].Name[idx:dot]
        entries = []
        for i in reversed(range(len(vs))):
            if vs[i].Name[idx:].startswith(name):
                entries.append(vs[i])
                del vs[i]
        s.write("\n" + indent_str + "# name: " + name + "\n")
        for e in entries:
            s.write(indent_str + "# " + e.Name[dot+1:] + " BitSize: " + str(e.BitSize) + " BitOffs: " + str(e.BitOffs) + "\n" )

        if dot >= 0:
            recursiveProcessImage(entries, dot+1, indent+1, s)


def generate_boost_serialization(package, ec_config_file, msg_output_dir):
    """
    Generate a boost::serialization header

    @param msg_path: The path to the .msg file
    @type msg_path: str
    """

    eprint("generating Test.msg")

    # Try to make the directory, but silently continue if it already exists
    try:
        os.makedirs(msg_output_dir)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

    dom = minidom.parse(ec_config_file)

    EtherCATConfig = dom.getElementsByTagName("EtherCATConfig")

    Config = EtherCATConfig[0].getElementsByTagName("Config")

    SlavesXml = Config[0].getElementsByTagName("Slave")
    slave_list = []
    for slave in SlavesXml:
        sl = parseSlave(slave)
        slave_list.append(sl)

    ProcessImageXml = Config[0].getElementsByTagName("ProcessImage")
    pi = parseProcessImage( ProcessImageXml[0] )
    
#    mcd = dom.getElementsByTagName("mcd")
#    if len(mcd) != 1:
#        return (ss_history, ret_period)

#        eprint("slave " + sl.name)

    map_data_types = {
        "BIT"   : "bool",
        "SINT"  : "int8",
        "USINT" : "uint8",
        "INT"   : "int16",
        "UINT"  : "uint16",
        "DINT"  : "int32",
        "UDINT" : "uint32"}

    for sl in slave_list:
        if not sl.hasPdo():
            continue

        s = StringIO()
        s.write("# autogenerated by rtt_subsystem_ports/create_msgs_from_ec_config.py\n")
        s.write("# do not modify this file\n\n")

        s.write("# slave '" + sl.name + "'\n")
        for tx in sl.tx_pdo:
            s.write("\n#\n#    TX PDO: '" + tx.name + "'\n#\n")
            for e in tx.entries:
                name = e.name
                if not name:
                    name = "unnamed"
                data_type = e.data_type
                if not data_type:
                    data_type = "unknown"
                s.write("# index: " + str(e.index) + ", name: '" + name + "', type: " + data_type + "\n")
                if data_type in map_data_types:
                    s.write( map_data_types[data_type] + " " + (''.join(ch for ch in name if ch.isalnum())) + "\n\n" )
                else:
                    s.write( "# strange datatype: " + data_type + "\n\n" )

        for rx in sl.rx_pdo:
            s.write("#    RX PDO: '" + rx.name + "'\n")
            for e in rx.entries:
                name = e.name
                if not name:
                    name = "unnamed"
                data_type = e.data_type
                if not data_type:
                    data_type = "unknown"
                s.write("# index: " + str(e.index) + ", name: '" + name + "', type: " + data_type + "\n")
        s.write("\n")

        msg_name = ''.join(ch for ch in sl.name if ch.isalnum())

        output_msg = msg_output_dir + "/" + msg_name

        (output_dir,filename) = os.path.split(output_msg)
        try:
            os.makedirs(output_dir)
        except OSError, e:
            pass

        f = open(output_msg, 'w')
        print >> f, s.getvalue()

        s.close()


    s = StringIO()
    s.write("# autogenerated by rtt_subsystem_ports/create_msgs_from_ec_config.py\n")
    s.write("# do not modify this file\n\n")

    s.write("#\n# inputs byteSize: " + str(pi.Inputs.ByteSize) + "\n#\n\n")

    recursiveProcessImage(pi.Inputs.variables, 0, 0, s)

#    vs = copy.copy(pi.Inputs.variables)
#    while len(vs) > 0:
#        dot = vs[0].Name.find(".")
#        name = vs[0].Name[:dot]
#        entries = []
#        for i in reversed(range(len(vs))):
#            if vs[i].Name.startswith(name):
#                entries.append(vs[i])
#                del vs[i]
#        s.write("\n# name: " + name + "\n")
#        for e in entries:
#            s.write("# " + e.Name[dot:] + " BitSize: " + str(e.BitSize) + " BitOffs: " + str(e.BitOffs) + "\n" )


#    for v in pi.Inputs.variables:
#        s.write("# " + v.Name + " BitSize: " + str(v.BitSize) + " BitOffs: " + str(v.BitOffs) + "\n" )
#        v.Comment
#        v.DataType

    s.write("#\n# outputs byteSize: " + str(pi.Outputs.ByteSize) + "\n#\n\n")
    for v in pi.Outputs.variables:
        s.write("# " + v.Name + " BitSize: " + str(v.BitSize) + " BitOffs: " + str(v.BitOffs) + "\n" )

    msg_name = "Test.msg"

    output_msg = msg_output_dir + "/" + msg_name

    (output_dir,filename) = os.path.split(output_msg)
    try:
        os.makedirs(output_dir)
    except OSError, e:
        pass

    f = open(output_msg, 'w')
    print >> f, s.getvalue()

    s.close()


def create_boost_headers(argv, stdout, stderr):
    parser = argparse.ArgumentParser(description='Generate boost serialization header for ROS message.')
    parser.add_argument('pkg',metavar='PKG',type=str, nargs=1,help='The package name.')
    parser.add_argument('ec_config_file',metavar='EC_CONF',type=str, nargs=1,help='EC definition file.')
    parser.add_argument('msg_output_dir',metavar='MSG_OUT',type=str, nargs=1,help='msg destination dir.')

    args = parser.parse_args()

    print args.pkg[0], args.ec_config_file[0], args.msg_output_dir[0]

    generate_boost_serialization(args.pkg[0], args.ec_config_file[0], args.msg_output_dir[0])

if __name__ == "__main__":
    try:
        create_boost_headers(sys.argv, sys.stdout, sys.stderr)
    except Exception, e:
        sys.stderr.write("Failed to generate boost headers: " + str(e))
        raise
        #sys.exit(1)

