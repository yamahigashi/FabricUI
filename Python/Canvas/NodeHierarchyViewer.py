# -*- coding: utf-8 -*-

from PySide import QtCore
from PySide import QtGui


class NodeHierarchyViewerModel(QtGui.QStandardItemModel):

    def __init__(self, controller, events):
        self.__controller = controller

        QtGui.QStandardItemModel.__init__(self)

        self.events = events
        self.setHeader()
        self.initData()

    def setHeader(self):
        '''
        self.setHorizontalHeaderLabels(['Title', 'Type', 'Ports'])

        self.setHorizontalHeaderItem(0, QtGui.QStandardItem('Name'))
        self.setHorizontalHeaderItem(1, QtGui.QStandardItem('execType'))
        self.setHorizontalHeaderItem(2, QtGui.QStandardItem('nodeType'))
        '''
        return

    def getRootIndex(self):
        return self.rootIndex

    def initData(self):
        self.refresh()

    def refresh(self):
        dfgexec = self.__controller.getExec()
        p = CanvasDFGExe(dfgexec)
        self.setItem(0, 0, p)
        self.rootIndex = self.indexFromItem(p)


class NodeHierarchyViewerView(QtGui.QTreeView):

    def __init__(self, parent=None, dfgWidget=None, controller=None):
        super(NodeHierarchyViewerView, self).__init__(parent)

        self.model = NodeHierarchyViewerModel(controller, None)
        self.setModel(self.model)
        self.setAcceptDrops(False)
        self.setDragEnabled(False)

        self.__dfgWidget = dfgWidget
        self.__uicontroller = dfgWidget.getUIController()
        self.__controller = controller

        self.connect(self.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.onSelectionChanged)

    def refresh(self):
        self.model.refresh()
        self.rootIndex = self.model.getRootIndex()
        self.setRootIndex(self.rootIndex)

    def getFullPathFromId(self, id):
        def hasParent(id):
            p = id.parent()
            if (not self.rootIndex) or (not p) or (p == self.rootIndex):
                return False
            else:
                return True

        pathParts = [str(self.model.data(id))]
        while hasParent(id):
            id = id.parent()
            pathParts.append(str(self.model.data(id)))
        pathParts.reverse()

        return ".".join(pathParts)

    def onSelectionChanged(self, newSel, oldSel):

        id = newSel.indexes()[0]
        fullPath = self.getFullPathFromId(id)
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
            self.__controller.frameAllNodes()
            self.__controller.zoomCanvas(1000.0)

        graph = self.__dfgWidget.getUIGraph()
        n = graph.nodeFromPath(name)
        if not n:
            print 'not found node, not match hierarchy?'
            return

        self.__controller.clearSelection()
        self.__controller.selectNode(n, True)
        self.__controller.frameSelectedNodes()
        # self.__dfgWidget.onNodeEditRequested(n)


class NodeHierarchyViewerWidget(QtGui.QTreeWidget):

    titleDataChanged = QtCore.Signal(str, bool)

    def __init__(self, host, controller, dfgWidget, settings, canvasWindow):

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

        self.__host = host
        self.__controller = controller
        self.__dfgWidget = dfgWidget

    def __setupToolbar(self):

        optSortOrderAlphabet = QtGui.QAction("Option", self)

        toolbar = QtGui.QMenuBar()
        modeMenu = toolbar.addMenu('Mode')
        viewMenu = toolbar.addMenu('View')
        filterMenu = toolbar.addMenu('Filter')

        viewMenu.addAction(optSortOrderAlphabet)
        toolbar.addSeparator()
        return toolbar

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


class CanvasDFGExe(QtGui.QStandardItem):

    def __init__(self, dfg, parent=None, name=None):
        self.dfgexec = dfg

        if name:
            self.name = name
        else:
            self.name = self.dfgexec.getTitle()

        QtGui.QStandardItem.__init__(self, self.name)

        self.parent = parent
        self.depth = self.parent.depth + 1 if self.parent else 0

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

    def _searchSubNodes(self):

        if not self.isGraph:
            return []

        kids = []

        for i in xrange(self.dfgexec.getNodeCount()):
            name = self.dfgexec.getNodeName(i)
            sub_type = self.dfgexec.getNodeType(name)

            if _ignoreNodeType(sub_type):
                continue

            try:
                sub_exec = CanvasDFGExe(self.dfgexec.getSubExec(name), parent=self, name=name)
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
    def appendRow(self, item):
        QtGui.QStandardItem.appendRow(self, item)


def _ignoreNodeType(t):
    '''
        DFGNodeType_Inst - 実行されるモノのインスタンス
        DFGNodeType_Get - 変数取得ノード
        DFGNodeType_Set - 変数設定ノード
        DFGNodeType_Var - 変数定義ノード
        DFGNodeType_User - ユーザノード
    '''

    return t not in [0, 4]


def dump(n):

    for k in n.subNodes:

        print "	" * k.depth, ">", k.name

        for p in k.ports:
            print "	" * (k.depth + 1), p.name

        dump(k)
