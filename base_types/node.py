import re
import bpy
import time
import random
from bpy.props import *
from bpy.app.handlers import persistent
from . node_function_call import getNodeFunctionCallOperatorName
from .. utils.nodes import getAnimationNodeTrees
from .. tree_info import getNetworkWithNode

class AnimationNode:
    isAnimationNode = True

    # unique string for each node; don't change it at all
    identifier = StringProperty(name = "Identifier", default = "")
    inInvalidNetwork = BoolProperty(name = "In Invalid Network", default = False)

    # used for the listboxes in the sidebar
    activeInputIndex = IntProperty()
    activeOutputIndex = IntProperty()

    searchTags = []
    onlySearchTags = False
    isDetermined = False

    @classmethod
    def poll(cls, nodeTree):
        return nodeTree.bl_idname == "an_AnimationNodeTree"


    # functions subclasses can override
    ######################################

    def create(self):
        pass

    def edit(self):
        pass

    def duplicate(self, sourceNode):
        pass

    def delete(self):
        pass

    def draw(self, layout):
        pass

    def drawAdvanced(self, layout):
        layout.label("Has no advanced settings")

    def socketRemoved(self):
        self.socketChanged()

    def socketMoved(self):
        self.socketChanged()

    def customSocketNameChanged(self, socket):
        self.socketChanged()

    def socketChanged(self):
        """
        Use this function when you don't need
        to know what happened exactly to the sockets
        """
        pass


    # Don't override these functions
    ######################################

    def init(self, context):
        self.identifier = createIdentifier()
        self.create()

    def update(self):
        '''Don't use this function at all!!'''
        pass

    def copy(self, sourceNode):
        self.identifier = createIdentifier()
        self.duplicate(sourceNode)

    def free(self):
        self.delete()

    def draw_buttons(self, context, layout):
        if self.inInvalidNetwork: layout.label("Invalid Network", icon = "ERROR")
        self.draw(layout)

    def functionOperator(self, layout, functionName, text = "", icon = "NONE", description = "", data = None):
        idName = getNodeFunctionCallOperatorName(description)
        props = layout.operator(idName, text = text, icon = icon)
        props.nodeTreeName = self.id_data.name
        props.nodeName = self.name
        props.functionName = functionName
        props.callWithData = data is not None
        props.data = str(data)

    def clearSockets(self):
        self.inputs.clear()
        self.outputs.clear()

    def removeSocket(self, socket):
        index = socket.index
        if socket.is_output:
            if index < self.activeOutputIndex: self.activeOutputIndex -= 1
        else:
            if index < self.activeInputIndex: self.activeInputIndex -= 1
        socket.sockets.remove(socket)

    def getUsedOutputsDict(self):
        usedOutputs = {socket.identifier : socket.isLinked for socket in self.outputs}
        return usedOutputs

    def disableSocketEditingInNode(self):
        for socket in self.sockets:
            socket.disableSocketEditingInNode()

    def toogleCustomNameInputVisibility(self):
        self.toogleSocketDisplayProperty("customNameInput")

    def toogleMoveOperatorsVisibility(self):
        self.toogleSocketDisplayProperty("moveOperators")

    def toogleRemoveOperatorVisibility(self):
        self.toogleSocketDisplayProperty("removeOperator")

    def toogleSocketDisplayProperty(self, name):
        if len(self.sockets) == 0: return
        state = not getattr(self.sockets[0].display, name)
        for socket in self.sockets:
            setattr(socket.display, name, state)

    @property
    def nodeTree(self):
        return self.id_data

    @property
    def inputsByIdentifier(self):
        return {socket.identifier : socket for socket in self.inputs}

    @property
    def outputsByIdentifier(self):
        return {socket.identifier : socket for socket in self.outputs}

    @property
    def linkedOutputs(self):
        return [socket for socket in self.outputs if socket.isLinked]

    @property
    def activeInputSocket(self):
        if len(self.inputs) == 0: return None
        return self.inputs[self.activeInputIndex]

    @property
    def activeOutputSocket(self):
        if len(self.outputs) == 0: return None
        return self.outputs[self.activeOutputIndex]

    @property
    def originNodes(self):
        nodes = set()
        for socket in self.inputs:
            nodes.update(socket.linkedNodes)
        return list(nodes)

    @property
    def unlinkedInputs(self):
        return [socket for socket in self.inputs if not socket.isLinked]

    @property
    def network(self):
        return getNetworkWithNode(self)

    @property
    def sockets(self):
        return list(self.inputs) + list(self.outputs)

    @property
    def inputNames(self):
        return {socket.identifier : socket.identifier for socket in self.inputs}

    @property
    def outputNames(self):
        return {socket.identifier : socket.identifier for socket in self.outputs}

    def getModuleList(self):
        return []

    def getExecutionCodeString(self):
        code = self.getExecutionCode()
        if isinstance(code, (list, tuple)):
            return "\n".join(code)
        return code

    def getTaggedExecutionCodeLines(self):
        """
        tags:
            # - self
            % - input variables
            $ - output variables
        """
        inputNames = self.inputNames
        outputNames = self.outputNames

        if hasattr(self, "execute"):
            keywordParameters = ["%{0}%".format(inputNames[socket.identifier]) for socket in self.inputs]
            parameterString = ", ".join(keywordParameters)

            executionString = "#self#.execute(" + parameterString + ")"

            outputVariables = ["${}$".format(outputNames[socket.identifier]) for socket in self.outputs]
            outputString = ", ".join(outputVariables)

            if outputString == "": return [executionString]
            return [outputString + " = "+ executionString]
        else:
            code = self.getExecutionCodeString()
            for inputName in inputNames.values():
                code = tagVariableName(code, inputName, "%")
            for outputName in outputNames.values():
                code = tagVariableName(code, outputName, "$")
            code = tagVariableName(code, "self", "#")
            return code.split("\n")

def tagVariableName(code, name, tag):
    """
    Find all occurences of 'name' in 'code' and set 'tag' before and after it.
    The occurence must not have a dot before it.
    """
    code = re.sub(r"([^\.\"']|^)\b({})\b".format(name), r"\1{0}\2{0}".format(tag), code)
    return code

@persistent
def createMissingIdentifiers(scene = None):
    def unidentifiedNodes():
        for tree in getAnimationNodeTrees():
            for node in tree.nodes:
                if not issubclass(type(node), AnimationNode): continue
                if node.identifier == "": yield node

    for node in unidentifiedNodes():
        node.identifier = createIdentifier()

def createIdentifier():
    identifierLength = 15
    characters = "abcdefghijklmnopqrstuvwxyz" + "0123456789"
    choice = random.SystemRandom().choice
    return "_" + ''.join(choice(characters) for _ in range(identifierLength))



# Register
##################################

def registerHandlers():
    bpy.app.handlers.load_post.append(createMissingIdentifiers)

def unregisterHandlers():
    bpy.app.handlers.load_post.remove(createMissingIdentifiers)
