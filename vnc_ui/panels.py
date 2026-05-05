import math
from PySide6 import QtWidgets, QtCore
from UtilityLib.constants import newestNetworkXml as nxml
from UtilityLib.constants import variablesDict
from NetworkLib.classBoundaryConditions import *
from vnc_ui.widgets import FixedPopupComboBox
from vnc_ui.scene_items import VesselEdge, JunctionNode

class PropertiesPanel(QtWidgets.QWidget):
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.current_item = None

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(10)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setLayout(self.layout)

        # 1. Tools Group
        tools_group = QtWidgets.QGroupBox("Network Builder Tools")
        tools_layout = QtWidgets.QVBoxLayout()
        tools_layout.setSpacing(8)

        self.btn_add_root = QtWidgets.QPushButton("Add New Root Node")
        self.btn_add_branch = QtWidgets.QPushButton("Add Branch to Selected")
        self.btn_delete = QtWidgets.QPushButton("Delete Selected")
        self.btn_save_project = QtWidgets.QPushButton("Save Project")
        self.btn_load_project = QtWidgets.QPushButton("Load Project")

        for button in (self.btn_add_root, self.btn_add_branch, self.btn_delete, self.btn_save_project, self.btn_load_project):
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            button.setMinimumHeight(34)

        self.btn_add_root.setToolTip("Creates an unattached starting point.")
        self.btn_add_branch.setToolTip("Select a node, then click this to instantly sprout a new vessel and child node.")

        tools_layout.addWidget(self.btn_add_root)
        tools_layout.addWidget(self.btn_add_branch)
        tools_layout.addWidget(self.btn_delete)
        tools_layout.addWidget(self.btn_save_project)
        tools_layout.addWidget(self.btn_load_project)
        tools_group.setLayout(tools_layout)
        self.layout.addWidget(tools_group)

        # 2. Vessel Geometry + Topology
        vessel_group = QtWidgets.QGroupBox("Vessel Geometry")
        vessel_layout = QtWidgets.QFormLayout()
        vessel_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        vessel_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        vessel_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        vessel_layout.setHorizontalSpacing(10)
        vessel_layout.setVerticalSpacing(8)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.name_edit.textChanged.connect(self.update_name)

        self.type_combo = QtWidgets.QComboBox()
        geometry_types = variablesDict.get('geometryType', {}).get('strCases', [])
        if not geometry_types:
            geometry_types = ['uniform', 'cone']
        self.type_combo.addItems(geometry_types)
        self.type_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.type_combo.currentTextChanged.connect(self.update_type)

        self.grid_points_edit = QtWidgets.QSpinBox()
        self.grid_points_edit.setRange(2, 10000)
        self.grid_points_edit.valueChanged.connect(self.update_grid_points)

        self.left_daughter_edit = QtWidgets.QLineEdit()
        self.left_daughter_edit.setReadOnly(True)
        self.right_daughter_edit = QtWidgets.QLineEdit()
        self.right_daughter_edit.setReadOnly(True)
        self.angle_y_edit = QtWidgets.QLineEdit()
        self.angle_y_edit.setPlaceholderText("rad")
        self.angle_y_edit.editingFinished.connect(self.update_angle_y)

        self.length_m_edit = QtWidgets.QDoubleSpinBox()
        self.length_m_edit.setRange(0.0, 10000.0)
        self.length_m_edit.setDecimals(6)
        self.length_m_edit.setSpecialValueText("N/A")
        self.length_m_edit.setSuffix(" m")
        self.length_m_edit.valueChanged.connect(self.update_length_m)

        self.radius_prox_edit = QtWidgets.QDoubleSpinBox()
        self.radius_prox_edit.setRange(0.0, 1000.0)
        self.radius_prox_edit.setDecimals(6)
        self.radius_prox_edit.setSpecialValueText("N/A")
        self.radius_prox_edit.setSuffix(" m")
        self.radius_prox_edit.valueChanged.connect(self.update_radius_prox)

        self.radius_dist_edit = QtWidgets.QDoubleSpinBox()
        self.radius_dist_edit.setRange(0.0, 1000.0)
        self.radius_dist_edit.setDecimals(6)
        self.radius_dist_edit.setSpecialValueText("N/A")
        self.radius_dist_edit.setSuffix(" m")
        self.radius_dist_edit.valueChanged.connect(self.update_radius_dist)

        vessel_layout.addRow("Identifier:", self.name_edit)
        vessel_layout.addRow("Geometry Type:", self.type_combo)
        vessel_layout.addRow("N (Grid Points):", self.grid_points_edit)
        vessel_layout.addRow("Left Daughter:", self.left_daughter_edit)
        vessel_layout.addRow("Right Daughter:", self.right_daughter_edit)
        vessel_layout.addRow("Angle Y Mother:", self.angle_y_edit)
        vessel_layout.addRow("Length:", self.length_m_edit)
        vessel_layout.addRow("Radius Proximal:", self.radius_prox_edit)
        vessel_layout.addRow("Radius Distal:", self.radius_dist_edit)

        vessel_group.setLayout(vessel_layout)
        self.layout.addWidget(vessel_group)

        compliance_group = QtWidgets.QGroupBox("Vessel Compliance")
        compliance_layout = QtWidgets.QVBoxLayout()
        compliance_layout.setSpacing(8)

        compliance_header = QtWidgets.QFormLayout()
        compliance_header.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        compliance_header.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        compliance_header.setHorizontalSpacing(10)
        compliance_header.setVerticalSpacing(8)

        self.compliance_type_combo = QtWidgets.QComboBox()
        self.compliance_type_combo.addItems(sorted(list(nxml.vesselComplianceElements.keys())))
        self.compliance_type_combo.currentTextChanged.connect(self.on_compliance_type_changed)
        compliance_header.addRow("Compliance Type:", self.compliance_type_combo)
        compliance_layout.addLayout(compliance_header)

        self.compliance_form_widget = QtWidgets.QWidget()
        self.compliance_form_layout = QtWidgets.QFormLayout()
        self.compliance_form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.compliance_form_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.compliance_form_layout.setHorizontalSpacing(10)
        self.compliance_form_layout.setVerticalSpacing(8)
        self.compliance_form_widget.setLayout(self.compliance_form_layout)
        compliance_layout.addWidget(self.compliance_form_widget)
        compliance_group.setLayout(compliance_layout)
        self.layout.addWidget(compliance_group)

        fluid_group = QtWidgets.QGroupBox("Vessel Fluid")
        fluid_layout = QtWidgets.QFormLayout()
        fluid_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        fluid_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        fluid_layout.setHorizontalSpacing(10)
        fluid_layout.setVerticalSpacing(8)

        self.apply_global_fluid_combo = QtWidgets.QComboBox()
        self.apply_global_fluid_combo.addItems(["True", "False"])
        self.apply_global_fluid_combo.currentTextChanged.connect(self.update_apply_global_fluid)

        self.fluid_my_edit = QtWidgets.QLineEdit()
        self.fluid_my_edit.editingFinished.connect(lambda: self.update_fluid_field('my'))
        self.fluid_rho_edit = QtWidgets.QLineEdit()
        self.fluid_rho_edit.editingFinished.connect(lambda: self.update_fluid_field('rho'))
        self.fluid_gamma_edit = QtWidgets.QLineEdit()
        self.fluid_gamma_edit.editingFinished.connect(lambda: self.update_fluid_field('gamma'))

        fluid_layout.addRow("Apply Global Fluid:", self.apply_global_fluid_combo)
        fluid_layout.addRow("my:", self.fluid_my_edit)
        fluid_layout.addRow("rho:", self.fluid_rho_edit)
        fluid_layout.addRow("gamma:", self.fluid_gamma_edit)
        fluid_group.setLayout(fluid_layout)
        self.layout.addWidget(fluid_group)
        # 3. Node Browser (on the right)
        browser_group = QtWidgets.QGroupBox("Node Browser")
        browser_layout = QtWidgets.QVBoxLayout()
        browser_layout.setSpacing(6)
        self.node_list = QtWidgets.QListWidget()
        self.node_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.node_list.itemClicked.connect(self.on_node_list_clicked)
        browser_layout.addWidget(self.node_list)
        browser_group.setLayout(browser_layout)
        self.layout.addWidget(browser_group)

        # 4. Boundary Condition Manager (bottom block)
        bc_group = QtWidgets.QGroupBox("Boundary Condition Manager")
        bc_layout = QtWidgets.QVBoxLayout()
        bc_layout.setSpacing(8)

        header_form = QtWidgets.QFormLayout()
        header_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        header_form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        header_form.setHorizontalSpacing(10)
        header_form.setVerticalSpacing(8)

        self.bc_type = FixedPopupComboBox(max_items=5)
        self.bc_type.addItems(self.available_bc_types())
        self.bc_type.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.bc_type.setMaxVisibleItems(5)
        list_view = QtWidgets.QListView()
        list_view.setUniformItemSizes(True)
        list_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        list_view.setSpacing(2)
        self.bc_type.setView(list_view)
        self.bc_type.activated[int].connect(self.on_bc_type_changed)

        self.bc_position = QtWidgets.QComboBox()
        self.bc_position.addItems(["Start (0)", "End (-1)"])
        self.bc_position.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        header_form.addRow("BC Type:", self.bc_type)
        header_form.addRow("Position:", self.bc_position)
        bc_layout.addLayout(header_form)

        self.bc_form_widget = QtWidgets.QWidget()
        self.bc_form_layout = QtWidgets.QFormLayout()
        self.bc_form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.bc_form_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.bc_form_layout.setHorizontalSpacing(10)
        self.bc_form_layout.setVerticalSpacing(8)
        self.bc_form_widget.setLayout(self.bc_form_layout)
        bc_layout.addWidget(self.bc_form_widget)

        button_row = QtWidgets.QHBoxLayout()
        self.btn_bc_add = QtWidgets.QPushButton("Add / Update BC")
        self.btn_bc_delete = QtWidgets.QPushButton("Delete BC")
        self.btn_bc_show = QtWidgets.QPushButton("Show BCs")
        for button in (self.btn_bc_add, self.btn_bc_delete, self.btn_bc_show):
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            button.setMinimumHeight(32)
        self.btn_bc_add.clicked.connect(self.add_or_update_boundary_condition)
        self.btn_bc_delete.clicked.connect(self.delete_boundary_condition)
        self.btn_bc_show.clicked.connect(self.show_boundary_conditions)
        button_row.addWidget(self.btn_bc_add)
        button_row.addWidget(self.btn_bc_delete)
        button_row.addWidget(self.btn_bc_show)
        bc_layout.addLayout(button_row)

        bc_group.setLayout(bc_layout)
        self.layout.addWidget(bc_group)
        self.layout.addStretch(1)
        self.set_enabled_fields(False)
        # (Save/Load project buttons will be connected by the main editor)
        self.bc_field_edits = {}
        self.compliance_field_edits = {}
        self._suspend_geometry_sync = False
        self._current_boundary_node = None
        self.on_bc_type_changed(self.bc_type.currentIndex())
        self.on_compliance_type_changed(self.compliance_type_combo.currentText())
        self._apply_responsive_styles(self.width())

    def set_enabled_fields(self, enabled, is_edge=False):
        self.name_edit.setEnabled(enabled)
        self.type_combo.setEnabled(is_edge)
        self.left_daughter_edit.setEnabled(is_edge)
        self.right_daughter_edit.setEnabled(is_edge)
        self.angle_y_edit.setEnabled(is_edge)
        self.length_m_edit.setEnabled(is_edge)
        self.radius_prox_edit.setEnabled(is_edge)
        self.radius_dist_edit.setEnabled(is_edge)
        self.grid_points_edit.setEnabled(is_edge)
        self.compliance_type_combo.setEnabled(is_edge)
        self.compliance_form_widget.setEnabled(is_edge)
        self.apply_global_fluid_combo.setEnabled(is_edge)
        self.fluid_my_edit.setEnabled(is_edge)
        self.fluid_rho_edit.setEnabled(is_edge)
        self.fluid_gamma_edit.setEnabled(is_edge)

    def _apply_responsive_styles(self, width):
        compact = width < 420
        button_padding = 6 if compact else 10
        button_font = 11 if compact else 13
        field_padding = 4 if compact else 6
        field_min_width = 0 if compact else 120
        self.setStyleSheet(f"""
            QWidget {{ background-color: #2b2b2b; color: #eeeeee; font-family: sans-serif; font-size: 13px; }}
            QGroupBox {{ font-weight: bold; border: 1px solid #555; border-radius: 5px; margin-top: 15px; padding-top: 15px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; color: #80c0ff; }}
            QLineEdit, QDoubleSpinBox, QComboBox {{
                background-color: #3b3b3b; color: white; padding: {field_padding}px; border: 1px solid #555; border-radius: 3px; min-width: {field_min_width}px;
            }}
            QComboBox::drop-down {{ width: 24px; border-left: 1px solid #555; }}
            QComboBox QAbstractItemView {{
                background-color: #2f2f2f; color: #ffffff; selection-background-color: #3a7ca5; selection-color: white;
                padding: 6px; outline: 0; min-width: 320px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px 10px; min-height: 24px; }}
            QPushButton {{ background-color: #3a7ca5; color: white; border: none; padding: {button_padding}px; border-radius: 4px; font-weight: bold; margin-bottom: 5px; font-size: {button_font}px; }}
            QPushButton:hover {{ background-color: #4a8cb5; }}
            QPushButton:pressed {{ background-color: #2a6c95; }}
            QPushButton#btn_delete {{ background-color: #a53a3a; }}
            QPushButton#btn_delete:hover {{ background-color: #b54a4a; }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_styles(self.width())

    def on_selection_changed(self):
        selected = self.scene.selectedItems()
        if not selected or len(selected) > 1:
            self.current_item = None
            self.set_enabled_fields(False)
            self.name_edit.clear()
            self.left_daughter_edit.clear()
            self.right_daughter_edit.clear()
            self.angle_y_edit.clear()
            self.length_m_edit.setValue(0.0)
            self.radius_prox_edit.setValue(0.0)
            self.radius_dist_edit.setValue(0.0)
            self.grid_points_edit.setValue(2)
            self.compliance_type_combo.setCurrentIndex(-1)
            self._build_compliance_editor(None)
            self.apply_global_fluid_combo.setCurrentIndex(0)
            self.fluid_my_edit.clear()
            self.fluid_rho_edit.clear()
            self.fluid_gamma_edit.clear()
            self.refresh_boundary_conditions_view()
            return

        item = selected[0]
        self.current_item = item

        self.blockSignals(True)
        self.name_edit.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.left_daughter_edit.blockSignals(True)
        self.right_daughter_edit.blockSignals(True)
        self.angle_y_edit.blockSignals(True)
        self.length_m_edit.blockSignals(True)
        self.radius_prox_edit.blockSignals(True)
        self.radius_dist_edit.blockSignals(True)
        self.grid_points_edit.blockSignals(True)
        self.compliance_type_combo.blockSignals(True)
        self.apply_global_fluid_combo.blockSignals(True)

        self.name_edit.setText(item.name)

        if isinstance(item, VesselEdge):
            self.set_enabled_fields(True, is_edge=True)
            self.type_combo.setCurrentText(item.geometry_type if hasattr(item, 'geometry_type') else item.vessel_type)
            self._suspend_geometry_sync = True
            self.length_m_edit.setValue(float(item.length_mm) / 1000.0)
            self.radius_prox_edit.setValue(self._area_mm2_to_radius_m(item.area_start_mm2))
            self.radius_dist_edit.setValue(self._area_mm2_to_radius_m(item.area_end_mm2))
            self.grid_points_edit.setValue(int(getattr(item, 'grid_points', 2)))
            self._suspend_geometry_sync = False
            self.angle_y_edit.setText(str(getattr(item, 'angle_y_mother', 0.0)))
            left_edge, right_edge = self._get_daughter_edges(item)
            self.left_daughter_edit.setText(left_edge.name if left_edge else '')
            self.right_daughter_edit.setText(right_edge.name if right_edge else '')
            comp_type = getattr(item, 'compliance_type', '')
            if comp_type:
                self.compliance_type_combo.setCurrentText(comp_type)
                self._build_compliance_editor(comp_type, item)
            else:
                self._build_compliance_editor(self.compliance_type_combo.currentText(), item)
            fluid_values = getattr(item, 'fluid_values', {})
            self.apply_global_fluid_combo.setCurrentText("True" if fluid_values.get('applyGlobalFluid', True) else "False")
            self.fluid_my_edit.setText('' if fluid_values.get('my', None) is None else str(fluid_values.get('my')))
            self.fluid_rho_edit.setText('' if fluid_values.get('rho', None) is None else str(fluid_values.get('rho')))
            self.fluid_gamma_edit.setText('' if fluid_values.get('gamma', None) is None else str(fluid_values.get('gamma')))
            self.refresh_boundary_conditions_view()
        elif isinstance(item, JunctionNode):
            self.set_enabled_fields(True, is_edge=False)
            self.type_combo.setCurrentIndex(-1)
            self.left_daughter_edit.clear()
            self.right_daughter_edit.clear()
            self.angle_y_edit.clear()
            self.length_m_edit.setValue(0.0)
            self.radius_prox_edit.setValue(0.0)
            self.radius_dist_edit.setValue(0.0)
            self.grid_points_edit.setValue(2)
            self.compliance_type_combo.setCurrentIndex(-1)
            self._build_compliance_editor(None)
            self.apply_global_fluid_combo.setCurrentIndex(0)
            self.fluid_my_edit.clear()
            self.fluid_rho_edit.clear()
            self.fluid_gamma_edit.clear()
            # update node browser selection highlight
            self.update_node_list_selection(item)
            self.refresh_boundary_conditions_view()

        self.name_edit.blockSignals(False)
        self.type_combo.blockSignals(False)
        self.left_daughter_edit.blockSignals(False)
        self.right_daughter_edit.blockSignals(False)
        self.angle_y_edit.blockSignals(False)
        self.length_m_edit.blockSignals(False)
        self.radius_prox_edit.blockSignals(False)
        self.radius_dist_edit.blockSignals(False)
        self.grid_points_edit.blockSignals(False)
        self.compliance_type_combo.blockSignals(False)
        self.apply_global_fluid_combo.blockSignals(False)
        self.blockSignals(False)

    def update_name(self, text):
        if self.current_item:
            self.current_item.name = text
            self.current_item.update_visuals()

    def update_type(self, text):
        if isinstance(self.current_item, VesselEdge):
            self.current_item.vessel_type = text
            self.current_item.geometry_type = text

    def _area_mm2_to_radius_m(self, area_mm2):
        try:
            return math.sqrt(max(0.0, float(area_mm2)) * 1e-6 / math.pi)
        except Exception:
            return 0.0

    def _radius_m_to_area_mm2(self, radius_m):
        try:
            return math.pi * (float(radius_m) ** 2) * 1e6
        except Exception:
            return 0.0

    def update_length_m(self, val):
        if self._suspend_geometry_sync:
            return
        if isinstance(self.current_item, VesselEdge):
            self.current_item.length_mm = val * 1000.0
            self.scene.enforce_fixed_lengths()

    def update_radius_prox(self, val):
        if self._suspend_geometry_sync:
            return
        if isinstance(self.current_item, VesselEdge):
            self.current_item.area_start_mm2 = self._radius_m_to_area_mm2(val)
            self.current_item.update_visuals()

    def update_radius_dist(self, val):
        if self._suspend_geometry_sync:
            return
        if isinstance(self.current_item, VesselEdge):
            self.current_item.area_end_mm2 = self._radius_m_to_area_mm2(val)
            self.current_item.update_visuals()

    def update_grid_points(self, val):
        if isinstance(self.current_item, VesselEdge):
            self.current_item.grid_points = int(val)

    def update_angle_y(self):
        if not isinstance(self.current_item, VesselEdge):
            return
        text = self.angle_y_edit.text().strip()
        if text == '' or text.lower() == 'none':
            self.current_item.angle_y_mother = 0.0
            return
        try:
            self.current_item.angle_y_mother = float(text)
        except ValueError:
            pass

    def update_apply_global_fluid(self, text):
        if not isinstance(self.current_item, VesselEdge):
            return
        self.current_item.fluid_values['applyGlobalFluid'] = text.lower() == 'true'

    def update_fluid_field(self, field_name):
        if not isinstance(self.current_item, VesselEdge):
            return
        widget = {
            'my': self.fluid_my_edit,
            'rho': self.fluid_rho_edit,
            'gamma': self.fluid_gamma_edit,
        }.get(field_name)
        if widget is None:
            return
        text = widget.text().strip()
        if text == '' or text.lower() == 'none':
            self.current_item.fluid_values[field_name] = None
            return
        try:
            self.current_item.fluid_values[field_name] = float(text)
        except ValueError:
            pass

    def available_bc_types(self):
        return sorted([key for key in nxml.bcTagsClassReferences.keys() if not key.startswith('_')])

    def _get_daughter_edges(self, edge):
        if not isinstance(edge, VesselEdge):
            return None, None
        children = list(edge.dest_node.outgoing_edges) if edge.dest_node else []
        if not children:
            return None, None
        children.sort(key=lambda e: e.dest_node.scenePos().x() if e.dest_node else 0.0)
        left_edge = children[0] if len(children) >= 1 else None
        right_edge = children[1] if len(children) >= 2 else None
        return left_edge, right_edge

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _selected_boundary_node(self):
        if isinstance(self.current_item, JunctionNode):
            return self.current_item
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, JunctionNode):
                return item
        return None

    def _boundary_vessel_id_for_node(self, node):
        if node is None:
            return None
        if node.outgoing_edges:
            return id(node.outgoing_edges[0])
        if node.incoming_edges:
            return id(node.incoming_edges[0])
        return None

    def _ensure_boundary_conditions_list(self, node):
        if not hasattr(node, 'boundary_conditions') or node.boundary_conditions is None:
            node.boundary_conditions = []
        return node.boundary_conditions

    def _parse_bc_value(self, template_value, text_value):
        if text_value is None:
            return None
        text_value = str(text_value).strip()
        if text_value == '' or text_value.lower() == 'none':
            return None
        if isinstance(template_value, bool):
            return text_value.lower() in ('1', 'true', 'yes', 'y', 't')
        if isinstance(template_value, (int, float)):
            try:
                number = float(text_value)
                if isinstance(template_value, int) and number.is_integer():
                    return int(number)
                return number
            except ValueError:
                return None
        return text_value

    def _parse_vessel_value(self, field_name, text_value):
        if text_value is None:
            return None
        text_value = str(text_value).strip()
        if text_value == '' or text_value.lower() == 'none':
            return None
        type_info = variablesDict.get(field_name, {}).get('type', '')
        if 'bool' in type_info:
            return text_value.lower() in ('1', 'true', 'yes', 'y', 't')
        if 'int' in type_info and 'float' not in type_info:
            try:
                return int(float(text_value))
            except ValueError:
                return None
        if 'float' in type_info:
            try:
                return float(text_value)
            except ValueError:
                return None
        return text_value

    def _create_compliance_widget(self, field_name):
        type_info = variablesDict.get(field_name, {}).get('type', '')
        if 'bool' in type_info:
            widget = QtWidgets.QComboBox()
            widget.addItems(["False", "True"])
            return widget
        widget = QtWidgets.QLineEdit()
        widget.setPlaceholderText(field_name)
        return widget

    def _set_compliance_widget_value(self, widget, field_name, value):
        if isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentText("True" if value else "False")
        else:
            widget.setText('' if value is None else str(value))

    def _get_compliance_widget_value(self, widget, field_name):
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText().lower() == 'true'
        return self._parse_vessel_value(field_name, widget.text())

    def _cache_compliance_values(self):
        if not isinstance(self.current_item, VesselEdge):
            return
        comp_type = self.current_item.compliance_type
        if not comp_type:
            return
        values = {}
        for field_name, widget in self.compliance_field_edits.items():
            values[field_name] = self._get_compliance_widget_value(widget, field_name)
        self.current_item.compliance_values_by_type[comp_type] = values

    def _build_compliance_editor(self, compliance_type, edge=None):
        self._clear_layout(self.compliance_form_layout)
        self.compliance_field_edits = {}
        if not compliance_type:
            return
        field_names = list(nxml.vesselComplianceElements.get(compliance_type, []))
        field_names = [f for f in field_names if f != 'complianceType']
        values = {}
        if isinstance(edge, VesselEdge):
            values = edge.compliance_values_by_type.get(compliance_type, {})
        for field_name in field_names:
            widget = self._create_compliance_widget(field_name)
            self._set_compliance_widget_value(widget, field_name, values.get(field_name, None))
            if isinstance(widget, QtWidgets.QComboBox):
                widget.currentTextChanged.connect(lambda _val, f=field_name: self.update_compliance_field(f))
            else:
                widget.editingFinished.connect(lambda f=field_name: self.update_compliance_field(f))
            self.compliance_form_layout.addRow(f"{field_name}:", widget)
            self.compliance_field_edits[field_name] = widget

    def on_compliance_type_changed(self, compliance_type):
        if isinstance(self.current_item, VesselEdge):
            self._cache_compliance_values()
            self.current_item.compliance_type = compliance_type
        self._build_compliance_editor(compliance_type, self.current_item)

    def update_compliance_field(self, field_name):
        if not isinstance(self.current_item, VesselEdge):
            return
        comp_type = self.current_item.compliance_type
        if not comp_type:
            return
        widget = self.compliance_field_edits.get(field_name)
        if widget is None:
            return
        value = self._get_compliance_widget_value(widget, field_name)
        if comp_type not in self.current_item.compliance_values_by_type:
            self.current_item.compliance_values_by_type[comp_type] = {}
        self.current_item.compliance_values_by_type[comp_type][field_name] = value

    def _bc_name_for_position(self, bc_type, position_index):
        return bc_type if position_index == 0 else f'_{bc_type}'

    def _build_bc_editor(self, bc_type, bc_instance=None):
        self._clear_layout(self.bc_form_layout)
        self.bc_field_edits = {}
        if not bc_type:
            return

        field_names = list(nxml.boundaryConditionElements.get(bc_type, []))
        for field_name in field_names:
            template_value = getattr(bc_instance, field_name, None) if bc_instance is not None else None
            if template_value is None:
                try:
                    template_value = getattr(eval(nxml.bcTagsClassReferences[bc_type])(), field_name)
                except Exception:
                    template_value = None

            editor = QtWidgets.QLineEdit()
            if template_value is not None:
                editor.setText(str(template_value))
            editor.setPlaceholderText(str(field_name))
            self.bc_form_layout.addRow(f"{field_name}:", editor)
            self.bc_field_edits[field_name] = editor

    def _populate_bc_editor_from_instance(self, bc_instance):
        if bc_instance is None:
            return
        bc_type = bc_instance.getVariableValue('name') or bc_instance.name
        if bc_type.startswith('_'):
            self.bc_position.setCurrentIndex(1)
            bc_type = bc_type[1:]
        else:
            self.bc_position.setCurrentIndex(0)
        if bc_type in self.available_bc_types():
            self.bc_type.blockSignals(True)
            self.bc_type.setCurrentText(bc_type)
            self.bc_type.blockSignals(False)
            self._build_bc_editor(bc_type, bc_instance)
            for field_name, editor in self.bc_field_edits.items():
                value = getattr(bc_instance, field_name, None)
                editor.setText('' if value is None else str(value))

    def _get_current_bc_instance(self):
        node = self._selected_boundary_node()
        if node is None:
            return None
        conditions = self._ensure_boundary_conditions_list(node)
        for bc in conditions:
            name = bc.getVariableValue('name') if hasattr(bc, 'getVariableValue') else getattr(bc, 'name', None)
            if name == self._bc_name_for_position(self.bc_type.currentText(), self.bc_position.currentIndex()):
                return bc
        return None

    def refresh_boundary_conditions_view(self):
        node = self._selected_boundary_node()
        self._current_boundary_node = node
        if node is None:
            self._build_bc_editor(self.bc_type.currentText())
            return

        conditions = self._ensure_boundary_conditions_list(node)
        bc_instance = self._get_current_bc_instance()
        if bc_instance is not None:
            self._populate_bc_editor_from_instance(bc_instance)
            return

        node_bc = getattr(node, 'boundary_condition', None)
        if node_bc is not None and hasattr(node_bc, 'getVariableValue'):
            self._populate_bc_editor_from_instance(node_bc)
            return

        if conditions:
            self._populate_bc_editor_from_instance(conditions[0])
            return

        self._build_bc_editor(self.bc_type.currentText())

    def on_bc_type_changed(self, index):
        txt = self.bc_type.itemText(index)
        if txt:
            self._build_bc_editor(txt)
        self.bc_type.hidePopup()

    def _build_boundary_condition_instance(self):
        bc_type = self.bc_type.currentText()
        if bc_type not in nxml.bcTagsClassReferences:
            return None

        cls_name = nxml.bcTagsClassReferences[bc_type]
        bc_instance = eval(cls_name)()
        position_index = self.bc_position.currentIndex()
        bc_name = self._bc_name_for_position(bc_type, position_index)
        bc_instance.update({'name': bc_name})
        if hasattr(bc_instance, 'setPosition'):
            bc_instance.setPosition(0 if position_index == 0 else -1)

        for field_name, editor in self.bc_field_edits.items():
            template_value = getattr(bc_instance, field_name, None)
            parsed_value = self._parse_bc_value(template_value, editor.text())
            bc_instance.update({field_name: parsed_value})

        return bc_instance

    def add_or_update_boundary_condition(self):
        node = self._selected_boundary_node()
        if node is None:
            QtWidgets.QMessageBox.warning(self, 'No node selected', 'Select a boundary node first.')
            return

        bc_instance = self._build_boundary_condition_instance()
        if bc_instance is None:
            QtWidgets.QMessageBox.warning(self, 'Invalid BC type', 'Choose a valid boundary condition type.')
            return

        conditions = self._ensure_boundary_conditions_list(node)
        for index, existing in enumerate(conditions):
            existing_name = existing.getVariableValue('name') if hasattr(existing, 'getVariableValue') else getattr(existing, 'name', None)
            if existing_name == bc_instance.getVariableValue('name'):
                conditions[index] = bc_instance
                break
        else:
            conditions.append(bc_instance)
        node.boundary_condition = bc_instance
        self.refresh_boundary_conditions_view()

    def delete_boundary_condition(self):
        node = self._selected_boundary_node()
        if node is None:
            return
        conditions = self._ensure_boundary_conditions_list(node)
        target_name = self._bc_name_for_position(self.bc_type.currentText(), self.bc_position.currentIndex())
        for index, existing in enumerate(list(conditions)):
            existing_name = existing.getVariableValue('name') if hasattr(existing, 'getVariableValue') else getattr(existing, 'name', None)
            if existing_name == target_name:
                del conditions[index]
                break
        if conditions:
            node.boundary_condition = conditions[0]
        elif hasattr(node, 'boundary_condition'):
            node.boundary_condition = None
        self.refresh_boundary_conditions_view()

    def show_boundary_conditions(self):
        node = self._selected_boundary_node()
        if node is None:
            QtWidgets.QMessageBox.information(self, 'Boundary conditions', 'No boundary node selected.')
            return
        conditions = self._ensure_boundary_conditions_list(node)
        if not conditions:
            QtWidgets.QMessageBox.information(self, 'Boundary conditions', 'No boundary conditions defined.')
            return
        lines = []
        for bc in conditions:
            name = bc.getVariableValue('name') if hasattr(bc, 'getVariableValue') else getattr(bc, 'name', 'BC')
            lines.append(name)
            for field_name in nxml.boundaryConditionElements.get(name, nxml.boundaryConditionElements.get(name.lstrip('_'), [])):
                if hasattr(bc, 'getVariableValue'):
                    lines.append(f'  {field_name}: {bc.getVariableValue(field_name)}')
                else:
                    lines.append(f'  {field_name}: {getattr(bc, field_name, None)}')
        QtWidgets.QMessageBox.information(self, 'Boundary conditions', '\n'.join(lines))

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

    def save_project(self):
        # wrapper to save project XML using the full network exporter
        self.export_network_xml()

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
