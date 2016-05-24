# -*- coding: utf-8 -*-

import os
from PySide import QtCore
from PySide import QtGui


NODE_HIERARCHY_VIEWER_QSS = os.path.join(os.path.dirname(__file__), "NodeHierarchyViewer.qss")


class NodeHierarchyViewerModel(QtGui.QStandardItemModel):

    def __init__(self, controller, events):
        self.__controller = controller

        QtGui.QStandardItemModel.__init__(self)

        self.events = events
        self.setHeader()
        self.initData()

    def setHeader(self):
        self.setHorizontalHeaderLabels(['Name', 'Type', "Modified", 'Preset'])

    def getRootIndex(self):
        return self.rootIndex

    def initData(self):
        self.refresh()

    def refresh(self):
        dfgexec = self.__controller.getBinding().getExec()
        p = CanvasDFGExec(dfgexec)
        p.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setItem(0, 0, p)
        self.rootIndex = self.indexFromItem(p)


class NodeHierarchyViewerProxyModel(QtGui.QSortFilterProxyModel):

    def __init__(self):
        QtGui.QSortFilterProxyModel.__init__(self)

        self.resetFilters()

    def resetFilters(self):
        self.doOnType = [True, True, True]
        self.doOnModified = False
        self.doOnPreset = False

        self.filterStringType = ["g", "f", "v"]
        self.filterStringModified = ''
        self.filterStringPreset = ''

    def filterAcceptsRow(self, sourceRow, sourceParent):
        if sourceParent.row() == -1:
            return True

        id = self.sourceModel().index(sourceRow, 0, sourceParent)
        item = self.sourceModel().itemFromIndex(id)

        if item.hasChildren():
            return True

        if True in self.doOnType and self.filterStringType:
            id = self.sourceModel().index(sourceRow, 1, sourceParent)
            if self.sourceModel().data(id) in self.filterStringType:
                return True

        if self.doOnModified and self.filterStringModified:
            id = self.sourceModel().index(sourceRow, 2, sourceParent)
            if self.filterStringModified in self.sourceModel().data(id):
                return True

        if self.doOnPreset and self.filterStringPreset:
            id = self.sourceModel().index(sourceRow, 3, sourceParent)
            if self.filterStringPreset == self.sourceModel().data(id):
                return True

        if True in self.doOnType or self.doOnModified or self.doOnPreset:
            return False

        return True


class NodeHierarchyViewerView(QtGui.QTreeView):

    def __init__(self, parent=None, dfgWidget=None, controller=None):
        super(NodeHierarchyViewerView, self).__init__(parent)

        self.model = NodeHierarchyViewerModel(controller, None)
        self.proxy = NodeHierarchyViewerProxyModel()
        self.proxy.setSourceModel(self.model)
        self.setModel(self.proxy)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.setAcceptDrops(False)
        self.setDragEnabled(False)

        self.__dfgWidget = dfgWidget
        self.__uicontroller = dfgWidget.getUIController()
        self.__controller = controller

        self.expanded.connect(self.onExpanded)
        self.connect(self.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.onSelectionChanged)

    def refresh(self):
        self.model.refresh()
        self.rootIndex = self.model.getRootIndex()
        # self.setRootIndex(self.rootIndex)
        self.expandToDepth(0)
        self.resizeColumnToContents(0)

    def getFullPathFromId(self, id):
        def hasParent(id):
            p = id.parent()
            if (not self.rootIndex) or (not p) or (p == self.rootIndex):
                return False
            else:
                return True

        if not self.model.data(id):
            return

        pathParts = [str(self.model.data(id))]
        while hasParent(id):
            id = id.parent()
            pathParts.append(str(self.model.data(id)))
        pathParts.reverse()

        return ".".join(pathParts)

    def onSelectionChanged(self, newSel, oldSel):

        id = self.proxy.mapSelectionToSource(newSel).indexes()[0]
        fullPath = self.getFullPathFromId(id)
        if not fullPath:
            return
        name = str(self.model.data(id))

        # compare "graph's current path" with "selected node's parent path",
        # if not match the path, walk to node's parent path.
        parentPath = '.'.join(fullPath.split('.')[0:-1])
        currentDFGExec = self.__controller.getExec()
        currentDFGExecPath = self.__controller.getExecPath()

        if currentDFGExecPath != parentPath:
            # 1: go up to root
            for x in currentDFGExecPath.split('.'):
                if x == '':
                    continue
                # print 'up'
                self.__dfgWidget.onGoUpPressed()

            # 2: walk down to parentPath
            self.__controller.clearSelection()
            currentDFGExec = self.__controller.getExec()
            subdfgexec = currentDFGExec.getSubExec(parentPath)
            self.__controller.setExec(parentPath, subdfgexec)

        graph = self.__dfgWidget.getUIGraph()
        n = graph.nodeFromPath(name)
        if not n:
            print 'not found node, not match hierarchy?'
            return

        self.__controller.clearSelection()
        self.__controller.selectNode(n, True)
        self.__controller.frameSelectedNodes()
        # self.__dfgWidget.onNodeEditRequested(n)

    def onExpanded(self, id):
        self.resizeColumnToContents(0)

    def filterColumn(self, colNum):
        # self.expandToDepth(0)
        self.proxy.invalidateFilter()

    def filterType(self, num, id, checked):
        if checked:
            self.proxy.doOnType[num] = True
            if id not in self.proxy.filterStringType:
                self.proxy.filterStringType.append(id)
        else:
            self.proxy.doOnType[num] = False
            if id in self.proxy.filterStringType:
                self.proxy.filterStringType.remove(id)

        self.filterColumn(1)

    def filterTypeGraph(self, checked):
        self.filterType(0, "g", checked)

    def filterTypeFunc(self, checked):
        self.filterType(0, "f", checked)

    def filterTypeVar(self, checked):
        self.filterType(0, "v", checked)

    def filterModified(self, checked):
        if checked:
            self.proxy.doOnModified = True
            self.proxy.filterStringModified = "*"
        else:
            self.proxy.doOnModified = False
            self.proxy.filterStringModified = ""
        self.filterColumn(2)

    def filterPreset(self, checked):
        if checked:
            self.proxy.doOnPreset = True
            self.proxy.filterStringPreset = "set"
        else:
            self.proxy.doOnPreset = False
            self.proxy.filterStringPreset = ""

        self.filterColumn(3)

    def showHide(self, num, checked):
        if checked:
            self.showColumn(num)
        else:
            self.hideColumn(num)

    def showHideType(self, checked):
        self.showHide(1, checked)

    def showHideModified(self, checked):
        self.showHide(2, checked)

    def showHidePreset(self, checked):
        self.showHide(3, checked)


class NodeHierarchyViewerWidget(QtGui.QTreeWidget):

    titleDataChanged = QtCore.Signal(str, bool)

    def __init__(self, host, controller, dfgWidget, settings, canvasWindow):

        self.__host = host
        self.__controller = controller
        self.__dfgWidget = dfgWidget

        QtGui.QTreeWidget.__init__(self)
        self.view = NodeHierarchyViewerView(parent=self, dfgWidget=dfgWidget, controller=controller)
        self.setObjectName('NodeHierarchyViewerWidget')

        splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self.view)

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.__setupToolbar())
        layout.addWidget(self.view)

        self.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        self.styleSheet()

    def __setupToolbar(self):

        toolbar = QtGui.QMenuBar()
        # modeMenu = toolbar.addMenu('Mode')
        toolbar.addMenu('Mode')
        viewMenu = toolbar.addMenu('View')
        filterMenu = toolbar.addMenu('Filter')

        # solt order
        optSortOrderAlphabet = QtGui.QAction("sort order alphabet", self, checkable=True)
        optSortOrderDefault = QtGui.QAction("sort order default", self, checkable=True)

        # filter column
        optToggleColumnType = QtGui.QAction("show column type", self, checkable=True, checked=True)
        optToggleColumnType.toggled.connect(self.view.showHideType)
        optToggleColumnModified = QtGui.QAction("show column modified", self, checkable=True, checked=True)
        optToggleColumnModified.toggled.connect(self.view.showHideModified)
        optToggleColumnPreset = QtGui.QAction("show column preset", self, checkable=True, checked=True)
        optToggleColumnPreset.toggled.connect(self.view.showHidePreset)

        # filter column
        optFilterColumnTypeMenu = filterMenu.addMenu('filter by Type')
        optFilterColumnTypeGraph = QtGui.QAction("(G)raph", self, checkable=True, checked=True)
        optFilterColumnTypeGraph.toggled.connect(self.view.filterTypeGraph)
        optFilterColumnTypeFunc = QtGui.QAction("(F)unc", self, checkable=True, checked=True)
        optFilterColumnTypeFunc.toggled.connect(self.view.filterTypeFunc)
        optFilterColumnTypeVar = QtGui.QAction("(V)ariable", self, checkable=True, checked=True)
        optFilterColumnTypeVar.toggled.connect(self.view.filterTypeVar)
        optFilterColumnModified = QtGui.QAction("filter column modified", self, checkable=True, checked=False)
        optFilterColumnModified.toggled.connect(self.view.filterModified)
        optFilterColumnPreset = QtGui.QAction("filter column preset", self, checkable=True, checked=False)
        optFilterColumnPreset.toggled.connect(self.view.filterPreset)

        viewMenu.addAction(optSortOrderAlphabet)
        viewMenu.addAction(optSortOrderDefault)
        viewMenu.addSeparator()
        viewMenu.addAction(optToggleColumnType)
        viewMenu.addAction(optToggleColumnModified)
        viewMenu.addAction(optToggleColumnPreset)

        optFilterColumnTypeMenu .addAction(optFilterColumnTypeGraph)
        optFilterColumnTypeMenu .addAction(optFilterColumnTypeFunc)
        optFilterColumnTypeMenu .addAction(optFilterColumnTypeVar)
        filterMenu.addAction(optFilterColumnModified)
        filterMenu.addAction(optFilterColumnPreset)

        toolbar.addSeparator()
        return toolbar

    def styleSheet(self):
        try:
            with open(NODE_HIERARCHY_VIEWER_QSS, 'r') as f:
                self.setStyleSheet(f.read())
        except IOError as e:
            print e

    def refresh(self, *args):

        self.view.refresh()


class CanvasPortInfo(object):

    '''
        type: 0 DFGPortType_In
        type: 1 DFGPortType_IO
        type: 2 DFGPortType_Out
    '''

    def __init__(self, container, index):

        self.container = container

        self.name = container.dfgexec.getExecPortName(index)
        self.portType = container.dfgexec.getExecPortType(index)
        self.hasSrc

    def __str__(self):
        return "	" * (self.container.depth + 1) + self.name

    @property
    def isConnected(self):

        if "exec" in self.name:
            return False

        if "." not in self.path:
            # top level port
            return False

        def _inner(x, t, c=0):

            try:
                if t in [0, 1]:  # In and IO
                    return x.hasSrcPorts(self.path)
                else:
                    return x.hasDstPorts(self.path)

            except Exception as e:
                print e
                if c > 10:
                    # TODO: exception message
                    raise

                print "fallback" * c, x.dfgexec.isPreset()

                if x.parent:
                    _inner(x.parent, t, c + 1)

                else:
                    print "gave up", self.path
                    return False

        _inner(self.container, self.portType)

    @property
    def hasSrc(self):
        if self.container.parent and self.container.parent.dfgexec.isPreset:
            return False

        if self.portType == 2:
            return False

        return self.isConnected

    @property
    def path(self):
        if self.container.path:
            return "{}.{}".format(self.container.path, self.name)
        else:
            return self.name


class CanvasDFGExec(QtGui.QStandardItem):

    def __init__(self, dfg, parent=None, name=None):
        self.dfgexec = dfg

        if name:
            self.name = name
        else:
            self.name = self.dfgexec.getTitle()

        if not self.name:
            self.name = "scene_root"

        QtGui.QStandardItem.__init__(self, self.name)

        self.parent = parent
        self.depth = self.parent.depth + 1 if self.parent else 0
        self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        self.subNodes = self._searchSubNodes() or []
        self.ports = self._searchPorts() or []

    @property
    def execType(self):
        ''' return Exec type

            0: graph
            1: func
        '''
        return self.dfgexec.getType()

    @property
    def nodeType(self):
        '''
            DFGNodeType_Inst - 実行されるモノのインスタンス
            DFGNodeType_Get - 変数取得ノード
            DFGNodeType_Set - 変数設定ノード
            DFGNodeType_Var - 変数定義ノード
            DFGNodeType_User - ユーザノード
        '''

        if not self.parent:
            return 0

        return self.parent.dfgexec.getNodeType(self.name)

    @property
    def presetName(self):
        return self.dfgexec.getPresetName()

    @property
    def path(self):

        if self.parent and len(self.parent.name) > 0:
            res = "{}.{}".format(self.parent.path, self.name)
        else:
            # node in top level graph
            res = self.name

        return res

    @property
    def isGraph(self):
        return self.execType == 0

    def setQtDynamicProperty(self):
        self.setProperty("execType", self.execType)
        self.setProperty("nodeType", self.nodeType)

    def _searchSubNodes(self):

        if not self.isGraph:
            return []

        kids = []

        for i in xrange(self.dfgexec.getNodeCount()):
            name = self.dfgexec.getNodeName(i)
            sub_type = self.dfgexec.getNodeType(name)

            try:
                if isVariableNode(sub_type):
                    sub_exec = CanvasDFGVariable(nodeType=sub_type, parent=self, name=name)
                    kids.append(sub_exec)
                else:
                    sub_exec = CanvasDFGExec(self.dfgexec.getSubExec(name), parent=self, name=name)
                    kids.append(sub_exec)

            except Exception as e:
                # TODO: handle 'backDrop': not an Inst
                print e
                continue

            self.appendRow(sub_exec)

        return kids

    def _searchPorts(self):
        if _ignoreNodeType(self.nodeType):
            return []

        ports = []
        for i in xrange(self.dfgexec.getExecPortCount()):
            port = CanvasPortInfo(self, i)
            # print port
            ports.append(port)

        return ports

    # -------------------------------------------------------------------------
    # implement / override QtGui.QStandardItem
    def appendRow(self, _exec):

        if _exec.isGraph:
            execTypeLabel = 'g'  # graph
            presetName = _exec.presetName
            if _exec.dfgexec.editWouldSplitFromPreset():
                isSplitted = ""
            else:
                isSplitted = "*"

        elif _exec.execType == 1:
            execTypeLabel = 'f'  # function
            presetName = _exec.presetName
            if _exec.dfgexec.editWouldSplitFromPreset():
                isSplitted = ""
            else:
                isSplitted = "*"

        elif _exec.execType == 2:
            execTypeLabel = 'v'
            presetName = 'get'
            isSplitted = ""

        elif _exec.execType == 3:
            execTypeLabel = 'v'
            presetName = 'set'
            isSplitted = ""

        elif _exec.execType == 4:
            execTypeLabel = 'v'
            presetName = 'define'
            isSplitted = ""

        a = QtGui.QStandardItem(execTypeLabel)
        b = QtGui.QStandardItem(isSplitted)
        c = QtGui.QStandardItem(presetName)
        for x in [a, b, c]:
            x.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        QtGui.QStandardItem.appendRow(self, [_exec, a, b, c])


class CanvasDFGVariable(CanvasDFGExec):

    ''' class for DFGNodeType_Var / Get / Set.

        these node can't be called from dfgexec.getSubExec(name) '''

    def __init__(self, nodeType=None, parent=None, name=None):

        self.name = name
        self._nodeType = nodeType

        QtGui.QStandardItem.__init__(self, self.name)

        self.parent = parent
        self.depth = self.parent.depth + 1 if self.parent else 0

    @property
    def execType(self):
        offset = 1
        return self.nodeType + offset

    @property
    def nodeType(self):
        return self._nodeType


def isVariableNode(t):

    return t in [1, 2, 3]


def _ignoreNodeType(t):

    return t not in [0, 4]
