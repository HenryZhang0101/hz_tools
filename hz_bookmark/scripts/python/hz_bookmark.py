config = {
    "Default_Sort_Mode" : "Node Type", # "Color", "Name", "Node Type"
    "shortcut" : {
        "Delete" : "Del",
        "Refresh" : "R",
        "Copy_Node" : "Alt+C",
        "Copy_Path" : "Ctrl+C",
        "Paste_Node" : "Ctrl+V",
        "Copy_As_ObjMerge_Relative" : "Ctrl+Shift+R",
        "Copy_As_OBjMerge_Absolute" : "Ctrl+Shift+C",
        "Open_Parmeter" : "Ctrl+P", 
        "Close" : "Q"
    }

}

import hou
from PySide2 import QtWidgets, QtCore  
from PySide2.QtGui import QColor, QBrush, QIcon, QKeySequence, QRegExpValidator

class SortableItem(QtWidgets.QTreeWidgetItem):
    def __lt__(self, other):
        tree = self.treeWidget()
        column = tree.sortColumn()

        sort_mode = getattr(tree, 'sort_mode', 'name')

        if sort_mode == 'Color':
            color1 = self.background(column).color()
            color2 = other.background(column).color()

            hsv1 = (color1.hue(), color1.saturation(), color1.value())
            hsv2 = (color2.hue(), color2.saturation(), color2.value())

            return hsv1 < hsv2
        
        elif sort_mode == "Node Type":
            value1 = self.data(column, QtCore.Qt.UserRole)
            value2 = other.data(column, QtCore.Qt.UserRole)
            return str(value1) < str(value2)

        else:
            return self.text(column).lower() < other.text(column).lower()

class BundleConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, name = None, pattern = None, filter = hou.nodeTypeFilter.NoFilter, windowName = ""):
        super().__init__(parent)
        self.setWindowTitle(windowName)
        self.setMinimumWidth(500)

        self.pattern = pattern
        if not pattern:
            self.setWindowIcon(hou.qt.Icon("DATATYPES_bundle"))
        else:
            self.setWindowIcon(hou.qt.Icon("DATATYPES_bundle_smart"))
            
        layout = QtWidgets.QFormLayout(self)

        # Bundle Name
        self.nameEdit = QtWidgets.QLineEdit(name)
        regex = QtCore.QRegExp(r'^[A-Za-z0-9_]+$')
        validator = QRegExpValidator(regex)
        self.nameEdit.setValidator(validator)
                
        # Bundle Pattern
        self.patternEdit = QtWidgets.QLineEdit(pattern)

        # Filter Type
        filterNames = ["Any node", "Any Obj","Any SOP", "Any ROP", "Obj:Geometry", "Obj:Light"]
        self.filterObjects = [hou.nodeTypeFilter.NoFilter, hou.nodeTypeFilter.Obj,hou.nodeTypeFilter.Sop, hou.nodeTypeFilter.Rop,hou.nodeTypeFilter.ObjGeometry,hou.nodeTypeFilter.ObjLight]
        filterIndex = self.filterObjects.index(filter)
        self.filterTypeCombo = QtWidgets.QComboBox()
        self.filterTypeCombo.addItems(filterNames)
        self.filterTypeCombo.setCurrentIndex(filterIndex)

        # Buttons
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout.addRow("Bundle Name:", self.nameEdit)
        if pattern:
            layout.addRow("Bundle Pattern:", self.patternEdit)
            layout.addRow("Node Filter:", self.filterTypeCombo)
        layout.addRow(buttonBox)

    def getValues(self):
        if self.pattern:
            self.pattern = self.patternEdit.text()

        return (
            self.nameEdit.text(),
            self.pattern,
            self.filterObjects[self.filterTypeCombo.currentIndex()]
        )
    def accept(self):
        name = self.nameEdit.text()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Invalid Name", "Name cannot be empty.")
            return
        if not self.nameEdit.hasAcceptableInput():
            QtWidgets.QMessageBox.warning(self, "Invalid Name", "Name must only contain letters, numbers, and underscores.")
            return
        super().accept()

class Bookmark(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # bundle layout
        self.bundleLayout = QtWidgets.QHBoxLayout()
        self.bundleComboBox = QtWidgets.QComboBox()
        self.bundleComboBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.bundleComboBox.currentIndexChanged.connect(self.updateTree)
        self.addBundle_btn = QtWidgets.QPushButton()
        self.addBundle_btn.setIcon(hou.qt.Icon("DATATYPES_bundle"))
        self.addBundle_btn.clicked.connect(lambda: self.addBundle(pattern=None))
        self.addSmartBundle_btn = QtWidgets.QPushButton()
        self.addSmartBundle_btn.setIcon(hou.qt.Icon("DATATYPES_bundle_smart"))
        self.addSmartBundle_btn.clicked.connect(lambda: self.addBundle(pattern="/obj/*",windowName = "add smart node bundle"))
        self.renameBundle_btn = QtWidgets.QPushButton()
        self.renameBundle_btn.setIcon(hou.qt.Icon("SCENEGRAPH_collection_lights_editable.svg"))
        self.renameBundle_btn.clicked.connect(self.editBundle)
        self.deleteBundle_btn = QtWidgets.QPushButton()
        self.deleteBundle_btn.setIcon(hou.qt.Icon("BUTTONS_delete"))
        self.deleteBundle_btn.clicked.connect(self.removeBundle)
        self.addBundle_btn.setToolTip("Add a new bundle")
        self.addSmartBundle_btn.setToolTip("Add a smart bundle")
        self.renameBundle_btn.setToolTip("Edit current bundle")
        self.deleteBundle_btn.setToolTip("Delete current bundle")
        self.bundleLayout.addWidget(self.bundleComboBox)
        self.bundleLayout.addWidget(self.addBundle_btn)
        self.bundleLayout.addWidget(self.addSmartBundle_btn)
        self.bundleLayout.addWidget(self.renameBundle_btn)
        self.bundleLayout.addWidget(self.deleteBundle_btn)

        # search bar
        self.searchLine = hou.qt.SearchLineEdit()
        self.searchLine.textChanged.connect(self.searchItem)

        # node tree
        self.nodeTree = QtWidgets.QTreeWidget()
        self.nodeTree.setAlternatingRowColors(True)
        self.nodeTree.setExpandsOnDoubleClick(False)
        self.nodeTree.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.nodeTree.itemDoubleClicked.connect(self.findNode)
        self.nodeTree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.nodeTree.setSortingEnabled(True)
        self.nodeTree.setColumnCount(4)
        self.nodeTree.headerItem().setText(0,"Nodes")
        self.nodeTree.headerItem().setText(1,"")
        self.nodeTree.headerItem().setText(2,"")
        self.nodeTree.headerItem().setText(3,"")
        self.nodeTree.headerItem().setIcon(1,hou.qt.Icon("NETVIEW_display_flag"))
        self.nodeTree.headerItem().setIcon(2,hou.qt.Icon("NETVIEW_template_flag"))
        self.nodeTree.headerItem().setIcon(3,hou.qt.Icon("NETVIEW_selectable_template_flag"))
        
        # node tree header
        header = self.nodeTree.header()
        header.setMinimumSectionSize(20)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)  
        for i in range(1, 4):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
            self.nodeTree.setColumnWidth(i, 25)
        header.setStretchLastSection(False)

        # right click menu
        self.nodeTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.nodeTree.customContextMenuRequested.connect(self.openMenu)
        self.nodeTree.itemClicked.connect(self.toggleColumnState)
        
        # load config
        self.config = config
        self.initBundle()
        self.updateTree()
        self.configShortcut()
        self.setSortMode(self.config["Default_Sort_Mode"])
        self.nodeTree.expandAll()

        # layout
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.treelayout = QtWidgets.QHBoxLayout()
        self.treelayout.addWidget(self.nodeTree)
        self.mainLayout.addLayout(self.bundleLayout)
        self.mainLayout.addWidget(self.searchLine)
        self.mainLayout.addLayout(self.treelayout)

        # self.test_btn = QtWidgets.QPushButton("test")
        # self.test_btn.clicked.connect(self.test)
        # self.mainLayout.addWidget(self.test_btn)

        self.setLayout(self.mainLayout)
        self.setAcceptDrops(True)
        self.showLayout()
    
    def test(self):
        print("test")
                
    def showLayout(self):
        return self.mainLayout
    
    def  closeTab(self):
        tabs = hou.ui.floatingPaneTabs()
        for tab in tabs:
            if tab.isCurrentTab():
                widget = tab.activeInterfaceRootWidget()
                if widget is self:
                    tab.close()

    def openMenu(self, position):
        desktop = hou.ui.curDesktop()
        tab =  desktop.paneTabOfType(hou.paneTabType.NetworkEditor)
        root:hou.OpNode = tab.pwd()
        root_type = root.type().childTypeCategory().name()
        menu = QtWidgets.QMenu()
        menu.setStyleSheet("""
                QMenu {
                    background-color: #444444;
                    border: 1px solid #222;
                }
                QMenu::item {
                    padding: 3px 10px;
                }
                QMenu::item:selected {
                    background-color: #666666;
                }
                QMenu::separator {
                    height: 1px;
                    background: #888;
                    margin: 4px 0;
                }
            """)

        item = self.nodeTree.itemAt(position)
        if not item:
            action1 = menu.addAction("Rrefresh")
            menu.addSeparator()
            action_add = menu.addAction("Add Seleted Nodes")
            action_paste = menu.addAction("Add Node From Clipboard")
            
            menu.addSeparator()
            action2 = menu.addAction("Sort by Name")
            action3 = menu.addAction("Sort by Color")
            action4 = menu.addAction("Sort by Node Type")
            
            
            action = menu.exec_(self.nodeTree.viewport().mapToGlobal(position))
            if action == action1:
                self.initBundle()
            if action == action2:
                self.setSortMode("Name")
            if action == action3:
                self.setSortMode("Color")
            if action == action4:
                self.setSortMode("Node Type")
            if action == action_add:
                self.addSeletcdNodes()
            if action == action_paste:
                self.pasteNode()

        else:
            actions = [
                ("Set Color", lambda: self.setColor(item), True),
                ("Clear Color", self.clearColor, True),
                (None, None, True),  # Separator
                ("Copy Node", lambda: self.copyNode(), True),
                ("Copy Path", lambda: self.copyPath(), True),
                ("Copy As ObjMerge - Relative", lambda: self.copyAsObjMerge(True), root_type == "Sop"),
                ("Copy As ObjMerge - Absolute", lambda: self.copyAsObjMerge(False), root_type == "Sop"),
                (None, None, True),  # Separator
                ("Node Parameter", lambda: self.openParam(), True),
                ("Node Network", lambda: self.openNetwork(item),True),
                (None, None, True),  # Separator
                ("Delete Mark", self.deleteNode, True)
            ]

            action_map = {}

            for label, callback, condition in actions:
                if not condition:
                    continue
                if label is None:
                    menu.addSeparator()
                else:
                    action = menu.addAction(label)
                    action_map[action] = callback

            selected_action = menu.exec_(self.nodeTree.viewport().mapToGlobal(position))
            if selected_action in action_map:
                action_map[selected_action]()

    def initBundle(self):
        currentText= self.bundleComboBox.currentText()
        self.bundleComboBox.clear()
        bundles = hou.nodeBundles()
        if bundles:
            for bundle in bundles:
                name = bundle.name()
                pattern = bundle.pattern()
                if pattern:
                    self.bundleComboBox.addItem(hou.qt.Icon("DATATYPES_bundle_smart"),name)
                else:
                    self.bundleComboBox.addItem(hou.qt.Icon("DATATYPES_bundle"),name)
        else:
            hou.addNodeBundle("Bookmarks")
            self.bundleComboBox.addItem(hou.qt.Icon("DATATYPES_bundle"),"Bookmarks")
        
        if currentText and self.bundleComboBox.findText(currentText) != -1:
            self.bundleComboBox.setCurrentText(currentText)
        
        self.nodeBundle = hou.nodeBundle(self.bundleComboBox.currentText())

    def addBundle(self, pattern = None, windowName = "Add node bundle"):
        dialog = BundleConfigDialog(self, "", pattern=pattern,windowName=windowName)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            name, pattern, filter_type = dialog.getValues()
            if name:
                try:
                    self.nodeBundle = hou.addNodeBundle(name)
                    self.nodeBundle.setPattern(pattern)
                    self.nodeBundle.setFilter(filter_type)
                    pattern = self.nodeBundle.pattern()
                    if pattern:
                        self.bundleComboBox.addItem(hou.qt.Icon("DATATYPES_bundle_smart"),name)
                    else:
                        self.bundleComboBox.addItem(hou.qt.Icon("DATATYPES_bundle"),name)
                    self.bundleComboBox.setCurrentText(name)
                except:
                    hou.ui.displayMessage("Node bundle already exists")

    def editBundle(self):
        name = self.bundleComboBox.currentText()
        dialog = BundleConfigDialog(self, name, pattern=self.nodeBundle.pattern(),filter=self.nodeBundle.filter(),windowName="Edit bundle")
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            newName, pattern, filter_type = dialog.getValues()
            try:
                if name != newName:
                    self.nodeBundle.setName(newName)
                    index = self.bundleComboBox.findText(name)
                    self.bundleComboBox.setItemText(index,newName)
                if self.nodeBundle.pattern():
                    self.nodeBundle.setPattern(pattern)
                    self.nodeBundle.setFilter(filter_type)
                self.updateTree()
                
            except:
                    hou.ui.displayMessage("Node bundle already exists")
                
    def removeBundle(self):
        name = self.bundleComboBox.currentText()
        confirmed = hou.ui.displayConfirmation(f"Remove bundle: {name}")
        if confirmed:
            try:
                hou.nodeBundle(name).destroy()
                index = self.bundleComboBox.findText(name)
                if index != -1:
                    self.bundleComboBox.removeItem(index)
                self.initBundle()
                self.updateTree
                
            except:
                print("nothing removed")

    def updateTree(self):
        state = {}
        root = self.nodeTree.invisibleRootItem()
        for item in self.iterateItems(root):
            state[self.getPath(item)] = item.isExpanded()

        self.nodeBundle = hou.nodeBundle(self.bundleComboBox.currentText())
        if not self.nodeBundle:
            return
        nodes = self.nodeBundle.nodes()
        self.nodeTree.clear()
        for node in nodes:
            if not node.parent().isEditable():
                continue
            parts = node.path().strip("/").split("/")
            root = self.nodeTree.invisibleRootItem()
            parent = root
            for i, part in enumerate(parts):
                if part in [parent.child(i).text(0) for i in range(parent.childCount())]:
                    
                    for i in range(parent.childCount()):
                        if parent.child(i).text(0) == part:
                            parent = parent.child(i)
                            break
                else:
                    
                    current_path = "/" + "/".join(parts[:i + 1])
                    hou_node = hou.node(current_path)

                    child = SortableItem([part, ""])
                    parent.addChild(child)
                    parent = child
                    if self.getPath(child) in state.keys():
                        child.setExpanded(state[self.getPath(child)])
                    else:
                        child.setExpanded(True)
                    
                    if not hou_node.parent().isEditable():
                        child.setForeground(0, QBrush(QColor(100, 100, 100)))
                        continue
                    # set color
                    if hou_node.type().defaultColor() != hou_node.color():
                        r, g, b = [int(c * 255) for c in hou_node.color().rgb()]
                        average_color = sum([r, g, b]) // 3
                        if average_color > 128: 
                            child.setForeground(0, QBrush(QColor(0, 0, 0)))
                        color = QColor(r, g, b)
                        for col in range(4):
                            child.setBackground(col, QBrush(color))
                    
                    # set icon
                    item_icon = hou_node.type().icon()
                    icon = QIcon(hou.qt.Icon(item_icon))
                    child.setIcon(0, icon)
                    child.setData(0, QtCore.Qt.UserRole, hou_node.type().name())


                    # set node flags
                    icon_off = hou.qt.Icon("SCENEGRAPH_active_off")
                    icon_on = hou.qt.Icon("SCENEGRAPH_active_on")

                    flags = ["isDisplayFlagSet", "isTemplateFlagSet", "isSelectableTemplateFlagSet"]
                    flag = -1

                    for i, flag_name in enumerate(flags):
                        if hasattr(hou_node, flag_name):
                            method = getattr(hou_node, flag_name)
                            if callable(method):
                                if method():
                                    icon = icon_on
                                    flag = 1
                                else:
                                    icon = icon_off
                                    flag = 0
                                child.setIcon(i+1, icon)
                        else:
                            flag = -1
                    
                        child.setData(i+1, QtCore.Qt.UserRole, flag)

        self.nodeTree.sortItems(0, self.nodeTree.header().sortIndicatorOrder())

    def getPath(self, item):
        path = []
        child = item
        while child:
            path.append(child.text(0))
            child = child.parent()
        path = "/" + "/".join(reversed(path))
        if hou.node(path):
            return path
        else:
            return None
    
    def getItem(self, path):
        parts = path.strip("/").split("/")

        def find_child(parent_item, name):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.text(0) == name:
                    return child
            return None
        for i in range(self.nodeTree.topLevelItemCount()):
            top = self.nodeTree.topLevelItem(i)
            if top.text(0) == parts[0]:
                current = top
                for part in parts[1:]:
                    current = find_child(current, part)
                    if current is None:
                        return None
                return current
        return None
    
    def selectItem(self, nodes):
        for node in nodes:
            path = node.path()
            item = self.getItem(path)
            item.setSelected(True)
    
    def deleteNode(self):
        items = self.nodeTree.selectedItems()
        deletedNodes = []
        if items:
            for item in items:
                path = self.getPath(item)
                nodes = self.nodeBundle.nodes()
                for node in nodes:
                    deletedNodes.append(node)
                    if node.path().startswith(path):
                        self.nodeBundle.removeNode(node)
        self.updateTree()

    def iterateItems(self, parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                yield child
                yield from self.iterateItems(child) 

    def searchItem(self):
        search_text = self.searchLine.text().lower()
        def filter_item(item):
            # Check if this item matches
            match = search_text in item.text(0).lower()
            # Recursively check children
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_item(child):
                    child_match = True
            # Show item if it matches or any child matches
            item.setHidden(not (match or child_match))
            return match or child_match

        root = self.nodeTree.invisibleRootItem()
        for i in range(root.childCount()):
            filter_item(root.child(i))

    def toggleColumnState(self, item, column):
        if column == 0:
            return

        current_state = item.data(column, QtCore.Qt.UserRole)
        if current_state == -1:
            return
    
        new_state = 1 - current_state
        node = hou.node(self.getPath(item))
        if column == 1:
            node.setDisplayFlag(new_state == 1)
            if hasattr(node,"setRenderFlag"):
                node.setRenderFlag(new_state == 1)
        if column == 2:
            node.setTemplateFlag(new_state == 1)
        if column == 3:
            node.setSelectableTemplateFlag(new_state == 1)

        root = self.nodeTree.invisibleRootItem()
        icon_off = hou.qt.Icon("SCENEGRAPH_active_off")
        icon_on = hou.qt.Icon("SCENEGRAPH_active_on")
        for item in self.iterateItems(root):
            # Return the item path
            path = self.getPath(item)
            hou_node = hou.node(path)
            if not hou_node.parent().isEditable():
                continue

            flags = ["isDisplayFlagSet", "isTemplateFlagSet", "isSelectableTemplateFlagSet"]
            data = -1

            for i, flag_name in enumerate(flags):
                if hasattr(hou_node, flag_name):
                    method = getattr(hou_node, flag_name)
                    if callable(method):
                        if method():
                            icon = icon_on
                            data = 1
                        else:
                            icon = icon_off
                            data = 0
                        item.setIcon(i+1, icon)
                else:
                    data = -1
                item.setData(i+1, QtCore.Qt.UserRole, data)
            
    def findNode(self, item, column):
        path = self.getPath(item)
        
        if not path or column != 0:
            return
        # get houdini network editor
        network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        current_node = hou.node(path)

        if len(path.split("/")) <=2:
            network_editor.setPwd(current_node)
        else:
            parent_node = current_node.parent()
            network_editor.setPwd(parent_node)
            network_editor.setCurrentNode(current_node)
            network_editor.frameSelection()
        
    def addNode(self,nodes):
        if self.nodeBundle.pattern():
            hou.ui.displayMessage("This is a smart bundle.")
        elif nodes:
            for node in nodes:
                
                self.nodeBundle.addNode(node)
            self.updateTree()
                        
            self.selectItem(nodes)
        else:
            return

    def addSeletcdNodes(self):
        nodes = hou.selectedNodes()
        self.addNode(nodes)
    
    def pasteNode(self):
        path_str = hou.ui.getTextFromClipboard()
        if path_str:
            paths = path_str.split(" ")
            nodes = [hou.node(path) for path in paths]
            self.addNode(nodes)

    def dropEvent(self, event):
        mimeData:QtCore.QMimeData = event.mimeData()
        if mimeData.hasText():
            paths = mimeData.text().split("\t")

            nodes = [hou.node(path) for path in paths]
            self.addNode(nodes)
        event.acceptProposedAction()

    def setSortMode(self, mode):
        self.nodeTree.sort_mode = mode  
        self.nodeTree.sortItems(0, self.nodeTree.header().sortIndicatorOrder())
        self.updateTree()

    def setColor(self, sitem):
        current_color = sitem.backgroundColor(1)
        hou_color = hou.qt.fromQColor(current_color)[0]
        color = hou.ui.selectColor(hou_color)
        items = self.nodeTree.selectedItems()
        if items and color:
            for item in items:
                node_path = self.getPath(item)
                node = hou.node(node_path)
                node.setColor(color)
        self.updateTree()   
    
    def clearColor(self):
        items = self.nodeTree.selectedItems()
        for item in items:
            node = hou.node(self.getPath(item))
            color = node.type().defaultColor()
            node.setColor(color)
        self.updateTree()

    def copyNode(self):
        items = self.nodeTree.selectedItems()
        nodes = []
        for item in items:
            nodes.append(hou.node(self.getPath(item)))
        try:
            hou.copyNodesToClipboard(tuple(nodes))
        except:
            hou.ui.displayMessage("Some nodes to copy to clipbard have different parents", buttons=('OK',),severity=hou.severityType.Warning)
    
    def copyPath(self):
        items = self.nodeTree.selectedItems()
        paths = []
        for item in items:
            path = self.getPath(item)
            paths.append(path)
        str_path = " ".join(paths)
        hou.ui.copyTextToClipboard(str_path)
    
    def openParam(self):
        items = self.nodeTree.selectedItems()
        for item in items:
            node = hou.node(self.getPath(item))
            hou.ui.showFloatingParameterEditor(node)
    
    def openNetwork(self,item):
        if item:
            node = hou.node(self.getPath(item))
            desktop = hou.ui.curDesktop()
            networkEditor = desktop.createFloatingPanel(hou.paneTabType.NetworkEditor)
            editorTab = networkEditor.paneTabs()[0]
            editorTab.setCurrentNode(node, pick_node = True)

    def copyAsObjMerge(self,rel):
        desktop = hou.ui.curDesktop()
        tab =  desktop.paneTabOfType(hou.paneTabType.NetworkEditor)
        root:hou.OpNode = tab.pwd()
        items = self.nodeTree.selectedItems()
        nodes = []
        if items:
            for i, item in enumerate(items):
                path = self.getPath(item)
                name = item.text(0)
                if "OUT" in name:
                    name = name.replace("OUT", "IN")
                else:
                    name = "IN_" + name
                objmerge = root.createNode("object_merge",node_name = name, force_valid_node_name=True)
                objmerge.setColor(hou.node(path).color())
                if rel:
                    path = objmerge.relativePathTo(hou.node(path))
                objmerge.setParms({"objpath1":path})
                objmerge.setPosition(hou.Vector2(i*3,0))
                nodes.append(objmerge)
        nodes = tuple(nodes)
        hou.copyNodesToClipboard(nodes)
        root.deleteItems(nodes)

    def configShortcut(self):
        shortcut = [
            ("Delete",self.deleteNode),
            ("Refresh",self.updateTree),
            ("Copy_Node",self.copyNode),
            ("Copy_Path",self.copyPath),
            ("Paste_Node",self.pasteNode),
            ("Copy_As_ObjMerge_Relative",lambda: self.copyAsObjMerge(True)),
            ("Copy_As_OBjMerge_Absolute",lambda: self.copyAsObjMerge(False)),
            ("Open_Parmeter",self.openParam),
            ("Close",self.closeTab)
        ]
        for name, action in shortcut:
            key_seq = self.config["shortcut"].get(name)
            if key_seq:
                shortcut = QtWidgets.QShortcut(QKeySequence(key_seq), self)
                shortcut.activated.connect(action)


widget = Bookmark()
def onCreateInterface():
    return widget

def onHipFileAfterLoad():
    widget.initBundle()