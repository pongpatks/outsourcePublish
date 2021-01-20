#import python modules
import glob, os, re, sys
sys.path.append('O:\\studioTools\\lib\\pyqt')
sys.path.append('O:\\studioTools\\maya\\python')

#import GUI
from PyQt4 import QtCore, QtGui, uic

#import pipeline modules 
from tool.utils import config, fileUtils
from tool.utils.sg import sg_utils
import shot_publish_utils1 as shotUtils

#get current module's path for accessing .ui file.
moduleFile = sys.modules[__name__].__file__
moduleDir = os.path.dirname(moduleFile)
sys.path.append(moduleDir)

############################################################
##### Global Variables                                ######
############################################################

DRIVE = 'S:'

#Since project short code in .config file is not truly unique, current solution is only hard code :-P
projectInfo = {'frd' : 'Lego_FRDCG',
                'frz' : 'Lego_Frozen',
                'cty' : 'Lego_CTYCG',
                'ppl' : 'Lego_Pipeline'}

#Andreas request publish user should be the outsource name. We dont have record of our outsource list. So, hardcode :-P
outsourceUserList = {'pfmumbai': 'PrimeFocus'}

#available's status color
colorCode = {'White' : QtGui.QColor(255, 255, 255),
            'Gray' : QtGui.QColor(240, 240, 240),
            'Yellow' : QtGui.QColor(255, 230, 40),
            'Green' : QtGui.QColor(0, 180, 55),
            'Red' : QtGui.QColor(255, 51, 0)}

#dropTable column id. as my delegate class need to access them too, let s make it global
STATUS_COL = 0
PROJ_COL = 1
EP_COL = 2
SEQ_COL = 3
SHOT_COL = 4
TASKNAME_COL = 5
VER_COL = 6
EXT_COL = 7
VERNAME_COL = 8
FRAMERANGE_COL = 9
PTPATH_COL = 10
RVPATH_COL = 11
ORIGPATH_COL = 12


def getExistingProjectDict(drive): 
    """ get list of project directories and add to comboBox """ 
    allProjDict = config.readProjectConfig()

    if os.path.exists(drive):
        projDict = dict()
        allDirs = os.listdir(drive)

        for proj in [dir for dir in allDirs if dir.startswith('Lego') or dir.startswith('TVC')]:
            projDict[proj] = allProjDict[proj]['code']

        return projDict

    return None

def getExistingEpisodeDict(drive, projName): 
    """ get list of project directories and add to comboBox """ 
    filePath = drive+'/'+projName+'/film'
    epConfigEntries = config.searchConfig(projName+':', config.episodeConfig)
    epDict = dict()

    if len(epConfigEntries)==0:
        return None

    for epEntry in epConfigEntries:
        epInfo = epEntry.split(':')
        #Searching config with just an epCode can get urself duplicate entries, so project name is needed for the query.
        if epInfo[0] == projName:
            epDict[epInfo[1]] = epInfo[3]

    return epDict

def getEpNameFromShortName(projName, epShortName):
    """Query episode from config file."""
    epConfigList = config.searchConfig(epShortName, config.episodeConfig)
        
    for epEntry in epConfigList:
        epInfo = epEntry.split(':')
        #Searching config with just an epCode can get urself duplicate entries, so project name is needed for the query.
        if epInfo[0] == projName:
            if epInfo[3] == epShortName:
                return epInfo[1]

def getFolderList(filePath, regex='*'):
    """"""
    fileList = []

    if os.path.exists(filePath):
        fileList = glob.glob(filePath+'/'+regex)
    else:
        print 'getFolderList: file path does not exists.'

    return [folder.split('\\')[-1] for folder in fileList]

def getLatestFileVersion(filePath):
    '''get the latest file name'''
    #look for that has '_v'in the middle, follow by any digit from 0-9 for 3 digits.
    re = 'v[0-9]??'

    try:
        if os.path.exists(filePath):
            fileList = glob.glob(filePath+'/' + re)
            #let's pray that python has a good sorting algorithm
            if fileList:
                return fileList[-1].split('\\')[-1]
            else:
                return ''
        else:
            print 'getLatestFileVersion: file path does not exists.'
            return ''
    except:
        print 'error checking for latest file'

def getNextVersionNumber(filePath):
    """Get latest version number from related folder directory"""
    currVerFile = getLatestFileVersion(filePath)

    if currVerFile != '':
        verString = currVerFile

        if verString.startswith('v'):
            return 'v%03d' % (int(verString[1:])+1)
    else:
        return 'v001'

def checkFileHierarchy(filePath):
    """Check if the filePath is in the correct PT hierarchy for render frames."""
    fileSplit = filePath.split('/')
    #Regular expression quick explain here -> start with q, follow by number for 4 digits, meet end of string.
    seqRegex = re.compile("q\d{4}$")
    shotRegex = re.compile("s\d{4}$")
    verRegex = re.compile("v\d{3}$")

    if len(fileSplit) != 10:
        return False   
    elif fileSplit[0]!='S:' and fileSplit[2]!='film' and fileSplit[6]!='comp' and fileSplit[7]!='render':
        return False
    elif seqRegex.match(fileSplit[4]) == None and shotRegex.match(fileSplit[5]) == None and verRegex.match(fileSplit[9]) == None:
        return False
    else:
        return True

def checkFileContent(filePath):
    """"""
    if not os.path.isdir(filePath):
        return False
    elif len(os.listdir(filePath))==0:
        return False
    else:
        return True

def generateMsgBox(text):
    """"""
    msgBox = QtGui.QMessageBox()
    msgBox.setWindowTitle("Error")
    msgBox.setText(text)
    msgBox.exec_() 


#load list of available projects as dict
availProjDict = getExistingProjectDict(DRIVE)

class CellComboBox(QtGui.QComboBox):
    def __init__(self, rowIndex, colIndex, parentWidget):
        super(CellComboBox, self).__init__()
        self.rowIndex= rowIndex
        self.colIndex = colIndex
        self.parentWidget = parentWidget

        self.dataDict = None

    def currentDataCode(self):
        try:
            code = self.dataDict[str(self.currentText())]
        except:
            print "Unexpected error:", sys.exc_info()[0]
            code = ''

        return code

    def addItemsByDict(self, dataDict):
        """"""
        self.dataDict = dataDict
        sortedDict = sorted(self.dataDict.keys())

        for key in sortedDict:
            self.addItem(key, self.dataDict[key])

class ComboBoxDelegate(QtGui.QItemDelegate):
    def __init__(self, parent):
        super(ComboBoxDelegate, self).__init__(parent)
        self.parent = parent

    def createEditor(self, parent, option, index):
        """"""
        editor = QtGui.QComboBox(parent)
        print 'create editor'
        if index.column() == PROJ_COL:
            for each in sorted(availProjDict.keys()):
                editor.addItem(each)
            return editor
        elif index.column() == EP_COL:
            print parent
            projName = str(self.parent.item(index.row(), PROJ_COL).text())
            epDict = getExistingEpisodeDict(DRIVE, projName)

            for each in sorted(epDict.keys()):
                editor.addItem(each)
            return editor
        else:
            return QtGui.QItemDelegate.createEditor(self, parent, option, index)

#Coz PySide doesn't work any more. So I try this way.
form_class, base_class = uic.loadUiType("%s/ui.ui" % moduleDir)

class MyForm(form_class, base_class):

    def __init__(self, parent=None):
        self.count = 0
        #Setup Window
        super(MyForm, self).__init__(parent)

        #Required by uic module
        self.setupUi(self)

        self.projDict = getExistingProjectDict(drive=DRIVE)
        
        self.lockItemSignal = False
        self.recursiveCount = 0
        # start functions 
        self.initUi()
        self.initSignals()

    def initUi(self):
        self.setWindowTitle('PT Frame Publish Stand Alone')
        self.resize(1280, 540)

        self.shot_tableWidget.setAcceptDrops(True)
        self.shot_tableWidget.setTextElideMode(QtCore.Qt.ElideLeft)
        #self.shot_tableWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        self.shot_tableWidget.setColumnWidth(STATUS_COL, 70)
        self.shot_tableWidget.setColumnWidth(PROJ_COL, 130)
        self.shot_tableWidget.setColumnWidth(EP_COL, 150)
        self.shot_tableWidget.setColumnWidth(SEQ_COL, 60)
        self.shot_tableWidget.setColumnWidth(SHOT_COL, 60)
        self.shot_tableWidget.setColumnWidth(TASKNAME_COL, 150)
        self.shot_tableWidget.setColumnWidth(VER_COL, 50)
        self.shot_tableWidget.setColumnWidth(EXT_COL, 50)
        self.shot_tableWidget.setColumnWidth(VERNAME_COL, 200)
        self.shot_tableWidget.setColumnWidth(FRAMERANGE_COL, 50)
        self.shot_tableWidget.setColumnWidth(PTPATH_COL, 400)
        self.shot_tableWidget.setColumnWidth(RVPATH_COL, 400)
        self.shot_tableWidget.setColumnWidth(ORIGPATH_COL, 400)

        self.shot_tableWidget.setColumnHidden(VERNAME_COL, 1)
        self.shot_tableWidget.setColumnHidden(RVPATH_COL, 1)
        self.shot_tableWidget.setColumnHidden(ORIGPATH_COL, 1)

        #install event filter on widgets that we want to intercept events.
        self.shot_tableWidget.installEventFilter(self)

        cmb_delegate = ComboBoxDelegate(self.shot_tableWidget)
        self.shot_tableWidget.setItemDelegate(cmb_delegate)

    def initSignals(self): 
        """ connect qt signal """ 
        self.shot_tableWidget.cellChanged.connect(self.editCell)
        self.input_lineEdit.returnPressed.connect(self.pressEnterRenderFrame)
        self.chk_debugMode.stateChanged.connect(self.setDebugColumnVisibility)
        self.btn_reset.clicked.connect(self.clearTable)
        self.publish_pushButton.clicked.connect(self.decidePublish)

    def setDebugColumnVisibility(self):
        """"""
        isChecked = not self.chk_debugMode.isChecked()

        self.shot_tableWidget.setColumnHidden(VERNAME_COL, isChecked)
        self.shot_tableWidget.setColumnHidden(RVPATH_COL, isChecked)
        self.shot_tableWidget.setColumnHidden(ORIGPATH_COL, isChecked)  

    def isUniqueInput(self, filePath):
        """Check if the input filePath has already been dropped on the table"""
        for row in range(0, self.shot_tableWidget.rowCount()):
            if filePath == self.shot_tableWidget.item(row, ORIGPATH_COL).text():
                return False

        return True

    def insertRowA(self, index, originalPath):
        """Insert row and determine file source type: from in-house, or outsource"""
        self.lockItemSignal = True
              
        self.shot_tableWidget.insertRow(index)
        self.fillInTable(index, ORIGPATH_COL, originalPath, isEditable=True, color=colorCode['Gray'])#Orignal file path  

        self.fillInTable(index, PROJ_COL, 'UNKNOWN', isEditable=True, color=colorCode['Red'])#project
        self.fillInTable(index, EP_COL, 'UNKNOWN', isEditable=True, color=colorCode['Red'])#episode
        self.fillInTable(index, SEQ_COL, 'UNKNOWN', isEditable=True, color=colorCode['Red'])#seq
        self.fillInTable(index, SHOT_COL, 'UNKNOWN', isEditable=True, color=colorCode['Red'])#shot
        self.fillInTable(index, TASKNAME_COL, 'UNKNOWN', isEditable=True, color=colorCode['White'])#episode

        self.fillInTable(index, VER_COL, 'v001', isEditable=True, color=colorCode['White'])#version (not the same when pub) 
        self.fillInTable(index, EXT_COL, '', isEditable=True, color=colorCode['White'])#ext
        self.fillInTable(index, VERNAME_COL, '', isEditable=True, color=colorCode['White'])#version name
        self.fillInTable(index, FRAMERANGE_COL, '', isEditable=True, color=colorCode['White'])#frame range
        self.fillInTable(index, PTPATH_COL, '', isEditable=True, color=colorCode['Gray'])#PT path
        self.fillInTable(index, RVPATH_COL, '', isEditable=True, color=colorCode['Gray'])#RV path code

        if checkFileHierarchy(originalPath):#Status
            self.fillInTable(index, STATUS_COL, 'In System', color=colorCode['Gray'])
        else:
            self.fillInTable(index, STATUS_COL, 'Outsource', color=colorCode['Yellow'])

        #self.shot_tableWidget.openPersistentEditor(self.shot_tableWidget.item(index, PROJ_COL))

        self.lockItemSignal = False

    def insertRow(self, index, status, projName, epName, seq, shot, taskName, version, ext, verName,  frameRange, PTpath, RVpathCode , originalPath):
        """"""
        self.lockItemSignal = True
        
        projCombobox = CellComboBox(index, self.projColId, self)
        epCombobox = CellComboBox(index, self.epColId, self)
        seqCombobox = CellComboBox(index, self.seqColId, self)
        shotCombobox = CellComboBox(index, self.shotColId, self)
        taskCombobox = CellComboBox(index, self.taskNameColId, self)
        taskCombobox.setEditable(True)

        self.shot_tableWidget.insertRow(index)
        self.fillInTable(index, self.verColId, version, isEditable=True, color=colorCode['Gray'])#version (not the same when pub) 
        self.fillInTable(index, self.extColId, ext, isEditable=True, color=colorCode['Gray'])#ext
        self.fillInTable(index, self.verNameColId, verName, isEditable=True, color=colorCode['Gray'])#version name
        self.fillInTable(index, self.frameRangeColId, frameRange, isEditable=True, color=colorCode['Gray'])
        self.fillInTable(index, self.ptPathColId, PTpath, isEditable=True, color=colorCode['Gray'])#PT path
        self.fillInTable(index, self.rvPathColId, RVpathCode, isEditable=True, color=colorCode['Gray'])#RV path code
        self.fillInTable(index, self.origPathColId, originalPath, isEditable=True, color=colorCode['Gray'])#Orignal file path  

        if status=='In System':
            self.fillInTable(index, self.statusColId, status, color=colorCode['Gray'])
            self.fillInTable(index, self.projColId, projName, color=colorCode['Gray'])#project
            self.fillInTable(index, self.epColId, epName, color=colorCode['Gray'])#episode
            self.fillInTable(index, self.seqColId, seq, color=colorCode['Gray'])
            self.fillInTable(index, self.shotColId, shot, color=colorCode['Gray'])
            self.fillInTable(index, self.taskNameColId, taskName, color=colorCode['Gray'])#taskname
        else:
            self.fillInTable(index, self.statusColId, status, color=colorCode['Yellow'])
            #self.fillInTable(index, self.projColId, projName, isEditable=True)#project
            #self.fillInTable(index, self.epColId, epName, isEditable=True)#episode
            #self.fillInTable(index, self.seqColId, seq, isEditable=True)
            #self.fillInTable(index, self.shotColId, shot, isEditable=True)
            #self.fillInTable(index, self.taskNameColId, taskName, isEditable=True)#taskname
            self.shot_tableWidget.setCellWidget(index, self.projColId, projCombobox)
            self.shot_tableWidget.setCellWidget(index, self.epColId, epCombobox)
            self.shot_tableWidget.setCellWidget(index, self.seqColId, seqCombobox)
            self.shot_tableWidget.setCellWidget(index, self.shotColId, shotCombobox)
            self.shot_tableWidget.setCellWidget(index, self.taskNameColId, taskCombobox)

            projCombobox.addItemsByDict(self.projDict)

            projCombobox.currentIndexChanged.connect(self.updateCellWidget)
            epCombobox.currentIndexChanged.connect(self.updateCellWidget)
            seqCombobox.currentIndexChanged.connect(self.updateCellWidget)
            shotCombobox.currentIndexChanged.connect(self.updateCellWidget)
            taskCombobox.currentIndexChanged.connect(self.updateCellWidget)

            self.lockItemSignal = False 
            projCombobox.currentIndexChanged.emit(0)

        self.lockItemSignal = False 

    def fillInTable(self, row, column, text, isEditable=False, color=''): 
        """ add item to table """
        if color=='':
            color = colorCode['White']
        item = QtGui.QTableWidgetItem()
        item.setText(text)
        item.setBackground(color)

        self.shot_tableWidget.setItem(row, column, item)
        
        if isEditable==False:
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

    def clearTable(self):  
        """ remove all rows in table """
        rowCount = self.shot_tableWidget.rowCount()

        for row in range(rowCount,0,-1) : 
            self.shot_tableWidget.removeRow(row-1)

        #self.publish_pushButton.setEnabled(True)

    def eventFilter(self, source, event):
        """Very useful func that intercept event from installed widget. Now u dont have to create custom widget class just for overriding its event anymore.
            But u have to call installEventFilter on the widget first (check initUi func.)"""
        if source is self.shot_tableWidget:
            #Move and Enter, pre-drop events which are required if u want to activate DropEvent.
            if event.type() == QtCore.QEvent.DragMove:
                event.accept()
                return True
            elif event.type() == QtCore.QEvent.DragEnter:
                event.accept()
                return True
            elif event.type() == QtCore.QEvent.Drop:
                self.filteredDropEvent(event)
                return True

        #if u expect Qt to handle event as it s normally do, u must return false.
        #True, if u have already handle event for Qt, and dont expect Qt to act anything.
        return False

    def updateCellWidget(self, selectedIndex):
        """"""
        #setup combobox first
        rowIndex = self.sender().rowIndex
        projCombobox = self.shot_tableWidget.cellWidget(rowIndex, self.projColId)
        epCombobox = self.shot_tableWidget.cellWidget(rowIndex, self.epColId)
        seqCombobox = self.shot_tableWidget.cellWidget(rowIndex, self.seqColId)
        shotCombobox = self.shot_tableWidget.cellWidget(rowIndex, self.shotColId)
        taskCombobox = self.shot_tableWidget.cellWidget(rowIndex, self.taskNameColId)

        if self.sender().colIndex == self.projColId:
            self.recursiveCount += 1
            epCombobox.clear()
            epCombobox.addItemsByDict(getExistingEpisodeDict(self.root, str(self.sender().currentText())))
        elif self.sender().colIndex == self.epColId:
            self.recursiveCount += 1
            seqCombobox.clear()
            lvlPath = '/'.join([self.root,'/',str(projCombobox.currentText()),'film',str(epCombobox.currentText())])
            seqCombobox.addItems(getFolderList(lvlPath, 'q[0-9]???'))
        elif self.sender().colIndex == self.seqColId:
            self.recursiveCount += 1
            shotCombobox.clear()
            lvlPath = '/'.join([self.root,'/',str(projCombobox.currentText()),'film',str(epCombobox.currentText()), str(seqCombobox.currentText())])
            shotCombobox.addItems(getFolderList(lvlPath, 's[0-9]???'))
        elif self.sender().colIndex == self.shotColId:
            self.recursiveCount += 1
            taskCombobox.clear()
            lvlPath = '/'.join([self.root, str(projCombobox.currentText()), 'film', str(epCombobox.currentText()), str(seqCombobox.currentText()), str(shotCombobox.currentText()), 'comp', 'render'])
            taskList = getFolderList(lvlPath)
            taskCombobox.addItems(taskList)
        else:
            self.recursiveCount += 1

        if self.recursiveCount == 1:
            print 'yo'
            self.editCell(rowIndex, self.sender().colIndex)
        
        self.recursiveCount -= 1 

    def editCell(self, row, column):
        """aaa"""

        if self.lockItemSignal==True:
            return 0
        print 'IN!:'+ str(row) + ' : '+str(column)
        status = str(self.shot_tableWidget.item(row, 0).text())

        if (column==1 or column==2 or column==3 or column==4 or column==5 or column==6) and status!='System':
            pass
            # projCombobox = self.shot_tableWidget.cellWidget(row, PROJ_COL)
            # epCombobox = self.shot_tableWidget.cellWidget(row, EP_COL)
            # seqCombobox = self.shot_tableWidget.cellWidget(row, SEQ_COL)
            # shotCombobox = self.shot_tableWidget.cellWidget(row, SHOT_COL)
            # taskCombobox = self.shot_tableWidget.cellWidget(row, TASKNAME_COL)

            # if str(projCombobox.currentText()) and str(epCombobox.currentText()) and str(seqCombobox.currentText()) and str(shotCombobox.currentText()) and str(taskCombobox.currentText()):
            #     print 'hey!'
            #     taskPath = '/'.join([self.root, str(projCombobox.currentText()), 'film', str(epCombobox.currentText()), str(seqCombobox.currentText()), str(shotCombobox.currentText()), 'comp', 'render', str(taskCombobox.currentText())])
            #     #PTpathSplit = str(self.shot_tableWidget.item(row, self.ptPathColId).text()).split('/')
            #     #PTpath = '/'.join(PTpathSplit[:8])+'/'+newTaskName
            #     newVersion = ''
            #     if column!=6:
            #         newVersion = getNextVersionNumber(taskPath)
            #         print newVersion
            #         self.shot_tableWidget.item(row, 6).setText(newVersion)
            #     else:
            #         newVersion = str(self.shot_tableWidget.item(row, 6).text())
            #         print newVersion

            #     newVerName = '_'.join([projCombobox.currentDataCode(), epCombobox.currentDataCode(), str(seqCombobox.currentText()), str(shotCombobox.currentText()), str(taskCombobox.currentText()), newVersion])
            #     #verNameSplit = str(self.shot_tableWidget.item(row, self.verNameColId).text()).split('_')
            #     #newVerName = '_'.join(verNameSplit[:4])+'_'+newTaskName+'_'+newVersion
            #     self.shot_tableWidget.item(row, self.verNameColId).setText(newVerName)

            #     PTpath = taskPath+'/'+newVersion
            #     #PTpathSplit[8] = newTaskName
            #     #PTpathSplit[9] = newVersion
            #     #newPTpath = '/'.join(PTpathSplit)
            #     #self.shot_tableWidget.item(row, self.ptPathColId).setText(newPTpath)
            #     self.shot_tableWidget.item(row, self.ptPathColId).setText(PTpath)

            #     origPath = str(self.shot_tableWidget.item(row, self.origPathColId).text())
            #     frameRange = str(self.shot_tableWidget.item(row, self.frameRangeColId).text())
            #     framePrefix = origPath.split('/')[-1].split('.')[0]

            #     ext = str(self.shot_tableWidget.item(row, self.extColId).text())
            
            #     newRVpathCode = PTpath+'/'+framePrefix+'.'+frameRange+'#.'+ext
            #     #newRVpathCode = newPTpath+'/'+str(self.shot_tableWidget.item(row, self.rvPathColId).text()).split('/')[-1]
            #     self.shot_tableWidget.item(row, self.rvPathColId).setText(newRVpathCode)

    def insertInSystemFile(self, currRow, versionPath):
        """Func that emulate tableWidget DropEvent."""

        if checkFileContent(versionPath):
            fileSplit = versionPath.split('/')
            fileList = sorted(os.listdir(versionPath))
            firstSplitUn = fileList[0].split('_')

            projName = fileSplit[1]
            epName = fileSplit[3]
            seq = fileSplit[4]
            shot = fileSplit[5]
            taskName = fileSplit[8]
            version = fileSplit[9]
            ext = fileList[0].split('.')[-1]

            #get frame range from fileName
            firstSplitDot = fileList[0].split('.')
            lastSplitDot = fileList[-1].split('.')
            firstFrame = str(int(firstSplitDot[1]))
            endFrame = str(int(lastSplitDot[1]))
            frameRange = firstFrame+'-'+endFrame
            
            verName = '_'.join(firstSplitUn[:4])+'_'+taskName+'_'+version
            PTpath = versionPath
            #this is a format for RV playback
            RVpathCode = versionPath+'/'+firstSplitDot[0]+'.'+frameRange+'#.'+firstSplitDot[-1]

            self.insertRow(currRow, 'In System', projName, epName, seq, shot, taskName, version, ext, verName, frameRange, PTpath, RVpathCode, versionPath)

            return True
        else:
            generateMsgBox('Invalid file drop. The drop must be folders which contain render frames.')
        
        return False

    def insertOutsourcefile(self, currRow, versionPath):
        """"""
        
        if checkFileContent(versionPath):
            #fileSplit = versionPath.split('/')
            fileList = sorted(os.listdir(versionPath))
            firstSplitUn = fileList[0].split('_')

            #Enough information to guess
            if len(firstSplitUn) >= 5:
                projName = projectInfo[firstSplitUn[0]]
                epName = getEpNameFromShortName(projName, firstSplitUn[1])
                seq = firstSplitUn[2]
                shot = firstSplitUn[3]
                taskName = 'FX_PASS'
                version = 'v001'
                ext = firstSplitUn[-1].split('.')[-1]

                #get frame range from fileName
                firstSplitDot = fileList[0].split('.')
                lastSplitDot = fileList[-1].split('.')
                firstFrame = str(int(firstSplitDot[1]))
                endFrame = str(int(lastSplitDot[1]))
                frameRange = firstFrame+'-'+endFrame

                verName = '_'.join(firstSplitUn[:4])+'_'+taskName+'_'+version
                PTpath = 'S:/'+projName+'/film/'+epName+'/'+seq+'/'+shot+'/comp/render/'+taskName+'/v001'
                #this is a format for RV playback
                #pathToFile = versionPath+'/'+firstSplitDot[0]+'.'+frameRange+hashTag+'.'+firstSplitDot[-1]
                RVpathCode = PTpath+'/'+firstSplitDot[0]+'.'+frameRange+'#.'+firstSplitDot[-1]

                self.insertRow(currRow, 'Outsource', projName, epName, seq, shot, taskName, version, ext, verName, frameRange, PTpath, RVpathCode, versionPath)
            #Nope, u re on ur own.
            else:
                projName = 'PROJ'
                epName = 'EP'
                seq = 'q####'
                shot = 's####'
                taskName = 'FX_PASS'
                version = 'v001'
                ext = firstSplitUn[-1].split('.')[-1]

                #get frame range from fileName
                firstSplitDot = fileList[0].split('.')
                print firstSplitDot
                lastSplitDot = fileList[-1].split('.')
                firstFrame = str(int(firstSplitDot[1]))
                endFrame = str(int(lastSplitDot[1]))
                frameRange = firstFrame+'-'+endFrame

                verName = 'UNKNOWN'
                PTpath = 'UNKNOWN'
                RVpathCode = 'UNKNOWN'

                self.insertRow(currRow, 'Outsource', projName, epName, seq, shot, taskName, version, ext, verName, frameRange, PTpath, RVpathCode, versionPath)
            
            return True
        else:
            generateMsgBox('Invalid file drop. The drop must be the version folder which contain render frames.')

        return False

    def filteredDropEvent(self, event):
        """Func that emulate tableWidget DropEvent."""
        #some kind of qt container, which was packed in the Event
        mime = event.mimeData()
        #if dropped data can be translated as path or url
        if mime.hasUrls():
            for url in mime.urls():
                currRow = self.shot_tableWidget.rowCount()
                versionPath = str(url.toLocalFile())

                if self.isUniqueInput(versionPath):
                    self.insertRowA(currRow, versionPath)

    def pressEnterRenderFrame(self):
        """"""
        versionPath = self.input_lineEdit.text().replace('\\','/')

        currRow = self.shot_tableWidget.rowCount()

        if self.isUniqueInput(versionPath):
            if checkFileHierarchy(versionPath):
                self.insertInSystemFile(currRow, versionPath)
            #Outsource files!??
            else:
                self.insertOutsourcefile(currRow, versionPath)
        else:
            generateMsgBox('Duplicated input. Please check your copied filepath.')

        self.input_lineEdit.setText('')

    def doPublish(self, i):
        """"""
        status =  str(self.shot_tableWidget.item(i, self.statusColId).text())
        if status == 'Outsource':
            try:
                src = str(self.shot_tableWidget.item(i, self.origPathColId).text())
                dst = str(self.shot_tableWidget.item(i, self.ptPathColId).text())
                fileUtils.copyMerge(src, dst)
            except:
                print "Unexpected error:", sys.exc_info()[0]

        if status != 'Published':
            shotUtils.setShotgunData(str(self.shot_tableWidget.cellWidget(i, self.projColId).currentText()), str(self.shot_tableWidget.cellWidget(i, self.epColId).currentText()), str(self.shot_tableWidget.cellWidget(i,self.seqColId).currentText()), str(self.shot_tableWidget.cellWidget(i,self.shotColId).currentText()), str(self.shot_tableWidget.cellWidget(i,self.taskNameColId).currentText()), 'aprv', str(self.shot_tableWidget.item(i,self.verNameColId).text()), str(self.shot_tableWidget.item(i,self.rvPathColId).text()), str(self.shot_tableWidget.item(i,self.origPathColId).text()), outsourceUserList['pfmumbai'])
        
            statusItem = self.shot_tableWidget.item(i,0)
            statusItem.setText('Published')
            statusItem.setBackground(colorCode['Green'])

        #self.publish_pushButton.setEnabled(False)

    def decidePublish(self):
        """bla bla"""
        # if self.all_checkBox.isChecked():
        #     for i in range(self.shot_tableWidget.rowCount()):
        #         self.doPublish(i)
        # else:
        #     #selectionModel() will return QModelIndex. With this obj, u can dynamically get row and column from selectedItem with ease.
        #     selModel = self.shot_tableWidget.selectionModel()
        #     modelIndexList = selModel.selectedRows(0)

        #     for each in modelIndexList:
        #         i = self.shot_tableWidget.itemFromIndex(each).row()

        #         self.doPublish(i)
        print str(self.shot_tableWidget.item(0,1).text())


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()
    sys.exit(app.exec_())