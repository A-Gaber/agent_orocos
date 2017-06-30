#!/usr/bin/python
import sys

import roslib

import gencpp
import genmsg

from  roslib import packages,msgs
import os

from cStringIO import StringIO

import argparse

import parse_subsystem_xml

def generate_boost_serialization(package, port_def, output_cpp):
    """
    Generate a boost::serialization header

    @param msg_path: The path to the .msg file
    @type msg_path: str
    """
    mc = genmsg.msg_loader.MsgContext()

    with open(port_def, 'r') as f:
        read_data = f.read()

    sd = parse_subsystem_xml.parseSubsystemXml(read_data)

    s = StringIO()
    s.write("// autogenerated by rtt_subsystem/create_subsystem_input_buffers.py\n")
    s.write("// do not modify this file\n\n")

#    s.write("#include \"common_behavior/input_data.h\"\n")
#    s.write("#include \"common_behavior/abstract_behavior.h\"\n")
#    s.write("#include \"common_behavior/abstract_predicate_list.h\"\n\n")

    for p_in in sd.buffers_in:
        s.write("#include \"" + p_in.type_pkg + "/" + p_in.type_name + ".h\"\n")

    for p in sd.buffers_in:
        if p.converter:
            s.write("#include <common_interfaces/abstract_buffer_converter.h>\n")
            break

    s.write("#include <shm_comm/shm_channel.h>\n")
    s.write("#include <vector>\n")
    s.write("#include <string>\n")
    s.write("#include <rtt/RTT.hpp>\n")
    s.write("#include <rtt/Logger.hpp>\n")
    s.write("#include <rtt/Component.hpp>\n")
    s.write("#include <rtt_rosclock/rtt_rosclock.h>\n")
    s.write("#include <ros/param.h>\n\n")
    s.write("#include \"" + package + "/master.h\"\n")

    s.write("using namespace RTT;\n\n")

    s.write("\nnamespace " + package + "_types {\n\n")

    components_counter = 0
    for rb in sd.trigger_methods.read_buffers:
        class_name = "InputBuffers" + str(components_counter)
        s.write("class " + class_name + ": public RTT::TaskContext {\n")
        s.write("public:\n")
        s.write("    explicit " + class_name + "(const std::string& name)\n")
        s.write("        : TaskContext(name, PreOperational)\n")
        s.write("        , port_msg_out_(\"msg_OUTPORT\")\n")

        all_buffers = rb.obligatory + rb.optional

        for buf_name in all_buffers:
            s.write("        , buf_prev_" + buf_name + "_(NULL)\n")
#            s.write("        , port_" + buf_name + "_out_(\"" + buf_name + "_OUTPORT\")\n")

        s.write("    {\n")
        s.write("        this->ports()->addPort(port_msg_out_);\n")
        for buf_name in all_buffers:
#            s.write("        this->ports()->addPort(port_" + buf_name + "_out_);\n")
            s.write("        addProperty(\"channel_name_" + buf_name + "\", channel_name_" + buf_name + "_);\n")

        s.write("        this->addOperation(\"getDiag\", &" + class_name + "::getDiag, this, RTT::ClientThread);\n")

        s.write("        use_sim_time_ = false;\n")
        s.write("        ros::param::get(\"/use_sim_time\", use_sim_time_);\n")
        s.write("        if (use_sim_time_) {\n")
        s.write("            first_timeout_ = " + str(rb.first_timeout_sim) + ";\n")
        s.write("        }\n")
        s.write("        else {\n")
        s.write("            first_timeout_ = " + str(rb.first_timeout) + ";\n")
        s.write("        }\n")

        s.write("    }\n\n")
        s.write("    // this method in not RT-safe\n")
        s.write("    std::string getDiag() {\n")
        s.write("        std::stringstream ss;\n")
#TODO: diagnostics
        s.write("        return ss.str();\n")
        s.write("    }\n\n")

        s.write("    bool configureHook() {\n")
        s.write("        Logger::In in(\"" + package + "::" + class_name + "::configureHook\");\n")

        s.write("        int result = 0;\n")

        for buf_name in all_buffers:
            buf_in = None
            for b in sd.buffers_in:
                if b.alias == buf_name:
                    buf_in = b
                    break
            if not buf_in:
                raise Exception('buffer not found', 'buffer specified in trigger methods <read_data>: \'' + buf_name + '\' could not be found in defined buffers')

            if buf_in.converter:
                s.write("        converter_" + buf_name + "_ = common_interfaces::BufferConverterFactory<" + buf_in.getTypeCpp() + " >::Instance()->Create(\"" + buf_in.converter + "\");\n")
                s.write("        if (!converter_" + buf_name + "_) {\n")
                s.write("            Logger::log() << Logger::Error << \"could not find buffer data converter '" + buf_in.converter + "'\" << Logger::endl;\n")
                s.write("            return false;\n")
                s.write("        }\n")
                s.write("        Logger::log() << Logger::Info << \"using data converter '" + buf_in.converter + "' for buffer '" + buf_name + "'\" << Logger::endl;\n")

            s.write("        if (channel_name_" + buf_name + "_.empty()) {\n")
            s.write("            Logger::log() << Logger::Error << \"parameter \'channel_name_" + buf_name + "\' is empty\" << Logger::endl;\n")
            s.write("            return false;\n")
            s.write("        }\n")
            s.write("        Logger::log() << Logger::Info << \"using channel name '\" << channel_name_" + buf_name + "_ << \"' for buffer '" + buf_name + "'\" << Logger::endl;\n")

#            s.write("        if (event_) {\n")
#            s.write("            if (period_min_ == 0.0) {\n")
#            s.write("                Logger::log() << Logger::Error << "parameter \'period_min\' is not set (0.0)" << Logger::endl;\n")
#            s.write("                return false;\n")
#            s.write("            }\n")
#            s.write("        }\n")
#            s.write("        if (event_no_data_) {\n")
#            s.write("            if (next_timeout_ == 0.0) {\n")
#            s.write("                Logger::log() << Logger::Error << "parameter \'next_timeout\' is not set (0.0)" << Logger::endl;\n")
#            s.write("                return false;\n")
#            s.write("            }\n")
#            s.write("            if (first_timeout_ == 0.0) {\n")
#            s.write("                Logger::log() << Logger::Error << "parameter \'first_timeout\' is not set (0.0)" << Logger::endl;\n")
#            s.write("                return false;\n")
#            s.write("            }\n")

#            s.write("            if (period_min_ > next_timeout_) {\n")
#            s.write("                Logger::log() << Logger::Error << "parameter \'period_min\' should be <= than \'next_timeout\': " << period_min_ << ", " << next_timeout_ << Logger::endl;\n")
#            s.write("                return false;\n")
#            s.write("            }\n")
#            s.write("            if (next_timeout_ >= first_timeout_) {\n")
#            s.write("                Logger::log() << Logger::Error << "parameter \'next_timeout\' should be < than \'first_timeout\': " << next_timeout_ << ", " << first_timeout_ << Logger::endl;\n")
#            s.write("                return false;\n")
#            s.write("            }\n")
#            s.write("        }\n")

#            s.write("        Logger::log() << Logger::Info << "parameter channel_name is set to: \'" << channel_name_" + buf_name + "_ << "\'" << Logger::endl;\n")
#            s.write("        Logger::log() << Logger::Info << "parameter event is set to: \'" << (event_?"true":"false") << Logger::endl;\n")
#            s.write("        Logger::log() << Logger::Info << "parameter event_no_data is set to: \'" << (event_no_data_?"true":"false") << Logger::endl;\n")
#            s.write("        Logger::log() << Logger::Info << "parameter \'period_min\' is set to: " << period_min_ << Logger::endl;\n")
#            s.write("        Logger::log() << Logger::Info << "parameter \'next_timeout\' is set to: " << next_timeout_ << Logger::endl;\n")
#            s.write("        Logger::log() << Logger::Info << "parameter \'first_timeout\' is set to: " << first_timeout_ << Logger::endl;\n")

            s.write("        bool create_channel_" + buf_name + " = false;\n")

            s.write("        Logger::log() << Logger::Info << \"trying to connect to channel\" << Logger::endl;\n")
            s.write("        result = shm_connect_reader(channel_name_" + buf_name + "_.c_str(), &re_" + buf_name + "_);\n")
            s.write("        if (result == SHM_INVAL) {\n")
            s.write("            Logger::log() << Logger::Error << \"shm_connect_reader('" + buf_name + "'): invalid parameters\" << Logger::endl;\n")
            s.write("            return false;\n")
            s.write("        }\n")
            s.write("        else if (result == SHM_FATAL) {\n")
            s.write("            Logger::log() << Logger::Error << \"shm_connect_reader('" + buf_name + "'): memory error\" << Logger::endl;\n")
            s.write("            return false;\n")
            s.write("        }\n")
            s.write("        else if (result == SHM_NO_CHANNEL) {\n")
            s.write("            Logger::log() << Logger::Warning << \"shm_connect_reader('" + buf_name + "'): could not open shm object, trying to initialize the channel...\" << Logger::endl;\n")
            s.write("            create_channel_" + buf_name + " = true;\n")
            s.write("        }\n")
            s.write("        else if (result == SHM_CHANNEL_INCONSISTENT) {\n")
            s.write("            Logger::log() << Logger::Warning << \"shm_connect_reader('" + buf_name + "'): shm channel is inconsistent, trying to initialize the channel...\" << Logger::endl;\n")
            s.write("            create_channel_" + buf_name + " = true;\n")
            s.write("        }\n")
            s.write("        else if (result == SHM_ERR_INIT) {\n")
            s.write("            Logger::log() << Logger::Error << \"shm_connect_reader('" + buf_name + "'): could not initialize channel\" << Logger::endl;\n")
            s.write("            return false;\n")
            s.write("        }\n")
            s.write("        else if (result == SHM_ERR_CREATE) {\n")
            s.write("            Logger::log() << Logger::Warning << \"shm_connect_reader('" + buf_name + "'): could not create reader\" << Logger::endl;\n")
            s.write("            create_channel_" + buf_name + " = true;\n")
            s.write("        }\n")

            s.write("        if (!create_channel_" + buf_name + ") {\n")
            s.write("            Logger::log() << Logger::Info << \"trying to read from channel\" << Logger::endl;\n")
            s.write("            void *pbuf = NULL;\n")
            s.write("            result = shm_reader_buffer_get(re_" + buf_name + "_, &pbuf);\n")
            s.write("            if (result < 0) {\n")
            s.write("                Logger::log() << Logger::Warning << \"shm_reader_buffer_get('" + buf_name + "'): error: \" << result << Logger::endl;\n")
            s.write("                create_channel_" + buf_name + " = true;\n")
            s.write("            }\n")
            s.write("        }\n")

            s.write("        if (create_channel_" + buf_name + ") {\n")
            s.write("            size_t data_size;\n")
            if buf_in.converter:
                s.write("            data_size = converter_" + buf_name + "_->getDataSize();\n")
            else:
                s.write("            data_size = sizeof(" + buf_in.getTypeCpp() + ");\n")
            s.write("            Logger::log() << Logger::Info << \"trying to create channel\" << Logger::endl;\n")
            s.write("            result = shm_create_channel(channel_name_" + buf_name + "_.c_str(), data_size, 1, true);\n")
            s.write("            if (result != 0) {\n")
            s.write("                Logger::log() << Logger::Error << \"create_shm_object('" + buf_name + "'): error: \" << result << \"   errno: \" << errno << Logger::endl;\n")
            s.write("                return false;\n")
            s.write("            }\n")

            s.write("            Logger::log() << Logger::Info << \"trying to connect to channel\" << Logger::endl;\n")
            s.write("            result = shm_connect_reader(channel_name_" + buf_name + "_.c_str(), &re_" + buf_name + "_);\n")
            s.write("            if (result != 0) {\n")
            s.write("                Logger::log() << Logger::Error << \"shm_connect_reader('" + buf_name + "'): error: \" << result << Logger::endl;\n")
            s.write("                return false;\n")
            s.write("            }\n")
            s.write("        }\n")
        s.write("        Logger::log() << Logger::Info << \"configure ok\" << Logger::endl;\n")
        s.write("        return true;\n")
        s.write("    }\n\n")

        s.write("    void cleanupHook() {\n")
        for buf_name in all_buffers:
            s.write("        shm_release_reader(re_" + buf_name + "_);\n")
        s.write("    }\n\n")

        s.write("    void stopHook() {\n")
        s.write("    }\n\n")

        s.write("    bool startHook() {\n")
#        s.write("        Logger::log() << Logger::Info << getName() << \" startHook a\" << Logger::endl;\n")
        s.write("        time_last_s_ = rtt_rosclock::host_now();     // save last write time\n")
        s.write("        int result = 0;\n")
        s.write("        void *pbuf = NULL;\n")
        for buf_name in all_buffers:
            s.write("        result = shm_reader_buffer_get(re_" + buf_name + "_, &pbuf);\n")
            s.write("        if (result < 0) {\n")
            s.write("            Logger::In in(\"" + package + "::" + class_name + "::startHook\");\n")
            s.write("            Logger::log() << Logger::Error << \"shm_reader_buffer_get('" + buf_name + "'): error: \" << result << Logger::endl;\n")
            s.write("            return false;\n")
            s.write("        }\n")
            s.write("        buf_prev_" + buf_name + "_ = pbuf;\n")

#        s.write("        diag_buf_valid_ = false;\n")
        s.write("        trigger();\n")

        s.write("        last_read_successful_ = false;\n")

#        s.write("        Logger::log() << Logger::Info << getName() << \" startHook b\" << Logger::endl;\n")
        s.write("        return true;\n")
        s.write("    }\n")

        s.write("    void updateHook() {\n")
#        s.write("        Logger::log() << Logger::Info << getName() << \" updateHook a\" << Logger::endl;\n")
        s.write("        void *pbuf = NULL;\n")
        s.write("        bool all_obligatory_reads_successful = true;\n")
        s.write("        " + package + "_types::InputData" + str(components_counter) + " buf = " + package + "_types::InputData" + str(components_counter) + "();\n")
        s.write("        double timeout_base_s, timeout_s;\n")
        s.write("        if (last_read_successful_) {\n")
        s.write("            timeout_base_s = first_timeout_;\n")
        s.write("        }\n")
        s.write("        else {\n")
        s.write("            timeout_base_s = " + str(rb.next_timeout) + ";\n")
        s.write("        }\n")
        s.write("        int read_status;\n")
        s.write("        timespec ts;\n")

        for buf_name in rb.obligatory:
            buf_in = None
            for b in sd.buffers_in:
                if b.alias == buf_name:
                    buf_in = b
                    break
            if not buf_in:
                raise Exception('buffer not found', 'buffer specified in trigger methods <read_data>: \'' + buf_name + '\' could not be found in defined buffers')

            s.write("        timeout_s = timeout_base_s - (rtt_rosclock::host_now() - time_last_s_).toSec();\n")

            s.write("        read_status = -1;\n")
            s.write("        if (timeout_s > 0) {\n")
            s.write("            clock_gettime(CLOCK_REALTIME, &ts);\n")
            s.write("            int timeout_sec = (int)timeout_s;\n")
            s.write("            int timeout_nsec = (int)((timeout_s - (double)timeout_sec) * 1000000000.0);\n")

            s.write("            ts.tv_sec += timeout_sec;\n")
            s.write("            ts.tv_nsec += timeout_nsec;\n")
            s.write("            if (ts.tv_nsec >= 1000000000) {\n")
            s.write("                ts.tv_nsec -= 1000000000;\n")
            s.write("                ++ts.tv_sec;\n")
            s.write("            }\n")

            s.write("            read_status = shm_reader_buffer_timedwait(re_" + buf_name + "_, &ts, &pbuf);\n")
            s.write("        }\n")
            s.write("        else {\n")
            s.write("            read_status = shm_reader_buffer_get(re_" + buf_name + "_, &pbuf);\n")
            s.write("        }\n")

            s.write("        if (read_status == SHM_TIMEOUT) {\n")
            s.write("            all_obligatory_reads_successful = false;\n")
            s.write("            buf." + buf_name + "_valid = false;\n")
#            s.write("            Logger::log() << Logger::Info << getName() << \" shm_reader_buffer_timedwait('" + buf_name + "') timeout\" << Logger::endl;\n")
            s.write("        }\n")
            s.write("        else if (read_status == 0 && pbuf != buf_prev_" + buf_name + "_) {\n")
            s.write("            buf_prev_" + buf_name + "_ = pbuf;\n")
            if buf_in.converter:
                s.write("            converter_" + buf_name + "_->convertToMsg(reinterpret_cast<const uint8_t* >(pbuf), buf." + buf_name + ");\n")
            else:
                s.write("            buf." + buf_name + " = *reinterpret_cast<" + buf_in.type_pkg + "::" + buf_in.type_name + "* >(pbuf);\n")
            s.write("            buf." + buf_name + "_valid = true;\n")
#            s.write("            Logger::log() << Logger::Info << getName() << \" shm_reader_buffer_timedwait('" + buf_name + "') read\" << Logger::endl;\n")
            s.write("        }\n")
            s.write("        else if (read_status > 0) {\n")
            s.write("            all_obligatory_reads_successful = false;\n")
            s.write("            buf." + buf_name + "_valid = false;\n")
#            s.write("            Logger::log() << Logger::Info << getName() << \" shm_reader_buffer_timedwait('" + buf_name + "') status: \" << read_status << Logger::endl;\n")
            s.write("        }\n")
            s.write("        else {\n")
            s.write("            buf." + buf_name + "_valid = false;\n")
            s.write("            Logger::log() << Logger::Error << getName() << \" shm_reader_buffer_timedwait('" + buf_name + "') status: \" << read_status << Logger::endl;\n")
            s.write("            error();\n")
            s.write("            return;\n")
            s.write("        }\n")


        for buf_name in rb.optional:
            buf_in = None
            for b in sd.buffers_in:
                if b.alias == buf_name:
                    buf_in = b
                    break
            if not buf_in:
                raise Exception('buffer not found', 'buffer specified in trigger methods <read_data>: \'' + buf_name + '\' could not be found in defined buffers')

            s.write("        read_status = shm_reader_buffer_get(re_" + buf_name + "_, &pbuf);\n")

            s.write("        if (read_status == 0 && pbuf != buf_prev_" + buf_name + "_) {\n")
            s.write("            buf_prev_" + buf_name + "_ = pbuf;\n")
            if buf_in.converter:
                s.write("            converter_" + buf_name + "_->convertToMsg(reinterpret_cast<const uint8_t* >(pbuf), buf." + buf_name + ");\n")
            else:
                s.write("            buf." + buf_name + " = *reinterpret_cast<" + buf_in.type_pkg + "::" + buf_in.type_name + "* >(pbuf);\n")
            s.write("            buf." + buf_name + "_valid = true;\n")
            s.write("        }\n")
            s.write("        else if (read_status > 0) {\n")
            s.write("            buf." + buf_name + "_valid = false;\n")
            s.write("        }\n")
            s.write("        else {\n")
            s.write("            buf." + buf_name + "_valid = false;\n")
            s.write("            Logger::log() << Logger::Error << getName() << \" shm_reader_buffer_timedwait('" + buf_name + "') status: \" << read_status << Logger::endl;\n")
            s.write("            error();\n")
            s.write("            return;\n")
            s.write("        }\n")

#        s.write("        Logger::log() << Logger::Info << getName() << \" writing with status: \" << (all_obligatory_reads_successful?\"true\":\"false\") << Logger::endl;\n")
        s.write("        last_read_successful_ = all_obligatory_reads_successful;\n")
        s.write("        port_msg_out_.write(buf);\n")
        s.write("        timeout_s = " + str(rb.min_period) + " - (rtt_rosclock::host_now() - time_last_s_).toSec();  // calculate sleep time\n")
        s.write("        if (timeout_s > 0) {\n")
        s.write("            usleep( static_cast<int >((timeout_s)*1000000.0) );\n")
        s.write("        }\n")
#        s.write("        if (use_sim_time_) {\n")
#        s.write("            timeout_s = " + str(rb.min_period) + " - (rtt_rosclock::host_now() - time_last_s_).toSec();  // calculate sleep time\n")
#        s.write("            while (timeout_s > 0.0001) {\n")
#        s.write("                usleep( static_cast<int >((timeout_s)*1000000.0) );\n")
#        s.write("                timeout_s = " + str(rb.min_period) + " - (rtt_rosclock::host_now() - time_last_s_).toSec();  // calculate sleep time\n")
#        s.write("            }\n")
#        s.write("        }\n")
        s.write("        time_last_s_ = rtt_rosclock::host_now();     // save last write time\n")

        s.write("        trigger();\n")

        s.write("    }\n\n")

        s.write("private:\n")

        s.write("    // properties\n")
        for buf_name in all_buffers:
            buf_in = None
            for b in sd.buffers_in:
                if b.alias == buf_name:
                    buf_in = b
                    break
            if not buf_in:
                raise Exception('buffer not found', 'buffer specified in trigger methods <read_data>: \'' + buf_name + '\' could not be found in defined buffers')

            s.write("    std::string channel_name_" + buf_name + "_;\n")
            s.write("    shm_reader_t* re_" + buf_name + "_;\n")
            s.write("    void *buf_prev_" + buf_name + "_;\n")

            if buf_in.converter:
                s.write("    shared_ptr<common_interfaces::BufferConverter<" + buf_in.getTypeCpp() + " > >converter_" + buf_name + "_;\n")

        s.write("    RTT::OutputPort<" + package + "_types::InputData" + str(components_counter) + " > port_msg_out_;\n")
        s.write("    double first_timeout_;\n")
        s.write("    bool last_read_successful_;\n")
        s.write("    ros::Time time_last_s_;\n")
        s.write("    bool use_sim_time_;\n")
        s.write("};\n\n")

        components_counter = components_counter + 1


    s.write("};  // namespace " + package + "_types\n\n")

    components_counter = 0
    for rb in sd.trigger_methods.read_buffers:
        class_name = "InputBuffers" + str(components_counter)
        s.write("ORO_LIST_COMPONENT_TYPE(" + package + "_types::" + class_name + ")\n")

    (output_dir,filename) = os.path.split(output_cpp)
    try:
        os.makedirs(output_dir)
    except OSError, e:
        pass

    f = open(output_cpp, 'w')
    print >> f, s.getvalue()

    s.close()


def create_boost_headers(argv, stdout, stderr):
    parser = argparse.ArgumentParser(description='Generate boost serialization header for ROS message.')
    parser.add_argument('pkg',metavar='PKG',type=str, nargs=1,help='The package name.')
    parser.add_argument('port_def',metavar='PORT_DEF',type=str, nargs=1,help='Port definition file.')
    parser.add_argument('output_cpp',metavar='OUTPUT_CPP',type=str, nargs=1,help='Output cpp file.')

    args = parser.parse_args()

    print args.pkg[0], args.port_def[0], args.output_cpp[0]

    generate_boost_serialization(args.pkg[0], args.port_def[0], args.output_cpp[0])

if __name__ == "__main__":
    try:
        create_boost_headers(sys.argv, sys.stdout, sys.stderr)
    except Exception, e:
        sys.stderr.write("Failed to generate boost headers: " + str(e))
        raise
        #sys.exit(1)
