# -*- coding: utf-8 -*-
"""Generate 青芽BUD business plan Word document."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT
import os

OUTPUT_PATH = r"C:\Users\XIAOMI\Desktop\青芽\WKBD\QINGYABUD\outputs\青芽BUD完整计划书V1.0.docx"

def set_chinese_font(run, font_name='Microsoft YaHei', size=10.5, bold=False, color=None):
    font = run.font
    font.name = font_name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    font.size = Pt(size)
    font.bold = bold
    if color:
        font.color.rgb = color

def add_heading_zh(doc, text, level=1):
    """Add heading with Chinese font support."""
    heading = doc.add_heading(level=level)
    run = heading.add_run(text)
    sizes = {1: 18, 2: 14, 3: 12}
    set_chinese_font(run, 'Microsoft YaHei', sizes.get(level, 12), bold=True, color=RGBColor(0x2E, 0x7D, 0x32) if level <= 2 else None)
    return heading

def add_paragraph_zh(doc, text, bold=False, size=10.5, align='left', color=None, first_line_indent=True):
    p = doc.add_paragraph()
    if align == 'center':
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == 'right':
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    set_chinese_font(run, 'Microsoft YaHei', size, bold, color)
    if first_line_indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(6)
    return p

def add_bullet_zh(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet' if level == 0 else 'List Bullet 2')
    run = p.add_run(text)
    set_chinese_font(run, 'Microsoft YaHei', 10.5)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    return p

def add_numbered_zh(doc, text):
    p = doc.add_paragraph(style='List Number')
    run = p.add_run(text)
    set_chinese_font(run, 'Microsoft YaHei', 10.5)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    return p

def add_table_zh(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 3'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        run = hdr_cells[i].paragraphs[0].add_run(h)
        set_chinese_font(run, 'Microsoft YaHei', 10.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            run = row_cells[i].paragraphs[0].add_run(str(val))
            set_chinese_font(run, 'Microsoft YaHei', 10)
    return table

def main():
    doc = Document()
    
    # Set default font for document
    style = doc.styles['Normal']
    style.font.name = 'Microsoft YaHei'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    style.font.size = Pt(10.5)
    
    # Page margins
    sections = doc.sections[0]
    sections.top_margin = Cm(2.5)
    sections.bottom_margin = Cm(2.5)
    sections.left_margin = Cm(2.5)
    sections.right_margin = Cm(2.5)
    
    # ===== COVER =====
    for _ in range(4):
        doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run('青芽BUD')
    set_chinese_font(run, 'Microsoft YaHei', 36, bold=True, color=RGBColor(0x2E, 0x7D, 0x32))
    
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run('正向行为引导电子疗愈宠物')
    set_chinese_font(run, 'Microsoft YaHei', 24, bold=True, color=RGBColor(0x43, 0xA0, 0x47))
    
    doc.add_paragraph()
    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub2.add_run('完整计划书 V1.0')
    set_chinese_font(run, 'Microsoft YaHei', 18, bold=False, color=RGBColor(0x66, 0x66, 0x66))
    
    doc.add_paragraph()
    sub3 = doc.add_paragraph()
    sub3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub3.add_run('IP 3D化 · 视频号/小红书爆款引流 · 小程序与微信接入')
    set_chinese_font(run, 'Microsoft YaHei', 12, bold=False, color=RGBColor(0x88, 0x88, 0x88))
    
    for _ in range(6):
        doc.add_paragraph()
    date_p = doc.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_p.add_run('2026年9月')
    set_chinese_font(run, 'Microsoft YaHei', 12)
    
    doc.add_page_break()
    
    # ===== TOC =====
    add_heading_zh(doc, '目录', level=1)
    doc.add_paragraph('（请在Word中右键目录 → 更新域以生成自动目录）')
    doc.add_page_break()
    
    # ===== 1. 执行摘要 =====
    add_heading_zh(doc, '一、执行摘要', level=1)
    add_paragraph_zh(doc, '青芽BUD 是一款以「正向行为引导」为核心的电子疗愈宠物小程序/APP。用户通过完成早睡早起、做好事、做公益、运动等正向行为，获得喂养和装扮青芽的道具；当用户情绪低落或出现自我伤害倾向时，青芽会同步进入低落状态，并通过温柔互动、安抚动作与正确引导，陪伴用户走出情绪低谷。')
    add_paragraph_zh(doc, '本项目已固定青芽国风3D Q版灵植小兽IP形象，并完成首版3D模型资产。下一阶段重点是：打造视频号与小红书爆款IP账号引流，并快速上线微信小程序与微信聊天入口MVP。')
    
    add_heading_zh(doc, '核心数据目标（12个月）', level=2)
    add_table_zh(doc, ['指标', '目标值', '说明'], [
        ['小红书粉丝', '10万+', '治愈/情感/自律类爆款内容'],
        ['视频号粉丝', '5万+', '真人+青芽合成短片，9:16竖屏'],
        ['小程序MAU', '3万+', 'MVP上线后6个月'],
        ['次日留存率', '≥45%', '情感陪伴型产品核心指标'],
        ['正向行为完成数', '100万+', '打卡/公益/运动等行为累计'],
    ])
    doc.add_paragraph()
    
    # ===== 2. 项目背景 =====
    add_heading_zh(doc, '二、项目背景与市场机会', level=1)
    add_heading_zh(doc, '2.1 心理健康与自我关怀市场持续升温', level=2)
    add_paragraph_zh(doc, '中国心理健康服务市场规模已突破千亿，但专业心理咨询存在供给不足、价格高昂、病耻感强等痛点。年轻用户（Z世代、大学生、职场新人）更倾向于通过低门槛、游戏化、陪伴型产品进行情绪调节与自我管理。电子宠物、疗愈类APP、正念打卡类产品在全球范围内均呈现高速增长。')
    add_heading_zh(doc, '2.2 微信生态是最佳启动阵地', level=2)
    add_bullet_zh(doc, '小程序无需下载，降低用户试用门槛；')
    add_bullet_zh(doc, '微信聊天入口可实现「好友/群聊」场景下的陪伴与提醒；')
    add_bullet_zh(doc, '视频号可直接向小程序导流，形成「内容-互动-工具」闭环；')
    add_bullet_zh(doc, '微信支付、服务通知、朋友圈分享天然适配激励分享与订阅。')
    
    # ===== 3. 产品定位 =====
    add_heading_zh(doc, '三、产品定位', level=1)
    add_heading_zh(doc, '3.1 产品定义', level=2)
    add_paragraph_zh(doc, '青芽BUD = 电子疗愈宠物 + 正向行为激励系统 + 情感陪伴AI。它不是传统记账打卡工具，也不是医疗级心理干预产品，而是一位「住在手机里的温柔伙伴」，通过游戏化机制帮助用户把微小的正向行为养成习惯，并在情绪低谷时提供即时陪伴。')
    add_heading_zh(doc, '3.2 目标用户画像', level=2)
    add_table_zh(doc, ['用户分层', '年龄段', '核心需求', '典型场景'], [
        ['学生党', '16-22岁', '自律、考试压力、孤独感', '熬夜刷手机、考试焦虑、emo时刻'],
        ['职场新人', '22-28岁', '作息规律、情绪管理、自我成长', '加班、失眠、自我怀疑'],
        ['轻度情绪困扰者', '18-30岁', '低成本情绪出口、被陪伴感', '深夜独处、社交退缩'],
        ['公益/运动爱好者', '20-35岁', '行为价值化、成就感', '每日步数、志愿服务、低碳行为'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '3.3 价值主张', level=2)
    add_bullet_zh(doc, '对用户的正向行为即时反馈：每完成一个小目标，青芽都会「长大」一点点；')
    add_bullet_zh(doc, '情绪低谷时不被说教：青芽用动作、陪伴和孢子光效传递「我陪你」；')
    add_bullet_zh(doc, '公益与自我成长连接：做好事、做公益也能喂养青芽，让善意可视化。')
    
    # ===== 4. IP资产 =====
    add_heading_zh(doc, '四、IP形象资产：青芽', level=1)
    add_heading_zh(doc, '4.1 核心设定', level=2)
    add_paragraph_zh(doc, '青芽是一只国风3D Q版灵植小兽，草木灵兽属性。整体感觉是温柔、软糯、有灵性、会陪伴、会释放浅绿色孢子。它不是普通宠物，也不是人类角色，而是介于植物精灵与毛茸小兽之间的存在。')
    add_heading_zh(doc, '4.2 外观规范（严格固定）', level=2)
    add_table_zh(doc, ['部位', '规范', '禁止项'], [
        ['体型', '巴掌大小、圆滚滚、头大身小、幼态比例', '不可忽大忽小、不可成人比例'],
        ['毛发', '米白色为主，浅薄荷绿渐变，毛茸茸细腻柔软', '不可塑料/金属/硬壳质感'],
        ['眼睛', '大圆眼睛，琥珀金色，水汪汪温柔懵懂', '不可黑/蓝/紫/红色'],
        ['头顶', '嫩绿色蕨类嫩芽，可微微发光', '不可变花朵/树叶/角/帽子'],
        ['耳朵', '毛茸茸兽耳，尖圆形状，白绿渐变', '不可人类耳朵/夸张猫耳狐耳'],
        ['配饰', '脖子必须佩戴浅青色叶脉纹理蝴蝶结', '不可换成铃铛/项圈/围巾/项链'],
        ['特效', '释放淡浅绿色荧光孢子，柔和轻盈治愈', '不可刺眼强光/爆炸/战斗光效'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '4.3 3D化成果', level=2)
    add_paragraph_zh(doc, '基于《青芽IP形象固定规范V1.0》及标准参考图，已完成首版3D模型生成。模型采用PBR材质，面数约20万，输出GLB/OBJ格式，可用于小程序3D展示、视频合成、表情包及未来APP场景。')
    add_bullet_zh(doc, '主文件：qingya_3d_20260905.glb（约42MB，GLB格式）')
    add_bullet_zh(doc, '源文件包：qingya_3d_20260905.zip（OBJ+贴图）')
    add_bullet_zh(doc, '预览图：qingya_3d_20260905_preview.png')
    add_bullet_zh(doc, '本地3D预览：http://localhost:18899/qingya_3d_20260905_viewer.html')
    add_paragraph_zh(doc, '后续将根据小程序运行性能与渲染效果，对模型进行LOD（多细节层次）优化，生成低面数版本用于实时渲染。')
    add_heading_zh(doc, '4.4 固定动作库', level=2)
    add_paragraph_zh(doc, '所有短视频、AI短片、表情包、封面图优先使用以下动作：亲脸颊、摸头、蹭脸、钻手心、拍背、怀中陪伴、孢子疗愈。动作表达要克制温柔，不夸张不做怪。')
    add_heading_zh(doc, '4.5 Slogan', level=2)
    add_paragraph_zh(doc, '「青芽｜你的专属疗愈电子宠物，即将住进你的手机。」所有视频结尾统一使用。')
    
    # ===== 5. 核心产品机制 =====
    add_heading_zh(doc, '五、核心产品机制', level=1)
    add_heading_zh(doc, '5.1 正向行为引导体系', level=2)
    add_paragraph_zh(doc, '用户可制定每日/每周正向计划，完成后获得「露珠」「阳光」「灵土」等喂养资源。行为类型分为四大类：')
    add_table_zh(doc, ['行为类型', '示例', '奖励资源', '设计意图'], [
        ['自律作息', '早睡早起、规律三餐、断网时间', '露珠', '重建生活节奏'],
        ['身体运动', '步行5000步、跑步、瑜伽', '阳光', '激活身体改善情绪'],
        ['善意行动', '做好事、夸奖他人、记录感恩', '灵土', '强化社会连接与自我价值'],
        ['公益环保', '捐步、垃圾分类、公益捐赠', '星光', '把个人成长与社会价值连接'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '5.2 青芽状态与情绪映射', level=2)
    add_paragraph_zh(doc, '青芽有独立的健康值、心情值、成长值。用户行为正向 → 青芽状态好、毛发蓬松、孢子明亮；用户熬夜/久坐/情绪低落 → 青芽会蔫、躲起来、发光变暗。')
    add_paragraph_zh(doc, '当系统检测到用户持续情绪低落或表达自我伤害相关内容时，青芽会进入「担忧状态」，主动靠近用户、释放安抚孢子，并引导用户进行深呼吸、倾诉或寻求专业帮助。')
    add_heading_zh(doc, '5.3 喂养与成长系统', level=2)
    add_bullet_zh(doc, '基础喂养：用露珠/阳光/灵土喂养青芽，维持生命值；')
    add_bullet_zh(doc, '装扮系统：解锁浅青色蝴蝶结、蕨芽头饰、小窝背景等（不影响IP核心设定）；')
    add_bullet_zh(doc, '成长阶段：种子→萌芽→幼苗→青芽，每个阶段解锁新动作与互动；')
    add_bullet_zh(doc, '互动反馈：点击、抚摸、语音呼唤，青芽会做出亲脸颊、蹭脸等动作。')
    add_heading_zh(doc, '5.4 计划与打卡', level=2)
    add_bullet_zh(doc, '支持自定义计划模板（早睡早起7天、21天运动挑战、30天感恩日记等）；')
    add_bullet_zh(doc, '支持微信服务通知提醒，避免打扰；')
    add_bullet_zh(doc, '打卡后可生成「青芽成长卡片」分享到朋友圈/群聊。')
    
    # ===== 6. 情感陪伴与危机干预 =====
    add_heading_zh(doc, '六、情感陪伴与危机干预', level=1)
    add_heading_zh(doc, '6.1 情绪低落识别', level=2)
    add_paragraph_zh(doc, '通过多维度信号识别用户情绪状态：打卡中断、深夜活跃、输入负面词汇、语音语调（未来）、连续未完成任务等。识别结果仅用于触发青芽的安抚互动，不用于医疗诊断。')
    add_heading_zh(doc, '6.2 青芽安抚机制', level=2)
    add_bullet_zh(doc, '轻度低落：青芽钻到手心、蹭脸、释放孢子光点；')
    add_bullet_zh(doc, '中度低落：青芽主动说「我陪你」，引导用户完成一次深呼吸或写三行心情；')
    add_bullet_zh(doc, '持续低落：推送「心情树洞」功能，提供情绪记录与可选的专业资源入口。')
    add_heading_zh(doc, '6.3 危险行为识别与引导', level=2)
    add_paragraph_zh(doc, '当用户输入明确自我伤害、自杀倾向等内容时，系统应：')
    add_numbered_zh(doc, '立即切换青芽至「担忧陪伴」状态，表达关心但不惊慌；')
    add_numbered_zh(doc, '提供温和引导话术：「你现在一定很辛苦，我陪你一起缓一缓」；')
    add_numbered_zh(doc, '弹出24小时心理援助热线（如北京回龙观医院心理危机干预热线、各地12355等）；')
    add_numbered_zh(doc, '建议用户联系信任的人，并提供一键复制求助信息的快捷按钮。')
    add_paragraph_zh(doc, '注意：青芽BUD不是医疗产品，所有危机干预均以「陪伴+资源转介」为边界，不涉及诊断、治疗建议或药物推荐。')
    
    # ===== 7. 流量策略 =====
    add_heading_zh(doc, '七、流量策略：视频号 + 小红书爆款IP账号', level=1)
    add_heading_zh(doc, '7.1 账号定位', level=2)
    add_table_zh(doc, ['平台', '账号定位', '内容调性', '更新频率'], [
        ['小红书', '青芽BUD · 你的电子疗愈宠物', '治愈图文、自律打卡、情绪共鸣、青芽日常', '每日1-2条，笔记+短视频'],
        ['视频号', '青芽BUD官方', '真人+青芽合成短片、情感故事、产品预告', '每周3-5条'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '7.2 内容矩阵', level=2)
    add_table_zh(doc, ['内容类型', '平台', '形式', '目的'], [
        ['情绪共鸣故事', '双平台', '15-25秒竖屏短片', '引发共鸣，建立情感连接'],
        ['青芽动作教程', '小红书', '图文/短视频', '展示IP，强化形象记忆'],
        ['用户打卡挑战', '双平台', '话题/合集', '促进UGC与小程序转化'],
        ['公益行动记录', '视频号', '真人+青芽短片', '传递品牌价值'],
        ['产品功能预告', '双平台', '短视频/图文', '引导搜索小程序'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '7.3 爆款公式', level=2)
    add_bullet_zh(doc, '前3秒强情绪钩子：「凌晨两点，我又醒了」「今天被领导骂了」；')
    add_bullet_zh(doc, '中间青芽作为情绪转折点出现，用亲脸颊/摸头/拍背等动作安抚；')
    add_bullet_zh(doc, '结尾情绪回暖+产品钩子+固定Slogan；')
    add_bullet_zh(doc, '字幕白色细体、关键句浅绿高亮、每句不超过14字、不挡青芽和人脸。')
    add_heading_zh(doc, '7.4 引流路径', level=2)
    add_numbered_zh(doc, '短视频/笔记引导搜索「青芽BUD」；')
    add_numbered_zh(doc, '主页置顶笔记放置小程序入口与微信聊天入口二维码；')
    add_numbered_zh(doc, '评论区运营：用青芽表情包回复，引导用户「领养青芽」；')
    add_numbered_zh(doc, '私域沉淀：引导加入「青芽陪伴群」，每日打卡互相鼓励。')
    
    # ===== 8. 技术开发路线 =====
    add_heading_zh(doc, '八、技术开发路线', level=1)
    add_heading_zh(doc, '8.1 整体架构', level=2)
    add_paragraph_zh(doc, '采用「小程序前端 + 微信云开发/云服务后端 + AI对话服务 + 3D渲染」的轻量架构，优先用微信生态能力降低早期成本。')
    add_heading_zh(doc, '8.2 小程序MVP功能清单', level=2)
    add_table_zh(doc, ['模块', 'MVP功能', '优先级'], [
        ['首页', '青芽3D展示、状态面板、快捷互动', 'P0'],
        ['计划', '创建计划、打卡、查看历史', 'P0'],
        ['商城', '用行为积分兑换喂养/装扮道具', 'P0'],
        ['心情', '情绪记录、安抚互动、资源入口', 'P1'],
        ['我的', '成长档案、分享卡片、设置', 'P1'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '8.3 微信聊天入口', level=2)
    add_bullet_zh(doc, '以微信公众号/服务号菜单或小程序客服消息为载体；')
    add_bullet_zh(doc, '用户可在聊天窗口与青芽对话，例如「我今晚想早睡」「我有点难过」；')
    add_bullet_zh(doc, '青芽识别意图后返回图文卡片，跳转小程序完成打卡或安抚互动；')
    add_bullet_zh(doc, '支持微信群场景：用户分享打卡卡片，群内成员可点赞鼓励。')
    add_heading_zh(doc, '8.4 技术选型', level=2)
    add_table_zh(doc, ['层', '选型建议', '说明'], [
        ['小程序前端', '微信小程序原生/Taro', '优先原生，保证3D性能'],
        ['3D渲染', 'Three.js / Babylon.js + GLB', '轻量、跨平台'],
        ['后端', '微信云开发 / Node.js + 云数据库', '降低运维成本'],
        ['AI对话', '混元大模型/文心一言API', '情感意图识别与回复生成'],
        ['数据库', '云开发数据库 / PostgreSQL', '用户数据、打卡记录、行为日志'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '8.5 APP后续规划', level=2)
    add_paragraph_zh(doc, '小程序验证PMF（产品-市场匹配）后，启动APP开发。APP将支持更复杂的3D交互、离线陪伴、Widget小组件、健康数据同步（运动/睡眠）等功能。')
    
    # ===== 9. 运营计划 =====
    add_heading_zh(doc, '九、运营计划', level=1)
    add_heading_zh(doc, '9.1 冷启动策略', level=2)
    add_bullet_zh(doc, '种子用户：从小红书/视频号粉丝、朋友圈、大学生社群招募1000名「青芽领养官」；')
    add_bullet_zh(doc, '内测激励：连续打卡7天获得限定装扮，邀请好友领养获得稀有孢子特效；')
    add_bullet_zh(doc, '内容共创：鼓励用户晒出青芽陪伴瞬间，官方转发并赠送道具。')
    add_heading_zh(doc, '9.2 用户激励体系', level=2)
    add_bullet_zh(doc, '每日签到、连续打卡、成就徽章；')
    add_bullet_zh(doc, '公益联名：与公益机构合作，用户完成公益行为可获得联名装扮；')
    add_bullet_zh(doc, '赛季活动：如「21天早睡挑战」「春季发芽计划」。')
    add_heading_zh(doc, '9.3 关键数据指标', level=2)
    add_table_zh(doc, ['指标', '定义', '目标'], [
        ['新增领养', '首次进入小程序并完成新手引导', '月新增5000+'],
        ['次日留存', '次日再次打开小程序用户占比', '≥45%'],
        ['7日留存', '7日内再次打开小程序用户占比', '≥25%'],
        ['打卡完成率', '创建计划后实际完成比例', '≥60%'],
        ['分享率', '用户主动分享卡片/邀请比例', '≥15%'],
    ])
    doc.add_paragraph()
    
    # ===== 10. 商业化 =====
    add_heading_zh(doc, '十、商业化模式', level=1)
    add_heading_zh(doc, '10.1 收入来源', level=2)
    add_table_zh(doc, ['模式', '说明', '预计占比'], [
        ['道具内购', '限定装扮、孢子特效、加速成长道具', '50%'],
        ['会员订阅', '青芽Plus：去广告、专属动作、成长报告', '30%'],
        ['品牌联名', '与公益组织、生活方式品牌联名活动', '15%'],
        ['企业服务', '为员工关怀/心理健康提供定制版本', '5%'],
    ])
    doc.add_paragraph()
    add_heading_zh(doc, '10.2 成本结构', level=2)
    add_bullet_zh(doc, '研发成本：小程序/APP开发、3D资产、AI服务；')
    add_bullet_zh(doc, '内容成本：视频号/小红书内容制作、KOL合作；')
    add_bullet_zh(doc, '运营成本：用户增长、客服、社群；')
    add_bullet_zh(doc, '合规成本：心理安全审核、未成年人保护、数据合规。')
    
    # ===== 11. 里程碑 =====
    add_heading_zh(doc, '十一、里程碑与时间表', level=1)
    add_table_zh(doc, ['阶段', '时间', '关键目标', '交付物'], [
        ['Phase 1 筹备期', '0-2个月', '完成3D模型优化、账号启动、小程序原型', '优化版3D模型、10条短视频/笔记、小程序Demo'],
        ['Phase 2 MVP上线', '2-4个月', '小程序正式上线，启动1000人内测', '小程序V1.0、首批种子用户、留存数据'],
        ['Phase 3 增长期', '4-6个月', '视频号/小红书爆款突破，用户规模化', '5万+粉丝、月新增5000+用户'],
        ['Phase 4 产品深化', '6-12个月', '完善AI陪伴、启动APP预研、探索商业化', 'AI情绪陪伴、APP原型、付费转化验证'],
    ])
    doc.add_paragraph()
    
    # ===== 12. 风险与合规 =====
    add_heading_zh(doc, '十二、风险与合规', level=1)
    add_heading_zh(doc, '12.1 心理健康合规', level=2)
    add_paragraph_zh(doc, '明确产品定位：青芽BUD是情感陪伴与正向行为激励工具，不是医疗、心理咨询或诊断服务。所有涉及情绪危机的交互必须以「陪伴+资源转介」为边界，提供可核实的心理援助热线。')
    add_heading_zh(doc, '12.2 未成年人保护', level=2)
    add_bullet_zh(doc, '接入微信/APP实名与年龄验证；')
    add_bullet_zh(doc, '未成年人使用时长限制与消费限制；')
    add_bullet_zh(doc, '针对未成年人的危机干预话术需更温和，并优先引导联系家长/老师。')
    add_heading_zh(doc, '12.3 数据隐私', level=2)
    add_bullet_zh(doc, '用户情绪数据、打卡数据加密存储；')
    add_bullet_zh(doc, '明确隐私政策，不将个人情绪数据用于广告定向；')
    add_bullet_zh(doc, '提供数据导出与删除入口。')
    add_heading_zh(doc, '12.4 内容安全', level=2)
    add_bullet_zh(doc, '建立AI回复安全审核机制，避免出现危险建议；')
    add_bullet_zh(doc, '用户UGC内容（心情树洞）需经过审核或敏感词过滤；')
    add_bullet_zh(doc, '定期审查青芽形象使用，确保符合IP规范。')
    
    # ===== 13. 附录 =====
    add_heading_zh(doc, '十三、附录', level=1)
    add_heading_zh(doc, '13.1 IP形象检查清单', level=2)
    add_bullet_zh(doc, '头顶是蕨芽，不是花、叶子、角或帽子；')
    add_bullet_zh(doc, '脖子上的叶脉蝴蝶结存在；')
    add_bullet_zh(doc, '眼睛是琥珀金色；')
    add_bullet_zh(doc, '体型是巴掌大小圆滚滚；')
    add_bullet_zh(doc, '主色是米白和薄荷绿，无粉色/紫色/大红色；')
    add_bullet_zh(doc, '动作温柔安抚，不搞怪夸张。')
    add_heading_zh(doc, '13.2 参考文档与资产', level=2)
    add_bullet_zh(doc, '《青芽IP形象固定规范V1.0》定稿.docx')
    add_bullet_zh(doc, '青芽标准参考图：qingya_reference.jpg')
    add_bullet_zh(doc, '青芽3D模型：qingya_3d_20260905.glb / .zip')
    add_bullet_zh(doc, '青芽3D预览：http://localhost:18899/qingya_3d_20260905_viewer.html')
    add_heading_zh(doc, '13.3 AI生成固定提示词', level=2)
    add_paragraph_zh(doc, '正面词：国风3D Q版灵植小兽青芽，巴掌大小圆滚滚幼态体型，白绿渐变细腻毛茸茸毛发，头顶固定嫩绿色发光蕨芽，琥珀金色大圆水汪汪眼睛，脖子佩戴浅青色叶脉蝴蝶结，圆乎乎兽耳，释放零星柔和浅绿色荧光孢子，OC渲染，柔和柔光，毛发质感真实，形象严格与参考图保持一致，不许改变五官、配饰、体型，无变形，无扭曲，无文字，无水印。')
    add_paragraph_zh(doc, '负面词：畸形，五官错乱，配饰消失，蕨芽变成花朵，配色改变，粉色，紫色，人形，人脸，尖锐，恐怖，文字，水印，logo，肢体变形，比例崩坏。')
    
    doc.save(OUTPUT_PATH)
    print(f"Plan document saved to: {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
