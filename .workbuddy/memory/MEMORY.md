# 青芽BUD 项目长期记忆

## 项目定位

青芽BUD：正向行为引导电子疗愈宠物小程序/APP。用户通过早睡早起、做好事、做公益、运动等正向行为获得喂养青芽的道具；情绪低落或自我伤害时，青芽会状态变差并温柔安抚、正确引导。

## 关键资产

- IP形象已固定：《青芽IP形象固定规范V1.0》定稿。
- 首版3D模型已生成（GLB/OBJ），路径在 `outputs/qingya_3d_20260905.*`。
- 3D模型已迭代至V4：多视角（正面/侧面/背面）约束生成，侧面轮廓更饱满；同时产出3.2MB兼容轻量版（`outputs/v4/qingya_3d_v4_web.glb`，无Draco压缩，6.3万面，所有GLB查看器可打开）。
- 本地3D预览服务端口：18899。

## 当前阶段

已完成：IP解析、3D首版、完整商业计划书。
下一步建议：3D模型LOD优化、视频号/小红书账号启动、小程序原型开发。

## 3D 动画技术决策（重要）

- **动画一律用 Blender 骨骼 + 形态键，禁止再手写逐顶点动画。**
  手写顶点动画曾把三角形边拉伸 369 倍，画面出现撕裂/乱码状伪影。
- 形态键里判定左右方向时**禁止用 sign() 硬切换**，必须用 tanh 平滑过渡
  （sign 会让相邻顶点反向跳变，实测 31.7 倍拉伸）。
- `outputs/v4/qingya_rig.py` 内置 `check_shape_safety()`：导出前按满权重检查三角形边长拉伸比，
  阈值 3.0x，超标即报警。以后新增任何形态键都要跑这个自检。
- Blender 4.2.9 便携版路径：
  `C:\Users\XIAOMI\.workbuddy\binaries\blender\blender-4.2.9-windows-x64\blender.exe`
  ⚠️ 必须用 `cd` 到脚本目录再 `--python 脚本名.py`；传绝对路径会被 Blender 拼成
  `<cwd>\<绝对路径>` 而报 file not found。
- V4 骨骼版成品：`outputs/v4/qingya_3d_v4_rigged.glb`（14 骨骼 + 6 形态键）与
  单文件预览 `outputs/v4/qingya_3d_v4_rigged.html`。

## 嘴部动画：已放弃（2026-09-06 用户决策）

**用户明确不要嘴部动画：不做张嘴、不做微笑，也不要牙齿/舌头。**
当前主版本是 `qingya_3d_v4_clean.*`（14 骨骼 + 4 形态键：blink_L/R、squint_L/R）。

`qingya_rig.py` 顶部两个开关控制，默认都关：

```python
ENABLE_MOUTH_KEYS = False   # mouth_open / smile 形态键
ENABLE_ORAL_PARTS = False   # 牙齿 / 舌头 / 口腔贴片
```

都改成 True 即可还原带嘴版（牙齿2犬齿 + 舌头 PinkTongue + 口腔贴片，
前端 bundle 里材质正则已含 `PinkTongue`，会随张嘴显隐）。
**别再主动重做嘴部，除非用户明确要求。**

## 本地预览服务

端口 18899，**根目录是 `outputs/`**（不是 `outputs/v4/`）。
正确 URL 形如 `http://127.0.0.1:18899/v4/qingya_3d_v4_clean.html`。

## 用户偏好

- 项目名暂定为「青芽BUD」。
- 需要同步做视频号、小红书爆款IP账号引流。
- 优先做出小程序和微信接入聊天入口。
