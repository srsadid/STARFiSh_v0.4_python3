from PySide6 import QtWidgets, QtCore
from vnc_ui.scene_items import JunctionNode

# Scale: 1 physical mm = PIXELS_PER_MM pixels on screen
PIXELS_PER_MM = 15.0

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
            if node in visited:
                return
            visited.add(node)

            for edge in node.outgoing_edges:
                child = edge.dest_node

                # Get current visual line to find the angle the user wanted
                current_line = QtCore.QLineF(node.scenePos(), child.scenePos())

                # If nodes are right on top of each other, give a default angle (straight down)
                if current_line.length() < 1.0:
                    current_line.setAngle(270)  # 270 is straight down in QGraphicsScene

                # Force the length to perfectly match the physical length_mm property
                fixed_visual_length = edge.length_mm * PIXELS_PER_MM
                current_line.setLength(fixed_visual_length)

                # Move the child node to the fixed position
                child.setPos(current_line.p2())
                edge.update_visuals()

                traverse_and_fix(child)

        for root in roots:
            traverse_and_fix(root)
