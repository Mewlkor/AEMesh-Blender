import bpy
import os
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, FloatProperty, EnumProperty, BoolProperty, CollectionProperty
from bpy.types import Operator
from struct import unpack, pack, calcsize
#from numpy import float32, short, ushort
import bmesh
from math import pi
from mathutils import Matrix, Vector
#import sys
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .read_helper import * 
from .BoundingSphere import *

bl_info = {
    "name": "AEM Blender Plugin",
    "author": "Chuck Norris",
    "version": (1, 7),
    "blender": (4, 1, 0),
    "location": "File > Import-Export",
    "description": "AByss Engine Mesh V4,V5 Import / V5 Export",
    "warning": "",
    "category": "Import-Export",
}

SCALE = 0.01

FLAGS = {
    "basemesh":1|16, #10001 every mesh should have it
    "uvs":2,        #00010 texture coordinates
    "normals":4,    #00100
    "unk":8,        #01000 per vertex attributes of some kind
}
VERSION = {
    "AEMesh\x00":1,
    "V2AEMesh\x00":2,
    "V3AEMesh\x00":3,
    "V4AEMesh\x00":4,
    "V5AEMesh\x00":5
}  

'''
def write floats(file, vec3f_list):
    file.write(pack(f"{len(vec3f_list)*3}", *(x for l in vec3f_list for x in l)))
    return
'''
    
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
                unpacked.append([indices[i+j], indices[i+j+1], indices[i+j+2]])
            else:
                unpacked.append([indices[i+j], indices[i+j+2], indices[i+j+1]])
        i += strip  
    return unpacked
    


'''    
def parse_animation(f):
    #read, test, go back
    unpack("3h", f.read(6))
    #type = f.read(2)
    if type == 0:
    if type == 1:
    if type == 2:
        #4 floats?
    if type == 3:
        read_float_twins_array(3, f)
    if type == 4:
        read read_float_quadruplets_array(2, f)
    if type == 5:
        read read_float_quadruplets_array(5, f) 
        # (t, x, y, z)
    if type == 6:
    if type == 10:
'''    


def import_aem(file_path, import_normals=True):
    print(f"\nLoading: {os.path.basename(file_path)}")
    importer_state = "READ_HEADER"  
    with open(file_path, 'rb') as file_aem:
        while (importer_state != "END"):
            if importer_state == "READ_HEADER":
                print(importer_state)
                magic = ""
                while not magic.endswith("AEMesh\x00"):
                    magic += file_aem.read(1).decode("utf-8")
                    if len(magic) > 9:
                        file_aem.close()
                        print("Unsuppored .aem file. Invalid signature") #self.report ...
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
                        submesh_num = unpack('h',file_aem.read(2))[0]
                        print(f'Number of submeshes: {submesh_num}')
                    submeshes_left = submesh_num
                    
                    importer_state = "READ_MESH"
                else:
                    print("Basemesh flag is false!")
                    importer_state = "END"
                    
            if importer_state == "READ_MESH":
                print(importer_state)
                submeshes_left -= 1            
                if version in (4, 5):   
                    #print(hex(file_aem.tell()))
                    pivot_point = unpack('fff',file_aem.read(12))
                    print(f'Pivot point: x: {pivot_point[0]}, y: {pivot_point[1]}, z: {pivot_point[2]}')
                    indices_num = read_short(file_aem)
                    faces = read_short_triplets_array(file_aem, indices_num)
                    v_num = read_short(file_aem)
                    vertices = read_float_triplets_array(file_aem, v_num * 3)
                    if uvs_present:
                        uvs = read_float_twins_array(file_aem, v_num * 2)
                    if import_normals and normals_present:
                        normals = read_float_triplets_array(file_aem, v_num*3)
                    if unk_present:
                        try:
                            #some_quaternions = read_float_quadruplets_array(file_aem, 4* v_num)
                            some_quaternions = read_float_array(file_aem, 4* v_num)
                            if any(i != 1 for i in some_quaternions):
                                print("Abnormality in the unknown values!")
                        except Exception as e:
                            print(f"quaternions loading failed: {e}")                            
                elif version in (1, 2, 3):  
                    if version in (2,3):
                        if version == 3:
                            pivot_point = unpack('fff',file_aem.read(12))
                            print(f'Pivot point: x: {pivot_point[0]}, y: {pivot_point[1]}, z: {pivot_point[2]}')    
                        vertex_cord_size = 6
                        UV_UNIT_POINT = 1/4095 #(2^12)-1
                        NORMALS_UNIT_POINT = 1/32767 #(2^15)-1 
                        indices_num = read_short(file_aem)
                        faces = read_short_triplets_array(file_aem, indices_num)
                        v_num = read_short(file_aem)
                        '''if cord is negative sign bits are FFFF else they are 0000'''
                        v_block = read_short_hexlets_array(file_aem, v_num*6)
                        vertices = [(x*sign_check(x, xs), y*sign_check(y, ys), z*sign_check(z, zs)) for x, xs, y, ys, z, zs in v_block]
                    if version == 1:
                        vertex_cord_size = 3
                        UV_UNIT_POINT = NORMALS_UNIT_POINT = 1/255 #(2^8)-1
                        indices_num = read_short(file_aem)
                        pre_strip_pos = file_aem.tell()
                        try: #handling sepcial case of AEM version 1 and a half
                            UV_UNIT_POINT = 1/4095
                            NORMALS_UNIT_POINT = 1/32767
                            indices = read_short_array(file_aem, indices_num)
                            t_strips_len = read_short(file_aem)
                            t_strips = read_short_array(file_aem, t_strips_len)
                            faces = triangle_strips_unpack(indices, t_strips)
                        except IndexError:
                            file_aem.seek(pre_strip_pos)
                            faces = read_short_triplets_array(file_aem, indices_num)
                        v_num = read_short(file_aem)
                        vertices = read_short_triplets_array(file_aem, v_num*3)
                    
                    if uvs_present:
                        uv_block = read_short_twins_array(file_aem, v_num*2) 
                        #print(f"UVS maximum raw value {max(uv_block)}")
                        uvs = [(u*UV_UNIT_POINT, v*UV_UNIT_POINT) for u, v in uv_block]
                    if import_normals and normals_present:
                        normals_block = read_short_triplets_array(file_aem, v_num*3)
                        normals = [(x*NORMALS_UNIT_POINT, y*NORMALS_UNIT_POINT, z*NORMALS_UNIT_POINT) for x, y, z in normals_block]
                    if unk_present:
                        try:
                            #print("some keys")
                            #print(f"vnum: {v_num}, {hex(v_num)}")
                            # file size - pos - 4*vnum*4 < 0 -> throw
                            some_twins = read_short_twins_array(file_aem, 2*v_num)
                            for i in range(0, len(some_quaternions), 5):
                                print(' '.join(f'{q}' for q in some_quaternions[i:i+5]))
                        except Exception as e:
                            print(f"quaternions loading failed: {e}")
                    
                    if version == 1:
                        is_transparent = int.from_bytes(file_aem.read(1))

                else:
                    print(f"Unsupported file AEM version: {version}")
                    return -1

                # Read BoundingSphere
                if version in (3, 4, 5):
                    bounding_sphere = unpack('<4f',file_aem.read(16))#read_float_quadruplets_array(file_aem, 4)
                    #unpack('<4f',file_aem.read(16))
                    print(f'BoundingBox: x: {bounding_sphere[0]}, y: {bounding_sphere[1]}, z: {bounding_sphere[2]}, r: {bounding_sphere[3]}')
                    
                importer_state = "BUILD_MESH"
                    
            if importer_state == "BUILD_MESH":

                obj_name = os.path.basename(file_path).split('.')[0]
                mesh = bpy.data.meshes.new(name=obj_name + "_Mesh")
                obj = bpy.data.objects.new(obj_name, mesh)
                bpy.context.collection.objects.link(obj)
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                if first_mesh:
                    root_mesh = obj
                    first_mesh = False
                else:
                    obj.parent = root_mesh
                
                mesh.from_pydata(vertices, [], faces)
                mesh.update()
                
                if uvs_present:
                    uv_layer = mesh.uv_layers.new(name="UVMap")
                    for poly in mesh.polygons:
                        for loop_index in poly.loop_indices:
                            loop_vert_index = mesh.loops[loop_index].vertex_index
                            uv_layer.data[loop_index].uv = uvs[loop_vert_index]
                
                if import_normals and normals_present:
                    mesh.normals_split_custom_set_from_vertices(normals)
                    obj.data.shade_smooth()
                
                if version in (3, 4, 5):
                    build_bounding_sphere(bounding_sphere, obj_name)
                    
                    importer_state = "READ_ANIM"
                else:
                    importer_state = "END"
                
                    
            if importer_state == "READ_ANIM": 
                print(importer_state)
                importer_state = "END"
                if version in (3, 4, 5):
                    reading_done_position = file_aem.tell()
                    
                    if (version == 3): 
                        fmt = "<4fiH"
                        fmt2 = "<2h4fH"
                    elif (version == 4):
                        fmt = "<4fi2H"#"<4f6I"
                        fmt2 = "<2h5f"
                    elif (version == 5):
                        fmt = "<4fi2H4f"
                        fmt2 = '<2h9f'
                    #file_aem.seek(-tail_len, 2)                
                    #tail_start_position = file_aem.tell()
                    
                    #bbox = unpack('<4f',file_aem.read(16))
                    tail_len = calcsize(fmt)
                    tail_bytes = file_aem.read(tail_len)
                    tail = unpack(fmt, tail_bytes)
                    tail2 = unpack(fmt2, tail_bytes)
                     
                    #if tail[2] (fps?) > 0: animation present ? 
                     
                    #print(f'BoundingBox: x: {bbox[0]}, y: {bbox[1]}, z: {bbox[2]}, r: {bbox[3]}')
                    
                    print(f'Unknown tail 1st interpetation: {tail[:5]}, {hex(tail[5])}, {tail[6:]}')  #[:-1]}, {hex(tail[-1])}')
                    print(f'Unknown tail 2nd interpetation: {tail2}')
                    #if reading_done_position != tail_start_position:
                    #    print(f'Unread data left at {hex(reading_done_position)} of size {hex(tail_start_position)}')
                    #if tail[5] != -1:
                    #   importer_state = "END"
                    if submeshes_left > 0:
                        importer_state = "READ_MESH"
                    else:
                        importer_state = "END"
                        
            if importer_state == "END":    
                if mesh_present == False:
                    return -1
                if version == 1:
                    return (version, is_transparent)
                return (root_mesh, version, normals_present, submesh_num)               
               
def export_aem(mesh, file_path, aem_version, triangulate_method):

    '''Arguments: mesh, triangulation method.
    Triangulates and splits faces of the mesh for compatibility with AEM format,
    and rotates the mesh 90 degrees clockwise around the X-axis.'''
    
    bm = bmesh.new()
    bm.from_mesh(mesh)
    rotation_matrix = Matrix.Rotation(-pi / 2, 4, 'X')
    bmesh.ops.transform(bm, matrix=rotation_matrix, verts=bm.verts)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method = triangulate_method)
    bmesh.ops.split_edges(bm, edges=bm.edges)
    bm.edges.ensure_lookup_table()

    def uv_from_vert_first(uv_layer, v):
        for l in v.link_loops:
            uv_data = l[uv_layer]
            return uv_data.uv
        return None

    def uv_from_vert_average(uv_layer, v):
        uv_average = Vector((0.0, 0.0))
        total = 0.0
        for loop in v.link_loops:
            uv_average += loop[uv_layer].uv
            total += 1.0

        if total != 0.0:
            return uv_average * (1.0 / total)
        else:
            return None

    # Example using the functions above
    uv_layer = bm.loops.layers.uv.active
    uv_per_vertex = []
    for v in bm.verts:
        uv_first = uv_from_vert_first(uv_layer, v)
        uv_per_vertex.append(uv_first)
        uv_average = uv_from_vert_average(uv_layer, v)
        print("Vertex: %r, uv_first=%r, uv_average=%r" % (v, uv_first, uv_average))
    bmnormals = []
    for v in bm.verts:
        # Custom normals are stored in the `normal` attribute of each vertex
        # But note, this is not directly "split normals" but rather the custom normal for this vertex
        bmnormals.append([*v.normal])

 
    bm.to_mesh(mesh)
    bm.free()

    
    #faces = [face.vertices for face in mesh.polygons]
    #vertices = [v.co for v in mesh.vertices]
    uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
    uvs = [uv.uv for uv in uv_layer] if uv_layer else []
    uvs = [uv.uv for uv in mesh.uv_layers.active.data]
    normals = [v.normal for v in mesh.vertices]

    # Extract vertices and faces
    #vertices = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]
    #faces = [(t.vertices[0], t.vertices[1], t.vertices[2]) for t in mesh.loop_triangles]
    #faces = [[*t.vertices] for t in mesh.loop_triangles]
    

    
    def write_short(file, value, endian='<'):
        """Writes a short integer to a binary file."""
        file.write(pack(f'{endian}h', value))

    def write_short_triplets_array(file, array, endian='<'):
        """Writes an array of 3-tuple shorts to a binary file."""
        for triplet in array:
            file.write(pack(f'{endian}hhh', *triplet))
    

    def write_float_triplets_array(file, array, endian='<'):
        """Writes an array of 3-tuple floats to a binary file."""
        for triplet in array:
            file.write(pack(f'{endian}fff', *triplet))
    

    addon_directory = os.path.dirname(os.path.abspath(__file__))
    header_file_path = os.path.join(addon_directory, 'header.bin')
    
    with open(header_file_path, 'rb') as file_header, open(file_path, 'wb') as file_aem:
        header = file_header.read(24)
        file_aem.write(header)
        

        indices = []
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                indices.append(mesh.loops[loop_index].vertex_index)
        indices_num = len(indices)
        write_short(file_aem, indices_num)
        #print(faces)
        #write_short_triplets_array(file_aem, faces)
        #print(*indices)
        file_aem.write(pack(f"{indices_num}H", *indices))
        
        vertices = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]#[*(v.co for v in mesh.vertices)]
        v_num = len(vertices)
        write_short(file_aem, v_num)
        write_float_triplets_array(file_aem, vertices)
    
        #uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
        #uvs = [uv.uv for uv in uv_layer] if uv_layer else []
        #print(*uvs)
        #for uv in uvs:
        #    file_aem.write(pack("ff", uv[0], uv[1]))
        for uv in uv_per_vertex:
            print(uv)
            if uv is not None:
                file_aem.write(pack(f"2f", uv[0],uv[1]))

        #normals = [v.normal for v in mesh.vertices]
        write_float_triplets_array(file_aem, bmnormals)   
        #file_aem.write(pack(f"{len(bmnormals)}f", *bmnormals))
        """
        processed_vertices = [False] * len(mesh.vertices)
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                if not processed_vertices[vertex_index]:
                    normal = normals[mesh.loops[loop_index].vertex_index]
                    print(normal.x, normal.y, normal.z, "\n")
                    file_aem.write(pack("fff", normal.x, normal.y, normal.z))"""
        # mesh.use_auto_smooth = True

           
        header = file_header.read(56)
        file_aem.write(header)



class ImportAEM(Operator, ImportHelper):
    """Import from AEM file format (.aem)"""
    bl_idname = "import_scene.aem"
    bl_label = "Import AEM"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".aem"

    filter_glob: StringProperty(
        default="*.aem",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    files: CollectionProperty(
        type=bpy.types.PropertyGroup
    )
    
    scale: FloatProperty(
        name="Scale Factor",
        description="Scale factor for imported objects",
        default=SCALE,
        min=0.001, max=1.0
    )
    
    import_normals: BoolProperty(
        name="Import Normals",
        description="Choose whether to import normals or not",
        default=True,
    )
    


    def execute(self, context):
        global SCALE
        SCALE = self.scale
        
        if len(self.filepath) < 1:
            print('No valid AEM provided.')
            return {'FINISHED'}
            
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        if len(self.files) > 1:
            directory = os.path.dirname(self.filepath)
            for file in self.files:
                file_path = os.path.join(directory, file.name)
                bpy.ops.object.select_all(action='DESELECT')
                root_mesh = import_aem(file_path)[0]
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active = root_mesh
                #bpy.ops.transform.rotate(value=-pi / 2, orient_axis='X')
                #bpy.ops.transform.resize(value=(SCALE,SCALE,SCALE))
                root_mesh.rotation_euler = (pi/2, 0, 0)
                root_mesh.scale = (SCALE,SCALE,SCALE)
                #bpy.ops.object.transform_apply(rotation=True, scale=True)
                #bpy.ops.object.shade_smooth()
                aem_collection = bpy.data.collections.new(os.path.basename(file_path).split('.')[0])
                bpy.context.scene.collection.children.link(aem_collection)
                for obj in bpy.context.selected_objects:
                    for coll in obj.users_collection:
                        coll.objects.unlink(obj)
                    aem_collection.objects.link(obj)

        else:
            bpy.ops.object.select_all(action='DESELECT')
            root_mesh = import_aem(self.filepath)[0]
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = root_mesh
            print(root_mesh)
            print(bpy.context.view_layer.objects.active)
            bpy.context.scene.tool_settings.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
            root_mesh.rotation_euler = (pi/2, 0, 0)
            root_mesh.scale = (SCALE,SCALE,SCALE)
            #bpy.ops.transform.rotate(value=-pi/2, orient_axis='X')
            #bpy.ops.transform.resize(value=(SCALE,SCALE,SCALE))
            #bpy.ops.object.transform_apply(rotation=True, scale=True)
            #bpy.ops.object.shade_smooth()
            
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "scale")

class ExportAEM(Operator, ExportHelper):
    """Export to AEM file format (.aem)"""
    bl_idname = "export_scene.aem"
    bl_label = "Export AEM"
    bl_options = {'UNDO'}

    filename_ext = ".aem"

    filter_glob: StringProperty(
        default="*.aem",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    aem_version: EnumProperty(
        name="AEM version",
        description="Choose exported AEM's version.",
        items=[
            ("V2AEMesh", "V2AEMesh", "Export V2AEMesh"),
            ("V5AEMesh", "V5AEMesh", "Export V5AEMesh")
        ],
        default='V5AEMesh'
    )
    
    scale: FloatProperty(
        name="Scale Factor (inverted)",
        description="Scale factor for exported objects - set the same as in import",
        default=SCALE,
        min=0.001, max=1.0
    )

    triangulate_method: EnumProperty(
        name="Triangulation Method",
        description="Method used for triangulating mesh",
        items=[
            ('BEAUTY', "Beauty", "Use Beauty method"),
            ('FIXED', "Fixed", "Use Fixed method"),
            ('ALTERNATE', "Fixed Alternate", "Use Fixed Alternate method"),
            ('SHORT_EDGE', "Shortest Diagonal", "Use Shortest Diagonal method"),
            ('LONG_EDGE', "Longest Diagonal", "Use Longest Diagonal method")
        ],
        default='BEAUTY'
    )
    
    
    add_prefix: StringProperty(
        name="Prefix",
        description="Prefix to add to exported files",
        default=""
    )

    add_suffix: StringProperty(
        name="Suffix",
        description="Suffix to add to exported files",
        default=""
    )
    

    overwrite: BoolProperty(
        name="Overwrite",
        description="Overwrite existing files",
        default=False
    )
    
    #def prepare_mesh(self, me, triangulate_method):



    def execute(self, context):
        global SCALE
        SCALE = self.scale

        directory = os.path.dirname(self.filepath)
        
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
            
        for obj in bpy.context.selected_objects:
            if not obj.data or not isinstance(obj.data, bpy.types.Mesh) or obj.type != 'MESH':
                self.report({'ERROR'}, f"Object {obj.name} does not have a mesh")
                continue

            if len(context.selected_objects) == 1:
                file_out = os.path.join(directory, self.add_prefix + os.path.splitext(os.path.basename(self.filepath))[0] + self.add_suffix + '.aem')
            else:
                file_out = os.path.join(directory, self.add_prefix + obj.name + self.add_suffix + '.aem')
            
            if ( (self.overwrite and os.path.exists(file_out) ) or (not os.path.exists(file_out)) ):
            
                mesh = obj.data.copy()
                
                #bpy.context.collection.objects.link(bpy.data.objects.new("aem_temp", mesh))
                #bpy.context.view_layer.objects.active = bpy.context.collection.objects['aem_temp']
            
                #AEM does't support quads nor higher n-gons
                '''bpy.ops.object.modifier_add(type='TRIANGULATE')
                bpy.context.object.modifiers["Triangulate"].quad_method = self.triangulate_method
                bpy.context.object.modifiers["Triangulate"].min_vertices = 4
                if self.triangulate_method == 'BEAUTY':
                    bpy.context.object.modifiers["Triangulate"].ngon_method = 'BEAUTY'
                else:
                    bpy.context.object.modifiers["Triangulate"].ngon_method = 'CLIP'       
                bpy.ops.object.modifier_apply(modifier="Triangulate")
                
                '''
                #self.prepare_mesh(mesh, self.triangulate_method)
                
                export_aem(mesh, self.filepath.replace(".aem", f"_{obj.name}.aem"), VERSION[self.aem_version+"\x00"], self.triangulate_method)
                bpy.data.meshes.remove(mesh)
            else:
                self.report({'WARNING'}, f"File {file_out} already exists and overwrite is disabled.")
    
        return {'FINISHED'}


    def write(self, context, filepath):
        export_aem(filepath)
        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(ImportAEM.bl_idname, text="Abyss Engine Mesh(.aem)")

def menu_func_export(self, context):
    self.layout.operator(ExportAEM.bl_idname, text="Abyss Engine Mesh(.aem)")

def register():
    bpy.utils.register_class(ImportAEM)
    bpy.utils.register_class(ExportAEM)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ImportAEM)
    bpy.utils.unregister_class(ExportAEM)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
