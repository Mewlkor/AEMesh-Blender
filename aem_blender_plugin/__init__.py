import bpy
import os
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, FloatProperty, EnumProperty, BoolProperty, CollectionProperty
from bpy.types import Operator
import struct
from numpy import float32, short, ushort
import bmesh
import math
from mathutils import Matrix

bl_info = {
    "name": "AEM Blender Plugin",
    "author": "Chuck Norris",
    "version": (1, 3),
    "blender": (4, 1, 0),
    "location": "File > Import-Export",
    "description": "AByss Engine Mesh V4,V5 Import / V5 Export",
    "warning": "",
    "category": "Import-Export",
}

SCALE = 0.01
NORMALS_UNIT_POINT = 1/(2<<15-1) # 1>>15

AEMflags = {
    "uvs":2, #000010  # these are Texture Coordinates if you will
    "normals":4, #000100
    "animations":8, #001000 # guess
    "faces":16 #010000
}

AEMVersion = {
    "AEMesh":1,
    "V2AEMesh":2,
    "V3AEMesh":3,
    "V4AEMesh":4,
    "V5AEMesh":5
}  

def sign_check(c, cs):
    if (cs == -1 and c < 0) or (cs == 0x0 and c >= 0):
        return 1
    return -1   

def read_float(file):
    return float32(struct.unpack('f', file.read(4))[0])
    
def read_short(file):
    return short(struct.unpack('h', file.read(2))[0])
    
'''for future optimisiation'''    
def read_short_array(file, len):
    return struct.unpack(f'{len}h', file.read(len*2))
    #list()
    
def prepare_mesh(me, triang_meth):
    '''Arguments: mesh, triangulation method.
    Triangulates and splits faces of the mesh for compatibility with AEM format,
    and rotates the mesh 90 degrees clockwise around the X-axis.'''
    
    bm = bmesh.new()
    bm.from_mesh(me)
    
    rotation_matrix = Matrix.Rotation(-math.pi / 2, 4, 'X')
    bmesh.ops.transform(bm, matrix=rotation_matrix, verts=bm.verts)
    
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method=triang_meth)
    bm.edges.ensure_lookup_table()
    bmesh.ops.split_edges(bm, edges=bm.edges)
    
    bm.to_mesh(me)
    bm.free()
    
def triangle_strips_unpack(indicies, tstrip_array):
    i = 0
    unpacked = []
    for strip in tstrip_array:
        for j in range(strip - 2):
            if j % 2 == 0:
                unpacked.append([indicies[i+j], indicies[i+j+1], indicies[i+j+2]])
            else:
                unpacked.append([indicies[i+j], indicies[i+j+2], indicies[i+j+1]])
        i += strip  
    return unpacked

def import_aem(file_path, import_normals=True):
    with open(file_path, 'rb') as file_aem:
        magic = ""
        magic_len = 0
        while magic[-4:] != "Mesh": 
            magic += file_aem.read(1).decode("utf-8")
            magic_len += 1
            if magic_len > 8:
                #self.report ...
                file_aem.close()
                print("Unsupported .aem file. Error reading header")
                return
        file_aem.read(1)
        flags = int.from_bytes(file_aem.read(1))
        normals_present = (flags & AEMflags["normals"]) != 0
        version = AEMVersion[magic]
            
        if version in (4, 5):
            file_aem.seek(0x18)
            f_num = int(read_short(file_aem) / 3)
            faces = [(read_short(file_aem), read_short(file_aem), read_short(file_aem)) for _ in range(f_num)]
            v_num = read_short(file_aem)
            vertices = [(read_float(file_aem) * SCALE, read_float(file_aem) * SCALE, read_float(file_aem) * SCALE) for _ in range(v_num)]
            print("\n\n\n vertices")
            print(vertices)
            vertices = [(x, -z, y) for x, y, z in vertices]
            uvs = [(read_float(file_aem), read_float(file_aem)) for _ in range(v_num)]
            if import_normals and normals_present:
                normals = [(read_float(file_aem), read_float(file_aem), read_float(file_aem)) for _ in range(v_num)]
                normals = [(x, -z, y) for x, y, z in normals]
                
            obj_name = os.path.basename(file_path).split('.')[0]
            mesh = bpy.data.meshes.new(name=obj_name + "_Mesh")
            obj = bpy.data.objects.new(obj_name, mesh)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            mesh.from_pydata(vertices, [], faces)
            mesh.update()

            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly in mesh.polygons:
                for loop_index in poly.loop_indices:
                    loop_vert_index = mesh.loops[loop_index].vertex_index
                    uv_layer.data[loop_index].uv = uvs[loop_vert_index]
            #for i, uv in enumerate(uvs):
             #   uv_layer.data[i].uv = uv
                
            
            if import_normals and normals_present:
                print("imported normals:")
                print(normals)
                mesh.normals_split_custom_set_from_vertices(normals)
            
        elif version in (1, 2):
            if AEMVersion[magic] == 2:
                vertex_cord_size = 6
                UV_UNIT_POINT = 1/4096 #(2<<12)
                f_num = int(read_short(file_aem) / 3)
                faces = [(read_short(file_aem), read_short(file_aem), read_short(file_aem)) for _ in range(f_num)]
            if AEMVersion[magic] == 1:
                vertex_cord_size = 3
                UV_UNIT_POINT = 1/256 #1/(2<<8) 
                f_num = read_short(file_aem)
                faces = [read_short(file_aem) for _ in range(f_num)]
                print(f_num)
                t_strips_len = read_short(file_aem)
                t_strips = [read_short(file_aem) for _ in range(t_strips_len)]
                print(t_strips)
                faces = triangle_strips_unpack(faces, t_strips)
            v_num = read_short(file_aem)
            v_block = [tuple(read_short(file_aem) for _ in range(vertex_cord_size)) for _ in range(v_num)]
            uvs = [(struct.unpack("h", file_aem.read(2))[0], struct.unpack("h", file_aem.read(2))[0]) for _ in range(v_num)]
            if import_normals and normals_present:
                normals_block = [(read_short(file_aem), read_short(file_aem), read_short(file_aem)) for _ in range(v_num)]
                        
            if version == 2:
                #if cord is negative sign bits are FFFF else they are 0000
                vertices = [(x*SCALE * sign_check(x, xs), -z*SCALE * sign_check(z, zs), y*SCALE * sign_check(y, ys)) for x, xs, y, ys, z, zs in v_block]
            if version == 1:
                vertices = [(x*SCALE, -z*SCALE, y*SCALE) for x, y, z in v_block]
            if import_normals and normals_present:
                normals = [(x*NORMALS_UNIT_POINT, -z*NORMALS_UNIT_POINT, y*NORMALS_UNIT_POINT) for x, y, z in normals_block]
            
            obj_name = os.path.basename(file_path).split('.')[0]
            mesh = bpy.data.meshes.new(name=obj_name + "_Mesh")
            obj = bpy.data.objects.new(obj_name, mesh)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            mesh.from_pydata(vertices, [], faces)
            mesh.update()

            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly in mesh.polygons:
                for loop_index in poly.loop_indices:
                    loop_vert_index = mesh.loops[loop_index].vertex_index
                    uv_layer.data[loop_index].uv = uvs[loop_vert_index]
            for uv_data in uv_layer.data:
                uv_data.uv *= UV_UNIT_POINT
            
            if import_normals and normals_present:
                mesh.normals_split_custom_set_from_vertices(normals)


        else:
            print("Unsupported file AEM version.")
            return

def export_aem(mesh, file_path, aem_version):

    faces = [face.vertices for face in mesh.polygons]
    vertices = [v.co for v in mesh.vertices]
    uvs = [uv.uv for uv in mesh.uv_layers.active.data]
    normals = [v.normal for v in mesh.vertices]

    addon_directory = os.path.dirname(os.path.abspath(__file__))
    header_file_path = os.path.join(addon_directory, 'header.bin')
    
    with open(header_file_path, 'rb') as file_header, open(file_path, 'wb') as file_aem:
        header = file_header.read(24)
        file_aem.write(header)
        
        f_num = ushort(len(faces))
        file_aem.write(struct.pack("H", f_num*3))
        for vi in faces:
            file_aem.write(struct.pack("H", vi[0] ))
            file_aem.write(struct.pack("H", vi[1] ))
            file_aem.write(struct.pack("H", vi[2] ))
        
        v_num = ushort(len(vertices))

        file_aem.write(struct.pack("H", v_num))
        for v in vertices:
            file_aem.write(struct.pack("f", v.x / SCALE))
            file_aem.write(struct.pack("f", v.y / SCALE))
            file_aem.write(struct.pack("f", v.z / SCALE))

        for i, v in enumerate(vertices):
            loop = mesh.loops[i]
            uv = mesh.uv_layers.active.data[loop.index].uv
            file_aem.write(struct.pack("ff", uv.x, uv.y))
        
        '''
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(mesh)

        for v, normal in zip(bm.verts, normals):
            v.normal = normal
        bm.to_mesh(mesh)
        bm.free()
        # Correctly set the custom normals
        # Convert vertex normals to loop normals
           '''     
        '''        processed_vertices = [False] * len(mesh.vertices)
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                if not processed_vertices[vertex_index]:
                    normal = normals[mesh.loops[loop_index].vertex_index]
                    print(normal.x, normal.y, normal.z, "\n")
                    file_aem.write(struct.pack("fff", normal.x, normal.z, -normal.y))
        # mesh.use_auto_smooth = True

        '''    

        for n in normals:
            file_aem.write(struct.pack("f", n.x))
            file_aem.write(struct.pack("f", n.y))
            file_aem.write(struct.pack("f", n.z))

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
        if len(self.files) > 1:
            directory = os.path.dirname(self.filepath)
            for file in self.files:
                file_path = os.path.join(directory, file.name)
                import_aem(file_path)
                #bpy.ops.object.mode_set(mode='EDIT')
                # Rotate the mesh in Edit Mode by 90 degrees clockwise around the X-axis
                #bpy.ops.transform.rotate(value=-math.pi / 2, orient_axis='X')
                #bpy.ops.object.mode_set(mode='OBJECT')
        else:
            import_aem(self.filepath)
            #bpy.ops.object.mode_set(mode='EDIT')
            # Rotate the mesh in Edit Mode by 90 degrees clockwise around the X-axis
            #bpy.ops.transform.rotate(value=-math.pi / 2, orient_axis='X')
            #bpy.ops.object.mode_set(mode='OBJECT')
            
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
                prepare_mesh(mesh, self.triangulate_method)
                
                export_aem(mesh, self.filepath.replace(".aem", f"_{obj.name}.aem"), AEMVersion[self.aem_version])
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
