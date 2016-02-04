## Make Material
from PySide import QtGui, QtCore
import mari
import os

CSS_tree = "\\QTreeWidget { background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #404040, stop: 1 transparent); alternate-background-color: rgba(255, 255, 255, 3%);} \\"
CSS_colorButton = "background-color: rgba(%s, %s, %s, %s); border: 1px solid; border-radius: 3px;"
solidBlack = [0.0, 0.0, 0.0, 1.0]
solidWhite = [1.0, 1.0, 1.0, 1.0]
iconpath = mari.resources.path(mari.resources.ICONS)

# CHANGELIST
# - CURRENTLY THIS IS 2.6 CODE --- not tested with mari 3
# - It is now a Palette 'Material manager' (disabled for debugging)
# - Converted most textbuttons to Icons for Space, added Tooltips
# - You can now toggle the visibility of a complete material via the dialog
# - You can now rename a Material
# - You can now duplicate a Material (requires MARI Extension Pack 'Duplcate Channel' Action)
# - The Material manager will now refresh itself when you switch objects
# - When the Material Groups are completely rebuild the current Layer Selection at the end is restored 
# - You can now make changes (Blendmode, Opacity, Visibility etc.) to Channel Material Layers in the Primary Input Groups and they will be restored
# - The Material Order wasn't correct when launching the tool after a project was reopened due to a missing 'break' code segment
# - Fixed Bug when reordering Materials: Masks disappeared
# - Sometimes the Material Order was wrong in the UI after creating a new Material, fixed by calling a sorting from the refresh() method
# - current channel selection is now restored after adding a new material or element
# - Fixed a bug where moving the first material up or the last material down would remove it from the interface.
# - Catching error when exectuting moveUp or moveDown when nothing is selected (same for visibility and rename)
# - Added Error Dialog when trying to add (or rename) a Material with a Name that already exists


# TO DO:

# - Check for duplicate Elements when renaming
# - REJECTED: Set first Material to Mask White
# - Add Rename for Elements
# - Add up down to Elements
# - Add Visibility to Elements
# - Throw warning when: Adding Element that exists
# - Throw Warning and prevent: Moving Element up or down if it is the first or last item
# - Add Session Import to setup Scene
#-  Set AISTandard
# - Add Light Chooser and Light Res
# - Add Light Rotation and Scene Playback
# - Adopt Naming Convention for Export Shaders
# - Add Primary Input option to exporter.
# - Add Float Values to all Elements Materials
# - Export Material
# - REJECTED: Add Refresh Option (rebuild tree)


#=================================================================
def toggleMaterialVisibility(materialName,materialInputs,visbility):
    '''Changes Visibility on a complete material when the visibility is changed via the Visibility Button
        under the materials
    '''

    mariGeo = mari.current.geo()

    for inputName in materialInputs:

        customName = "m%s" % inputName
        materialChannelName = "%s_%s" % (materialName, inputName)
        sourceChannel = mariGeo.channel(materialChannelName)
        sourceChannel.setMetadata('materialVisibility',visbility)

        if inputName == 'Mask':
            pass
        else:
            baseChannel = mariGeo.channel(customName)
            if baseChannel.findLayer("mGroup"):
                baseChannel = baseChannel.layer("mGroup").groupStack()

            if baseChannel.findLayer(materialChannelName):
                layer = baseChannel.layer(materialChannelName)
                baseChannel.layer(materialChannelName).setVisibility(visbility)
            else:
                mari.utils.message('Associated Material not found','Material could not be found')

#=================================================================
def sortMaterialLayers(layerOrderFromUI):
    '''Sorts material layers based on material UI order
    '''
    mariGeo = mari.current.geo()

    current_channel_selection = mari.current.channel()
    current_layer_selection = mari.current.layer().name()

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
                    for Grouplayer in groupStack.layerList():
                        setMetadataFromChannelLayer(Grouplayer)
                    groupStack.removeLayers(groupStack.layerList())

            for layerName in layerOrderFromUI[::-1]:
                channelName = "%s_%s" % (layerName, inputName)
                channelMaskName = "%s_%s" % (layerName, 'Mask')
                layerChannel = mariGeo.channel(channelName)
                maskChannel = mariGeo.channel(channelMaskName)
                inputVisibility = layerChannel.metadata('materialVisibility')
                link_layer = groupStack.createChannelLayer(channelName, layerChannel)
                link_layer.setMetadata("material", layerName)
                link_layer.setVisibility(inputVisibility)
                restoreChannelLayerSettings(layerChannel,link_layer)

                maskStack = link_layer.makeMaskStack()
                maskStack.removeLayers(maskStack.layerList())

                maskStack.createChannelLayer(maskChannel.name(), maskChannel)

                try:
                    layerSelection = groupStack.findLayer(current_layer_selection)
                    layerSelection.makeCurrent()
                except:
                    pass


    try:
        current_channel_selection.makeCurrent()
        layerSelection = current_channel_selection.findLayer(current_layer_selection)
        layerSelection.makeCurrent()       
    except:
        pass

#=================================================================
def getMaterialOrder():
    '''Finds the material layer order and visibility from the first primary input channel found
    '''
    mariGeo = mari.current.geo()

    layerOrderList = []
    for channel in mariGeo.channelList():
        if channel.hasMetadata("isPrimaryInput"):
            for layer in channel.layerList():
                if layer.hasMetadata("materialGroup"):
                    groupStack = layer.groupStack()
                    for layer in groupStack.layerList():
                        if layer.hasMetadata("material"):
                            if layer.metadata("material") not in layerOrderList:
                                layerVisibility = layer.isVisible()
                                layerData = (layer.metadata("material"),layerVisibility)
                                layerOrderList.append(layerData)
            break


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
            if channel.hasMetadata("materialVisibility"):
                materialVisibility = channel.metadata("materialVisibility")
            else:
                materialVisibility = "True"

            materialSet = (channel.metadata("material"),materialVisibility)
            materials.add(materialSet)

    return materials

#=================================================================

def checkDuplicateMaterialName(material):
    ''' Checks if a Material with the given Name exists'''

    existingMaterials = getAllMaterials()
    materialExists = False

    for existingMaterial in existingMaterials:
        if material == existingMaterial[0]:
            materialExists = True
            mari.utils.message('A Material with this Name already exists','Unable to create Material')


    return materialExists 

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
    # layer.setMetadataFlags("baseColor", 16)
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
    channel.setMetadata("materialVisibility", True)
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
    materialChannelName = "%s_%s" % (materialName, inputName)
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

    channelName = "%s_%s" % (materialName, inputName)
    linkLayer = groupStack.createChannelLayer(channelName, newChannel)
    linkLayer.setMetadata("material", materialName)
    linkLayer.setMetadataFlags("material", 16)


    maskStack = linkLayer.makeMaskStack()
    maskStack.removeLayers(maskStack.layerList())

    maskStack.createChannelLayer(maskChannel.name(), maskChannel)

    return newChannel

#=================================================================

def updateMaterialChannel(oldMaterialName, newMaterialName, inputName):
    ''' Updates the Name of a Material Channel
    '''

    mariGeo = mari.current.geo()


    for input in inputName:


        customName = "m%s" % input
        oldMaterialChannelName = "%s_%s" % (oldMaterialName, input)
        oldMaskChannelName = "%s_%s" % (oldMaterialName, 'Mask')
        newMaterialChannelName = "%s_%s" % (newMaterialName, input)
        newMaskChannelName = "%s_%s" % (newMaterialName, 'Mask')

        if input != 'Mask':
            baseChannel = mariGeo.channel(customName)
            if baseChannel.findLayer("mGroup"):
                groupStack = baseChannel.layer("mGroup").groupStack()
            else:
                mari.utils.message('Unable to find Material Group')
                return

            channelLayer = groupStack.findLayer(oldMaterialChannelName)

            # testing for channel Mask
            if channelLayer.hasMaskStack():
                maskStack = channelLayer.maskStack()
                maskLayer = maskStack.findLayer(oldMaskChannelName)
                maskLayer.setName(newMaskChannelName)


            channelObject = channelLayer.channel()
            
            channelLayer.setName(newMaterialChannelName)
            channelObject.setName(newMaterialChannelName)

            channelLayer.setMetadata("material", newMaterialName)
            channelObject.setMetadata("material", newMaterialName)

        else:
            channelObject = mariGeo.channel(oldMaterialChannelName)
            channelObject.setName(newMaterialChannelName)
            channelObject.setMetadata("material", newMaterialName)

#=================================================================

def setMetadataFromChannelLayer(layer):
    '''
    Reads out settings such as Opacity and Blendmode from a primaryInput ChannelLayer and
    records those settings as Metadata directly on the channel
    '''

    layer = layer

    advBlend = layer.getAdvancedBlendComponent()
    layerBelow = layer.getLayerBelowBlendLut().controlPointsAsString()
    thisLayer = layer.getThisLayerBlendLut().controlPointsAsString()
    blendAmount = layer.blendAmount()
    blendAmountEnabled = layer.blendAmountEnabled()
    blendMode = layer.blendMode()
    blendType = layer.blendType()
    visibility =layer.isVisible()
    colorTag = layer.colorTag()
    swizzle_r = layer.swizzle(0)
    swizzle_g = layer.swizzle(1)
    swizzle_b = layer.swizzle(2)
    swizzle_a = layer.swizzle(3)


    channel = layer.channel()

    channel.setMetadata('mm_SettingsAvailable', True)

    channel.setMetadata('mm_AdvancedBlend', advBlend)
    channel.setMetadata('mm_layerBelow',layerBelow)
    channel.setMetadata('mm_thisLayer',thisLayer)
    channel.setMetadata('mm_blendAmount',blendAmount)
    channel.setMetadata('mm_blendAmountEnabled',blendAmountEnabled)
    channel.setMetadata('mm_blendMode',blendMode)
    channel.setMetadata('mm_blendType',blendType)
    channel.setMetadata('mm_channelLayerVisibility',visibility)
    channel.setMetadata('mm_colorTag',colorTag)
    channel.setMetadata('mm_swizzle_r',swizzle_r)
    channel.setMetadata('mm_swizzle_g',swizzle_g)
    channel.setMetadata('mm_swizzle_b',swizzle_b)
    channel.setMetadata('mm_swizzle_a',swizzle_a)
    channel.setMetadata('mm_SettingsAvailable', True)

    channel.setMetadataFlags('mm_SettingsAvailable', 1 | 16)

    channel.setMetadataFlags('mm_AdvancedBlend', 1 | 16)
    channel.setMetadataFlags('mm_layerBelow', 1 | 16)
    channel.setMetadataFlags('mm_thisLayer', 1 | 16)
    channel.setMetadataFlags('mm_blendAmount', 1 | 16)
    channel.setMetadataFlags('mm_blendAmountEnabled', 1 | 16)
    channel.setMetadataFlags('mm_blendMode', 1 | 16)
    channel.setMetadataFlags('mm_blendType', 1 | 16)
    channel.setMetadataFlags('mm_channelLayerVisibility', 1 | 16)
    channel.setMetadataFlags('mm_colorTag', 1 | 16)
    channel.setMetadataFlags('mm_swizzle_r', 1 | 16)
    channel.setMetadataFlags('mm_swizzle_g', 1 | 16)
    channel.setMetadataFlags('mm_swizzle_b', 1 | 16)
    channel.setMetadataFlags('mm_swizzle_a', 1 | 16)

def restoreChannelLayerSettings(channel,layer):
    ''' restores all previous settings on a channel layer after the material group is completely rebuild
    '''

    if channel.hasMetadata('mm_SettingsAvailable'):

        advBlend = channel.metadata('mm_AdvancedBlend')
        layerBelow = channel.metadata('mm_layerBelow')
        thisLayer = channel.metadata('mm_thisLayer')
        blendAmount = channel.metadata('mm_blendAmount')
        blendAmountEnabled = channel.metadata('mm_blendAmountEnabled')
        blendMode = channel.metadata('mm_blendMode')
        blendType = channel.metadata('mm_blendType')
        visibility = channel.metadata('mm_channelLayerVisibility')
        colorTag = channel.metadata('mm_colorTag')
        swizzle_r = channel.metadata('mm_swizzle_r')
        swizzle_g = channel.metadata('mm_swizzle_g')
        swizzle_b = channel.metadata('mm_swizzle_b')
        swizzle_a = channel.metadata('mm_swizzle_a')

        layer.setAdvancedBlendComponent(advBlend)

        curBelow = layer.getLayerBelowBlendLut()
        curBelow.setControlPointsFromString(layerBelow)
        layer.setLayerBelowBlendLut(curBelow)

        curThis = layer.getLayerBelowBlendLut()
        curThis.setControlPointsFromString(thisLayer)
        layer.setThisLayerBlendLut(curThis)

        layer.setBlendAmount(blendAmount)
        layer.setBlendAmountEnabled(blendAmountEnabled)
        layer.setBlendMode(blendMode)
        layer.setBlendType(blendType)
        layer.setVisibility(visibility)
        layer.setColorTag(colorTag)
        layer.setSwizzle(0,swizzle_r)
        layer.setSwizzle(1,swizzle_g)
        layer.setSwizzle(2,swizzle_b)
        layer.setSwizzle(3,swizzle_a)

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

def duplicateMaterialChannel(src_materialName, new_materialName):
    '''Duplicates a Material Channel
    '''

    currentChannel = mari.current.channel()

    mariGeo = mari.current.geo()

    duplicateAction = mari.actions.find('/Mari/MARI Extension Pack/Channels/Duplicate')

    src_inputChannels = getMaterialInputs(src_materialName)
    maskStacks = []

    for channel in src_inputChannels:
        inputName = channel
        customName = "m%s" % inputName
        materialChannelName = "%s_%s" % (new_materialName, inputName)


        channelObj = src_inputChannels[channel]
        channelObj.makeCurrent()
        duplicateAction.trigger()

        duplicatedMaterial = mari.current.channel()

        duplicatedMaterial.setMetadata('material', new_materialName)
        duplicatedMaterial.setName(materialChannelName)

        if inputName == 'Mask':
            pass
        else:
            baseChannel = mariGeo.channel(customName)
            #Create and link mask
            if baseChannel.findLayer("mGroup"):
                groupStack = baseChannel.layer("mGroup").groupStack()
            else:
                newGroup = baseChannel.createGroupLayer("mGroup")
                newGroup.setMetadata("materialGroup", True)
                newGroup.setMetadataFlags("materialGroup", 16)
                groupStack = newGroup.groupStack()

        # channelName = "%s_%s" % (materialName, inputName)
            linkLayer = groupStack.createChannelLayer(materialChannelName, duplicatedMaterial)
            linkLayer.setMetadata("material", new_materialName)
            linkLayer.setMetadataFlags("material", 16)


            maskStack = linkLayer.makeMaskStack()
            maskStacks.append(maskStack)

    maskChannelName = "%s_%s" % (new_materialName, 'Mask')
    maskChannel = mariGeo.channel(maskChannelName)
    for maskStack in maskStacks:
        maskStack.removeLayers(maskStack.layerList())
        maskStack.createChannelLayer(maskChannel.name(), maskChannel)


    currentChannel.makeCurrent()

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
        # shader.setMetadataFlags("isMaterialShader", 16)

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
            if shader.hasMetadata("isMaterialShader"):
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
            mariShader.setInput(input_name, newChannel)

        self.close()
        self.channelsCreated.emit()

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class CreateMaterial(QtGui.QDialog):
    '''
    Dialog used to create a new Material
    '''
    materialCreated = QtCore.Signal(str)
    def __init__(self, parent, mode, material=None):
        super(CreateMaterial, self).__init__(parent)

        self.setWindowTitle("Create Material / Element")

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

        duplicataNameCheck = checkDuplicateMaterialName(self.name.text())

        if duplicataNameCheck:
            return

        current_channel_selection = mari.current.channel()
        current_layer_selection = mari.current.layer()

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

        try:
            current_channel_selection.makeCurrent()
            current_layer_selection.makeCurrent()
        except:
            pass


        self.close()
        self.materialCreated.emit(materialName)

#______________________________________________________________________________________________________________________________
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

class renameMaterialUI(QtGui.QDialog):
    '''
    Dialog used to rename a Material, both used for Duplicating Materials as well as renaming
    '''
    # materialCreated = QtCore.Signal(str)
    def __init__(self, parent,title, mode, material=None):
        super(renameMaterialUI, self).__init__(parent)

        self.setWindowTitle(title)

        self.setParent(parent)

        #Layouts
        mainLayout = QtGui.QVBoxLayout()
        nameLayout = QtGui.QHBoxLayout()
        buttonLayout = QtGui.QHBoxLayout()
        self.setLayout(mainLayout)

        #Widgets
        materialNameLabel = QtGui.QLabel("Name:")
        self.name = QtGui.QLineEdit(material)
        cancelBtn = QtGui.QPushButton("Cancel")
        renameBtn = QtGui.QPushButton("Rename")
        duplicateBtn = QtGui.QPushButton('Duplicate')

        #Populate Layouts
        buttonLayout.addWidget(cancelBtn)
        if mode == 'Duplicate':
            buttonLayout.addWidget(duplicateBtn)
        else:
            buttonLayout.addWidget(renameBtn)
        nameLayout.addWidget(materialNameLabel)
        nameLayout.addWidget(self.name)
        mainLayout.addLayout(nameLayout)
        mainLayout.addLayout(buttonLayout)

        #Connections
        cancelBtn.clicked.connect(self.reject)
        
        if mode == 'Duplicate':
            duplicateBtn.clicked.connect(self.accept)
        else:
            renameBtn.clicked.connect(self.accept)


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getRenamedMaterial(self):
        ''' Grabs the new name from the Rename Dialog'''

        return self.name.text()

# _____________________________________________________________________________________________________________________________
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
        self.selectButton.setToolTip('Select the Element via the LayerStack')
        self.cacheButton = QtGui.QPushButton("Cache")
        self.cacheButton.setToolTip('Cache the selected ELement')
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

        self.setWindowTitle("Material Manager")

        self.setMinimumSize(400, 600)

        #Layouts
        mainLayout = QtGui.QVBoxLayout()
        inputBtnLayout = QtGui.QHBoxLayout()
        materialBtnLayout = QtGui.QHBoxLayout()
        elementBtnLayout = QtGui.QHBoxLayout()
        self.setLayout(mainLayout)


        # icons
        upIcon = QtGui.QIcon(iconpath + os.sep +  "Top.png")
        downIcon = QtGui.QIcon(iconpath + os.sep +  "Bottom.png")
        removeMat = QtGui.QIcon(iconpath + os.sep +  "RemoveShader.png")
        addMat = QtGui.QIcon(iconpath + os.sep +  "AddMaterials.png")
        plus = QtGui.QIcon(iconpath + os.sep +  "Plus.png")
        minus = QtGui.QIcon(iconpath + os.sep +  "Minus.png")
        visbility = QtGui.QIcon(iconpath + os.sep +  "ToggleHidden.png")
        renameMaterial = QtGui.QIcon(iconpath + os.sep + "script.png")
        duplicateMaterial = QtGui.QIcon(iconpath + os.sep + "DuplicateShader.png")

        createShaderBtn = QtGui.QPushButton("Create Shader")
        createShaderBtn.setToolTip('Create a new Shader')
        inputBtnLayout.addWidget(createShaderBtn)
        createInputChanBtn = QtGui.QPushButton("Create Inputs")
        createInputChanBtn.setToolTip('Choose which Shader Inputs to use')
        inputBtnLayout.addWidget(createInputChanBtn)
        mainLayout.addLayout(inputBtnLayout)


        inputBtnLayout.addWidget(createShaderBtn)

        visibilityItemBtn =QtGui.QPushButton(visbility, "")
        visibilityItemBtn.setToolTip('Toggle Visbility of current Material')
        materialBtnLayout.addWidget(visibilityItemBtn)


        renameMatBtn =QtGui.QPushButton(renameMaterial, "")
        renameMatBtn.setToolTip('Rename currently selected Material')
        materialBtnLayout.addWidget(renameMatBtn)

        moveItemUpBtn = QtGui.QPushButton(upIcon, "")


        moveItemUpBtn.setToolTip('Move currenty selected material up')
        materialBtnLayout.addWidget(moveItemUpBtn)
        moveItemDownBtn = QtGui.QPushButton(downIcon, "")
        moveItemDownBtn.setToolTip('Move currenty selected material down')
        materialBtnLayout.addWidget(moveItemDownBtn)
        duplicateMaterialBtn = QtGui.QPushButton(duplicateMaterial,"")
        duplicateMaterialBtn.setToolTip('Duplicate the currently selected material')
        materialBtnLayout.addWidget(duplicateMaterialBtn)
        removeMaterialBtn = QtGui.QPushButton(removeMat, "")
        removeMaterialBtn.setToolTip('Remove Selected Material')
        materialBtnLayout.addWidget(removeMaterialBtn)
        addMaterialBtn = QtGui.QPushButton(addMat, "")
        addMaterialBtn.setToolTip('Add new Material')
        materialBtnLayout.addWidget(addMaterialBtn)

        removeElementBtn = QtGui.QPushButton(minus, "")
        removeElementBtn.setToolTip('Removes a Material Element')

        elementBtnLayout.addWidget(removeElementBtn)
        addElementBtn = QtGui.QPushButton(plus, "")
        addElementBtn.setToolTip('Add a Material Element')

        elementBtnLayout.addWidget(addElementBtn)

        self.materialTree = QtGui.QTreeWidget()
        # self.materialTree.setColumnCount(2)
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

        mari.utils.connect(mari.projects.opened,self.onProjectOpen)
        mari.utils.connect(mari.projects.closed,self.onProjectClosed)
        mari.utils.connect(mari.geo.entityMadeCurrent,self.onProjectOpen)

        # remove when part of palette:
        self.onProjectOpen()

        self.materialTree.itemClicked.connect(self.buildMaterialSettings)
        addMaterialBtn.clicked.connect(self.addMaterial)
        addElementBtn.clicked.connect(self.addElement)
        removeMaterialBtn.clicked.connect(self.removeMaterial)
        removeElementBtn.clicked.connect(self.removeElement)
        moveItemUpBtn.clicked.connect(self.moveItemUp)
        moveItemDownBtn.clicked.connect(self.moveItemDown)
        visibilityItemBtn.clicked.connect(self.toggleMaterialVisibility)
        renameMatBtn.clicked.connect(self.renameMaterial)
        duplicateMaterialBtn.clicked.connect(self.duplicateMaterial)
        createShaderBtn.clicked.connect(self.createMaterialShader)
        createInputChanBtn.clicked.connect(self.createInputChannels)

    def onProjectOpen(self):
        self.buildTreeFromChannels()
        self.sortMaterialListItems()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def onProjectClosed(self):
        self.materialTree.clear()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def createMaterialShader(self):
        diag = ChooseShader(self)
        diag.show()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def createInputChannels(self):
        diag = CreateChannels(self)
        diag.show()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def moveItemDown(self):
        '''Move item up one row
        '''

        takeItem = self.materialTree.currentItem()
        if takeItem is None:
            return
        takeIndex = self.materialTree.indexOfTopLevelItem(takeItem)
        maxIndex = len(getAllMaterials()) - 1
        if takeIndex == maxIndex:
            return
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
        if takeItem is None:
            return
        takeIndex = self.materialTree.indexOfTopLevelItem(takeItem)
        if takeIndex == 0:
            return
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
            newItem.setText(0, name[0])
            if name[1]:
                newItem.setIcon(0, QtGui.QPixmap("%s/lighting_full.png" % iconpath))
                newItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)

            else:
                newItem.setIcon(0, QtGui.QPixmap("%s/toolbar_ellispe.png" % iconpath))
                newItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)


            self.materialTree.addTopLevelItem(newItem)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def buildTreeFromChannels(self):

        self.materialTree.clear()

        materials = getAllMaterials()

        for material in materials:

            materialName = material[0]
            materialVisibility = material[1]

            newItem = QtGui.QTreeWidgetItem()
            newItem.setText(0, materialName)
            if materialVisibility:
                newItem.setIcon(0, QtGui.QPixmap("%s/lighting_full.png" % iconpath))
                newItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
            else:
                newItem.setIcon(0, QtGui.QPixmap("%s/toolbar_ellispe.png" % iconpath))
                newItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

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
        self.sortMaterialListItems()
        for index in range(self.materialTree.topLevelItemCount()):
            item = self.materialTree.topLevelItem(index)
            if item.text(0) == material:
                item.setSelected(True)
                self.materialTree.setCurrentItem(item)
                self.buildMaterialSettings()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def addMaterial(self):
        ''' Launches a dialog to create a new Material'''
        diag = CreateMaterial(self, "material")
        diag.show()
        diag.materialCreated.connect(self.refresh)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def renameMaterial(self):
        ''' Launches a dialog to rename a Material'''
        material = None
        try:
            material = self.materialTree.currentItem().text(0)
        except:
            return

        title = 'Rename Material / Element'
        diag = renameMaterialUI(self,title,'Rename',material=material)
        diag.show()
        newMaterialName = None

        if diag.exec_():
            newMaterialName = diag.getRenamedMaterial()

        # if nothing is selected
        if newMaterialName is None:
            return

        # if old name is same as new name
        if material == newMaterialName:
            return

        # if name already exists
        duplicateNameCheck = checkDuplicateMaterialName(newMaterialName)
        if duplicateNameCheck:
            return

        materialInputs = getMaterialInputs(material)

        updateMaterialChannel(material,newMaterialName,materialInputs)
        self.materialTree.currentItem().setText(0, newMaterialName)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def duplicateMaterial(self):
        '''Duplicate a Material'''

        duplicateAction = mari.actions.find('/Mari/MARI Extension Pack/Channels/Duplicate')
        if duplicateAction is None:
            mari.utils.message('Channel Duplication Action could not be found. \nChannel Duplicaion is a feature of MARI Extension Pack.','Feature not supported')
            return

        try:
            currentMaterial = self.materialTree.currentItem().text(0)
        except:
            return

        title = 'Duplicate as'
        diag = renameMaterialUI(self,title,'Duplicate',material=currentMaterial)
        diag.show()
        newMaterialName = None

        if diag.exec_():
            newMaterialName = diag.getRenamedMaterial()

        # if nothing is selected
        if newMaterialName is None:
            return

        # if name already exists
        duplicateNameCheck = checkDuplicateMaterialName(newMaterialName)
        if duplicateNameCheck:
            return

        duplicateMaterialChannel(currentMaterial,newMaterialName)
        self.buildTreeFromChannels()
        self.sortMaterialListItems()

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

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def toggleMaterialVisibility(self):
        '''Toggles Visibility of Material
        '''
        currentItem = self.materialTree.currentItem()
        if currentItem is None:
            return
        currentMaterial = currentItem.text(0)
        itemFlags = currentItem.flags()
        visbilityState = False
        if itemFlags & QtCore.Qt.ItemIsEditable:
            visbilityState = True

        materialInputs = getMaterialInputs(currentMaterial)

        if visbilityState:
            currentItem.setIcon(0, QtGui.QPixmap("%s/toolbar_ellispe.png" % iconpath))
            currentItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable )
            toggleMaterialVisibility(currentMaterial,materialInputs,False)
        else:
            currentItem.setIcon(0, QtGui.QPixmap("%s/lighting_full.png" % iconpath))
            currentItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
            toggleMaterialVisibility(currentMaterial,materialInputs,True)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _makePalette():
    # Create the palette if it doesn't exist; if it does, we don't need to do any more initialisation here
    materialPalette = mari.palettes.find("Material Manager")
    if materialPalette is None:
      try:
          materialPalette = mari.palettes.createWithIcon('Material Manager', iconpath + os.sep +  "Shader.png")
      except ValueError:
          print "Failed to register Material palette"
          return

    # Clear the content of palette to clean up first
    materialPalette.setBodyWidget(QtGui.QWidget())

    materialControlWidget = MaterialManager()
    materialPalette.setBodyWidget(materialControlWidget)

    return materialPalette, materialControlWidget


diag = MaterialManager()
diag.show()


# if mari.app.isRunning():
#     _makePalette()

