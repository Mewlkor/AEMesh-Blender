# importer.py
import bpy, os
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty, BoolProperty, CollectionProperty
from bpy.types import Armature, Operator
import math
from struct import unpack
from mathutils import Euler, Vector
from collections import defaultdict
from . import common
from .common import FLAGS
from .read_helper import *

from . import red

VERSION = {
    "AEMesh\x00": 1,
    "V2AEMesh\x00": 2,
    "V3AEMesh\x00": 3,
    "V4AEMesh\x00": 4,
    "V5AEMesh\x00": 5,
}


def sign_check(c, cs):
    if (cs == -1 and c < 0) or (cs == 0x0 and c >= 0):
        return 1
    return -1


def triangle_strips_unpack(indices, tstrip_array):
    i = 0
    unpacked = []
    for strip in tstrip_array:
        for j in range(strip - 2):
            if j % 2 == 0:
                unpacked.append(
                    [indices[i + j], indices[i + j + 1], indices[i + j + 2]]
                )
            else:
                unpacked.append(
                    [indices[i + j], indices[i + j + 2], indices[i + j + 1]]
                )
        i += strip
    return unpacked


def import_aem(file_path):
    print(f"\nLoading: {os.path.basename(file_path)}")
    bones = []
    meshes = []
    anims = []
    importer_state = "READ_HEADER"
    bpy.ops.object.armature_add()
    print(bpy.data.objects.keys())
    armature_obj = bpy.data.objects["Armature"]
    armature_obj.name = "Armature"
    armature = bpy.data.armatures[0]  # armature_obj  # armature_obj.data
    print(armature)
    armature.name = "Armature"
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")
    root_bone = armature.edit_bones[0]  # .new("root")
    root_bone.name = "root"
    root_bone.head = (0, 0, 0)
    root_bone.tail = (0, 0, 1)
    # root_bone.name = "root"
    bpy.ops.object.mode_set(mode="OBJECT")
    # root_bone.matrix = Matrix.Identity(4)
    # edit_bone.parent = root_bone
    with open(file_path, "rb") as file_aem:
        while importer_state != "END":
            if importer_state == "READ_HEADER":
                print(importer_state)
                magic = ""
                while not magic.endswith("AEMesh\x00"):
                    magic += file_aem.read(1).decode("utf-8")
                    if len(magic) > 9:
                        file_aem.close()
                        print(
                            "Unsuppored .aem file. Invalid signature"
                        )  # self.report ...
                        return -1
                flags = int.from_bytes(file_aem.read(1))
                mesh_present = bool(flags & FLAGS["basemesh"])
                if mesh_present:
                    uvs_present = bool(flags & FLAGS["uvs"])
                    normals_present = bool(flags & FLAGS["normals"])
                    unk_present = bool(flags & FLAGS["unk"])
                    version = VERSION[magic]

                    submesh_num = 1
                    first_mesh = True
                    if version in (3, 4, 5):
                        submesh_num = unpack("h", file_aem.read(2))[0]
                        print(f"Number of submeshes: {submesh_num}")
                    submeshes_left = submesh_num

                    importer_state = "READ_MESH"
                else:
                    print("Basemesh flag is false!")
                    importer_state = "END"

            if importer_state == "READ_MESH":
                print(importer_state)
                submeshes_left -= 1
                if version in (4, 5):
                    # print(hex(file_aem.tell()))
                    pivot_point = unpack("fff", file_aem.read(12))
                    print(
                        f"Pivot point: x: {pivot_point[0]}, y: {pivot_point[1]}, z: {pivot_point[2]}"
                    )
                    indices_num = read_ushort(file_aem)
                    faces = read_ushort_triplets_array(file_aem, indices_num)
                    v_num = read_ushort(file_aem)
                    vertices = read_float_triplets_array(file_aem, v_num * 3)
                    if uvs_present:
                        uvs = read_float_twins_array(file_aem, v_num * 2)
                    if normals_present:
                        normals = read_float_triplets_array(file_aem, v_num * 3)
                    if unk_present:
                        try:
                            # some_quaternions = read_float_quadruplets_array(file_aem, 4* v_num)
                            some_quaternions = read_float_array(file_aem, 4 * v_num)
                            if any(i != 1 for i in some_quaternions):
                                print("Abnormality in the unknown values!")
                        except Exception as e:
                            print(f"quaternions loading failed: {e}")
                elif version in (1, 2, 3):
                    if version in (2, 3):
                        if version == 3:
                            pivot_point = unpack("fff", file_aem.read(12))
                            print(
                                f"Pivot point: x: {pivot_point[0]}, y: {pivot_point[1]}, z: {pivot_point[2]}"
                            )
                        vertex_cord_size = 6
                        UV_UNIT_POINT = 1 / 4096  # (2^12)
                        NORMALS_UNIT_POINT = 1 / 32768  # (2^15)
                        indices_num = read_short(file_aem)
                        faces = read_short_triplets_array(file_aem, indices_num)
                        v_num = read_short(file_aem)
                        """if cord is negative sign bits are FFFF else they are 0000"""
                        v_block = read_short_hexlets_array(file_aem, v_num * 6)
                        vertices = [
                            (
                                x * sign_check(x, xs),
                                y * sign_check(y, ys),
                                z * sign_check(z, zs),
                            )
                            for x, xs, y, ys, z, zs in v_block
                        ]
                    if version == 1:
                        vertex_cord_size = 3
                        UV_UNIT_POINT = NORMALS_UNIT_POINT = 1 / 256  # (2^8)
                        indices_num = read_short(file_aem)
                        pre_strip_pos = file_aem.tell()
                        try:  # handling sepcial case of AEM version 1 and a half
                            UV_UNIT_POINT = 1 / 4096
                            NORMALS_UNIT_POINT = 1 / 32768
                            indices = read_short_array(file_aem, indices_num)
                            t_strips_len = read_short(file_aem)
                            t_strips = read_short_array(file_aem, t_strips_len)
                            faces = triangle_strips_unpack(indices, t_strips)
                        except IndexError:
                            file_aem.seek(pre_strip_pos)
                            faces = read_short_triplets_array(file_aem, indices_num)
                        v_num = read_short(file_aem)
                        vertices = read_short_triplets_array(file_aem, v_num * 3)

                    if uvs_present:
                        uv_block = read_short_twins_array(file_aem, v_num * 2)
                        # print(f"UVS maximum raw value {max(uv_block)}")
                        uvs = [
                            (u * UV_UNIT_POINT, v * UV_UNIT_POINT) for u, v in uv_block
                        ]
                    if normals_present:
                        normals_block = read_short_triplets_array(file_aem, v_num * 3)
                        normals = [
                            (
                                x * NORMALS_UNIT_POINT,
                                y * NORMALS_UNIT_POINT,
                                z * NORMALS_UNIT_POINT,
                            )
                            for x, y, z in normals_block
                        ]
                    if unk_present:
                        try:
                            # print("some keys")
                            # print(f"vnum: {v_num}, {hex(v_num)}")
                            # file size - pos - 4*vnum*4 < 0 -> throw
                            some_twins = read_short_twins_array(file_aem, 2 * v_num)
                            for i in range(0, len(some_quaternions), 5):
                                print(
                                    " ".join(
                                        f"{q}" for q in some_quaternions[i : i + 5]
                                    )
                                )
                        except Exception as e:
                            print(f"quaternions loading failed: {e}")

                    if version == 1:
                        is_transparent = int.from_bytes(file_aem.read(1))

                else:
                    print(f"Unsupported file AEM version: {version}")
                    return -1

                # Read BoundingSphere
                if version in (3, 4, 5):
                    bounding_sphere = unpack(
                        "<4f", file_aem.read(16)
                    )  # read_float_quadruplets_array(file_aem, 4)
                    # unpack('<4f',file_aem.read(16))
                    print(
                        f"BoundingBox: x: {bounding_sphere[0]}, y: {bounding_sphere[1]}, z: {bounding_sphere[2]}, r: {bounding_sphere[3]}"
                    )

                importer_state = "BUILD_MESH"

            if importer_state == "BUILD_MESH":
                bon_idx = submesh_num - submeshes_left
                bone_name = f"submesh_{bon_idx}"

                # Create armature if it doesn't exist

                obj_name = os.path.basename(file_path).split(".")[0]
                mesh = bpy.data.meshes.new(name=bone_name)
                mesh.from_pydata(vertices, [], faces)

                if uvs_present:
                    uv_layer = mesh.uv_layers.new(name="UVMap")
                    for poly in mesh.polygons:
                        for loop_index in poly.loop_indices:
                            loop_vert_index = mesh.loops[loop_index].vertex_index
                            uv_layer.data[loop_index].uv = uvs[loop_vert_index]

                if normals_present:
                    mesh.normals_split_custom_set_from_vertices(normals)
                    # Select all imported objects

                # Make sure we're in object mode
                # bpy.ops.object.mode_set(mode="EDIT")
                # bpy.ops.mesh.select_all(action="SELECT")
                # Select all imported objects

                # Return to object mode
                bpy.ops.object.mode_set(mode="OBJECT")
                obj = bpy.data.objects.new(obj_name, mesh)
                obj.data.shade_smooth()
                bpy.context.collection.objects.link(obj)
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)

                bpy.context.view_layer.objects.active = armature_obj
                bpy.ops.object.mode_set(mode="EDIT")
                armature = armature_obj.data
                edit_bone = armature.edit_bones.new(bone_name)
                # edit_bone.matrix = Matrix.Identity(4)
                edit_bone.head = (0, 0, 0)
                edit_bone.tail = (0, 0, 1)  # Default tail position

                # Parent to root if it exists

                edit_bone.parent = armature.edit_bones["root"]

                bpy.ops.object.mode_set(mode="OBJECT")
                if first_mesh:
                    root_mesh = armature_obj
                    first_mesh = False
                # else:
                obj.rotation_mode = "XYZ"
                obj.parent = root_mesh
                obj.rotation_euler = Euler([math.radians(90), 0, 0], "XYZ")
                mesh.update()

                # Add armature modifier to mesh

                armature_mod = obj.modifiers.new(name="Armature", type="ARMATURE")

                armature_mod.object = armature_obj

                # Create vertex groups for bone weights
                vertex_group = obj.vertex_groups.new(name=bone_name)
                for v_idx in range(len(vertices)):
                    vertex_group.add([v_idx], 1.0, "REPLACE")

                meshes.append(obj)
                if version in (3, 4, 5):
                    # build_bounding_sphere(bounding_sphere, obj_name)

                    importer_state = "READ_ANIM"
                else:
                    importer_state = "END"

            if importer_state == "READ_ANIM":
                print(importer_state)
                importer_state = "END"
                TRAN_X = 1
                TRAN_Y = 2
                TRAN_Z = 4
                TRAN_XYZ = 7
                ROT_X = 0x40
                ROT_Y = 0x80
                ROT_Z = 0x100
                ROT_XYZ = 0x1C0
                SCALE_X = 8
                SCALE_Y = 0x10
                SCALE_Z = 0x20
                SCALE_XYZ = 0x38
                ROT_Z, ROT_Y = ROT_Y, ROT_Z

                if version in (3, 4, 5):

                    mesh = red.Mesh()
                    red_success = mesh.read_enhanced_data_from_file(file_aem, flags)
                    if red_success != -1 and len(mesh.transform.keyframes) > 0:
                        # group keyframes by type of tranformation
                        trans = defaultdict(lambda: [None, None, None])
                        rots = defaultdict(lambda: [None, None, None])
                        scals = defaultdict(lambda: [None, None, None])

                        for kf in mesh.transform.keyframes:
                            type = kf["type"]
                            t = kf["time"]

                            if type in (TRAN_X, TRAN_Y, TRAN_Z, TRAN_XYZ):
                                if type == TRAN_X:
                                    trans[t][0] = kf["values"][0]
                                elif type == TRAN_Y:
                                    trans[t][1] = kf["values"][0]
                                elif type == TRAN_Z:
                                    trans[t][2] = kf["values"][0]
                                elif type == TRAN_XYZ:
                                    trans[t] = list(kf["values"])

                            if type in (ROT_X, ROT_Y, ROT_Z, ROT_XYZ):
                                from math import pi

                                if type == ROT_X:
                                    rots[t][0] = kf["values"][0]
                                elif type == ROT_Y:
                                    rots[t][1] = kf["values"][0]
                                elif type == ROT_Z:
                                    rots[t][2] = kf["values"][0]
                                elif type == ROT_XYZ:
                                    print(
                                        "WARNING: ROT_XYZ detected. case for analysis."
                                    )
                                    rots[t] = list(r for r in kf["values"])

                            if type in (SCALE_X, SCALE_Y, SCALE_Z, SCALE_XYZ):
                                if type == SCALE_X:
                                    scals[t][0] = kf["values"][0]
                                elif type == SCALE_Y:
                                    scals[t][1] = kf["values"][0]
                                elif type == SCALE_Z:
                                    scals[t][2] = kf["values"][0]
                                elif type == SCALE_XYZ:
                                    scals[t] = list(kf["values"])

                        all_times = sorted(
                            list(
                                set(trans.keys()) | set(rots.keys()) | set(scals.keys())
                            )
                        )
                        frame_rate = round(
                            1.0 / (mesh.transform.timeBetweenFrames / 1000.0)
                        )
                        bpy.context.scene.frame_set(1)
                        bpy.context.view_layer.objects.active = armature_obj
                        bpy.ops.object.mode_set(mode="POSE")
                        pose_bone = armature_obj.pose.bones[bone_name]
                        pose_bone.rotation_mode = "XYZ"
                        print(f"FRAME RATE {frame_rate}")
                        for t in all_times:
                            """
                            calculate frame based on the time and the bake fps.
                            "Bad Practice" if we wanted to use the animation in blender, super usefull for .aem as the animations were created for 30fps
                            The gltf export converts from exact frame to time. In game time is way better because framerate is unstable.
                            """
                            frame = round(((t * int(frame_rate)) / 1000) + 1)
                            bpy.context.scene.frame_set(frame)

                            # Set location
                            if t in trans:
                                pose_bone.location = Vector(trans[t])
                                pose_bone.keyframe_insert(data_path="location")

                            # Set rotation (convert degrees to radians)
                            if t in rots:
                                pose_bone.rotation_euler = Euler(
                                    [
                                        rots[t][0],
                                        rots[t][1],
                                        rots[t][2],
                                    ],
                                    "XYZ",
                                )

                                pose_bone.keyframe_insert(data_path="rotation_euler")
                                print(f"ADDED ROTATION KEYFRAME FOR MESH:{bone_name}")

                            # Set scale
                            if t in scals:
                                pose_bone.scale = Vector(scals[t])
                                pose_bone.keyframe_insert(data_path="scale")

                        bpy.ops.object.mode_set(mode="OBJECT")
                    if submeshes_left > 0:
                        importer_state = "READ_MESH"

            if importer_state == "END":
                for mesh in meshes:
                    mesh.select_set(True)
                    bpy.context.view_layer.objects.active = mesh
                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.remove_doubles(
                        threshold=0.0001,
                        use_unselected=False,
                        use_sharp_edge_from_normals=True,
                    )
                    bpy.ops.object.mode_set(mode="OBJECT")
                    mesh.select_set(False)
                if mesh_present == False:
                    return -1
                if version == 1:
                    return (root_mesh, version, is_transparent)
                return (root_mesh, version, normals_present, submesh_num)


class ImportAEM(Operator, ImportHelper):
    """Import from AEM file format (.aem)"""

    bl_idname = "import_scene.aem"
    bl_label = "Import AEM"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ".aem"

    filter_glob: StringProperty(
        default="*.aem",
        options={"HIDDEN"},
        maxlen=255,
    )

    files: CollectionProperty(type=bpy.types.PropertyGroup)

    scale: FloatProperty(
        name="Scale Factor",
        description="Scale factor for imported objects",
        default=common.SCALE,
        min=0.001,
        max=1.0,
    )

    dummy_property: BoolProperty(
        name="Dummy toggle",
        description="Does nothing",
        default=True,
    )

    def execute(self, context):
        common.SCALE = self.scale

        if len(self.filepath) < 1:
            print("No valid AEM provided.")
            return {"FINISHED"}

        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)

        if len(self.files) > 1:
            directory = os.path.dirname(self.filepath)
            for file in self.files:
                file_path = os.path.join(directory, file.name)
                bpy.ops.object.select_all(action="DESELECT")
                root_mesh = import_aem(file_path)[0]
                bpy.ops.object.select_all(action="DESELECT")
                bpy.context.view_layer.objects.active = root_mesh
                # bpy.ops.transform.rotate(value=-pi / 2, orient_axis='X')
                # bpy.ops.transform.resize(value=(SCALE,SCALE,SCALE))
                # root_mesh.rotation_euler = (pi / 2, 0, 0)
                root_mesh.scale = (self.scale, self.scale, self.scale)
                # bpy.ops.object.transform_apply(rotation=True, scale=True)
                # bpy.ops.object.shade_smooth()
                aem_collection = bpy.data.collections.new(
                    os.path.basename(file_path).split(".")[0]
                )
                bpy.context.scene.collection.children.link(aem_collection)
                for obj in bpy.context.selected_objects:
                    for coll in obj.users_collection:
                        coll.objects.unlink(obj)
                    aem_collection.objects.link(obj)

        else:
            bpy.ops.object.select_all(action="DESELECT")
            root_mesh = import_aem(self.filepath)[0]
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = root_mesh
            print(root_mesh)
            print(bpy.context.view_layer.objects.active)
            bpy.context.scene.tool_settings.transform_pivot_point = "INDIVIDUAL_ORIGINS"
            # root_mesh.rotation_euler = (pi / 2, 0, 0)
            root_mesh.scale = (self.scale, self.scale, self.scale)
            # Enter edit mode
        # bpy.ops.object.mode_set(mode="EDIT")

        # # Select all vertices
        # bpy.ops.mesh.select_all(action="SELECT")

        # # Merge vertices by distance while preserving sharp edges
        # bpy.ops.mesh.remove_doubles(
        #     threshold=1, use_unselected=False, use_sharp_edge_from_normals=True
        # )

        # # Return to object mode
        # bpy.ops.object.mode_set(mode="OBJECT")
        # bpy.ops.transform.rotate(value=-pi/2, orient_axis='X')
        # bpy.ops.transform.resize(value=(SCALE,SCALE,SCALE))
        # bpy.ops.object.transform_apply(rotation=True, scale=True)
        # bpy.ops.object.shade_smooth()

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "scale")


def menu_func_import(self, context):
    self.layout.operator(ImportAEM.bl_idname, text="Abyss Engine Mesh(.aem)")
