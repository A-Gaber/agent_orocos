#!/usr/bin/python
import sys
import copy

import roslib

import gencpp
import genmsg

from  roslib import packages,msgs
import os

from cStringIO import StringIO

import argparse

import parse_subsystem_xml

def logicExprToCpp(expr, predicates):
    cpp = expr

    predicates_copy = copy.copy(predicates)
    predicates_copy.append("IN_ERROR")
    predicates_copy.append("TRUE")
    predicates_copy.append("FALSE")
    predicates_copy.append("CURRENT_BEHAVIOR_OK")

#    for st in states:
#        predicates_copy.append("PREV_STATE_" + st.name)
    predicates_sorted = sorted(predicates_copy, key=lambda pred: -len(pred))

    pred_id_map = {}
    id_pred_map = {}
    count = 0
    for pred in predicates_sorted:
        pred_id = "{" + str(count) + "}"
        pred_id_map[pred] = pred_id
        id_pred_map[pred_id] = pred
        count = count + 1

    # find all predicates
    for pred in predicates_sorted:
        cpp = cpp.replace(pred, pred_id_map[pred])

    # find all 'not'
    idx = 0
    while True:
        idx = cpp.find("not", idx)
        if idx == -1:
            break

        if idx + 3 >= len(cpp):
            raise Exception('invalid expression', 'invalid logic expression syntax, character ' + idx + ", expr: '" + cpp + "'")

        if (idx == 0 or cpp[idx-1].isspace() or cpp[idx-1] == '(') and cpp[idx+3].isspace():
            cpp = cpp[:idx] + '!' + cpp[idx+3:]
            idx = idx + 1
        else:
            idx = idx + 3

    # find all 'and'
    idx = 0
    while True:
        idx = cpp.find("and", idx)
        if idx == -1:
            break

        if idx + 3 >= len(cpp) or idx == 0:
            raise Exception('invalid expression', 'invalid logic expression syntax, character ' + idx + ", expr: '" + cpp + "'")

        if cpp[idx-1].isspace() and cpp[idx+3].isspace():
            cpp = cpp[:idx] + '&&' + cpp[idx+3:]
            idx = idx + 2
        else:
            idx = idx + 3

    # find all 'or'
    idx = 0
    while True:
        idx = cpp.find("or", idx)
        if idx == -1:
            break

        if idx + 2 >= len(cpp) or idx == 0:
            raise Exception('invalid expression', 'invalid logic expression syntax, character ' + idx + ", expr: '" + cpp + "'")

        if cpp[idx-1].isspace() and cpp[idx+2].isspace():
            cpp = cpp[:idx] + '||' + cpp[idx+2:]
            idx = idx + 2
        else:
            idx = idx + 2

    # find all predicates
    for pred in predicates_sorted:
        if pred == 'TRUE':
            cpp = cpp.replace(pred_id_map[pred], "true")
        elif pred == 'FALSE':
            cpp = cpp.replace(pred_id_map[pred], "false")
        else:
            cpp = cpp.replace(pred_id_map[pred], "p->" + pred)

    return cpp

def eprint(s):
    sys.stderr.write(s + '\n')
    sys.stderr.flush()

def generate_boost_serialization(package, port_def, output_cpp):
    """
    Generate a boost::serialization header

    @param msg_path: The path to the .msg file
    @type msg_path: str
    """
    mc = genmsg.msg_loader.MsgContext()

#    spec = genmsg.msg_loader.load_msg_from_file(mc, msg_path, msg_type)
#    cpp_prefix = '%s::'%(package)

    with open(port_def, 'r') as f:
        read_data = f.read()

    sd = parse_subsystem_xml.parseSubsystemXml(read_data)

#    eprint("generating master.cpp")

    s = StringIO()
    s.write("// autogenerated by rtt_subsystem_ports/create_master_h.py\n")
    s.write("// do not modify this file\n\n")
    s.write("#include <rtt/plugin/ServicePlugin.hpp>\n")
    s.write("#include <rtt/extras/PeriodicActivity.hpp>\n")
    s.write("#include \"rtt/Logger.hpp\"\n")
    s.write("#include <rtt/base/DataObjectLockFree.hpp>\n")
    s.write("#include <ros/param.h>\n")
    s.write("#include <rtt_rosclock/rtt_rosclock.h>\n")


    s.write("#include \"common_behavior/master_service.h\"\n")
    s.write("#include \"" + package + "/master.h\"\n")
    s.write("#include \"common_behavior/abstract_state.h\"\n")


    s.write("\nnamespace " + package + "_types {\n\n")

    #
    # _Master
    #
    s.write("class " + package + "_Master : public common_behavior::MasterService {\n")
    s.write("public:\n")
    s.write("    explicit " + package + "_Master(RTT::TaskContext* owner)\n")
    s.write("        : common_behavior::MasterService(owner)\n")
    s.write("        , owner_(owner)\n")
    if sd.trigger_methods.onNoData():
        s.write("        , port_no_data_trigger_in__(\"no_data_trigger_INPORT_\")\n")
    s.write("    {\n")

    for p_in in sd.buffers_in:
# TODO: verify this
        if sd.trigger_methods.onNewData(p_in.alias):
            s.write("        owner_->addEventPort(\"" + p_in.alias + "_INPORT\", port_" + p_in.alias + "_in_);\n")
        else:
            s.write("        owner_->addPort(\"" + p_in.alias + "_INPORT\", port_" + p_in.alias + "_in_);\n")
        s.write("        owner_->addPort(\"" + p_in.alias + "_OUTPORT\", port_" + p_in.alias + "_out_);\n\n")

    if sd.trigger_methods.onNoData():
        s.write("\n        owner_->addEventPort(port_no_data_trigger_in__);\n")

    s.write("        bool use_sim_time = false;\n")
    s.write("        ros::param::get(\"/use_sim_time\", use_sim_time);\n")
    s.write("        if (use_sim_time) {\n")
#        s.write("        bool use_sim_time = false;\n")
#        s.write("        ros::param::get(\"/use_sim_time\", use_sim_time);\n")
#        s.write("        if (use_sim_time) {\n")
    if sd.trigger_gazebo:
        s.write("            if (!boost::dynamic_pointer_cast<RTT::internal::GlobalService >(RTT::internal::GlobalService::Instance())->require(\"gazebo_rtt_service\")) {\n")
        s.write("                RTT::Logger::log() << RTT::Logger::Error << \"could not load service 'gazebo_rtt_service'\" << RTT::Logger::endl;\n")
        s.write("            }\n")
        s.write("            else {\n")
        s.write("                RTT::Service::shared_ptr gazebo_rtt_service = RTT::internal::GlobalService::Instance()->getService(\"gazebo_rtt_service\");\n")
        s.write("                RTT::OperationInterfacePart *singleStepOp = gazebo_rtt_service->getOperation(\"singleStep\");\n")
        s.write("                if (singleStepOp == NULL) {\n")
        s.write("                    RTT::Logger::log() << RTT::Logger::Error << \"the service \" << gazebo_rtt_service->getName() << \" has no matching operation singleStep\" << RTT::Logger::endl;\n")
        s.write("                }\n")
        s.write("                else {\n")
        s.write("                    singleStep_ =  RTT::OperationCaller<void()>(singleStepOp);\n")
        s.write("                }\n")
        s.write("            }\n")
    s.write("            rtt_rosclock::disable_sim();\n")

    if sd.use_ros_sim_clock:
        s.write("            rtt_rosclock::use_ros_clock_topic();\n")

#        s.write("            RTT::Service::shared_ptr rosclock = RTT::internal::GlobalService::Instance()->getService(\"ros\")->getService(\"clock\");\n")
#
#        s.write("            RTT::Service::shared_ptr rosclock = RTT::internal::GlobalService::Instance()->getService(\"ros\")->getService(\"clock\");\n")
#        s.write("            if (!rosclock) {\n")
#        s.write("                RTT::Logger::log() << RTT::Logger::Error << \"could not get 'ros.clock' service\" << RTT::Logger::endl;\n")
#        s.write("            }\n")
#        s.write("            else {\n")
#        s.write("                RTT::OperationCaller<void()> useROSClockTopic = rosclock->getOperation(\"useROSClockTopic\");\n")
#        s.write("                if (!useROSClockTopic.ready()) {\n")
#        s.write("                    RTT::Logger::log() << RTT::Logger::Error << \"could not get 'useROSClockTopic' operation of 'ros.clock'\" << RTT::Logger::endl;\n")
#        s.write("                }\n")
#        s.write("                else {\n")
#        s.write("                    useROSClockTopic();\n")
#        s.write("                }\n")
#        s.write("            }\n")
    else:
        s.write("            rtt_rosclock::use_manual_clock();\n")

    s.write("            rtt_rosclock::enable_sim();\n")

    s.write("        }\n")

    if sd.trigger_methods.onPeriod():
        if sd.use_sim_clock:
            s.write("        if (use_sim_time) {\n")
            s.write("            owner->loadService(\"sim_clock_activity\");\n")
            s.write("        }\n")
        s.write("        owner->setPeriod(" + str(sd.trigger_methods.onPeriod().value) + ");\n")

    for pred in sd.predicates:
        s.write("       pred_" + pred + " = PredicateFactory::Instance()->getPredicate(\"" + package + "_types::" + pred + "\");\n")

    s.write("    }\n\n")

    s.write("    virtual ~" + package + "_Master() {\n")
    s.write("    }\n\n")

    s.write("    virtual void initBuffersData(common_behavior::InputDataPtr& in_data) const {\n")
    s.write("        boost::shared_ptr<InputData > in = boost::static_pointer_cast<InputData >(in_data);\n")
    for p_in in sd.buffers_in:
        s.write("        in->" + p_in.alias + " = " + p_in.getTypeCpp() + "();\n")
    s.write("    }\n\n")

    s.write("    virtual void readBuffers(common_behavior::InputDataPtr& in_data) {\n")
    s.write("        boost::shared_ptr<InputData > in = boost::static_pointer_cast<InputData >(in_data);\n")
    for p_in in sd.buffers_in:
#        no_data_max = 50
#        if p_in.event:
        no_data_max = 0
        s.write("        if (port_" + p_in.alias + "_in_.read(in->" + p_in.alias + ", false) != RTT::NewData) {\n")
        s.write("            if (" + p_in.alias + "_no_data_counter_ >= " + str(no_data_max) + ") {\n")
        s.write("                in->" + p_in.alias + " = " + p_in.getTypeCpp() + "();\n")
        s.write("            }\n")
        s.write("            else {\n")
        s.write("                " + p_in.alias + "_no_data_counter_++;\n")
        s.write("                in->" + p_in.alias + " = " + p_in.alias + "_prev_;\n")
        s.write("            }\n")
        s.write("        }\n")
        s.write("        else {\n")
        s.write("            " + p_in.alias + "_no_data_counter_ = 0;\n")
        s.write("            " + p_in.alias + "_prev_ = in->" + p_in.alias + ";\n")
        s.write("        }\n")
    s.write("    }\n\n")

    s.write("    virtual void writePorts(common_behavior::InputDataPtr& in_data) {\n")
    s.write("        boost::shared_ptr<InputData> in = boost::static_pointer_cast<InputData >(in_data);\n")
    for p_in in sd.buffers_in:
        s.write("        port_" + p_in.alias + "_out_.write(in->" + p_in.alias + ");\n")
    s.write("    }\n\n")

    s.write("    virtual common_behavior::InputDataPtr getDataSample() const {\n")
    s.write("        boost::shared_ptr<InputData > ptr(new InputData());\n")
    for p_in in sd.buffers_in:
        s.write("        ptr->" + p_in.alias + " = " + p_in.getTypeCpp() + "();\n")
    s.write("        return boost::static_pointer_cast<common_behavior::InputData >( ptr );\n")
    s.write("    }\n\n")

    s.write("    virtual void getLowerInputBuffers(std::vector<common_behavior::InputBufferInfo >& info) const {\n")
    s.write("        info = std::vector<common_behavior::InputBufferInfo >();\n")
    for p in sd.buffers_in:
        if p.side == 'bottom':
# TODO: verify this
            s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\", ")
            event = sd.trigger_methods.onNewData(p.alias)
            if event:
                s.write(" true, " + str(event.min) + ", ")
            else:
                s.write(" false, 0.0, ")
            no_data_event = sd.trigger_methods.onNoData(p.alias)
            if no_data_event:
                s.write(" true, " + str(no_data_event.first_timeout) + ", " + str(no_data_event.next_timeout) + ", " + str(no_data_event.first_timeout_sim))
            else:
                s.write(" false, 0.0, 0.0, 0.0")
            s.write("));\n")

#            if p.event:
#                s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\", true, " + str(p.period_min) + ", " + str(p.period_avg) + ", " + str(p.period_max) + ", " + str(p.period_sim_max) + "));\n")
#            else:
#                s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\"));\n")
#            s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\"));\n")
    s.write("    }\n\n")

    s.write("    virtual void getUpperInputBuffers(std::vector<common_behavior::InputBufferInfo >& info) const {\n")
    s.write("        info = std::vector<common_behavior::InputBufferInfo >();\n")

    if sd.trigger_methods.onNewData():
        for tm in sd.trigger_methods.onNewData():
            s.write("// " + tm.name + ", " + str(tm.min) + "\n")
            
    if sd.trigger_methods.onNoData():
        for tm in sd.trigger_methods.onNoData():
            s.write("// " + tm.name + ", " + str(tm.first_timeout) + ", " + str(tm.next_timeout) + ", " + str(tm.first_timeout_sim) + "\n")

    for p in sd.buffers_in:
        if p.side == 'top':
# TODO: verify this
            s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\", ")
            event = sd.trigger_methods.onNewData(p.alias)
            if event:
                s.write(" true, " + str(event.min) + ", ")
            else:
                s.write(" false, 0.0, ")
            no_data_event = sd.trigger_methods.onNoData(p.alias)
            if no_data_event:
                s.write(" true, " + str(no_data_event.first_timeout) + ", " + str(no_data_event.next_timeout) + ", " + str(no_data_event.first_timeout_sim))
            else:
                s.write(" false, 0.0, 0.0, 0.0")
            s.write("));\n")

#            if p.event:
#                s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\", true, " + str(p.period_min) + ", " + str(p.period_avg) + ", " + str(p.period_max) + ", " + str(p.period_sim_max) + "));\n")
#            else:
#                s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\"));\n")
#            s.write("        info.push_back(common_behavior::InputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\"));\n")
    s.write("    }\n\n")

    s.write("    virtual void getLowerOutputBuffers(std::vector<common_behavior::OutputBufferInfo >& info) const {\n")
    s.write("        info = std::vector<common_behavior::OutputBufferInfo >();\n")
    for p in sd.buffers_out:
        if p.side == 'bottom':
            s.write("        info.push_back(common_behavior::OutputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\"));\n")
    s.write("    }\n\n")

    s.write("    virtual void getUpperOutputBuffers(std::vector<common_behavior::OutputBufferInfo >& info) const {\n")
    s.write("        info = std::vector<common_behavior::OutputBufferInfo >();\n")
    for p in sd.buffers_out:
        if p.side == 'top':
            s.write("        info.push_back(common_behavior::OutputBufferInfo(\"" + p.getTypeStr() + "\", \"" + p.alias + "\"));\n")
    s.write("    }\n\n")

    s.write("    virtual std::vector<std::string > getBehaviors() const {\n")
    
    s.write("        return std::vector<std::string >({\n")
    for b in sd.behaviors:
        s.write("                   \"" + package + "_" + b.name + "\",\n")
    s.write("                   });\n")
    s.write("    }\n\n")

    s.write("    virtual std::vector<std::string > getStates() const {\n")
    
    s.write("        static const std::vector<std::string > states({\n")
    for st in sd.states:
        s.write("                   \"" + package + "_" + st.name + "\",\n")
    s.write("                   });\n")
    s.write("        return states;\n")
    s.write("    }\n\n")

    s.write("    virtual std::string getInitialState() const {\n")
    s.write("        static const std::string initial_state(\"" + package + "_" + sd.getInitialStateName() + "\");\n")
    s.write("        return initial_state;\n")
    s.write("    }\n\n")

    s.write("    virtual common_behavior::PredicateListPtr allocatePredicateList() {\n")
    for pred in sd.predicates:
        s.write("        if (!pred_" + pred + ") {\n")
        s.write("            return NULL;\n")
        s.write("        }\n")
    s.write("        PredicateListPtr ptr(new PredicateList());\n")
    s.write("        return boost::static_pointer_cast<common_behavior::PredicateList >( ptr );\n")
    s.write("    }\n\n")

    s.write("    virtual void calculatePredicates(const common_behavior::InputDataConstPtr& in_data, const std::vector<const RTT::TaskContext*>& components, common_behavior::PredicateListPtr& pred_list) const {\n")
    s.write("        PredicateListPtr p = boost::static_pointer_cast<PredicateList >( pred_list );\n")
    s.write("        InputDataConstPtr d = boost::static_pointer_cast<const InputData >( in_data );\n")
    for pred in sd.predicates:
#        s.write("        p->" + pred + " = pred_" + pred + "(d, components, prev_state_name);\n")
        s.write("        p->" + pred + " = pred_" + pred + "(d, components);\n")
    s.write("        p->IN_ERROR = false;\n")
    s.write("        p->CURRENT_BEHAVIOR_OK = false;\n")
#    for st in sd.states:
#        s.write("        p->PREV_STATE_" + st.name + " = (prev_state_name == \"" + package + "_" + st.name + "\");\n")
    s.write("    }\n\n")

    s.write("    virtual std::string getPredicatesStr(const common_behavior::PredicateListConstPtr& pred_list) const {\n")
    s.write("        PredicateListConstPtr p = boost::static_pointer_cast<const PredicateList >( pred_list );\n")
    s.write("        std::string r;\n")
    for pred in sd.predicates:
        s.write("        r = r + \"" + pred + ":\" + (p->" + pred + "?\"t\":\"f\") + \", \";\n")
    s.write("        r = r + \"IN_ERROR:\" + (p->IN_ERROR?\"t\":\"f\") + \", \";\n")
    s.write("        r = r + \"CURRENT_BEHAVIOR_OK:\" + (p->CURRENT_BEHAVIOR_OK?\"t\":\"f\") + \", \";\n")
#    for st in sd.states:
#        s.write("        r = r + \"PREV_STATE_" + st.name + ":\" + (p->PREV_STATE_" + st.name + "?\"t\":\"f\") + \", \";\n")
    s.write("        return r;\n")
    s.write("    }\n\n")

    s.write("    virtual void iterationEnd() {\n")
    if sd.trigger_gazebo:
        s.write("        singleStep_();\n")
    else:
        s.write("        // do nothing\n")
    s.write("    }\n\n")

    s.write("protected:\n")
    for p in sd.buffers_in:
        s.write("    " + p.getTypeCpp() + " " + p.alias + "_prev_;\n")
        s.write("    int " + p.alias + "_no_data_counter_;\n")
        s.write("    RTT::InputPort<" + p.getTypeCpp() + " > port_" + p.alias + "_in_;\n")
        s.write("    RTT::OutputPort<" + p.getTypeCpp() + " > port_" + p.alias + "_out_;\n")

    if sd.trigger_methods.onNoData() != None:
        s.write("\n    RTT::InputPort<bool > port_no_data_trigger_in__;\n")

    s.write("\n    RTT::TaskContext* owner_;\n")
    if sd.trigger_gazebo:
        s.write("    RTT::OperationCaller<void()> singleStep_;\n")

    for pred in sd.predicates:
        s.write("    predicateFunction pred_" + pred + ";\n")

    s.write("};\n\n")

    #
    # behavior_
    #
    for b in sd.behaviors:

        s.write("class behavior_" + b.name + " : public common_behavior::BehaviorBase {\n")
        s.write("public:\n")
        s.write("    behavior_" + b.name + "()\n")
        s.write("        : common_behavior::BehaviorBase(\"" + package + "_" + b.name + "\", \"" + b.name + "\")\n")
        s.write("    {\n")
        for rc in b.running_components:
            s.write("        addRunningComponent(\"" + rc + "\");\n")
        s.write("    }\n\n")

        s.write("    virtual bool checkErrorCondition(const common_behavior::PredicateListConstPtr& pred_list) const {\n")
        s.write("        PredicateListConstPtr p = boost::static_pointer_cast<const PredicateList >( pred_list );\n")
#        s.write("        return " + logicExprToCpp(b.err_cond, sd.predicates, sd.states) + ";\n")
        s.write("        return " + logicExprToCpp(b.err_cond, sd.predicates) + ";\n")
        s.write("    }\n\n")

        s.write("    virtual bool checkStopCondition(const common_behavior::PredicateListConstPtr& pred_list) const {\n")
        s.write("        PredicateListConstPtr p = boost::static_pointer_cast<const PredicateList >( pred_list );\n")
#        s.write("        return " + logicExprToCpp(b.stop_cond, sd.predicates, sd.states) + ";\n")
        s.write("        return " + logicExprToCpp(b.stop_cond, sd.predicates) + ";\n")
        s.write("    }\n")
        s.write("};\n\n")

    #
    # state_
    #
    for st in sd.states:
        s.write("class state_" + st.name + " : public common_behavior::StateBase {\n")
        s.write("protected:\n")
        s.write("    const std::string error_no_cond;\n")
        s.write("    const std::string error_too_many_cond;\n")
        for i in range(len(st.next_states)):
            ns_name = st.next_states[i][0]
            s.write("    const std::string next_state_name_" + str(i) + ";\n")

        s.write("public:\n")
        s.write("    state_" + st.name + "()\n")
        s.write("        : common_behavior::StateBase(\"" + package + "_" + st.name + "\", \"" + st.name + "\",\n")
        s.write("            std::vector<std::string >({\n")
        for b in st.behaviors:
            s.write("                \"" + package + "_" + b + "\",\n")
        s.write("            }))\n")
        s.write("        , error_no_cond(\"could not select next state\")\n")
        s.write("        , error_too_many_cond(\"too many next states\")\n")
        for i in range(len(st.next_states)):
            ns_name = st.next_states[i][0]
            s.write("        , next_state_name_" + str(i) + "(\"" + package + "_" + ns_name + "\")\n")
        s.write("    {\n")
        s.write("    }\n\n")

        s.write("    virtual const std::string& getNextState(const common_behavior::PredicateListConstPtr& pred_list) const {\n")
        s.write("        PredicateListConstPtr p = boost::static_pointer_cast<const PredicateList >( pred_list );\n")
        s.write("        int conditions_true_count = 0;\n")
        for i in range(len(st.next_states)):
            ns_cond = st.next_states[i][1]
            s.write("        bool next_state_pred_val_" + str(i) + " = (" + logicExprToCpp(ns_cond, sd.predicates) + ");\n")
            s.write("        conditions_true_count += (next_state_pred_val_" + str(i) + "?1:0);\n")

        s.write("        if (conditions_true_count > 1) {\n")
        s.write("            return error_too_many_cond;\n")
        s.write("        }\n")

        for i in range(len(st.next_states)):
            s.write("        if (next_state_pred_val_" + str(i) + ") {\n")
            s.write("            return  next_state_name_" + str(i) + ";\n")
            s.write("        }\n")

        s.write("        return error_no_cond;\n")
        s.write("    }\n\n")

        s.write("};\n\n")

    s.write("common_behavior::PredicateList& PredicateList::operator=(const common_behavior::PredicateList& arg) {\n")
    s.write("    const PredicateList* p = dynamic_cast<const PredicateList* >(&arg);\n")
    for pred in sd.predicates:
        s.write("    " + pred + " = p->" + pred + ";\n")
    s.write("    IN_ERROR = p->IN_ERROR;\n")
    s.write("    CURRENT_BEHAVIOR_OK = p->CURRENT_BEHAVIOR_OK;\n")
#    for st in sd.states:
#        s.write("    PREV_STATE_" + st.name + " = p->PREV_STATE_" + st.name + ";\n")
    s.write("    return *dynamic_cast<common_behavior::PredicateList* >(this);\n")
    s.write("};\n\n")



    s.write("};  // namespace " + package + "_types\n\n")

#    for st in sd.states:
#        s.write("REGISTER_STATE( " + package + "_types::state_" + st.name + " );\n")

    for b in sd.behaviors:
        s.write("REGISTER_BEHAVIOR( " + package + "_types::behavior_" + b.name + " );\n")

    for st in sd.states:
        s.write("REGISTER_STATE( " + package + "_types::state_" + st.name + " );\n")

    s.write("ORO_SERVICE_NAMED_PLUGIN(" + package + "_types::" + package + "_Master, \"" + package + "_master\");\n")


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

