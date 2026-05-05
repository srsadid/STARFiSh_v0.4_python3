import math
from PySide6 import QtWidgets, QtCore, QtGui

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
        self.vessel_type = "uniform"
        self.geometry_type = "uniform"
        self.grid_points = 50
        self.angle_y_mother = 0.0
        self.compliance_type = "Hayashi"
        self.compliance_values_by_type = {}
        self.fluid_values = {
            'applyGlobalFluid': True,
            'my': 1.0e-6,
            'rho': 1050.0,
            'gamma': 2.0,
        }

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
