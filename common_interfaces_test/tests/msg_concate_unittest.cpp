/*
 Copyright (c) 2014, Robot Control and Pattern Recognition Group, Warsaw University of Technology
 All rights reserved.
 
 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:
     * Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
     * Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.
     * Neither the name of the Warsaw University of Technology nor the
       names of its contributors may be used to endorse or promote products
       derived from this software without specific prior written permission.
 
 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL <COPYright HOLDER> BE LIABLE FOR ANY
 DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

#include <limits.h>
#include "common_interfaces_test_msgs/Container.h"
#include "common_interfaces/message_concate.h"
#include <rtt/extras/SlaveActivity.hpp>

#include "gtest/gtest.h"

namespace message_concate_tests {

using namespace common_interfaces_test_msgs;

class TestComponentIn : public RTT::TaskContext {

public:

    explicit TestComponentIn(const std::string& name) :
        TaskContext(name, PreOperational)
    {
        this->ports()->addPort("Container_cont1_sub1_field1", port1);
        this->ports()->addPort("Container_cont1_sub1_field2", port2);
        this->ports()->addPort("Container_cont1_sub2_field1", port3);
        this->ports()->addPort("Container_cont1_sub2_field2", port4);
        this->ports()->addPort("Container_cont1_field1", port5);
        this->ports()->addPort("Container_cont1_field2", port6);
        this->ports()->addPort("Container_cont2_sub1_field1", port7);
        this->ports()->addPort("Container_cont2_sub1_field2", port8);
        this->ports()->addPort("Container_cont2_sub2_field1", port9);
        this->ports()->addPort("Container_cont2_sub2_field2", port10);
        this->ports()->addPort("Container_cont2_field1", port11);
        this->ports()->addPort("Container_cont2_field2", port12);
        this->ports()->addPort("Container_cont3", port13);
        this->ports()->addPort("Container_cont4", port14);
        this->ports()->addPort("Container_field1", port15);
        this->ports()->addPort("Container_field2", port16);
    }

    bool configureHook() {
        return true;
    }

    bool startHook() {
        return true;
    }

    void updateHook() {
        port1.write(cont_.cont1.sub1.field1);
        port2.write(cont_.cont1.sub1.field2);
        port3.write(cont_.cont1.sub2.field1);
        port4.write(cont_.cont1.sub2.field2);
        port5.write(cont_.cont1.field1);
        port6.write(cont_.cont1.field2);
        port7.write(cont_.cont2.sub1.field1);
        port8.write(cont_.cont2.sub1.field2);
        port9.write(cont_.cont2.sub2.field1);
        port10.write(cont_.cont2.sub2.field2);
        port11.write(cont_.cont2.field1);
        port12.write(cont_.cont2.field2);
        port13.write(cont_.cont3);
        port14.write(cont_.cont4);
        port15.write(cont_.field1);
        port16.write(cont_.field2);
    }

    bool connectPorts(RTT::TaskContext* other, const std::vector<std::string >& not_connected_ports = std::vector<std::string >()) {
        RTT::DataFlowInterface::Ports ports = this->ports()->getPorts();
        for (int i = 0; i < ports.size(); ++i) {
            bool ignore = false;
            for (int j = 0; j < not_connected_ports.size(); ++j) {
                if (ports[i]->getName() == not_connected_ports[j] || ports[i]->getName() + "_INPORT" == not_connected_ports[j]) {
                    ignore = true;
                }
            }
            if (ignore) {
                continue;
            }
            RTT::base::PortInterface* pi = other->ports()->getPort(ports[i]->getName() + "_INPORT");
            if (!pi || !ports[i]->connectTo( pi )) {
                return false;
            }
        }
        return true;
    }

    void setData(const Container& cont) {
        cont_ = cont;
    }

private:
    Container cont_;

    RTT::OutputPort<uint32_t > port1;
    RTT::OutputPort<uint32_t > port2;
    RTT::OutputPort<uint32_t > port3;
    RTT::OutputPort<uint32_t > port4;
    RTT::OutputPort<double > port5;
    RTT::OutputPort<double > port6;
    RTT::OutputPort<uint32_t > port7;
    RTT::OutputPort<uint32_t > port8;
    RTT::OutputPort<uint32_t > port9;
    RTT::OutputPort<uint32_t > port10;
    RTT::OutputPort<double > port11;
    RTT::OutputPort<double > port12;
    RTT::OutputPort<SubContainer > port13;
    RTT::OutputPort<SubContainer > port14;
    RTT::OutputPort<uint32_t > port15;
    RTT::OutputPort<uint32_t > port16;
};

class TestComponentOut : public RTT::TaskContext {

public:

    explicit TestComponentOut(const std::string& name) :
        TaskContext(name, PreOperational),
        read_successful_(false)
    {
        this->ports()->addPort("msg", port);
    }

    bool configureHook() {
        return true;
    }

    bool startHook() {
        return true;
    }

    void updateHook() {
        read_successful_ = (port.read(cont_) == RTT::NewData);
    }

    bool connectPorts(RTT::TaskContext* other) {
        if (!port.connectTo( other->ports()->getPort("msg_OUTPORT") )) {
            return false;
        }
        return true;
    }

    Container getData() {
        return cont_;
    }

    bool isReadSuccessful() const {
        return read_successful_;
    }

private:
    Container cont_;

    bool read_successful_;

    RTT::InputPort<Container > port;
};

void initContainerData(Container& cont_in) {
  cont_in.cont1.sub1.field1 = 1;
//  cont_in.cont1.sub1.field1_valid = true;
  cont_in.cont1.sub1.field2 = 2;
//  cont_in.cont1.sub1_valid = true;
  cont_in.cont1.sub2.field1 = 3;
//  cont_in.cont1.sub2.field1_valid = true;
  cont_in.cont1.sub2.field2 = 4;
  cont_in.cont1.field1 = 5.0;
//  cont_in.cont1.field1_valid = true;
  cont_in.cont1.field2 = 6.0;
//  cont_in.cont1_valid = true;
  cont_in.cont2.sub1.field1 = 7;
  cont_in.cont2.sub1.field2 = 8;
  cont_in.cont2.sub2.field1 = 9;
  cont_in.cont2.sub2.field2 = 10;
  cont_in.cont2.field1 = 11.0;
//  cont_in.cont2.field1_valid = true;
  cont_in.cont2.field2 = 12.0;
  cont_in.cont3.sub1.field1 = 13;
  cont_in.cont3.sub1.field2 = 14;
  cont_in.cont3.sub2.field1 = 15;
  cont_in.cont3.sub2.field2 = 16;
  cont_in.cont3.field1 = 17.0;
  cont_in.cont3.field2 = 18.0;
//  cont_in.cont3_valid = true;
  cont_in.cont4.sub1.field1 = 19;
  cont_in.cont4.sub1.field2 = 21;
  cont_in.cont4.sub1_valid = true;
  cont_in.cont4.sub2.field1 = 22;
  cont_in.cont4.sub2.field2 = 23;
  cont_in.cont4.field1 = 24.0;
  cont_in.cont4.field2 = 25.0;
  cont_in.field1 = 26;
//  cont_in.field1_valid = true;
  cont_in.field2 = 27;
}


// Tests for class MessageConcate.

// Tests MessageConcate class for data valid on all input ports.
TEST(MessageConcateTest, AllValid) {

  // the component under test
  MessageConcate<Container_Ports > concate("concate");
  concate.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( concate.configure() );
  EXPECT_TRUE( concate.start() );
  EXPECT_EQ( concate.ports()->getPortNames().size(), 17);

  // component that writes data on input ports of the component under test
  TestComponentIn test_in("test_in");
  test_in.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( test_in.connectPorts(&concate) );
  EXPECT_TRUE( test_in.configure() );
  EXPECT_TRUE( test_in.start() );

  // component that reads data from output port of the component under test
  TestComponentOut test_out("test_out");
  test_out.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( test_out.connectPorts(&concate) );
  EXPECT_TRUE( test_out.configure() );
  EXPECT_TRUE( test_out.start() );

  // generate some data
  Container cont_in;
  initContainerData(cont_in);

  // load the data into test_in component
  test_in.setData( cont_in );

  // execute all components
  test_in.getActivity()->execute();
  concate.getActivity()->execute();
  test_out.getActivity()->execute();

  EXPECT_TRUE(test_out.isReadSuccessful());

  // get the result data
  Container cont_out = test_out.getData();

  // check the data
  EXPECT_EQ(cont_out.cont1.sub1.field1,         cont_in.cont1.sub1.field1);
  EXPECT_EQ(cont_out.cont1.sub1.field1_valid,   true);
  EXPECT_EQ(cont_out.cont1.sub1.field2,         cont_in.cont1.sub1.field2);
  EXPECT_EQ(cont_out.cont1.sub1_valid,          true);
  EXPECT_EQ(cont_out.cont1.sub2.field1,         cont_in.cont1.sub2.field1);
  EXPECT_EQ(cont_out.cont1.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont1.sub2.field2,         cont_in.cont1.sub2.field2);
  EXPECT_EQ(cont_out.cont1.field1,              cont_in.cont1.field1);
  EXPECT_EQ(cont_out.cont1.field1_valid,        true);
  EXPECT_EQ(cont_out.cont1.field2,              cont_in.cont1.field2);
  EXPECT_EQ(cont_out.cont1_valid,               true);

  EXPECT_EQ(cont_out.cont2.sub1.field1,         cont_in.cont2.sub1.field1);
  EXPECT_EQ(cont_out.cont2.sub1.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub1.field2,         cont_in.cont2.sub1.field2);
  EXPECT_EQ(cont_out.cont2.sub1_valid,          true);
  EXPECT_EQ(cont_out.cont2.sub2.field1,         cont_in.cont2.sub2.field1);
  EXPECT_EQ(cont_out.cont2.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub2.field2,         cont_in.cont2.sub2.field2);
  EXPECT_EQ(cont_out.cont2.field1,              cont_in.cont2.field1);
  EXPECT_EQ(cont_out.cont2.field1_valid,        true);
  EXPECT_EQ(cont_out.cont2.field2,              cont_in.cont2.field2);

  EXPECT_EQ(cont_out.cont3.sub1.field1,         cont_in.cont3.sub1.field1);
  EXPECT_EQ(cont_out.cont3.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub1.field2,         cont_in.cont3.sub1.field2);
  EXPECT_EQ(cont_out.cont3.sub1_valid,          false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field1,         cont_in.cont3.sub2.field1);
  EXPECT_EQ(cont_out.cont3.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field2,         cont_in.cont3.sub2.field2);
  EXPECT_EQ(cont_out.cont3.field1,              cont_in.cont3.field1);
  EXPECT_EQ(cont_out.cont3.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.field2,              cont_in.cont3.field2);
  EXPECT_EQ(cont_out.cont3_valid,               true);

  EXPECT_EQ(cont_out.cont4.sub1.field1,         cont_in.cont4.sub1.field1);
  EXPECT_EQ(cont_out.cont4.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub1.field2,         cont_in.cont4.sub1.field2);
  EXPECT_EQ(cont_out.cont4.sub1_valid,          true);                      // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field1,         cont_in.cont4.sub2.field1);
  EXPECT_EQ(cont_out.cont4.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field2,         cont_in.cont4.sub2.field2);
  EXPECT_EQ(cont_out.cont4.field1,              cont_in.cont4.field1);
  EXPECT_EQ(cont_out.cont4.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.field2,              cont_in.cont4.field2);

  EXPECT_EQ(cont_out.field1,                    cont_in.field1);
  EXPECT_EQ(cont_out.field1_valid,              true);

  EXPECT_EQ(cont_out.field2,                    cont_in.field2);

  // stop & cleanup
  test_in.stop();
  test_in.cleanup();

  test_out.stop();
  test_out.cleanup();

  concate.stop();
  concate.cleanup();
}

// Tests MessageConcate class for data valid on some input ports.
TEST(MessageConcateTest, InvalidCaughtOnTheSameLevel) {
  // the component under test
  MessageConcate<Container_Ports > concate("concate");
  concate.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( concate.configure() );
  EXPECT_TRUE( concate.start() );
  EXPECT_EQ( concate.ports()->getPortNames().size(), 17);

  // component that writes data on input ports of the component under test
  TestComponentIn test_in("test_in");
  test_in.setActivity( new RTT::extras::SlaveActivity() );
  std::vector<std::string > not_connected_ports;
  not_connected_ports.push_back("Container_cont1_sub1_field1");
  EXPECT_TRUE( test_in.connectPorts(&concate, not_connected_ports) );
  EXPECT_TRUE( test_in.configure() );
  EXPECT_TRUE( test_in.start() );

  // component that reads data from output port of the component under test
  TestComponentOut test_out("test_out");
  test_out.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( test_out.connectPorts(&concate) );
  EXPECT_TRUE( test_out.configure() );
  EXPECT_TRUE( test_out.start() );

  // generate some data
  Container cont_in;
  initContainerData(cont_in);

  // load the data into test_in component
  test_in.setData( cont_in );

  // execute all components
  test_in.getActivity()->execute();
  concate.getActivity()->execute();
  test_out.getActivity()->execute();

  // get the result data
  Container cont_out = test_out.getData();

  // check the data

  EXPECT_EQ(cont_out.cont1.sub1.field1,         0);         // invalid values are set to default values
  EXPECT_EQ(cont_out.cont1.sub1.field1_valid,   false);     // this was not connected, so it is invalid
  EXPECT_EQ(cont_out.cont1.sub1.field2,         cont_in.cont1.sub1.field2);
  EXPECT_EQ(cont_out.cont1.sub1_valid,          true);
  EXPECT_EQ(cont_out.cont1.sub2.field1,         cont_in.cont1.sub2.field1);
  EXPECT_EQ(cont_out.cont1.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont1.sub2.field2,         cont_in.cont1.sub2.field2);
  EXPECT_EQ(cont_out.cont1.field1,              cont_in.cont1.field1);
  EXPECT_EQ(cont_out.cont1.field1_valid,        true);
  EXPECT_EQ(cont_out.cont1.field2,              cont_in.cont1.field2);
  EXPECT_EQ(cont_out.cont1_valid,               true);

  EXPECT_EQ(cont_out.cont2.sub1.field1,         cont_in.cont2.sub1.field1);
  EXPECT_EQ(cont_out.cont2.sub1.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub1.field2,         cont_in.cont2.sub1.field2);
  EXPECT_EQ(cont_out.cont2.sub1_valid,          true);
  EXPECT_EQ(cont_out.cont2.sub2.field1,         cont_in.cont2.sub2.field1);
  EXPECT_EQ(cont_out.cont2.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub2.field2,         cont_in.cont2.sub2.field2);
  EXPECT_EQ(cont_out.cont2.field1,              cont_in.cont2.field1);
  EXPECT_EQ(cont_out.cont2.field1_valid,        true);
  EXPECT_EQ(cont_out.cont2.field2,              cont_in.cont2.field2);

  EXPECT_EQ(cont_out.cont3.sub1.field1,         cont_in.cont3.sub1.field1);
  EXPECT_EQ(cont_out.cont3.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub1.field2,         cont_in.cont3.sub1.field2);
  EXPECT_EQ(cont_out.cont3.sub1_valid,          false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field1,         cont_in.cont3.sub2.field1);
  EXPECT_EQ(cont_out.cont3.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field2,         cont_in.cont3.sub2.field2);
  EXPECT_EQ(cont_out.cont3.field1,              cont_in.cont3.field1);
  EXPECT_EQ(cont_out.cont3.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.field2,              cont_in.cont3.field2);
  EXPECT_EQ(cont_out.cont3_valid,               true);

  EXPECT_EQ(cont_out.cont4.sub1.field1,         cont_in.cont4.sub1.field1);
  EXPECT_EQ(cont_out.cont4.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub1.field2,         cont_in.cont4.sub1.field2);
  EXPECT_EQ(cont_out.cont4.sub1_valid,          true);                      // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field1,         cont_in.cont4.sub2.field1);
  EXPECT_EQ(cont_out.cont4.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field2,         cont_in.cont4.sub2.field2);
  EXPECT_EQ(cont_out.cont4.field1,              cont_in.cont4.field1);
  EXPECT_EQ(cont_out.cont4.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.field2,              cont_in.cont4.field2);

  EXPECT_EQ(cont_out.field1,                    cont_in.field1);
  EXPECT_EQ(cont_out.field1_valid,              true);

  EXPECT_EQ(cont_out.field2,                    cont_in.field2);

  // stop & cleanup
  test_in.stop();
  test_in.cleanup();

  test_out.stop();
  test_out.cleanup();

  concate.stop();
  concate.cleanup();
}


// Tests MessageConcate class for data valid on some input ports.
TEST(MessageConcateTest, InvalidCaughtOnHigherLevel) {
  // the component under test
  MessageConcate<Container_Ports > concate("concate");
  concate.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( concate.configure() );
  EXPECT_TRUE( concate.start() );
  EXPECT_EQ( concate.ports()->getPortNames().size(), 17);

  // component that writes data on input ports of the component under test
  TestComponentIn test_in("test_in");
  test_in.setActivity( new RTT::extras::SlaveActivity() );
  std::vector<std::string > not_connected_ports;
  not_connected_ports.push_back("Container_cont1_sub1_field2");
  EXPECT_TRUE( test_in.connectPorts(&concate, not_connected_ports) );
  EXPECT_TRUE( test_in.configure() );
  EXPECT_TRUE( test_in.start() );

  // component that reads data from output port of the component under test
  TestComponentOut test_out("test_out");
  test_out.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( test_out.connectPorts(&concate) );
  EXPECT_TRUE( test_out.configure() );
  EXPECT_TRUE( test_out.start() );

  // generate some data
  Container cont_in;
  initContainerData(cont_in);

  // load the data into test_in component
  test_in.setData( cont_in );

  // execute all components
  test_in.getActivity()->execute();
  concate.getActivity()->execute();
  test_out.getActivity()->execute();

  // get the result data
  Container cont_out = test_out.getData();

  // check the data

  EXPECT_EQ(cont_out.cont1.sub1.field1,         0);     // invalid values are set to default values
  EXPECT_EQ(cont_out.cont1.sub1.field1_valid,   false); // invalid values are set to default values
  EXPECT_EQ(cont_out.cont1.sub1.field2,         0);     // this was not connected, so the whole container is invalid
  EXPECT_EQ(cont_out.cont1.sub1_valid,          false);
  EXPECT_EQ(cont_out.cont1.sub2.field1,         cont_in.cont1.sub2.field1);
  EXPECT_EQ(cont_out.cont1.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont1.sub2.field2,         cont_in.cont1.sub2.field2);
  EXPECT_EQ(cont_out.cont1.field1,              cont_in.cont1.field1);
  EXPECT_EQ(cont_out.cont1.field1_valid,        true);
  EXPECT_EQ(cont_out.cont1.field2,              cont_in.cont1.field2);
  EXPECT_EQ(cont_out.cont1_valid,               true);

  EXPECT_EQ(cont_out.cont2.sub1.field1,         cont_in.cont2.sub1.field1);
  EXPECT_EQ(cont_out.cont2.sub1.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub1.field2,         cont_in.cont2.sub1.field2);
  EXPECT_EQ(cont_out.cont2.sub1_valid,          true);
  EXPECT_EQ(cont_out.cont2.sub2.field1,         cont_in.cont2.sub2.field1);
  EXPECT_EQ(cont_out.cont2.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub2.field2,         cont_in.cont2.sub2.field2);
  EXPECT_EQ(cont_out.cont2.field1,              cont_in.cont2.field1);
  EXPECT_EQ(cont_out.cont2.field1_valid,        true);
  EXPECT_EQ(cont_out.cont2.field2,              cont_in.cont2.field2);

  EXPECT_EQ(cont_out.cont3.sub1.field1,         cont_in.cont3.sub1.field1);
  EXPECT_EQ(cont_out.cont3.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub1.field2,         cont_in.cont3.sub1.field2);
  EXPECT_EQ(cont_out.cont3.sub1_valid,          false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field1,         cont_in.cont3.sub2.field1);
  EXPECT_EQ(cont_out.cont3.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field2,         cont_in.cont3.sub2.field2);
  EXPECT_EQ(cont_out.cont3.field1,              cont_in.cont3.field1);
  EXPECT_EQ(cont_out.cont3.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.field2,              cont_in.cont3.field2);
  EXPECT_EQ(cont_out.cont3_valid,               true);

  EXPECT_EQ(cont_out.cont4.sub1.field1,         cont_in.cont4.sub1.field1);
  EXPECT_EQ(cont_out.cont4.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub1.field2,         cont_in.cont4.sub1.field2);
  EXPECT_EQ(cont_out.cont4.sub1_valid,          true);                      // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field1,         cont_in.cont4.sub2.field1);
  EXPECT_EQ(cont_out.cont4.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field2,         cont_in.cont4.sub2.field2);
  EXPECT_EQ(cont_out.cont4.field1,              cont_in.cont4.field1);
  EXPECT_EQ(cont_out.cont4.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.field2,              cont_in.cont4.field2);

  EXPECT_EQ(cont_out.field1,                    cont_in.field1);
  EXPECT_EQ(cont_out.field1_valid,              true);

  EXPECT_EQ(cont_out.field2,                    cont_in.field2);

  // stop & cleanup
  test_in.stop();
  test_in.cleanup();

  test_out.stop();
  test_out.cleanup();

  concate.stop();
  concate.cleanup();
}


// Tests MessageConcate class for data valid on some input ports.
TEST(MessageConcateTest, InvalidCaughtOnHighestLevel) {
  // the component under test
  MessageConcate<Container_Ports > concate("concate");
  concate.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( concate.configure() );
  EXPECT_TRUE( concate.start() );
  EXPECT_EQ( concate.ports()->getPortNames().size(), 17);

  // component that writes data on input ports of the component under test
  TestComponentIn test_in("test_in");
  test_in.setActivity( new RTT::extras::SlaveActivity() );
  std::vector<std::string > not_connected_ports;
  not_connected_ports.push_back("Container_cont2_sub2_field2");
  EXPECT_TRUE( test_in.connectPorts(&concate, not_connected_ports) );
  EXPECT_TRUE( test_in.configure() );
  EXPECT_TRUE( test_in.start() );

  // component that reads data from output port of the component under test
  TestComponentOut test_out("test_out");
  test_out.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( test_out.connectPorts(&concate) );
  EXPECT_TRUE( test_out.configure() );
  EXPECT_TRUE( test_out.start() );

  // generate some data
  Container cont_in;
  initContainerData(cont_in);

  // load the data into test_in component
  test_in.setData( cont_in );

  // execute all components
  test_in.getActivity()->execute();
  concate.getActivity()->execute();
  test_out.getActivity()->execute();

  // get the result data
  Container cont_out = test_out.getData();

  // check the data (all values are invalid)
  EXPECT_EQ(cont_out.cont1.sub1.field1,         0);
  EXPECT_EQ(cont_out.cont1.sub1.field1_valid,   false);
  EXPECT_EQ(cont_out.cont1.sub1.field2,         0);
  EXPECT_EQ(cont_out.cont1.sub1_valid,          false);
  EXPECT_EQ(cont_out.cont1.sub2.field1,         0);
  EXPECT_EQ(cont_out.cont1.sub2.field1_valid,   false);
  EXPECT_EQ(cont_out.cont1.sub2.field2,         0);
  EXPECT_EQ(cont_out.cont1.field1,              0.0);
  EXPECT_EQ(cont_out.cont1.field1_valid,        false);
  EXPECT_EQ(cont_out.cont1.field2,              0.0);
  EXPECT_EQ(cont_out.cont1_valid,               false);

  EXPECT_EQ(cont_out.cont2.sub1.field1,         0);
  EXPECT_EQ(cont_out.cont2.sub1.field1_valid,   false);
  EXPECT_EQ(cont_out.cont2.sub1.field2,         0);
  EXPECT_EQ(cont_out.cont2.sub1_valid,          false);
  EXPECT_EQ(cont_out.cont2.sub2.field1,         0);
  EXPECT_EQ(cont_out.cont2.sub2.field1_valid,   false);
  EXPECT_EQ(cont_out.cont2.sub2.field2,         0);
  EXPECT_EQ(cont_out.cont2.field1,              0.0);
  EXPECT_EQ(cont_out.cont2.field1_valid,        false);
  EXPECT_EQ(cont_out.cont2.field2,              0.0);

  EXPECT_EQ(cont_out.cont3.sub1.field1,         0);
  EXPECT_EQ(cont_out.cont3.sub1.field1_valid,   false);
  EXPECT_EQ(cont_out.cont3.sub1.field2,         0);
  EXPECT_EQ(cont_out.cont3.sub1_valid,          false);
  EXPECT_EQ(cont_out.cont3.sub2.field1,         0);
  EXPECT_EQ(cont_out.cont3.sub2.field1_valid,   false);
  EXPECT_EQ(cont_out.cont3.sub2.field2,         0);
  EXPECT_EQ(cont_out.cont3.field1,              0.0);
  EXPECT_EQ(cont_out.cont3.field1_valid,        false);
  EXPECT_EQ(cont_out.cont3.field2,              0.0);

  EXPECT_EQ(cont_out.cont4.sub1.field1,         0);
  EXPECT_EQ(cont_out.cont4.sub1.field1_valid,   false);
  EXPECT_EQ(cont_out.cont4.sub1.field2,         0);
  EXPECT_EQ(cont_out.cont4.sub1_valid,          false);
  EXPECT_EQ(cont_out.cont4.sub2.field1,         0);
  EXPECT_EQ(cont_out.cont4.sub2.field1_valid,   false);
  EXPECT_EQ(cont_out.cont4.sub2.field2,         0);
  EXPECT_EQ(cont_out.cont4.field1,              0.0);
  EXPECT_EQ(cont_out.cont4.field1_valid,        false);
  EXPECT_EQ(cont_out.cont4.field2,              0.0);

  EXPECT_EQ(cont_out.field1,                    0);
  EXPECT_EQ(cont_out.field1_valid,              false);

  EXPECT_EQ(cont_out.field2,                    0);

  // stop & cleanup
  test_in.stop();
  test_in.cleanup();

  test_out.stop();
  test_out.cleanup();

  concate.stop();
  concate.cleanup();
}


// Tests MessageConcate class for data valid on some input ports.
TEST(MessageConcateTest, InvalidCaughtOnMiddleLevel) {
  // the component under test
  MessageConcate<Container_Ports > concate("concate");
  concate.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( concate.configure() );
  EXPECT_TRUE( concate.start() );
  EXPECT_EQ( concate.ports()->getPortNames().size(), 17);

  // component that writes data on input ports of the component under test
  TestComponentIn test_in("test_in");
  test_in.setActivity( new RTT::extras::SlaveActivity() );
  std::vector<std::string > not_connected_ports;
  not_connected_ports.push_back("Container_cont1_sub2_field2");
  EXPECT_TRUE( test_in.connectPorts(&concate, not_connected_ports) );
  EXPECT_TRUE( test_in.configure() );
  EXPECT_TRUE( test_in.start() );

  // component that reads data from output port of the component under test
  TestComponentOut test_out("test_out");
  test_out.setActivity( new RTT::extras::SlaveActivity() );
  EXPECT_TRUE( test_out.connectPorts(&concate) );
  EXPECT_TRUE( test_out.configure() );
  EXPECT_TRUE( test_out.start() );

  // generate some data
  Container cont_in;
  initContainerData(cont_in);

  // load the data into test_in component
  test_in.setData( cont_in );

  // execute all components
  test_in.getActivity()->execute();
  concate.getActivity()->execute();
  test_out.getActivity()->execute();

  // get the result data
  Container cont_out = test_out.getData();

  // check the data (only the high level container is invalid)
  EXPECT_EQ(cont_out.cont1.sub1.field1,         0);
  EXPECT_EQ(cont_out.cont1.sub1.field1_valid,   false);
  EXPECT_EQ(cont_out.cont1.sub1.field2,         0);
  EXPECT_EQ(cont_out.cont1.sub1_valid,          false);
  EXPECT_EQ(cont_out.cont1.sub2.field1,         0);
  EXPECT_EQ(cont_out.cont1.sub2.field1_valid,   false);
  EXPECT_EQ(cont_out.cont1.sub2.field2,         0);
  EXPECT_EQ(cont_out.cont1.field1,              0.0);
  EXPECT_EQ(cont_out.cont1.field1_valid,        false);
  EXPECT_EQ(cont_out.cont1.field2,              0.0);
  EXPECT_EQ(cont_out.cont1_valid,               false);

  EXPECT_EQ(cont_out.cont2.sub1.field1,         cont_in.cont2.sub1.field1);
  EXPECT_EQ(cont_out.cont2.sub1.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub1.field2,         cont_in.cont2.sub1.field2);
  EXPECT_EQ(cont_out.cont2.sub1_valid,          true);
  EXPECT_EQ(cont_out.cont2.sub2.field1,         cont_in.cont2.sub2.field1);
  EXPECT_EQ(cont_out.cont2.sub2.field1_valid,   true);
  EXPECT_EQ(cont_out.cont2.sub2.field2,         cont_in.cont2.sub2.field2);
  EXPECT_EQ(cont_out.cont2.field1,              cont_in.cont2.field1);
  EXPECT_EQ(cont_out.cont2.field1_valid,        true);
  EXPECT_EQ(cont_out.cont2.field2,              cont_in.cont2.field2);

  EXPECT_EQ(cont_out.cont3.sub1.field1,         cont_in.cont3.sub1.field1);
  EXPECT_EQ(cont_out.cont3.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub1.field2,         cont_in.cont3.sub1.field2);
  EXPECT_EQ(cont_out.cont3.sub1_valid,          false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.sub2.field1,         cont_in.cont3.sub2.field1);
  EXPECT_EQ(cont_out.cont3.sub2.field1_valid,   false);
  EXPECT_EQ(cont_out.cont3.sub2.field2,         cont_in.cont3.sub2.field2);
  EXPECT_EQ(cont_out.cont3.field1,              cont_in.cont3.field1);
  EXPECT_EQ(cont_out.cont3.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont3.field2,              cont_in.cont3.field2);
  EXPECT_EQ(cont_out.cont3_valid,               true);

  EXPECT_EQ(cont_out.cont4.sub1.field1,         cont_in.cont4.sub1.field1);
  EXPECT_EQ(cont_out.cont4.sub1.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub1.field2,         cont_in.cont4.sub1.field2);
  EXPECT_EQ(cont_out.cont4.sub1_valid,          true);                      // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field1,         cont_in.cont4.sub2.field1);
  EXPECT_EQ(cont_out.cont4.sub2.field1_valid,   false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.sub2.field2,         cont_in.cont4.sub2.field2);
  EXPECT_EQ(cont_out.cont4.field1,              cont_in.cont4.field1);
  EXPECT_EQ(cont_out.cont4.field1_valid,        false);                     // this field is set manually
  EXPECT_EQ(cont_out.cont4.field2,              cont_in.cont4.field2);

  EXPECT_EQ(cont_out.field1,                    cont_in.field1);
  EXPECT_EQ(cont_out.field1_valid,              true);

  EXPECT_EQ(cont_out.field2,                    cont_in.field2);

  // stop & cleanup
  test_in.stop();
  test_in.cleanup();

  test_out.stop();
  test_out.cleanup();

  concate.stop();
  concate.cleanup();
}

};  // namespace message_concate_tests
