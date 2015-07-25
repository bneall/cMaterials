## Make Material
from PySide import QtGui,QtCore
import mari

CSS_tree = "\\QTreeWidget { background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #404040, stop: 1 transparent); alternate-background-color: rgba(255, 255, 255, 3%);} \\"
CSS_colorButton = "background-color: rgba(%s, %s, %s, %s); border: 1px solid; border-radius: 3px;"
solidBlack = [0.0, 0.0, 0.0, 1.0]
solidWhite = [1.0, 1.0, 1.0, 1.0]
iconpath = mari.resources.path(mari.resources.ICONS)

#=================================================================
def sortMaterialLayers(layerOrderFromUI):
    '''Sorts material layers based on material UI order
    '''
    mariGeo = mari.current.geo()

    for shader in mariGeo.shaderList():
        if shader.hasMetadata("isMaterialShader"):
            mariShader = shader

    for input_item in mariShader.inputList():
        inputChannel = input_item[1]
        inputName = input_item[0]
        if inputChannel:
            for layer in inputChannel.layerList():
                if layer.hasMetadata("materialGroup"):
                    groupStack = layer.groupStack()
                    groupStack.removeLayers(groupStack.layerList())

            for layerName in layerOrderFromUI[::-1]:
                channelName = "%s_m%s" % (layerName, inputName)
                layerChannel = mariGeo.channel(channelName)
                link_layer = groupStack.createChannelLayer(channelName, layerChannel)
                link_layer.setMetadata("material", layerName)

#=================================================================
def getMaterialOrder():
    '''Finds the material layer order from the first primary input channel found
    '''
    mariGeo = mari.current.geo()

    layerOrderList = []
    for channel in mariGeo.channelList():
        if channel.hasMetadata("isMaterialChannel"):
            for layer in channel.layerList():
                if layer.hasMetadata("materialGroup"):
                    groupStack = layer.groupStack()
                    for layer in groupStack.layerList():
                        if layer.hasMetadata("material"):
                            if layer.metadata("material") not in layerOrderList:
                                layerOrderList.append(layer.metadata("material"))

    return layerOrderList

#=================================================================
def getElementRepBaseLayer(materialChannel, elementName):

    for layer in materialChannel.layerList():
        if layer.hasMetadata("elementGroup"):
            if layer.metadata("elementGroup") == elementName:
                groupStack = layer.groupStack()
                for layer in groupStack.layerList():
                    if layer.hasMetadata("baseColor"):
                        return layer

#=================================================================
def getMaterialElements(materialName):

    mariGeo = mari.current.geo()

    elementChannels = {}
    for channel in mariGeo.channelList():
        if channel.hasMetadata("element"):
            if channel.hasMetadata("material"):
                if channel.metadata("material") == materialName:
                    elementName = channel.metadata("element")
                    elementChannels[elementName]=channel

    return elementChannels

#=================================================================
def getBaseColorLayer(materialChannel):
    '''Get base color layer
    '''
    for layer in materialChannel.layerList():
        if layer.hasMetadata("baseColor"):
            return layer

#=================================================================
def getAllMaterials():
    '''Get list of materials on the geo
    '''
    mariGeo = mari.current.geo()

    materials = set()
    for channel in mariGeo.channelList():
        if channel.hasMetadata("material"):
            materials.add(channel.metadata("material"))

    return materials

#=================================================================
def getMaterialInputs(materialName):
    '''Get material input channels
    '''
    mariGeo = mari.current.geo()

    materialInputList = {}
    for channel in mariGeo.channelList():
        if channel.hasMetadata("material") and channel.metadata("material") == materialName:
            if not channel.hasMetadata("element"):
                inputName = channel.metadata("materialType")
                inputChannel = channel
                materialInputList[inputName]=inputChannel

    return materialInputList

#=================================================================
def getShaderInputs():
    '''Get active shader inputs
    '''
    mariGeo = mari.current.geo()

    shaderInputList = {}
    for shader in mariGeo.shaderList():
        if shader.hasMetadata("isMaterialShader"):
            for sinput in shader.inputList():
                inputName = sinput[0]
                inputChannel = sinput[1]
                if inputChannel:
                    shaderInputList[inputName]=inputChannel

    return shaderInputList

#=================================================================
def createColorLayer(layerName, layerStack, color):
    '''Create Color Procedural Layer
    '''
    r, g, b, a = color
    layer = layerStack.createProceduralLayer("%s_baseColor" % layerName, "Basic/Color")
    layer.setProceduralParameter("Color", mari.Color(r,g,b,a))
    layer.setMetadata("baseColor", True)
    layer.setMetadataFlags("baseColor", 16)
    layer.setLocked(True)

    return layer

#=================================================================
def setChannelMetadata(channel, materialName, channelType, element=False, mask=False):
    '''Set Channel Metadata
    '''
    channel.setMetadata("material", materialName)
    channel.setMetadataFlags("material", 1 | 16)
    channel.setMetadata("materialType", channelType)
    channel.setMetadataFlags("materialType", 1 | 16)

    if element:
        channel.setMetadata("element", element)
        channel.setMetadataFlags("element", 1 | 16)

    if mask:
        channel.setMetadata("mask", mask)
        channel.setMetadataFlags("mask", 1 | 16)

#=================================================================
def createMaskChannel(materialName, channelType, element=False):
    '''Create Material Mask Channel
    '''

    mariGeo = mari.current.geo()

    maskChannelName = "%s_%s" % (materialName, channelType)
    newMaskChannel = mariGeo.createChannel(maskChannelName, 4096, 4096, 8)

    #Metadata
    setChannelMetadata(newMaskChannel, materialName, channelType, element, mask=True)

    #Base Layer
    createColorLayer(materialName, newMaskChannel, solidBlack)

    return newMaskChannel

#=================================================================
def createMaterialChannel(maskChannel, materialName, inputName, color):
    '''Create Material Channel
    '''
    mariGeo = mari.current.geo()

    customName = "m%s" % inputName
    materialChannelName = "%s_%s" % (materialName, customName)
    baseChannel = mariGeo.channel(customName)
    newChannel = mariGeo.createChannel(materialChannelName, 4096, 4096, 8)

    #Metadata
    setChannelMetadata(newChannel, materialName, inputName)

    #Base Layer
    createColorLayer(materialName, newChannel, color)

    #Create and link mask
    if baseChannel.findLayer("mGroup"):
        groupStack = baseChannel.layer("mGroup").groupStack()
    else:
        newGroup = baseChannel.createGroupLayer("mGroup")
        newGroup.setMetadata("materialGroup", True)
        newGroup.setMetadataFlags("materialGroup", 16)
        groupStack = newGroup.groupStack()

    channelName = "%s_m%s" % (materialName, inputName)
    linkLayer = groupStack.createChannelLayer(channelName, newChannel)
    linkLayer.setMetadata("material", materialName)
    linkLayer.setMetadataFlags("material", 16)
    maskStack = linkLayer.makeMaskStack()
    maskStack.removeLayers(maskStack.layerList())

    maskStack.createChannelLayer(maskChannel.name(), maskChannel)

    return newChannel

#=================================================================
def createElementRep(materialChannel, elementMaskChannel, color):
    '''Create element rep within a material channel
    '''
    mariGeo = mari.current.geo()

    #Element Group
    elementGroup = materialChannel.createGroupLayer(elementMaskChannel.name())
    elementGroupStack = elementGroup.groupStack()

    #Set metedata
    elementBaseName = elementMaskChannel.name().split("_")[-1]
    elementGroup.setMetadata("elementGroup", elementBaseName)
    elementGroup.setMetadataFlags("elementGroup", 16)

    #Base Color
    createColorLayer(elementMaskChannel.name(), elementGroupStack, color)

    #Mask stack and link
    elementMaskStack = elementGroup.makeMaskStack()
    elementMaskStack.removeLayers(elementMaskStack.layerList())
    elementMaskStack.createChannelLayer(elementMaskChannel.name(), elementMaskChannel)

#=================================================================
def removeSingleMaterial(materialName, metadataOnly=False):
    '''Find and remove material channels
    '''
    mariGeo = mari.current.geo()

    for channel in mariGeo.channelList():
        if channel.hasMetadata("material"):
            if channel.metadata("material") == materialName:
                if metadataOnly:
                    try:
                        for mdata in ["material", "materialType", "mask", "element"]:
                            channel.removeMetadata(mdata)
                    except:
                        pass
                else:
                    mariGeo.removeChannel(channel, 1)

#=================================================================
def removeSingleElement(materialName, elementName):

    mariGeo = mari.current.geo()

    for channel in mariGeo.channelList():
        if channel.hasMetadata("material"):
            if channel.metadata("material") == materialName:
                if not channel.hasMetadata("mask"):
                    for layer in channel.layerList():
                        if layer.hasMetadata("elementGroup"):
                            if layer.metadata("elementGroup") == elementName:
                                channel.removeLayers([layer])
                if channel.hasMetadata("element"):
                    if channel.metadata("element") == elementName:
                        mariGeo.removeChannel(channel)

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class ChooseShader(QtGui.QDialog):
    def __init__(self, parent):
        super(ChooseShader, self).__init__(parent)

        self.setParent(parent)
        self.setWindowTitle("Create Material Shader")

        #Layouts
        mainLayout = QtGui.QVBoxLayout()
        self.setLayout(mainLayout)

        #Widgets
        self.diffshaderCombo = QtGui.QComboBox()
        self.specshaderCombo = QtGui.QComboBox()
        self.createShaderBtn = QtGui.QPushButton("Create Shader")

        #Populate Layouts
        mainLayout.addWidget(self.diffshaderCombo)
        mainLayout.addWidget(self.specshaderCombo)
        mainLayout.addWidget(self.createShaderBtn)

        #Connections
        self.createShaderBtn.clicked.connect(self.createShader)

        self.getShaders()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def getShaders(self):
        mariGeo = mari.current.geo()
        diffshaders = mariGeo.shaderDiffuseTypeList()
        specshaders = mariGeo.shaderSpecularTypeList()
        self.diffshaderCombo.addItems(diffshaders)
        self.specshaderCombo.addItems(specshaders)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def createShader(self):
        '''Create a Material shader
        '''
        mariGeo = mari.current.geo()
        diffshader = self.diffshaderCombo.currentText()
        specshader = self.specshaderCombo.currentText()

        #Create Shader
        shader = mariGeo.createShader("mBeauty", diffshader, specshader)
        shader.setInput("DiffuseColor", None)
        mariGeo.setCurrentShader(shader)

        #Tag Shader
        shader.setMetadata("isMaterialShader", True)
        shader.setMetadataFlags("isMaterialShader", 16)

        self.close()

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class CreateChannels(QtGui.QDialog):
    channelsCreated = QtCore.Signal()
    def __init__(self, parent):
        super(CreateChannels, self).__init__(parent)

        self.setParent(parent)

        #Layouts
        mainLayout = QtGui.QVBoxLayout()
        self.setLayout(mainLayout)

        #Widgets
        self.inputList = QtGui.QListWidget()
        createChannelsBtn = QtGui.QPushButton("Create Channels")

        #Populate Layouts
        mainLayout.addWidget(self.inputList)
        mainLayout.addWidget(createChannelsBtn)

        #Connections
        createChannelsBtn.clicked.connect(self.createChannels)

        self.populateShaderInputs()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def getMaterialShader(self):
        '''Get material shader
        '''

        mariGeo = mari.current.geo()
        for shader in mariGeo.shaderList():
            if shader.hasMetadata("isPrimaryInput"):
                return mariGeo, shader

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def populateShaderInputs(self):
        '''Detect available shader inputs
        '''
        mariGeo, mariShader = self.getMaterialShader()

        self.inputList.clear()
        for input_item in mariShader.inputList():
            inputChannel = input_item[1]
            inputName = input_item[0]
            if not inputChannel:
                inputItem = QtGui.QListWidgetItem(inputName)
                inputItem.setCheckState(QtCore.Qt.Unchecked)
                self.inputList.addItem(inputItem)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def createChannels(self):
        '''Create channels and connect them to the shader
        '''

        mariGeo, mariShader = self.getMaterialShader()

        #Build list of selected inputs
        input_list = []
        for index in range(self.inputList.count()):
            item = self.inputList.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                input_list.append(item.text())

        #Build channels
        for input_name in input_list:
            custom_name = "m%s" % input_name
            newChannel = mariGeo.createChannel(custom_name, 4096, 4096, 8)
            newChannel.setMetadata("isPrimaryInput", True)
            newChannel.setMetadataFlags("isPrimaryInput", 1 | 16)
            baseLyr = newChannel.createProceduralLayer("Base", "Basic/Color")
            baseLyr.setProceduralParameter("Color", mari.Color(0.0, 0.0, 0.0))
            groupLyr = newChannel.createGroupLayer("mGroup")
            groupLyr.setMetadata("materialGroup", True)
            groupLyr.setMetadataFlags("materialGroup", 16)
            mariShader.setInput(input_name, newChannel)

        self.close()
        self.channelsCreated.emit()

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class CreateMaterial(QtGui.QDialog):
    materialCreated = QtCore.Signal(str)
    def __init__(self, parent, mode, material=None):
        super(CreateMaterial, self).__init__(parent)

        self.setParent(parent)

        self.mode = mode
        self.material = material

        #Layouts
        mainLayout = QtGui.QVBoxLayout()
        nameLayout = QtGui.QHBoxLayout()
        buttonLayout = QtGui.QHBoxLayout()
        self.setLayout(mainLayout)

        #Widgets
        materialNameLabel = QtGui.QLabel("Name:")
        self.name = QtGui.QLineEdit("New Material")
        self.inputTree = QtGui.QTreeWidget()
        cancelBtn = QtGui.QPushButton("Cancel")
        createBtn = QtGui.QPushButton("Create All")
        #--- tree settings
        self.inputTree.setColumnCount(3)
        self.inputTree.setHeaderHidden(True)
        self.inputTree.setRootIsDecorated(False)
        self.inputTree.setSelectionMode(self.inputTree.NoSelection)
        self.inputTree.setFocusPolicy(QtCore.Qt.NoFocus)
        self.inputTree.setAlternatingRowColors(True)
        self.inputTree.setStyleSheet(CSS_tree)

        #Populate Layouts
        buttonLayout.addWidget(cancelBtn)
        buttonLayout.addWidget(createBtn)
        nameLayout.addWidget(materialNameLabel)
        nameLayout.addWidget(self.name)
        mainLayout.addLayout(nameLayout)
        mainLayout.addWidget(self.inputTree)
        mainLayout.addLayout(buttonLayout)

        #Connections
        cancelBtn.clicked.connect(self.reject)
        createBtn.clicked.connect(self.buildAll)

        self.getInputs()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def getInputs(self):
        '''Create new items from active shader inputs
        '''
        if self.mode == "material":
            inputChannels = getShaderInputs()

        if self.mode == "element":
            inputChannels = getMaterialInputs(self.material)

        for inputName, inputChannel in inputChannels.iteritems():
            newItem = QtGui.QTreeWidgetItem()
            newItem.setText(0, inputName)
            newItem.setData(0, 32, inputChannel)
            newItem.setData(2, 32, solidWhite)
            self.inputTree.addTopLevelItem(newItem)
            self.makeColorButton(newItem)

        self.inputTree.resizeColumnToContents(0)
        self.inputTree.setColumnWidth(1, 85)
        self.inputTree.setColumnWidth(2, 45)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def makeColorButton(self, item):
        '''Makes Color Picker Button
        '''
        def getColor():
            color = mari.colors.pick(mari.colors.foreground())
            byteRGB = QtGui.QColor.fromRgbF(color.r(), color.g(), color.b(), a=color.a())
            colorButton.setStyleSheet(CSS_colorButton % (byteRGB.red(), byteRGB.green(), byteRGB.blue(), byteRGB.alpha()))
            item.setData(2, 32, [color.r(), color.g(), color.b(), color.a()])

        colorButton = QtGui.QPushButton(self)
        colorButton.setStyleSheet(CSS_colorButton % (255, 255, 255, 255))
        colorButton.setToolTip("Choose Base Color")
        colorButton.clicked.connect(getColor)

        colorWidget = QtGui.QWidget(self.inputTree)
        colorLayout = QtGui.QHBoxLayout(colorWidget)
        colorLayout.setContentsMargins(1, 1, 1, 1)
        colorLayout.addWidget(colorButton)
        colorWidget.setLayout(colorLayout)

        self.inputTree.setItemWidget(item, 2, colorWidget)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def buildAll(self):
        '''Make material from specified settings
        '''
        if self.mode == "material":
            materialName = self.name.text()
            maskChannel = createMaskChannel(materialName, "Mask")

        if self.mode == "element":
            elementName = self.name.text()
            materialName = self.material
            maskChannel = createMaskChannel(materialName, elementName, element=elementName)

        for index in range(self.inputTree.topLevelItemCount()):
            inputItem = self.inputTree.topLevelItem(index)
            inputName = inputItem.text(0)
            targetChannel = inputItem.data(0, 32)
            color = inputItem.data(2, 32)

            if self.mode == "material":
                createMaterialChannel(maskChannel, materialName, inputName, color)

            if self.mode == "element":
                if inputName != "Mask":
                    createElementRep(targetChannel, maskChannel, color)

        self.close()
        self.materialCreated.emit(materialName)

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class InputWidget(QtGui.QWidget):
    def __init__(self, parent, name, colorLayer, channel):
        super(InputWidget, self).__init__()

        self.setParent(parent)

        self.channel = channel
        self.colorLayer = colorLayer

        #Widgets
        self.colorButton = QtGui.QPushButton()
        self.selectButton = QtGui.QPushButton("Select")
        self.cacheButton = QtGui.QPushButton("Cache")
        self.cacheButton.setCheckable(True)

        #Check if already cached
        if self.channel.layerList()[0].isCachedUpToHere():
            self.cacheButton.setChecked(True)

        #Connections
        self.colorButton.clicked.connect(self.setColor)
        self.selectButton.clicked.connect(self.selectChannel)
        self.cacheButton.toggled.connect(self.cacheControl)

        #Init
        currentColor = self.colorLayer.getProceduralParameter("Color")
        byteRGB = QtGui.QColor.fromRgbF(currentColor.r(), currentColor.g(), currentColor.b(), a=currentColor.a())
        self.colorButton.setStyleSheet(CSS_colorButton % (byteRGB.red(), byteRGB.green(), byteRGB.blue(), byteRGB.alpha()))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setColor(self):
        color = mari.colors.pick(mari.colors.foreground())
        byteRGB = QtGui.QColor.fromRgbF(color.r(), color.g(), color.b(), a=color.a())
        self.colorButton.setStyleSheet(CSS_colorButton % (byteRGB.red(), byteRGB.green(), byteRGB.blue(), byteRGB.alpha()))
        self.colorLayer.setLocked(False)
        self.colorLayer.setProceduralParameter("Color", color)
        self.colorLayer.setLocked(True)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def selectChannel(self):
        mari.geo.setCurrent(self.channel.geoEntity())
        self.channel.makeCurrent()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def cacheControl(self):
        topLayer = self.channel.layerList()[0]
        if self.cacheButton.isChecked():
            topLayer.cacheUpToHere()
        else:
            topLayer.uncacheUpToHere()

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class MaterialManager(QtGui.QDialog):
    materialCreated = QtCore.Signal()
    def __init__(self):
        super(MaterialManager, self).__init__()

        self.setMinimumSize(400, 600)

        #Layouts
        mainLayout = QtGui.QVBoxLayout()
        inputBtnLayout = QtGui.QHBoxLayout()
        materialBtnLayout = QtGui.QHBoxLayout()
        elementBtnLayout = QtGui.QHBoxLayout()
        self.setLayout(mainLayout)

        createShaderBtn = QtGui.QPushButton("Create Shader")
        inputBtnLayout.addWidget(createShaderBtn)
        createInputChanBtn = QtGui.QPushButton("Create Inputs")
        inputBtnLayout.addWidget(createInputChanBtn)
        mainLayout.addLayout(inputBtnLayout)

        inputBtnLayout.addWidget(createShaderBtn)
        moveItemUpBtn = QtGui.QPushButton("up")
        materialBtnLayout.addWidget(moveItemUpBtn)
        moveItemDownBtn = QtGui.QPushButton("down")
        materialBtnLayout.addWidget(moveItemDownBtn)
        removeMaterialBtn = QtGui.QPushButton("Remove Material")
        materialBtnLayout.addWidget(removeMaterialBtn)
        addMaterialBtn = QtGui.QPushButton("New Material")
        materialBtnLayout.addWidget(addMaterialBtn)

        removeElementBtn = QtGui.QPushButton("Remove Element")
        elementBtnLayout.addWidget(removeElementBtn)
        addElementBtn = QtGui.QPushButton("New Element")
        elementBtnLayout.addWidget(addElementBtn)

        self.materialTree = QtGui.QTreeWidget()
        mainLayout.addWidget(self.materialTree)
        mainLayout.addLayout(materialBtnLayout)
        #--- tree settings
        self.materialTree.setHeaderHidden(True)
        self.materialTree.setRootIsDecorated(False)
        self.materialTree.setFocusPolicy(QtCore.Qt.NoFocus)
        self.materialTree.setAlternatingRowColors(True)
        self.materialTree.setStyleSheet(CSS_tree)

        self.settingsTree = QtGui.QTreeWidget()
        mainLayout.addWidget(self.settingsTree)
        mainLayout.addLayout(elementBtnLayout)
        #--- tree settings
        self.settingsTree.setColumnCount(4)
        self.settingsTree.setHeaderHidden(True)
        self.settingsTree.setRootIsDecorated(False)
        self.settingsTree.setFocusPolicy(QtCore.Qt.NoFocus)
        self.settingsTree.setAlternatingRowColors(True)
        self.settingsTree.setStyleSheet(CSS_tree)

        self.buildTreeFromChannels()
        self.sortMaterialListItems()

        self.materialTree.itemClicked.connect(self.buildMaterialSettings)
        addMaterialBtn.clicked.connect(self.addMaterial)
        addElementBtn.clicked.connect(self.addElement)
        removeMaterialBtn.clicked.connect(self.removeMaterial)
        removeElementBtn.clicked.connect(self.removeElement)
        moveItemUpBtn.clicked.connect(self.moveItemUp)
        moveItemDownBtn.clicked.connect(self.moveItemDown)
        createShaderBtn.clicked.connect(self.createMaterialShader)
        createInputChanBtn.clicked.connect(self.createInputChannels)

    def createMaterialShader(self):
        diag = ChooseShader(self)
        diag.show()

    def createInputChannels(self):
        diag = CreateChannels(self)
        diag.show()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def moveItemDown(self):
        '''Move item up one row
        '''

        takeItem = self.materialTree.currentItem()
        takeIndex = self.materialTree.indexOfTopLevelItem(takeItem)
        takeItem = self.materialTree.takeTopLevelItem(takeIndex)
        self.materialTree.insertTopLevelItem(takeIndex + 1, takeItem)
        self.materialTree.clearSelection()
        takeItem.setSelected(True)
        self.materialTree.setCurrentItem(takeItem)
        layerOrderFromUI = self.getLayerOrder()
        sortMaterialLayers(layerOrderFromUI)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def moveItemUp(self):
        '''Move item up one row
        '''

        takeItem = self.materialTree.currentItem()
        takeIndex = self.materialTree.indexOfTopLevelItem(takeItem)
        takeItem = self.materialTree.takeTopLevelItem(takeIndex)
        self.materialTree.insertTopLevelItem(takeIndex - 1, takeItem)
        self.materialTree.clearSelection()
        takeItem.setSelected(True)
        self.materialTree.setCurrentItem(takeItem)
        layerOrderFromUI = self.getLayerOrder()
        sortMaterialLayers(layerOrderFromUI)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def getLayerOrder(self):
        layerOrderFromUI = []
        it = QtGui.QTreeWidgetItemIterator(self.materialTree)
        while it.value():
            item = it.value()
            itemName = item.text(0)
            if not item.parent():
                layerOrderFromUI.append(itemName)
            it += 1
        return layerOrderFromUI

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def sortMaterialListItems(self):
        '''Sorts materials in UI based on material layers order in the channels
        '''
        orderList = getMaterialOrder()

        if len(orderList) != len(getAllMaterials()):
            return

        self.materialTree.clear()

        for name in orderList:
            newItem = QtGui.QTreeWidgetItem()
            newItem.setText(0, name)
            newItem.setIcon(0, QtGui.QPixmap("%s/lighting_full.png" % iconpath))
            self.materialTree.addTopLevelItem(newItem)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def buildTreeFromChannels(self):

        self.materialTree.clear()

        materials = getAllMaterials()
        for material in materials:
            newItem = QtGui.QTreeWidgetItem()
            newItem.setText(0, material)
            newItem.setIcon(0, QtGui.QPixmap("%s/lighting_full.png" % iconpath))
            self.materialTree.addTopLevelItem(newItem)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def buildItem(self, parent, name, inputName, inputChannel, baseColorLayer, cacheON=True):
            newItem = QtGui.QTreeWidgetItem()
            newItem.setFlags(QtCore.Qt.ItemIsEnabled)
            newItem.setText(0, name)
            newItem.setIcon(0, QtGui.QPixmap("%s/MoveRight.png" % iconpath))
            parent.addChild(newItem)

            #Set control widget
            controlWidget = InputWidget(self.settingsTree, inputName, baseColorLayer, inputChannel)

            #Color widget
            colorWidget = QtGui.QWidget(self.settingsTree)
            colorLayout = QtGui.QHBoxLayout(colorWidget)
            colorLayout.setContentsMargins(1, 1, 1, 1)
            colorLayout.addWidget(controlWidget.colorButton)
            colorWidget.setLayout(colorLayout)

            self.settingsTree.setItemWidget(newItem, 1, colorWidget)
            self.settingsTree.setItemWidget(newItem, 2, controlWidget.selectButton)
            if cacheON:
                self.settingsTree.setItemWidget(newItem, 3, controlWidget.cacheButton)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def buildMaterialSettings(self):

        self.settingsTree.clear()

        material = self.materialTree.currentItem().text(0)
        materialInputs = getMaterialInputs(material)
        elements = getMaterialElements(material)

        #Base
        inputTopItem = QtGui.QTreeWidgetItem()
        inputTopItem.setText(0, "[%s] Base" % material)
        inputTopItem.setIcon(0, QtGui.QPixmap("%s/Home.png" % iconpath))
        inputTopItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.settingsTree.addTopLevelItem(inputTopItem)

        for inputName, inputChannel in materialInputs.iteritems():
            baseColorLayer = getBaseColorLayer(inputChannel)
            self.buildItem(inputTopItem, inputName, inputName, inputChannel, baseColorLayer)

        #Elements
        for elementName, elementChannel in elements.iteritems():
            elementTopItem = QtGui.QTreeWidgetItem()
            elementTopItem.setText(0, elementName)
            elementTopItem.setIcon(0, QtGui.QPixmap("%s/Materials.png" % iconpath))
            self.settingsTree.addTopLevelItem(elementTopItem)

            for inputName, inputChannel in materialInputs.iteritems():
                if inputName == "Mask":
                    baseColorLayer = getBaseColorLayer(elementChannel)
                    self.buildItem(elementTopItem, inputName, inputName, elementChannel, baseColorLayer)
                else:
                    baseColorLayer = getElementRepBaseLayer(inputChannel, elementName)
                    self.buildItem(elementTopItem, inputName, inputName, inputChannel, baseColorLayer, cacheON=False)

        self.settingsTree.expandAll()
        self.settingsTree.resizeColumnToContents(0)
        self.settingsTree.setColumnWidth(0, self.settingsTree.columnWidth(0)+30)
        self.settingsTree.setColumnWidth(1, 45)
        self.settingsTree.setColumnWidth(2, 45)
        self.settingsTree.setColumnWidth(3, 45)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def refresh(self, material):
        self.buildTreeFromChannels()
        for index in range(self.materialTree.topLevelItemCount()):
            item = self.materialTree.topLevelItem(index)
            if item.text(0) == material:
                item.setSelected(True)
                self.materialTree.setCurrentItem(item)
                self.buildMaterialSettings()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def addMaterial(self):
        diag = CreateMaterial(self, "material")
        diag.show()
        diag.materialCreated.connect(self.refresh)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def addElement(self):
        currentMaterial = self.materialTree.currentItem().text(0)
        diag = CreateMaterial(self, "element", material=currentMaterial)
        diag.show()
        diag.materialCreated.connect(self.buildMaterialSettings)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def removeMaterial(self):
        currentMaterial = self.materialTree.currentItem().text(0)        
        removeSingleMaterial(currentMaterial)
        self.buildTreeFromChannels()
        self.settingsTree.clear()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def removeElement(self):
        currentMaterial = self.materialTree.currentItem().text(0)
        currentElement = self.settingsTree.currentItem().text(0)
        removeSingleElement(currentMaterial, currentElement)
        self.buildMaterialSettings()

diag = MaterialManager()
diag.show()
