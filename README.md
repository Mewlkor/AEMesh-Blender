
### Structure of *.aem*:

| char magic [7] or [9]    | AEMesh   | V2AEMesh | V3AEMesh | V4AEMesh | V5AEMesh |
| ------------------------ | -------- | -------- | -------- | -------- | -------- |
| **byte** *flags*               | ✔        | ✔        | ✔        | ✔        | ✔        |
| **short** *submesh_count* (sc) | ❌ just 1 | ❌ just 1 | ✔        | ✔        | ✔        |
*mesh* \[sc] 
| &nbsp; **float** *pivot_point* \[3]               | ❌      | ❌        | ✔        | ✔        | ✔        |
| &nbsp; **short** *face_indicies_count* (fc)           | ❌ / ✔**      | ✔        | ✔        | ✔        | ✔        |
| &nbsp; **short** *face_indicies* \[fc/3]\[3]           | ❌ / ✔**      | ✔        | ✔        | ✔        | ✔        |
| &nbsp; **short** *triangle_strips_count* (tc)        | ✔ / ❌**      | ❌        | ❌        | ❌        | ❌        |
| &nbsp; **short** *triangle_strips* \[tc]            | ✔ / ❌**      | ❌        | ❌        | ❌        | ❌        |
| &nbsp; **short** *vertex_count* (vc)                  | ✔       | ✔        | ✔        | ✔        | ✔        |
| &nbsp; **TYPE** *vertices* \[3\*vc]\[3]                      | ✔ **short** | ❌        | ❌        | ✔ **float** | ✔ **float** |
| &nbsp; **short** *vertex_coord, sign* \[3\*vc]\[3]\[2]$\newline$  $(x, y, z),\,(\!<\!0\;\, or ≥\!0)$ | ❌      | ✔        | ✔        | ❌        | ❌        |
| &nbsp; **TYPE** *texture_coord* \[2\*vc]\[2]$\newline$ $(u, v)$                          | ✔ **short**, Q8* / Q12** | ✔ **short**, Q12* | ✔ **short**, Q12* | ✔ **float** | ✔ **float** |             
| &nbsp; **short** *normals* \[3\*vc]\[3] $\newline$ $(x, y, z)$                | ✔ **short**, Q8* / Q15** | ✔ **short**, Q15* | ✔ **short**, Q15* | ✔ **float** | ✔ **float** |
| &nbsp; **TYPE** *unknown* \[vc][2 or 4] $\newline$ $(g, b)/(a, r, g, b)?$           | ❌      | ❔ **short**   | ✔ **short**  | ✔ **float** | ✔ **float** |
| &nbsp; **float** *bounding_sphere* \[4] $\newline$ $(x, y, z, r)$           | ❌      | ❌        | ❌        | ✔        | ✔        |
| &nbsp; *animation data*                      | ❌      | ❌        | ✔        | ✔        | ✔        |
|

\***Qn** is format of storing fixed point fractional numbers as integer in which **n** LSB (least significant bits) store fractional part, for example in Q8:\
    decimal: $24$, binary: $0001\,1000 \rightarrow {\large\frac{24}{256}} = 0.09375$, becouse $2^8=256$\
    decimal: $315$, binary: $1 \mathbf{.}0011\,1011 \rightarrow {\large\frac{315}{256}} = 1.23046875$\
    (in binary format dot $\mathbf{.}$ is just there for visual separation of integer and fractional parts)

\*\*There is rarer version of **AEMesh** similar to **V2** but without sign next to vertex coord. 

### Animation data:

KeyFrame %d of %d\
Time: %d\
posx: %f\
posy: %f\
posz: %f\
rotx: %f\
roty: %f\
rotz: %f\
scax: %f\
scay: %f\
scaz: %f