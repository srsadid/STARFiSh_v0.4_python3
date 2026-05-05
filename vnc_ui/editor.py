import math
import os
import subprocess
import sys
from PySide6 import QtWidgets, QtCore, QtGui
from UtilityLib import moduleXML as mXML
from UtilityLib.constants import newestNetworkXml as nxml
import NetworkLib.classVascularNetwork as cVascNw
from vnc_ui.scene import VascularScene
from vnc_ui.scene_items import VesselEdge, JunctionNode
from vnc_ui.panels import PropertiesPanel

class VascularEditor(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CRIMSON STARFISH - Vascular Network Editor')

        self.scene = VascularScene()
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.scene.setBackgroundBrush(QtGui.QColor(35, 35, 35))
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        # Use a QSplitter for the model builder layout and a scroll area for the right panel
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.prop_panel = PropertiesPanel(self.scene)
        self.prop_scroll = QtWidgets.QScrollArea()
        self.prop_scroll.setWidgetResizable(True)
        self.prop_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.prop_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.prop_scroll.setWidget(self.prop_panel)
        splitter.addWidget(self.view)
        splitter.addWidget(self.prop_scroll)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        self.prop_panel.setMinimumWidth(360)
        self.prop_scroll.setMinimumWidth(360)
        self.prop_scroll.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.prop_panel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)

        self.prop_panel.btn_add_root.clicked.connect(self.add_root)
        self.prop_panel.btn_add_branch.clicked.connect(self.add_branch)
        self.prop_panel.btn_delete.clicked.connect(self.delete_selected)
        # connect project import/export to editor-level handlers
        self.prop_panel.btn_save_project.clicked.connect(self.export_network_xml)
        self.prop_panel.btn_load_project.clicked.connect(self.import_network_xml)

        self.prop_panel.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #eeeeee; font-family: sans-serif; font-size: 14px;}
            QGroupBox { font-weight: bold; border: 1px solid #555; border-radius: 5px; margin-top: 15px; padding-top: 15px;}
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; color: #80c0ff; }
            QLineEdit, QDoubleSpinBox, QComboBox {
                background-color: #3b3b3b; color: white; padding: 6px; border: 1px solid #555; border-radius: 3px; min-width: 120px;
            }
            QPushButton { background-color: #3a7ca5; color: white; border: none; padding: 10px; border-radius: 4px; font-weight: bold; margin-bottom: 5px;}
            QPushButton:hover { background-color: #4a8cb5; }
            QPushButton:pressed { background-color: #2a6c95; }
            QPushButton#btn_delete { background-color: #a53a3a; }
            QPushButton#btn_delete:hover { background-color: #b54a4a; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; }
        """)

        # Apply specific ID styling
        self.prop_panel.btn_delete.setObjectName("btn_delete")

        # Tabs for model builder and visualization
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabPosition(QtWidgets.QTabWidget.North)
        self.tabs.tabBar().setExpanding(False)

        model_tab = QtWidgets.QWidget()
        model_layout = QtWidgets.QHBoxLayout(model_tab)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.addWidget(splitter)
        self.tabs.addTab(model_tab, "Model Parameters & Builder")

        visualization_tab = QtWidgets.QWidget()
        visualization_layout = QtWidgets.QVBoxLayout(visualization_tab)
        visualization_layout.setContentsMargins(12, 12, 12, 12)
        visualization_layout.setSpacing(12)

        visualization_title = QtWidgets.QLabel("2D Visualization")
        visualization_title.setStyleSheet("font-size: 18px; font-weight: bold;")

        visualization_note = QtWidgets.QLabel(
            "Launches the GTK-based 2D visualization in a separate window. "
            "This keeps the Qt editor responsive while the plot UI runs."
        )
        visualization_note.setWordWrap(True)

        self.btn_open_visualization = QtWidgets.QPushButton("Open 2D Visualization")
        self.btn_open_visualization.clicked.connect(self.launch_visualization)
        self.btn_open_visualization.setFixedWidth(220)

        visualization_layout.addWidget(visualization_title)
        visualization_layout.addWidget(visualization_note)
        visualization_layout.addWidget(self.btn_open_visualization)
        visualization_layout.addStretch(1)

        self.tabs.addTab(visualization_tab, "Visualization")

        # Set the tabs as the central widget.
        self.setCentralWidget(self.tabs)

        self.node_count = 0
        self.edge_count = 0

        self.setup_sample_network()

    def launch_visualization(self):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "visualization_2d.py"))
        try:
            subprocess.Popen([sys.executable, script_path])
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to launch visualization: {exc}")

    def add_root(self):
        self.node_count += 1
        node = JunctionNode(f"Junction {self.node_count}")
        center_point = self.view.mapToScene(self.view.viewport().rect().center())
        node.setPos(center_point)
        self.scene.addItem(node)
        self.prop_panel.refresh_node_list()

    def add_branch(self):
        """The easiest way to build trees. Spawns a child connected to the selected node."""
        selected = self.scene.selectedItems()
        nodes = [item for item in selected if isinstance(item, JunctionNode)]

        if not nodes:
            QtWidgets.QMessageBox.warning(self, "No Node Selected", "Please click a Junction Node to branch from.")
            return

        parent = nodes[0]
        self.node_count += 1
        self.edge_count += 1

        # Create new child
        child = JunctionNode(f"Junction {self.node_count}")

        # Initial guess position: place it slightly below and right to give it a starting angle
        offset = len(parent.outgoing_edges) * 30  # Fan out if multiple branches
        child.setPos(parent.scenePos().x() + 20 + offset, parent.scenePos().y() + 100)
        self.scene.addItem(child)

        # Create vessel
        edge = VesselEdge(parent, child, f"Vessel {self.edge_count}")
        self.scene.addItem(edge)

        # Enforce exact physical lengths, preserving the angle we just created
        self.scene.enforce_fixed_lengths()

        # Select the new edge so user can immediately edit its properties
        parent.setSelected(False)
        edge.setSelected(True)
        self.prop_panel.refresh_node_list()

    def delete_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, VesselEdge):
                item.cleanup()
                self.scene.removeItem(item)

        for item in self.scene.selectedItems():
            if isinstance(item, JunctionNode):
                for edge in list(item.incoming_edges + item.outgoing_edges):
                    edge.cleanup()
                    self.scene.removeItem(edge)
                self.scene.removeItem(item)
            self.prop_panel.refresh_node_list()

    def setup_sample_network(self):
        self.node_count = 4
        self.edge_count = 3

        inlet_node = JunctionNode("Inlet Node")
        bifurcation_node = JunctionNode("Bifurcation Node")
        outlet1_node = JunctionNode("Outlet 1 Node")
        outlet2_node = JunctionNode("Outlet 2 Node")

        # The positions are just initial angles, the `enforce_fixed_lengths` will correct the distances
        inlet_node.setPos(0, -200)
        bifurcation_node.setPos(0, 0)
        outlet1_node.setPos(-100, 100)
        outlet2_node.setPos(100, 100)

        self.scene.addItem(inlet_node)
        self.scene.addItem(bifurcation_node)
        self.scene.addItem(outlet1_node)
        self.scene.addItem(outlet2_node)

        v1 = VesselEdge(inlet_node, bifurcation_node, "Main Artery")
        v2 = VesselEdge(bifurcation_node, outlet1_node, "Left Branch")
        v3 = VesselEdge(bifurcation_node, outlet2_node, "Right Branch")

        # Let's give them different physical lengths to demonstrate the feature!
        v1.length_mm = 15.0
        v2.length_mm = 8.0
        v3.length_mm = 12.0

        self.scene.addItem(v1)
        self.scene.addItem(v2)
        self.scene.addItem(v3)

        # Fix the layout immediately so it perfectly matches physical lengths
        self.scene.enforce_fixed_lengths()

        self.scene.setSceneRect(-800, -800, 1600, 1600)
        self.prop_panel.refresh_node_list()

    # --- Network import/export (full STARFiSh XML) ---
    def import_network_xml(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Network XML", "", "XML Files (*.xml)")
        if not fname:
            return
        # networkName used for loading (moduleXML expects a name)
        networkName = os.path.splitext(os.path.basename(fname))[0]
        try:
            vascularNetwork = mXML.loadNetworkFromXML(networkName, networkXmlFile=fname)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to load network: {e}')
            return

        # prepare network topology
        try:
            vascularNetwork.evaluateConnections()
            vascularNetwork.findStartAndEndNodes()
        except Exception:
            pass

        # clear current scene
        for it in list(self.scene.items()):
            if isinstance(it, VesselEdge) or isinstance(it, JunctionNode):
                try:
                    it.cleanup()
                except Exception:
                    pass
                self.scene.removeItem(it)

        # create scene nodes for each unique node id
        node_map = {}
        nodes_ids = set()
        for vessel in vascularNetwork.vessels.values():
            if hasattr(vessel, 'startNode') and vessel.startNode is not None:
                nodes_ids.add(vessel.startNode)
            if hasattr(vessel, 'endNode') and vessel.endNode is not None:
                nodes_ids.add(vessel.endNode)

        # position nodes on a circle for initial layout
        nodes_list = sorted(list(nodes_ids))
        n = len(nodes_list) if nodes_list else 1
        for i, nid in enumerate(nodes_list):
            angle = 2.0 * math.pi * i / n
            x = math.cos(angle) * 200
            y = math.sin(angle) * 200
            node = JunctionNode(f"Node {nid}")
            node.setPos(x, y)
            self.scene.addItem(node)
            node_map[nid] = node

        # create vessel edges
        edge_map = {}
        for vessel in vascularNetwork.vessels.values():
            # find start/end node objects
            try:
                s = node_map.get(vessel.startNode, None)
                e = node_map.get(vessel.endNode, None)
            except Exception:
                s = None
                e = None
            if s is None:
                s = JunctionNode(f"start_{vessel.Id}")
                s.setPos(0, -200)
                self.scene.addItem(s)
            if e is None:
                e = JunctionNode(f"end_{vessel.Id}")
                e.setPos(0, 0)
                self.scene.addItem(e)

            edge = VesselEdge(s, e, vessel.name if vessel.name else f"Vessel {vessel.Id}")
            # set physical properties
            try:
                edge.length_mm = float(vessel.length) * 1000.0
            except Exception:
                pass
            try:
                edge.area_start_mm2 = math.pi * (float(vessel.radiusProximal) ** 2) * 1e6
                edge.area_end_mm2 = math.pi * (float(vessel.radiusDistal) ** 2) * 1e6
            except Exception:
                pass
            try:
                edge.geometry_type = vessel.geometryType
                edge.vessel_type = edge.geometry_type
            except Exception:
                pass
            try:
                edge.grid_points = int(vessel.N)
            except Exception:
                pass
            try:
                edge.angle_y_mother = float(vessel.angleYMother)
            except Exception:
                pass
            try:
                edge.compliance_type = vessel.complianceType
                edge.compliance_values_by_type[edge.compliance_type] = {}
                for field_name in nxml.vesselComplianceElements.get(edge.compliance_type, []):
                    if field_name == 'complianceType':
                        continue
                    edge.compliance_values_by_type[edge.compliance_type][field_name] = getattr(vessel, field_name, None)
            except Exception:
                pass
            try:
                edge.fluid_values = {
                    'applyGlobalFluid': getattr(vessel, 'applyGlobalFluid', True),
                    'my': getattr(vessel, 'my', None),
                    'rho': getattr(vessel, 'rho', None),
                    'gamma': getattr(vessel, 'gamma', None),
                }
            except Exception:
                pass
            edge.vessel_id = vessel.Id
            self.scene.addItem(edge)
            edge_map[vessel.Id] = edge

        # attach BCs to nodes based on vascularNetwork.boundaryConditions
        for vid, bc_list in vascularNetwork.boundaryConditions.items():
            edge = edge_map.get(vid)
            if edge is None:
                continue
            for bc in bc_list:
                name = bc.getVariableValue('name') if hasattr(bc, 'getVariableValue') else getattr(bc, 'name', None)
                if isinstance(name, (list, tuple)) and name:
                    name = name[0]
                if not name:
                    continue
                is_end = str(name).startswith('_')
                node = edge.dest_node if is_end else edge.source_node
                if node is None:
                    continue
                if not hasattr(node, 'boundary_conditions') or node.boundary_conditions is None:
                    node.boundary_conditions = []
                node.boundary_conditions.append(bc)
                if not hasattr(node, 'boundary_condition') or node.boundary_condition is None:
                    node.boundary_condition = bc

        # finalize
        self.scene.enforce_fixed_lengths()
        self.prop_panel.refresh_node_list()
        QtWidgets.QMessageBox.information(self, 'Imported', f'Imported network from {fname}')

    def export_network_xml(self):
        # export full vascularNetwork XML from current scene
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Network XML", "network_export.xml", "XML Files (*.xml)")
        if not fname:
            return

        # traverse scene to assign IDs and topology
        edges = [it for it in self.scene.items() if isinstance(it, VesselEdge)]
        # find roots (edges whose source node has no incoming edges)
        roots = [e for e in edges if len(e.source_node.incoming_edges) == 0]
        id_map = {}
        parent_children = {}
        next_id = 1
        from collections import deque
        q = deque(roots)
        visited = set()
        while q:
            e = q.popleft()
            if e in visited:
                continue
            visited.add(e)
            if e not in id_map:
                id_map[e] = next_id
                next_id += 1
            # children
            kids = e.dest_node.outgoing_edges
            parent_children[id_map[e]] = []
            for child in kids:
                if child not in id_map:
                    id_map[child] = next_id
                    next_id += 1
                parent_children[id_map[e]].append(id_map[child])
                q.append(child)

        # assign any remaining edges
        for e in edges:
            if e not in id_map:
                id_map[e] = next_id
                next_id += 1

        # construct vascularNetwork
        vascularNetwork = cVascNw.VascularNetwork()
        vesselData = {}
        # build vessel data entries
        for e, vid in id_map.items():
            name = e.name.replace(' ', '')
            length_m = float(e.length_mm) / 1000.0
            # radii from areas
            r0 = math.sqrt(max(1e-12, e.area_start_mm2 * 1e-6) / math.pi)
            r1 = math.sqrt(max(1e-12, e.area_end_mm2 * 1e-6) / math.pi)
            geometry_type = getattr(e, 'geometry_type', None) or getattr(e, 'vessel_type', None) or 'cone'
            grid_points = int(getattr(e, 'grid_points', max(2, int(max(2, e.length_mm)))))
            compliance_type = getattr(e, 'compliance_type', None) or 'Hayashi'
            vessel_entry = {
                'Id': vid,
                'name': name,
                'geometryType': geometry_type,
                'length': length_m,
                'radiusProximal': r0,
                'radiusDistal': r1,
                'N': grid_points,
                'complianceType': compliance_type,
                'angleYMother': getattr(e, 'angle_y_mother', 0.0),
            }
            compliance_values = getattr(e, 'compliance_values_by_type', {}).get(compliance_type, {})
            for field_name in nxml.vesselComplianceElements.get(compliance_type, []):
                if field_name == 'complianceType':
                    continue
                if field_name in compliance_values:
                    vessel_entry[field_name] = compliance_values[field_name]
            fluid_values = getattr(e, 'fluid_values', {})
            for field_name in nxml.vesselFluidElements:
                if field_name in fluid_values:
                    vessel_entry[field_name] = fluid_values[field_name]
            vesselData[vid] = vessel_entry

        # apply topology
        for parent_id, children in parent_children.items():
            if len(children) >= 1:
                vesselData[parent_id]['leftDaughter'] = children[0]
            if len(children) >= 2:
                vesselData[parent_id]['rightDaughter'] = children[1]

        vascularNetwork.updateNetwork({'vesselData': vesselData})

        # attach boundary conditions from nodes, respecting start/end positions
        boundary_by_vessel = {}
        nodes = [it for it in self.scene.items() if isinstance(it, JunctionNode)]
        for node in nodes:
            conditions = getattr(node, 'boundary_conditions', None)
            if not conditions:
                continue
            for bc in conditions:
                name = bc.getVariableValue('name') if hasattr(bc, 'getVariableValue') else getattr(bc, 'name', None)
                if isinstance(name, (list, tuple)) and name:
                    name = name[0]
                if not name:
                    continue
                is_end = str(name).startswith('_')
                if is_end:
                    edge = node.incoming_edges[0] if node.incoming_edges else None
                    if edge is None and node.outgoing_edges:
                        edge = node.outgoing_edges[0]
                else:
                    edge = node.outgoing_edges[0] if node.outgoing_edges else None
                    if edge is None and node.incoming_edges:
                        edge = node.incoming_edges[0]
                if edge is None:
                    continue
                vid = id_map.get(edge)
                if vid is None:
                    continue
                boundary_by_vessel.setdefault(vid, []).append(bc)

        for vid, bcs in boundary_by_vessel.items():
            vascularNetwork.boundaryConditions[vid] = list(bcs)

        # write XML
        try:
            mXML.writeNetworkToXML(vascularNetwork, dataNumber='xxx', networkXmlFile=fname)
            QtWidgets.QMessageBox.information(self, 'Exported', f'Exported network XML to {fname}')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to write network XML: {e}')
