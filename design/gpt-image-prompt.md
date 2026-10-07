# 奇境王冠 · 对局界面重构 · GPT 生图提示词

用法：把「主提示词」整段发给 GPT（图像生成），比例选 16:9 横版。想看别的城堡方向或手机版，就在主提示词后面追加对应的「变体」段落。生成结果不满意时，追加「修正指令」里对应的一句即可，不用重写整段。

---

## 主提示词（中文，可直接用）

请生成一张手机/电脑横屏策略小游戏的**对局界面完整截图**，16:9，1920×1080 构图，看起来像一款已经上线、制作精良的独立游戏。

**整体风格**：童话绘本 × 精致休闲手游。正俯视视角（top-down，镜头垂直向下，不要透视、不要斜视、没有天空和地平线）。手绘水彩质感的扁平插画：柔和色块、轻微纸张颗粒、干净的深紫棕色细描边（不是黑色），阴影只用很淡的落地投影。明亮、温暖、清晨阳光感，饱和度适中、不刺眼。参考气质：《皇室战争》的读图清晰度 + 《动物森友会》的柔和配色 + 儿童绘本的手绘笔触。

**战场（占画面中间约 70% 高度）**：
- 一整片柔软的春日草坪，浅苹果绿到嫩黄绿的渐变，零星小白花、粉色雏菊和三叶草点缀，四周边缘是圆润的灌木丛和花丛，装饰集中在边缘，中间留空以保证战斗清晰。
- 三条奶油沙色小路从左到右横穿战场，路宽适中、边缘有一圈清晰的嫩绿色草边。上路和下路在画面正中央呈 X 形交叉汇合，中路笔直穿过交汇点；交汇处有一个小小的圆形石砖花纹广场。所有分岔和汇合的内角都是**圆润的弧线过渡**，没有尖角。路面干净，只有少量浅色小石子，**路中间没有白线**。
- 左侧是蓝方阵营，右侧是红方阵营，左右镜像对称。

**城堡（左右两端各一座，竖向覆盖三条路）**：
- 造型：一组相连的**童话圆塔要塞**。上路、下路尽头各一座小圆塔，中路尽头是一座更大的王塔，三座塔之间用低矮的奶油色石墙连接。正俯视下塔顶是圆形：奶油白石材外圈 + 一圈可爱的方形城垛 + 阵营色（蓝方天蓝 / 红方珊瑚粉）的放射状尖顶瓦片，中心一颗金色顶珠，每座塔插一面阵营色三角小旗。
- 每座塔面向道路的一侧有一个**深紫色拱形门洞、金色门框**，门正对道路，门前铺一块浅米色石板出生平台。
- 王塔正中央架着**唯一一门主炮**：圆形阵营色底座、白色描边、四颗金铆钉，深灰色短粗炮管指向战场，Q 版可爱，不写实。

**单位（战场上分散 6–8 个）**：
- 使用**系统 Emoji 风格**的小动物：🐍 绿蛇、🦁 狮子、🐘 大象、🐉 绿龙。每只动物站在一个圆形底座上：蓝方是浅蓝底 + 天蓝细圈，红方是浅粉底 + 珊瑚红细圈，底下有柔和的椭圆落地影。动物严格走在道路中线上。
- 画面里有一两处正在交战：小星形碰撞光点、一只单位头顶有细细的圆角血条；一颗炮弹带着一小段白色拖尾从王塔飞向敌人。

**顶部 HUD（细长一条，约占画面高度 8%）**：
- 左侧：蓝方血量牌，奶油色圆角胶囊，左端一个蓝色圆形徽章（皇冠图标），文字“曙光王庭”，右侧数字“10000”，下方蓝色血条。
- 右侧：红方血量牌，镜像布局，红色徽章，文字“暮影王庭”。
- 正中：倒计时牌，奶黄到金黄的渐变胶囊，大号圆润数字“04:45”，下面小字“交汇战线”。
- 最右上角：一个圆形菜单按钮（三条横线）。

**底部 HUD（约占画面高度 18%）**：
- 正中一个**淡粉紫色圆角托盘**：紫色边框、外圈一道奶黄描边，托盘左上角点缀一朵🌸，右上角一朵🌼。托盘里从左到右依次是：
  1. 金币块：暖黄色圆角卡，“🟡 19.4”，下面一条深棕槽 + 金色渐变进度条，小字“金币增长：1 / 秒”。
  2. 四张竖版卡牌：奶白色细边框、紫色外描边、圆角，各自有饱和的柔和渐变底：蛇是嫩绿、狮子是橙黄、大象是天蓝、龙是淡紫。卡面上半部是大号 Emoji 动物，下面是粗体卡名“毒影蛇 / 圣鬃狮 / 磐石象 / 星焰龙”和一行小字定位“快速刺客 / 均衡战士 / 慢速坦克 / 远程魔法”。每张卡右上角一枚立体金币角标写着“10”。其中一张卡被选中（向上微浮、金色发光描边），一张卡正在冷却（底部升起半透明深色遮罩，中间写“3.2”）。
- 左下角两个独立技能按钮：淡紫色“魔力药水”（🧪图标）和蜜桃橙色“爆裂炮阵”（一门横向的可爱小炮图标），奶黄细边、紫色外描边、右上角小金币角标。

**文字**：所有界面文字都是简体中文，圆润粗体（类似“站酷快乐体”或“汉仪小麦体”的可爱感），清晰可读、不要乱码。

**不要**：写实材质、3D 渲染感、强烈高光和厚重阴影、黑色粗描边、透视地平线和天空、过度花哨的背景、文字乱码、多余的 UI 元素、水印。

---

## English version (if Chinese text comes out garbled, use this and keep the quoted Chinese UI strings)

A complete in-game battle screen of a polished landscape strategy game, 16:9, 1920×1080. Strict top-down orthographic view, no perspective, no sky, no horizon. Hand-painted storybook watercolor meets premium casual mobile game: soft flat color shapes, subtle paper grain, clean thin dark plum-brown outlines (never black), only very light drop shadows. Bright warm morning light, gentle saturation. Mood: Clash Royale's readability + Animal Crossing's soft palette + children's picture book brushwork.

Battlefield (middle ~70% of height): a soft spring lawn, apple-green to fresh yellow-green, sparse tiny white flowers and pink daisies, rounded bushes and flower clusters only along the edges, center kept clean. Three creamy sand-colored paths cross from left to right with a crisp light-green grass rim. Top and bottom paths cross in an X at the exact center while the middle path runs straight through; a small round patterned stone plaza at the crossing. Every fork and merge has smooth rounded inner corners. Clean path surface with a few pebbles, no center line. Blue team on the left, red team on the right, mirror symmetric.

Castles (one at each end, spanning all three lanes vertically): a connected group of fairy-tale round towers — a small tower at the end of the top and bottom lanes, a larger king tower at the middle lane, joined by low cream stone walls. Seen from above, each tower roof is a circle: cream stone rim, a ring of cute square battlements, radial team-colored roof tiles (sky blue / coral pink), a golden finial in the center, and a small triangular team flag. Each tower has a deep purple arched gate with a gold frame facing its lane, and a pale beige stone spawn pad in front. The king tower carries the only cannon: round team-colored base with white rim and four gold rivets, short chunky dark-gray barrel aimed at the field, cute chibi style.

Units (6–8 spread on the paths): emoji-style animals 🐍 🦁 🐘 🐉, each standing on a round token — blue team pale-blue fill with a thin sky-blue ring, red team pale-pink fill with a thin coral ring — with a soft oval ground shadow, walking exactly on the path centerline. One or two small fights with star-shaped spark hits, a thin rounded health bar over one unit, and a cannonball with a short white trail flying from the king tower.

Top HUD (thin strip, ~8% height): left a cream capsule health plate with a blue round crest (crown icon), text "曙光王庭", number "10000", blue health bar; right the mirrored red plate "暮影王庭"; center a butter-yellow to gold gradient timer capsule with big rounded digits "04:45" and small text "交汇战线"; top-right corner a round hamburger menu button.

Bottom HUD (~18% height): a pale pink-lilac rounded tray in the center with a purple border and a cream outer outline, a 🌸 on its top-left corner and a 🌼 on its top-right. Inside, left to right: a warm-yellow coin block "🟡 19.4" with a dark-brown slot and golden progress bar and tiny text "金币增长：1 / 秒"; then four portrait cards with cream thin borders, purple outer outline and rounded corners, saturated soft gradients — snake fresh green, lion orange-yellow, elephant sky blue, dragon lavender — big emoji animal on top, bold name "毒影蛇 / 圣鬃狮 / 磐石象 / 星焰龙" and a small role line "快速刺客 / 均衡战士 / 慢速坦克 / 远程魔法", a glossy gold coin badge "10" at each top-right. One card is selected (lifted, golden glowing outline), one is cooling down (translucent dark overlay rising from the bottom with "3.2"). Bottom-left: two separate skill buttons, lilac "魔力药水" with 🧪 and peach-orange "爆裂炮阵" with a cute sideways mini cannon icon, cream border, purple outline, small gold coin badges.

All UI text in Simplified Chinese, rounded bold cute font, crisp and legible. Avoid: realistic materials, 3D render look, strong highlights or heavy shadows, thick black outlines, perspective horizon or sky, busy background, garbled text, extra UI elements, watermark.

---

## 变体（追加在主提示词后面）

- **城堡换成蘑菇童话村**：把城堡改成三朵大蘑菇屋，菌盖是阵营色（蓝 / 珊瑚红）带奶白圆斑，门廊和圆木门朝向道路，中间最大的蘑菇伞顶上架主炮；身后是木篱笆和花丛。其余不变。
- **城堡换成糖果蛋糕城**：把城堡改成三座俯视的圆形奶油蛋糕塔，阵营色糖霜、彩色糖粒，饼干色拱门朝向道路，侧塔顶上一颗红樱桃，中间大蛋糕顶上架主炮；身后是威化饼格纹墙和棒棒糖柱。其余不变。
- **手机横屏版**：画面比例改成 19.5:9 超宽，战场左右拉长，三条路更长；顶部 HUD 和底部托盘按比例保持可读，按钮更大便于手指点按，左右边缘留出刘海安全区。
- **首页菜单**：同一美术风格的开始界面，草坪背景虚化，中间一块奶油色圆角大卡片，顶部大号标题“奇境王冠”带小皇冠，两个模式选项“三路战线 / 交汇战线”，一个时长下拉框，一个大号金黄色“进入战场”按钮，底部小字版本号。
- **胜利结算**：对局画面上覆盖一层淡淡的暖色蒙层，中间一块带彩带和星星的结算卡，大字“胜利”，下方双方城门剩余血量对比，两个按钮“重新开始 / 返回首页”。

## 修正指令（结果不满意时追加一句）

- 视角不对：「镜头必须是正上方垂直俯视，去掉所有透视、地平线和天空。」
- 太写实：「降低写实感，改为扁平手绘绘本插画，减少高光和材质细节。」
- 太花：「减少草地上的花和装饰，让道路和单位更醒目，装饰只放在画面边缘。」
- 字是乱码：「界面文字只保留：曙光王庭、暮影王庭、04:45、交汇战线、毒影蛇、圣鬃狮、磐石象、星焰龙、魔力药水、爆裂炮阵，其余文字去掉。」
- 卡牌不好看：「卡牌参考精致卡牌手游：圆角竖卡、柔和渐变底、Emoji 主图居中偏上、右上角立体金币角标、粗体卡名。」
- 城堡突兀：「城堡的颜色和描边要与草地、道路同一画风，奶油色石材 + 阵营色点缀，不要灰色写实石墙。」
