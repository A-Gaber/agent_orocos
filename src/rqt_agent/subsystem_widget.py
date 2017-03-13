#!/usr/bin/env python

# Copyright (c) 2011, Dorian Scholz, TU Darmstadt
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#   * Neither the name of the TU Darmstadt nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import division
import os
import math
import subprocess

from python_qt_binding import loadUi
from python_qt_binding.QtCore import Qt, QTimer, Signal, Slot, QRectF, QPointF
from python_qt_binding.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QListWidgetItem, QDialog, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPathItem, QTableWidgetItem
from python_qt_binding.QtGui import QColor, QPen, QBrush, QPainterPath, QPolygonF, QTransform
import roslib
import rospkg
import rospy
from rospy.exceptions import ROSException

import xml.dom.minidom as minidom

from rqt_topic.topic_info import TopicInfo

from subsystem_msgs.srv import *

def getComponentBrush(state):
    b = QBrush(QColor(0,0,255)) # unconfigured/preoperational
    if state == 'S':      # stopped
        b = QBrush(QColor(255,255,255))
    elif state == 'R':    # running
        b = QBrush(QColor(0,255,0))
    elif state == 'E':    # error
        b = QBrush(QColor(255,0,0))
    elif state == 'F':    # fatal error
        b = QBrush(QColor(255,127,127))
    elif state == 'X':    # exception
        b = QBrush(QColor(0,255,255))
    return b

def getComponentTooltip(state):
    tooltip = 'unconfigured/preoperational'
    if state == 'S':      # stopped
        tooltip = 'stopped'
    elif state == 'R':    # running
        tooltip = 'running'
    elif state == 'E':    # error
        tooltip = 'error'
    elif state == 'F':    # fatal error
        tooltip = 'fatal error'
    elif state == 'X':    # exception
        tooltip = 'exception'
    return tooltip

class GraphScene(QGraphicsScene):
    def __init__(self, rect):
        super(GraphScene, self).__init__(rect)

class GraphView(QGraphicsView):

    comp_select_signal = Signal(str)

    def __init__ (self, parent = None):
        super (GraphView, self).__init__ (parent)
        self.parent = parent
        self.transform_press = None
        self.mousePressPos = None
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)

    def isPanActive(self):
        return (self.transform_press != None and self.mousePressPos != None)

    def wheelEvent (self, event):
        if self.isPanActive():
            return

        oldPos = self.mapToScene(event.pos())
        self.translate(oldPos.x(),oldPos.y())

        factor = 1.2
        if event.angleDelta().y() < 0 :
            factor = 1.0 / factor
        self.scale(factor, factor)

        # Get the new position
        newPos = self.mapToScene(event.pos())
        # Move scene to old position
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())

    def selectComponent(self, name):
#        print "selected component: ", name
        self.comp_select_signal.emit(name)

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            self.transform_press = self.transform()
            self.mousePressPos = event.pos()
        else:
            super(GraphView, self).mousePressEvent(event)
            selected = False
            for item in self.items():
                if type(item) is QGraphicsEllipseItem:
                    if item.contains( self.mapToScene(event.pos()) ):
                        self.selectComponent(item.data(0))
                        selected = True
                        break
                elif type(item) is QGraphicsPathItem:
                    if item.contains( self.mapToScene(event.pos()) ):
                        print "connections: ", item.data(0)
            if not selected:
                self.selectComponent(None)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MidButton:
            mouseMovePos = event.pos()
            view_diff = (mouseMovePos - self.mousePressPos)
            tf = self.transform_press
            scene_diff = view_diff
            new_tf = QTransform(tf.m11(), tf.m12(), tf.m21(), tf.m22(), tf.dx()+view_diff.x(), tf.dy()+view_diff.y())
            self.setTransform(new_tf)
        else:
            super(GraphView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MidButton:
            self.transform_press = None
            self.mousePressPos = None
        else:
            super(GraphView, self).mouseReleaseEvent(event)

class MyDialog(QDialog):

    def scX(self, x):
        return self.scale_factor * float(x)

    def scY(self, y):
        return self.scale_factor * float(y)

    def tfX(self, x):
        return self.scale_factor * float(x)

    def tfY(self, y):
        return self.scale_factor * (self.height - float(y))

    @Slot(int)
    def portSelected(self, index):
        for e in self.prev_selected_connections:
            e.setPen( QPen(QBrush(QColor(0,0,0)), 0) )
        self.prev_selected_connections = []

        if not self.component_selected:
            return

        for conn in self.parent.all_connections:
            if (conn[0] == self.component_selected and conn[1] == self.selected_component_port_names[index]) or \
                (conn[2] == self.component_selected and conn[3] == self.selected_component_port_names[index]):
                for e in self.edges:
                    data = e.data(0)
                    if (data[0] == conn[0] and data[1] == conn[2]) or \
                        (data[0] == conn[2] and data[1] == conn[0]):
                        e.setPen( QPen(QBrush(QColor(255,0,0)), 5) )
                        self.prev_selected_connections.append(e)

    @Slot(str)
    def componentSelected(self, name):
        self.comboBoxConnections.clear()
        self.component_selected = name

        if name == None:
            self.labelSelectedComponent.setText('')
            return

        self.labelSelectedComponent.setText(name)
        for comp in self.parent.subsystem_info.components:
            if comp.name == name:
                self.selected_component_port_names = []
                for p in comp.ports:
                    self.selected_component_port_names.append(p.name)
                    port_str = ''
                    if p.is_input:
                        port_str += '[IN]'
                    else:
                        port_str += '[OUT]'
                    port_str += ' ' + p.name
                    if p.is_connected:
                        port_str += ' <conncected>'
                    else:
                        port_str += ' <not conncected>'
                    type_str = ''
                    for tn in p.type_names:
                        type_str += ' ' + tn
                    if len(type_str) == 0:
                        type_str = 'unknown type'
                    port_str += ', type:' + type_str
                    self.comboBoxConnections.addItem(port_str)
                break

    def __init__(self, subsystem_name, parent=None):
        super(MyDialog, self).__init__(parent)

        self.parent = parent

        self.setWindowFlags(Qt.Window)

        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('rqt_agent'), 'resource', 'GraphVis.ui')
        loadUi(ui_file, self)

        self.setWindowTitle(subsystem_name + " - transition function")
        self.components_state = None
        self.initialized = False

        self.pushButton_close.clicked.connect(self.closeClick)
        self.pushButton_zoom_in.clicked.connect(self.zoomInClick)
        self.pushButton_zoom_out.clicked.connect(self.zoomOutClick)

        self.prev_selected_connections = []
        self.comboBoxConnections.highlighted.connect(self.portSelected)

        self.componentSelected(None)

    def drawGraph(self, graph_file_name):
        self.graph = None
        try:
            with open(graph_file_name, 'r') as f:
                self.graph = f.read().splitlines()
        except (IOError, OSError) as e:
            print "caught exception: ", e
            return

        header = self.graph[0].split()
        if header[0] != 'graph':
            raise Exception('wrong graph format', 'header is: ' + self.graph[0])

        self.scale_factor = 100.0
        self.width = float(header[2])
        self.height = float(header[3])
        print "QGraphicsScene size:", self.width, self.height

        self.scene = GraphScene(QRectF(0, 0, self.scX(self.width), self.scY(self.height)))

        self.nodes = {}
        self.edges = []

        for l in self.graph:
            items = l.split()
            if len(items) == 0:
                continue
            elif items[0] == 'stop':
                break
            elif items[0] == 'node':
                #node CImp 16.472 5.25 0.86659 0.5 CImp filled ellipse lightblue lightblue
                if len(items) != 11:
                    raise Exception('wrong number of items in line', 'line is: ' + l)
                name = items[1]
                w = self.scX(items[4])
                h = self.scY(items[5])
                x = self.tfX(items[2])
                y = self.tfY(items[3])

                self.nodes[name] = self.scene.addEllipse(x - w/2, y - h/2, w, h)
                self.nodes[name].setData(0, name)
                text_item = self.scene.addSimpleText(name)
                br = text_item.boundingRect()
                text_item.setPos(x - br.width()/2, y - br.height()/2)

            elif items[0] == 'edge':
                # edge CImp Ts 4 16.068 5.159 15.143 4.9826 12.876 4.5503 11.87 4.3583 solid black
                line_len = int(items[3])
                if (line_len * 2 + 6) != len(items):
                    raise Exception('wrong number of items in line', 'should be: ' + str(line_len * 2 + 6) + ', line is: ' + l)
                line = []
                for i in range(line_len):
                    line.append( (self.tfX(items[4+i*2]), self.tfY(items[5+i*2])) )

                control_points_idx = 1
                path = QPainterPath(QPointF(line[0][0], line[0][1]))
                while True:
                    q1 = line[control_points_idx]
                    q2 = line[control_points_idx+1]
                    p2 = line[control_points_idx+2]
                    path.cubicTo( q1[0], q1[1], q2[0], q2[1], p2[0], p2[1] )
                    control_points_idx = control_points_idx + 3
                    if control_points_idx >= len(line):
                        break
                edge = self.scene.addPath(path)
                edge.setData(0, (items[1], items[2]))
                self.edges.append(edge)

                end_p = QPointF(line[-1][0], line[-1][1])
                p0 = end_p - QPointF(line[-2][0], line[-2][1])
                p0_norm = math.sqrt(p0.x()*p0.x() + p0.y()*p0.y())
                p0 = p0 / p0_norm
                p0 = p0 * self.scale_factor * 0.15
                p1 = QPointF(p0.y(), -p0.x()) * 0.25
                p2 = -p1

                poly = QPolygonF()
                poly.append(p0+end_p)
                poly.append(p1+end_p)
                poly.append(p2+end_p)
                poly.append(p0+end_p)

#                poly_path = QPainterPath()
#                poly_path.addPolygon(poly)
#                painter = QPainter()
                self.scene.addPolygon(poly)

        self.graphicsView = GraphView()
        self.verticalLayout.insertWidget(0, self.graphicsView)
        self.graphicsView.setScene(self.scene)

        self.graphicsView.comp_select_signal.connect(self.componentSelected)

        self.initialized = True

    @Slot()
    def closeClick(self):
        self.close()

    @Slot()
    def zoomInClick(self):
        if not self.initialized:
            return

        scaleFactor = 1.1
        self.graphicsView.scale(scaleFactor, scaleFactor)

    @Slot()
    def zoomOutClick(self):
        if not self.initialized:
            return

        scaleFactor = 1.0/1.1
        self.graphicsView.scale(scaleFactor, scaleFactor)

    def updateState(self, components_state):
        if not self.initialized:
            return

        changed = False
        if self.components_state == None:
            changed = True
        else:
            for comp_name in self.components_state:
                if self.components_state[comp_name] != components_state[comp_name]:
                    changed = True
                    break

        if changed:
            self.components_state = components_state
            for comp_name in self.nodes:
                if comp_name in self.components_state:
                    self.nodes[comp_name].setBrush(getComponentBrush(self.components_state[comp_name]))

#    def wheelEvent(self, event):
#        print dir(event)
#        print event.delta()
#        ui->graphicsView->setTransformationAnchor(QGraphicsView::AnchorUnderMouse);
#        // Scale the view / do the zoom
#        double scaleFactor = 1.15;
#        if(event->delta() > 0) {
#            // Zoom in
#            ui->graphicsView-> scale(scaleFactor, scaleFactor);
# 
#        } else {
#            // Zooming out
#             ui->graphicsView->scale(1.0 / scaleFactor, 1.0 / scaleFactor);
#        }
#        //ui->graphicsView->setTransform(QTransform(h11, h12, h21, h22, 0, 0));


class StateHistoryDialog(QDialog):

    @Slot()
    def closeClick(self):
        self.close()

    def __init__(self, subsystem_name, parent=None):
        super(StateHistoryDialog, self).__init__(parent)

        self.parent = parent

        self.setWindowFlags(Qt.Window)

        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('rqt_agent'), 'resource', 'StateHistory.ui')
        loadUi(ui_file, self)

        self.setWindowTitle(subsystem_name + " - state history")

        self.pushButton_close.clicked.connect(self.closeClick)

    def updateState(self, mcd):
        hist = mcd[0]
        if self.tableWidget.rowCount() != len(hist):
            self.tableWidget.setRowCount( len(hist) )
        row = 0
        for ss in hist:
            for col in range(4):
                self.tableWidget.setItem(row, col, QTableWidgetItem(ss[col]))
#                item.setText( ss[col] )
            row = row + 1

class SubsystemWidget(QWidget):
    """
    main class inherits from the ui window class.

    You can specify the topics that the topic pane.

    SubsystemWidget.start must be called in order to update topic pane.
    """

    SELECT_BY_NAME = 0
    SELECT_BY_MSGTYPE = 1

    _column_names = ['topic', 'type', 'bandwidth', 'rate', 'value']

# ___________________________________________________________
# |[ipc_buffers]                                             |
# |                     subsystem_name                       |
# |  master_component                                        |
# |  subsystem_state       [components]                      |
# |                        [components]                      |
# |                        [components]                      |
# |                        [components]                      |
# |                        [components]                      |
# |                                                          |
# |                                                          |
# |                                                          |
# |                                                          |
# |[ipc_buffers]                                             |
# |__________________________________________________________|

    def layout_widgets(self, layout):
       return (layout.itemAt(i) for i in range(layout.count()))

    def resetBuffersLayout(self):
        self.buffer_groups = {}
        self.lower_subsystems = []

        print self.subsystem_name, ".resetBuffersLayout()"

        for buf in self.all_buffers:
            self.all_buffers[buf].hide()

        while True:
            w = self.lower_buffers_layout.takeAt(0)
            if w == None:
                break;
            del w

        while True:
            w = self.upper_buffers_layout.takeAt(0)
            if w == None:
                break;
            del w

    @Slot()
    def on_click(self):
        #self.dialogGraph.exec_()
        self.dialogGraph.show()

    @Slot()
    def on_click_showHistory(self):
        #self.dialogGraph.exec_()
        self.dialogHistory.show()

    def __init__(self, plugin=None, name=None):
        """
        @type selected_topics: list of tuples.
        @param selected_topics: [($NAME_TOPIC$, $TYPE_TOPIC$), ...]
        @type select_topic_type: int
        @param select_topic_type: Can specify either the name of topics or by
                                  the type of topic, to filter the topics to
                                  show. If 'select_topic_type' argument is
                                  None, this arg shouldn't be meaningful.
        """
        super(SubsystemWidget, self).__init__()

        self.initialized = False

        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('rqt_agent'), 'resource', 'SubsystemWidget.ui')
        loadUi(ui_file, self)
        self._plugin = plugin

        print "created Subsystem widget"

        if name != None:
            self.SubsystemName.setText(name)
        else:
            self.SubsystemName.setText("<could not get subsystem name>")

        self.subsystem_name = name

        self.subsystem_info = None
        self.state = ''
        self.behavior = ''

        self.all_buffers = {}
        self.resetBuffersLayout()

        self.components = {}

        self.graph = None

        self.dialogGraph = MyDialog(self.subsystem_name, self)
        self.showGraph.clicked.connect(self.on_click)

        self.dialogHistory = StateHistoryDialog(self.subsystem_name, self)
        self.showHistory.clicked.connect(self.on_click_showHistory)

    def isInitialized(self):
        return self.initialized

    class Graph:
        class Options:
            def toStr(self):
                result = ''
                if self.style:
                    result = result + "style=" + self.style + ','

                if self.width:
                    result = result + "width=" + self.width + ','

                if self.height:
                    result = result + "height=" + self.height + ','

                if self.color:
                    result = result + "color=" + self.color + ','

                if self.shape:
                    result = result + "shape=" + self.shape + ','

                if self.label:
                    result = result + "label=" + self.label + ','

                if result == '':
                    return None

                return result[:-1]      # remove trailing ','

            def getOption(self, options_str, option):
                idx = options_str.find(option)
                if idx == -1:
                    return None

                idx = options_str.find('=', idx)
                if idx == -1:
                    raise Exception('option has no \'=\'', 'option: ' + option + ', options_str: ' + options_str)
                comma_idx = options_str.find(',', idx)
                bracket_idx = options_str.find(']', idx)
                if comma_idx == -1 and bracket_idx == -1:
                    value = options_str[idx+1:]
                elif comma_idx == -1:
                    value = options_str[idx+1:bracket_idx]
                elif bracket_idx == -1:
                    value = options_str[idx+1:comma_idx]
                else:
                    value = options_str[idx+1:min(bracket_idx, comma_idx)]
                value = value.strip()
                return value

            def __init__(self, options_str=None):
                if options_str:
                    self.style = self.getOption(options_str, "style")
                    self.width = self.getOption(options_str, "width")
                    self.height = self.getOption(options_str, "height")
                    self.color = self.getOption(options_str, "color")
                    self.shape = self.getOption(options_str, "shape")
                    self.label = self.getOption(options_str, "label")
                else:
                    self.style = None
                    self.width = None
                    self.height = None
                    self.color = None
                    self.shape = None
                    self.label = None
            

        def clear(self):
            self.edges = []
            self.vertices = []
            self.ranks = []

        def parseDot(self, dot_graph):
            self.clear()

            for l in dot_graph:
                brackets_beg = l.find('[')
                if brackets_beg == -1:
                    continue
                brackets_end = l.find(']', brackets_beg)
                data = l[:brackets_beg]
                options = l[brackets_beg+1:brackets_end]
                edge_sign = data.find('->')
                if edge_sign > 0:
                    edge_from = data[:edge_sign]
                    edge_to = data[edge_sign+2:]
                    self.edges.append( (edge_from, edge_to, self.Options(options)) )
                else:
                    self.vertices.append( (data, self.Options(options)) )

        def __init__(self, dot_graph=None):
            self.clear()

            if dot_graph:
                self.parseDot(dot_graph)

        def toStr(self):
            lines = []
            lines.append('digraph G {\n')
            lines.append('rankdir=TB;\n')
            for v in self.vertices:
                options_str = v[1].toStr()
                if options_str:
                    options_str = '[' + options_str + ']'
                else:
                    options_str = ''
                lines.append(v[0] + options_str + ';\n')

            for e in self.edges:
                options_str = e[2].toStr()
                if options_str:
                    options_str = '[' + options_str + ']'
                else:
                    options_str = ''

                lines.append(e[0] + '->' + e[1] + options_str + ';\n')

            for rank in self.ranks:
                lines.append(rank)
            lines.append('}\n')
            return lines

        def addRank(self, name_list, rank_type='same'):
            if name_list == None or len(name_list) == 0:
                return

            rank_line = "{ rank=" + rank_type + "; "
            for name in name_list:
                rank_line = rank_line + ' "' + name + '"'
            rank_line = rank_line + ' }\n'

            self.ranks.append(rank_line)

    def extractConnectionInfo(self, conn, comp_from, comp_to):
        if (not comp_to) or (not comp_from):
            print 'WARNING: wrong edge(1): ', conn, comp_from, comp_to
            return None

        if conn.find(comp_from.name) != 0:
            print 'WARNING: wrong edge(2): ', conn, comp_from.name, comp_to.name
            return None

        idx = len(comp_from.name)
        port_from = None
        for p in comp_from.ports:
            if conn.find(p.name, idx) == idx:
                port_from = p.name
                idx += len(p.name)
                break

        if not port_from:
            print 'WARNING: wrong edge(3): ', conn, comp_from.name, comp_to.name
            return None

        if conn.find(comp_to.name, idx) != idx:
            print 'WARNING: wrong edge(4): ', conn, comp_from.name, comp_to.name

        idx += len(comp_to.name)

        port_to = None
        for p in comp_to.ports:
            if conn.find(p.name, idx) == idx:
                port_to = p.name
                idx += len(p.name)
                break

        if not port_to:
            print 'WARNING: wrong edge(5): ', conn, comp_from.name, comp_to.name
            return None

        return (comp_from.name, port_from, comp_to.name, port_to)

    def parseMasterComponentDiag(self, state):
        ss_history = []
        ret_period = "?"

        dom = minidom.parseString(state)
        mcd = dom.getElementsByTagName("mcd")
        if len(mcd) != 1:
            return (ss_history, ret_period)

        hist = mcd[0].getElementsByTagName("h")
        if len(hist) == 1:
            ss_list = hist[0].getElementsByTagName("ss")
            for ss in ss_list:
#                print "ss", ss
#                print dir(ss.getAttribute("n")) # string
                ss_history.append( (ss.getAttribute("n"), ss.getAttribute("r"), ss.getAttribute("t"), ss.getAttribute("e")) )

        period = mcd[0].getElementsByTagName("p")
        if len(period) == 1:
            ret_period = period[0].childNodes[0].data

        return (ss_history, ret_period)

    def update_subsystem(self, msg):
        for value in msg.status[1].values:
            if value.key == 'master_component':
                self.state = value.value
            elif value.key[-2:] == 'Rx' or value.key[-2:] == 'Tx':
                if value.key[0:-2] in self.all_buffers:
                    if value.value == '<data ok>':
                        self.all_buffers[value.key[:-2]].setStyleSheet("background-color: green")
                    else:
                        self.all_buffers[value.key[:-2]].setStyleSheet("background-color: red")
                    self.all_buffers[value.key[:-2]].setToolTip(value.value)

        if self.graph == None and self.initialized:
            #
            # read the dot graph from file
            #
            dot_graph = None
            try:
                with open('/tmp/' + self.subsystem_name + '.dot', 'r') as f:
                    dot_graph = f.read().splitlines()
            except (IOError, OSError) as e:
                print "caught exception: ", e

            if dot_graph != None:
                print "Read dot graph, lines:", len(dot_graph)
                self.graph = self.Graph(dot_graph)
                print "Parsed dot graph: vertices:", len(self.graph.vertices), "edges:", len(self.graph.edges)

                # remove ugly 'data' boxes
                new_graph = self.Graph()
                data_edges = {}
                for v in self.graph.vertices:
                    if v[1].shape == 'box':# and v[1].label=='"data"':
                        data_edges[v[0]] = [None, None]
                    else:
                        new_graph.vertices.append(v)
                for e in self.graph.edges:
                    if e[1] in data_edges:
                        data_edges[e[1]][0] = e[0]
                    elif e[0] in data_edges:
                        data_edges[e[0]][1] = e[1]
                    else:
                        new_graph.edges.append( e )
                for label in data_edges:
                    if data_edges[label][0] == None or data_edges[label][1] == None:
                        continue
                    options = self.Graph.Options()
                    options.label = None #label     # these labels are looong
                    new_graph.edges.append( (data_edges[label][0], data_edges[label][1], options) )

                # save all connections
                self.all_connections = []


                for conn in data_edges:
                    edge_from = data_edges[conn][0]
                    edge_to = data_edges[conn][1]

                    if (not edge_from) or (not edge_to):
                        continue

                    edge_name = conn.strip('"')
                    edge_from = edge_from.strip('"')
                    edge_to = edge_to.strip('"')

                    comp_from = None
                    comp_to = None
                    for comp in self.subsystem_info.components:
                        if comp.name == edge_from:
                            comp_from = comp
                            if comp_to:
                                break
                        if comp.name == edge_to:
                            comp_to = comp
                            if comp_from:
                                break
#                    print edge_from, edge_to, edge_name
                    conn_info = self.extractConnectionInfo(edge_name, comp_from, comp_to)
                    if conn_info:
                        self.all_connections.append(conn_info)
# TODO

                self.graph = new_graph

                # remove unconnected edges and "graph_component", "scheme", "diag" and "gazebo"
                new_graph = self.Graph()
                data_edges = []
                for v in self.graph.vertices:
                    if v[0] == '"scheme"' or v[0] == '"graph_component"' or v[0] == '"diag"' or v[0] == '"gazebo"':
                        continue
                    if v[1].shape == 'point':
                        data_edges.append(v[0])
                    else:
                        new_graph.vertices.append(v)
                        new_graph.vertices[-1][1].width = None
                        new_graph.vertices[-1][1].height = None

                for e in self.graph.edges:
                    if e[0] in data_edges or e[1] in data_edges:
                        pass
                    else:
                        new_graph.edges.append( e )

                self.graph = new_graph

                # remove multiple edges
                new_graph = self.Graph()
                data_edges = set()
                for v in self.graph.vertices:
                    new_graph.vertices.append(v)

                for e in self.graph.edges:
                    edge = (e[0], e[1])
                    if not edge in data_edges:
                        new_graph.edges.append( e )
                        data_edges.add(edge)

                # draw inputs on the top and outputs at the bottom
                if False:
                    lower_buffers_rx_tx = []
                    lower_buffers_s_c = []
                    upper_buffers_rx_tx = []
                    upper_buffers_s_c = []

                    lower_buffers_rx_tx_rank = 'same'
                    upper_buffers_rx_tx_rank = 'same'
                    for i in range(len(self.subsystem_info.lower_inputs)):
                        if self.subsystem_info.lower_inputs_ipc[i]:
                            lower_buffers_rx_tx.append(self.subsystem_info.lower_inputs[i] + "Rx")
                            lower_buffers_rx_tx_rank = 'sink'
                        else:
                            lower_buffers_rx_tx.append(self.subsystem_info.lower_inputs[i] + "Concate")
                        lower_buffers_s_c.append(self.subsystem_info.lower_inputs[i] + "Split")
                    for i in range(len(self.subsystem_info.lower_outputs)):
                        if self.subsystem_info.lower_outputs_ipc[i]:
                            lower_buffers_rx_tx.append(self.subsystem_info.lower_outputs[i] + "Tx")
                            lower_buffers_rx_tx_rank = 'sink'
                        else:
                            lower_buffers_rx_tx.append(self.subsystem_info.lower_outputs[i] + "Split")
                        lower_buffers_s_c.append(self.subsystem_info.lower_outputs[i] + "Concate")

                    for i in range(len(self.subsystem_info.upper_inputs)):
                        if self.subsystem_info.upper_inputs_ipc[i]:
                            upper_buffers_rx_tx.append(self.subsystem_info.upper_inputs[i] + "Rx")
                            upper_buffers_rx_tx_rank = 'source'
                        else:
                            upper_buffers_rx_tx.append(self.subsystem_info.upper_inputs[i] + "Concate")
                        upper_buffers_s_c.append(self.subsystem_info.upper_inputs[i] + "Split")
                    for i in range(len(self.subsystem_info.upper_outputs)):
                        if self.subsystem_info.upper_outputs_ipc[i]:
                            upper_buffers_rx_tx.append(self.subsystem_info.upper_outputs[i] + "Tx")
                            upper_buffers_rx_tx_rank = 'source'
                        else:
                            upper_buffers_rx_tx.append(self.subsystem_info.upper_outputs[i] + "Split")
                        upper_buffers_s_c.append(self.subsystem_info.upper_outputs[i] + "Concate")

                    new_graph.addRank(upper_buffers_rx_tx, rank_type=upper_buffers_rx_tx_rank)
                    new_graph.addRank(upper_buffers_s_c)
                    new_graph.addRank(lower_buffers_s_c)
                    new_graph.addRank(lower_buffers_rx_tx, rank_type=lower_buffers_rx_tx_rank)
                else:
                    buffers_rx = []
                    buffers_s = []
                    buffers_tx = []
                    buffers_c = []

                    buffers_rx_rank = 'same'
                    buffers_tx_rank = 'same'
                    for i in range(len(self.subsystem_info.lower_inputs)):
                        if self.subsystem_info.lower_inputs_ipc[i]:
                            buffers_rx.append(self.subsystem_info.lower_inputs[i] + "Rx")
                            buffers_rx_rank = 'source'
                        buffers_s.append(self.subsystem_info.lower_inputs[i] + "Split")

                    for i in range(len(self.subsystem_info.upper_inputs)):
                        if self.subsystem_info.upper_inputs_ipc[i]:
                            buffers_rx.append(self.subsystem_info.upper_inputs[i] + "Rx")
                            buffers_rx_rank = 'source'
                        buffers_s.append(self.subsystem_info.upper_inputs[i] + "Split")


                    for i in range(len(self.subsystem_info.lower_outputs)):
                        if self.subsystem_info.lower_outputs_ipc[i]:
                            buffers_tx.append(self.subsystem_info.lower_outputs[i] + "Tx")
                            buffers_tx_rank = 'sink'
                        buffers_c.append(self.subsystem_info.lower_outputs[i] + "Concate")
                    for i in range(len(self.subsystem_info.upper_outputs)):
                        if self.subsystem_info.upper_outputs_ipc[i]:
                            buffers_tx.append(self.subsystem_info.upper_outputs[i] + "Tx")
                            buffers_tx_rank = 'sink'
                        buffers_c.append(self.subsystem_info.upper_outputs[i] + "Concate")

                    new_graph.addRank(buffers_rx, rank_type=buffers_rx_rank)
                    new_graph.addRank(buffers_s)
                    new_graph.addRank(buffers_c)
                    new_graph.addRank(buffers_tx, rank_type=buffers_tx_rank)

                self.graph = new_graph

                with open('/tmp/' + self.subsystem_name + '_out.dot', 'w') as f:
                    f.writelines( self.graph.toStr() )

                subprocess.call(['dot', '-Tplain', '-O', '/tmp/' + self.subsystem_name + '_out.dot'])
                self.dialogGraph.drawGraph('/tmp/' + self.subsystem_name + '_out.dot.plain')

        # iterate through components and add them to QListWidget
        for value in msg.status[0].values:
            if not value.key in self.components:
                item = QListWidgetItem()
                item.setText(value.key)
                self.components[value.key] = item
                self.listWidget.addItem(item)

        components_state = {}
        for value in msg.status[0].values:
            self.components[value.key].setBackground( getComponentBrush(value.value) )
            self.components[value.key].setToolTip( getComponentTooltip(value.value) )
            components_state[value.key] = value.value

        #
        # update graph
        #
        self.dialogGraph.updateState(components_state)

        for value in msg.status[1].values:
            if value.key in self.components:
                self.components[value.key].setText(value.key + ' (' + value.value + ')')

        #rospy.wait_for_service('/' + name = '/getSubsystemInfo')
        if self.subsystem_info == None:
            try:
                self._getSubsystemInfo = rospy.ServiceProxy('/' + self.subsystem_name + '/getSubsystemInfo', GetSubsystemInfo)
                self.subsystem_info = self._getSubsystemInfo()
            except rospy.ServiceException, e:
                print "Service call failed: %s"%e

            if self.subsystem_info != None:
                print self.subsystem_info

            self.initialized = True

        mcd = self.parseMasterComponentDiag(self.state)
        if len(mcd[0]) > 0:
            self.SubsystemState.setText(mcd[0][0][0])
            self.dialogHistory.updateState(mcd)
        else:
            self.SubsystemState.setText("unknown")

#            self.SubsystemBehavior.setText(behavior_name.strip())

    def getCommonBuffers(self, subsystem):
        if not self.isInitialized() or not subsystem.isInitialized():
            return None
        if (subsystem.subsystem_info == None) or (self.subsystem_info == None):
            return None
        common_buffers = None
        for this_index in range(len(self.subsystem_info.upper_inputs)):
            up_in = self.subsystem_info.upper_inputs[this_index]
            if not self.subsystem_info.upper_inputs_ipc[this_index]:
                continue
            for index in range(len(subsystem.subsystem_info.lower_outputs)):
                lo_out = subsystem.subsystem_info.lower_outputs[index]
                if not subsystem.subsystem_info.lower_outputs_ipc[index]:
                    continue
                if up_in == lo_out:
                    if common_buffers == None:
                        common_buffers = []
                    common_buffers.append(up_in)

        for this_index in range(len(self.subsystem_info.upper_outputs)):
            up_out = self.subsystem_info.upper_outputs[this_index]
            if not self.subsystem_info.upper_outputs_ipc[this_index]:
                continue
            for index in range(len(subsystem.subsystem_info.lower_inputs)):
                lo_in = subsystem.subsystem_info.lower_inputs[index]
                if not subsystem.subsystem_info.lower_inputs_ipc[index]:
                    continue
                if up_out == lo_in:
                    if common_buffers == None:
                        common_buffers = []
                    common_buffers.append(up_out)
        return common_buffers

    def getCommonString(self, str_list):
        idx = 0
        while True:
            character = None
            for s in str_list:
                if idx >= len(s):
                    return s
                if character == None:
                    character = s[idx]
                elif character != s[idx]:
                    return s[:idx]
            idx = idx + 1
        return None     # this is never reached

    def groupBuffers(self, buffer_list, subsystem_name):
        if buffer_list == None or len(buffer_list) == 0:
            print "Error in %s.groupBuffers(%s, %s): buffers list is None or empty"%(self.subsystem_name, buffer_list, subsystem_name)
            return False
        if subsystem_name in self.buffer_groups:
            # TODO: remove old buffer widgets
            return False
        self.buffer_groups[subsystem_name] = buffer_list

        lo_in = []
        up_in = []
        lo_out = []
        up_out = []

        for buf_name in buffer_list:
            if buf_name in self.subsystem_info.lower_inputs:
                lo_in.append(buf_name)
            elif buf_name in self.subsystem_info.upper_inputs:
                up_in.append(buf_name)
            elif buf_name in self.subsystem_info.lower_outputs:
                lo_out.append(buf_name)
            elif buf_name in self.subsystem_info.upper_outputs:
                up_out.append(buf_name)

        # buffer group should be either in lower part or upper part
        if (len(lo_in) > 0 or len(lo_out) > 0) and (len(up_in) > 0 or len(up_out) > 0):
            print "Error in %s.groupBuffers(%s, %s): mixed upper and lower buffers"%(self.subsystem_name, buffer_list, subsystem_name)
            return False

        # get most common part of buffers' names
        name_list = []
        common_name = self.getCommonString(buffer_list)
        for idx in range(len(buffer_list)):
            name_list.append( buffer_list[idx][len(common_name):] )

        print common_name, name_list

        vbox = QVBoxLayout()

        hbox1 = QHBoxLayout()
        hbox1.addStretch()
        if not (common_name) in self.all_buffers:
            self.all_buffers[common_name] = QLabel(common_name)
        hbox1.addWidget(self.all_buffers[common_name])
        self.all_buffers[common_name].show()
        hbox1.addStretch()

        hbox2 = QHBoxLayout()
        hbox2.addSpacing(20)
        for buf_name in name_list:
#            hbox2.addStretch()
            if common_name+buf_name in lo_in or common_name+buf_name in up_out:
                suffix = ' /\\'
            else:
                suffix = ' \\/'

            if not (common_name+buf_name) in self.all_buffers:
                self.all_buffers[common_name+buf_name] = QPushButton(buf_name + suffix)
            hbox2.addWidget( self.all_buffers[common_name+buf_name] )
            self.all_buffers[common_name+buf_name].show()
#            hbox2.addWidget( QPushButton(buf_name + suffix) )
#        hbox2.addStretch()
        hbox2.addSpacing(20)


        if len(lo_in) > 0 or len(lo_out) > 0:
            vbox.addLayout(hbox1)
            vbox.addLayout(hbox2)
            self.lower_buffers_layout.addLayout(vbox)
            self.lower_subsystems.append(subsystem_name)
        else:
            vbox.addLayout(hbox2)
            vbox.addLayout(hbox1)
            self.upper_buffers_layout.addLayout(vbox)

    def getLowerSubsystemPosition(self, subsystem_name):
        for i in range(len(self.lower_subsystems)):
            if self.lower_subsystems[i] == subsystem_name:
                return i
        return -1

    def getLowerSubsystems(self):
        return self.lower_subsystems

    def start(self):
        """
        This method needs to be called to start updating topic pane.
        """

    def shutdown_plugin(self):
        for topic in self._topics.values():
            topic['info'].stop_monitoring()
        self._timer_refresh_topics.stop()


    # TODO(Enhancement) Save/Restore tree expansion state
    def save_settings(self, plugin_settings, instance_settings):
        header_state = self.topics_tree_widget.header().saveState()
        instance_settings.set_value('tree_widget_header_state', header_state)

    def restore_settings(self, pluggin_settings, instance_settings):
        if instance_settings.contains('tree_widget_header_state'):
            header_state = instance_settings.value('tree_widget_header_state')
            if not self.topics_tree_widget.header().restoreState(header_state):
                rospy.logwarn("rqt_topic: Failed to restore header state.")


