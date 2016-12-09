/***************************************************************************
  tag: Peter Soetens  Thu Jul 3 15:30:14 CEST 2008  deployer.cpp

                        deployer.cpp -  description
                           -------------------
    begin                : Thu July 03 2008
    copyright            : (C) 2008 Peter Soetens
    email                : peter.soetens@fmtc.be

 ***************************************************************************
 *   This program is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Lesser General Public            *
 *   License as published by the Free Software Foundation; either          *
 *   version 2.1 of the License, or (at your option) any later version.    *
 *                                                                         *
 *   This program is distributed in the hope that it will be useful,       *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU     *
 *   Lesser General Public License for more details.                       *
 *                                                                         *
 *   You should have received a copy of the GNU Lesser General Public      *
 *   License along with this program; if not, write to the Free Software   *
 *   Foundation, Inc., 59 Temple Place,                                    *
 *   Suite 330, Boston, MA  02111-1307  USA                                *
 ***************************************************************************/

#include "subsystem_deployer/subsystem_deployer.h"

#include <rtt/rtt-config.h>
#include <rtt/os/main.h>
#include <rtt/RTT.hpp>
#include <rtt/Logger.hpp>
#include <rtt/internal/GlobalService.hpp>
#include <ocl/TaskBrowser.hpp>
#include <rtt/extras/SlaveActivity.hpp>

#include <rtt_roscomm/rtt_rostopic.h>

#include <iostream>
#include <string>
#include <unistd.h>
#include <stdio.h>

using namespace RTT;
using namespace std;

SubsystemDeployer::SubsystemDeployer(const std::string& name) :
    name_(name)
{
}

bool SubsystemDeployer::import(const std::string& name) {
    if (!ros_import_.ready()) {
        Logger::log() << Logger::Error << "ros.import operation is not ready" << Logger::endl;
        return false;
    }

    if (!ros_import_(name)) {
        Logger::log() << Logger::Error << "could not import: " << name << Logger::endl;
        return false;
    }

    return true;
}

static void printInputBufferInfo(const common_behavior::InputBufferInfo& info) {
    Logger::log()
        << " enable_ipc: " << (info.enable_ipc_?"true":"false")
        << ", ipc_channel_name: \'" << info.ipc_channel_name_ << "\'"
        << ", event_port: " << (info.event_port_?"true":"false")
        << ", interface_prefix: \'" << info.interface_prefix_ << "\'"
        << Logger::endl;
}

static void printOutputBufferInfo(const common_behavior::OutputBufferInfo& info) {
    Logger::log()
        << " enable_ipc: " << (info.enable_ipc_?"true":"false")
        << ", ipc_channel_name: \'" << info.ipc_channel_name_ << "\'"
        << ", interface_prefix: \'" << info.interface_prefix_ << "\'"
        << Logger::endl;
}

static bool loadROSParam(RTT::TaskContext* tc) {
    tc->loadService("rosparam");

    RTT::Service::shared_ptr tc_rosparam = tc->provides("rosparam");

    RTT::OperationCaller<bool()> tc_rosparam_getAll = tc_rosparam->getOperation("getAll");
    if (!tc_rosparam_getAll.ready()) {
        Logger::log() << Logger::Error << "could not get ROS parameter getAll operation for " << tc->getName() << Logger::endl;
        return false;
    }
    if (!tc_rosparam_getAll()) {
        Logger::log() << Logger::Warning << "could not read ROS parameters for " << tc->getName() << Logger::endl;
//        return false;     // TODO: this IS an error
    }

    return true;
}

template <class T>
static bool setComponentProperty(RTT::TaskContext *tc, const std::string& prop_name, const T& value) {
    RTT::Property<T>* property = dynamic_cast<RTT::Property<T>* >(tc->properties()->getProperty(prop_name));
    if (!property) {
        RTT::log(RTT::Error) << "component " << tc->getName() << " does not have property " << prop_name << RTT::endlog();
        return false;
    }
    property->set(value);

    return true;
}

bool SubsystemDeployer::deployInputBufferIpcComponent(const common_behavior::InputBufferInfo& buf_info) {
    std::string type = buf_info.interface_prefix_ + "Rx";
    if (buf_info.enable_ipc_) {
        std::string name = type;
        if (!dc_->loadComponent(name, type)) {
            RTT::log(RTT::Error) << "Unable to load component " << type << RTT::endlog();
            return false;
        }
        RTT::TaskContext* comp = dc_->getPeer(name);
        if (!setTriggerOnStart(comp, false)) {
            return false;
        }

        if (!setComponentProperty<std::string >(comp, "channel_name", buf_info.ipc_channel_name_)) {
            return false;
        }
        if (!setComponentProperty<bool >(comp, "event_port", buf_info.event_port_)) {
            return false;
        }

        buffer_rx_components_.push_back(comp);

        return true;
    }
    RTT::log(RTT::Error) << "component " << type << " should not have IPC buffer" << RTT::endlog();
    return false;
}

bool SubsystemDeployer::deployOutputBufferIpcComponent(const common_behavior::OutputBufferInfo& buf_info) {
    std::string type = buf_info.interface_prefix_ + "Tx";
    if (buf_info.enable_ipc_) {
        std::string name = type;
        if (!dc_->loadComponent(name, type)) {
            RTT::log(RTT::Error) << "Unable to load component " << type << RTT::endlog();
            return false;
        }
        RTT::TaskContext* comp = dc_->getPeer(name);
        if (!setTriggerOnStart(comp, false)) {
            return false;
        }

        if (!setComponentProperty<std::string >(comp, "channel_name", buf_info.ipc_channel_name_)) {
            return false;
        }

        buffer_tx_components_.push_back(comp);

        return true;
    }
    RTT::log(RTT::Error) << "component " << type << " should not have IPC buffer" << RTT::endlog();
    return false;
}

bool SubsystemDeployer::deployBufferSplitComponent(const common_behavior::BufferInfo& buf_info) {
    std::string type = buf_info.interface_prefix_ + "Split";
    std::string name = type;
    if (!dc_->loadComponent(name, type)) {
        RTT::log(RTT::Error) << "Unable to load component " << type << RTT::endlog();
        return false;
    }
    RTT::TaskContext* comp = dc_->getPeer(name);
    if (!setTriggerOnStart(comp, false)) {
        return false;
    }

    buffer_split_components_.push_back(comp);

    return true;
}

bool SubsystemDeployer::deployBufferConcateComponent(const common_behavior::BufferInfo& buf_info) {
    std::string type = buf_info.interface_prefix_ + "Concate";
    std::string name = type;
    if (!dc_->loadComponent(name, type)) {
        RTT::log(RTT::Error) << "Unable to load component " << type << RTT::endlog();
        return false;
    }
    RTT::TaskContext* comp = dc_->getPeer(name);
    if (!setTriggerOnStart(comp, false)) {
        return false;
    }

    buffer_concate_components_.push_back(comp);

    return true;
}

bool SubsystemDeployer::createInputBuffers(const std::vector<common_behavior::InputBufferInfo >& buffers) {
    for (int i = 0; i < buffers.size(); ++i) {
        const common_behavior::InputBufferInfo& buf_info = buffers[i];
        if (buf_info.enable_ipc_) {
            if (!deployInputBufferIpcComponent(buf_info)) {
                return false;
            }
        }

        if (!deployBufferSplitComponent(buf_info)) {
            return false;
        }

        if (buf_info.enable_ipc_) {
            // connect Split-Rx ports
            if (!dc_->connect(std::string("master_component.") + buf_info.interface_prefix_ + "_OUTPORT", buf_info.interface_prefix_ + "Split.msg_INPORT", ConnPolicy())) {
                RTT::log(RTT::Error) << "could not connect ports Split-Rx: " << buf_info.interface_prefix_ << RTT::endlog();
                return false;
            }

            // connect Rx to master_component
            if (!dc_->connect(buf_info.interface_prefix_ + "Rx.msg_OUTPORT", std::string("master_component.") + buf_info.interface_prefix_ + "_INPORT", ConnPolicy::data(ConnPolicy::LOCKED))) {
                RTT::log(RTT::Error) << "could not connect ports Rx-master_component: " << buf_info.interface_prefix_ << RTT::endlog();
                return false;
            }
        }
        else {
            // there is no Rx component, so create additional Concate component
            if (!deployBufferConcateComponent(buf_info)) {
                return false;
            }

            // connect Split-Concate ports
            if (!dc_->connect(buf_info.interface_prefix_ + "Concate.msg_OUTPORT", buf_info.interface_prefix_ + "Split.msg_INPORT", ConnPolicy())) {
                RTT::log(RTT::Error) << "could not connect ports Split-Concate: " << buf_info.interface_prefix_ << RTT::endlog();
                return false;
            }

            // connect Concate to master_component
            if (!dc_->connect(buf_info.interface_prefix_ + "Concate.msg_OUTPORT", std::string("master_component.") + buf_info.interface_prefix_ + "_INPORT", ConnPolicy())) {
                RTT::log(RTT::Error) << "could not connect ports Concate-master_component: " << buf_info.interface_prefix_ << RTT::endlog();
                return false;
            }
        }
    }
    return true;
}

bool SubsystemDeployer::createOutputBuffers(const std::vector<common_behavior::OutputBufferInfo >& buffers) {
    for (int i = 0; i < buffers.size(); ++i) {
        const common_behavior::OutputBufferInfo& buf_info = buffers[i];
        if (buf_info.enable_ipc_) {
            if (!deployOutputBufferIpcComponent(buf_info)) {
                return false;
            }
        }

        if (!deployBufferConcateComponent(buf_info)) {
            return false;
        }

        if (buf_info.enable_ipc_) {
            if (!dc_->connect(buf_info.interface_prefix_ + "Concate.msg_OUTPORT", buf_info.interface_prefix_ + "Tx.msg_INPORT", ConnPolicy())) {
                RTT::log(RTT::Error) << "could not connect ports Concate-Tx: " << buf_info.interface_prefix_ << RTT::endlog();
                return false;
            }
        }
        else {
            // there is no Tx component, so create additional Split component
            if (!deployBufferSplitComponent(buf_info)) {
                return false;
            }

            // connect Split-Concate ports
            if (!dc_->connect(buf_info.interface_prefix_ + "Concate.msg_OUTPORT", buf_info.interface_prefix_ + "Split.msg_INPORT", ConnPolicy())) {
                RTT::log(RTT::Error) << "could not connect ports Split-Concate: " << buf_info.interface_prefix_ << RTT::endlog();
                return false;
            }
        }
    }
    return true;
}

bool SubsystemDeployer::setTriggerOnStart(RTT::TaskContext* tc, bool trigger) {
    RTT::base::AttributeBase* base = tc->attributes()->getAttribute("TriggerOnStart");
    if (!base) {
        RTT::log(RTT::Error) << "component " << tc->getName() << " does not have attribute " << "TriggerOnStart" << RTT::endlog();
        return false;
    }
    RTT::Attribute<bool>* triggerOnStart = static_cast<RTT::Attribute<bool>* >(base);
    if (!triggerOnStart) {
        RTT::log(RTT::Error) << "component " << tc->getName() << " does not have attribute " << "TriggerOnStart" << " of type bool" << RTT::endlog();
        return false;
    }
    triggerOnStart->set(trigger);
    return true;
}

bool SubsystemDeployer::initializeSubsystem(const std::string& master_package_name) {
    Logger::In in("SubsystemDeployer::init");

    dc_.reset(new OCL::DeploymentComponent(name_));

    dc_->import("rtt_ros");

    RTT::Service::shared_ptr ros = RTT::internal::GlobalService::Instance()->getService("ros");
    if (!ros) {
        Logger::log() << Logger::Error << "rtt_ros: ros service could not be loaded (NULL pointer)" << Logger::endl;
        return false;
    }

    ros_import_ = ros->getOperation("import");

    if (!import("rtt_roscomm") ||
        !import("rtt_rosparam") ||
        !import("rtt_rosclock") ||
        !import("rtt_rospack") ||
        !import("rtt_actionlib") ||
        !import("common_behavior") ||
        !import("conman") ||
        !import("rtt_diagnostic_msgs") ||
//        !import("conman_ros") ||
        !import("eigen_typekit"))
    {
        Logger::log() << Logger::Error << "could not load some core dependencies" << Logger::endl;
        return false;
    }

    Logger::log() << Logger::Info << "loaded core dependencies" << Logger::endl;

    //
    // load conman scheme
    //
    if (!dc_->loadComponent("scheme","conman::Scheme")) {
        Logger::log() << Logger::Error << "could not load conman::Scheme" << Logger::endl;
        return false;
    }

    scheme_ = dc_->getPeer("scheme");

    if (!setTriggerOnStart(scheme_, false)) {
        return false;
    }

    if (!scheme_) {
        Logger::log() << Logger::Error << "scheme in NULL" << Logger::endl;
        return false;
    }
    // scheme.loadService("conman_ros");    // TODO: check if this is needed
    scheme_->configure();

    //
    // load master component
    //
    if (!dc_->loadComponent("master_component","MasterComponent")) {
        Logger::log() << Logger::Error << "could not load MasterComponent" << Logger::endl;
        return false;
    }

    master_component_ = dc_->getPeer("master_component");

    if (!setTriggerOnStart(master_component_, false)) {
        return false;
    }

    if (!master_component_) {
        Logger::log() << Logger::Error << "master_component in NULL" << Logger::endl;
        return false;
    }

    // TODO: MasterService and its package are arguments
    if (!import(master_package_name)) {
        return false;
    }

    //setActivity("master_component", 0, 6, ORO_SCHED_RT);
    master_component_->loadService(master_package_name + "_master");



    RTT::OperationCaller<bool(RTT::TaskContext*)> master_component_addConmanScheme = master_component_->getOperation("addConmanScheme");
    if (!master_component_addConmanScheme.ready()) {
        Logger::log() << Logger::Error << "Could not get addConmanScheme operation of Master Component" << Logger::endl;
        return false;
    }

    if (!master_component_addConmanScheme(scheme_)) {
        Logger::log() << Logger::Error << "Could not add Conman Scheme to Master Component" << Logger::endl;
        return false;
    }

    //
    // manage ports and ipc buffers
    //
    std::vector<std::string > master_port_names = master_component_->ports()->getPortNames();
    for (int i = 0; i < master_port_names.size(); ++i) {
        Logger::log() << Logger::Info << "master_component port[" << i << "]: " << master_port_names[i] << Logger::endl;
    }

    master_service_ = master_component_->getProvider<common_behavior::MasterServiceRequester >("master");
    if (!master_service_) {
        RTT::log(RTT::Error) << "Unable to load common_behavior::MasterService from master_component" << RTT::endlog();
        return false;
    }

    // inputs
    std::vector<common_behavior::InputBufferInfo > lowerInputBuffers;
    std::vector<common_behavior::InputBufferInfo > upperInputBuffers;

    master_service_->getLowerInputBuffers(lowerInputBuffers);
    master_service_->getUpperInputBuffers(upperInputBuffers);

    Logger::log() << Logger::Info << "lowerInputBuffers:" << Logger::endl;
    for (int i = 0; i < lowerInputBuffers.size(); ++i) {
        printInputBufferInfo(lowerInputBuffers[i]);
    }

    Logger::log() << Logger::Info << "upperInputBuffers:" << Logger::endl;
    for (int i = 0; i < upperInputBuffers.size(); ++i) {
        printInputBufferInfo(upperInputBuffers[i]);
    }

    if (!createInputBuffers(lowerInputBuffers)) {
        RTT::log(RTT::Error) << "Could not create lower input buffers" << RTT::endlog();
        return false;
    }

    if (!createInputBuffers(upperInputBuffers)) {
        RTT::log(RTT::Error) << "Could not create upper input buffers" << RTT::endlog();
        return false;
    }

    // outputs
    std::vector<common_behavior::OutputBufferInfo > lowerOutputBuffers;
    std::vector<common_behavior::OutputBufferInfo > upperOutputBuffers;

    master_service_->getLowerOutputBuffers(lowerOutputBuffers);
    master_service_->getUpperOutputBuffers(upperOutputBuffers);

    Logger::log() << Logger::Info << "lowerOutputBuffers:" << Logger::endl;
    for (int i = 0; i < lowerOutputBuffers.size(); ++i) {
        printOutputBufferInfo(lowerOutputBuffers[i]);
    }

    Logger::log() << Logger::Info << "upperOutputBuffers:" << Logger::endl;
    for (int i = 0; i < upperOutputBuffers.size(); ++i) {
        printOutputBufferInfo(upperOutputBuffers[i]);
    }

    if (!createOutputBuffers(lowerOutputBuffers)) {
        RTT::log(RTT::Error) << "Could not create lower output buffers" << RTT::endlog();
        return false;
    }

    if (!createOutputBuffers(upperOutputBuffers)) {
        RTT::log(RTT::Error) << "Could not create upper output buffers" << RTT::endlog();
        return false;
    }

/*
ros.import("rtt_velma_core_cs_ve_body_msgs");
ros.import("velma_core_cs_ve_body_interface");
ros.import("velma_core_ve_body");
ros.import("rtt_velma_core_ve_body_re_body_msgs");
ros.import("velma_core_ve_body_re_body_interface");
ros.import("rtt_std_msgs");
ros.import("port_operations");
ros.import("rtt_control_msgs");
ros.import("lwr_fri");
ros.import("controller_common");
ros.import("velma_controller");
ros.import("rtt_cartesian_trajectory_msgs");
ros.import("rtt_std_msgs");
ros.import("rtt_tf");
ros.import("velma_sim_gazebo");
*/

    //
    // diagnostics ROS interface
    //
    dc_->loadComponent("diag","DiagnosticComponent");
    diag_component_ = dc_->getPeer("diag");
    if (!diag_component_->setPeriod(0.01)) {
        RTT::log(RTT::Error) << "could not change period of component \'" << diag_component_->getName() << RTT::endlog();
        return false;
    }

//TODO:
//    diag_component_.loadService("sim_clock_activity");

    RTT::base::PortInterface* diag_port_out_ = diag_component_->ports()->getPort("diag_OUTPORT");
    if (diag_port_out_) {
        if (!diag_port_out_->createStream(rtt_roscomm::topic(std::string("/") + master_package_name + "/diag"))) {
            RTT::log(RTT::Error) << "could not create ROS stream for port \'" << diag_component_->getName() << "." << diag_port_out_->getName() << "\'" << RTT::endlog();
            return false;
        }
    }
    else {
        RTT::log(RTT::Error) << "component \'" << diag_component_->getName() << "\' does not have port \'diag_OUTPORT\'" << RTT::endlog();
        return false;
    }

    Logger::log() << Logger::Info << "OK" << Logger::endl;

    RTT::log(RTT::Info) << "Master Component ports:" << RTT::endlog();
    std::vector<std::string > port_names = master_component_->ports()->getPortNames();
    for (int  i = 0; i < port_names.size(); ++i) {
        RTT::log(RTT::Info) << "  " << port_names[i] << RTT::endlog();
    }

    return true;
}

std::vector<RTT::TaskContext* > SubsystemDeployer::getAllComponents() const {
    std::vector<RTT::TaskContext* > result;

    std::vector< std::string > peer_names = dc_->getPeerList();
    for (int i = 0; i < peer_names.size(); ++i) {
        result.push_back(dc_->getPeer(peer_names[i]));
    }

    return result;
}

std::vector<RTT::TaskContext* > SubsystemDeployer::getCoreComponents() const {
    std::vector<RTT::TaskContext* > result;
    result.push_back(master_component_);
    result.push_back(scheme_);
    result.push_back(diag_component_);
    result.insert(result.end(), buffer_rx_components_.begin(), buffer_rx_components_.end());
    result.insert(result.end(), buffer_tx_components_.begin(), buffer_tx_components_.end());
    result.insert(result.end(), buffer_split_components_.begin(), buffer_split_components_.end());
    result.insert(result.end(), buffer_concate_components_.begin(), buffer_concate_components_.end());
    return result;
}

std::vector<RTT::TaskContext* > SubsystemDeployer::getNonCoreComponents() const {
    std::vector<RTT::TaskContext* > result;
    std::vector<RTT::TaskContext* > core = getCoreComponents();
    
    std::vector< std::string > peer_names = dc_->getPeerList();

    for (int i = 0; i < peer_names.size(); ++i) {
        const std::string& name = peer_names[i];
        bool is_core = false;
        for (int j = 0; j < core.size(); ++j) {
            if (core[j]->getName() == name) {
                is_core = true;
                break;
            }
        }
        if (!is_core) {
            TaskContext* tc = dc_->getPeer(name);
            result.push_back(tc);
        }
    }
    return result;
}

bool SubsystemDeployer::configure() {
    Logger::In in("SubsystemDeployer::configure");

    // disable Trigger On Start for all components
    const std::vector<RTT::TaskContext* > all_components = getAllComponents();
    for (int i = 0; i < all_components.size(); ++i) {
        setTriggerOnStart(all_components[i], false);
    }

    // initialize conman scheme
    RTT::OperationCaller<bool(const std::string&)> scheme_addBlock = scheme_->getOperation("addBlock");
    if (!scheme_addBlock.ready()) {
        Logger::log() << Logger::Error << "Could not get addBlock operation of Conman scheme" << Logger::endl;
        return false;
    }
    std::vector<RTT::TaskContext* > conman_peers = getNonCoreComponents();
    conman_peers.insert(conman_peers.end(), buffer_tx_components_.begin(), buffer_tx_components_.end());
    conman_peers.insert(conman_peers.end(), buffer_split_components_.begin(), buffer_split_components_.end());
    conman_peers.insert(conman_peers.end(), buffer_concate_components_.begin(), buffer_concate_components_.end());
    std::vector<bool > conman_peers_running(conman_peers.size(), false);
    for (int i = 0; i < conman_peers.size(); ++i) {
        if (conman_peers[i]->isRunning()) {
            conman_peers[i]->stop();
            conman_peers_running[i] = true;
        }
        scheme_->addPeer(conman_peers[i]);
        if (!scheme_addBlock(conman_peers[i]->getName())) {
            Logger::log() << Logger::Warning << "Could not add block to Conman scheme: " << conman_peers[i]->getName() << Logger::endl;
            return true;
        }
    }

/*
    RTT::OperationCaller<int(std::vector<std::vector<std::string> >&) > scheme_getFlowCycles = scheme_->getOperation("getFlowCycles");
    if (!scheme_getFlowCycles.ready()) {
        Logger::log() << Logger::Error << "Could not get getFlowCycles operation of Conman scheme" << Logger::endl;
        return false;
    }

    std::vector<std::vector<std::string> > cycles;
    scheme_getFlowCycles(cycles);

    Logger::log() << Logger::Warning << "Cycles in scheme graph:" << Logger::endl;
    for (int i = 0; i < cycles.size(); ++i) {
        std::string cycle_str;
        for (int j = 0; j < cycles[i].size(); ++j) {
            cycle_str = cycle_str + (cycle_str.empty()?"":", ") + cycles[i][j];
        }
        Logger::log() << Logger::Warning << "  " << cycle_str << Logger::endl;
    }
*/
    // break all cycles at inputs to non-core components
//    RTT::OperationCaller<const std::vector<std::pair<std::string, std::string > >&() > master_component_getLatchedConnections = master_component_->getOperation("getLatchedConnections");
//    if (!master_component_getLatchedConnections.ready()) {
//        Logger::log() << Logger::Error << "Could not get getLatchedConnections operation of Master Component" << Logger::endl;
//        return false;
//    }

    RTT::OperationCaller<bool(const std::string&, const std::string&, const bool) > scheme_latchConnections = scheme_->getOperation("latchConnections");
    if (!scheme_latchConnections.ready()) {
        Logger::log() << Logger::Error << "Could not get getFlowCycles operation of Conman scheme" << Logger::endl;
        return false;
    }

    const std::vector<std::pair<std::string, std::string > >& latched_connections = master_service_->getLatchedConnections();
    for (int i = 0; i < latched_connections.size(); ++i) {
        scheme_latchConnections(latched_connections[i].first, latched_connections[i].second, true);
    }

    const std::vector<RTT::TaskContext* > core_components = getCoreComponents();
    const std::vector<RTT::TaskContext* > non_core_components = getNonCoreComponents();
/*
    for (int i = 0; i < cycles.size(); ++i) {
        for (int j = 0; j < cycles[i].size(); ++j) {
            int prev_j = (j + cycles[i].size() - 1) % cycles[i].size();
            bool this_non_core = false;
            for (int k = 0; k < non_core_components.size(); ++k) {
                if (cycles[i][j] == non_core_components[k]->getName()) {
                    this_non_core = true;
                    break;
                }
            }
            if (!this_non_core) {
                continue;
            }
            bool prev_core = false;
            for (int k = 0; k < core_components.size(); ++k) {
                if (cycles[i][prev_j] == core_components[k]->getName()) {
                    prev_core = true;
                    break;
                }
            }
            if (prev_core) {
                Logger::log() << Logger::Info << "Latching connections: " << cycles[i][prev_j] << ", " << cycles[i][j] << Logger::endl;
                scheme_latchConnections(cycles[i][prev_j], cycles[i][j], true);
                break;
            }
        }
    }*/

/*    RTT::OperationCaller<bool(const std::string&, const std::string&, const bool) > scheme_latchConnections = scheme_->getOperation("latchConnections");
    if (!scheme_latchConnections.ready()) {
        Logger::log() << Logger::Error << "Could not get getFlowCycles operation of Conman scheme" << Logger::endl;
        return false;
    }

    const std::vector<RTT::TaskContext* > core_components = getCoreComponents();
    const std::vector<RTT::TaskContext* > non_core_components = getNonCoreComponents();

    for (int i = 0; i < cycles.size(); ++i) {
        for (int j = 0; j < cycles[i].size(); ++j) {
            int prev_j = (j + cycles[i].size() - 1) % cycles[i].size();
            bool this_non_core = false;
            for (int k = 0; k < non_core_components.size(); ++k) {
                if (cycles[i][j] == non_core_components[k]->getName()) {
                    this_non_core = true;
                    break;
                }
            }
            if (!this_non_core) {
                continue;
            }
            bool prev_core = false;
            for (int k = 0; k < core_components.size(); ++k) {
                if (cycles[i][prev_j] == core_components[k]->getName()) {
                    prev_core = true;
                    break;
                }
            }
            if (prev_core) {
                Logger::log() << Logger::Info << "Latching connections: " << cycles[i][prev_j] << ", " << cycles[i][j] << Logger::endl;
                scheme_latchConnections(cycles[i][prev_j], cycles[i][j], true);
                break;
            }
        }
    }
*/

/*
//    std::vector< std::string > peer_names = dc_->getPeerList();
    for (int i = 0; i < peer_names.size(); ++i) {
        const std::string& name = peer_names[i];
        if (!isCorePeer(name)) {
            TaskContext* tc = dc_->getPeer(name);
            if (!setTriggerOnStart(tc, false)) {
                return false;
            }

            scheme_->addPeer(tc);

            RTT::OperationCaller<bool(const std::string&)> scheme_addBlock = scheme_->getOperation("addBlock");
            if (!scheme_addBlock.ready()) {
                Logger::log() << Logger::Error << "Could not get addBlock operation of Conman scheme" << Logger::endl;
                return false;
            }

            if (!scheme_addBlock(name)) {
                Logger::log() << Logger::Warning << "Could not add block to Conman scheme: " << name << Logger::endl;
                return true;
            }
        }
    }
*/

    // add all peers to diagnostics component
    for (int i = 0; i < all_components.size(); ++i) {
        if (all_components[i]->getName() != diag_component_->getName()) {
            diag_component_->addPeer(all_components[i]);
        }
    }

    Logger::log() << Logger::Info << "[before master_component configure] scheme_->getActivity(): "
        << (scheme_->getActivity()) << Logger::endl;

    // configure unconfigured core peers
    // master component can be configured after all peers are added to scheme
    for (int i = 0; i < core_components.size(); ++i) {
        if (!core_components[i]->isConfigured()) {
            if (!core_components[i]->configure()) {
                RTT::log(RTT::Error) << "Unable to configure component " << core_components[i]->getName() << RTT::endlog();
                return false;
            }
        }
    }

    // configure other unconfigured peers
    for (int i = 0; i < non_core_components.size(); ++i) {
        if (!non_core_components[i]->isConfigured()) {
            loadROSParam(non_core_components[i]);
            if (!non_core_components[i]->configure()) {
                RTT::log(RTT::Error) << "Unable to configure component " << non_core_components[i]->getName() << RTT::endlog();
                return false;
            }
        }
    }

    // start conman scheme first
    if (!scheme_->start()) {
        RTT::log(RTT::Error) << "Unable to start component: " << scheme_->getName() << RTT::endlog();
        return false;
    }

    if (scheme_->getTaskState() != RTT::TaskContext::Running) {
        RTT::log(RTT::Error) << "Component is not in the running state: " << scheme_->getName() << RTT::endlog();
        return false;
    }

/*
// TODO: remove
    Logger::log() << Logger::Info << "scheme activity: "
        << (scheme_->getActivity()->isActive()?"active":"not acitve") << Logger::endl;

    Logger::log() << Logger::Info << "scheme_->getActivity(): "
        << (scheme_->getActivity()) << Logger::endl;

    Logger::log() << Logger::Info << "scheme_->getPeer(LWRlSim)->getActivity(): "
        << (scheme_->getPeer("LWRlSim")->getActivity()) << Logger::endl;

    Logger::log() << Logger::Info << "scheme_->getPeer(LWRlSim)->engine()->getActivity(): "
        << (scheme_->getPeer("LWRlSim")->engine()->getActivity()) << Logger::endl;

    Logger::log() << Logger::Info << "dynamic_cast<extras::SlaveActivity* >(scheme_->getPeer(LWRlSim)->engine()->getActivity())->getMaster(): "
        << (dynamic_cast<extras::SlaveActivity* >(scheme_->getPeer("LWRlSim")->engine()->getActivity())->getMaster()) << Logger::endl;


    dynamic_cast<extras::SlaveActivity* >(scheme_->getPeer("LWRlSim")->engine()->getActivity())->getMaster()->isActive();
    dynamic_cast<extras::SlaveActivity* >(scheme_->getPeer("LWRlSim")->getActivity())->getMaster()->isActive();

    std::vector<std::string > scheme_peers = scheme_->getPeerList();
    for (int i = 0; i < scheme_peers.size(); ++i) {
        RTT::TaskContext* tc = scheme_->getPeer(scheme_peers[i]);

        if (tc->getActivity()) {
            Logger::log() << Logger::Info << "task " << tc->getName() << " has activity: " << (tc->getActivity()->isActive()?"active":"not active") << Logger::endl;
        }
        else {
            Logger::log() << Logger::Info << "task " << tc->getName() << " has no activity" << Logger::endl;
        }

        if(!tc->isRunning()) {
            tc->start();
        }

        if (tc->engine() == NULL) {
            Logger::log() << Logger::Info << "task " << tc->getName() << " execution engine is NULL" << Logger::endl;
        }
        else {
            Logger::log() << Logger::Info << "task " << tc->getName() << " execution engine is not NULL" << Logger::endl;
        }
        RTT::base::ActivityInterface* ai = tc->engine()->getActivity();
        if (ai == NULL) {
            Logger::log() << Logger::Info << "task " << tc->getName() << " execution engine activity is NULL" << Logger::endl;
        }
        else {
            Logger::log() << Logger::Info << "task " << tc->getName() << " execution engine activity is not NULL" << Logger::endl;
        }

        Logger::log() << Logger::Info << "task " << tc->getName() << " execution engine activity: "
            << (ai->isActive()?"active":"not acitve") << Logger::endl;

        extras::SlaveActivity* sa = dynamic_cast<extras::SlaveActivity* >(ai);
        if (sa == NULL) {
            Logger::log() << Logger::Info << "slave activity is NULL" << Logger::endl;
        }
        else {
            Logger::log() << Logger::Info << "slave activity is not NULL" << Logger::endl;
        }

        base::ActivityInterface* mmaster = sa->getMaster();
        if (mmaster == NULL) {
            Logger::log() << Logger::Info << "mmaster is NULL" << Logger::endl;
        }
        else {
            Logger::log() << Logger::Info << "mmaster is not NULL" << Logger::endl;
        }

        Logger::log() << Logger::Info << "mmaster activity: "
            << (mmaster->isActive()?"active":"not acitve") << Logger::endl;
        
        //tc->engine()->getActivity()->start();
        
        tc->engine()->stopTask(tc);
        tc->stop();
    }
*/

    // start other core peers
    for (int i = 0; i < core_components.size(); ++i) {
        if (!core_components[i]->isRunning()) {
            if (!core_components[i]->start()) {
                RTT::log(RTT::Error) << "Unable to start component " << core_components[i]->getName() << RTT::endlog();
                return false;
            }
        }
    }

    // start non-core components that should always run
    for (int i = 0; i < conman_peers.size(); ++i) {
        if (conman_peers_running[i]) {
            conman_peers[i]->start();
        }
    }

    Logger::log() << Logger::Info << "OK" << Logger::endl;

    return true;
}

void SubsystemDeployer::runScripts(const std::vector<std::string>& scriptFiles) {
    /******************** WARNING ***********************
     *   NO log(...) statements before __os_init() !!!!! 
     ***************************************************/
    int rc = 0;
    bool deploymentOnlyChecked = false;


            /* Only start the scripts after the Orb was created. Processing of
               scripts stops after the first failed script, and -1 is returned.
               Whether a script failed or all scripts succeeded, in non-daemon
               and non-checking mode the TaskBrowser will be run to allow
               inspection if the input is a tty.
             */
            bool result = true;
            for (std::vector<std::string>::const_iterator iter=scriptFiles.begin();
                 iter!=scriptFiles.end() && result;
                 ++iter)
            {
                if ( !(*iter).empty() )
                {
                    if ( (*iter).rfind(".xml",std::string::npos) == (*iter).length() - 4 || (*iter).rfind(".cpf",std::string::npos) == (*iter).length() - 4) {
/*                        if ( deploymentOnlyChecked ) {
                            if (!dc_->loadComponents( (*iter) )) {
                                result = false;
                                log(Error) << "Failed to load file: '"<< (*iter) <<"'." << endlog();
                            } else if (!dc_.configureComponents()) {
                                result = false;
                                log(Error) << "Failed to configure file: '"<< (*iter) <<"'." << endlog();
                            }
                            // else leave result=true and continue
                        } else {*/
                            result = dc_->kickStart( (*iter) );
//                        }
                        continue;
                    }

                    if ( (*iter).rfind(".ops",std::string::npos) == (*iter).length() - 4 ||
                         (*iter).rfind(".osd",std::string::npos) == (*iter).length() - 4 ||
                         (*iter).rfind(".lua",std::string::npos) == (*iter).length() - 4) {
                        result = dc_->runScript( (*iter) ) && result;
                        continue;
                    }
                    log(Error) << "Unknown extension of file: '"<< (*iter) <<"'. Must be xml, cpf for XML files or, ops, osd or lua for script files."<<endlog();
                }
            }
            rc = (result ? 0 : -1);
}

bool SubsystemDeployer::runTaskBrowser() {

//            if ( !deploymentOnlyChecked ) {
                if (isatty(fileno(stdin))) {
                    OCL::TaskBrowser tb( dc_.get() );
                    tb.loop();
                } else {
                    dc_->waitForInterrupt();
                }

                dc_->shutdownDeployment();
//            }
}

boost::shared_ptr<OCL::DeploymentComponent >& SubsystemDeployer::getDc() {
    return dc_;
}

