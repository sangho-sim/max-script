bl_info = {
    "name": "Retopo Annotate (리토폴로지 주석 툴)",
    "author": "RetopoAnnotate",
    "version": (1, 5, 0),
    "blender": (4, 2, 0),
    "location": "3D 뷰 > 사이드바(N) > Retopo 탭",
    "description": "주석(Annotation)으로 리토폴로지 엣지/메쉬/컷 생성, 버텍스 익스트루드 자동 쿼드",
    "category": "Mesh",
}

import math
import time

import bmesh
import bpy
from bpy.app.handlers import persistent
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, PointerProperty)
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Matrix, Vector, kdtree
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_line_line_2d


# ---------------------------------------------------------------------------
# 주석(Annotation) 데이터 접근 - 4.5(grease_pencil) / 5.x(annotation) 호환
# ---------------------------------------------------------------------------

def _scene_ann_attr():
    props = bpy.types.Scene.bl_rna.properties
    return "annotation" if "annotation" in props.keys() else "grease_pencil"


def _ann_collection():
    if hasattr(bpy.data, "annotations"):
        return bpy.data.annotations
    return bpy.data.grease_pencils


def get_annotation(scene):
    return getattr(scene, _scene_ann_attr(), None)


def ensure_annotation(scene):
    ann = get_annotation(scene)
    if ann is None:
        ann = _ann_collection().new("Annotations")
        setattr(scene, _scene_ann_attr(), ann)
    if len(ann.layers) == 0:
        layer = ann.layers.new("Retopo")
        layer.color = (1.0, 0.35, 0.1)
    return ann


class StrokeRef:
    __slots__ = ("layer", "frame", "stroke", "points")

    def __init__(self, layer, frame, stroke, points):
        self.layer = layer
        self.frame = frame
        self.stroke = stroke
        self.points = points


def _visible_frame(layer, scene):
    frame = layer.active_frame
    if frame is not None:
        return frame
    best = None
    for fr in layer.frames:
        if fr.frame_number <= scene.frame_current and (best is None or fr.frame_number > best.frame_number):
            best = fr
    return best


def collect_strokes(scene, junk=None):
    """변환할 3D 스트로크 목록. junk 리스트를 주면 점 1개짜리(클릭) 스트로크를 따로 담음."""
    ann = get_annotation(scene)
    out = []
    if ann is None:
        return out
    for layer in ann.layers:
        if layer.annotation_hide:
            continue
        frame = _visible_frame(layer, scene)
        if frame is None:
            continue
        for s in frame.strokes:
            if getattr(s, "display_mode", "3DSPACE") != "3DSPACE":
                continue
            pts = [Vector(p.co) for p in s.points]
            if len(pts) >= 2:
                out.append(StrokeRef(layer, frame, s, pts))
            elif junk is not None:
                junk.append(StrokeRef(layer, frame, s, pts))
    return out


def stroke_count(scene):
    ann = get_annotation(scene)
    if ann is None:
        return 0
    n = 0
    for layer in ann.layers:
        frame = _visible_frame(layer, scene)
        if frame is not None and not layer.annotation_hide:
            n += len(frame.strokes)
    return n


def remove_strokes(refs):
    """변환이 끝난 스트로크 삭제. 5.2+ 는 개별 삭제, 그 이전은 프레임 단위 삭제."""
    groups = {}
    for r in refs:
        key = r.frame.as_pointer()
        groups.setdefault(key, (r.layer, r.frame, set()))[2].add(r.stroke.as_pointer())
    for layer, frame, ptrs in groups.values():
        if hasattr(frame.strokes, "remove"):
            idx = [i for i, s in enumerate(frame.strokes) if s.as_pointer() in ptrs]
            for i in reversed(idx):
                frame.strokes.remove(frame.strokes[i])
        else:
            layer.frames.remove(frame)


def clear_all_annotations(scene):
    ann = get_annotation(scene)
    if ann is None:
        return
    for layer in ann.layers:
        for fr in list(layer.frames):
            layer.frames.remove(fr)


# ---------------------------------------------------------------------------
# 폴리라인 유틸
# ---------------------------------------------------------------------------

def poly_length(pts):
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def dedupe(pts, eps=1e-6):
    out = [pts[0].copy()]
    for p in pts[1:]:
        if (p - out[-1]).length > eps:
            out.append(p.copy())
    return out


def smooth_polyline(pts, iterations=2, closed=False, fixed=()):
    pts = [p.copy() for p in pts]
    n = len(pts)
    if n < 3:
        return pts
    fixed = set(fixed)
    for _ in range(iterations):
        new = [p.copy() for p in pts]
        for i in range(n):
            if (not closed and (i == 0 or i == n - 1)) or i in fixed:
                continue
            new[i] = pts[i] * 0.5 + (pts[i - 1] + pts[(i + 1) % n]) * 0.25
        pts = new
    return pts


# ---------------------------------------------------------------------------
# 꺾임(두 오브젝트 교차선 / 모서리) 처리
#  선이 한 표면에서 다른 표면으로 넘어갈 때 두 샘플 사이 직선은 허공(오목한 모서리 앞)을 지나므로
#  두 평면의 교선 위 점을 끼워 넣고, 그 점에 반드시 버텍스가 오게 나눈다.
# ---------------------------------------------------------------------------

CREASE_ANGLE = math.radians(30)
FLAT_ANGLE = math.radians(15)


def plane_cross_point(pa, na, pb, nb):
    """두 평면(pa,na)(pb,nb) 의 교선 위에서 pa-pb 중점과 가장 가까운 점."""
    d = na.cross(nb)
    if d.length < 1e-6:
        return None
    m = (pa + pb) * 0.5
    den = na.dot(nb.cross(d))
    if abs(den) < 1e-12:
        return None
    return (na.dot(pa) * nb.cross(d) + nb.dot(pb) * d.cross(na) + d.dot(m) * na.cross(nb)) / den


def insert_creases(pts, nrms, spacing):
    """pts/nrms 사이 꺾임 점을 끼워 넣음 → (pts, nrms, [(점, 교선 방향)])."""
    if len(pts) < 2 or any(n is None for n in nrms):
        return pts, nrms, []
    op, on, cr = [pts[0]], [nrms[0]], []
    n = len(pts)
    for i in range(n - 1):
        a, b = nrms[i], nrms[i + 1]
        if a.angle(b, 0.0) > CREASE_ANGLE:
            flat_a = i == 0 or nrms[i - 1].angle(a, 0.0) < FLAT_ANGLE
            flat_b = i + 2 >= n or b.angle(nrms[i + 2], 0.0) < FLAT_ANGLE
            q = plane_cross_point(pts[i], a, pts[i + 1], b) if (flat_a and flat_b) else None
            ch = (pts[i + 1] - pts[i]).length
            if q is not None and (q - (pts[i] + pts[i + 1]) * 0.5).length < max(ch * 1.5, spacing * 0.5) \
                    and all((q - c[0]).length > spacing * 0.5 for c in cr):
                op.append(q)
                on.append((a + b).normalized())
                cr.append((q.copy(), a.cross(b).normalized()))
        op.append(pts[i + 1])
        on.append(nrms[i + 1])
    return op, on, cr


def snap_grid_creases(grid, proj):
    """그리드 안쪽 점 중 꺾이는 곳(두 표면 교차선) 바로 옆 점을 교선 위로 옮김
    → 채우기 면이 오목한 모서리를 가로질러 허공에 뜨지 않음."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if rows < 3 or cols < 3 or not proj.ok:
        return grid
    hn = [[proj.normal(p) for p in row] for row in grid]
    moves = []
    for j in range(1, rows - 1):
        for i in range(1, cols - 1):
            p, n_p = grid[j][i], hn[j][i]
            if n_p is None:
                continue
            best = None
            for jj, ii in ((j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1)):
                q, n_q = grid[jj][ii], hn[jj][ii]
                if n_q is None or n_p.angle(n_q, 0.0) <= CREASE_ANGLE:
                    continue
                x = plane_cross_point(p, n_p, q, n_q)
                if x is None:
                    continue
                dp = (p - x).length
                dq = (q - x).length
                if dq < (p - q).length * 0.15:
                    continue  # 이웃이 이미 교차선 위 → 이 점은 옮기지 않음 (옮기면 쿼드가 찌그러짐)
                if dp <= dq and dp < (p - q).length * 0.75 and (best is None or dp < best[0]):
                    best = (dp, x)
            if best:
                moves.append((j, i, best[1]))
    for j, i, x in moves:
        grid[j][i] = x
    return grid


def best_quad_order(q, cos, proj, spacing):
    """쿼드는 첫 버텍스에서 대각선(0-2)으로 삼각형이 나뉨. 꺾이는 곳에서 1-3 대각선이 표면에 더 잘
    붙으면 순서를 한 칸 돌려 그 대각선으로 나뉘게 함 (쿼드는 그대로)."""
    if len(q) != 4 or not proj.ok:
        return q
    p = cos

    def tf(a, b, c):
        return proj.distance((a + b + c) / 3.0) if (b - a).cross(c - a).length > 1e-12 else 0.0
    d02 = max(tf(p[0], p[1], p[2]), tf(p[0], p[2], p[3]))
    d13 = max(tf(p[0], p[1], p[3]), tf(p[1], p[2], p[3]))
    if d13 < d02 * 0.7 and d02 - d13 > spacing * 0.02:
        return (q[1], q[2], q[3], q[0])
    return q


def anchor_indices(pts, creases):
    if not creases:
        return []
    out = []
    for i in range(1, len(pts) - 1):
        if any((pts[i] - c[0]).length < 1e-6 for c in creases):
            out.append(i)
    return out


def crease_at(p, creases):
    for c in creases:
        if (p - c[0]).length < 1e-6:
            return c
    return None


def resample_anchored(pts, nseg, creases):
    """resample 과 같지만 꺾임 점마다 반드시 버텍스가 오도록 구간별로 나눔."""
    cuts = anchor_indices(pts, creases)
    nseg = max(1, int(nseg))
    if not cuts or nseg < len(cuts) + 1:
        return resample(pts, nseg)
    bounds = [0] + cuts + [len(pts) - 1]
    pieces = [pts[bounds[k]:bounds[k + 1] + 1] for k in range(len(bounds) - 1)]
    lens = [max(poly_length(p), 1e-9) for p in pieces]
    total = sum(lens)
    segs = [max(1, round(nseg * L / total)) for L in lens]
    while sum(segs) > nseg:
        k = max(range(len(segs)), key=lambda i: segs[i] if segs[i] > 1 else -1)
        if segs[k] <= 1:
            break
        segs[k] -= 1
    while sum(segs) < nseg:
        k = max(range(len(segs)), key=lambda i: lens[i] / segs[i])
        segs[k] += 1
    out = []
    for k, p in enumerate(pieces):
        r = resample(p, segs[k])
        out += r if k == 0 else r[1:]
    return out


def resample(pts, nseg):
    """열린 폴리라인을 호 길이 기준으로 nseg 등분 (nseg+1 점)."""
    nseg = max(1, int(nseg))
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + (pts[i + 1] - pts[i]).length)
    total = cum[-1]
    if total < 1e-12 or len(pts) < 2:
        return [pts[0].copy() for _ in range(nseg + 1)]
    out = []
    j = 0
    for k in range(nseg + 1):
        t = total * k / nseg
        while j < len(pts) - 2 and cum[j + 1] < t:
            j += 1
        seg = cum[j + 1] - cum[j]
        f = 0.0 if seg < 1e-12 else (t - cum[j]) / seg
        out.append(pts[j].lerp(pts[j + 1], min(max(f, 0.0), 1.0)))
    return out


def is_closed_stroke(pts, spacing):
    length = poly_length(pts)
    if length < spacing * 3:
        return False
    gap = (pts[0] - pts[-1]).length
    return gap < max(spacing * 1.5, length * 0.18)


def find_corners(dense):
    """닫힌 루프에서 모서리 4개 인덱스 찾기 (부족하면 가장 긴 변을 분할)."""
    n = len(dense)
    k = max(2, n // 24)
    ang = []
    for i in range(n):
        a = dense[i] - dense[i - k]
        b = dense[(i + k) % n] - dense[i]
        if a.length < 1e-12 or b.length < 1e-12:
            ang.append(0.0)
        else:
            ang.append(a.angle(b, 0.0))
    order = sorted(range(n), key=lambda i: -ang[i])
    picked = []
    minsep = max(1, n // 8)
    for i in order:
        if ang[i] < math.radians(35):
            break
        if all(min(abs(i - j), n - abs(i - j)) >= minsep for j in picked):
            picked.append(i)
        if len(picked) == 4:
            break
    if not picked:
        picked = [0]
    picked.sort()
    while len(picked) < 4:
        best_gap, best_i = -1, 0
        for i in range(len(picked)):
            a = picked[i]
            b = picked[(i + 1) % len(picked)] + (n if i == len(picked) - 1 else 0)
            if b - a > best_gap:
                best_gap, best_i = b - a, i
        mid = (picked[best_i] + best_gap // 2) % n
        picked.append(mid)
        picked.sort()
    return picked


def coons_grid(B, R, T, L):
    """B:아래(c00→c10) R:오른쪽(c10→c11) T:위(c01→c11) L:왼쪽(c00→c01)."""
    a = len(B) - 1
    b = len(R) - 1
    c00, c10, c01, c11 = B[0], B[a], T[0], T[a]
    grid = []
    for j in range(b + 1):
        v = j / b
        row = []
        for i in range(a + 1):
            u = i / a
            if j == 0:
                p = B[i]
            elif j == b:
                p = T[i]
            elif i == 0:
                p = L[j]
            elif i == a:
                p = R[j]
            else:
                p = ((1 - v) * B[i] + v * T[i] + (1 - u) * L[j] + u * R[j]
                     - ((1 - u) * (1 - v) * c00 + u * (1 - v) * c10
                        + (1 - u) * v * c01 + u * v * c11))
            row.append(p.copy())
        grid.append(row)
    return grid


# ---------------------------------------------------------------------------
# 타겟(하이폴리) 표면 투영
# ---------------------------------------------------------------------------

_bvh_cache = {"key": None, "bvh": None}


def target_objects(st):
    """타겟 메쉬 목록: 오브젝트 1개, 또는 컬렉션(하위 컬렉션 포함) 안의 보이는 메쉬 전부."""
    if st.target_type == 'COLLECTION':
        col = st.target_collection
        if col is None:
            return []
        out = []
        for o in col.all_objects:
            if o.type != 'MESH' or o == st.retopo:
                continue
            try:
                if not o.visible_get():
                    continue
            except RuntimeError:
                pass  # 현재 뷰 레이어에 없는 오브젝트
            out.append(o)
        return out
    return [st.target] if st.target is not None and st.target.type == 'MESH' else []


def has_target(st):
    return bool(target_objects(st))


class Projector:
    """타겟 표면 투영/레이캐스트. target 은 오브젝트, 오브젝트 목록, 또는 설정(st)."""

    def __init__(self, context, target, offset=0.0):
        self.ok = False
        self.offset = offset
        if isinstance(target, RetopoAnnotSettings):
            objs = target_objects(target)
        elif target is None:
            objs = []
        elif isinstance(target, (list, tuple)):
            objs = [o for o in target if o is not None and o.type == 'MESH']
        else:
            objs = [target] if target.type == 'MESH' else []
        if not objs:
            return
        key = tuple((o.name, o.data.name, len(o.data.vertices), len(o.modifiers),
                     tuple(round(x, 5) for row in o.matrix_world for x in row)) for o in objs)
        if _bvh_cache["key"] != key:
            dg = context.evaluated_depsgraph_get()
            if len(objs) == 1:
                _bvh_cache["bvh"] = BVHTree.FromObject(objs[0], dg)
                _bvh_cache["mw"] = objs[0].matrix_world.copy()
            else:
                # 여러 오브젝트를 월드 좌표 하나의 BVH 로 합침
                verts, polys = [], []
                for o in objs:
                    ev = o.evaluated_get(dg)
                    me = ev.to_mesh()
                    mw = o.matrix_world
                    base = len(verts)
                    verts.extend(mw @ v.co for v in me.vertices)
                    polys.extend(tuple(base + i for i in p.vertices) for p in me.polygons)
                    ev.to_mesh_clear()
                _bvh_cache["bvh"] = BVHTree.FromPolygons(verts, polys)
                _bvh_cache["mw"] = Matrix.Identity(4)
            _bvh_cache["key"] = key
        self.bvh = _bvh_cache["bvh"]
        self.mw = _bvh_cache["mw"].copy()
        self.mwi = self.mw.inverted()
        self.nm = self.mw.to_3x3().inverted().transposed()
        self.ok = True

    def project(self, co):
        if not self.ok:
            return co.copy()
        loc, nor, _i, _d = self.bvh.find_nearest(self.mwi @ co)
        if loc is None:
            return co.copy()
        n = (self.nm @ nor).normalized()
        return self.mw @ loc + n * self.offset

    def ray(self, origin, direction, dist=1.0e9):
        """월드 좌표 레이 → 타겟 표면의 첫 교차점(월드) 또는 None."""
        if not self.ok:
            return None
        d = (self.mwi.to_3x3() @ direction)
        if d.length < 1e-12:
            return None
        loc, _nor, _i, _d = self.bvh.ray_cast(self.mwi @ origin, d.normalized(), dist)
        return None if loc is None else self.mw @ loc

    def distance(self, co):
        if not self.ok:
            return 0.0
        loc, _nor, _i, _d = self.bvh.find_nearest(self.mwi @ co)
        return 1.0e9 if loc is None else (self.mw @ loc - co).length

    def normal(self, co):
        if not self.ok:
            return None
        loc, nor, _i, _d = self.bvh.find_nearest(self.mwi @ co)
        if loc is None:
            return None
        return (self.nm @ nor).normalized()


def invalidate_bvh():
    _bvh_cache["key"] = None
    _bvh_cache["bvh"] = None


# ---------------------------------------------------------------------------
# BMesh 유틸
# ---------------------------------------------------------------------------

def edge_between(a, b):
    for e in a.link_edges:
        if e.other_vert(a) is b:
            return e
    return None


def open_edges(v):
    return [e for e in v.link_edges if len(e.link_faces) < 2 and not e.hide]


def quad_ok(cos):
    """보타이(꼬인) 쿼드/면적 0 방지. 오목 1곳까지는 허용."""
    n = (cos[2] - cos[0]).cross(cos[3] - cos[1])
    if n.length < 1e-12:
        return False
    neg = 0
    for i in range(4):
        e1 = cos[(i + 1) % 4] - cos[i]
        e2 = cos[(i + 2) % 4] - cos[(i + 1) % 4]
        if e1.cross(e2).dot(n) <= 0:
            neg += 1
    return neg <= 1


def winding_vs_neighbors(order):
    """order 순서로 면을 만들 때, 인접 면과 방향이 같으면 +, 반대면 -."""
    same = opp = 0
    m = len(order)
    for i in range(m):
        p, q = order[i], order[(i + 1) % m]
        e = edge_between(p, q)
        if e is None:
            continue
        for lf in e.link_faces:
            for loop in lf.loops:
                if loop.edge is e:
                    if loop.vert is p:
                        same += 1
                    else:
                        opp += 1
    return same, opp


def orient_new_face(face, mw, proj):
    """인접 면이 있으면 그 방향에 맞추고, 없으면 타겟 표면 노멀에 맞춤."""
    same = opp = 0
    for loop in face.loops:
        e = loop.edge
        for lf in e.link_faces:
            if lf is face:
                continue
            for l2 in lf.loops:
                if l2.edge is e:
                    if l2.vert is loop.vert:
                        same += 1
                    else:
                        opp += 1
    if same > opp:
        face.normal_flip()
        return
    if same == 0 and opp == 0 and proj is not None and proj.ok:
        face.normal_update()
        c = mw @ face.calc_center_median()
        sn = proj.normal(c)
        if sn is not None:
            wn = (mw.to_3x3().inverted().transposed() @ face.normal)
            if wn.dot(sn) < 0:
                face.normal_flip()


def weld_to_existing(bm, new_verts, dist, exclude=()):
    newset = set(new_verts) | set(exclude)
    existing = [v for v in bm.verts if v not in newset and not v.hide and v.is_valid]
    if not existing or dist <= 0:
        return []
    kd = kdtree.KDTree(len(existing))
    for i, v in enumerate(existing):
        kd.insert(v.co, i)
    kd.balance()
    targetmap = {}
    for v in new_verts:
        if not v.is_valid:
            continue
        co, i, d = kd.find(v.co)
        if i is not None and d <= dist:
            targetmap[v] = existing[i]
    if targetmap:
        bmesh.ops.weld_verts(bm, targetmap=targetmap)
    return list(targetmap.values())


class MeshAccess:
    """오브젝트 모드/에디트 모드 모두에서 bmesh 편집."""

    def __init__(self, obj):
        self.obj = obj
        self.edit = (obj.mode == 'EDIT')
        if self.edit:
            self.bm = bmesh.from_edit_mesh(obj.data)
        else:
            self.bm = bmesh.new()
            self.bm.from_mesh(obj.data)
        self.bm.verts.ensure_lookup_table()

    def commit(self):
        if self.edit:
            self.bm.normal_update()
            bmesh.update_edit_mesh(self.obj.data, loop_triangles=True, destructive=True)
        else:
            self.bm.to_mesh(self.obj.data)
            self.bm.free()
            self.obj.data.update()


# ---------------------------------------------------------------------------
# 자동 쿼드 채우기 (버텍스 익스트루드 → 인접 4버텍스로 면 생성)
# ---------------------------------------------------------------------------

def fill_spike_quads(bm, seeds, mw, proj):
    """익스트루드된 '가시' 버텍스 s(부모 p) 옆에 이웃 n, n의 가시 m 이 있으면 (p,n,m,s) 면 생성."""
    created = []
    for s in seeds:
        if not s.is_valid or len(s.link_edges) != 1:
            continue
        es = s.link_edges[0]
        if es.link_faces:
            continue
        p = es.other_vert(s)
        dir_s = s.co - p.co
        if dir_s.length < 1e-9:
            continue
        best = None
        for en in open_edges(p):
            n = en.other_vert(p)
            if n is s:
                continue
            for em in open_edges(n):
                m = em.other_vert(n)
                if m is p or m is s or edge_between(m, s) or edge_between(m, p):
                    continue
                dir_m = m.co - n.co
                if dir_m.length < 1e-9:
                    continue
                par = dir_m.normalized().dot(dir_s.normalized())
                if par < 0.3:
                    continue
                side = (p.co - n.co)
                if side.length < 1e-9:
                    continue
                ang = dir_m.angle(side, 0.0)
                if not (math.radians(25) < ang < math.radians(155)):
                    continue
                order = [p, n, m, s]
                if not quad_ok([v.co for v in order]):
                    continue
                same, opp = winding_vs_neighbors(order[:3])
                if same and opp:
                    continue
                if best is None or par > best[0]:
                    best = (par, order, same)
        if best is None:
            continue
        _par, order, same = best
        if same:
            order = list(reversed(order))
        try:
            bm.edges.new((order[2], order[3]) if not same else (order[0], order[1]))
        except ValueError:
            pass
        try:
            f = bm.faces.new(order)
        except ValueError:
            continue
        orient_new_face(f, mw, proj)
        created.append(f)
    return created


def fill_quad_cycles(bm, seeds, mw, proj):
    """엣지로 닫힌 4-버텍스 루프(면 없음)를 찾아 쿼드 생성."""
    created = []
    seen = set()
    for v in seeds:
        if not v.is_valid:
            continue
        for e1 in open_edges(v):
            a = e1.other_vert(v)
            for e2 in open_edges(a):
                if e2 is e1:
                    continue
                b = e2.other_vert(a)
                if b is v:
                    continue
                for e3 in open_edges(b):
                    if e3 is e2:
                        continue
                    c = e3.other_vert(b)
                    if c is v or c is a:
                        continue
                    e4 = edge_between(c, v)
                    if e4 is None or len(e4.link_faces) >= 2:
                        continue
                    key = frozenset((v, a, b, c))
                    if key in seen:
                        continue
                    seen.add(key)
                    order = [v, a, b, c]
                    if bm.faces.get(order) is not None:
                        continue
                    if edge_between(v, b) or edge_between(a, c):
                        continue
                    if not quad_ok([x.co for x in order]):
                        continue
                    same, opp = winding_vs_neighbors(order)
                    if same and opp:
                        continue
                    if same:
                        order.reverse()
                    try:
                        f = bm.faces.new(order)
                    except ValueError:
                        continue
                    orient_new_face(f, mw, proj)
                    created.append(f)
    return created


def auto_fill(bm, seeds, mw, proj):
    faces = fill_spike_quads(bm, seeds, mw, proj)
    faces += fill_quad_cycles(bm, [v for v in seeds if v.is_valid], mw, proj)
    return faces


# ---------------------------------------------------------------------------
# 주석 → 메쉬 변환기
# ---------------------------------------------------------------------------

def find_view3d(context):
    """(area, region, rv3d) - 현재 컨텍스트 우선, 없으면 가장 큰 3D 뷰."""
    area = context.area
    if area is not None and area.type == 'VIEW_3D':
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region is not None:
            return area, region, area.spaces.active.region_3d
    best = None
    screen = context.screen or (context.window.screen if context.window else None)
    if screen is None:
        return None, None, None
    for a in screen.areas:
        if a.type != 'VIEW_3D':
            continue
        if best is None or a.width * a.height > best.width * best.height:
            best = a
    if best is None:
        return None, None, None
    region = next((r for r in best.regions if r.type == 'WINDOW'), None)
    return best, region, best.spaces.active.region_3d


def ensure_retopo_object(context):
    st = context.scene.retopo_annot
    obj = st.retopo
    if obj is not None and obj.name in context.scene.objects and obj.type == 'MESH':
        return obj
    if st.target_type == 'COLLECTION' and st.target_collection is not None:
        base = st.target_collection.name
    else:
        base = st.target.name if st.target else "Mesh"
    me = bpy.data.meshes.new("Retopo_" + base)
    obj = bpy.data.objects.new("Retopo_" + base, me)
    context.scene.collection.objects.link(obj)
    obj.show_in_front = st.show_in_front
    obj.show_wire = True
    obj.color = (0.2, 0.6, 1.0, 1.0)
    st.retopo = obj
    return obj


def wire_loop_from(bm, start):
    """start 에서 면 없는 엣지만 따라가 닫힌 루프면 버텍스 목록 반환."""
    loop = [start]
    seen = {start}
    prev, cur = None, start
    while len(loop) < 5000:
        wires = [e for e in cur.link_edges if not e.link_faces]
        if len(wires) != 2:
            return None
        nxts = [e.other_vert(cur) for e in wires if e.other_vert(cur) is not prev]
        if not nxts:
            return None
        n = nxts[0]
        if n is start:
            return loop if len(loop) >= 4 else None
        if n in seen:
            return None
        loop.append(n)
        seen.add(n)
        prev, cur = cur, n
    return None


class Converter:
    def __init__(self, context, region=None, rv3d=None, obj=None):
        self.context = context
        self.st = context.scene.retopo_annot
        self.region = region
        self.rv3d = rv3d
        self.obj = obj if obj is not None else ensure_retopo_object(context)
        self.mw = self.obj.matrix_world.copy()
        self.mwi = self.mw.inverted()
        sc = self.mw.to_scale()
        self.scale = max((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0, 1e-9)
        self.proj = Projector(context, self.st, self.st.surface_offset)
        self.d = max(self.st.spacing, 1e-4)
        self.count = self.st.density_mode == 'COUNT'
        self.merge = min(self.st.merge_dist, self.d * 0.45)
        self.stats = {"edges": 0, "fills": 0, "lofts": 0, "cuts": 0, "faces": 0,
                      "strips": 0, "extrudes": 0, "contours": 0}
        self.creases = []  # (점, 교선 방향) - 이 점들에는 반드시 버텍스가 옴

    # --- 선택 ---
    @staticmethod
    def select_only(bm, verts):
        for f in bm.faces:
            f.select = False
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        vs = set(v for v in verts if v.is_valid)
        for v in vs:
            v.select = True
            for e in v.link_edges:
                if e.other_vert(v) in vs:
                    e.select = True

    @staticmethod
    def selected_chain(bm):
        """선택된 버텍스가 경계/와이어 엣지로 이어진 한 줄(또는 루프)이면 (순서 목록, 닫힘) 반환."""
        sel = [v for v in bm.verts if v.select and not v.hide]
        if len(sel) < 2:
            return None
        sset = set(sel)
        adj = {v: [] for v in sel}
        for v in sel:
            for e in v.link_edges:
                o = e.other_vert(v)
                if o in sset and len(e.link_faces) < 2:
                    adj[v].append(o)
        if any(len(n) == 0 or len(n) > 2 for n in adj.values()):
            return None
        ends = [v for v in sel if len(adj[v]) == 1]
        closed = not ends
        if not closed and len(ends) != 2:
            return None
        start = sel[0] if closed else ends[0]
        order, prev, cur = [start], None, start
        while True:
            nxt = [o for o in adj[cur] if o is not prev]
            if not nxt or nxt[0] is start:
                break
            prev, cur = cur, nxt[0]
            order.append(cur)
            if len(order) > len(sel):
                return None
        if len(order) != len(sel) or (closed and len(order) < 3):
            return None
        return order, closed

    @staticmethod
    def wire_component(verts):
        """버텍스들에서 면 없는 엣지로 이어진 전체 줄."""
        seen = set()
        stack = [v for v in verts if v.is_valid]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            for e in v.link_edges:
                if not e.link_faces:
                    stack.append(e.other_vert(v))
        return list(seen)

    # --- 준비 ---
    def prep(self, pts):
        pts = dedupe(pts, 1e-6)
        if len(pts) < 2:
            return None
        if self.proj.ok and self.st.snap_creases:
            nrms = [self.proj.normal(p) for p in pts]
            pts, _n, cr = insert_creases(pts, nrms, self.d)
            self.creases += cr
            return smooth_polyline(pts, 2, fixed=anchor_indices(pts, cr))
        return smooth_polyline(pts, 2)

    def view_hint(self, center):
        if self.rv3d is None:
            return None
        vi = self.rv3d.view_matrix.inverted()
        if self.rv3d.is_perspective:
            return (vi.translation - center).normalized()
        return (vi.to_3x3() @ Vector((0, 0, 1))).normalized()

    # --- 생성 ---
    def add_chain(self, bm, pts, closed):
        length = poly_length(pts + ([pts[0]] if closed else []))
        n = self.st.count_edge if self.count else max(1, round(length / self.d))
        if closed:
            rs = resample(pts + [pts[0]], max(3, n))[:-1]
        else:
            rs = resample_anchored(pts, n, self.creases)
        rs = [self.proj.project(p) for p in rs]
        vs = [bm.verts.new(self.mwi @ p) for p in rs]
        for i in range(len(vs) - 1):
            bm.edges.new((vs[i], vs[i + 1]))
        if closed and len(vs) > 2:
            bm.edges.new((vs[-1], vs[0]))
        kept = []
        if not closed and len(vs) > 2:
            # 손으로 그은 선 끝은 딱 맞지 않으므로 끝점은 엣지 길이 정도 안의 버텍스에 붙임
            kept += weld_to_existing(bm, [vs[0], vs[-1]], self.d * 0.9 / self.scale, exclude=vs)
        kept += weld_to_existing(bm, [v for v in vs if v.is_valid], self.merge / self.scale)
        self.stats["edges"] += 1
        out = [v for v in vs if v.is_valid] + kept
        self.select_only(bm, self.wire_component(out))  # 다음 선이 이 줄에서 연장되도록 선택
        return out

    def close_wire_loops(self, bm, verts):
        """새 엣지가 기존 엣지와 이어져 닫힌 루프가 되면 그 안을 쿼드로 채움."""
        done = set()
        for v in verts:
            if not v.is_valid or v in done:
                continue
            loop = wire_loop_from(bm, v)
            if not loop:
                continue
            done.update(loop)
            pts = [self.mw @ x.co for x in loop]
            bmesh.ops.delete(bm, geom=loop, context='VERTS')
            self.fill_loop(bm, pts)
            self.stats["edges"] -= 1

    def build_grid(self, bm, grid):
        b = len(grid) - 1
        a = len(grid[0]) - 1
        P = self.proj
        grid = [[P.project(p) for p in row] for row in grid]
        for _ in range(self.st.relax_iterations):
            for j in range(1, b):
                for i in range(1, a):
                    grid[j][i] = (grid[j - 1][i] + grid[j + 1][i] + grid[j][i - 1] + grid[j][i + 1]) * 0.25
            for j in range(1, b):
                for i in range(1, a):
                    grid[j][i] = P.project(grid[j][i])
        if self.st.snap_creases:
            grid = snap_grid_creases(grid, P)
        verts = [[bm.verts.new(self.mwi @ p) for p in row] for row in grid]
        faces = []
        for j in range(b):
            for i in range(a):
                q = (verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i])
                if self.st.snap_creases:
                    q = best_quad_order(q, [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]],
                                        P, self.d)
                try:
                    faces.append(bm.faces.new(q))
                except ValueError:
                    pass
        # 방향 맞추기: 면마다 타겟 노멀(없으면 뷰 방향)과 비교해 다수결
        if faces and self.faces_point_inward(faces):
            for f in faces:
                f.normal_flip()
        flat = [v for row in verts for v in row]
        boundary = [v for v in flat if v.is_boundary]
        weld_to_existing(bm, boundary, self.merge / self.scale)
        self.stats["faces"] += len(faces)
        self.last_grid = verts
        return faces

    def faces_point_inward(self, faces):
        """면 노멀이 타겟 표면 노멀(없으면 뷰 방향)과 반대인 면이 더 많으면 True.
        원통을 한 바퀴 도는 링처럼 노멀 합이 0 이 되는 경우에도 정확하도록 면마다 비교."""
        nm = self.mw.to_3x3().inverted().transposed()
        good = bad = 0
        for f in faces:
            f.normal_update()
            c = self.mw @ f.calc_center_median()
            ref = self.proj.normal(c) if self.proj.ok else self.view_hint(c)
            if ref is None:
                continue
            if (nm @ f.normal).dot(ref) >= 0:
                good += 1
            else:
                bad += 1
        return bad > good

    # --- Strokes 방식: 선택한 엣지 줄/루프를 그은 선까지 쿼드로 연장 ---
    def bridge(self, bm, chain, closed, target_pts):
        """chain(기존 버텍스) → target_pts(월드 좌표, chain 과 같은 개수) 사이를 쿼드로 채움."""
        A = [self.mw @ v.co for v in chain]
        B = list(target_pts)
        k = len(A)
        if closed:
            best = None
            for rev in (False, True):
                BB = list(reversed(B)) if rev else B
                for off in range(k):
                    s = sum((A[i] - BB[(i + off) % k]).length for i in range(k))
                    if best is None or s < best[0]:
                        best = (s, [BB[(i + off) % k] for i in range(k)])
            B = best[1]
        elif (A[0] - B[0]).length + (A[-1] - B[-1]).length > (A[0] - B[-1]).length + (A[-1] - B[0]).length:
            B.reverse()
        avg = sum((A[i] - B[i]).length for i in range(k)) / k
        m = self.st.count_v if self.count else max(1, round(avg / self.d))
        rows = [list(chain)]
        for j in range(1, m + 1):
            t = j / m
            rows.append([bm.verts.new(self.mwi @ self.proj.project(A[i].lerp(B[i], t))) for i in range(k)])
        cols = k if closed else k - 1
        # 방향 판정은 면을 만들기 전에 (새 면을 이웃으로 세지 않도록)
        same, opp = winding_vs_neighbors([rows[0][0], rows[0][1 % k], rows[1][1 % k], rows[1][0]])
        faces = []
        for j in range(m):
            for i in range(cols):
                i2 = (i + 1) % k
                try:
                    faces.append(bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i])))
                except ValueError:
                    pass
        if faces:
            flip = same > opp
            if same == 0 and opp == 0:
                flip = self.faces_point_inward(faces)
            if flip:
                for f in faces:
                    f.normal_flip()
        far = rows[-1]
        side = [rows[j][0] for j in range(1, m)] + ([rows[j][-1] for j in range(1, m)] if not closed else [])
        weld_to_existing(bm, far + side, self.merge / self.scale, exclude=[v for r in rows[1:] for v in r])
        self.select_only(bm, [v for v in far if v.is_valid])
        self.stats["extrudes"] += 1
        self.stats["faces"] += len(faces)
        return faces

    def try_extrude(self, bm, pts):
        """선택된 엣지 줄이 있고 새 선이 그 끝에 이어지지 않으면 → 선택을 선까지 연장."""
        sel = self.selected_chain(bm)
        if not sel:
            return False
        chain, closed = sel
        pclosed = is_closed_stroke(pts, self.d)
        if closed != pclosed:
            return False
        if not closed:
            join = max(self.d * 2.5, self.merge * 2)
            ends = (self.mw @ chain[0].co, self.mw @ chain[-1].co)
            if any((pts[0] - e).length < join or (pts[-1] - e).length < join for e in ends):
                return False  # 선택 줄의 끝에서 이어 그림 → 엣지 연장으로 처리
            B = resample_anchored(pts, len(chain) - 1, self.creases)
        else:
            p = pts[:-1]
            B = resample(smooth_polyline(p, 2, closed=True) + [p[0]], len(chain))[:-1]
        self.bridge(bm, chain, closed, B)
        return True

    # --- PolyStrips: 폭이 있는 쿼드 띠 ---
    def find_attach_edge(self, bm, p, w):
        best = None
        for e in bm.edges:
            if len(e.link_faces) != 1 or e.hide:
                continue
            a, b = self.mw @ e.verts[0].co, self.mw @ e.verts[1].co
            d = ((a + b) * 0.5 - p).length
            if d < w * 0.75 and (best is None or d < best[0]):
                best = (d, e.verts[0], e.verts[1], (a - b).length)
        return best[1:] if best else None

    def polystrip(self, bm, pts):
        w = self.st.strip_width if self.st.strip_width > 0 else self.d
        att = [self.find_attach_edge(bm, pts[0], w), self.find_attach_edge(bm, pts[-1], w)]
        for a in att:
            if a:
                w = a[2]  # 붙는 면의 폭을 이어받음
                break
        L = poly_length(pts)
        n = self.st.count_edge if self.count else max(1, round(L / self.d))
        raw = resample_anchored(pts, n, self.creases)
        rs = [self.proj.project(p) for p in raw]
        rowA, rowB = [], []
        for i, c in enumerate(rs):
            t = rs[min(i + 1, n)] - rs[max(i - 1, 0)]
            nrm = self.proj.normal(c) or self.view_hint(c) or Vector((0, 0, 1))
            s = t.cross(nrm)
            s = s.normalized() if s.length > 1e-12 else Vector((1, 0, 0))
            hw = w * 0.5
            cr = crease_at(raw[i], self.creases)
            if cr is not None and 0 < i < n:
                # 꺾임 점: 폭 방향을 교선 방향으로 → 양쪽 버텍스도 교선 위에 놓임.
                # 방향 부호는 바로 앞 줄(한 표면 위)에 맞추고, 비스듬히 지나가면 폭이 줄지 않게 늘림
                c = raw[i]
                prev = rowB[-1] - rowA[-1]
                d = cr[1] if cr[1].dot(prev) >= 0 else -cr[1]
                t1 = (rs[i] - rs[i - 1]).normalized()
                t2 = (rs[i + 1] - rs[i]).normalized()
                sin_t = (t1.cross(d).length + t2.cross(d).length) * 0.5
                hw = hw / max(sin_t, 0.4)
                s = d
            elif rowA and s.dot(rowB[-1] - rowA[-1]) < 0:
                s = -s  # 앞 줄과 좌우가 뒤바뀌지 않게
            rowA.append(c - s * hw)
            rowB.append(c + s * hw)
        self.build_grid(bm, [rowA, rowB])
        verts = self.last_grid
        for col, a in ((0, att[0]), (n, att[1])):
            if not a:
                continue
            ca, cb = verts[0][col], verts[1][col]
            if not (ca.is_valid and cb.is_valid):
                continue
            va, vb = a[0], a[1]
            if (ca.co - va.co).length + (cb.co - vb.co).length > (ca.co - vb.co).length + (cb.co - va.co).length:
                va, vb = vb, va
            bmesh.ops.weld_verts(bm, targetmap={ca: va, cb: vb})
        self.select_only(bm, [])
        self.stats["strips"] += 1

    # --- Contours: 원통형(팔/다리 등)을 가로지르는 선 → 둘레 링 ---
    def is_contour_stroke(self, pts):
        if not self.proj.ok or self.rv3d is None or len(pts) < 6:
            return False
        tol = max(self.d * 0.5, poly_length(pts) * 0.02)
        on = [self.proj.distance(p) < tol for p in pts]
        k = max(1, len(pts) // 10)
        return (not any(on[:k])) and (not any(on[-k:])) and sum(on) >= len(pts) * 0.25

    def contour_ring(self, pts):
        view = self.view_hint(pts[len(pts) // 2])
        if view is None:
            return None
        tol = max(self.d * 0.5, poly_length(pts) * 0.02)
        onpts = [p for p in pts if self.proj.distance(p) < tol]
        if len(onpts) < 2:
            return None
        u = pts[-1] - pts[0]
        u -= view * u.dot(view)
        if u.length < 1e-9:
            return None
        u.normalize()
        v = view - u * view.dot(u)
        v.normalize()
        width = (onpts[-1] - onpts[0]).length
        R = max(width, self.d) * 1.5
        mid = (onpts[0] + onpts[-1]) * 0.5
        front = self.proj.ray(mid + view * R * 2, -view) or mid
        back = self.proj.ray(front - view * (R * 1e-3), -view)
        if back is not None and (back - front).length < R * 2:
            center = (front + back) * 0.5
        else:
            center = front - view * (width * 0.5)
        ring = []
        samples = 72
        for s in range(samples):
            a = 2 * math.pi * s / samples
            dv = u * math.cos(a) + v * math.sin(a)
            h = self.proj.ray(center + dv * R, -dv, R * 1.2)
            if h is not None:
                ring.append(h)
        if len(ring) < samples * 0.6:
            return None
        return smooth_polyline(ring, 1, closed=True)

    def contour(self, bm, pts):
        ring = self.contour_ring(pts)
        if ring is None:
            return False
        sel = self.selected_chain(bm)
        per = poly_length(ring + [ring[0]])
        if sel and sel[1]:
            spans = len(sel[0])
        else:
            spans = self.st.count_u if self.count else max(4, round(per / self.d))
        rs = [self.proj.project(p) for p in resample(ring + [ring[0]], spans)[:-1]]
        if sel and sel[1]:
            self.bridge(bm, sel[0], True, rs)  # 선택한 링과 새 링 사이를 채움
        else:
            vs = [bm.verts.new(self.mwi @ p) for p in rs]
            for i in range(len(vs)):
                bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))
            self.select_only(bm, vs)
        self.stats["contours"] += 1
        return True

    def fill_loop(self, bm, pts):
        pts = smooth_polyline(pts, 3, closed=True)  # 시작/끝 이음매 꺾임 제거
        loop = pts + [pts[0]]
        dense = resample(loop, 128)[:-1]
        n = len(dense)
        cs = find_corners(dense)
        sides = []
        for i in range(4):
            a = cs[i]
            b = cs[(i + 1) % 4] + (n if i == 3 else 0)
            sides.append([dense[k % n] for k in range(a, b + 1)])
        Ls = [poly_length(s) for s in sides]
        na = max(1, round((Ls[0] + Ls[2]) / (2 * self.d)))
        nb = max(1, round((Ls[1] + Ls[3]) / (2 * self.d)))
        if self.count:
            na, nb = self.st.count_u, self.st.count_v
        S0 = resample(sides[0], na)
        S1 = resample(sides[1], nb)
        S2 = resample(sides[2], na)
        S3 = resample(sides[3], nb)
        grid = coons_grid(S0, S1, list(reversed(S2)), list(reversed(S3)))
        self.build_grid(bm, grid)
        self.select_only(bm, [])
        self.stats["fills"] += 1

    def loft(self, bm, A, B):
        if ((A[0] - B[0]).length + (A[-1] - B[-1]).length >
                (A[0] - B[-1]).length + (A[-1] - B[0]).length):
            B = list(reversed(B))
        n = self.st.count_u if self.count else max(1, round((poly_length(A) + poly_length(B)) / 2 / self.d))
        SA = resample(A, n)
        SB = resample(B, n)
        avg = sum((SA[i] - SB[i]).length for i in range(n + 1)) / (n + 1)
        m = self.st.count_v if self.count else max(1, round(avg / self.d))
        R = [SA[-1].lerp(SB[-1], j / m) for j in range(m + 1)]
        L = [SA[0].lerp(SB[0], j / m) for j in range(m + 1)]
        self.build_grid(bm, coons_grid(SA, R, SB, L))
        self.select_only(bm, [])
        self.stats["lofts"] += 1

    # --- 컷 ---
    def cut(self, bm, pts, dry=False):
        region, rv3d = self.region, self.rv3d
        if region is None or rv3d is None:
            return 0
        mw = self.mw
        S2, P = [], []
        for p in pts:
            s = location_3d_to_region_2d(region, rv3d, p)
            if s is not None:
                S2.append(s)
                P.append(p)
        if len(S2) < 2:
            return 0
        minx = min(s.x for s in S2)
        maxx = max(s.x for s in S2)
        miny = min(s.y for s in S2)
        maxy = max(s.y for s in S2)
        cache = {}

        def v2d(v):
            r = cache.get(v)
            if r is None:
                r = location_3d_to_region_2d(region, rv3d, mw @ v.co)
                cache[v] = r if r is not None else False
            return r if r is not False else None

        hits = []
        for e in bm.edges:
            if e.hide:
                continue
            v0, v1 = e.verts
            a2, b2 = v2d(v0), v2d(v1)
            if a2 is None or b2 is None:
                continue
            if (max(a2.x, b2.x) < minx or min(a2.x, b2.x) > maxx or
                    max(a2.y, b2.y) < miny or min(a2.y, b2.y) > maxy):
                continue
            abl = (b2 - a2).length
            if abl < 1e-6:
                continue
            a3, b3 = mw @ v0.co, mw @ v1.co
            tol = max((b3 - a3).length * 0.75, self.d * 1.5)
            for k in range(len(S2) - 1):
                ip = intersect_line_line_2d(a2, b2, S2[k], S2[k + 1])
                if ip is None:
                    continue
                t = (ip - a2).length / abl
                sl = (S2[k + 1] - S2[k]).length
                f = 0.0 if sl < 1e-9 else (ip - S2[k]).length / sl
                if (a3.lerp(b3, t) - P[k].lerp(P[k + 1], f)).length > tol:
                    continue  # 뒷면 엣지
                hits.append((k + f, e, t))
        if dry or len(hits) < 2:
            return len(hits)

        hits.sort(key=lambda h: h[0])
        per_edge = {}
        for idx, (_s, e, t) in enumerate(hits):
            per_edge.setdefault(e, []).append((t, idx))
        hit_vert = [None] * len(hits)
        snap = 0.08
        new_verts = []
        for e, lst in per_edge.items():
            v0, v1 = e.verts[0], e.verts[1]
            lst.sort(key=lambda x: x[0])
            cur_v, cur_t = v0, 0.0
            for t, idx in lst:
                if t < snap:
                    hit_vert[idx] = v0
                    continue
                if t > 1.0 - snap:
                    hit_vert[idx] = v1
                    continue
                ce = edge_between(cur_v, v1)
                if ce is None:
                    continue
                fac = (t - cur_t) / (1.0 - cur_t)
                if fac <= 1e-4:
                    hit_vert[idx] = cur_v
                    continue
                _ne, nv = bmesh.utils.edge_split(ce, cur_v, fac)
                new_verts.append(nv)
                hit_vert[idx] = nv
                cur_v, cur_t = nv, t
        seq = [v for v in hit_vert if v is not None]
        self.last_cut_verts = list(seq)
        made = 0
        new_edges = []
        for va, vb in zip(seq, seq[1:]):
            if va is vb or edge_between(va, vb):
                continue
            common = set(va.link_faces) & set(vb.link_faces)
            for f in common:
                try:
                    _nf, nl = bmesh.utils.face_split(f, va, vb)
                except (ValueError, TypeError):
                    continue
                if nl is not None:
                    new_edges.append(nl.edge)
                made += 1
                break
        for v in new_verts:
            v.co = self.mwi @ self.proj.project(self.mw @ v.co)
        for e in new_edges:
            e.select = True
        if made:
            self.stats["cuts"] += 1
        return made

    # --- 영역 선택 / 흐름 재구성 ---
    def region_select(self, bm, pts):
        """주석으로 둘러싼 곳의 면을 선택 (이후 촘촘하게/성기게/고르게 재구성 버튼이 이 영역에 적용)."""
        if self.region is None or self.rv3d is None:
            return 0
        poly = [s for s in (location_3d_to_region_2d(self.region, self.rv3d, p) for p in pts) if s is not None]
        if len(poly) < 3:
            return 0
        vi = self.rv3d.view_matrix.inverted()
        eye = vi.translation
        nm = self.mw.to_3x3().inverted().transposed()
        bm.normal_update()
        for x in bm.faces:
            x.select_set(False)
        chosen = []
        for f in bm.faces:
            c = self.mw @ f.calc_center_median()
            s = location_3d_to_region_2d(self.region, self.rv3d, c)
            inside = s is not None and point_in_poly(s, poly)
            if inside and not self.obj.show_in_front:
                view = (eye - c) if self.rv3d.is_perspective else (vi.to_3x3() @ Vector((0, 0, 1)))
                inside = (nm @ f.normal).dot(view) > 0  # 뒤쪽 면은 제외
            if inside:
                chosen.append(f)
        for f in chosen:
            f.select_set(True)
        bm.select_flush_mode()
        n = len(chosen)
        self.stats["regions"] = self.stats.get("regions", 0) + 1
        self.stats["selected"] = n
        return n

    def flow_rebuild(self, bm, pts):
        """선택한 면 영역을 그은 선 방향으로 엣지 흐름이 가도록 다시 채움."""
        faces = [f for f in bm.faces if f.select]
        if not faces:
            self.stats["message"] = "흐름 재구성: 먼저 다시 만들 면 영역을 선택하세요 (영역 선택 모드로 둘러싸도 됨)"
            return 0
        flow = pts[-1] - pts[0]
        new, msg = rebuild_region(bm, faces, self.mw, self.proj, self.st, flow=flow)
        self.stats["message"] = msg
        if new:
            self.stats["rebuilds"] = self.stats.get("rebuilds", 0) + 1
            self.stats["faces"] += len(new)
        return len(new)

    # --- 전체 실행 ---
    def run(self, strokes, mode, batch=True):
        ma = MeshAccess(self.obj)
        bm = ma.bm
        prepared = []
        for pts in strokes:
            p = self.prep(pts)
            if p is not None and poly_length(p) > self.d * 0.25:
                prepared.append(p)

        if self.st.density_mode == 'AVERAGE':
            # 선택한 엣지(없으면 전체 경계 엣지)의 평균 길이를 간격으로 사용
            es = [e for e in bm.edges if e.select] or [e for e in bm.edges if e.is_boundary or e.is_wire]
            if es:
                self.d = max(sum((self.mw @ e.verts[0].co - self.mw @ e.verts[1].co).length for e in es) / len(es), 1e-4)
                self.merge = min(self.st.merge_dist, self.d * 0.45)

        rest = []
        for p in prepared:
            if mode == 'REGION':
                self.region_select(bm, p)
                continue
            if mode == 'FLOW':
                self.flow_rebuild(bm, p)
                continue
            if mode == 'CUT':
                self.cut(bm, p)
                continue
            if mode == 'POLYSTRIP':
                self.polystrip(bm, p)
                continue
            if mode == 'CONTOUR':
                if not self.contour(bm, p):
                    rest.append(p)
                continue
            if mode == 'AUTO':
                if len(bm.faces) and self.cut(bm, p, dry=True) >= 2:
                    self.cut(bm, p)
                    continue
                if self.is_contour_stroke(p) and self.contour(bm, p):
                    continue
                if self.try_extrude(bm, p):
                    continue
            rest.append(p)
        if mode == 'CONTOUR':
            mode = 'EDGES'  # 컨투어를 만들 수 없던 선은 엣지로

        if mode == 'EDGES':
            for p in rest:
                closed = is_closed_stroke(p, self.d)
                self.add_chain(bm, p[:-1] if closed else p, closed)
        elif mode == 'LOFT':
            opens = list(rest)
            while len(opens) >= 2:
                self.loft(bm, opens.pop(0), opens.pop(0))
            for p in opens:
                self.add_chain(bm, p, False)
        elif mode in ('FILL', 'AUTO'):
            opens = []
            for p in rest:
                if is_closed_stroke(p, self.d):
                    self.fill_loop(bm, p[:-1])
                else:
                    opens.append(p)
            join = max(self.d * 2.5, self.merge * 2)
            chains = chain_strokes(opens, join)
            leftovers = []
            for pts, parts in chains:
                closed = (parts > 1 and (pts[0] - pts[-1]).length < join) or \
                         (parts == 1 and is_closed_stroke(pts, self.d))
                if closed:
                    self.fill_loop(bm, pts[:-1] if (pts[0] - pts[-1]).length < 1e-9 else pts)
                elif mode == 'FILL' and parts == 1 and len(chains) == 1 and len(leftovers) == 0 \
                        and not batch:
                    self.fill_loop(bm, pts)
                else:
                    leftovers.append(pts)
            if mode == 'FILL':
                while len(leftovers) >= 2:
                    self.loft(bm, leftovers.pop(0), leftovers.pop(0))
                for p in leftovers:
                    self.fill_loop(bm, p)
            elif batch and len(leftovers) == 2:
                self.loft(bm, leftovers[0], leftovers[1])
            else:
                for p in leftovers:
                    self.close_wire_loops(bm, self.add_chain(bm, p, False))

        bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.is_valid], dist=1e-6)
        ma.commit()
        return self.stats


# ---------------------------------------------------------------------------
# 주름 만들기: 선택한 포인트들을 잇는 경로로 컷 + 컷으로 생긴 버텍스 자동 합치기
# ---------------------------------------------------------------------------

def order_points(sel):
    """선택 순서가 없을 때: 한쪽 끝에서 시작해 가장 가까운 점을 차례로 잇는 순서."""
    pts = list(sel)
    c = sum((v.co for v in pts), Vector()) / len(pts)
    cur = max(pts, key=lambda v: (v.co - c).length)
    order = [cur]
    rest = [v for v in pts if v is not cur]
    while rest:
        cur = min(rest, key=lambda v: (v.co - order[-1].co).length)
        order.append(cur)
        rest.remove(cur)
    return order


class _SelfSurface:
    """타겟이 없을 때 리토 메쉬 자신의 표면에 경로를 붙이기 위한 투영기."""

    def __init__(self, bm, mw, offset=0.0):
        self.bvh = BVHTree.FromBMesh(bm)
        self.mw = mw.copy()
        self.mwi = mw.inverted()
        self.ok = True

    def project(self, co):
        loc, _n, _i, _d = self.bvh.find_nearest(self.mwi @ co)
        return co.copy() if loc is None else self.mw @ loc


def make_crease(context, obj, bm, order, region, rv3d, merge_ratio=0.35, closed=False, crease=False):
    """order(버텍스 목록)를 순서대로 잇는 경로로 컷하고, 컷으로 생긴 버텍스 중
    원래 버텍스에 가까운 것(엣지 길이 × merge_ratio 이내)과 서로 겹치는 것을 합친다."""
    st = context.scene.retopo_annot
    conv = Converter(context, region, rv3d, obj=obj)
    mw = conv.mw
    lens = [(mw @ e.verts[0].co - mw @ e.verts[1].co).length for e in bm.edges]
    avg = sum(lens) / len(lens) if lens else st.spacing
    conv.d = max(avg, 1e-4)
    surf = conv.proj if conv.proj.ok else _SelfSurface(bm, mw)
    old = set(bm.verts)
    anchors = [mw @ v.co for v in order]
    segs = [(anchors[i], anchors[i + 1], order[i], order[i + 1]) for i in range(len(anchors) - 1)]
    if closed and len(anchors) > 2:
        segs.append((anchors[-1], anchors[0], order[-1], order[0]))
    cuts = 0
    passed = []
    for A, B, va0, vb0 in segs:
        n = max(8, int((B - A).length / (avg * 0.2)) + 1)
        pts = [A.lerp(B, t / n) for t in range(n + 1)]
        pts = [pts[0]] + [surf.project(p) for p in pts[1:-1]] + [pts[-1]]
        conv.last_cut_verts = []
        if conv.cut(bm, pts):
            cuts += 1
        passed += conv.last_cut_verts
        # 앵커 → 컷 경로 → 앵커: 같은 면인데 엣지가 없으면 직접 연결 (끝점 교차 누락 보정)
        chain = [va0] + list(conv.last_cut_verts) + [vb0]
        for x, y in zip(chain, chain[1:]):
            if x is y or not (x.is_valid and y.is_valid) or edge_between(x, y):
                continue
            for f in set(x.link_faces) & set(y.link_faces):
                try:
                    bmesh.utils.face_split(f, x, y)
                    break
                except (ValueError, TypeError):
                    continue
    # 컷으로 생긴 버텍스 자동 합치기
    new = [v for v in bm.verts if v not in old]
    thr_ratio = max(0.0, min(merge_ratio, 0.49))
    targetmap = {}
    for v in new:
        best = None
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in old:
                continue
            d = (mw @ o.co - mw @ v.co).length
            # 이 버텍스가 나눈 원래 엣지 길이(양 옆 원래 버텍스까지 거리 합)에 대한 비율로 판단
            span = sum((mw @ x.co - mw @ v.co).length for x in (e2.other_vert(v) for e2 in v.link_edges) if x in old)
            if span > 0 and d <= thr_ratio * span and (best is None or d < best[0]):
                best = (d, o)
        if best is not None:
            targetmap[v] = best[1]
    if targetmap:
        bmesh.ops.weld_verts(bm, targetmap=targetmap)
    remain = [v for v in new if v.is_valid]
    if remain:
        bmesh.ops.remove_doubles(bm, verts=remain, dist=avg * 0.05 / max(conv.scale, 1e-9))
    # 경로 선택 (+ 선택 시 크리즈)
    path = set(v for v in order if v.is_valid) | set(v for v in new if v.is_valid)
    path |= set(targetmap.get(v, v) for v in passed)
    path = set(v for v in path if v.is_valid)
    Converter.select_only(bm, list(path))
    if crease:
        layer = None
        try:
            layer = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
        except (AttributeError, ValueError):
            layer = getattr(bm.edges.layers, "crease", None)
            layer = layer.verify() if layer is not None else None
        if layer is not None:
            for e in bm.edges:
                if e.select:
                    e[layer] = 1.0
    merged = len(targetmap)
    return {"segments": len(segs), "cuts": cuts, "new_verts": len([v for v in new if v.is_valid]), "merged": merged}


# ---------------------------------------------------------------------------
# 빈 곳 채우기: 스트립/면으로 둘러싸인 빈 곳을 기존 경계 버텍스를 그대로 써서 쿼드로 채움
#  - 빈 곳을 둘러싼 경계 버텍스를 선택 (U자 안쪽이면 입구 양쪽 끝 버텍스 2개만 골라도 됨)
#  - 같은 경계에서 고른 점들은 그 사이 '짧은 쪽' 경계를 따라 이어짐
#  - 경계 줄 1개(열림) → 두 끝을 새 변으로 이어 닫음 / 2개 → 두 줄 사이 / 닫힌 경계 → 구멍
# ---------------------------------------------------------------------------

def _open_edge(e):
    return len(e.link_faces) < 2 and not e.hide


def _boundary_components(bm):
    """열린 엣지로 이어진 버텍스 묶음 → {vert: comp_id}."""
    comp = {}
    cid = 0
    for v in bm.verts:
        if v in comp or not any(_open_edge(e) for e in v.link_edges):
            continue
        stack = [v]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp[x] = cid
            for e in x.link_edges:
                if _open_edge(e):
                    stack.append(e.other_vert(x))
        cid += 1
    return comp


def _boundary_cycle(start):
    """start 가 속한 경계가 단순한 고리면 순서대로 버텍스 목록, 아니면 None."""
    loop = [start]
    prev, cur = None, start
    while len(loop) < 100000:
        nxt = [e.other_vert(cur) for e in cur.link_edges if _open_edge(e)]
        if len(nxt) != 2:
            return None
        n = nxt[0] if nxt[0] is not prev else nxt[1]
        if n is start:
            return loop
        loop.append(n)
        prev, cur = cur, n
    return None


def _boundary_path(a, b):
    """열린 엣지만 따라 a→b 최단 경로 (다익스트라)."""
    import heapq
    dist = {a: 0.0}
    back = {}
    heap = [(0.0, id(a), a)]
    while heap:
        d, _k, v = heapq.heappop(heap)
        if v is b:
            break
        if d > dist.get(v, 1e30):
            continue
        for e in v.link_edges:
            if not _open_edge(e):
                continue
            o = e.other_vert(v)
            nd = d + e.calc_length()
            if nd < dist.get(o, 1e30):
                dist[o] = nd
                back[o] = v
                heapq.heappush(heap, (nd, id(o), o))
    if b not in dist:
        return None
    path = [b]
    while path[-1] is not a:
        path.append(back[path[-1]])
    return list(reversed(path))


def gap_chains(bm):
    """선택에서 채울 경계 줄들 → [(버텍스 목록, 닫힘)] 또는 오류 문자열."""
    comp = _boundary_components(bm)
    groups = {}
    for v in bm.verts:
        if v.select and not v.hide and v in comp:
            groups.setdefault(comp[v], []).append(v)
    groups = [g for g in groups.values() if len(g) >= 2]
    if not groups:
        return "빈 곳을 둘러싼 경계(열린 엣지) 버텍스를 2개 이상 선택하세요"
    chains = []
    for g in groups:
        cyc = _boundary_cycle(g[0])
        if cyc is not None:
            sel = set(g)
            if len(sel) == len(cyc):
                chains.append((cyc, True))
                continue
            idx = [i for i, v in enumerate(cyc) if v in sel]
            n = len(cyc)
            # 고른 점들을 모두 덮는 가장 짧은 호 = 고리에서 선택 사이 가장 큰 빈틈을 뺀 나머지
            lens = [(cyc[(i + 1) % n].co - cyc[i].co).length for i in range(n)]

            def arc_len(i, j):
                s, k = 0.0, i
                while k != j:
                    s += lens[k]
                    k = (k + 1) % n
                return s
            gaps = [(arc_len(idx[k], idx[(k + 1) % len(idx)]), k) for k in range(len(idx))]
            _gl, k = max(gaps)
            start = idx[(k + 1) % len(idx)]
            end = idx[k]
            arc = [cyc[start]]
            i = start
            while i != end:
                i = (i + 1) % n
                arc.append(cyc[i])
            chains.append((arc, False))
        else:
            if len(g) != 2:
                return "경계가 여러 갈래로 이어져 있습니다. 빈 곳 입구의 양 끝 버텍스 2개만 선택하세요"
            p = _boundary_path(g[0], g[1])
            if p is None or len(p) < 2:
                return "선택한 두 버텍스가 경계로 이어져 있지 않습니다"
            chains.append((p, False))
    if len(chains) > 2:
        return "경계 줄은 1~2개만 선택하세요 (지금 %d개)" % len(chains)
    return chains


def _turn(P, i, N, w=1):
    a = P[i] - P[(i - w) % N]
    b = P[(i + w) % N] - P[i]
    if a.length < 1e-12 or b.length < 1e-12:
        return 0.0
    return a.angle(b, 0.0)


def flow_continuity(P, ext, i0, a, b, step=1):
    """모서리 (i0, a, b) 로 나눴을 때 격자 선이 주변에서 들어오는 엣지를 얼마나 곧게 잇는지 (0~1)."""
    N = len(P)
    s = n = 0.0

    def one(k, other):
        nonlocal s, n
        e = ext[k]
        if e is None:
            return
        d = P[other] - P[k]
        if d.length < 1e-12:
            return
        s += max(0.0, d.normalized().dot(e))
        n += 1
    for k in range(1, a, step):          # 세로 선: 아래 변 k ↔ 위 변 k
        lo = (i0 + k) % N
        hi = (i0 + 2 * a + b - k) % N
        one(lo, hi)
        one(hi, lo)
    for j in range(1, b, step):          # 가로 선: 왼쪽 변 j ↔ 오른쪽 변 j
        lf = (i0 - j) % N
        rt = (i0 + a + j) % N
        one(lf, rt)
        one(rt, lf)
    return s / n if n else 0.0


def boundary_ext_dirs(loop, region_faces, mw):
    """경계 점마다 영역 밖에서 들어오는 엣지 방향 (영역 안쪽을 향함). 딱 하나가 아니면 None."""
    fs = set(region_faces)
    lset = set(loop)
    out = []
    for v in loop:
        cand = []
        for e in v.link_edges:
            if any(f in fs for f in e.link_faces):
                continue  # 영역 안 엣지 / 영역 경계 엣지
            o = e.other_vert(v)
            if o in lset and not e.link_faces:
                continue
            cand.append(o)
        if len(cand) == 1:
            d = (mw @ v.co) - (mw @ cand[0].co)
            out.append(d.normalized() if d.length > 1e-12 else None)
        else:
            out.append(None)
    return out


def solve_quad_sides(P, bonus=(), flow=None, top=1, ext=None):
    """닫힌 경계 점 P(N개, 짝수) 를 마주보는 변끼리 개수가 같은 4변으로 나눔 → (i0, a, b).
    flow(방향 벡터)를 주면 첫 변(엣지 줄 방향)이 그 방향과 나란한 쪽을 크게 선호.
    ext[i] = 경계 점 i 로 바깥에서 들어오는 엣지 방향(없으면 None) → 새 격자 선이 주변 엣지를 곧게 잇는 쪽을 선호."""
    ext_pts = [i for i in range(len(P)) if ext is not None and ext[i] is not None]
    step = 2 if len(ext_pts) > 120 else 1
    fl = flow.normalized() if flow is not None and flow.length > 1e-12 else None
    N = len(P)
    half = N // 2
    cum = [0.0]
    for i in range(N):
        cum.append(cum[-1] + (P[(i + 1) % N] - P[i]).length)
    total = cum[-1]

    def seg(i, k):  # i 에서 k 개 엣지 길이
        j = i + k
        return cum[j] - cum[i] if j <= N else (total - cum[i]) + cum[j - N]
    turn = [max(_turn(P, i, N, 1), _turn(P, i, N, 2) * 0.8) for i in range(N)]
    bonus = set(bonus)
    best = None
    allc = []
    for i0 in range(N):
        for a in range(1, half):
            b = half - a
            cs = (i0, (i0 + a) % N, (i0 + half) % N, (i0 + half + a) % N)
            score = sum(turn[c] + (0.6 if c in bonus else 0.0) for c in cs)
            L1, L2 = seg(cs[0], a), seg(cs[1], b)
            L3, L4 = seg(cs[2], a), seg(cs[3], b)
            score -= 1.5 * (abs(L1 - L3) / max(L1 + L3, 1e-9) + abs(L2 - L4) / max(L2 + L4, 1e-9))
            # 칸이 정사각형에 가깝게 (한 줄짜리 길쭉한 쿼드 방지): 실제로 마주보는 변 사이 거리로 칸 크기 추정
            along = across = 0.0
            for t in (0.25, 0.5, 0.75):
                kb, ka = round(t * b), round(t * a)
                along += (P[(i0 - kb) % N] - P[(i0 + a + kb) % N]).length / a
                across += (P[(i0 + ka) % N] - P[(i0 + 2 * a + b - ka) % N]).length / b
            score -= 2.0 * abs(math.log(max(along, 1e-9)) - math.log(max(across, 1e-9)))
            if fl is not None:
                # 엣지 줄(첫 변과 셋째 변 방향)이 그은 선과 나란할수록 좋음
                d1 = P[cs[1]] - P[cs[0]]
                d3 = P[cs[2]] - P[cs[3]]
                al = 0.0
                for d in (d1, d3):
                    if d.length > 1e-12:
                        al += abs(d.normalized().dot(fl))
                score += 3.0 * al
            if ext_pts:
                score += 4.0 * flow_continuity(P, ext, i0, a, b, step)
            allc.append((score, i0, a, b))
            if best is None or score > best[0]:
                best = (score, i0, a, b)
    if top > 1:
        allc.sort(key=lambda c: -c[0])
        return [c[1:] for c in allc[:top]]  # 점수 높은 순으로 여러 후보
    return best[1:]


def fill_gap(context, obj):
    """선택한 경계로 둘러싼 빈 곳을 쿼드로 채움 → (만든 면 수, 메시지)."""
    st = context.scene.retopo_annot
    bm = bmesh.from_edit_mesh(obj.data)
    chains = gap_chains(bm)
    if isinstance(chains, str):
        return 0, chains
    mw = obj.matrix_world
    mwi = mw.inverted()
    proj = Projector(context, st, st.surface_offset)
    elen = [e.calc_length() for e in bm.edges if _open_edge(e)]
    avg = (sum(elen) / len(elen)) if elen else max(st.spacing, 1e-4)
    avg_w = avg * mw.to_scale().length / math.sqrt(3)

    # 경계 고리 만들기: 항목 = 기존 BMVert 또는 새로 만들 월드 좌표
    items, bonus = [], []

    def closing(pa, pb, count):
        return [proj.project(pa.lerp(pb, k / count)) for k in range(1, count)]

    if len(chains) == 1 and chains[0][1]:
        items = list(chains[0][0])
        if len(items) % 2:
            # 홀수면 쿼드로 못 채우므로 가장 긴 경계 엣지 가운데에 버텍스 하나 추가
            n = len(items)
            k = max(range(n), key=lambda i: (items[(i + 1) % n].co - items[i].co).length)
            e = edge_between(items[k], items[(k + 1) % n])
            _ne, nv = bmesh.utils.edge_split(e, items[k], 0.5)
            nv.co = mwi @ proj.project(mw @ nv.co)
            items.insert(k + 1, nv)
    elif len(chains) == 1:
        ch = chains[0][0]
        pa, pb = mw @ ch[-1].co, mw @ ch[0].co
        c = max(1, round((pb - pa).length / avg_w))
        if (len(ch) - 1 + c) % 2:
            c = c + 1 if (pb - pa).length / avg_w >= c or c == 1 else c - 1
        items = list(ch) + closing(pa, pb, c)
        bonus = [0, len(ch) - 1]
    else:
        A, B = chains[0][0], chains[1][0]
        if ((A[-1].co - B[0].co).length + (B[-1].co - A[0].co).length >
                (A[-1].co - B[-1].co).length + (B[0].co - A[0].co).length):
            B = list(reversed(B))
        g1 = (mw @ A[-1].co, mw @ B[0].co)
        g2 = (mw @ B[-1].co, mw @ A[0].co)
        c1 = max(1, round((g1[1] - g1[0]).length / avg_w))
        c2 = max(1, round((g2[1] - g2[0]).length / avg_w))
        if (len(A) - 1 + len(B) - 1 + c1 + c2) % 2:
            c2 += 1
        items = list(A) + closing(*g1, c1) + list(B) + closing(*g2, c2)
        bonus = [0, len(A) - 1, len(A) + c1 - 1, len(A) + c1 - 1 + len(B) - 1]

    N = len(items)
    if N < 4:
        return 0, "채울 경계가 너무 짧습니다"
    GP = [mw @ x.co if isinstance(x, bmesh.types.BMVert) else x for x in items]

    # 빈 곳이 두 표면(바닥/벽 등)에 걸쳐 있으면 교차선을 따라 두 조각으로 나눠 채움
    # → 조각마다 한 표면 위에만 있어 면이 접히거나 겹치지 않고, 교차선 위에 버텍스 줄이 생김
    patches = []
    cz = loop_creases(GP, proj, avg_w) if st.snap_creases else []
    if len(cz) == 2:
        ca, cb = sorted(cz, key=lambda c: c[0])
        i1, i2 = ca[0], cb[0]
        n1 = i2 - i1
        n2 = N - n1
        if n1 >= 2 and n2 >= 2:
            nA, nB = ca[2], ca[3]
            q1, q2 = GP[i1], GP[i2]
            g = (q2 - q1).length / avg_w
            c = max(1, round(g))
            if (n1 + c) % 2:
                c = c + 1 if g >= c or c == 1 else c - 1
            row = []
            for k in range(1, c):
                x = on_crease(q1.lerp(q2, k / c), nA, nB, proj, avg_w)
                items.append(x)
                GP.append(x)
                row.append(len(items) - 1)
            loop1 = list(range(i1, i2 + 1)) + list(reversed(row))
            loop2 = list(range(i2, N)) + list(range(0, i1 + 1)) + row
            b1 = {0, i2 - i1}
            b2 = {0, N - i2 + i1}
            for k in bonus:
                if k in loop1:
                    b1.add(loop1.index(k))
                if k in loop2:
                    b2.add(loop2.index(k))
            patches = [(loop1, b1), (loop2, b2)]
    if not patches:
        patches = [(list(range(N)), set(bonus))]
    plans = [plan_patch(GP, lp, bl, proj, st) for lp, bl in patches]

    made_verts = {}

    def vert_of(k):
        x = items[k]
        if isinstance(x, bmesh.types.BMVert):
            return x
        if k not in made_verts:
            made_verts[k] = bm.verts.new(mwi @ x)
        return made_verts[k]

    quads, interior = [], []
    for gi, grid, a, b in plans:
        V = []
        for j in range(b + 1):
            row = []
            for i in range(a + 1):
                if gi[j][i] >= 0:
                    row.append(vert_of(gi[j][i]))
                else:
                    v = bm.verts.new(mwi @ grid[j][i])
                    interior.append(v)
                    row.append(v)
            V.append(row)
        quads += [(V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]) for j in range(b) for i in range(a)]

    # 선택한 경계 안쪽이 이미 면이면(= 빈 곳의 반대편을 고른 것) 또는 채울 넓이가 없으면 채우지 않음
    bad = sum(1 for q in quads if not quad_ok([mw @ v.co for v in q]))
    over = under = 0
    if bad > len(quads) * 0.3:
        over = 1 << 30
    for q in quads:
        qc = sum((mw @ v.co for v in q), Vector()) / 4
        for k in range(4):
            e = edge_between(q[k], q[(k + 1) % 4])
            if e is None or not e.link_faces:
                continue
            m = mw @ ((e.verts[0].co + e.verts[1].co) * 0.5)
            d = (mw @ e.verts[1].co - mw @ e.verts[0].co).normalized()
            fc = mw @ e.link_faces[0].calc_center_median()
            u1 = (qc - m) - d * (qc - m).dot(d)
            u2 = (fc - m) - d * (fc - m).dot(d)
            if u1.dot(u2) > 0:
                over += 1
            else:
                under += 1
    if over > under:
        for v in interior + list(made_verts.values()):
            if v.is_valid:
                bm.verts.remove(v)
        bmesh.update_edit_mesh(obj.data)
        return 0, ("채울 빈 곳이 없습니다 (선택한 경계 안쪽이 이미 면이거나 폭이 없음). "
                   "빈 곳을 둘러싼 경계를 선택하세요")

    same = opp = 0
    for q in quads:
        s, o = winding_vs_neighbors(list(q))
        same += s
        opp += o
    faces = []
    for q in quads:
        if st.snap_creases:
            q = best_quad_order(q, [mw @ v.co for v in q], proj, avg_w)
        try:
            faces.append(bm.faces.new(q))
        except ValueError:
            pass
    conv = Converter.__new__(Converter)  # 방향 판정 함수만 빌려 씀
    conv.mw, conv.proj, conv.rv3d = mw, proj, None
    flip = same > opp if (same or opp) else (faces and conv.faces_point_inward(faces))
    if flip:
        for f in faces:
            f.normal_flip()
    for v in bm.verts:
        v.select = False
    for e in bm.edges:
        e.select = False
    for f in bm.faces:
        f.select = False
    for f in faces:
        f.select = True
    bm.normal_update()
    bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
    sizes = " + ".join("%d x %d" % (p[2], p[3]) for p in plans)
    return len(faces), "빈 곳 채우기: 면 %d개 (%s%s)" % (len(faces), sizes,
                                                  ", 꺾이는 곳에서 나눔" if len(plans) > 1 else "")


def _mesh_islands(bm):
    """엣지로 이어진 조각 → {vert: 조각 번호}."""
    isl = {}
    k = 0
    for v in bm.verts:
        if v in isl or v.hide:
            continue
        stack = [v]
        while stack:
            x = stack.pop()
            if x in isl:
                continue
            isl[x] = k
            stack.extend(e.other_vert(x) for e in x.link_edges if not e.hide)
        k += 1
    return isl


def connect_select(bm):
    """떨어진 두 조각의 마주 보는 경계 버텍스를 골라 선택 → None 또는 오류 문자열.
    선택이 두 조각에 걸쳐 있으면 그 두 조각, 아니면 가장 가까운 두 조각."""
    comp = _boundary_components(bm)
    isl = _mesh_islands(bm)
    by_comp = {}
    for v, c in comp.items():
        by_comp.setdefault(c, []).append(v)
    if len(by_comp) < 2:
        return "연결할 떨어진 조각이 없습니다 (열린 경계가 있는 조각이 2개 이상 필요)"
    sel_comps = []
    for v in bm.verts:
        if v.select and v in comp and comp[v] not in sel_comps:
            sel_comps.append(comp[v])
    # 이미 두 조각에서 경계를 2개 이상씩 골랐으면 그대로 사용
    if len(sel_comps) == 2 and all(sum(1 for v in by_comp[c] if v.select) >= 2 for c in sel_comps):
        return None
    if len(sel_comps) == 2:
        pairs = [tuple(sel_comps)]
    else:
        cs = list(by_comp)
        if len(sel_comps) == 1:
            cs = sel_comps + [c for c in cs if c != sel_comps[0]]
            pairs = [(sel_comps[0], c) for c in cs[1:]]
        else:
            pairs = [(cs[i], cs[j]) for i in range(len(cs)) for j in range(i + 1, len(cs))]
    kds = {}

    def kd_of(c):
        if c not in kds:
            vs = by_comp[c]
            kd = kdtree.KDTree(len(vs))
            for i, v in enumerate(vs):
                kd.insert(v.co, i)
            kd.balance()
            kds[c] = kd
        return kds[c]
    best = None
    for ca, cb in pairs:
        diff_island = isl[by_comp[ca][0]] != isl[by_comp[cb][0]]
        kd = kd_of(cb)
        for v in by_comp[ca]:
            _co, i, d = kd.find(v.co)
            key = (0 if diff_island else 1, d)
            if best is None or key < best[0]:
                best = (key, ca, cb, v, by_comp[cb][i])
    if best is None:
        return "연결할 조각을 찾지 못했습니다"
    _k, ca, cb, va, vb = best
    dmin = (va.co - vb.co).length
    elen = [e.calc_length() for c in (ca, cb) for v in by_comp[c] for e in v.link_edges if _open_edge(e)]
    avg = sum(elen) / max(len(elen), 1)
    lim = dmin * 2.0 + avg

    def facing(c, start, other):
        kd = kd_of(other)
        cyc = _boundary_cycle(start)
        if cyc is None:
            nb = [e.other_vert(start) for e in start.link_edges if _open_edge(e)]
            return [start] + nb[:1]
        n = len(cyc)
        i0 = cyc.index(start)
        chain = [start]
        def faces_other(k):
            # 경계 방향과 상대 조각 쪽 방향이 거의 나란하면(모서리를 돌아 옆면) 마주 보는 곳이 아님
            v = cyc[k]
            co, _i, d = kd.find(v.co)
            if d > lim:
                return False
            t = cyc[(k + 1) % n].co - cyc[(k - 1) % n].co
            w = co - v.co
            if t.length < 1e-12 or w.length < 1e-12:
                return True
            return abs(t.normalized().dot(w.normalized())) < 0.8
        for step in (1, -1):
            k = i0
            for _ in range(n - 1):
                k = (k + step) % n
                v = cyc[k]
                if v in chain or not faces_other(k):
                    break
                if step == 1:
                    chain.append(v)
                else:
                    chain.insert(0, v)
        if len(chain) < 2:
            chain.append(cyc[(i0 + 1) % n])
        if len(chain) >= n:
            return None
        return chain
    A = facing(ca, va, cb)
    B = facing(cb, vb, ca)
    if not A or not B:
        return "마주 보는 경계를 찾지 못했습니다. 두 조각의 마주 보는 경계 버텍스를 직접 선택하세요"
    for v in bm.verts:
        v.select = False
    for e in bm.edges:
        e.select = False
    for f in bm.faces:
        f.select = False
    for v in A + B:
        v.select = True
    return None


def connect_pieces(context, obj):
    """떨어진 두 조각을 표면에 맞는 쿼드로 이음 → (만든 면 수, 메시지)."""
    bm = bmesh.from_edit_mesh(obj.data)
    err = connect_select(bm)
    if err:
        return 0, err
    bmesh.update_edit_mesh(obj.data)
    n, msg = fill_gap(context, obj)
    return n, msg.replace("빈 곳 채우기", "조각 연결")


def loop_creases(GP, proj, avg):
    """경계 고리에서 꺾이는 곳(두 표면 교차선) 위에 있는 점 → [(번호, 거리, 앞쪽 노멀, 뒤쪽 노멀)]."""
    N = len(GP)
    hn = [proj.normal(p) for p in GP]
    cand = []
    for i in range(N):
        a, b = hn[i - 1], hn[(i + 1) % N]
        if a is None or b is None or a.angle(b, 0.0) <= CREASE_ANGLE:
            continue
        x = plane_cross_point(GP[i - 1], a, GP[(i + 1) % N], b)
        if x is not None and (x - GP[i]).length < avg * 0.25:
            cand.append((i, (x - GP[i]).length, a, b))
    out = []
    for c in cand:  # 붙어 있는 후보는 교차선에 가장 가까운 하나만
        for k, o in enumerate(out):
            dj = abs(o[0] - c[0])
            if dj <= 1 or dj >= N - 1:
                if c[1] < o[1]:
                    out[k] = c
                break
        else:
            out.append(c)
    return out


def on_crease(x, nA, nB, proj, avg):
    """점 x 를 두 표면(노멀 nA, nB)의 교선 위로."""
    pa = proj.ray(x + nA * avg * 4, -nA, avg * 8) or proj.project(x)
    pb = proj.ray(x + nB * avg * 4, -nB, avg * 8) or proj.project(x)
    q = plane_cross_point(pa, nA, pb, nB)
    return x if q is None or (q - x).length > avg * 3 else q


def grid_max_aspect(grid):
    """격자 칸 중 가장 길쭉한 칸의 (긴 변 / 짧은 변)."""
    worst = 1.0
    for j in range(len(grid) - 1):
        for i in range(len(grid[0]) - 1):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            ls = [(q[(k + 1) % 4] - q[k]).length for k in range(4)]
            worst = max(worst, max(ls) / max(min(ls), 1e-9))
    return worst


def grid_tangled(grid, proj):
    """뒤집히거나 꼬인(보타이) 칸이 있으면 True. 칸 방향은 대부분의 칸 방향과 비교."""
    b = len(grid) - 1
    a = len(grid[0]) - 1
    signs = []
    bad = False
    for j in range(b):
        for i in range(a):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            n = (q[2] - q[0]).cross(q[3] - q[1])
            ref = proj.normal((q[0] + q[1] + q[2] + q[3]) / 4) if proj.ok else None
            if ref is None:
                ref = n
            # 네 모서리 각각의 방향이 모두 같은 쪽이어야 정상 (하나라도 다르면 꼬임)
            s = [((q[(k + 1) % 4] - q[k]).cross(q[(k + 2) % 4] - q[(k + 1) % 4])).dot(ref) for k in range(4)]
            pos = sum(1 for x in s if x > 0)
            neg = sum(1 for x in s if x < 0)
            if pos == 2 and neg == 2:
                bad = True  # 꼬인(보타이) 칸 (한 모서리만 오목한 칸은 허용)
            signs.append(1 if pos >= neg else -1)
    if bad:
        return True
    return 0 < sum(1 for x in signs if x < 0) < len(signs)  # 일부만 뒤집힘


def plan_patch(GP, loop, bonus, proj, st, flow=None, sides=None, ext=None):
    """경계 고리(전체 항목 번호 목록) 하나를 쿼드 그리드로 → (칸별 항목 번호(안쪽 -1), 위치 그리드, a, b).
    ext[GP 번호] = 그 경계 점으로 바깥에서 들어오는 엣지 방향 → 경계 바로 안쪽 점을 그 방향으로 당겨 흐름을 곧게 이음."""
    N = len(loop)
    P = [GP[k] for k in loop]
    i0, a, b = sides if sides is not None else solve_quad_sides(P, bonus, flow)
    idx = lambda k: (i0 + k) % N
    S1 = [idx(k) for k in range(0, a + 1)]
    S2 = [idx(a + k) for k in range(0, b + 1)]
    S3 = [idx(a + b + k) for k in range(0, a + 1)]
    S4 = [idx(2 * a + b + k) for k in range(0, b + 1)]
    grid = coons_grid([P[k] for k in S1], [P[k] for k in S2],
                      [P[k] for k in reversed(S3)], [P[k] for k in reversed(S4)])
    grid = [[p if (j in (0, b) or i in (0, a)) else proj.project(p) for i, p in enumerate(row)]
            for j, row in enumerate(grid)]
    # 경계 점 → 바로 안쪽 점 쌍 (바깥 엣지 방향이 있는 것만)
    pulls = []
    if ext is not None and a > 1 and b > 1:
        for i in range(1, a):
            pulls.append(((0, i), (1, i), ext[loop[S1[i]]]))
            pulls.append(((b, i), (b - 1, i), ext[loop[S3[a - i]]]))
        for j in range(1, b):
            pulls.append(((j, 0), (j, 1), ext[loop[S4[b - j]]]))
            pulls.append(((j, a), (j, a - 1), ext[loop[S2[j]]]))
        pulls = [p for p in pulls if p[2] is not None]

    def relax(times, pull=True):
        for _ in range(times):
            for j in range(1, b):
                for i in range(1, a):
                    grid[j][i] = (grid[j - 1][i] + grid[j + 1][i] + grid[j][i - 1] + grid[j][i + 1]) * 0.25
            if pull:
                for (jb, ib), (jn, i_n), e in pulls:
                    pb, pn = grid[jb][ib], grid[jn][i_n]
                    grid[jn][i_n] = pn.lerp(pb + e * (pn - pb).length, 0.6)
            for j in range(1, b):
                for i in range(1, a):
                    grid[j][i] = proj.project(grid[j][i])
    relax(max(2, st.relax_iterations))
    # 들쭉날쭉한 경계(오목한 모서리)에서 칸이 뒤집히거나 꼬이면, 안쪽 점을 더 고르게 펴서 풀어 줌
    for _ in range(12):
        if not grid_tangled(grid, proj):
            break
        relax(5, pull=False)
    if st.snap_creases:
        grid = snap_grid_creases(grid, proj)
    gi = []
    for j in range(b + 1):
        row = []
        for i in range(a + 1):
            if j == 0:
                li = S1[i]
            elif j == b:
                li = S3[a - i]
            elif i == 0:
                li = S4[b - j]
            elif i == a:
                li = S2[j]
            else:
                li = None
            row.append(loop[li] if li is not None else -1)
        gi.append(row)
    return gi, grid, a, b


# ---------------------------------------------------------------------------
# 만든 메쉬 성기게: 엣지 링을 따라 루프를 하나 건너 하나 제거
#  (경계 루프·꺾이는 곳(교차선) 루프·중간에서 끊기는 루프는 남김 → 면이 뜨거나 n각형이 생기지 않게)
# ---------------------------------------------------------------------------

def _opposite_edge(f, e):
    if len(f.verts) != 4:
        return None
    ev = set(e.verts)
    for x in f.edges:
        if x is not e and not (set(x.verts) & ev):
            return x
    return None


def _edge_ring(e0, faces):
    ring = [e0]
    seen = set()
    for d in range(2):
        cur, side = e0, []
        while True:
            nf = [f for f in cur.link_faces if f in faces and f not in seen]
            if not nf:
                break
            seen.add(nf[0])
            o = _opposite_edge(nf[0], cur)
            if o is None or o in ring or o in side:
                break
            side.append(o)
            cur = o
        ring = list(reversed(side)) + ring if d == 0 else ring + side
    return ring


def _edge_loop(e0):
    """→ (엣지 목록, 완전한가). 완전 = 양 끝이 열린 경계에서 끝나거나 한 바퀴 닫힘."""
    loop = [e0]
    complete = True
    for v in e0.verts:
        cur = e0
        while True:
            if len(v.link_edges) != 4:
                if not any(len(x.link_faces) < 2 for x in v.link_edges):
                    complete = False
                break
            curf = set(cur.link_faces)
            nxt = [x for x in v.link_edges if x is not cur and not (set(x.link_faces) & curf)]
            if len(nxt) != 1:
                complete = False
                break
            if nxt[0] in loop:
                break
            cur = nxt[0]
            loop.append(cur)
            v = cur.other_vert(v)
    return loop, complete


def _is_crease_loop(loop):
    for e in loop:
        if len(e.link_faces) == 2 and e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0) > CREASE_ANGLE:
            return True
    return False


def _remove_alternate_loops(bm, seed, faces):
    ring = _edge_ring(seed, faces)
    rem = set()
    for k in range(1, len(ring) - 1, 2):
        lp, complete = _edge_loop(ring[k])
        if not complete or _is_crease_loop(lp) or any(len(e.link_faces) < 2 for e in lp):
            continue
        # 루프 전체를 지움 (영역 안 부분만 지우면 영역 둘레에 5각형이 생김)
        if any(len(f.verts) != 4 for e in lp for f in e.link_faces):
            continue
        if rem & {x for e in lp for v in e.verts for x in v.link_edges}:
            continue  # 바로 옆 루프와 같이 지우면 면이 합쳐져 망가짐
        rem.update(lp)
    if rem:
        bmesh.ops.dissolve_edges(bm, edges=list(rem), use_verts=True)
    return len(rem)


def densify_edges(faces):
    """촘촘하게: 나눌 엣지 집합. 영역 면의 엣지 + 둘레에서 바깥으로 이어지는 엣지 링
    (영역 옆 면이 한 변만 나뉘면 5각형이 되므로, 맞은편 변도 나눠 메쉬 끝/영역까지 이어 감)."""
    split = {e for f in faces for e in f.edges}
    queue = list({f for e in split for f in e.link_faces if f not in faces})
    seen_q = set(queue)
    while queue:
        f = queue.pop()
        seen_q.discard(f)
        if len(f.verts) != 4:
            continue
        es = list(f.edges)  # 쿼드: es[i] 맞은편 = es[(i+2)%4]
        flags = [e in split for e in es]
        k = sum(flags)
        if k == 0 or k == 4 or (k == 2 and flags[0] == flags[2]):
            continue
        for i in range(4):
            if flags[i] and not flags[(i + 2) % 4]:
                o = es[(i + 2) % 4]
                split.add(o)
                for nf in o.link_faces:
                    if nf is not f and nf not in seen_q:
                        queue.append(nf)
                        seen_q.add(nf)
        flags = [e in split for e in es]
        if sum(flags) == 3:
            for i in range(4):
                if not flags[i]:
                    split.add(es[i])
                    for nf in es[i].link_faces:
                        if nf is not f and nf not in seen_q:
                            queue.append(nf)
                            seen_q.add(nf)
        if f not in seen_q:  # 이 면도 다시 확인 (2개 인접 → 4개가 되었는지)
            queue.append(f)
            seen_q.add(f)
    return list(split)


def sparsify(bm, faces):
    """faces(쿼드 격자 영역)를 가로·세로 반으로 성기게 → 지운 엣지 수."""
    bm.normal_update()
    faces = set(faces)
    quads = [f for f in faces if len(f.verts) == 4]
    if not quads:
        return 0
    c = sum((f.calc_center_median() for f in faces), Vector()) / len(faces)
    seed_f = min(quads, key=lambda f: (f.calc_center_median() - c).length)
    e1 = seed_f.edges[0]
    e2 = seed_f.edges[1]
    m2 = (e2.verts[0].co + e2.verts[1].co) * 0.5
    dir1 = (e1.verts[1].co - e1.verts[0].co).normalized()
    centers = [f.calc_center_median() for f in faces]
    elen = [e.calc_length() for f in faces for e in f.edges]
    avg = sum(elen) / len(elen)
    removed = _remove_alternate_loops(bm, e1, faces)
    # 첫 방향을 지우면 요소가 바뀌므로 위치로 영역과 두 번째 방향 시작 엣지를 다시 찾음
    bm.normal_update()
    kd = kdtree.KDTree(len(centers))
    for i, p in enumerate(centers):
        kd.insert(p, i)
    kd.balance()
    faces2 = {f for f in bm.faces if kd.find(f.calc_center_median())[2] < avg * 1.5}
    best = None
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co
        if (b - a).length < 1e-12 or abs((b - a).normalized().dot(dir1)) >= 0.5:
            continue
        t = max(0.0, min(1.0, (m2 - a).dot(b - a) / (b - a).length_squared))
        d = (m2 - a.lerp(b, t)).length
        if best is None or d < best[0]:
            best = (d, e)
    if best:
        bm.normal_update()
        removed += _remove_alternate_loops(bm, best[1], faces2)
    return removed


# ---------------------------------------------------------------------------
# 영역 재구성: 선택한 면 영역을 바깥 경계는 그대로 두고 쿼드 격자로 다시 채움
#  - flow 방향을 주면 엣지 줄이 그 방향(주석으로 그은 선)을 따르도록 모서리를 고름
#  - flow 없이 = 고르게(평평하게) 재구성: 극점·삼각형·찌그러진 면을 없애고 간격을 고르게
# ---------------------------------------------------------------------------

def region_boundary_loop(faces):
    """면 영역의 바깥 경계 → (순서대로 버텍스 목록, 오류 문자열)."""
    fs = set(faces)
    bedges = {e for f in fs for e in f.edges if sum(1 for x in e.link_faces if x in fs) == 1}
    adj = {}
    for e in bedges:
        a, b = e.verts
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if not adj:
        return None, "영역 경계를 찾지 못했습니다 (면을 선택하세요)"
    if any(len(v) != 2 for v in adj.values()):
        return None, "영역 경계가 한 줄로 이어지지 않습니다 (모서리 한 점으로만 붙은 면이 있음)"
    start = next(iter(adj))
    loop, prev, cur = [start], None, start
    while True:
        a, b = adj[cur]
        n = a if a is not prev else b
        if n is start:
            break
        loop.append(n)
        prev, cur = cur, n
        if len(loop) > len(adj):
            return None, "영역 경계가 이상합니다"
    if len(loop) != len(adj):
        return None, "영역 안에 구멍이 있거나 떨어진 조각이 있습니다 (구멍 없는 한 덩어리를 선택하세요)"
    return loop, None


def grow_region(faces, limit=1.6):
    """오목하게 파인 칸(영역과 엣지 2개 이상 맞닿은 바깥 쿼드)을 채워 경계를 매끈하게 → 면 목록."""
    fs = set(faces)
    n0 = len(fs)
    for _ in range(40):
        cnt = {}
        for f in fs:
            for e in f.edges:
                for g in e.link_faces:
                    if g not in fs:
                        cnt[g] = cnt.get(g, 0) + 1
        add = [g for g, c in cnt.items() if c >= 2 and len(g.verts) == 4]
        if not add:
            break
        fs.update(add)
        if len(fs) > n0 * limit:
            return None
    return list(fs)


def rebuild_region(bm, faces, mw, proj, st, flow=None):
    """선택 면 영역을 다시 채움 → (새 면 목록, 메시지).
    들쭉날쭉한 영역은 파인 칸을 메운 영역도 시도하고, 모서리 후보 여러 개 중 꼬이거나 뒤집힌 칸이 없는
    것을 고른다. 끝내 안 되면 메쉬를 건드리지 않고 알려 줌."""
    faces = [f for f in faces if f.is_valid]
    variants = [faces]
    grown = grow_region(faces)
    if grown is not None and len(grown) != len(faces):
        variants.append(grown)
    err = None
    chosen = None
    for fv in variants:
        lp, e = region_boundary_loop(fv)
        if e:
            err = err or e
            continue
        if len(lp) < 4:
            err = err or "영역이 너무 작습니다"
            continue
        if len(lp) % 2:
            err = err or "경계 버텍스 수가 홀수라 쿼드로만 다시 채울 수 없습니다 (삼각형/오각형이 섞인 영역)"
            continue
        GPv = [mw @ v.co for v in lp]
        idx = list(range(len(lp)))
        ext = boundary_ext_dirs(lp, fv, mw)  # 주변 메쉬에서 들어오는 엣지 → 그 흐름을 이어 가도록
        found = False
        for sides in solve_quad_sides(GPv, (), flow, top=10, ext=ext):
            plan = plan_patch(GPv, idx, set(), proj, st, flow=flow, sides=sides, ext=ext)
            if not grid_tangled(plan[1], proj):
                # 주변 흐름을 얼마나 잇는지 (들쭉날쭉한 원래 영역보다 파인 칸을 메운 영역이 더 자연스러우면 그쪽)
                # (주변 메쉬가 없으면 이을 흐름도 없으므로 만점)
                cont = flow_continuity(GPv, ext, *sides) if any(e is not None for e in ext) else 1.0
                qual = cont - 0.15 * (grid_max_aspect(plan[1]) - 1.0)  # 길쭉한 칸은 감점
                if chosen is None or qual > chosen[3] + 0.02:
                    chosen = (fv, lp, plan, qual)
                found = True
                break
        if not found:
            err = "이 영역 모양으로는 꼬이지 않게 다시 채울 수 없습니다. 더 둥글거나 네모난 영역을 선택하세요 (메쉬는 그대로)"
    if chosen is None:
        return [], err or "다시 채울 수 없습니다"
    faces, loop, plan, _cont = chosen
    N = len(loop)
    mwi = mw.inverted()
    nm = mw.to_3x3().inverted().transposed()
    ref_n = sum(((nm @ f.normal) for f in faces), Vector())
    GP = [mw @ v.co for v in loop]
    fs = set(faces)
    border = {edge_between(loop[k], loop[(k + 1) % N]) for k in range(N)}
    in_edges = [e for f in fs for e in f.edges if e not in border and all(x in fs for x in e.link_faces)]
    bset = set(loop)
    interior = list({v for f in fs for v in f.verts} - bset)
    bmesh.ops.delete(bm, geom=list(fs), context='FACES_ONLY')
    if interior:
        bmesh.ops.delete(bm, geom=interior, context='VERTS')
    left = [e for e in set(in_edges) if e.is_valid and not e.link_faces]
    if left:
        bmesh.ops.delete(bm, geom=left, context='EDGES')
    gi, grid, a, b = plan
    V = []
    for j in range(b + 1):
        row = []
        for i in range(a + 1):
            row.append(loop[gi[j][i]] if gi[j][i] >= 0 else bm.verts.new(mwi @ grid[j][i]))
        V.append(row)
    quads = [(V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]) for j in range(b) for i in range(a)]
    same = opp = 0
    for q in quads:
        s, o = winding_vs_neighbors(list(q))
        same += s
        opp += o
    new = []
    for q in quads:
        if st.snap_creases:
            q = best_quad_order(q, [mw @ v.co for v in q], proj, max(st.spacing, 1e-4))
        try:
            new.append(bm.faces.new(q))
        except ValueError:
            pass
    bm.normal_update()
    if same or opp:
        flip = same > opp
    else:
        flip = bool(new) and sum(((nm @ f.normal) for f in new), Vector()).dot(ref_n) < 0
    if flip:
        for f in new:
            f.normal_flip()
    for x in list(bm.faces):
        x.select = False
    for f in new:
        f.select_set(True)
    bm.select_flush_mode()
    return new, "재구성: 면 %d → %d (%d x %d)" % (len(faces), len(new), a, b)


def offset_region(bm, faces, mw, proj):
    """선택 면 영역 경계 안쪽에 루프를 하나 더(인셋) → 영역 둘레를 따라 흐름이 바뀜."""
    faces = [f for f in faces if f.is_valid]
    if not faces:
        return [], "면을 선택하세요"
    ls = [e.calc_length() for f in faces for e in f.edges]
    t = (sum(ls) / len(ls)) * 0.5
    old = set(bm.verts)
    res = bmesh.ops.inset_region(bm, faces=faces, thickness=t, depth=0.0,
                                 use_even_offset=True, use_boundary=True)
    mwi = mw.inverted()
    if proj.ok:
        for v in bm.verts:
            if v not in old:
                v.co = mwi @ proj.project(mw @ v.co)
    bm.normal_update()
    return res.get("faces", []), "오프셋: 경계 안쪽에 루프 추가 (새 면 %d)" % len(res.get("faces", []))


def point_in_poly(p, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        a, b = poly[i], poly[j]
        if (a.y > p.y) != (b.y > p.y):
            x = a.x + (p.y - a.y) * (b.x - a.x) / ((b.y - a.y) or 1e-12)
            if p.x < x:
                inside = not inside
        j = i
    return inside


def scan_merge(context, objs, spacing, max_faces=150000):
    """여러 오브젝트 표면을 하나로 합쳐 고른 쿼드 리토 메쉬(새 오브젝트)를 만든다 → (오브젝트, 메시지)."""
    objs = [o for o in objs if o is not None and o.type == 'MESH']
    if not objs:
        return None, "메쉬 오브젝트를 선택하세요"
    dg = context.evaluated_depsgraph_get()
    verts, polys = [], []
    area = 0.0
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        base = len(verts)
        verts.extend(mw @ v.co for v in me.vertices)
        polys.extend(tuple(base + i for i in p.vertices) for p in me.polygons)
        ev.to_mesh_clear()
    src = bpy.data.meshes.new("_retopo_scan_src")
    src.from_pydata(verts, [], polys)
    src.update()
    area = sum(p.area for p in src.polygons)
    vs = max(spacing, 1e-4)
    if area / (vs * vs) > max_faces:
        vs = math.sqrt(area / max_faces)  # 너무 촘촘하면 자동으로 키움
    tmp = bpy.data.objects.new("_retopo_scan_tmp", src)
    context.scene.collection.objects.link(tmp)
    try:
        mod = tmp.modifiers.new("scan", 'REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = vs
        mod.adaptivity = 0.0
        dg = context.evaluated_depsgraph_get()
        dg.update()
        new_me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    finally:
        bpy.data.objects.remove(tmp)
        bpy.data.meshes.remove(src)
    name = "Retopo_Scan"
    new_me.name = name
    obj = bpy.data.objects.new(name, new_me)
    context.scene.collection.objects.link(obj)
    # 원래 표면에 붙이고 고르게 + 열린 면(판 등)에서 생긴 뒷면 겹을 지움
    proj = Projector(context, objs, context.scene.retopo_annot.surface_offset)
    bm = bmesh.new()
    bm.from_mesh(new_me)
    for it in range(4):
        if it:
            new_co = {}
            for v in bm.verts:
                if v.link_edges:
                    new_co[v] = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
            for v, co in new_co.items():
                v.co = co
        for v in bm.verts:
            v.co = proj.project(v.co)
    bm.normal_update()
    # 오브젝트별 표면: 두 표면이 겹치는 곳(상자 바닥이 판 위에 놓인 곳 등)에서는 열린 면(판)의 방향을 따름
    per = []
    for o in objs:
        b = BVHTree.FromObject(o, dg)
        ob = bmesh.new()
        ob.from_mesh(o.data)
        is_open = any(e.is_boundary for e in ob.edges)
        ob.free()
        per.append((b, o.matrix_world.copy(), o.matrix_world.inverted(),
                    o.matrix_world.to_3x3().inverted().transposed(), is_open))

    def surf_normal(p):
        best = None
        for b, mw, mwi, nmx, is_open in per:
            loc, nor, _i, d = b.find_nearest(mwi @ p)
            if loc is None:
                continue
            d = (mw @ loc - p).length
            best_d = best[0] if best else 1e30
            if d < best_d - vs * 0.05 or (abs(d - best_d) <= vs * 0.05 and is_open):
                best = (d, (nmx @ nor).normalized())
        return best[1] if best else None
    back = [f for f in bm.faces if (surf_normal(f.calc_center_median()) or f.normal).dot(f.normal) < 0]
    if back and len(back) < len(bm.faces):
        bmesh.ops.delete(bm, geom=back, context='FACES')
    bm.to_mesh(new_me)
    nf = len(bm.faces)
    bm.free()
    new_me.update()
    obj.show_wire = True
    obj.color = (0.2, 0.6, 1.0, 1.0)
    return obj, "스캔 합치기: 오브젝트 %d개 → 리토 메쉬 면 %d개 (칸 크기 %.3g)" % (len(objs), nf, vs)


def chain_strokes(strokes, join):
    remaining = [list(s) for s in strokes]
    chains = []
    while remaining:
        cur = remaining.pop(0)
        parts = 1
        changed = True
        while changed:
            changed = False
            for k, s in enumerate(remaining):
                if (cur[-1] - s[0]).length < join:
                    cur = cur + s[1:]
                elif (cur[-1] - s[-1]).length < join:
                    cur = cur + list(reversed(s))[1:]
                elif (cur[0] - s[-1]).length < join:
                    cur = s[:-1] + cur
                elif (cur[0] - s[0]).length < join:
                    cur = list(reversed(s))[:-1] + cur
                else:
                    continue
                remaining.pop(k)
                parts += 1
                changed = True
                break
        chains.append((cur, parts))
    return chains


# 마지막 변환 기록: 밀도를 바꾸면 이 기록으로 다시 생성
_last = {"obj": None, "snap": None, "strokes": None, "mode": None, "batch": True,
         "region": None, "rv3d": None, "sig": None}


def _mesh_signature(obj):
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        s = Vector()
        for v in bm.verts:
            s += v.co
        return (len(bm.verts), len(bm.edges), len(bm.faces), tuple(round(x, 5) for x in s))
    me = obj.data
    s = Vector()
    for v in me.vertices:
        s += v.co
    return (len(me.vertices), len(me.edges), len(me.polygons), tuple(round(x, 5) for x in s))


def _snapshot(obj):
    if obj.mode == 'EDIT':
        return bmesh.from_edit_mesh(obj.data).copy()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def _restore(obj, snap):
    tmp = bpy.data.meshes.new("_retopo_tmp")
    snap.to_mesh(tmp)
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        bm.clear()
        bm.from_mesh(tmp)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
    else:
        obj.data.clear_geometry()
        snap.to_mesh(obj.data)
    bpy.data.meshes.remove(tmp)


# ---------------------------------------------------------------------------
# 이어짐 / 새로 생성 표시
#  - 에디트 모드에서 리토 메쉬의 열린 테두리(와이어 포함)를 초록으로: 여기서 선을 시작/끝내면 기존 메쉬에 이어짐
#  - 변환 직후 새로 생긴 면을 1.5초 강조: 초록 "이어서 생성" / 주황 "따로 생성"
# ---------------------------------------------------------------------------

CONN_COLOR = (0.25, 1.0, 0.45)
NEW_COLOR = (1.0, 0.62, 0.15)
FLASH_TIME = 1.5
_flash = {"data": None}
_border = {"key": None, "lines": []}


def _read_bm(obj):
    if obj.mode == 'EDIT':
        return bmesh.from_edit_mesh(obj.data), False
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm, True


def _open_verts(bm):
    return [v.co.copy() for v in bm.verts
            if any(len(e.link_faces) < 2 for e in v.link_edges) or not v.link_edges]


def make_flash(obj, snap, stats):
    """snap(변환 전) 과 비교해 새로 생긴 면/엣지를 찾아 강조 데이터를 만든다."""
    _flash["data"] = None
    try:
        st = bpy.context.scene.retopo_annot
        if not st.show_connect:
            return
    except Exception:
        return
    old_fc = kdtree.KDTree(max(len(snap.faces), 1))
    for i, f in enumerate(snap.faces):
        old_fc.insert(f.calc_center_median(), i)
    old_fc.balance()
    old_ed = kdtree.KDTree(max(len(snap.edges), 1))
    for i, e in enumerate(snap.edges):
        old_ed.insert((e.verts[0].co + e.verts[1].co) * 0.5, i)
    old_ed.balance()
    ov = _open_verts(snap)
    old_open = kdtree.KDTree(max(len(ov), 1))
    for i, co in enumerate(ov):
        old_open.insert(co, i)
    old_open.balance()
    bm, own = _read_bm(obj)
    try:
        eps = max(st.spacing, 1e-4) * 0.01
        mw = obj.matrix_world
        tris, lines, pts = [], [], []
        connected = stats.get("cuts", 0) > 0

        def is_old(tree, n, co):
            if n == 0:
                return False
            hit = tree.find(co)
            return hit[2] is not None and hit[2] < eps

        for f in bm.faces:
            if is_old(old_fc, len(snap.faces), f.calc_center_median()):
                continue
            cos = [mw @ v.co for v in f.verts]
            for k in range(1, len(cos) - 1):
                tris += [cos[0], cos[k], cos[k + 1]]
            for k in range(len(cos)):
                lines += [cos[k], cos[(k + 1) % len(cos)]]
            pts += cos
            if not connected and any(is_old(old_open, len(ov), v.co) for v in f.verts):
                connected = True
        for e in bm.edges:
            if e.link_faces or is_old(old_ed, len(snap.edges), (e.verts[0].co + e.verts[1].co) * 0.5):
                continue
            a, b = mw @ e.verts[0].co, mw @ e.verts[1].co
            lines += [a, b]
            pts += [a, b]
            if not connected and any(is_old(old_open, len(ov), v.co) for v in e.verts):
                connected = True
        if not pts:
            return
        center = sum(pts, Vector()) / len(pts)
        label = "컷" if stats.get("cuts", 0) > 0 else ("이어서 생성" if connected else "따로 생성")
        _flash["data"] = {"tris": tris, "lines": lines, "center": center, "label": label,
                          "color": CONN_COLOR if connected else NEW_COLOR, "t": time.monotonic()}
        if not bpy.app.timers.is_registered(_flash_tick):
            bpy.app.timers.register(_flash_tick, first_interval=0.05)
    finally:
        if own:
            bm.free()


def _redraw_3d():
    try:
        for win in bpy.context.window_manager.windows:
            for a in win.screen.areas:
                if a.type == 'VIEW_3D':
                    a.tag_redraw()
    except Exception:
        pass


def _flash_tick():
    _redraw_3d()
    d = _flash["data"]
    if d is None or time.monotonic() - d["t"] > FLASH_TIME:
        _flash["data"] = None
        _redraw_3d()
        return None
    return 0.05


def _border_lines(obj):
    """리토 메쉬의 열린 테두리/와이어 엣지 (월드 좌표). 메쉬가 바뀔 때만 다시 계산."""
    bm = bmesh.from_edit_mesh(obj.data)
    key = (obj.name, len(bm.verts), len(bm.edges), len(bm.faces), _border.get("dirty", 0),
           tuple(round(x, 4) for x in obj.matrix_world.translation))
    if _border["key"] == key:
        return _border["lines"]
    mw = obj.matrix_world
    lines = []
    for e in bm.edges:
        if len(e.link_faces) < 2 and not e.hide:
            lines += [mw @ e.verts[0].co, mw @ e.verts[1].co]
    _border.update(key=key, lines=lines)
    return lines


def _conn_obj(context):
    st = getattr(context.scene, "retopo_annot", None)
    if st is None or not st.show_connect:
        return None, None
    obj = context.edit_object
    if obj is None or obj.type != 'MESH' or st.retopo is None or obj.name != st.retopo.name:
        return st, None
    return st, obj


def _draw_view():
    try:
        import gpu
        from gpu_extras.batch import batch_for_shader
        context = bpy.context
        st, obj = _conn_obj(context)
        if st is None:
            return
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')
        if obj is not None:
            lines = _border_lines(obj)
            if lines:
                gpu.state.line_width_set(3.0)
                shader.bind()
                shader.uniform_float("color", (*CONN_COLOR, 0.85))
                batch_for_shader(shader, 'LINES', {"pos": lines}).draw(shader)
        d = _flash["data"]
        if d is not None:
            a = max(0.0, 1.0 - (time.monotonic() - d["t"]) / FLASH_TIME)
            shader.bind()
            if d["tris"]:
                shader.uniform_float("color", (*d["color"], 0.35 * a))
                batch_for_shader(shader, 'TRIS', {"pos": d["tris"]}).draw(shader)
            if d["lines"]:
                gpu.state.line_width_set(2.0)
                shader.uniform_float("color", (*d["color"], a))
                batch_for_shader(shader, 'LINES', {"pos": d["lines"]}).draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')
    except Exception as ex:  # 그리기 오류로 뷰포트가 멈추지 않게
        print("[RetopoAnnotate] draw", ex)


def _draw_pixel():
    try:
        import blf
        context = bpy.context
        st, obj = _conn_obj(context)
        if st is None:
            return
        region, rv3d = context.region, context.region_data
        font = 0
        blf.size(font, 13)
        if obj is not None:
            blf.color(font, *CONN_COLOR, 0.9)
            blf.position(font, 16, 40, 0)
            blf.draw(font, "초록 테두리에서 시작/끝 = 이어서 생성")
        if st.next_mode != 'NONE' and context.mode == 'EDIT_MESH':
            names = {'REGION': "영역 둘러싸기", 'FLOW': "흐름 선 (선택 영역 위에 흐름 방향으로)", 'CUT': "컷 선"}
            blf.size(font, 16)
            blf.color(font, 1.0, 0.85, 0.2, 1.0)
            blf.position(font, 16, 64, 0)
            blf.draw(font, "다음 선 = " + names.get(st.next_mode, st.next_mode) + "  (한 번만)")
            blf.size(font, 13)
        d = _flash["data"]
        if d is not None and region is not None and rv3d is not None:
            p = location_3d_to_region_2d(region, rv3d, d["center"])
            if p is not None:
                a = max(0.0, 1.0 - (time.monotonic() - d["t"]) / FLASH_TIME)
                blf.size(font, 20)
                w, _h = blf.dimensions(font, d["label"])
                blf.color(font, 0, 0, 0, 0.7 * a)
                blf.position(font, p.x - w / 2 + 1, p.y - 1, 0)
                blf.draw(font, d["label"])
                blf.color(font, *d["color"], a)
                blf.position(font, p.x - w / 2, p.y, 0)
                blf.draw(font, d["label"])
    except Exception as ex:
        print("[RetopoAnnotate] draw text", ex)


_draw_handles = []


def run_and_record(context, strokes, mode, batch, region, rv3d):
    obj = ensure_retopo_object(context)
    snap = _snapshot(obj)
    conv = Converter(context, region, rv3d)
    stats = conv.run(strokes, mode, batch=batch)
    try:
        make_flash(obj, snap, stats)
    except Exception as ex:
        print("[RetopoAnnotate] flash", ex)
    old = _last.get("snap")
    if old is not None:
        old.free()
    _last.update(obj=obj.name, snap=snap, strokes=[[p.copy() for p in s] for s in strokes],
                 mode=mode, batch=batch, region=region, rv3d=rv3d, sig=_mesh_signature(obj))
    return stats


def redo_last(context):
    """마지막 변환을 현재 밀도 설정으로 다시 생성. 성공하면 True."""
    st = context.scene.retopo_annot
    obj = st.retopo
    if obj is None or _last["snap"] is None or obj.name != _last["obj"]:
        return False
    if _mesh_signature(obj) != _last["sig"]:
        return False  # 그 사이 사용자가 메쉬를 수정함 → 덮어쓰지 않음
    _restore(obj, _last["snap"])
    snap = _last["snap"]
    _last["snap"] = None
    try:
        run_and_record(context, _last["strokes"], _last["mode"], _last["batch"],
                       _last["region"], _last["rv3d"])
    finally:
        snap.free()
    return True


def convert_now(context, mode, batch, area=None, region=None, rv3d=None):
    scene = context.scene
    st = scene.retopo_annot
    junk = []
    refs = collect_strokes(scene, junk)
    if not refs:
        if junk and st.clear_after:
            remove_strokes(junk)  # 클릭으로 찍힌 점은 변환할 수 없으니 화면에서 치움
        return None
    if region is None:
        area, region, rv3d = find_view3d(context)
    stats = run_and_record(context, [r.points for r in refs], mode, batch, region, rv3d)
    if st.clear_after:
        remove_strokes(refs + junk)
    for win in context.window_manager.windows:
        for a in win.screen.areas:
            if a.type == 'VIEW_3D':
                a.tag_redraw()
    return stats

def can_redo(context):
    st = context.scene.retopo_annot
    obj = st.retopo
    return (obj is not None and _last["snap"] is not None and obj.name == _last["obj"]
            and _mesh_signature(obj) == _last["sig"])


def stats_text(s):
    if s.get("message"):
        return s["message"]
    if s.get("regions"):
        return "영역 선택: 면 %d개 (촘촘하게/성기게/고르게 재구성 버튼이 이 영역에 적용됨)" % s.get("selected", 0)
    return ("엣지 {edges} / 채우기 {fills} / 두 선 사이 {lofts} / 연장 {extrudes} / 스트립 {strips} / "
            "컨투어 {contours} / 컷 {cuts} / 면 {faces}").format(**s)


def _status(msg, seconds=4.0):
    """상태 표시줄에 잠깐 메시지 (자동 변환은 보고창이 없으므로)."""
    try:
        for win in bpy.context.window_manager.windows:
            win.workspace.status_text_set(msg)

        def clear():
            try:
                for w in bpy.context.window_manager.windows:
                    w.workspace.status_text_set(None)
            except Exception:
                pass
            return None
        bpy.app.timers.register(clear, first_interval=seconds)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

def _upd_ann_style(self, context):
    ann = get_annotation(context.scene)
    if ann is None:
        return
    for layer in ann.layers:
        layer.annotation_opacity = self.ann_opacity
        layer.thickness = self.ann_thickness
        layer.color = self.ann_color
    context.scene.tool_settings.annotation_thickness = self.ann_thickness


def _upd_hide(self, context):
    ann = get_annotation(context.scene)
    if ann is not None:
        for layer in ann.layers:
            layer.annotation_hide = self.ann_hide


def _upd_display(self, context):
    if self.retopo is not None:
        self.retopo.show_in_front = self.show_in_front
        self.retopo.show_wire = self.show_wire


def _upd_density(self, context):
    if self.redo_on_change:
        try:
            redo_last(context)
        except Exception as ex:
            print("[RetopoAnnotate] redo", ex)


def _upd_symmetry(self, context):
    apply_symmetry(self)


def apply_symmetry(st):
    obj = st.retopo
    if obj is None:
        return
    mod = obj.modifiers.get("Retopo Mirror")
    if st.symmetry_x and mod is None:
        mod = obj.modifiers.new("Retopo Mirror", 'MIRROR')
        mod.use_axis[0] = True
        mod.use_clip = True
        mod.use_mirror_merge = True
        mod.show_on_cage = True
        mod.show_in_editmode = True
    elif not st.symmetry_x and mod is not None:
        obj.modifiers.remove(mod)


def _upd_target(self, context):
    invalidate_bvh()


def _poll_mesh(self, obj):
    return obj.type == 'MESH'


class RetopoAnnotSettings(bpy.types.PropertyGroup):
    target: PointerProperty(name="타겟(하이폴리)", type=bpy.types.Object, poll=_poll_mesh,
                            update=_upd_target)
    target_type: EnumProperty(
        name="타겟 종류", default='OBJECT', update=_upd_target,
        items=[('OBJECT', "오브젝트", "메쉬 오브젝트 하나를 타겟으로"),
               ('COLLECTION', "컬렉션", "컬렉션(하위 포함) 안의 보이는 메쉬 전부를 타겟으로")])
    target_collection: PointerProperty(name="타겟 컬렉션", type=bpy.types.Collection, update=_upd_target)
    retopo: PointerProperty(name="리토폴로지 메쉬", type=bpy.types.Object, poll=_poll_mesh)
    mode: EnumProperty(
        name="변환 모드",
        items=[
            ('AUTO', "자동", "메쉬를 가로지르면 컷, 형태 밖→안→밖으로 가로지르면 컨투어, 선택 엣지가 있으면 그 선까지 연장, 닫힌 도형이면 채우기, 그 외 엣지"),
            ('POLYSTRIP', "폴리스트립", "그은 선을 따라 폭이 있는 쿼드 띠 (기존 경계에서 시작하면 붙음)"),
            ('CONTOUR', "컨투어", "팔/다리 같은 원통형을 가로질러 그으면 둘레 링. 링이 선택돼 있으면 사이를 채움"),
            ('EDGES', "엣지", "그은 선을 엣지로"),
            ('FILL', "도형 채우기", "그린 모양대로 쿼드 메쉬 생성"),
            ('LOFT', "두 선 사이", "두 선 사이를 쿼드로 채움"),
            ('CUT', "컷", "그은 선대로 메쉬를 자름"),
            ('REGION', "영역 선택", "둘러싼 곳의 면을 선택 → 촘촘하게/성기게/고르게 재구성 버튼을 그 영역에 적용"),
            ('FLOW', "흐름 재구성", "선택한 면 영역을 그은 선 방향으로 엣지가 흐르도록 다시 채움 (바깥 경계는 그대로)"),
        ],
        default='AUTO')
    density_mode: EnumProperty(
        name="밀도 방식",
        items=[('LENGTH', "엣지 길이", "원하는 엣지 길이로 자동 분할"),
               ('COUNT', "분할 수", "가로/세로 분할 수를 직접 지정"),
               ('AVERAGE', "평균", "선택한 엣지(없으면 경계 엣지)의 평균 길이로 분할 → 기존 메쉬와 같은 크기의 쿼드")],
        default='LENGTH', update=_upd_density)
    strip_width: FloatProperty(name="스트립 폭", default=0.0, min=0.0, soft_max=2.0, unit='LENGTH', precision=3,
                               update=_upd_density,
                               description="폴리스트립 폭 (0 = 엣지 길이와 같게). 기존 면에 붙으면 그 폭을 이어받음")
    symmetry_x: BoolProperty(name="대칭 X", default=False, update=_upd_symmetry,
                             description="리토 메쉬에 X축 미러(중앙 클리핑/병합)를 적용")
    redo_on_change: BoolProperty(name="마지막 메쉬에 바로 적용", default=True,
                                 description="밀도를 바꾸면 방금 만든 메쉬를 새 밀도로 다시 생성")
    count_u: IntProperty(name="가로 분할", default=6, min=1, max=200, update=_upd_density,
                         description="채우기/두 선 사이: 가로 방향 면 개수")
    count_v: IntProperty(name="세로 분할", default=6, min=1, max=200, update=_upd_density,
                         description="채우기/두 선 사이: 세로 방향 면 개수")
    count_edge: IntProperty(name="선 분할", default=8, min=1, max=500, update=_upd_density,
                            description="엣지 모드: 선 하나를 몇 칸으로 나눌지")
    spacing: FloatProperty(name="엣지 길이", default=0.1, min=0.001, soft_max=2.0, update=_upd_density,
                           unit='LENGTH', precision=3)
    merge_dist: FloatProperty(name="병합 거리", default=0.03, min=0.0, soft_max=0.5,
                              unit='LENGTH', precision=3)
    surface_offset: FloatProperty(name="표면 띄우기", default=0.001, min=0.0, soft_max=0.05,
                                  unit='LENGTH', precision=4)
    relax_iterations: IntProperty(name="이완 반복", default=3, min=0, max=50)
    auto_quad: BoolProperty(name="자동 쿼드 채우기", default=True,
                            description="버텍스 익스트루드/엣지 연결로 4버텍스가 이어지면 자동으로 면 생성")
    live: BoolProperty(name="자동 변환", default=True,
                       description="주석을 그으면 즉시 메쉬로 변환")
    clear_after: BoolProperty(name="변환 후 주석 삭제", default=True,
                              description="변환된 주석을 지워 화면을 깨끗하게 유지")
    ann_opacity: FloatProperty(name="주석 불투명도", default=0.8, min=0.05, max=1.0,
                               update=_upd_ann_style)
    ann_thickness: IntProperty(name="주석 두께", default=2, min=1, max=10, update=_upd_ann_style)
    ann_color: FloatVectorProperty(name="주석 색", subtype='COLOR', size=3, min=0, max=1,
                                   default=(1.0, 0.35, 0.1), update=_upd_ann_style)
    ann_hide: BoolProperty(name="주석 숨기기", default=False, update=_upd_hide)
    show_in_front: BoolProperty(name="메쉬 앞에 표시", default=True, update=_upd_display)
    show_wire: BoolProperty(name="와이어 표시", default=True, update=_upd_display)
    next_mode: EnumProperty(
        name="다음 선",
        items=[('NONE', "없음", ""), ('REGION', "영역 선택", ""), ('FLOW', "흐름 재구성", ""), ('CUT', "컷", "")],
        default='NONE',
        description="한 번만: 다음에 긋는 주석 선을 이 방식으로 처리한 뒤 원래 모드로 돌아감")
    snap_creases: BoolProperty(name="꺾이는 곳 교차선에 맞춤", default=True,
                               description="선이 다른 면/오브젝트로 꺾여 넘어가는 곳에 버텍스를 두 표면의 교차선 위에 "
                                           "놓아 메쉬가 모서리에서 떠 있지 않게 함")
    show_connect: BoolProperty(name="이어짐 표시", default=True, update=lambda s, c: _redraw_3d(),
                               description="열린 테두리를 초록으로 표시하고, 새로 만든 메쉬가 기존 메쉬에 "
                                           "이어졌는지(초록) 따로 생성됐는지(주황) 잠깐 강조")


# ---------------------------------------------------------------------------
# 오퍼레이터
# ---------------------------------------------------------------------------

def _set_snap(ts):
    ts.use_snap = True
    for elems in ({'FACE_PROJECT'}, {'FACE_NEAREST'}, {'FACE'}):
        try:
            ts.snap_elements = elems
            break
        except (TypeError, ValueError):
            continue
    for attr, val in (("use_snap_self", False), ("use_snap_project", True)):
        if hasattr(ts, attr):
            try:
                setattr(ts, attr, val)
            except (TypeError, AttributeError):
                pass


class RETOPO_OT_setup(bpy.types.Operator):
    bl_idname = "retopo.setup"
    bl_label = "리토폴로지 시작"
    bl_description = "선택한 하이폴리를 타겟으로, 새 리토폴로지 메쉬/스냅/주석을 설정"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        st = context.scene.retopo_annot
        act = context.active_object
        if st.target_type == 'COLLECTION':
            if st.target_collection is None:
                # 지정한 컬렉션이 없으면 선택한 오브젝트가 들어 있는 컬렉션을 사용
                if act is not None and act.users_collection and act.users_collection[0] != context.scene.collection:
                    st.target_collection = act.users_collection[0]
                elif context.collection is not None and context.collection != context.scene.collection:
                    st.target_collection = context.collection
            if not has_target(st):
                self.report({'WARNING'}, "타겟 컬렉션을 지정하세요 (안에 보이는 메쉬가 있어야 함)")
                return {'CANCELLED'}
        else:
            if act is not None and act.type == 'MESH' and act != st.retopo:
                st.target = act
            if st.target is None:
                self.report({'WARNING'}, "타겟 메쉬를 선택하세요")
                return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        st.retopo = None
        obj = ensure_retopo_object(context)
        invalidate_bvh()
        ts = context.scene.tool_settings
        _set_snap(ts)
        ts.use_mesh_automerge = True
        ts.double_threshold = st.merge_dist
        ts.annotation_stroke_placement_view3d = 'SURFACE'
        ann = ensure_annotation(context.scene)
        _upd_ann_style(st, context)
        apply_symmetry(st)
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            bpy.ops.wm.tool_set_by_id(name="builtin.annotate")
        except Exception:
            pass
        self.report({'INFO'}, "리토폴로지 준비 완료: 주석으로 그리세요")
        return {'FINISHED'}


class RETOPO_OT_convert(bpy.types.Operator):
    bl_idname = "retopo.convert_annotations"
    bl_label = "주석 → 메쉬 변환"
    bl_description = "현재 주석 선들을 설정된 모드로 엣지/메쉬/컷으로 변환"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(items=[('SETTING', "설정값", ""), ('AUTO', "자동", ""), ('EDGES', "엣지", ""),
                              ('FILL', "채우기", ""), ('LOFT', "두 선 사이", ""), ('CUT', "컷", ""),
                              ('POLYSTRIP', "폴리스트립", ""), ('CONTOUR', "컨투어", ""),
                              ('REGION', "영역 선택", ""), ('FLOW', "흐름 재구성", "")],
                       default='SETTING')

    def execute(self, context):
        st = context.scene.retopo_annot
        mode = st.mode if self.mode == 'SETTING' else self.mode
        if self.mode == 'SETTING' and st.next_mode != 'NONE':
            mode = st.next_mode
            st.next_mode = 'NONE'
        stats = convert_now(context, mode, batch=True)
        if stats is None:
            self.report({'WARNING'}, "변환할 주석이 없습니다 (주석 툴로 그려주세요)")
            return {'CANCELLED'}
        self.report({'INFO'}, stats_text(stats))
        return {'FINISHED'}


class RETOPO_OT_live(bpy.types.Operator):
    bl_idname = "retopo.live_mode"
    bl_label = "자동 변환"
    bl_description = "켜져 있으면 주석 선을 다 긋는 즉시 메쉬로 변환하고 주석을 지웁니다"

    def execute(self, context):
        st = context.scene.retopo_annot
        st.live = not st.live
        return {'FINISHED'}


def _annotating(win):
    try:
        for op in win.modal_operators:
            if op.bl_idname.startswith(("GPENCIL_OT_annotate", "ANNOTATION_OT", "TRANSFORM_OT")):
                return True
    except AttributeError:
        pass
    return False


_loft_wait = {"shown": False}


def _auto_convert_tick():
    """주석 스트로크가 완성되면 바로 변환 (자동 변환이 켜진 경우)."""
    try:
        wm = bpy.context.window_manager
        if _just_undone() or _undo_state["kind"] is not None:
            return 0.15  # 되돌리기 직후 되살아난 주석은 _undo_fix 가 처리 (다시 변환하지 않음)
        for win in wm.windows:
            scene = win.scene
            st = getattr(scene, "retopo_annot", None)
            if st is None or not st.live or _annotating(win):
                continue
            if stroke_count(scene) == 0:
                continue
            area = max((a for a in win.screen.areas if a.type == 'VIEW_3D'),
                       key=lambda a: a.width * a.height, default=None)
            if area is None:
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            rv3d = area.spaces.active.region_3d
            with bpy.context.temp_override(window=win, area=area, region=region):
                try:
                    one_shot = st.next_mode != 'NONE'
                    mode = st.next_mode if one_shot else st.mode
                    if mode == 'LOFT' and len(collect_strokes(scene)) < 2:
                        # 두 선 사이: 첫 선은 주석으로 남겨 두고 두 번째 선을 기다림
                        if not _loft_wait["shown"]:
                            _loft_wait["shown"] = True
                            _status("두 선 사이: 두 번째 선을 그으세요", 4.0)
                        continue
                    _loft_wait["shown"] = False
                    stats = convert_now(bpy.context, mode, batch=False, region=region, rv3d=rv3d)
                    if stats:
                        if one_shot:
                            st.next_mode = 'NONE'  # 한 번만 쓰고 원래 모드로
                        bpy.ops.ed.undo_push(message="Retopo 주석 변환")
                        if mode in ('REGION', 'FLOW') or stats.get("message"):
                            _status(stats_text(stats))
                except Exception as ex:  # 자동 변환은 멈추지 않음
                    print("[RetopoAnnotate]", ex)
                    clear_all_annotations(scene)
    except Exception as ex:
        print("[RetopoAnnotate] tick", ex)
    return 0.15

class RETOPO_OT_quad_extrude(bpy.types.Operator):
    bl_idname = "retopo.quad_extrude"
    bl_label = "쿼드 익스트루드"
    bl_description = ("선택 버텍스를 익스트루드. 옆 버텍스가 이미 익스트루드 되어 있거나 안쪽 모서리면 "
                      "인접 4버텍스로 즉시 면 생성")
    bl_options = {'REGISTER', 'UNDO'}

    grab: BoolProperty(name="이동 시작", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        return self.run(context, interactive=True)

    def execute(self, context):
        return self.run(context, interactive=False)

    def run(self, context, interactive):
        st = context.scene.retopo_annot
        obj = context.edit_object
        mw = obj.matrix_world
        mwi = mw.inverted()
        bm = bmesh.from_edit_mesh(obj.data)
        proj = Projector(context, st, st.surface_offset)

        def P(co_local):
            return mwi @ proj.project(mw @ co_local)

        sel = [v for v in bm.verts if v.select and not v.hide]
        if not sel:
            self.report({'WARNING'}, "버텍스를 선택하세요")
            return {'CANCELLED'}
        spacing_local = st.spacing / max(sum(abs(x) for x in mw.to_scale()) / 3, 1e-9)
        new_verts = []
        spikes = []
        for v in sel:
            nv = self._extrude_one(bm, v, P, spacing_local, mw, proj, spikes)
            if nv is not None:
                new_verts.append(nv)
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        for v in new_verts:
            v.select = True
        bm.select_flush(True)
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        if interactive and self.grab and spikes:
            bpy.ops.transform.translate('INVOKE_DEFAULT')
        return {'FINISHED'}

    def _extrude_one(self, bm, v, P, spacing, mw, proj, spikes):
        # 1) 이웃 n 이 이미 m 쪽으로 익스트루드 되어 있으면 → (v, n, m, v') 쿼드
        best = None
        for en in open_edges(v):
            n = en.other_vert(v)
            for em in open_edges(n):
                m = em.other_vert(n)
                if m is v or edge_between(m, v):
                    continue
                d = m.co - n.co
                side = v.co - n.co
                if d.length < 1e-9 or side.length < 1e-9:
                    continue
                ang = d.angle(side, 0.0)
                if not (math.radians(40) < ang < math.radians(140)):
                    continue
                order = [v, n, m]
                same, opp = winding_vs_neighbors(order)
                if same and opp:
                    continue
                cand = v.co + d
                if not quad_ok([v.co, n.co, m.co, cand]):
                    continue
                # 이미 면 쪽으로 들어가는 방향 제외 (v의 면 중심 반대쪽이어야 함)
                if v.link_faces:
                    c = sum((f.calc_center_median() for f in v.link_faces), Vector()) / len(v.link_faces)
                    if d.dot(v.co - c) <= 0:
                        continue
                score = 1.0 if not em.link_faces else 0.5  # 가시(wire) 우선
                if best is None or score > best[0]:
                    best = (score, n, m, d)
        if best is not None:
            _s, n, m, d = best
            nv = bm.verts.new(P(v.co + d))
            order = [v, n, m, nv]
            same, _opp = winding_vs_neighbors(order[:3])
            if same:
                order.reverse()
            try:
                f = bm.faces.new(order)
                orient_new_face(f, mw, proj)
            except ValueError:
                pass
            return nv

        # 2) 안쪽 모서리(L자): 두 경계 이웃이 다른 면 소속 & 각도 < 150도 → 평행사변형 쿼드
        bnb = [e for e in open_edges(v) if e.link_faces]
        if len(bnb) == 2:
            e1, e2 = bnb
            if not (set(e1.link_faces) & set(e2.link_faces)):
                n1, n2 = e1.other_vert(v), e2.other_vert(v)
                ang = (n1.co - v.co).angle(n2.co - v.co, 0.0)
                if ang < math.radians(150):
                    cand = n1.co + n2.co - v.co
                    order = [v, n1, None, n2]
                    nv = bm.verts.new(P(cand))
                    order[2] = nv
                    if quad_ok([x.co for x in order]):
                        same, opp = winding_vs_neighbors(order)
                        if same and not opp:
                            order.reverse()
                        try:
                            f = bm.faces.new(order)
                            orient_new_face(f, mw, proj)
                            return nv
                        except ValueError:
                            pass
                    bm.verts.remove(nv)

        # 3) 일반 익스트루드: 바깥 방향으로 가시 버텍스 생성 후 이동
        if v.link_faces:
            c = sum((f.calc_center_median() for f in v.link_faces), Vector()) / len(v.link_faces)
            d = v.co - c
        else:
            nbs = [e.other_vert(v).co for e in v.link_edges]
            if nbs:
                avg = sum(nbs, Vector()) / len(nbs)
                d = v.co - avg
                if d.length < 1e-6:
                    tang = (nbs[0] - v.co)
                    nrm = proj.normal(mw @ v.co) if proj.ok else Vector((0, 0, 1))
                    nrm = mw.to_3x3().inverted() @ nrm
                    d = tang.cross(nrm)
            else:
                d = Vector((0, 0, 1))
        if d.length < 1e-9:
            d = Vector((0, 0, 1))
        nv = bm.verts.new(P(v.co + d.normalized() * spacing))
        bm.edges.new((v, nv))
        spikes.append(nv)
        return nv


class RETOPO_OT_fill_quads(bpy.types.Operator):
    bl_idname = "retopo.fill_quads"
    bl_label = "4버텍스 면 채우기"
    bl_description = "선택(없으면 전체) 버텍스 주변의 닫힌 4버텍스 루프와 익스트루드 가시를 면으로 채움"
    bl_options = {'REGISTER', 'UNDO'}

    only_selected: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        st = context.scene.retopo_annot
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        seeds = [v for v in bm.verts if v.select] if self.only_selected else list(bm.verts)
        if not seeds:
            seeds = list(bm.verts)
        proj = Projector(context, st, st.surface_offset)
        faces = auto_fill(bm, seeds, obj.matrix_world, proj)
        if not faces:
            return {'CANCELLED'}
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        self.report({'INFO'}, "면 %d개 생성" % len(faces))
        return {'FINISHED'}


class RETOPO_OT_project(bpy.types.Operator):
    bl_idname = "retopo.project_selected"
    bl_label = "표면에 붙이기"
    bl_description = "선택한(없으면 전체) 버텍스를 타겟 표면에 투영"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and has_target(context.scene.retopo_annot)

    def execute(self, context):
        st = context.scene.retopo_annot
        obj = context.edit_object
        mw = obj.matrix_world
        mwi = mw.inverted()
        bm = bmesh.from_edit_mesh(obj.data)
        proj = Projector(context, st, st.surface_offset)
        vs = [v for v in bm.verts if v.select] or list(bm.verts)
        for v in vs:
            v.co = mwi @ proj.project(mw @ v.co)
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class RETOPO_OT_relax(bpy.types.Operator):
    bl_idname = "retopo.relax"
    bl_label = "이완 (Relax)"
    bl_description = "선택한(없으면 전체) 버텍스 간격을 고르게 펴고 타겟 표면에 다시 붙임"
    bl_options = {'REGISTER', 'UNDO'}

    iterations: IntProperty(name="반복", default=5, min=1, max=100)
    strength: FloatProperty(name="강도", default=0.5, min=0.0, max=1.0)
    boundary: EnumProperty(name="경계", default='EXCLUDE', items=[
        ('EXCLUDE', "고정", "경계 버텍스는 움직이지 않음"),
        ('SLIDE', "경계 따라", "경계 버텍스는 경계를 따라서만 이동"),
        ('INCLUDE', "포함", "경계도 함께 이완")])

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        st = context.scene.retopo_annot
        obj = context.edit_object
        mw = obj.matrix_world
        mwi = mw.inverted()
        bm = bmesh.from_edit_mesh(obj.data)
        proj = Projector(context, st, st.surface_offset)
        vs = [v for v in bm.verts if v.select and not v.hide] or [v for v in bm.verts if not v.hide]
        for _ in range(self.iterations):
            new = {}
            for v in vs:
                edge_bound = v.is_boundary or v.is_wire
                if edge_bound and self.boundary == 'EXCLUDE':
                    continue
                if edge_bound and self.boundary == 'SLIDE':
                    nbs = [e.other_vert(v).co for e in v.link_edges if e.is_boundary or e.is_wire]
                else:
                    nbs = [e.other_vert(v).co for e in v.link_edges]
                if len(nbs) < 2:
                    continue
                avg = sum(nbs, Vector()) / len(nbs)
                new[v] = v.co.lerp(avg, self.strength)
            for v, co in new.items():
                v.co = mwi @ proj.project(mw @ co) if proj.ok else co
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class RETOPO_OT_crease(bpy.types.Operator):
    bl_idname = "retopo.crease_path"
    bl_label = "주름 만들기"
    bl_description = ("선택한 버텍스들을 선택한 순서대로 잇는 경로로 메쉬를 컷하고, "
                      "컷하면서 생긴 버텍스 중 가까운 것은 자동으로 합칩니다")
    bl_options = {'REGISTER', 'UNDO'}

    merge_ratio: FloatProperty(name="합치기 거리", default=0.35, min=0.0, max=0.49, subtype='FACTOR',
                               description="컷으로 생긴 버텍스가 원래 버텍스에 엣지 길이의 이 비율 안으로 가까우면 합침")
    closed: BoolProperty(name="처음과 끝 잇기", default=False)
    crease: BoolProperty(name="경로에 크리즈(주름 강조)", default=False,
                         description="만든 경로 엣지에 크리즈 1.0 을 지정 (서브디비전에서 주름이 날카롭게 유지)")

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        sel = [v for v in bm.verts if v.select and not v.hide]
        if len(sel) < 2:
            self.report({'WARNING'}, "주름을 지나갈 버텍스를 2개 이상 선택하세요 (클릭한 순서대로 이어짐)")
            return {'CANCELLED'}
        hist = [e for e in bm.select_history if isinstance(e, bmesh.types.BMVert) and e.select]
        order = hist if len(hist) == len(sel) else order_points(sel)
        _area, region, rv3d = find_view3d(context)
        if region is None:
            self.report({'WARNING'}, "3D 뷰가 필요합니다")
            return {'CANCELLED'}
        r = make_crease(context, obj, bm, order, region, rv3d, self.merge_ratio, self.closed, self.crease)
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        self.report({'INFO'}, "주름: 구간 %d / 컷 %d / 합친 버텍스 %d" % (r["segments"], r["cuts"], r["merged"]))
        return {'FINISHED'}


class RETOPO_OT_fill_gap(bpy.types.Operator):
    bl_idname = "retopo.fill_gap"
    bl_label = "빈 곳 채우기"
    bl_description = ("스트립 사이 등 빈 곳을 둘러싼 경계 버텍스를 선택하고 누르면, 기존 버텍스를 그대로 써서 "
                      "쿼드로 채웁니다. U자 안쪽처럼 한쪽이 트인 곳은 입구 양 끝 버텍스 2개만 골라도 됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        snap = _snapshot(obj)
        try:
            n, msg = fill_gap(context, obj)
            if n:
                make_flash(obj, snap, {"cuts": 0})
        finally:
            snap.free()
        self.report({'INFO'} if n else {'WARNING'}, msg)
        return {'FINISHED'} if n else {'CANCELLED'}


class RETOPO_OT_connect(bpy.types.Operator):
    bl_idname = "retopo.connect_pieces"
    bl_label = "떨어진 메쉬 연결"
    bl_description = ("따로 떨어진 두 조각(또는 두 리토 오브젝트)의 마주 보는 경계를 찾아 표면에 맞는 쿼드로 이어 붙입니다. "
                      "두 조각의 경계 버텍스를 골라 두면 그 부분을, 아니면 가장 가까운 두 조각을 연결")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode in ('EDIT_MESH', 'OBJECT')

    def execute(self, context):
        st = context.scene.retopo_annot
        tg = set(target_objects(st))
        objs = [o for o in context.selected_objects if o.type == 'MESH' and o not in tg]
        if context.mode == 'EDIT_MESH':
            objs = [o for o in context.objects_in_mode if o.type == 'MESH'] or objs
        # 따로 된 리토 오브젝트 여러 개 → 먼저 하나로 합침
        if len(objs) >= 2:
            keep = st.retopo if st.retopo in objs else (context.active_object if context.active_object in objs else objs[0])
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            for o in context.selected_objects:
                o.select_set(o in objs)
            context.view_layer.objects.active = keep
            bpy.ops.object.join()
            st.retopo = keep
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(keep.data)
            for v in bm.verts:
                v.select = False
            bm.select_flush(False)
            bmesh.update_edit_mesh(keep.data)
        elif context.mode != 'EDIT_MESH':
            obj = st.retopo or (objs[0] if objs else None)
            if obj is None:
                self.report({'WARNING'}, "연결할 리토 메쉬를 선택하세요")
                return {'CANCELLED'}
            for o in context.selected_objects:
                o.select_set(False)
            obj.select_set(True)
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
        obj = context.edit_object
        snap = _snapshot(obj)
        try:
            n, msg = connect_pieces(context, obj)
            if n:
                make_flash(obj, snap, {"cuts": 0})
        finally:
            snap.free()
        self.report({'INFO'} if n else {'WARNING'}, msg)
        return {'FINISHED'} if n else {'CANCELLED'}


class RETOPO_OT_mesh_density(bpy.types.Operator):
    bl_idname = "retopo.mesh_density"
    bl_label = "만든 메쉬 밀도"
    bl_description = ("선택한 면(없으면 전체)의 밀도를 바꿉니다. 촘촘하게: 쿼드 하나를 4개로 나누고 새 점을 "
                      "표면에 붙임 / 성기게: 엣지 루프를 하나 건너 하나씩 없앰(쿼드 격자 모양 영역)")
    bl_options = {'REGISTER', 'UNDO'}

    step: IntProperty(name="방향", default=1, min=-1, max=1)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        st = context.scene.retopo_annot
        bm = bmesh.from_edit_mesh(obj.data)
        sel = [f for f in bm.faces if f.select]
        faces = sel or list(bm.faces)
        if not faces:
            self.report({'WARNING'}, "면이 없습니다")
            return {'CANCELLED'}
        n0 = len(bm.faces)
        if self.step > 0:
            edges = densify_edges(set(faces))
            old = set(bm.verts)
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
            proj = Projector(context, st, st.surface_offset)
            mw = obj.matrix_world
            mwi = mw.inverted()
            if proj.ok:
                for v in bm.verts:
                    if v not in old:
                        v.co = mwi @ proj.project(mw @ v.co)
            bm.normal_update()
            bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        else:
            sparsify(bm, faces)
            bm.normal_update()
            bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        n1 = len(bmesh.from_edit_mesh(obj.data).faces)
        if n1 == n0:
            self.report({'WARNING'}, "바뀐 것이 없습니다 (성기게는 쿼드 격자 모양 영역에서 동작)")
            return {'CANCELLED'}
        self.report({'INFO'}, "면 %d → %d" % (n0, n1))
        return {'FINISHED'}


class RETOPO_OT_next_stroke(bpy.types.Operator):
    bl_idname = "retopo.next_stroke"
    bl_label = "다음 선으로 수정"
    bl_description = ("한 번만: 다음에 긋는 주석 선을 이 방식으로 처리 (영역 선택 = 둘러싼 면 선택, "
                      "흐름 재구성 = 선택 영역을 그 선 방향으로 다시 채움, 컷 = 그 선대로 자름). 다시 누르면 취소")
    bl_options = {'REGISTER'}

    mode: EnumProperty(items=[('REGION', "영역 선택", ""), ('FLOW', "흐름 재구성", ""), ('CUT', "컷", "")],
                       default='FLOW')

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        st = context.scene.retopo_annot
        if st.next_mode == self.mode:
            st.next_mode = 'NONE'
            _status("다음 선: 취소 (원래 모드)", 2.0)
            return {'FINISHED'}
        st.next_mode = self.mode
        try:
            bpy.ops.wm.tool_set_by_id(name="builtin.annotate")  # 바로 그을 수 있게 주석 툴로
        except Exception:
            pass
        names = {'REGION': "영역 선택 — 수정할 곳을 둘러싸세요",
                 'FLOW': "흐름 재구성 — 선택 영역 위에 원하는 흐름 방향으로 그으세요",
                 'CUT': "컷 — 자를 곳을 그으세요"}
        _status("다음 선: " + names[self.mode], 6.0)
        _redraw_3d()
        return {'FINISHED'}


class RETOPO_OT_rebuild_region(bpy.types.Operator):
    bl_idname = "retopo.rebuild_region"
    bl_label = "고르게 재구성"
    bl_description = ("선택한 면 영역(바깥 경계는 그대로)을 고른 쿼드 격자로 다시 채움 → 간격이 고르고 평평해지며 "
                      "삼각형·극점·찌그러진 면이 사라짐")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        st = context.scene.retopo_annot
        bm = bmesh.from_edit_mesh(obj.data)
        faces = [f for f in bm.faces if f.select]
        if not faces:
            self.report({'WARNING'}, "다시 만들 면을 선택하세요 (주석 '영역 선택' 모드로 둘러싸도 됨)")
            return {'CANCELLED'}
        proj = Projector(context, st, st.surface_offset)
        new, msg = rebuild_region(bm, faces, obj.matrix_world, proj, st)
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        self.report({'INFO'} if new else {'WARNING'}, msg)
        return {'FINISHED'} if new else {'CANCELLED'}


class RETOPO_OT_offset_region(bpy.types.Operator):
    bl_idname = "retopo.offset_region"
    bl_label = "오프셋 (루프 추가)"
    bl_description = "선택한 면 영역 경계 바로 안쪽에 엣지 루프를 하나 더 넣어 영역 둘레를 따라 흐름을 바꿉니다"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        st = context.scene.retopo_annot
        bm = bmesh.from_edit_mesh(obj.data)
        faces = [f for f in bm.faces if f.select]
        if not faces:
            self.report({'WARNING'}, "면을 선택하세요")
            return {'CANCELLED'}
        proj = Projector(context, st, st.surface_offset)
        new, msg = offset_region(bm, faces, obj.matrix_world, proj)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class RETOPO_OT_scan_merge(bpy.types.Operator):
    bl_idname = "retopo.scan_merge"
    bl_label = "스캔 → 합친 리토 메쉬"
    bl_description = ("선택한 오브젝트들(없으면 타겟)의 표면을 스캔해, 겹친 곳은 하나로 합친 고른 쿼드 리토 메쉬를 "
                      "새 오브젝트로 만듭니다. 칸 크기 = 엣지 길이")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        st = context.scene.retopo_annot
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        objs = [o for o in context.selected_objects if o.type == 'MESH' and o != st.retopo
                and not o.name.startswith("Retopo")]
        if not objs:
            objs = target_objects(st)
        if not objs:
            self.report({'WARNING'}, "스캔할 메쉬 오브젝트를 선택하세요")
            return {'CANCELLED'}
        obj, msg = scan_merge(context, objs, st.spacing)
        if obj is None:
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        obj.show_in_front = st.show_in_front
        st.retopo = obj
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class RETOPO_OT_adjust(bpy.types.Operator):
    bl_idname = "retopo.adjust_last"
    bl_label = "마지막 결과 조절"
    bl_description = "방금 만든 메쉬의 밀도(분할) 또는 스트립 폭을 한 단계 조절 (Alt+휠)"
    bl_options = {'REGISTER'}

    what: EnumProperty(items=[('DENSITY', "밀도", ""), ('WIDTH', "폭", "")], default='DENSITY')
    step: IntProperty(default=1)

    @classmethod
    def poll(cls, context):
        # 에디트 모드면 항상 휠을 받음 (조절할 결과가 없으면 이유를 알려 줌 — 휠이 프레임 이동으로 새지 않게)
        return context.mode == 'EDIT_MESH' and context.scene.retopo_annot.retopo is not None

    def execute(self, context):
        st = context.scene.retopo_annot
        if not can_redo(context):
            msg = ("Alt+휠: 조절할 결과가 없습니다 — 주석으로 방금 만든 결과에만 적용 "
                   "(그 뒤 메쉬를 고치거나 되돌렸다면 새로 그은 뒤 사용)")
            self.report({'WARNING'}, msg)
            _status(msg)
            return {'FINISHED'}
        if self.what == 'WIDTH' and _last.get("mode") not in ('POLYSTRIP', 'AUTO'):
            msg = "Shift+Alt+휠(스트립 폭)은 폴리스트립 결과에만 적용됩니다"
            self.report({'WARNING'}, msg)
            _status(msg)
            return {'FINISHED'}
        if self.what == 'WIDTH':
            base = st.strip_width if st.strip_width > 0 else st.spacing
            st.strip_width = max(1e-3, base * (1.2 ** self.step))
        elif st.density_mode == 'COUNT':
            st.count_u = max(1, st.count_u + self.step)
            st.count_edge = max(1, st.count_edge + self.step)
        else:
            if st.density_mode == 'AVERAGE':
                st.density_mode = 'LENGTH'
            st.spacing = max(1e-3, st.spacing * (0.85 ** self.step))
        if self.what == 'WIDTH':
            _status("스트립 폭 %.3g" % st.strip_width, 2.0)
        elif st.density_mode == 'COUNT':
            _status("분할 수 %d" % st.count_u, 2.0)
        else:
            _status("엣지 길이 %.3g" % st.spacing, 2.0)
        return {'FINISHED'}


class RETOPO_OT_clear(bpy.types.Operator):
    bl_idname = "retopo.clear_annotations"
    bl_label = "주석 모두 지우기"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        clear_all_annotations(context.scene)
        for a in context.screen.areas:
            a.tag_redraw()
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# 자동 쿼드 핸들러 (변형 중에는 건드리지 않고, 끝난 뒤 타이머로 처리)
# ---------------------------------------------------------------------------

_pending = {"flag": False}

# 되돌리기/다시 실행 직후에는 자동 채우기·자동 변환을 하지 않음
# (다시 만들면 Ctrl+Z 가 안 먹는 것처럼 보이고 다시 실행(Ctrl+Shift+Z) 기록도 사라짐)
_undo_state = {"t": -1.0, "kind": None, "sig": None, "extra": False}


def _just_undone(window=0.6):
    return time.monotonic() - _undo_state["t"] < window


def _edit_sig():
    """에디트 중인 리토 메쉬의 모양 + 선택 상태 (되돌리기 전후 비교용)."""
    try:
        ctx = bpy.context
        st = ctx.scene.retopo_annot
        obj = ctx.edit_object
        if obj is None or st.retopo is None or obj.name != st.retopo.name:
            return None
        bm = bmesh.from_edit_mesh(obj.data)
        s = Vector()
        for v in bm.verts:
            s += v.co
        sel = sum(i for i, v in enumerate(bm.verts) if v.select)
        return (len(bm.verts), len(bm.edges), len(bm.faces), tuple(round(x, 5) for x in s), sel)
    except Exception:
        return None


@persistent
def _on_undo_pre(*_args):
    _undo_state["sig"] = _edit_sig()


def _mark_undo(kind):
    _undo_state["t"] = time.monotonic()
    _pending["flag"] = False
    if _undo_state["extra"]:  # 아래 _undo_fix 가 한 번 더 이동한 것 → 또 이동하지 않음
        _undo_state["extra"] = False
        return
    _undo_state["kind"] = kind
    if not bpy.app.timers.is_registered(_undo_fix):
        bpy.app.timers.register(_undo_fix, first_interval=0.01)


@persistent
def _on_undo(*_args):
    _mark_undo('UNDO')


@persistent
def _on_redo(*_args):
    _mark_undo('REDO')


def _undo_fix():
    """자동 변환 중에는 '주석 긋기' 단계와 '변환' 단계가 따로 기록되어 Ctrl+Z 를 두 번 눌러야 했음.
    되돌리기/다시 실행 후 메쉬와 선택이 그대로면(= 주석 긋기 단계) 같은 방향으로 한 단계 더 이동해
    Ctrl+Z / Ctrl+Shift+Z 한 번 = 결과 하나가 되게 한다."""
    kind = _undo_state["kind"]
    _undo_state["kind"] = None
    if kind is None:
        return None
    try:
        ctx = bpy.context
        scene = ctx.scene
        st = getattr(scene, "retopo_annot", None)
        before = _undo_state["sig"]
        restored = stroke_count(scene) > 0
        if restored:
            clear_all_annotations(scene)  # 되살아난 주석은 이미 변환된 선 → 다시 변환하지 않음
        # 한 단계 더 이동하는 것은 '주석 긋기' 단계에 멈췄을 때뿐 (주석이 되살아나고 메쉬는 그대로).
        # 그 밖의 단계(리토폴로지 시작 등)는 메쉬가 같아도 건너뛰지 않음 → 너무 많이 되돌리지 않게
        if st is not None and st.live and restored and before is not None and _edit_sig() == before:
            win = ctx.window_manager.windows[0]
            area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), None)
            _undo_state["extra"] = True
            try:
                with ctx.temp_override(window=win, area=area):
                    r = bpy.ops.ed.undo() if kind == 'UNDO' else bpy.ops.ed.redo()
                if 'FINISHED' not in r:
                    _undo_state["extra"] = False
            except Exception:
                _undo_state["extra"] = False
    except Exception as ex:
        _undo_state["extra"] = False
        print("[RetopoAnnotate] undo", ex)
    return None


def _transform_running():
    wm = bpy.context.window_manager
    for win in wm.windows:
        try:
            for op in win.modal_operators:
                if op.bl_idname.startswith(("TRANSFORM_OT", "MESH_OT_extrude", "VIEW3D_OT_edit_mesh_extrude",
                                            "MESH_OT_knife", "MESH_OT_loopcut")):
                    return True
        except AttributeError:
            pass
    return False


def _auto_fill_timer():
    if not _pending["flag"]:
        return None
    if _transform_running():
        return 0.1
    _pending["flag"] = False
    if _just_undone():
        return None
    ctx = bpy.context
    obj = ctx.edit_object
    if obj is None or obj.type != 'MESH':
        return None
    st = ctx.scene.retopo_annot
    if not st.auto_quad:
        return None
    bm = bmesh.from_edit_mesh(obj.data)
    seeds = [v for v in bm.verts if v.select]
    if not seeds or len(seeds) > 500:
        return None
    proj = Projector(ctx, st, st.surface_offset)
    faces = auto_fill(bm, seeds, obj.matrix_world, proj)
    if faces:
        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        try:
            win = ctx.window_manager.windows[0]
            with ctx.temp_override(window=win):
                bpy.ops.ed.undo_push(message="Retopo 자동 쿼드")
        except Exception:
            pass
    return None


@persistent
def _depsgraph_post(scene, depsgraph):
    _border["dirty"] = _border.get("dirty", 0) + 1  # 테두리 표시 다시 계산
    st = getattr(scene, "retopo_annot", None)
    if st is None or not st.auto_quad or _pending["flag"] or _just_undone():
        return
    obj = bpy.context.edit_object
    if obj is None or obj.type != 'MESH':
        return
    for upd in depsgraph.updates:
        if upd.is_updated_geometry and getattr(upd.id, "original", upd.id) in (obj, obj.data):
            _pending["flag"] = True
            bpy.app.timers.register(_auto_fill_timer, first_interval=0.05)
            return


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class RETOPO_PT_main(bpy.types.Panel):
    """시작: 타겟 · 리토 메쉬."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retopo"
    bl_label = "리토폴로지 주석 툴"

    def draw(self, context):
        st = context.scene.retopo_annot
        lay = self.layout
        lay.row(align=True).prop(st, "target_type", expand=True)
        col = lay.column(align=True)
        if st.target_type == 'COLLECTION':
            col.prop(st, "target_collection")
            n = len(target_objects(st))
            col.label(text="타겟 메쉬 %d개" % n, icon='OUTLINER_COLLECTION' if n else 'ERROR')
        else:
            col.prop(st, "target")
        col.prop(st, "retopo")
        row = lay.row(align=True)
        row.scale_y = 1.2
        row.operator("retopo.setup", text="리토폴로지 시작", icon='MOD_REMESH')
        row.operator("retopo.scan_merge", text="스캔 → 합친 메쉬", icon='MESH_ICOSPHERE')


class _SubPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retopo"
    bl_parent_id = "RETOPO_PT_main"


class RETOPO_PT_draw(_SubPanel, bpy.types.Panel):
    """① 그리기: 주석 → 메쉬."""
    bl_label = "① 그리기 (주석 → 메쉬)"

    def draw(self, context):
        st = context.scene.retopo_annot
        lay = self.layout
        lay.prop(st, "mode", text="")
        row = lay.row(align=True)
        row.prop(st, "spacing")
        op = row.operator("retopo.adjust_last", text="", icon='ADD')
        op.what, op.step = 'DENSITY', 1
        op = row.operator("retopo.adjust_last", text="", icon='REMOVE')
        op.what, op.step = 'DENSITY', -1
        if st.mode in ('AUTO', 'POLYSTRIP'):
            row = lay.row(align=True)
            row.prop(st, "strip_width")
            op = row.operator("retopo.adjust_last", text="", icon='ADD')
            op.what, op.step = 'WIDTH', 1
            op = row.operator("retopo.adjust_last", text="", icon='REMOVE')
            op.what, op.step = 'WIDTH', -1
        row = lay.row(align=True)
        row.prop(st, "live", toggle=True, icon='PAUSE' if st.live else 'PLAY')
        if not st.live:
            row.operator("retopo.convert_annotations", text="지금 변환", icon='MESH_GRID')
        lay.label(text="+/− : 방금 만든 결과 다시 만들기 (Alt+휠, Shift+Alt+휠)", icon='INFO')


class RETOPO_PT_edit(_SubPanel, bpy.types.Panel):
    """② 수정: 주석/버튼으로 토폴로지 고치기."""
    bl_label = "② 수정"

    def draw(self, context):
        st = context.scene.retopo_annot
        lay = self.layout
        col = lay.column(align=True)
        col.label(text="주석으로 (다음 선 한 번만):")
        row = col.row(align=True)
        op = row.operator("retopo.next_stroke", text="영역 둘러싸기", icon='SELECT_SET', depress=(st.next_mode == 'REGION'))
        op.mode = 'REGION'
        op = row.operator("retopo.next_stroke", text="흐름 선", icon='FORCE_CURVE', depress=(st.next_mode == 'FLOW'))
        op.mode = 'FLOW'
        op = row.operator("retopo.next_stroke", text="컷 선", icon='SCULPTMODE_HLT', depress=(st.next_mode == 'CUT'))
        op.mode = 'CUT'
        col = lay.column(align=True)
        col.label(text="선택한 면 영역:")
        row = col.row(align=True)
        row.operator("retopo.rebuild_region", text="고르게 재구성", icon='MESH_GRID')
        row.operator("retopo.offset_region", text="오프셋", icon='FULLSCREEN_EXIT')
        row = col.row(align=True)
        row.operator("retopo.mesh_density", text="촘촘하게 ×2", icon='ADD').step = 1
        row.operator("retopo.mesh_density", text="성기게 ÷2", icon='REMOVE').step = -1
        col = lay.column(align=True)
        col.label(text="선택한 버텍스:")
        row = col.row(align=True)
        row.operator("retopo.fill_gap", text="빈 곳 채우기", icon='MESH_GRID')
        row.operator("retopo.crease_path", text="주름 만들기", icon='SHARPCURVE')
        col.operator("retopo.connect_pieces", text="떨어진 메쉬 연결", icon='AUTOMERGE_OFF')
        row = col.row(align=True)
        row.operator("retopo.quad_extrude", text="쿼드 익스트루드", icon='ADD')
        row.operator("retopo.project_selected", text="표면에 붙이기", icon='SNAP_FACE')
        row = lay.row(align=True)
        row.operator("retopo.relax", text="이완", icon='MOD_SMOOTH')
        row.prop(st, "symmetry_x", toggle=True, icon='MOD_MIRROR')


class RETOPO_PT_view(_SubPanel, bpy.types.Panel):
    bl_label = "표시"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        st = context.scene.retopo_annot
        lay = self.layout
        row = lay.row(align=True)
        row.prop(st, "show_in_front", toggle=True)
        row.prop(st, "show_wire", toggle=True)
        lay.prop(st, "show_connect", toggle=True, icon='LINKED')
        row = lay.row(align=True)
        row.prop(st, "ann_opacity", slider=True)
        row.prop(st, "ann_thickness")
        row = lay.row(align=True)
        row.prop(st, "ann_color", text="")
        row.prop(st, "ann_hide", toggle=True, icon='HIDE_ON' if st.ann_hide else 'HIDE_OFF')
        lay.operator("retopo.clear_annotations", icon='TRASH')


class RETOPO_PT_advanced(_SubPanel, bpy.types.Panel):
    bl_label = "고급 설정"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        st = context.scene.retopo_annot
        lay = self.layout
        lay.label(text="밀도 방식")
        lay.row(align=True).prop(st, "density_mode", expand=True)
        if st.density_mode == 'COUNT':
            row = lay.row(align=True)
            row.prop(st, "count_u")
            row.prop(st, "count_v")
            lay.prop(st, "count_edge")
        col = lay.column(align=True)
        col.prop(st, "merge_dist")
        col.prop(st, "surface_offset")
        col.prop(st, "relax_iterations")
        col = lay.column(align=True)
        col.prop(st, "snap_creases")
        col.prop(st, "redo_on_change")
        col.prop(st, "clear_after")
        col.prop(st, "auto_quad")
        lay.operator("retopo.fill_quads", icon='FACESEL')


class RETOPO_PT_keys(_SubPanel, bpy.types.Panel):
    bl_label = "단축키"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        col = self.layout.column(align=True)
        for line in ("Alt+휠: 방금 만든 결과 밀도", "Shift+Alt+휠: 방금 만든 스트립 폭",
                     "Ctrl+Alt+E: 다음 선 = 영역 둘러싸기", "Ctrl+Alt+R: 다음 선 = 흐름 선",
                     "Ctrl+Alt+X: 다음 선 = 컷 선", "Ctrl+Alt+F: 고르게 재구성",
                     "Ctrl+Alt+O: 오프셋", "Ctrl+Alt+B: 떨어진 메쉬 연결", "Ctrl+Alt+ + / − : 선택 영역 밀도",
                     "Shift+F: 쿼드 익스트루드", "Ctrl+Shift+F: 주석 변환 (자동 변환 끔일 때)"):
            col.label(text=line)

classes = (
    RetopoAnnotSettings,
    RETOPO_OT_setup,
    RETOPO_OT_convert,
    RETOPO_OT_live,
    RETOPO_OT_quad_extrude,
    RETOPO_OT_fill_quads,
    RETOPO_OT_project,
    RETOPO_OT_relax,
    RETOPO_OT_crease,
    RETOPO_OT_fill_gap,
    RETOPO_OT_connect,
    RETOPO_OT_mesh_density,
    RETOPO_OT_next_stroke,
    RETOPO_OT_rebuild_region,
    RETOPO_OT_offset_region,
    RETOPO_OT_scan_merge,
    RETOPO_OT_adjust,
    RETOPO_OT_clear,
    RETOPO_PT_main,
    RETOPO_PT_draw,
    RETOPO_PT_edit,
    RETOPO_PT_view,
    RETOPO_PT_advanced,
    RETOPO_PT_keys,
)

_keymaps = []


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.retopo_annot = PointerProperty(type=RetopoAnnotSettings)
    if _depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_post)
    for hl, fn in ((bpy.app.handlers.undo_post, _on_undo), (bpy.app.handlers.redo_post, _on_redo),
                   (bpy.app.handlers.undo_pre, _on_undo_pre), (bpy.app.handlers.redo_pre, _on_undo_pre)):
        if fn not in hl:
            hl.append(fn)
    if not bpy.app.timers.is_registered(_auto_convert_tick):
        bpy.app.timers.register(_auto_convert_tick, first_interval=0.5, persistent=True)
    if not _draw_handles:
        _draw_handles.append(bpy.types.SpaceView3D.draw_handler_add(_draw_view, (), 'WINDOW', 'POST_VIEW'))
        _draw_handles.append(bpy.types.SpaceView3D.draw_handler_add(_draw_pixel, (), 'WINDOW', 'POST_PIXEL'))
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Mesh", space_type='EMPTY')
        _keymaps.append((km, km.keymap_items.new("retopo.quad_extrude", 'F', 'PRESS', shift=True)))
        # Alt+휠 / Shift+Alt+휠: 방금 만든 결과가 있을 때만 동작(poll), 없으면 원래 기능으로 통과
        for key, step in (('WHEELUPMOUSE', 1), ('WHEELDOWNMOUSE', -1)):
            kmi = km.keymap_items.new("retopo.adjust_last", key, 'PRESS', alt=True)
            kmi.properties.what, kmi.properties.step = 'DENSITY', step
            _keymaps.append((km, kmi))
            kmi = km.keymap_items.new("retopo.adjust_last", key, 'PRESS', alt=True, shift=True)
            kmi.properties.what, kmi.properties.step = 'WIDTH', step
            _keymaps.append((km, kmi))
        # 주석으로 토폴로지 수정 (에디트 모드)
        for key, mode in (('E', 'REGION'), ('R', 'FLOW'), ('X', 'CUT')):
            kmi = km.keymap_items.new("retopo.next_stroke", key, 'PRESS', ctrl=True, alt=True)
            kmi.properties.mode = mode
            _keymaps.append((km, kmi))
        _keymaps.append((km, km.keymap_items.new("retopo.rebuild_region", 'F', 'PRESS', ctrl=True, alt=True)))
        _keymaps.append((km, km.keymap_items.new("retopo.offset_region", 'O', 'PRESS', ctrl=True, alt=True)))
        _keymaps.append((km, km.keymap_items.new("retopo.connect_pieces", 'B', 'PRESS', ctrl=True, alt=True)))
        for key, step in (('EQUAL', 1), ('NUMPAD_PLUS', 1), ('MINUS', -1), ('NUMPAD_MINUS', -1)):
            kmi = km.keymap_items.new("retopo.mesh_density", key, 'PRESS', ctrl=True, alt=True)
            kmi.properties.step = step
            _keymaps.append((km, kmi))
        km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')
        _keymaps.append((km, km.keymap_items.new("retopo.convert_annotations", 'F', 'PRESS',
                                                  ctrl=True, shift=True)))


def unregister():
    if bpy.app.timers.is_registered(_auto_convert_tick):
        bpy.app.timers.unregister(_auto_convert_tick)
    if bpy.app.timers.is_registered(_flash_tick):
        bpy.app.timers.unregister(_flash_tick)
    for h in _draw_handles:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
        except Exception:
            pass
    _draw_handles.clear()
    for km, kmi in _keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _keymaps.clear()
    if _depsgraph_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_post)
    for hl, fn in ((bpy.app.handlers.undo_post, _on_undo), (bpy.app.handlers.redo_post, _on_redo),
                   (bpy.app.handlers.undo_pre, _on_undo_pre), (bpy.app.handlers.redo_pre, _on_undo_pre)):
        if fn in hl:
            hl.remove(fn)
    if bpy.app.timers.is_registered(_undo_fix):
        bpy.app.timers.unregister(_undo_fix)
    del bpy.types.Scene.retopo_annot
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
