import sys
import math
import sys
import math
import os
from PySide6 import QtWidgets, QtCore, QtGui

# Ensure repository root is on sys.path so sibling packages like UtilityLib import
cur = os.path.dirname(os.path.realpath(__file__))
repo_root = os.path.abspath(os.path.join(cur, '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# XML/network utilities
from UtilityLib import moduleXML as mXML
import NetworkLib.classVascularNetwork as cVascNw

# Scale: 1 physical mm = PIXELS_PER_MM pixels on screen
PIXELS_PER_MM = 15.0

class VesselEdge(QtWidgets.QGraphicsLineItem):
    """
    Represents a Vessel (Edge) connecting two Junctions (Nodes).
    This is where the physical properties of the 1D model live.
    """
    def __init__(self, source_node, dest_node, name="Vessel"):
        super().__init__()
        self.source_node = source_node
        self.dest_node = dest_node
        self.name = name
        
        # 1D Physical Properties
        self.length_mm = 10.0
        self.area_start_mm2 = 5.0
        self.area_end_mm2 = 5.0
        self.elasticity_Pa = 1.0e6
        self.vessel_type = "Cylindrical"
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.base_color = QtGui.QColor(200, 50, 50)
        self.setZValue(0)
        
        # Connect to nodes
        self.source_node.add_outgoing_edge(self)
        self.dest_node.add_incoming_edge(self)
        self.update_visuals()
        
    def update_visuals(self):
        """Updates the line and text/thickness to match properties."""
        line = QtCore.QLineF(self.source_node.sceneBoundingRect().center(), 
                             self.dest_node.sceneBoundingRect().center())
        self.setLine(line)
        
        # Thickness based on Area
        thickness = max(3.0, min(30.0, math.sqrt(self.area_start_mm2) * 2.5))
        
        pen = QtGui.QPen(self.base_color, thickness, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        if self.isSelected():
            pen.setColor(QtCore.Qt.yellow)
            pen.setWidthF(thickness + 3)
            
        self.setPen(pen)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            self.update_visuals()
        return super().itemChange(change, value)
        
    def cleanup(self):
        """Removes itself from the connected nodes."""
        if self in self.source_node.outgoing_edges:
            self.source_node.outgoing_edges.remove(self)
        if self in self.dest_node.incoming_edges:
            self.dest_node.incoming_edges.remove(self)


class JunctionNode(QtWidgets.QGraphicsEllipseItem):
    """
    Represents a Junction (Node).
    """
    def __init__(self, name="Junction"):
        super().__init__(-12, -12, 24, 24)
        self.name = name
        self.incoming_edges = []
        self.outgoing_edges = []
        self.setZValue(1)
        
        self.setBrush(QtGui.QBrush(QtGui.QColor(80, 180, 250)))
        self.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        
        # Make the node draggable and selectable
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        
        self.label = QtWidgets.QGraphicsTextItem(self.name, self)
        self.label.setDefaultTextColor(QtCore.Qt.white)
        self.label.setFont(QtGui.QFont("Arial", 9))
        self.label.setPos(15, -15)

    def add_incoming_edge(self, edge):
        self.incoming_edges.append(edge)
        
    def add_outgoing_edge(self, edge):
        self.outgoing_edges.append(edge)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            # Update visual lines immediately while dragging
            for edge in self.incoming_edges + self.outgoing_edges:
                edge.update_visuals()
        elif change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            if value:
                self.setPen(QtGui.QPen(QtCore.Qt.yellow, 3))
            else:
                self.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        return super().itemChange(change, value)
        
    def mouseReleaseEvent(self, event):
        """When the user stops dragging, enforce the physical line lengths."""
        super().mouseReleaseEvent(event)
        if self.scene():
            self.scene().enforce_fixed_lengths()
            
    def update_visuals(self):
        self.label.setPlainText(self.name)


class VascularScene(QtWidgets.QGraphicsScene):
    def enforce_fixed_lengths(self):
        """
        Traverses the graph from the root(s) and forces the distance between
        connected nodes to exactly match `length_mm * PIXELS_PER_MM`.
        This preserves the ANGLE the user dragged the node to, but fixes the LENGTH.
        """
        # Find roots (nodes with no incoming edges)
        nodes = [item for item in self.items() if isinstance(item, JunctionNode)]
        roots = [n for n in nodes if not n.incoming_edges]
        
        visited = set()
        
        def traverse_and_fix(node):
            if node in visited: return
            visited.add(node)
            
            for edge in node.outgoing_edges:
                child = edge.dest_node
                
                # Get current visual line to find the angle the user wanted
                current_line = QtCore.QLineF(node.scenePos(), child.scenePos())
                
                # If nodes are right on top of each other, give a default angle (straight down)
                if current_line.length() < 1.0:
                    current_line.setAngle(270) # 270 is straight down in QGraphicsScene
                
                # Force the length to perfectly match the physical length_mm property
                fixed_visual_length = edge.length_mm * PIXELS_PER_MM
                current_line.setLength(fixed_visual_length)
                
                # Move the child node to the fixed position
                child.setPos(current_line.p2())
                edge.update_visuals()
                
                traverse_and_fix(child)
                
        for root in roots:
            traverse_and_fix(root)


class PropertiesPanel(QtWidgets.QWidget):
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.current_item = None
        
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        
        # 1. Tools Group
        tools_group = QtWidgets.QGroupBox("Network Builder Tools")
        tools_layout = QtWidgets.QVBoxLayout()
        
        self.btn_add_root = QtWidgets.QPushButton("Add New Root Node")
        self.btn_add_branch = QtWidgets.QPushButton("Add Branch to Selected")
        self.btn_delete = QtWidgets.QPushButton("Delete Selected")
        self.btn_save_project = QtWidgets.QPushButton("Save Project")
        self.btn_load_project = QtWidgets.QPushButton("Load Project")
        
        self.btn_add_root.setToolTip("Creates an unattached starting point.")
        self.btn_add_branch.setToolTip("Select a node, then click this to instantly sprout a new vessel and child node.")
        
        tools_layout.addWidget(self.btn_add_root)
        tools_layout.addWidget(self.btn_add_branch)
        tools_layout.addWidget(self.btn_delete)
        tools_layout.addWidget(self.btn_save_project)
        tools_layout.addWidget(self.btn_load_project)
        tools_group.setLayout(tools_layout)
        self.layout.addWidget(tools_group)
        
        # 2. Properties Group
        prop_group = QtWidgets.QGroupBox("Vessel Properties")
        form_layout = QtWidgets.QFormLayout()
        form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        
        # Create fields
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.textChanged.connect(self.update_name)
        
        self.length_edit = QtWidgets.QDoubleSpinBox()
        self.length_edit.setRange(0.0, 10000.0)
        self.length_edit.setSpecialValueText("N/A")
        self.length_edit.setSuffix(" mm")
        self.length_edit.valueChanged.connect(self.update_length)
        
        self.area_start_edit = QtWidgets.QDoubleSpinBox()
        self.area_start_edit.setRange(0.0, 1000.0)
        self.area_start_edit.setSpecialValueText("N/A")
        self.area_start_edit.setSuffix(" mm²")
        self.area_start_edit.valueChanged.connect(self.update_area_start)
        
        self.area_end_edit = QtWidgets.QDoubleSpinBox()
        self.area_end_edit.setRange(0.0, 1000.0)
        self.area_end_edit.setSpecialValueText("N/A")
        self.area_end_edit.setSuffix(" mm²")
        self.area_end_edit.valueChanged.connect(self.update_area_end)
        
        self.elasticity_edit = QtWidgets.QLineEdit()
        self.elasticity_edit.setPlaceholderText("e.g. 1.0e6")
        self.elasticity_edit.textChanged.connect(self.update_elasticity)
        
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(["Cylindrical", "Conical", "Elastic Tube"])
        self.type_combo.currentTextChanged.connect(self.update_type)
        
        # Add to form layout
        form_layout.addRow("Identifier:", self.name_edit)
        form_layout.addRow("Vessel Length:", self.length_edit)
        form_layout.addRow("Start Area:", self.area_start_edit)
        form_layout.addRow("End Area:", self.area_end_edit)
        form_layout.addRow("Elasticity (Pa):", self.elasticity_edit)
        form_layout.addRow("Shape Type:", self.type_combo)
        
        prop_group.setLayout(form_layout)
        self.layout.addWidget(prop_group)
        # 3. Node Browser (on the right)
        browser_group = QtWidgets.QGroupBox("Node Browser")
        browser_layout = QtWidgets.QVBoxLayout()
        self.node_list = QtWidgets.QListWidget()
        self.node_list.itemClicked.connect(self.on_node_list_clicked)
        browser_layout.addWidget(self.node_list)
        browser_group.setLayout(browser_layout)
        self.layout.addWidget(browser_group)

        # 4. Boundary Condition Manager (bottom block)
        bc_group = QtWidgets.QGroupBox("Boundary Condition Manager")
        bc_layout = QtWidgets.QFormLayout()

        self.bc_type = QtWidgets.QComboBox()
        self.bc_type.addItems(["<none>", "Flow-Sinus2", "ReflectionCoefficient"])
        self.bc_type.currentTextChanged.connect(self.on_bc_type_changed)

        # Flow-Sinus2 params
        self.amp_edit = QtWidgets.QDoubleSpinBox()
        self.amp_edit.setRange(0.0, 1e6)
        self.amp_edit.setSuffix(" ml s-1")
        self.freq_edit = QtWidgets.QDoubleSpinBox()
        self.freq_edit.setRange(0.0, 1000.0)
        self.freq_edit.setSuffix(" s-1")

        # ReflectionCoefficient params
        self.rt_edit = QtWidgets.QDoubleSpinBox()
        self.rt_edit.setRange(-10.0, 10.0)

        bc_layout.addRow("BC Type:", self.bc_type)
        bc_layout.addRow("amp:", self.amp_edit)
        bc_layout.addRow("freq:", self.freq_edit)
        bc_layout.addRow("Rt:", self.rt_edit)

        # Save BC to node
        self.btn_assign_bc = QtWidgets.QPushButton("Assign BC to Selected Node")
        self.btn_assign_bc.clicked.connect(self.assign_bc_to_selected_node)
        self.btn_save_xml = QtWidgets.QPushButton("Save Boundary XML")
        self.btn_save_xml.clicked.connect(self.save_boundary_xml)
        bc_layout.addRow(self.btn_assign_bc)
        bc_layout.addRow(self.btn_save_xml)

        bc_group.setLayout(bc_layout)
        self.layout.addWidget(bc_group)
        self.layout.addStretch()
        self.set_enabled_fields(False)
        # (Save/Load project buttons will be connected by the main editor)

    def set_enabled_fields(self, enabled, is_edge=False):
        self.name_edit.setEnabled(enabled)
        self.length_edit.setEnabled(is_edge)
        self.area_start_edit.setEnabled(is_edge)
        self.area_end_edit.setEnabled(is_edge)
        self.elasticity_edit.setEnabled(is_edge)
        self.type_combo.setEnabled(is_edge)
        
    def on_selection_changed(self):
        selected = self.scene.selectedItems()
        if not selected or len(selected) > 1:
            self.current_item = None
            self.set_enabled_fields(False)
            self.name_edit.clear()
            return
            
        item = selected[0]
        self.current_item = item
        
        self.blockSignals(True)
        self.name_edit.blockSignals(True)
        self.length_edit.blockSignals(True)
        self.area_start_edit.blockSignals(True)
        self.area_end_edit.blockSignals(True)
        self.elasticity_edit.blockSignals(True)
        self.type_combo.blockSignals(True)
        
        self.name_edit.setText(item.name)
        
        if isinstance(item, VesselEdge):
            self.set_enabled_fields(True, is_edge=True)
            self.length_edit.setValue(item.length_mm)
            self.area_start_edit.setValue(item.area_start_mm2)
            self.area_end_edit.setValue(item.area_end_mm2)
            self.elasticity_edit.setText(str(item.elasticity_Pa))
            self.type_combo.setCurrentText(item.vessel_type)
        elif isinstance(item, JunctionNode):
            self.set_enabled_fields(True, is_edge=False)
            self.length_edit.setValue(0)
            self.area_start_edit.setValue(0)
            self.area_end_edit.setValue(0)
            self.elasticity_edit.setText("")
            self.type_combo.setCurrentIndex(-1)
            # update node browser selection highlight
            self.update_node_list_selection(item)
            # populate Boundary Condition Manager with existing BC if present
            if hasattr(item, 'boundary_condition') and isinstance(item.boundary_condition, dict):
                bcd = item.boundary_condition
                bctype = bcd.get('type', '<none>')
                # set BC type (this will enable/disable fields via the connected slot)
                try:
                    self.bc_type.setCurrentText(bctype)
                except Exception:
                    self.bc_type.setCurrentIndex(0)

                if bctype == 'Flow-Sinus2':
                    self.amp_edit.setValue(float(bcd.get('amp', 0.0)))
                    self.freq_edit.setValue(float(bcd.get('freq', 0.0)))
                elif bctype == 'ReflectionCoefficient':
                    self.rt_edit.setValue(float(bcd.get('Rt', 0.0)))
            else:
                # reset BC panel to defaults
                self.bc_type.setCurrentIndex(0)
                self.amp_edit.setValue(0.0)
                self.freq_edit.setValue(0.0)
                self.rt_edit.setValue(0.0)
            
        self.name_edit.blockSignals(False)
        self.length_edit.blockSignals(False)
        self.area_start_edit.blockSignals(False)
        self.area_end_edit.blockSignals(False)
        self.elasticity_edit.blockSignals(False)
        self.type_combo.blockSignals(False)
        self.blockSignals(False)

    def update_name(self, text):
        if self.current_item:
            self.current_item.name = text
            self.current_item.update_visuals()
            
    def update_length(self, val):
        if isinstance(self.current_item, VesselEdge): 
            self.current_item.length_mm = val
            # Enforce the new fixed length immediately!
            self.scene.enforce_fixed_lengths()
            
    def update_area_start(self, val):
        if isinstance(self.current_item, VesselEdge): 
            self.current_item.area_start_mm2 = val
            self.current_item.update_visuals()
            
    def update_area_end(self, val):
        if isinstance(self.current_item, VesselEdge): self.current_item.area_end_mm2 = val
    def update_elasticity(self, text):
        if isinstance(self.current_item, VesselEdge):
            try: self.current_item.elasticity_Pa = float(text)
            except ValueError: pass
    def update_type(self, text):
        if isinstance(self.current_item, VesselEdge): self.current_item.vessel_type = text

    # Node Browser handlers
    def refresh_node_list(self):
        self.node_list.clear()
        nodes = [it for it in self.scene.items() if isinstance(it, JunctionNode)]
        for n in nodes:
            w = QtWidgets.QListWidgetItem(n.name)
            w.setData(QtCore.Qt.UserRole, id(n))
            self.node_list.addItem(w)

    def on_node_list_clicked(self, item):
        # find object by id and select it in scene
        obj_id = item.data(QtCore.Qt.UserRole)
        for it in self.scene.items():
            if id(it) == obj_id:
                self.scene.clearSelection()
                it.setSelected(True)
                self.scene.views()[0].centerOn(it)
                break

    def update_node_list_selection(self, node):
        # ensure node is visible and selected in list
        for i in range(self.node_list.count()):
            it = self.node_list.item(i)
            if it.data(QtCore.Qt.UserRole) == id(node):
                self.node_list.setCurrentItem(it)
                return

    # Boundary condition management
    def on_bc_type_changed(self, txt):
        # toggle parameter enablement simply
        self.amp_edit.setEnabled(txt == 'Flow-Sinus2')
        self.freq_edit.setEnabled(txt == 'Flow-Sinus2')
        self.rt_edit.setEnabled(txt == 'ReflectionCoefficient')

    def assign_bc_to_selected_node(self):
        selected = self.scene.selectedItems()
        nodes = [item for item in selected if isinstance(item, JunctionNode)]
        if not nodes:
            QtWidgets.QMessageBox.warning(self, "No node selected", "Select a junction node to assign a BC.")
            return
        node = nodes[0]
        # attach bc data to node
        node.boundary_condition = {'type': self.bc_type.currentText()}
        if self.bc_type.currentText() == 'Flow-Sinus2':
            node.boundary_condition.update({'amp': self.amp_edit.value(), 'freq': self.freq_edit.value()})
        elif self.bc_type.currentText() == 'ReflectionCoefficient':
            node.boundary_condition.update({'Rt': self.rt_edit.value()})
        QtWidgets.QMessageBox.information(self, "Boundary assigned", f"Assigned {self.bc_type.currentText()} to {node.name}")

    def save_boundary_xml(self):
        # collect BCs and vessels
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Boundary XML", "boundary_export.xml", "XML Files (*.xml)")
        if not fname:
            return
        # build xml string
        import math, xml.etree.ElementTree as ET

        root = ET.Element('export')
        bcs = ET.SubElement(root, 'boundaryConditions')

        # map vessel edges to ids
        vessels = [it for it in self.scene.items() if isinstance(it, VesselEdge)]
        vessels = list(dict.fromkeys(vessels))
        vessel_id_map = {}
        for i, v in enumerate(reversed(vessels)):
            # reversed because scene.items gives top-down; keep stable but it's arbitrary
            vessel_id_map[v] = i

        # boundary conditions on nodes
        nodes = [it for it in self.scene.items() if isinstance(it, JunctionNode)]
        for node in nodes:
            if hasattr(node, 'boundary_condition'):
                # find connected vessel id (use outgoing edge if present else incoming)
                vid = None
                if node.outgoing_edges:
                    vid = vessel_id_map.get(node.outgoing_edges[0], 0)
                elif node.incoming_edges:
                    vid = vessel_id_map.get(node.incoming_edges[0], 0)
                else:
                    vid = 0
                bc = ET.SubElement(bcs, 'boundaryCondition', vesselId=str(vid))
                bctype = node.boundary_condition.get('type')
                if bctype == 'Flow-Sinus2':
                    el = ET.SubElement(bc, 'Flow-Sinus2')
                    ET.SubElement(el, 'amp', unit='ml s-1').text = str(node.boundary_condition.get('amp', 0.0))
                    ET.SubElement(el, 'ampConst', unit='m3 s-1').text = '0.0'
                    ET.SubElement(el, 'Npulse').text = '25.0'
                    ET.SubElement(el, 'Tpulse', unit='s').text = '0.0'
                    ET.SubElement(el, 'freq', unit='s-1').text = str(node.boundary_condition.get('freq', 8.0))
                    ET.SubElement(el, 'Tspace', unit='s').text = '0.5'
                    ET.SubElement(el, 'runtimeEvaluation').text = 'False'
                    ET.SubElement(el, 'prescribe').text = 'influx'
                elif bctype == 'ReflectionCoefficient':
                    el = ET.SubElement(bc, 'ReflectionCoefficient')
                    ET.SubElement(el, 'Rt').text = str(node.boundary_condition.get('Rt', 0.0))

        # vessels
        vessels_el = ET.SubElement(root, 'vessels')
        for v, vid in vessel_id_map.items():
            ve = ET.SubElement(vessels_el, 'vessel', Id=str(vid), name=v.name.replace(' ', ''))
            topo = ET.SubElement(ve, 'topology')
            ET.SubElement(topo, 'leftDaughter').text = 'None'
            ET.SubElement(topo, 'rightDaughter').text = 'None'
            ET.SubElement(topo, 'angleYMother').text = '0'
            geom = ET.SubElement(ve, 'geometry')
            ET.SubElement(geom, 'geometryType').text = 'cone'
            # convert mm to m for length, mm^2 to m^2 for area -> estimate radii
            length_m = v.length_mm / 1000.0
            r0_m = math.sqrt(max(1e-12, v.area_start_mm2 * 1e-6) / math.pi)
            r1_m = math.sqrt(max(1e-12, v.area_end_mm2 * 1e-6) / math.pi)
            ET.SubElement(geom, 'length', unit='m').text = str(length_m)
            ET.SubElement(geom, 'radiusProximal', unit='m').text = str(r0_m)
            ET.SubElement(geom, 'radiusDistal', unit='m').text = str(r1_m)
            ET.SubElement(geom, 'N').text = str(max(1, int(v.length_mm)))

        # write XML
        tree = ET.ElementTree(root)
        tree.write(fname, encoding='utf-8', xml_declaration=True)
        QtWidgets.QMessageBox.information(self, 'Saved', f'Saved boundary/vessel XML to {fname}')

    def save_project(self):
        # wrapper to save project XML (uses existing save logic)
        self.save_boundary_xml()

    def load_project(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Project XML", "", "XML Files (*.xml)")
        if not fname:
            return
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(fname)
            root = tree.getroot()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to parse XML: {e}')
            return

        # Build map of scene vessels by normalized name
        scene_vessels = [it for it in self.scene.items() if isinstance(it, VesselEdge)]
        scene_vessel_map = {v.name.replace(' ', ''): v for v in scene_vessels}

        # Load vessels (if present)
        vessels_el = root.find('vessels')
        if vessels_el is not None:
            for ve in vessels_el.findall('vessel'):
                name = ve.get('name')
                if not name:
                    continue
                v = scene_vessel_map.get(name)
                if v is None:
                    # no matching vessel in scene; skip
                    continue
                geom = ve.find('geometry')
                if geom is not None:
                    length_el = geom.find('length')
                    rprox = geom.find('radiusProximal')
                    rdist = geom.find('radiusDistal')
                    n_el = geom.find('N')
                    try:
                        if length_el is not None:
                            # length in meters -> convert to mm
                            v.length_mm = float(length_el.text) * 1000.0
                        if rprox is not None and rdist is not None:
                            r0 = float(rprox.text)
                            r1 = float(rdist.text)
                            # areas in m^2 -> convert to mm^2
                            v.area_start_mm2 = math.pi * (r0 ** 2) * 1e6
                            v.area_end_mm2 = math.pi * (r1 ** 2) * 1e6
                    except Exception:
                        pass

        # Load boundary conditions
        bcs_el = root.find('boundaryConditions')
        if bcs_el is not None:
            for bc in bcs_el.findall('boundaryCondition'):
                vid = bc.get('vesselId')
                # find vessel element with matching Id to get its name
                vessel_name = None
                if vessels_el is not None:
                    for ve in vessels_el.findall('vessel'):
                        if ve.get('Id') == vid:
                            vessel_name = ve.get('name')
                            break
                if not vessel_name:
                    continue
                v = scene_vessel_map.get(vessel_name)
                if not v:
                    continue
                # attach BC to the node that is the source of this vessel (consistent with save logic)
                node = v.source_node
                # determine BC type from children
                if node is None:
                    continue
                # prefer Flow-Sinus2 or ReflectionCoefficient
                if bc.find('Flow-Sinus2') is not None:
                    el = bc.find('Flow-Sinus2')
                    amp = 0.0
                    freq = 0.0
                    ael = el.find('amp')
                    fel = el.find('freq')
                    try:
                        if ael is not None: amp = float(ael.text)
                        if fel is not None: freq = float(fel.text)
                    except Exception:
                        pass
                    node.boundary_condition = {'type': 'Flow-Sinus2', 'amp': amp, 'freq': freq}
                elif bc.find('ReflectionCoefficient') is not None:
                    el = bc.find('ReflectionCoefficient')
                    rt = 0.0
                    rel = el.find('Rt')
                    try:
                        if rel is not None: rt = float(rel.text)
                    except Exception:
                        pass
                    node.boundary_condition = {'type': 'ReflectionCoefficient', 'Rt': rt}

        # Refresh visuals and node list
        for sv in scene_vessels:
            sv.update_visuals()
        self.refresh_node_list()
        QtWidgets.QMessageBox.information(self, 'Loaded', f'Loaded project from {fname}')


class VascularEditor(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('STARFiSh 1D UI (Fixed Lengths & Angles)')
        
        self.scene = VascularScene()
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.scene.setBackgroundBrush(QtGui.QColor(35, 35, 35))
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.view)
        
        self.prop_panel = PropertiesPanel(self.scene)
        self.prop_panel.setMinimumWidth(400) # Increased width to stop text cutoff

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
        
        layout.addWidget(self.prop_panel)
        
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        self.node_count = 0
        self.edge_count = 0
        
        self.setup_sample_network()

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
        offset = len(parent.outgoing_edges) * 30 # Fan out if multiple branches
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
                try: it.cleanup()
                except Exception: pass
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
                s = None; e = None
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
            edge.vessel_id = vessel.Id
            self.scene.addItem(edge)
            edge_map[vessel.Id] = edge

        # attach BCs to nodes based on vascularNetwork.boundaryConditions
        for vid, bc_list in vascularNetwork.boundaryConditions.items():
            if vid in edge_map:
                edge = edge_map[vid]
                node = edge.source_node
                # attach first bc summary
                if len(bc_list) > 0:
                    bc = bc_list[0]
                    try:
                        bctype = bc.name
                    except Exception:
                        bctype = getattr(bc, 'getVariableValue', lambda k: '<unknown>')('name')
                    node.boundary_condition = {'type': bctype}
                    # copy common fields
                    for fld in ('amp', 'freq', 'Rt'):
                        val = getattr(bc, fld, None)
                        if val is not None:
                            node.boundary_condition[fld] = val

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
            if e in visited: continue
            visited.add(e)
            if e not in id_map:
                id_map[e] = next_id; next_id += 1
            # children
            kids = e.dest_node.outgoing_edges
            parent_children[id_map[e]] = []
            for child in kids:
                if child not in id_map:
                    id_map[child] = next_id; next_id += 1
                parent_children[id_map[e]].append(id_map[child])
                q.append(child)

        # assign any remaining edges
        for e in edges:
            if e not in id_map:
                id_map[e] = next_id; next_id += 1

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
            vesselData[vid] = {'Id': vid, 'name': name, 'geometryType': 'cone', 'length': length_m, 'radiusProximal': r0, 'radiusDistal': r1, 'N': max(2, int(max(2, e.length_mm)))}

        # apply topology
        for parent_id, children in parent_children.items():
            if len(children) >= 1:
                vesselData[parent_id]['leftDaughter'] = children[0]
            if len(children) >= 2:
                vesselData[parent_id]['rightDaughter'] = children[1]

        vascularNetwork.updateNetwork({'vesselData': vesselData})

        # attach boundary conditions
        for e, vid in id_map.items():
            node = e.source_node
            if hasattr(node, 'boundary_condition'):
                bc = node.boundary_condition
                # map simple types
                bclist = []
                bctype = bc.get('type', 'None')
                # Create minimal boundary instance via tags required by moduleXML parser
                # We'll create simple ReflectionCoefficient or Flow-Sinus2 typed wrappers if possible
                # Fallback: create a simple dict-like object
                class SimpleBC:
                    def __init__(self, name, data):
                        self.name = name
                        for k, v in data.items(): setattr(self, k, v)
                bobj = SimpleBC(bctype, bc)
                vascularNetwork.boundaryConditions[vid] = [bobj]

        # write XML
        try:
            mXML.writeNetworkToXML(vascularNetwork, dataNumber='xxx', networkXmlFile=fname)
            QtWidgets.QMessageBox.information(self, 'Exported', f'Exported network XML to {fname}')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to write network XML: {e}')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    
    # Apply a dark theme globally
    app.setStyle("Fusion")
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(43, 43, 43))
    dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(43, 43, 43))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(43, 43, 43))
    dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(dark_palette)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    editor = VascularEditor()
    editor.resize(1200, 800)
    editor.show()
    sys.exit(app.exec())