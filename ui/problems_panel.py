import bpy
import sys
from .. import problems
from .. utils.layout import writeText

class ProblemsPanel(bpy.types.Panel):
    bl_idname = "an_problems_panel"
    bl_label = "Problems"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Animation Nodes"

    @classmethod
    def poll(cls, context):
        tree = cls.getTree()
        if tree is None: return False
        return tree.bl_idname == "an_AnimationNodeTree" and len(problems.getProblems()) > 0

    def draw_header(self, context):
        self.layout.label("", icon = "ERROR")

    def draw(self, context):
        layout = self.layout
        col = layout.column(align = True)
        subcol = col.column(align = True)
        subcol.scale_y = 1.5
        subcol.operator("an.tag_retry_execution", text = "Retry", icon = "FILE_REFRESH")
        if sys.platform == "win32":
            col.operator("wm.console_toggle", text = "Toogle Console", icon = "CONSOLE")

        layout.separator()

        for problem in problems.getProblems():
            problem.draw(layout)
            layout.separator()

        layout.separator()

        col = layout.column(align = True)
        tree = self.getTree()
        lastExec = tree.lastExecutionInfo
        col.label("Last successful execution using:")
        col.label("    Blender:   v{}".format(lastExec.blenderVersionString))
        col.label("    Animation Nodes:   v{}".format(lastExec.animationNodesVersionString))

        if lastExec.isDefault:
            writeText(col,
                ("These versions are only guesses. This file has not been executed "
                 "in a version that supports storing of version information yet."),
                autoWidth = True)

    @classmethod
    def getTree(cls):
        return bpy.context.space_data.edit_tree
