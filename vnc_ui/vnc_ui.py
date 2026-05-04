import sys
from PySide6 import QtWidgets, QtCore
from NodeGraphQt import NodeGraph, BaseNode, PropertiesBinWidget

class ArteryNode(BaseNode):
    __identifier__ = 'vascular.nodes'
    NODE_NAME = 'Artery Segment'

    def __init__(self):
        super(ArteryNode, self).__init__()
        self.add_input('in', multi_input=True)
        self.add_output('out', multi_output=True)

        # Remove 'label=' as it's not supported in create_property
        # The first string will be the name used in the Properties Bin
        self.create_property('length_mm', 10.0)
        self.create_property('area_start_mm2', 5.0)
        self.create_property('area_end_mm2', 5.0)
        self.create_property('elasticity_Pa', 1.0e6)
        
        # add_combo_menu usually takes (name, label, items)
        self.add_combo_menu('vessel_type', 'Vessel Shape', 
                            items=['Cylindrical', 'Conical', 'Elastic Tube'])

        self.set_color(150, 30, 30)

class VascularEditor(QtWidgets.QMainWindow):
    def __init__(self):
        super(VascularEditor, self).__init__()
        self.setWindowTitle('Vascular Network Designer')

        self.graph = NodeGraph()
        self.graph.register_node(ArteryNode)

        layout = QtWidgets.QHBoxLayout()
        self.viewer = self.graph.viewer()
        layout.addWidget(self.viewer)

        self.prop_bin = PropertiesBinWidget(node_graph=self.graph)
        self.prop_bin.setMinimumWidth(350)
        layout.addWidget(self.prop_bin)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.setup_sample_network()

    def setup_sample_network(self):
        # Clear existing to be safe
        self.graph.clear_session()
        
        # Create Nodes
        root = self.graph.create_node('vascular.nodes.ArteryNode', name='Inlet')
        b1 = self.graph.create_node('vascular.nodes.ArteryNode', name='Branch A', pos=[400, -100])
        b2 = self.graph.create_node('vascular.nodes.ArteryNode', name='Branch B', pos=[400, 100])

        # Connect
        root.set_output(0, b1.input(0))
        root.set_output(0, b2.input(0))
        
        self.graph.auto_layout_nodes()
        self.graph.fit_to_selection()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    editor = VascularEditor()
    editor.showMaximized()
    sys.exit(app.exec())