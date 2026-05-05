from PySide6 import QtWidgets, QtCore

class FixedPopupComboBox(QtWidgets.QComboBox):
    def __init__(self, max_items=5, parent=None):
        super().__init__(parent)
        self._max_popup_items = max_items
        self._popup_installed = False
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_app_focus_changed)
            app.installEventFilter(self)

    def set_popup_max_items(self, max_items):
        self._max_popup_items = max_items

    def showPopup(self):
        super().showPopup()
        self._apply_popup_height()
        self._attach_popup_listeners()

    def _attach_popup_listeners(self):
        if self._popup_installed:
            return
        view = self.view()
        if view is None:
            return
        popup = view.window()
        if popup is not None:
            popup.installEventFilter(self)
        view.installEventFilter(self)
        if view.viewport() is not None:
            view.viewport().installEventFilter(self)
        self._popup_installed = True

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and self._popup_visible():
            if hasattr(event, 'globalPosition'):
                global_pos = event.globalPosition().toPoint()
            else:
                global_pos = event.globalPos()
            if not self._popup_contains(global_pos):
                self.hidePopup()
        return super().eventFilter(obj, event)

    def _on_app_focus_changed(self, old, new):
        if not self._popup_visible():
            return
        if new is None:
            self.hidePopup()
            return
        view = self.view()
        if self.isAncestorOf(new):
            return
        if view is not None and view.isAncestorOf(new):
            return
        self.hidePopup()

    def _popup_visible(self):
        view = self.view()
        return view is not None and view.isVisible()

    def _popup_contains(self, global_pos):
        view = self.view()
        if view is None:
            return False
        popup = view.window()
        if popup is not None and popup.geometry().contains(global_pos):
            return True
        return self.rect().contains(self.mapFromGlobal(global_pos))

    def _apply_popup_height(self):
        view = self.view()
        if view is None:
            return
        row_height = view.sizeHintForRow(0)
        if row_height <= 0:
            row_height = view.fontMetrics().height() + 8
        visible = min(self._max_popup_items, max(1, self.count()))
        spacing = view.spacing() if hasattr(view, "spacing") else 0
        frame = view.frameWidth() * 2
        height = (row_height * visible) + (spacing * max(0, visible - 1)) + frame
        view.setFixedHeight(height)
        view.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        popup = view.window()
        if popup is not None:
            margins = popup.contentsMargins()
            popup.setFixedHeight(height + margins.top() + margins.bottom())
