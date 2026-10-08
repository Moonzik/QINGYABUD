# -*- coding: utf-8 -*-
"""
青芽 BUD — 骨骼绑定 (rigging) + 形态键 (shape keys) 自动脚本
在 Blender 4.x 中运行:  blender --background --python qingya_rig.py

坐标系说明（关键，之前踩过坑）:
  - glTF / three.js 为 Y-up；Blender 为 Z-up。
  - Blender 的 glTF 导入器会自动把顶点转到 Z-up，但**手工创建的骨骼不会**，
    所以本脚本里所有骨骼/变形向量都用 glTF 语义书写，再统一经 G2B 转换。
  - 面部区域 JSON 里的 center 是网格**局部**坐标（未应用节点变换），
    转换链: local -> glTF world -> Blender，详见 l2b()。
"""
import bpy
import json
import os
import sys
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
GLB_IN = os.path.join(HERE, "qingya_3d_v4_vivid.glb")
# 用户要求：嘴巴要会动（第 11 条反馈），因此嘴部形态键必须保留。
GLB_OUT = os.path.join(HERE, "qingya_3d_v4_rigged.glb")
REGIONS = os.path.join(HERE, "face_regions_falloff.json")

ENABLE_MOUTH_KEYS = True    # 生成 mouth_open / smile 形态键（用户要求嘴巴会动）
ENABLE_ORAL_PARTS = False   # 是否合并牙齿 / 舌头 / 口腔贴片

# ---------------------------------------------------------------- 坐标转换
# glTF world (x, y=高, z=前)  ->  Blender (x, y=-前, z=高)
def g2b(p):
    return (p[0], -p[2], p[1])


# 网格局部坐标 -> Blender（先套节点矩阵 T，再做 Y-up/Z-up 互换）
# T = [[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]]  =>  world=(lx, -lz, ly)
def l2b(p):
    lx, ly, lz = p
    return (lx, -ly, -lz)


# ---------------------------------------------------------------- 骨骼布局
# 全部按 glTF world 语义书写 (Y 向上, 脸朝 +Z)，运行时转 Blender 空间。
# 依据模型实测切片: 嫩芽 y 0.85~1.00 | 头 y 0.40~0.85 | 躯干 y 0.00~0.40 | 尾拖到 z=-0.65
# (name, head, tail, parent, radius)
BONES_GLTF = [
    ("root",       (0.0,  0.02, -0.05), (0.0,  0.16, -0.02), None,    0.16),
    ("spine",      (0.0,  0.16, -0.02), (0.0,  0.34,  0.01), "root",  0.19),
    ("chest",      (0.0,  0.34,  0.01), (0.0,  0.44,  0.04), "spine", 0.17),
    ("neck",       (0.0,  0.44,  0.04), (0.0,  0.50,  0.06), "chest", 0.16),
    ("head",       (0.0,  0.50,  0.06), (0.0,  0.76,  0.09), "neck",  0.18),
    ("sprout",     (0.0,  0.76,  0.09), (0.0,  0.88,  0.13), "head",  0.085),
    ("sprout_tip", (0.0,  0.88,  0.13), (0.0,  1.00,  0.14), "sprout", 0.085),
    ("tail1",      (0.0,  0.30, -0.14), (0.0,  0.29, -0.32), "root",  0.12),
    ("tail2",      (0.0,  0.29, -0.32), (0.0,  0.25, -0.48), "tail1", 0.11),
    ("tail3",      (0.0,  0.25, -0.48), (0.0,  0.18, -0.64), "tail2", 0.10),
    ("arm_L",      (-0.22, 0.32, 0.03), (-0.29, 0.17, 0.10), "chest", 0.09),
    ("arm_R",      ( 0.22, 0.32, 0.03), ( 0.29, 0.17, 0.10), "chest", 0.09),
    ("leg_L",      (-0.11, 0.09, 0.02), (-0.12, 0.00, 0.07), "root",  0.11),
    ("leg_R",      ( 0.11, 0.09, 0.02), ( 0.12, 0.00, 0.07), "root",  0.11),
]
# 转成 Blender 空间
BONES = [(n, g2b(h), g2b(t), p, r) for (n, h, t, p, r) in BONES_GLTF]

# 骨骼管辖区间（glTF world 语义）：(y_min, y_max, z_min, z_max, x_min, x_max)
# 顶点只与"区间包含它"的骨骼竞争权重。
# 为什么需要：纯欧氏距离下，长骨（head/spine）会把短骨（chest/neck）完全吞掉
# —— 实测 chest/neck 主导顶点数为 0，等于白绑。划区间后头/颈/胸各归其位。
BONE_ZONES_GLTF = {
    "root":       (0.00, 0.20, -0.75,  0.50, -0.50,  0.50),
    "spine":      (0.14, 0.38, -0.40,  0.22, -0.22,  0.22),
    "chest":      (0.30, 0.47, -0.15,  0.14, -0.22,  0.22),
    "neck":       (0.38, 0.55, -0.14,  0.16, -0.20,  0.20),
    "head":       (0.44, 0.90,  0.00,  0.50, -0.50,  0.50),
    "sprout":     (0.78, 0.92, -0.25,  0.40, -0.25,  0.25),
    "sprout_tip": (0.88, 1.06, -0.25,  0.40, -0.25,  0.25),
    "tail1":      (0.10, 0.44, -0.38, -0.10, -0.30,  0.30),
    "tail2":      (0.10, 0.44, -0.56, -0.26, -0.30,  0.30),
    "tail3":      (0.04, 0.40, -0.75, -0.46, -0.30,  0.30),
    "arm_L":      (0.14, 0.38, -0.25,  0.40, -0.50, -0.15),
    "arm_R":      (0.14, 0.38, -0.25,  0.40,  0.15,  0.50),
    "leg_L":      (0.00, 0.15, -0.25,  0.40, -0.50, -0.02),
    "leg_R":      (0.00, 0.15, -0.25,  0.40,  0.02,  0.50),
}

ZONE_OUTSIDE_FALLOFF = 0.03  # 管辖区间外骨骼的权重保留系数（0=硬清零，会导致关节硬折角）
MAX_VGROUPS = 4      # 每顶点最多受几根骨骼影响 (glTF 常用 4)


def log(m):
    print("[qingya-rig]", m, flush=True)


# ---------------------------------------------------------------- 1. 导入
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("GLB 中未找到网格")
    meshes.sort(key=lambda o: len(o.data.vertices), reverse=True)
    return meshes[0]


def bake_world_transform(obj):
    """把 object 世界矩阵烘焙进网格数据，object 矩阵归零。
    之后网格顶点即为 Blender 世界坐标 (Z-up)。"""
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix()
    obj.data.update()
    log("已烘焙世界变换 -> Blender Z-up 空间")


# ---------------------------------------------------------------- 2. 骨架
def build_armature():
    arm_data = bpy.data.armatures.new("QingyaRig")
    arm_obj = bpy.data.objects.new("QingyaRig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_obj.data.edit_bones
    created = {}
    for name, h, t, parent, _r in BONES:
        b = eb.new(name)
        b.head = Vector(h)
        b.tail = Vector(t)
        if parent and parent in created:
            b.parent = created[parent]
        created[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    log(f"骨架创建完成: {len(created)} 根骨骼 (Blender Z-up)")
    return arm_obj


# ---------------------------------------------------------------- 3. 权重
def segments_from_bones():
    return [(n, np.array(h, dtype=np.float64), np.array(t, dtype=np.float64))
            for (n, h, t, _p, _r) in BONES]


def seg_dist_matrix(V, segs):
    N, B = V.shape[0], len(segs)
    D = np.zeros((N, B), dtype=np.float64)
    for bi, (_n, a, b) in enumerate(segs):
        ab = b - a
        ab2 = float(np.dot(ab, ab))
        if ab2 < 1e-12:
            D[:, bi] = np.linalg.norm(V - a, axis=1)
            continue
        t = np.clip(((V - a) @ ab) / ab2, 0.0, 1.0)
        D[:, bi] = np.linalg.norm(V - (a + np.outer(t, ab)), axis=1)
    return D


def zone_mask(V, name):
    """把 glTF 语义的管辖区间转成 Blender 空间的布尔掩码。
    glTF (x, y=高, z=前) -> Blender (x, y=-前, z=高)"""
    z = BONE_ZONES_GLTF.get(name)
    if not z:
        return None
    ymin, ymax, zmin, zmax, xmin, xmax = z
    return ((V[:, 2] >= ymin) & (V[:, 2] <= ymax) &
            (V[:, 1] >= -zmax) & (V[:, 1] <= -zmin) &
            (V[:, 0] >= xmin) & (V[:, 0] <= xmax))


def compute_weights(V, segs):
    D = seg_dist_matrix(V, segs)
    radii = np.array([b[4] for b in BONES], dtype=np.float64)[None, :]
    # 衰减系数 1.2（而非 2.0）：让每顶点平均受到 ~2.5 根骨骼影响。
    # 过于陡峭的衰减会让关节处只受单骨控制，弯曲时出现硬折角。
    W = np.exp(-1.2 * np.power(D / radii, 2.0))
    # 分区软约束：区间外的骨骼大幅衰减（而非归零）。
    # 硬清零会让关节处的顶点只受单骨控制，弯曲时出现硬折角；
    # 保留少量权重可让颈/腰/尾根平滑过渡，同时不会喧宾夺主。
    for bi, (name, *_rest) in enumerate(BONES):
        m = zone_mask(V, name)
        if m is not None:
            W[~m, bi] *= ZONE_OUTSIDE_FALLOFF
    # 未被任何区间覆盖的顶点，退化为无约束的最近骨骼
    orphan = W.sum(axis=1) < 1e-12
    if orphan.any():
        W[orphan] = np.exp(-1.2 * np.power(D[orphan] / radii, 2.0))
        log(f"  区间未覆盖顶点 {int(orphan.sum())} 个，已回退为最近骨骼")
    out = np.zeros_like(W)
    idx = np.argpartition(-W, MAX_VGROUPS - 1, axis=1)[:, :MAX_VGROUPS]
    rows = np.arange(V.shape[0])[:, None]
    out[rows, idx] = W[rows, idx]
    s = out.sum(axis=1, keepdims=True)
    s[s < 1e-9] = 1.0
    return out / s


def read_dominant_from_vgroups(obj, bone_names):
    """从网格实际顶点组读出每顶点的主导骨骼索引。"""
    vgs = [obj.vertex_groups.get(n) for n in bone_names]
    nverts = len(obj.data.vertices)
    dom = np.zeros(nverts, dtype=np.int64)
    for vi in range(nverts):
        best_w, best_i = -1.0, 0
        for gi, vg in enumerate(vgs):
            if vg is None:
                continue
            try:
                w = vg.weight(vi)
            except RuntimeError:
                continue
            if w > best_w:
                best_w, best_i = w, gi
        dom[vi] = best_i
    return dom


def auto_skin(obj, arm_obj, bone_names):
    """用 Blender 内置热扩散自动权重（ARMATURE_AUTO）绑定。

    手写欧氏高斯对这种"团块"模型调不出合理结果：spine 一放大就抢走脸部，
    head 一放大就吞掉 chest/neck。Blender 的自动权重沿网格拓扑做热扩散，
    能正确处理头/颈/胸的过渡。
    """
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    arm_obj.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except RuntimeError as e:
        log(f"自动权重失败: {e}")
        return False

    vgs = [obj.vertex_groups.get(n) for n in bone_names]

    # 热扩散可能因非流形几何失败（"failed to find solution"），此时 parent_set
    # 不抛异常但顶点组是空的。必须实测覆盖率，否则会导出一个没有蒙皮的模型。
    sample = min(3000, len(obj.data.vertices))
    got = 0
    for vi in range(sample):
        for vg in vgs:
            if vg is None:
                continue
            try:
                if vg.weight(vi) > 0.0:
                    got += 1
                    break
            except RuntimeError:
                pass
    if got < sample * 0.9:
        log(f"自动权重覆盖率不足 ({got}/{sample})，判定失败 -> 回退分区高斯权重")
        for vg in list(obj.vertex_groups):
            obj.vertex_groups.remove(vg)
        return False

    # 后处理：限制每顶点最多 MAX_VGROUPS 根骨骼 + 归一化 + 清除碎权重
    nverts = len(obj.data.vertices)
    for vi in range(nverts):
        pairs = []
        for gi, vg in enumerate(vgs):
            if vg is None:
                continue
            try:
                w = vg.weight(vi)
            except RuntimeError:
                continue
            if w > 0.002:
                pairs.append((w, gi))
        if not pairs:
            continue
        pairs.sort(reverse=True)
        pairs = pairs[:MAX_VGROUPS]
        tot = sum(w for w, _ in pairs)
        if tot <= 1e-9:
            continue
        for w, gi in pairs:
            vgs[gi].add([vi], w / tot, "REPLACE")
    mod = obj.modifiers.new("QingyaArmature", "ARMATURE")
    mod.object = arm_obj
    log(f"自动权重完成: {len(bone_names)} 个顶点组 (每顶点最多 {MAX_VGROUPS} 根骨骼)")
    return True


def apply_weights(obj, arm_obj, W, bone_names):
    for n in bone_names:
        obj.vertex_groups.new(name=n)
    vgs = [obj.vertex_groups[n] for n in bone_names]
    idx = np.argpartition(-W, MAX_VGROUPS - 1, axis=1)[:, :MAX_VGROUPS]
    rows = np.arange(W.shape[0])[:, None]
    wi = W[rows, idx]
    for bi in range(len(bone_names)):
        r, c = np.nonzero(idx == bi)
        if r.size == 0:
            continue
        wv = wi[r, c]
        keep = wv > 0.002
        for vi, w in zip(r[keep], wv[keep]):
            vgs[bi].add([int(vi)], float(w), "REPLACE")
    mod = obj.modifiers.new("QingyaArmature", "ARMATURE")
    mod.object = arm_obj
    obj.parent = arm_obj
    log(f"权重已写入 {len(bone_names)} 个顶点组 + Armature 修改器")


# ---------------------------------------------------------------- 4. 形态键
# 变形量按 glTF 语义给出，统一由 g2b() 转换到 Blender 空间

# 颌关节铰链（glTF world）：下颌绕它旋转张开，而不是整块前突。
# 位置取嘴后方、头部两侧连线中点附近，符合解剖学。
JAW_HINGE_GLTF = np.array([0.03, 0.475, 0.285])
JAW_OPEN_DEG = 16.0      # 最大张口角度（20 度时嘴角有 2 条边被拉伸 3.6x，降到 16 消除）
UPPER_LIP_LIFT = 0.012   # 上唇上提量：猫张嘴时上唇明显上抬，露出舌头
LOWER_LID_RATIO = 0.25   # 下眼睑相对上眼睑的抬升比例（真实眨眼下眼睑几乎不动）
EYE_CLOSE_TRAVEL = 0.009 # 上眼睑闭合行程（归一化目标，单位=模型尺度）
DELTA_SMOOTH_ITERS = 10   # 位移场拉普拉斯平滑次数（加大张口后增强）
DELTA_SMOOTH_LAM = 0.60


def build_adjacency(obj):
    """顶点邻接表（按坐标合并重复顶点，AI 生成的网格有大量重合点）"""
    from collections import defaultdict
    co = np.zeros((len(obj.data.vertices), 3), dtype=np.float64)
    obj.data.vertices.foreach_get("co", co.ravel())
    co = co.reshape(-1, 3)
    bucket = {}
    for i, (x, y, z) in enumerate(co):
        bucket.setdefault((round(x, 4), round(y, 4), round(z, 4)), []).append(i)
    adj = defaultdict(set)
    for poly in obj.data.polygons:
        vs = list(poly.vertices)
        for i in range(len(vs)):
            u, v = vs[i], vs[(i + 1) % len(vs)]
            gu = bucket[(round(co[u, 0], 4), round(co[u, 1], 4), round(co[u, 2], 4))]
            gv = bucket[(round(co[v, 0], 4), round(co[v, 1], 4), round(co[v, 2], 4))]
            for uu in gu:
                for vv in gv:
                    if uu != vv:
                        adj[uu].add(vv)
    return adj


def smooth_delta(D, affected, adj, iters=DELTA_SMOOTH_ITERS, lam=DELTA_SMOOTH_LAM):
    """
    对位移场做拉普拉斯平滑。

    为什么需要：AI 生成的网格在嘴部存在大量 0.003 长度的极短边，
    任何非刚性变形（下颌旋转）都会把这些边扯成数倍长，画面上就是撕裂感。
    平滑让相邻顶点的位移趋于一致 —— 消除局部撕扯，同时保留整体变形趋势。

    实测（18° 张口）：未平滑 15.70x / 26 条超标边 -> 平滑 6 次 2.99x / 0 条，
    且嘴前部下降量保留 84%。
    """
    D = D.copy()
    affected = list(affected)
    for _ in range(iters):
        new = D.copy()
        for vi in affected:
            nb = adj.get(vi)
            if not nb:
                continue
            new[vi] = D[vi] * (1.0 - lam) + D[list(nb)].mean(0) * lam
        D = new
    return D


def build_shape_keys(obj, regions):
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    basis = obj.data.shape_keys.key_blocks["Basis"]
    nverts = len(obj.data.vertices)
    base = np.zeros((nverts, 3), dtype=np.float64)
    for i in range(nverts):
        base[i] = tuple(basis.data[i].co)

    def new_key(name):
        sk = obj.shape_key_add(name=name, from_mix=False)
        for i in range(nverts):
            sk.data[i].co = tuple(base[i])
        return sk

    def reg(key):
        """返回 (indices, weights, center) —— center 已转到 Blender 空间"""
        if key not in regions:
            return None
        d = regions[key]
        return (np.array(d["indices"], dtype=np.int64),
                np.array(d["weights"], dtype=np.float64),
                np.array(l2b(d["center"]), dtype=np.float64))

    made = {}
    eye_idx = {}       # 键 -> 受影响顶点，便于后续归一化时只遍历局部
    eye_travel = {}    # 键 -> 上眼睑最大下落量

    # 眨眼 / 眯眼：竖直压扁。glTF 的"竖直"是 Y，转到 Blender 是 Z（索引 2）；
    # glTF 的深度 Z 转到 Blender 是 Y（索引 1），且符号相反。
    for kname, rkey, amt, squeeze in (("blink_L", "eyeL", 0.90, -0.15),
                                      ("blink_R", "eyeR", 0.90, -0.15),
                                      ("squint_L", "eyeL", 0.42, 0.06),
                                      ("squint_R", "eyeR", 0.42, 0.06)):
        r = reg(rkey)
        if r is None:
            continue
        idx, w, c = r
        # 以区域竖直中位数作为"眼睑闭合线"。真实眨眼是上眼睑主导下落，
        # 下眼睑只轻微上抬；若按区域 center 对称压扁，会因左右眼 center
        # 与顶点分布不一致，导致一只眼主要向下、另一只主要向上（左右不对称）。
        lid_z = float(np.median(base[idx, 2]))
        sk = new_key(kname)
        maxdrop = 0.0
        for k, vi in enumerate(idx):
            wi = w[k]
            p = base[vi].copy()
            above = base[vi, 2] > lid_z
            ratio = 1.0 if above else LOWER_LID_RATIO
            dz = -(base[vi, 2] - lid_z) * wi * amt * ratio
            p[2] = base[vi, 2] + dz                            # 向闭合线靠拢
            p[1] = c[1] + (p[1] - c[1]) * (1.0 - wi * squeeze)  # 深度方向 (Blender Y)
            sk.data[int(vi)].co = tuple(p)
            if above:
                maxdrop = max(maxdrop, -dz)
        made[kname] = sk
        eye_idx[kname] = idx
        eye_travel[kname] = maxdrop

    # 左右眼区域大小不一致（AI 模型本身不对称），直接缩放会让一只眼眨得深、
    # 另一只浅。统一上眼睑行程，保证左右同步。
    for pair, target in ((("blink_L", "blink_R"), EYE_CLOSE_TRAVEL),
                         (("squint_L", "squint_R"),
                          EYE_CLOSE_TRAVEL * 0.42 / 0.90)):
        for kn in pair:
            if kn not in made or kn not in eye_idx:
                continue
            if eye_travel.get(kn, 0) <= 1e-9:
                continue
            f = float(np.clip(target / eye_travel[kn], 0.4, 2.5))
            if abs(f - 1.0) < 0.02:
                continue
            sk = made[kn]
            for vi in eye_idx[kn]:
                d0 = np.asarray(sk.data[int(vi)].co) - base[vi]
                sk.data[int(vi)].co = tuple(base[vi] + d0 * f)
            log(f"  {kn} 上眼睑行程归一化 x{f:.2f}")

    # ---- 张嘴 / 微笑：下颌绕颌关节旋转（不再是整块前突）----
    if not ENABLE_MOUTH_KEYS:
        log("ENABLE_MOUTH_KEYS=False，跳过 mouth_open / smile 形态键")
        return made

    r = reg("mouth")
    if r is not None:
        idx, w, c = r
        H = np.array(g2b(JAW_HINGE_GLTF), dtype=np.float64)
        # 以嘴区中心高度为界分上下颌
        cy = float(np.median(base[idx, 2]))          # Blender 空间竖直轴是 Z
        lower_m = base[idx, 2] <= cy
        upper_m = ~lower_m
        li, ui = idx[lower_m], idx[upper_m]
        wl, wu = w[lower_m], w[upper_m]

        def rotate_jaw(pts, deg):
            """绕 Blender X 轴（左右轴）旋转，旋转发生在 Y-Z 平面。
            右手定则：y' = y*cos - z*sin ; z' = y*sin + z*cos
            这里 y=前后(索引1), z=竖直(索引2)。
            嘴位于铰链前方 => pz<0；下颌位于铰链下方 => py<0。
            deg>0 时必须让下颌下沉，故竖直项须为 +pz*sin（此前写成 -pz*sin，
            导致下颌反而上抬 —— 实测 457 个顶点全部向上）。"""
            th = np.radians(deg)
            s, sn = np.cos(th), np.sin(th)
            out = pts.copy()
            py = pts[:, 2] - H[2]      # 竖直
            pz = pts[:, 1] - H[1]      # 前后（Blender Y 为负=前）
            out[:, 2] = H[2] + py * s + pz * sn     # 竖直
            out[:, 1] = H[1] - py * sn + pz * s     # 前后
            return out

        def jaw_delta(deg, corner_lift=0.0, corner_amp=0.0, half_w=1.0):
            D = np.zeros_like(base)
            # 下颌：刚性旋转后按 falloff 权重混合，核心区近乎刚性
            R = rotate_jaw(base[li], deg)
            for k, vi in enumerate(li):
                D[vi] = wl[k] * (R[k] - base[vi])
            # 上唇：微上提 + 微后收，避免"整块下坠"
            for k, vi in enumerate(ui):
                D[vi, 2] += wu[k] * UPPER_LIP_LIFT
                D[vi, 1] -= wu[k] * UPPER_LIP_LIFT * 0.3
            # 嘴角上扬（微笑用），tanh 平滑过渡，禁止 sign 硬切换
            if corner_amp > 0:
                for k, vi in enumerate(ui):
                    side = float(np.tanh(1.6 * (base[vi, 0] - c[0]) / half_w))
                    D[vi, 0] += side * wu[k] * corner_amp
                    D[vi, 2] += wu[k] * corner_lift
            return D

        half_w = float(np.abs(base[idx, 0] - c[0]).max()) or 1e-4
        adj = build_adjacency(obj)

        # 张嘴：下颌旋转 + 位移场平滑
        # （不再叠加口腔内凹 —— 实心网格上雕不出可用的口腔空间，
        #   改为独立 mesh 的口腔贴片+牙齿，由前端按权重显隐）
        sk = new_key("mouth_open")
        d = smooth_delta(jaw_delta(JAW_OPEN_DEG), idx, adj)
        for k, vi in enumerate(idx):
            sk.data[int(vi)].co = tuple(base[vi] + d[vi])
        made["mouth_open"] = sk

        # 微笑：嘴角上扬 + 微微张口（闭着嘴笑会显得僵硬）
        sk = new_key("smile")
        d = smooth_delta(
            jaw_delta(JAW_OPEN_DEG * 0.34, corner_lift=0.012,
                      corner_amp=0.013, half_w=half_w), idx, adj)
        for k, vi in enumerate(idx):
            sk.data[int(vi)].co = tuple(base[vi] + d[vi])
        made["smile"] = sk

    log(f"形态键创建完成: Basis + {list(made.keys())}")
    return made


# ---------------------------------------------------------------- 4b. 形变安全自检
# 形态键若让三角形边被拉伸数倍，渲染时纹理会被扯成条状（表现为"乱码/畸变"）。
# 这里在导出前逐个形态键做满权重检查，超标直接报警，避免把坏数据带出去。
MAX_STRETCH = 3.0


def check_shape_safety(obj, base_v, limit=MAX_STRETCH):
    if not obj.data.shape_keys:
        return {}
    polys = obj.data.polygons
    # 只取三角面/四边面的边，构建唯一边表
    eset = set()
    for poly in polys:
        vs = list(poly.vertices)
        for i in range(len(vs)):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            eset.add((a, b) if a < b else (b, a))
    if not eset:
        return {}
    ea = np.fromiter((e[0] for e in eset), dtype=np.int64, count=len(eset))
    eb = np.fromiter((e[1] for e in eset), dtype=np.int64, count=len(eset))

    def edge_len(V):
        return np.linalg.norm(V[ea] - V[eb], axis=1)

    e0 = edge_len(base_v)
    e0 = np.maximum(e0, 1e-9)
    out = {}
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name == "Basis":
            continue
        co = np.zeros((len(obj.data.vertices), 3), dtype=np.float64)
        kb.data.foreach_get("co", co.ravel())
        co = co.reshape(-1, 3)
        delta = co - base_v
        Vm = base_v + delta
        ratio = edge_len(Vm) / e0
        out[kb.name] = {
            "max_stretch": round(float(ratio.max()), 3),
            "edges_over_limit": int((ratio > limit).sum()),
            "total_edges": int(len(e0)),
            "max_displacement": round(float(np.linalg.norm(delta, axis=1).max()), 5),
            "affected_verts": int((np.linalg.norm(delta, axis=1) > 1e-6).sum()),
        }
        flag = "OK " if ratio.max() <= limit else "WARN"
        log(f"  [{flag}] {kb.name:11s} 最大拉伸 {ratio.max():6.2f}x  "
            f"超标边 {int((ratio > limit).sum()):4d}/{len(e0)}  "
            f"最大位移 {np.linalg.norm(delta, axis=1).max():.5f}")
    return out


# ---------------------------------------------------------------- 4c. 牙齿 + 舌头
# 参考真实猫咪张嘴：主要视觉是**粉红色的舌头**从口腔露出，牙齿只是上下
# 两颗细尖犬齿作为点缀。 因此：
#   - 牙齿：仅上颌 2 颗细长犬齿（猫科特征），闭嘴时藏在上唇后方，
#     嘴张得够大时才从唇缘探出。
#   - 舌头：粉色椭圆面片，放在口腔最深处（牙齿之后、口腔贴片之前），
#     是嘴张开时最显眼的元素。
#   - 口腔贴片：暗色背景，让舌头和牙齿有"在洞里"的感觉。
#
# 重要：AI 生成的实心网格没有真正的口腔空腔，因此这些部件都是独立 mesh
# 合并进主网格的，闭嘴时被上下唇遮挡，张嘴时才"露出来"。前端按
# mouth_open / smile 权重统一控制它们的显隐（见 qingya_rig_bundle.js）。
#
# 坐标按 glTF world 语义书写 (x 右, y 高, z 前)，由 g2b() 转换。
MOUTH_X = 0.0295          # 嘴部水平中心（实测嘴区 x[-0.019,0.078]）
LIP_FRONT_Z = 0.370       # 唇面最前端，口腔件必须比它更靠前才可见
ORAL_Z = LIP_FRONT_Z + 0.004       # 口腔贴片（最深的暗背景）
TONGUE_Z = LIP_FRONT_Z + 0.008    # 舌头（在牙齿后，但在所有件里靠前最显眼）
TOOTH_Z = LIP_FRONT_Z + 0.006     # 牙齿（嵌在舌头前面一点点）

# 上颌 2 颗细尖犬齿（猫科特征：比门牙长、比犬科细）
# (名称, x 偏移, 根部 y, 尖端 y, 底半径)
TEETH_GLTF = [
    ("canine_L", MOUTH_X - 0.014, 0.475, 0.430, 0.0055),  # 左犬齿：长 0.045
    ("canine_R", MOUTH_X + 0.014, 0.475, 0.430, 0.0055),  # 右犬齿
]
TOOTH_SEGMENTS = 8
# 舌头：椭圆形粉色面片，嘴张时主要的视觉元素
TONGUE_COLOR = (0.95, 0.56, 0.62, 1.0)   # 猫舌粉色
TONGUE_CX, TONGUE_CY = MOUTH_X, 0.448    # 舌头中心：略偏下，靠近下唇内侧
TONGUE_HALF_W, TONGUE_HALF_H = 0.022, 0.018  # 半宽 / 半高
# 口腔贴片：比舌头稍大一圈的暗色背景，给舌头和牙齿"深度感"
ORAL_W, ORAL_H = 0.044, 0.030            # 半宽 / 半高
ORAL_COLOR = (0.30, 0.12, 0.14, 1.0)


def merge_teeth_into(obj):
    """
    把牙齿 + 舌头 + 口腔贴片合并进主网格。

    为什么不作为独立 mesh：独立 mesh 需要单独绑定 skin，骨骼 bind 矩阵
    会让牙齿位置偏移，实测渲染不出来（几何 z=0.388 > 唇面 0.370 却不可见）。
    合并后这些顶点由 compute_weights() 按位置自动获得 head 骨骼权重
    （它们都在头部区域），既跟头动，也不受形态键影响（不在 mouth 索引内）。
    """
    import bmesh
    verts, faces = [], []

    # ---- 牙齿：2 颗细长犬齿 ----
    for _name, x, root_y, tip_y, radius in TEETH_GLTF:
        cy = (root_y + tip_y) / 2.0
        height = abs(root_y - tip_y)
        base_off = len(verts)
        for i in range(TOOTH_SEGMENTS):
            a = 2.0 * np.pi * i / TOOTH_SEGMENTS
            verts.append((x + radius * np.cos(a),
                          -TOOTH_Z + radius * np.sin(a),   # g2b: glTF z -> Blender -y
                          cy + height / 2.0))
        verts.append((x, -TOOTH_Z, cy + height / 2.0))
        verts.append((x, -TOOTH_Z, cy - height / 2.0))
        root_ctr = base_off + TOOTH_SEGMENTS
        tip_i = base_off + TOOTH_SEGMENTS + 1
        for i in range(TOOTH_SEGMENTS):
            j = (i + 1) % TOOTH_SEGMENTS
            faces.append((base_off + i, base_off + j, tip_i))
            faces.append((base_off + j, base_off + i, root_ctr))
    teeth_face_count = len(faces)

    # ---- 舌头：椭圆形粉色面片 ----
    tongue_off = len(verts)
    cols, rows = 14, 8
    for r_i in range(rows):
        for c_i in range(cols):
            u = (c_i / (cols - 1)) * 2 - 1
            v = (r_i / (rows - 1)) * 2 - 1
            # 舌头表面微微内凹（中心略深），模拟舌头表面
            dz = -0.0035 * (1 - u * u) * (1 - v * v)
            verts.append((TONGUE_CX + u * TONGUE_HALF_W,
                          -(TONGUE_Z + dz),
                          TONGUE_CY + v * TONGUE_HALF_H))
    for r_i in range(rows - 1):
        for c_i in range(cols - 1):
            a = tongue_off + r_i * cols + c_i
            b = a + 1
            c = a + cols
            d = c + 1
            faces.append((a, b, d))
            faces.append((a, d, c))
    tongue_face_count = len(faces) - teeth_face_count

    # ---- 口腔贴片：暗色背景，给口腔件"深度感" ----
    ocx, ocy = MOUTH_X, 0.456
    oral_off = len(verts)
    cols, rows = 10, 6
    for r_i in range(rows):
        for c_i in range(cols):
            u = (c_i / (cols - 1)) * 2 - 1
            v = (r_i / (rows - 1)) * 2 - 1
            dz = -0.006 * (1 - u * u) * (1 - v * v)
            verts.append((ocx + u * ORAL_W,
                          -(ORAL_Z + dz),
                          ocy + v * ORAL_H))
    for r_i in range(rows - 1):
        for c_i in range(cols - 1):
            a = oral_off + r_i * cols + c_i
            b = a + 1
            c = a + cols
            d = c + 1
            faces.append((a, b, d))
            faces.append((a, d, c))
    oral_face_count = len(faces) - teeth_face_count - tongue_face_count

    # ---- 合并进主网格 ----
    start_v = len(obj.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # 材质槽: 主网格已有 + 牙釉质 / 舌粉 / 口腔
    offset = len(obj.data.materials)
    mat_tooth = bpy.data.materials.new("ToothEnamel")
    mat_tooth.use_nodes = True
    bsdf = mat_tooth.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        for key, val in (("Base Color", (0.97, 0.955, 0.90, 1.0)),
                         ("Roughness", 0.26),
                         ("Specular IOR Level", 0.55),
                         ("Specular", 0.55)):
            try:
                bsdf.inputs[key].default_value = val
            except Exception:
                pass
    mat_tongue = bpy.data.materials.new("PinkTongue")
    mat_tongue.use_nodes = True
    tbsdf = mat_tongue.node_tree.nodes.get("Principled BSDF")
    if tbsdf:
        try:
            tbsdf.inputs["Base Color"].default_value = TONGUE_COLOR
        except Exception:
            pass
        try:
            tbsdf.inputs["Roughness"].default_value = 0.55
        except Exception:
            pass
        # 轻微次表面散射感：稍加点自发光模拟舌头的湿润
        try:
            tbsdf.inputs["Emissive Color"].default_value = (0.18, 0.06, 0.08, 1.0)
        except Exception:
            pass
    mat_oral = bpy.data.materials.new("OralCavity")
    mat_oral.use_nodes = True
    obsdf = mat_oral.node_tree.nodes.get("Principled BSDF")
    if obsdf:
        try:
            obsdf.inputs["Base Color"].default_value = ORAL_COLOR
        except Exception:
            pass
        try:
            obsdf.inputs["Roughness"].default_value = 0.85
        except Exception:
            pass
    new_mats = [mat_tooth, mat_tongue, mat_oral]
    for m in new_mats:
        obj.data.materials.append(m)

    # 追加顶点
    new_verts = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()
    # 追加面，并指定材质槽
    # 牙齿 -> offset+0, 舌头 -> offset+1, 口腔 -> offset+2
    for fi, f in enumerate(faces):
        face = bm.faces.new([new_verts[i] for i in f])
        if fi < teeth_face_count:
            face.material_index = offset + 0
        elif fi < teeth_face_count + tongue_face_count:
            face.material_index = offset + 1
        else:
            face.material_index = offset + 2
        face.smooth = False

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    log(f"口腔件已合并进主网格: "
        f"{len(TEETH_GLTF)} 颗犬齿({teeth_face_count}面) + "
        f"舌头({tongue_face_count}面, {cols}×{rows}) + "
        f"口腔贴片({oral_face_count}面), "
        f"共 {len(verts)} 顶点 {len(faces)} 面, 起始索引 {start_v}, "
        f"牙 z={TOOTH_Z:.3f} 舌 z={TONGUE_Z:.3f} 口腔 z={ORAL_Z:.3f} "
        f"(唇面 {LIP_FRONT_Z:.3f})")
    return start_v, start_v + len(verts), teeth_face_count


# ---------------------------------------------------------------- 5. 导出
def export_glb(path):
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        export_yup=True,          # 导出时转回 glTF 的 Y-up，three.js 可直接用
        export_skins=True,
        export_morph=True,
        export_morph_normal=False,
        export_morph_tangent=False,
        export_apply=False,
        export_animations=False,
        export_image_format="JPEG",
    )
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError as e:
        log(f"导出参数降级 (TypeError: {e})")
        kwargs.pop("export_morph_normal", None)
        kwargs.pop("export_morph_tangent", None)
        bpy.ops.export_scene.gltf(**kwargs)
    log(f"已导出: {path}")


# ---------------------------------------------------------------- main
def main():
    log("脚本启动")
    if not os.path.exists(GLB_IN):
        raise RuntimeError(f"找不到输入模型: {GLB_IN}")

    regions = {}
    if os.path.exists(REGIONS):
        with open(REGIONS, "r", encoding="utf-8") as f:
            regions = json.load(f)
        log(f"载入面部区域: {list(regions.keys())}")
        for k, d in regions.items():
            log(f"  {k}: center local {d['center']} -> blender "
                f"{[round(x,4) for x in l2b(d['center'])]}")
    else:
        log("警告: 未找到 face_regions_falloff.json，将跳过形态键")

    clean_scene()
    obj = import_glb(GLB_IN)
    log(f"导入网格: {obj.name}, 顶点 {len(obj.data.vertices)}, 面 {len(obj.data.polygons)}")
    bake_world_transform(obj)

    # 牙齿要在建形态键之前合并进来：合并后原顶点索引保持不变，
    # face_regions 里的索引依旧有效，而牙齿顶点不在其中 -> 形态键位移自动为 0
    teeth_range = merge_teeth_into(obj) if ENABLE_ORAL_PARTS else None
    if not ENABLE_ORAL_PARTS:
        log("ENABLE_ORAL_PARTS=False，跳过牙齿/舌头/口腔贴片")

    nverts = len(obj.data.vertices)
    V = np.zeros((nverts, 3), dtype=np.float64)
    obj.data.vertices.foreach_get("co", V.ravel())
    V = V.reshape(-1, 3)
    log(f"Blender 空间包围盒 min={V.min(0).round(3)} max={V.max(0).round(3)}")

    # 形态键作用于绑定前顶点，所以先建形态键再绑骨骼
    shape_stats = {}
    if regions:
        build_shape_keys(obj, regions)
        log("形变安全自检 (满权重, 阈值 %.1fx):" % MAX_STRETCH)
        shape_stats = check_shape_safety(obj, V)
        bad = [k for k, v in shape_stats.items() if v["edges_over_limit"] > 0]
        if bad:
            log("!! 以下形态键存在撕裂风险: " + ", ".join(bad))

    arm_obj = build_armature()
    segs = segments_from_bones()
    W = compute_weights(V, segs)
    bone_names = [b[0] for b in BONES]
    if not auto_skin(obj, arm_obj, bone_names):
        # 自动权重不可用时的兜底：手写欧氏高斯
        apply_weights(obj, arm_obj, W, bone_names)

    # 从实际写入的顶点组统计主导骨骼（自动权重时 W 已不代表真实结果）
    dom = read_dominant_from_vgroups(obj, bone_names)
    if teeth_range:
        tv = np.arange(teeth_range[0], teeth_range[1])
        if len(tv):
            cnt = np.bincount(dom[tv], minlength=len(bone_names))
            top = int(cnt.argmax())
            log(f"牙齿顶点主导骨骼: {bone_names[top]} ({cnt[top]*100//len(tv)}%)")

    export_glb(GLB_OUT)

    # 骨骼主导顶点数，用于自检布局是否正确
    dist = {n: int((dom == i).sum()) for i, n in enumerate(bone_names)}
    report = {
        "input": os.path.basename(GLB_IN),
        "output": os.path.basename(GLB_OUT),
        "vertices": int(nverts),
        "bones": bone_names,
        "shape_keys": [kb.name for kb in obj.data.shape_keys.key_blocks]
                      if obj.data.shape_keys else [],
        "dominant_vertex_count": dist,
        "bbox_min": V.min(0).round(4).tolist(),
        "bbox_max": V.max(0).round(4).tolist(),
        "shape_safety": shape_stats,
    }
    rp = os.path.join(HERE, "rig_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log("报告已写入 rig_report.json")
    log("主导顶点数: " + json.dumps(dist, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
        log("全部完成")
    except Exception as e:
        import traceback
        traceback.print_exc()
        log("失败: " + str(e))
        sys.exit(1)
