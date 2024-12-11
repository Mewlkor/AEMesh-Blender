
Structure of *.aem*:

| char magic [7] or [9]    | AEMesh   | V2AEMesh | V3AEMesh | V4AEMesh | V5AEMesh |
| ------------------------ | -------- | -------- | -------- | -------- | -------- |
| **byte** *flags*               | ✔        | ✔        | ✔        | ✔        | ✔        |
| **short** *submesh_count* (sc) | ❌ just 1 | ❌ just 1 | ✔        | ✔        | ✔        |
*mesh* \[sc] 
| &nbsp; **float** *pivot_point* \[3]               | ❌      | ❌        | ✔        | ✔        | ✔        |
| &nbsp; **short** *face_indicies_count* (fc)           | ❌      | ✔        | ✔        | ✔        | ✔        |
| &nbsp; **short** *face_indicies* \[fc/3]\[3]           | ❌      | ✔        | ✔        | ✔        | ✔        |
| &nbsp; **short** *triangle_strips_count* (tc)        | ✔      | ❌        | ❌        | ❌        | ❌        |
| &nbsp; **short** *triangle_strips* \[tc]            | ✔      | ❌        | ❌        | ❌        | ❌        |
| &nbsp; **short** *vertex_count* (vc)                  | ✔      | ✔        | ✔        | ✔        | ✔        |
| &nbsp; **TYPE** *vertices* \[3\*vc]\[3]                      | ✔ **short** | ❌        | ❌        | ✔ **float** | ✔ **float** |
| &nbsp; **short** *vertex_coord, sign* \[3\*vc]\[3]\[2] (x, y, z) (<0 or ≥0) | ❌      | ✔        | ✔        | ❌        | ❌        |
| &nbsp; **TYPE** *texture_coord* \[2\*vc]\[2] (u, v)                          | ✔ **short*** | ✔ **short**** | ✔ **short**** | ✔ **float** | ✔ **float** |             
| &nbsp; **short** *normals* \[3\*vc]\[3] (x, y, z)                | ✔ **short**\* | ✔ **short***** | ✔ **short***** | ✔ **float** | ✔ **float** |
| &nbsp; **float** *bounding_sphere* \[4] (x, y, z, radius)           | ❌      | ❌        | ❌        | ✔        | ✔        |
| &nbsp; animation keys                      | ❌      | ❌        | ✔        | ✔        | ✔        |
|

Max value: \*255, \*\*4095, \*\*\*32768

Animation data:

KeyFrame %d of %d
Time: %d
posx: %f
posy: %f
posz: %f
rotx: %f
roty: %f
rotz: %f
scax: %f
scay: %f
scaz: %f