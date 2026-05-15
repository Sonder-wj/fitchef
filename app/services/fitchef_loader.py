# services/fitchef_loader.py
# 职责：加载 FitChef 知识库（食材营养 + 食谱 + 膳食指南）
# 接口与 tcm_loader 一致，可无缝替换

import json
from pathlib import Path
from typing import List, Dict

DATA_DIR = Path(__file__).parent.parent / "data"

# ═══════════════════════════════════════════════════════════════
# 数据容器（保持与 TCMDocument 相同接口）
# ═══════════════════════════════════════════════════════════════

class FitChefDocument:
    def __init__(self, doc_id: str, text: str, metadata: dict):
        self.id = doc_id
        self.text = text
        self.metadata = metadata


# ═══════════════════════════════════════════════════════════════
# 精选食谱（减脂 / 增肌 / 快手 / 家常 / 早餐 / 汤羹）
# ═══════════════════════════════════════════════════════════════

RECIPES = [
    # ── 减脂餐 ──
    {"type":"recipe","name":"香煎鸡胸肉","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["减脂","高蛋白","快手"],"ingredients":["鸡胸肉200g","橄榄油5g","黑胡椒","盐","蒜2瓣","柠檬汁"],"steps":["鸡胸肉横切成两片，用刀背轻轻拍松","撒盐、黑胡椒、蒜末腌制10分钟","热锅倒橄榄油，中火每面煎4-5分钟至金黄","出锅挤柠檬汁即可"],"nutrition":{"calories":290,"protein_g":42,"fat_g":11,"carbs_g":2},"tips":"搭配西兰花和糙米饭，就是完美的减脂餐"},
    {"type":"recipe","name":"西兰花炒虾仁","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["减脂","高蛋白","快手"],"ingredients":["西兰花200g","虾仁150g","蒜3瓣","盐","料酒","橄榄油5g"],"steps":["西兰花掰小朵焯水1分钟捞出","虾仁加料酒、盐腌5分钟","热锅倒油，炒香蒜末","下虾仁炒至变色，加西兰花翻炒均匀"],"nutrition":{"calories":230,"protein_g":35,"fat_g":8,"carbs_g":10},"tips":"西兰花焯水时加少许盐和油，颜色更翠绿"},
    {"type":"recipe","name":"番茄菌菇豆腐汤","meal":"午餐/晚餐","time":20,"diff":"简单","tags":["减脂","低卡","素食"],"ingredients":["番茄2个","嫩豆腐200g","金针菇100g","鸡蛋1个","葱花","盐","白胡椒粉"],"steps":["番茄去皮切块，豆腐切小块，金针菇去根撕开","热锅少许油炒番茄至出汁","加500ml水烧开，放入金针菇煮2分钟","下豆腐煮2分钟，淋蛋花","加盐、白胡椒粉调味，撒葱花出锅"],"nutrition":{"calories":180,"protein_g":18,"fat_g":7,"carbs_g":15},"tips":"番茄炒出沙再加水，汤底更浓郁"},
    {"type":"recipe","name":"凉拌鸡丝","meal":"午餐/晚餐","time":20,"diff":"简单","tags":["减脂","高蛋白","凉拌","夏季"],"ingredients":["鸡胸肉200g","黄瓜1根","香菜","生抽","醋","辣椒油","蒜末","芝麻"],"steps":["鸡胸肉冷水下锅加姜片料酒，煮熟后捞出放凉","鸡胸肉手撕成丝，黄瓜切丝","碗中调汁：生抽2勺+醋1勺+辣椒油少许+蒜末","鸡丝黄瓜拌匀淋酱汁，撒香菜芝麻"],"nutrition":{"calories":260,"protein_g":40,"fat_g":10,"carbs_g":5},"tips":"鸡胸肉冷水下锅，水开后转小火焖熟更嫩"},
    {"type":"recipe","name":"蒸龙利鱼","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["减脂","高蛋白","无油"],"ingredients":["龙利鱼柳200g","姜丝","葱丝","蒸鱼豉油","料酒"],"steps":["鱼柳用料酒、姜丝腌制10分钟","水开后上锅蒸8分钟","倒掉盘里多余的水","铺上葱丝，淋蒸鱼豉油，热油泼一下即可"],"nutrition":{"calories":180,"protein_g":36,"fat_g":4,"carbs_g":1},"tips":"龙利鱼也可以换成巴沙鱼或鳕鱼"},
    {"type":"recipe","name":"藜麦鸡胸沙拉","meal":"午餐","time":25,"diff":"简单","tags":["减脂","高蛋白","沙拉"],"ingredients":["藜麦50g","鸡胸肉150g","生菜","小番茄","黄瓜","橄榄油","柠檬汁","黑胡椒"],"steps":["藜麦洗净煮15分钟沥干放凉","鸡胸肉煎熟切片","生菜撕碎，小番茄对半切，黄瓜切片","所有食材混合，淋橄榄油+柠檬汁+黑胡椒"],"nutrition":{"calories":380,"protein_g":38,"fat_g":14,"carbs_g":28},"tips":"藜麦提前泡30分钟去掉苦味（皂苷）"},
    {"type":"recipe","name":"蚝油生菜","meal":"午餐/晚餐","time":5,"diff":"简单","tags":["减脂","低卡","快手","素菜"],"ingredients":["生菜300g","蚝油2勺","蒜末","生抽","淀粉少许"],"steps":["生菜焯水10秒捞出摆盘（水里加盐和油）","碗中调汁：蚝油+生抽+淀粉+水搅匀","热油炒香蒜末，倒入料汁煮至浓稠","淋在生菜上即可"],"nutrition":{"calories":60,"protein_g":3,"fat_g":3,"carbs_g":8},"tips":"焯水时间要短，保持脆嫩口感"},
    {"type":"recipe","name":"冬瓜虾皮汤","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["减脂","低卡","消肿"],"ingredients":["冬瓜300g","虾皮10g","姜片","葱花","盐","白胡椒粉"],"steps":["冬瓜去皮切片，虾皮冲洗一下","热锅少许油爆香姜片","下冬瓜翻炒1分钟，加600ml水烧开","放入虾皮煮8分钟至冬瓜透明","加盐和白胡椒粉调味，撒葱花"],"nutrition":{"calories":50,"protein_g":4,"fat_g":1,"carbs_g":8},"tips":"冬瓜利水消肿，减脂期晚餐喝这个很合适"},
    {"type":"recipe","name":"秋葵蒸蛋","meal":"早餐/午餐","time":15,"diff":"简单","tags":["减脂","高蛋白","早餐"],"ingredients":["鸡蛋2个","秋葵3根","温水","生抽","香油"],"steps":["鸡蛋打散加1.5倍温水搅匀，过筛去泡沫","秋葵切薄片放在蛋液上","盖上保鲜膜扎几个孔，水开蒸10分钟","出锅淋少许生抽和香油"],"nutrition":{"calories":180,"protein_g":14,"fat_g":11,"carbs_g":6},"tips":"温水蒸蛋更嫩滑，过筛是嫩的关键"},
    {"type":"recipe","name":"蒜蓉空心菜","meal":"午餐/晚餐","time":8,"diff":"简单","tags":["减脂","快手","素菜"],"ingredients":["空心菜300g","蒜5瓣","盐","橄榄油5g"],"steps":["空心菜摘段洗净，茎和叶分开放","蒜切成蒜末","热锅倒油，先下蒜末爆香","先炒茎30秒，再下叶子大火快炒","加盐翻炒均匀出锅"],"nutrition":{"calories":80,"protein_g":5,"fat_g":5,"carbs_g":8},"tips":"茎叶分开下锅，保证茎熟了叶不烂"},  # continued...

    # ── 增肌餐 ──
    {"type":"recipe","name":"牛肉炒西兰花","meal":"午餐/晚餐","time":20,"diff":"中等","tags":["增肌","高蛋白"],"ingredients":["牛里脊200g","西兰花200g","蒜","姜","生抽","蚝油","淀粉","料酒","橄榄油10g"],"steps":["牛肉逆纹切片，加生抽+料酒+淀粉腌15分钟","西兰花焯水1分钟捞出","热锅倒油，大火快速滑炒牛肉至变色盛出","余油炒香蒜姜，下西兰花和牛肉回锅翻炒","加蚝油调味出锅"],"nutrition":{"calories":380,"protein_g":45,"fat_g":16,"carbs_g":12},"tips":"牛肉逆纹切+淀粉腌制，炒出来才嫩"},
    {"type":"recipe","name":"番茄牛腩","meal":"午餐/晚餐","time":90,"diff":"中等","tags":["增肌","高蛋白","炖煮","暖心"],"ingredients":["牛腩400g","番茄3个","洋葱半个","姜","八角","生抽","番茄酱","料酒"],"steps":["牛腩切块焯水去血沫，番茄去皮切块","热油炒洋葱和姜片出香","下牛腩翻炒，加料酒、生抽、八角","加番茄和番茄酱，倒开水没过食材","小火炖1小时至牛腩软烂，加盐调味收汁"],"nutrition":{"calories":520,"protein_g":48,"fat_g":28,"carbs_g":18},"tips":"一次多做些可以分装冷冻，工作日热一下就能吃"},
    {"type":"recipe","name":"三文鱼配芦笋","meal":"午餐/晚餐","time":20,"diff":"简单","tags":["增肌","高蛋白","Omega3"],"ingredients":["三文鱼200g","芦笋150g","柠檬","橄榄油","盐","黑胡椒","蒜粉"],"steps":["三文鱼用盐、黑胡椒、蒜粉腌10分钟","芦笋去老根","平底锅热油，三文鱼每面煎3-4分钟","同时芦笋煎至表面微焦","出锅挤柠檬汁"],"nutrition":{"calories":420,"protein_g":40,"fat_g":26,"carbs_g":5},"tips":"三文鱼不要煎全熟，中间微微粉红最嫩"},
    {"type":"recipe","name":"鸡蛋豆腐煲","meal":"午餐/晚餐","time":25,"diff":"简单","tags":["增肌","高蛋白","素食可选"],"ingredients":["老豆腐300g","鸡蛋3个","葱","生抽","蚝油","水淀粉","橄榄油10g"],"steps":["豆腐切厚片，两面煎至金黄","鸡蛋打散加少许盐","锅里余油倒入蛋液，半凝固时加豆腐","轻推不要翻炒，鸡蛋定型后淋生抽+蚝油+水","小火焖3分钟，水淀粉勾薄芡撒葱"],"nutrition":{"calories":400,"protein_g":35,"fat_g":24,"carbs_g":10},"tips":"豆腐煎过再炖不容易碎，口感也更好"},
    {"type":"recipe","name":"土豆炖鸡块","meal":"午餐/晚餐","time":40,"diff":"简单","tags":["增肌","碳水+蛋白质","饱腹"],"ingredients":["鸡腿肉300g","土豆2个","胡萝卜1根","姜片","生抽","老抽","料酒","八角"],"steps":["鸡腿肉切块焯水，土豆胡萝卜切滚刀块","热油炒香姜片八角，下鸡块炒至微黄","加料酒、生抽、老抽翻炒上色","加开水没过鸡肉，炖15分钟","加土豆胡萝卜再炖15分钟，收汁出锅"],"nutrition":{"calories":480,"protein_g":38,"fat_g":18,"carbs_g":45},"tips":"鸡腿肉比鸡胸肉多汁，炖煮不容易柴"},
    {"type":"recipe","name":"虾仁滑蛋","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["增肌","高蛋白","快手"],"ingredients":["虾仁200g","鸡蛋3个","料酒","盐","白胡椒粉","葱花","牛奶1勺"],"steps":["虾仁加料酒、盐腌5分钟，鸡蛋打散加牛奶和盐搅匀","热油炒虾仁至变色盛出","锅里补油转小火，倒入蛋液","蛋液半凝固时加入虾仁轻推","蛋液八成熟关火撒葱花，余温焖熟"],"nutrition":{"calories":310,"protein_g":42,"fat_g":15,"carbs_g":3},"tips":"加牛奶让蛋更嫩滑，小火慢推是嫩的关键"},
    {"type":"recipe","name":"孜然牛肉","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["增肌","高蛋白","快手","下饭"],"ingredients":["牛里脊250g","洋葱半个","孜然粉","辣椒粉","生抽","料酒","淀粉","盐"],"steps":["牛肉逆纹切薄片，加生抽+料酒+淀粉腌15分钟","洋葱切丝","热锅热油，大火爆炒牛肉至变色盛出","余油炒洋葱至透明，倒回牛肉","加孜然粉+辣椒粉+盐翻炒均匀出锅"],"nutrition":{"calories":350,"protein_g":48,"fat_g":15,"carbs_g":8},"tips":"全程大火快炒，牛肉在锅里不能超过3分钟"},

    # ── 家常菜 ──
    {"type":"recipe","name":"番茄炒蛋","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["家常","快手","入门"],"ingredients":["鸡蛋3个","番茄2个","葱花","盐","糖少许","油10g"],"steps":["鸡蛋打散加盐搅匀，番茄切块","热锅倒油，大火炒蛋至凝固盛出","余油炒番茄至出汁变软","倒回鸡蛋翻炒均匀","加少许糖提鲜，撒葱花出锅"],"nutrition":{"calories":250,"protein_g":15,"fat_g":16,"carbs_g":10},"tips":"番茄炒出汁再放蛋，每口都能裹上番茄汁"},
    {"type":"recipe","name":"宫保鸡丁","meal":"午餐/晚餐","time":20,"diff":"中等","tags":["家常","川菜","下饭"],"ingredients":["鸡胸肉250g","花生米50g","黄瓜半根","干辣椒","花椒","葱姜蒜","生抽","醋","糖","淀粉","料酒"],"steps":["鸡肉切丁加料酒+生抽+淀粉腌15分钟","调碗汁：生抽+醋+糖+淀粉+水搅匀","花生米小火炒香，黄瓜切丁","热油爆香干辣椒花椒葱姜蒜","下鸡丁炒变色，加黄瓜丁翻炒","淋入碗汁大火收汁，加花生米翻匀出锅"],"nutrition":{"calories":420,"protein_g":42,"fat_g":20,"carbs_g":18},"tips":"碗汁提前调好，这就是宫保的'荔枝味'"},
    {"type":"recipe","name":"麻婆豆腐","meal":"午餐/晚餐","time":15,"diff":"中等","tags":["家常","川菜","下饭","麻辣"],"ingredients":["嫩豆腐1盒","猪肉末100g","郫县豆瓣酱","花椒粉","蒜末","姜末","葱花","生抽","水淀粉"],"steps":["豆腐切1.5cm方块，盐水焯1分钟捞出","热油炒肉末至酥香","加豆瓣酱小火炒出红油","加蒜姜末炒香，加半碗水烧开","轻放豆腐推匀，小火煮3分钟入味","水淀粉勾芡，撒花椒粉和葱花"],"nutrition":{"calories":300,"protein_g":25,"fat_g":18,"carbs_g":12},"tips":"豆腐焯盐水不容易碎，推的时候用锅铲背面"},
    {"type":"recipe","name":"可乐鸡翅","meal":"午餐/晚餐","time":30,"diff":"简单","tags":["家常","入门","宴客"],"ingredients":["鸡翅中8个","可乐1罐","生抽","老抽","姜片","料酒"],"steps":["鸡翅正反面各划两刀，冷水下锅加料酒姜片焯水捞出","热锅少许油，鸡翅煎至两面微黄","加生抽1勺+老抽半勺上色","倒可乐没过鸡翅，大火烧开转小火","炖15分钟至汤汁浓稠裹住鸡翅即可"],"nutrition":{"calories":380,"protein_g":30,"fat_g":18,"carbs_g":25},"tips":"最后大火收汁时要不停翻动，防止糊锅"},
    {"type":"recipe","name":"地三鲜","meal":"午餐/晚餐","time":25,"diff":"中等","tags":["家常","东北菜","素菜"],"ingredients":["土豆2个","茄子1个","青椒1个","蒜","生抽","老抽","糖","淀粉","油"],"steps":["土豆茄子青椒切滚刀块，蒜切末","土豆块炸至金黄捞出，茄子裹淀粉炸至表面焦脆","青椒过油10秒捞出","留底油炒香蒜末，加生抽+老抽+糖+水烧开","水淀粉勾芡，下所有食材快速翻炒裹汁"],"nutrition":{"calories":350,"protein_g":6,"fat_g":22,"carbs_g":38},"tips":"茄子裹薄淀粉再炸，吸油少口感好"},
    {"type":"recipe","name":"酸辣土豆丝","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["家常","快手","素菜","酸辣"],"ingredients":["土豆2个","干辣椒","花椒","醋","盐","葱花","蒜"],"steps":["土豆切细丝泡水去淀粉，换水2次","热锅倒油，爆香干辣椒花椒蒜末","沥干土豆丝大火快炒2分钟","沿锅边淋醋，加盐翻炒均匀","出锅前撒葱花"],"nutrition":{"calories":150,"protein_g":4,"fat_g":6,"carbs_g":28},"tips":"泡水去淀粉是关键，炒出来才脆不粘锅"},
    {"type":"recipe","name":"鱼香肉丝","meal":"午餐/晚餐","time":20,"diff":"中等","tags":["家常","川菜","下饭","经典"],"ingredients":["猪里脊200g","木耳","胡萝卜","青椒","郫县豆瓣酱","葱姜蒜","生抽","醋","糖","淀粉","料酒"],"steps":["肉切丝加料酒+生抽+淀粉腌15分钟","木耳胡萝卜青椒切丝","调鱼香汁：生抽2+醋2+糖1.5+淀粉+水搅匀","热油滑炒肉丝至变色盛出","炒豆瓣酱出红油加葱姜蒜末","下所有蔬菜翻炒，倒回肉丝","淋鱼香汁大火翻炒均匀出锅"],"nutrition":{"calories":350,"protein_g":28,"fat_g":18,"carbs_g":20},"tips":"鱼香汁的黄金比例：生抽2醋2糖1.5"},
    {"type":"recipe","name":"蒜蓉粉丝蒸虾","meal":"午餐/晚餐","time":20,"diff":"简单","tags":["家常","宴客","海鲜"],"ingredients":["大虾12只","粉丝1把","蒜1头","葱花","生抽","蚝油","糖","油"],"steps":["粉丝温水泡软剪段铺盘底","虾去虾线开背，铺在粉丝上","蒜切末，热油炸一半至金黄（金银蒜）","混合生蒜和炸蒜，加生抽+蚝油+糖拌匀","蒜蓉铺在虾上，水开蒸8分钟","出锅撒葱花淋热油"],"nutrition":{"calories":280,"protein_g":30,"fat_g":12,"carbs_g":18},"tips":"金银蒜是灵魂——炸蒜增香，生蒜提鲜"},
    {"type":"recipe","name":"红烧排骨","meal":"午餐/晚餐","time":60,"diff":"中等","tags":["家常","硬菜","宴客"],"ingredients":["排骨500g","冰糖","生抽","老抽","料酒","姜片","八角","桂皮","香叶"],"steps":["排骨冷水下锅加料酒姜片焯水捞出","小火炒冰糖至枣红色（糖色）","下排骨快速翻炒上色","加生抽+老抽+料酒+八角+桂皮+香叶","加开水没过排骨，大火烧开转小火炖40分钟","大火收汁至浓稠"],"nutrition":{"calories":520,"protein_g":35,"fat_g":38,"carbs_g":12},"tips":"炒糖色小火慢搅，枣红色立刻下排骨，过火会苦"},
    {"type":"recipe","name":"拍黄瓜","meal":"午餐/晚餐","time":5,"diff":"简单","tags":["快手","凉拌","素菜","夏季"],"ingredients":["黄瓜2根","蒜3瓣","生抽","醋","香油","盐","糖","辣椒油"],"steps":["黄瓜洗净用刀拍裂，切段","蒜捣成蒜泥","碗中调汁：生抽+醋+盐+糖+香油+辣椒油+蒜泥","倒入黄瓜拌匀即可"],"nutrition":{"calories":50,"protein_g":2,"fat_g":3,"carbs_g":6},"tips":"黄瓜放保鲜袋里用擀面杖拍，不溅汁"},

    # ── 早餐 ──
    {"type":"recipe","name":"牛油果鸡蛋吐司","meal":"早餐","time":10,"diff":"简单","tags":["早餐","快手","健康脂肪"],"ingredients":["全麦吐司2片","牛油果1个","鸡蛋1个","盐","黑胡椒","柠檬汁"],"steps":["牛油果对半切开去核，挖出果肉捣成泥","加柠檬汁+盐+黑胡椒拌匀","鸡蛋煎成太阳蛋","吐司烤至微脆","吐司上抹牛油果泥，放上煎蛋即可"],"nutrition":{"calories":350,"protein_g":14,"fat_g":20,"carbs_g":30},"tips":"牛油果加柠檬汁可以防止氧化变黑"},
    {"type":"recipe","name":"燕麦香蕉碗","meal":"早餐","time":5,"diff":"简单","tags":["早餐","快手","高纤维"],"ingredients":["即食燕麦50g","牛奶200ml","香蕉1根","坚果碎","蜂蜜可选"],"steps":["燕麦加牛奶微波炉高火2分钟","香蕉切片摆上","撒坚果碎","喜欢甜的淋少许蜂蜜"],"nutrition":{"calories":320,"protein_g":12,"fat_g":10,"carbs_g":50},"tips":"隔夜燕麦：前一晚放冰箱，早上拿出来直接吃"},
    {"type":"recipe","name":"虾仁蔬菜粥","meal":"早餐","time":30,"diff":"简单","tags":["早餐","暖胃","高蛋白"],"ingredients":["大米100g","虾仁100g","玉米粒","胡萝卜丁","姜丝","盐","白胡椒粉","葱花"],"steps":["大米淘洗后泡30分钟","米加水大火煮开转小火熬20分钟至米开花","加玉米粒胡萝卜丁煮5分钟","下虾仁和姜丝煮2分钟至虾仁变红","加盐白胡椒粉调味撒葱花"],"nutrition":{"calories":380,"protein_g":28,"fat_g":3,"carbs_g":62},"tips":"前一晚米泡好，早上只需要20分钟"},
    {"type":"recipe","name":"菠菜鸡蛋饼","meal":"早餐","time":10,"diff":"简单","tags":["早餐","快手","高蛋白"],"ingredients":["鸡蛋2个","菠菜100g","面粉30g","盐","水少量","油"],"steps":["菠菜焯水切碎","鸡蛋+面粉+水+盐搅成面糊","加入菠菜碎拌匀","平底锅刷油，倒一勺面糊摊薄","两面煎至金黄即可"],"nutrition":{"calories":220,"protein_g":18,"fat_g":10,"carbs_g":18},"tips":"面糊调到能流动的稠度，太厚饼不软"},
    {"type":"recipe","name":"紫薯牛奶","meal":"早餐","time":20,"diff":"简单","tags":["早餐","饮品","高纤维"],"ingredients":["紫薯1个","牛奶300ml","蜂蜜可选"],"steps":["紫薯去皮切块蒸熟（约15分钟）","紫薯和牛奶一起放入搅拌机","搅打至顺滑无颗粒","喜欢甜的加少许蜂蜜"],"nutrition":{"calories":200,"protein_g":10,"fat_g":6,"carbs_g":30},"tips":"紫薯可以用红薯、南瓜替换，各有风味"},

    # ── 汤羹 ──
    {"type":"recipe","name":"玉米排骨汤","meal":"午餐/晚餐","time":90,"diff":"简单","tags":["汤羹","家常","滋补"],"ingredients":["排骨400g","玉米2根","胡萝卜1根","姜片","料酒","盐","枸杞"],"steps":["排骨冷水下锅加料酒焯水捞出","玉米切段，胡萝卜切滚刀块","排骨+玉米+胡萝卜+姜片入锅加足水","大火烧开转小火炖1小时","加盐和枸杞再炖5分钟"],"nutrition":{"calories":380,"protein_g":30,"fat_g":22,"carbs_g":20},"tips":"煲汤水要一次加足，中途加水破坏味道"},
    {"type":"recipe","name":"番茄蛋花汤","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["汤羹","快手","入门"],"ingredients":["番茄2个","鸡蛋1个","葱花","盐","香油","淀粉少许"],"steps":["番茄去皮切丁","热油炒番茄出汁，加水烧开","水淀粉勾薄芡","转小火淋入蛋液（筷子搅动形成蛋花）","加盐、香油、葱花出锅"],"nutrition":{"calories":100,"protein_g":8,"fat_g":5,"carbs_g":10},"tips":"淋蛋花时汤要微开，筷子在汤里画圈，蛋花才飘逸"},
    {"type":"recipe","name":"酸辣汤","meal":"午餐/晚餐","time":20,"diff":"简单","tags":["汤羹","酸辣","暖身"],"ingredients":["豆腐100g","木耳","鸡蛋1个","金针菇","白胡椒粉","醋","生抽","水淀粉","香油","葱花"],"steps":["豆腐木耳金针菇切丝","高汤或水烧开，下豆腐木耳金针菇煮3分钟","加生抽+白胡椒粉+醋调味","水淀粉勾芡至浓稠","淋蛋花，加香油和葱花出锅"],"nutrition":{"calories":120,"protein_g":12,"fat_g":5,"carbs_g":10},"tips":"白胡椒粉和醋的量要够，酸辣味才正"},
    {"type":"recipe","name":"红枣枸杞乌鸡汤","meal":"午餐/晚餐","time":120,"diff":"简单","tags":["汤羹","滋补","女性"],"ingredients":["乌鸡半只","红枣8颗","枸杞10g","当归2片","黄芪5g","姜片","盐","料酒"],"steps":["乌鸡斩块焯水去血沫","所有药材冲洗一下","乌鸡+药材+姜片+料酒入锅加足水","大火烧开转小火慢炖1.5小时","加盐和枸杞再炖10分钟"],"nutrition":{"calories":350,"protein_g":42,"fat_g":12,"carbs_g":15},"tips":"枸杞最后10分钟放，久煮会烂发酸"},

    # ── 更多减脂/健身餐 ──
    {"type":"recipe","name":"鸡胸肉丸子","meal":"午餐/晚餐","time":30,"diff":"中等","tags":["减脂","高蛋白","备餐"],"ingredients":["鸡胸肉500g","胡萝卜半根","香菇5朵","姜末","料酒","盐","白胡椒粉","蛋清1个"],"steps":["鸡胸肉剁成泥，胡萝卜香菇切碎末","所有食材混合加调料顺一个方向搅上劲","手蘸水搓成丸子","水开后转小火下丸子煮至浮起","捞出放凉可冷冻保存"],"nutrition":{"calories":320,"protein_g":55,"fat_g":7,"carbs_g":8},"tips":"周末做一批冻起来，工作日随吃随取，煮汤炒菜都行"},
    {"type":"recipe","name":"泡菜豆腐锅","meal":"午餐/晚餐","time":20,"diff":"简单","tags":["减脂","低卡","韩式"],"ingredients":["韩式泡菜100g","嫩豆腐200g","金针菇","西葫芦","洋葱","韩式辣酱","鸡蛋1个","葱"],"steps":["洋葱切丝，西葫芦切片","热锅少许油炒洋葱和泡菜出香","加水烧开，加1勺韩式辣酱","下西葫芦和金针菇煮3分钟","下豆腐煮2分钟，打一个蛋","蛋半熟关火撒葱花"],"nutrition":{"calories":220,"protein_g":20,"fat_g":10,"carbs_g":16},"tips":"泡菜发酵产生的乳酸菌对肠道有好处"},
    {"type":"recipe","name":"杂粮饭","meal":"主食","time":40,"diff":"简单","tags":["减脂","主食","高纤维"],"ingredients":["大米100g","糙米50g","燕麦米30g","小米20g"],"steps":["所有米淘洗干净","加2倍水浸泡30分钟","电饭煲按杂粮饭模式（没有就正常煮）","煮好后焖10分钟再开盖拌匀"],"nutrition":{"calories":700,"protein_g":18,"fat_g":5,"carbs_g":148},"tips":"一次煮一锅分装冷冻，每顿热一小碗，控量方便"},
    {"type":"recipe","name":"低脂酸奶杯","meal":"加餐/早餐","time":3,"diff":"简单","tags":["减脂","加餐","高蛋白","甜点"],"ingredients":["无糖酸奶200g","混合莓果","燕麦片2勺","奇亚籽1勺"],"steps":["杯中先铺一层酸奶","加燕麦片和奇亚籽","再加一层酸奶","顶部铺上莓果","可以马上吃，也可以冷藏过夜"],"nutrition":{"calories":220,"protein_g":14,"fat_g":6,"carbs_g":28},"tips":"买酸奶看配料表，选只有'生牛乳+菌种'的"},

    # ── 更多增肌/高蛋白 ──
    {"type":"recipe","name":"黑椒牛排","meal":"午餐/晚餐","time":15,"diff":"中等","tags":["增肌","高蛋白","宴客"],"ingredients":["西冷牛排200g","黄油10g","蒜2瓣","迷迭香可选","盐","黑胡椒"],"steps":["牛排提前30分钟从冰箱取出回温，用厨房纸吸干","两面撒盐和黑胡椒按摩一下","大火热锅至冒烟，不放油直接下牛排","每面煎1.5分钟（5分熟）","转小火加黄油、蒜、迷迭香，用勺子浇黄油汁淋牛排30秒","出锅醒肉5分钟再切"],"nutrition":{"calories":420,"protein_g":42,"fat_g":28,"carbs_g":1},"tips":"醒肉5分钟让汁水重新分布，切开不会流血水"},
    {"type":"recipe","name":"卤牛肉","meal":"午餐/晚餐","time":90,"diff":"中等","tags":["增肌","高蛋白","备餐","凉菜"],"ingredients":["牛腱子500g","生抽","老抽","料酒","冰糖","八角","桂皮","香叶","花椒","姜","葱段"],"steps":["牛腱子清水泡1小时去血水","冷水下锅加姜料酒焯水10分钟","另起锅加足水+所有调料（生抽3老抽1料酒2）","大火烧开转小火卤1小时","筷子能轻松扎透即可","关火泡在卤汁里放凉，冷藏后切片更好"],"nutrition":{"calories":550,"protein_g":65,"fat_g":25,"carbs_g":8},"tips":"冷藏过夜再切，薄而不散，纹理漂亮"},
    {"type":"recipe","name":"山药排骨汤","meal":"午餐/晚餐","time":60,"diff":"简单","tags":["增肌","汤羹","滋补"],"ingredients":["排骨400g","铁棍山药300g","胡萝卜","姜片","料酒","盐","枸杞"],"steps":["排骨焯水洗净，山药去皮切段（戴手套！）","排骨+姜片+料酒+水大火烧开","转小火炖30分钟","加山药和胡萝卜再炖20分钟","加盐和枸杞，5分钟后出锅"],"nutrition":{"calories":450,"protein_g":32,"fat_g":24,"carbs_g":30},"tips":"山药黏液会让皮肤痒，一定要戴手套削皮"},
    {"type":"recipe","name":"口蘑炒牛肉","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["增肌","高蛋白","快手"],"ingredients":["牛里脊200g","口蘑200g","蒜","生抽","蚝油","黑胡椒","淀粉","料酒"],"steps":["牛肉逆纹切片加料酒+生抽+淀粉腌15分钟","口蘑切片，蒜切末","牛肉大火滑炒至变色盛出","余油炒香蒜末，下口蘑炒至出汁变软","倒回牛肉，加蚝油+黑胡椒翻炒均匀"],"nutrition":{"calories":330,"protein_g":42,"fat_g":14,"carbs_g":10},"tips":"口蘑不要洗太久，用厨房纸擦干净即可"},

    # ── 更多家常菜 ──
    {"type":"recipe","name":"蒜蓉西兰花","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["家常","快手","素菜","减脂"],"ingredients":["西兰花1颗","蒜5瓣","盐","蚝油","油5g"],"steps":["西兰花掰小朵，淡盐水泡10分钟","开水加盐和油焯西兰花1分钟捞出","蒜切末","热锅凉油小火炒蒜末至微黄","下西兰花大火翻炒，加蚝油和盐炒匀"],"nutrition":{"calories":80,"protein_g":6,"fat_g":5,"carbs_g":10},"tips":"西兰花焯水冰镇一下，颜色翠绿口感脆"},
    {"type":"recipe","name":"手撕包菜","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["家常","快手","下饭"],"ingredients":["圆白菜半个","干辣椒","花椒","蒜","生抽","醋","糖","盐","油10g"],"steps":["包菜手撕成块（不要用刀切），洗净沥干","热锅倒油爆香干辣椒花椒蒜末","下包菜大火爆炒至变软","沿锅边淋醋和生抽","加盐和少许糖翻炒出锅"],"nutrition":{"calories":100,"protein_g":3,"fat_g":6,"carbs_g":12},"tips":"手撕+大火爆炒，口感比刀切的好很多"},
    {"type":"recipe","name":"肉末茄子","meal":"午餐/晚餐","time":20,"diff":"中等","tags":["家常","下饭"],"ingredients":["茄子2个","猪肉末100g","蒜末","姜末","豆瓣酱","生抽","糖","淀粉","葱花"],"steps":["茄子切条加盐腌10分钟挤出水（这样不吸油）","肉末加料酒生抽腌一下","热油炒肉末至变色加豆瓣酱炒出红油","加姜蒜末炒香","下茄子翻炒，加少许水焖3分钟","加生抽糖调味，水淀粉勾芡撒葱花"],"nutrition":{"calories":250,"protein_g":18,"fat_g":16,"carbs_g":14},"tips":"茄子加盐腌出水再炒，告别油腻"},
    {"type":"recipe","name":"红烧鸡块","meal":"午餐/晚餐","time":40,"diff":"简单","tags":["家常","下饭","硬菜"],"ingredients":["鸡腿3个","土豆2个","干香菇5朵","姜片","八角","生抽","老抽","冰糖","料酒"],"steps":["鸡腿剁块焯水，土豆切块，香菇泡发","小火炒冰糖至枣红色","下鸡块翻炒上色","加姜片八角料酒生抽老抽","加香菇和泡香菇的水","炖20分钟后加土豆再炖10分钟，收汁"],"nutrition":{"calories":420,"protein_g":35,"fat_g":18,"carbs_g":30},"tips":"泡香菇的水不要倒掉，是天然的鲜味剂"},
    {"type":"recipe","name":"韭菜炒鸡蛋","meal":"午餐/晚餐","time":8,"diff":"简单","tags":["家常","快手","入门"],"ingredients":["韭菜200g","鸡蛋3个","盐","油10g"],"steps":["韭菜洗净切段（叶和茎分开）","鸡蛋打散加盐搅匀","热油先炒鸡蛋至凝固盛出","余油炒韭菜茎30秒","加韭菜叶和鸡蛋大火快炒30秒出锅"],"nutrition":{"calories":220,"protein_g":16,"fat_g":14,"carbs_g":6},"tips":"韭菜不能久炒，出水就老了，全程大火快炒"},
    {"type":"recipe","name":"虎皮青椒","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["家常","素菜","下饭","快手"],"ingredients":["青椒4个","蒜末","生抽","醋","糖","盐","油"],"steps":["青椒去蒂去籽拍扁","碗汁：生抽+醋+糖+盐+水搅匀","热锅不放油，青椒两面煎出虎皮","推到一边加油和蒜末爆香","淋碗汁翻炒均匀出锅"],"nutrition":{"calories":60,"protein_g":2,"fat_g":4,"carbs_g":8},"tips":"干煸青椒时用铲子压一压，虎皮更快出来"},

    # ── 更多早餐/轻食 ──
    {"type":"recipe","name":"鲜虾肠粉","meal":"早餐","time":20,"diff":"中等","tags":["早餐","粤式","高蛋白"],"ingredients":["粘米粉100g","澄粉30g","水250g","虾仁","鸡蛋","生抽","油"],"steps":["粘米粉+澄粉+水搅成米浆","平盘刷油倒薄薄一层米浆，放虾仁","大火蒸2分钟至起泡","用刮板卷起装盘","淋生抽和熟油"],"nutrition":{"calories":300,"protein_g":22,"fat_g":6,"carbs_g":42},"tips":"米浆要薄，厚了口感不好，多做几次就掌握了"},
    {"type":"recipe","name":"隔夜燕麦杯","meal":"早餐","time":5,"diff":"简单","tags":["早餐","备餐","快手","减脂"],"ingredients":["燕麦50g","牛奶150ml","酸奶50g","奇亚籽1勺","蜂蜜","水果"],"steps":["密封罐里燕麦+牛奶+酸奶搅匀","加奇亚籽拌匀","加盖放冰箱过夜","早上拿出来加蜂蜜搅匀","加水果（香蕉/莓果/芒果）开吃"],"nutrition":{"calories":300,"protein_g":14,"fat_g":8,"carbs_g":46},"tips":"基础版外可以加可可粉、抹茶粉、花生酱变口味"},
    {"type":"recipe","name":"虾饺","meal":"早餐","time":30,"diff":"困难","tags":["早餐","粤式","宴客"],"ingredients":["澄粉100g","玉米淀粉30g","开水","虾仁200g","猪肉末50g","笋丁","姜末","盐","糖","白胡椒粉","香油"],"steps":["虾仁一半剁成泥一半切丁，加猪肉末+笋丁+调料搅成馅","澄粉+玉米淀粉混合，加滚开水烫面搅成团","面团揉光滑，分成小剂子擀薄皮","包入虾馅捏成月牙形","水开上锅大火蒸6分钟"],"nutrition":{"calories":280,"protein_g":25,"fat_g":8,"carbs_g":30},"tips":"澄粉必须用100℃滚水烫面，面团才够透明有弹性"},

    # ── 减脂餐 第二批 ──
    {"type":"recipe","name":"金枪鱼沙拉","meal":"午餐","time":10,"diff":"简单","tags":["减脂","高蛋白","沙拉","快手"],"ingredients":["水浸金枪鱼罐头1罐","生菜","小番茄","玉米粒","黄瓜","橄榄油","柠檬汁","黑胡椒"],"steps":["金枪鱼沥干水分捣散","生菜撕碎，小番茄对半切，黄瓜切片","玉米粒焯水沥干","所有食材混合，淋橄榄油+柠檬汁+黑胡椒"],"nutrition":{"calories":260,"protein_g":30,"fat_g":10,"carbs_g":14},"tips":"选水浸金枪鱼不要油浸的，热量差一倍"},
    {"type":"recipe","name":"荞麦面拌鸡丝","meal":"午餐","time":20,"diff":"简单","tags":["减脂","低GI","主食"],"ingredients":["荞麦面80g","鸡胸肉150g","黄瓜丝","胡萝卜丝","芝麻酱1勺","生抽","醋","蒜末","辣椒油"],"steps":["鸡胸肉煮熟撕成丝","荞麦面煮4分钟过凉水沥干","芝麻酱+生抽+醋+蒜末调成酱汁","面+鸡丝+蔬菜码好淋酱汁拌匀"],"nutrition":{"calories":380,"protein_g":35,"fat_g":12,"carbs_g":38},"tips":"荞麦面GI值低，适合减脂期做主食"},
    {"type":"recipe","name":"巴沙鱼番茄煲","meal":"午餐/晚餐","time":25,"diff":"简单","tags":["减脂","高蛋白","低卡"],"ingredients":["巴沙鱼柳200g","番茄2个","金针菇","豆腐100g","姜丝","盐","白胡椒粉","料酒"],"steps":["鱼柳切块加料酒姜丝腌10分钟","番茄去皮炒出汁加水烧开","下金针菇和豆腐煮3分钟","滑入鱼块煮2分钟至变白","加盐和白胡椒粉调味"],"nutrition":{"calories":220,"protein_g":32,"fat_g":6,"carbs_g":12},"tips":"巴沙鱼非常嫩不要久煮，变色即可"},
    {"type":"recipe","name":"香菇青菜","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["减脂","素菜","快手","低卡"],"ingredients":["上海青300g","鲜香菇6朵","蒜","蚝油","盐","油5g"],"steps":["青菜对半切开洗净，香菇切片","水开加盐和油，青菜焯水30秒捞出摆盘","热油炒香蒜末和香菇","加蚝油和少许水煮至香菇变软","连汁浇在青菜上"],"nutrition":{"calories":70,"protein_g":4,"fat_g":5,"carbs_g":8},"tips":"青菜焯水时加油和盐，颜色碧绿不发黄"},
    {"type":"recipe","name":"裙带菜豆腐汤","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["减脂","低卡","高钙","快手"],"ingredients":["干裙带菜5g","嫩豆腐150g","味噌可选","葱花","盐"],"steps":["裙带菜泡发5分钟捞出","水烧开下裙带菜和豆腐丁","煮3分钟加盐或味噌调味","撒葱花出锅"],"nutrition":{"calories":60,"protein_g":8,"fat_g":2,"carbs_g":4},"tips":"裙带菜泡发后会变大5倍，别放多了"},
    {"type":"recipe","name":"芹菜炒香干","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["减脂","高纤维","快手"],"ingredients":["芹菜200g","香干150g","蒜","生抽","盐","干辣椒可选","油5g"],"steps":["芹菜切段，香干切条","热油爆香蒜和干辣椒","下香干炒1分钟至表面微焦","加芹菜大火翻炒2分钟","生抽和盐调味出锅"],"nutrition":{"calories":180,"protein_g":16,"fat_g":8,"carbs_g":10},"tips":"芹菜大火快炒保持脆度，炒太久出水就老了"},
    {"type":"recipe","name":"白灼虾","meal":"午餐/晚餐","time":8,"diff":"简单","tags":["减脂","高蛋白","快手","海鲜"],"ingredients":["活虾300g","姜片","葱段","料酒","蘸料：生抽+醋+姜末+小米辣"],"steps":["虾去虾线洗净","水加姜片葱段料酒烧开","虾入锅煮2-3分钟变红捞出","过冰水（口感更Q弹）","调蘸料搭配吃"],"nutrition":{"calories":180,"protein_g":36,"fat_g":2,"carbs_g":3},"tips":"白灼是最能保留虾鲜甜的做法，蘸料是灵魂"},
    {"type":"recipe","name":"蒸茄子","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["减脂","素菜","低卡","夏季"],"ingredients":["长茄子2个","蒜末","生抽","醋","香油","辣椒油","葱花"],"steps":["茄子洗净整根上锅蒸10分钟","取出放凉手撕成条","碗中蒜末+生抽+醋+香油+辣椒油调汁","浇在茄子上撒葱花"],"nutrition":{"calories":70,"protein_g":2,"fat_g":3,"carbs_g":10},"tips":"蒸的茄子比炒的健康太多，还不吸油"},

    # ── 增肌餐 第二批 ──
    {"type":"recipe","name":"煎牛排配红薯","meal":"午餐/晚餐","time":25,"diff":"中等","tags":["增肌","高蛋白","碳水"],"ingredients":["牛排200g","红薯1个","芦笋","黄油10g","迷迭香","盐","黑胡椒"],"steps":["红薯切块烤箱200度烤20分钟（或蒸熟）","牛排回温30分钟，吸干表面水分","大火热锅不放油，牛排每面煎2分钟","转小火加黄油迷迭香淋油30秒","醒肉5分钟切开，搭配红薯和煎芦笋"],"nutrition":{"calories":520,"protein_g":44,"fat_g":24,"carbs_g":38},"tips":"红薯是增肌期优质碳水，比白米饭营养密度高"},
    {"type":"recipe","name":"鸡肉蘑菇意面","meal":"午餐","time":25,"diff":"简单","tags":["增肌","碳水","西式"],"ingredients":["意大利面80g","鸡胸肉150g","白蘑菇100g","蒜","淡奶油30ml","帕玛森芝士","盐","黑胡椒","橄榄油"],"steps":["意面煮至弹牙（包装时间-1分钟）捞出","鸡胸肉切片加盐黑胡椒腌","热油煎鸡肉至金黄盛出","余油炒蒜末和蘑菇片至出汤","加淡奶油和少许意面水搅成酱汁","倒回意面和鸡肉拌匀，撒芝士"],"nutrition":{"calories":480,"protein_g":38,"fat_g":16,"carbs_g":48},"tips":"留一碗煮面水，含淀粉能让酱汁更浓稠挂面"},
    {"type":"recipe","name":"烤鸡腿","meal":"午餐/晚餐","time":40,"diff":"简单","tags":["增肌","高蛋白","烤箱"],"ingredients":["鸡全腿2个","蒜","迷迭香","柠檬","橄榄油","盐","黑胡椒","辣椒粉"],"steps":["鸡腿用厨房纸吸干水分","蒜末+橄榄油+盐+黑胡椒+辣椒粉+迷迭香混合抹匀鸡腿","柠檬切片垫鸡腿下面","烤箱200度预热，烤35分钟至皮金黄","出炉静置5分钟再吃"],"nutrition":{"calories":420,"protein_g":38,"fat_g":26,"carbs_g":3},"tips":"烤之前鸡皮要完全擦干，才能烤出脆皮效果"},
    {"type":"recipe","name":"虾仁豆腐蒸蛋","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["增肌","高蛋白","嫩滑"],"ingredients":["鸡蛋2个","嫩豆腐100g","虾仁6只","温水","生抽","香油","葱花"],"steps":["鸡蛋打散加1.5倍温水搅匀过筛","豆腐切小块放入蛋液中","盖上保鲜膜扎孔，水开蒸8分钟","摆上虾仁再蒸3分钟","出锅淋生抽香油撒葱花"],"nutrition":{"calories":230,"protein_g":28,"fat_g":12,"carbs_g":4},"tips":"蛋液过筛去泡沫，蒸出来像布丁一样嫩"},

    # ── 家常菜 第二批 ──
    {"type":"recipe","name":"红烧肉","meal":"午餐/晚餐","time":80,"diff":"中等","tags":["家常","硬菜","宴客","经典"],"ingredients":["五花肉500g","冰糖30g","生抽","老抽","料酒","姜片","八角","桂皮","香叶","葱段"],"steps":["五花肉切3cm方块，冷水下锅焯水捞出","小火炒冰糖至枣红色（糖色）","下五花肉快速翻裹糖色","加生抽+老抽+料酒+姜片+八角+桂皮+香叶","加开水没过肉，大火烧开转小火炖1小时","大火收汁至浓稠红亮"],"nutrition":{"calories":650,"protein_g":25,"fat_g":55,"carbs_g":15},"tips":"炒糖色是灵魂，宁浅勿深，过了会苦"},
    {"type":"recipe","name":"回锅肉","meal":"午餐/晚餐","time":25,"diff":"中等","tags":["家常","川菜","下饭","经典"],"ingredients":["二刀肉（猪后腿）300g","蒜苗","豆瓣酱","豆豉","姜片","甜面酱","生抽","料酒","白糖"],"steps":["整块肉冷水下锅加姜料酒煮20分钟至筷子能扎透","捞出放凉切薄片（越薄越好）","热锅少油下肉片炒至卷曲出油（灯盏窝）","加豆瓣酱豆豉炒出红油","加甜面酱+生抽+糖翻炒","下蒜苗白部分炒几下，再下蒜苗叶翻炒出锅"],"nutrition":{"calories":420,"protein_g":28,"fat_g":32,"carbs_g":8},"tips":"肉煮好后放凉再切，热切会碎；片要薄才能卷成灯盏窝"},
    {"type":"recipe","name":"糖醋里脊","meal":"午餐/晚餐","time":25,"diff":"中等","tags":["家常","酸甜","宴客","经典"],"ingredients":["猪里脊300g","鸡蛋1个","面粉","淀粉","番茄酱","白醋","糖","生抽","盐","料酒"],"steps":["里脊切条加盐+料酒+鸡蛋腌15分钟","面粉+淀粉1:1裹匀肉条","六成热油炸至淡黄捞出","油升温复炸至金黄酥脆","另起锅：番茄酱+糖+白醋+生抽+水煮至冒泡","水淀粉勾芡至浓稠","下炸好的肉条快速翻匀出锅"],"nutrition":{"calories":480,"protein_g":32,"fat_g":22,"carbs_g":40},"tips":"复炸是酥脆的关键，第一次炸熟第二次炸脆"},
    {"type":"recipe","name":"干煸四季豆","meal":"午餐/晚餐","time":15,"diff":"中等","tags":["家常","川菜","下饭","素菜"],"ingredients":["四季豆300g","猪肉末50g","芽菜/榨菜末","干辣椒","花椒","蒜末","姜末","生抽","盐"],"steps":["四季豆去筋掰段沥干水分（一定要干！）","热锅多油煎炸四季豆至表面起皱（约5分钟）捞出","留底油炒肉末至酥香","加干辣椒花椒蒜姜末炒香","加芽菜末翻炒","倒回四季豆加生抽盐翻炒均匀"],"nutrition":{"calories":200,"protein_g":12,"fat_g":14,"carbs_g":12},"tips":"四季豆必须完全炸熟，生四季豆有毒"},
    {"type":"recipe","name":"皮蛋豆腐","meal":"凉菜","time":5,"diff":"简单","tags":["家常","凉菜","快手","夏季"],"ingredients":["内酯豆腐1盒","皮蛋2个","葱花","姜末","生抽","醋","香油","辣椒油"],"steps":["豆腐倒扣在盘子里（完整取出）","皮蛋切碎撒在豆腐上","碗中调汁：生抽+醋+姜末+香油+辣椒油","淋汁撒葱花，吃的时候捣碎拌匀"],"nutrition":{"calories":150,"protein_g":12,"fat_g":8,"carbs_g":6},"tips":"姜末是点睛之笔，去皮蛋的腥味"},
    {"type":"recipe","name":"红烧鱼","meal":"午餐/晚餐","time":30,"diff":"中等","tags":["家常","海鲜","宴客"],"ingredients":["鲈鱼1条（约500g）","姜片","葱段","蒜","生抽","老抽","料酒","糖","豆瓣酱可选"],"steps":["鱼洗净两面各划三刀，厨房纸吸干，抹少许盐","热锅热油，鱼下锅煎至两面金黄","加姜蒜豆瓣酱炒香","加料酒+生抽+老抽+糖+开水没过鱼一半","大火烧开转小火炖8分钟","中间翻面一次","大火收汁撒葱段"],"nutrition":{"calories":350,"protein_g":45,"fat_g":14,"carbs_g":8},"tips":"煎鱼不粘锅的秘诀：油热下锅后不要动，定型了自然就翻了"},
    {"type":"recipe","name":"上汤娃娃菜","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["家常","素菜","汤菜"],"ingredients":["娃娃菜2颗","皮蛋1个","咸蛋黄1个","火腿丁","蒜","高汤或水","盐","白胡椒粉"],"steps":["娃娃菜对半切开","热油炒蒜末和咸蛋黄至起泡出沙","加皮蛋丁和火腿丁翻炒","加高汤或水烧开","放入娃娃菜煮3-5分钟至软","加盐白胡椒粉调味"],"nutrition":{"calories":120,"protein_g":10,"fat_g":6,"carbs_g":8},"tips":"咸蛋黄炒出沙是汤底变奶白的关键"},
    {"type":"recipe","name":"农家小炒肉","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["家常","湘菜","下饭","快手"],"ingredients":["五花肉200g","青椒4个","蒜","豆豉","生抽","老抽","盐","油"],"steps":["五花肉切薄片，青椒切片","热锅不放油直接煸青椒至虎皮盛出（去生味）","锅里少许油下五花肉煸炒至出油微焦","加蒜豆豉炒香","淋生抽老抽上色","倒回青椒大火翻炒均匀"],"nutrition":{"calories":380,"protein_g":18,"fat_g":32,"carbs_g":8},"tips":"五花肉片越薄越好，冷冻半小时更好切"},
    {"type":"recipe","name":"干锅花菜","meal":"午餐/晚餐","time":15,"diff":"中等","tags":["家常","湘菜","下饭"],"ingredients":["花菜300g","五花肉100g","干辣椒","蒜","豆瓣酱","生抽","盐","青蒜苗"],"steps":["花菜掰小朵焯水1分钟沥干","五花肉切薄片","热锅不放油炒花菜至表面微焦盛出","锅里放油煸五花肉至出油卷曲","加豆瓣酱干辣椒蒜炒香","倒回花菜大火翻炒","加生抽盐青蒜苗翻炒出锅"],"nutrition":{"calories":220,"protein_g":14,"fat_g":16,"carbs_g":10},"tips":"花菜一定要炒到表面微焦，口感才有层次"},

    # ── 快手/一人食 ──
    {"type":"recipe","name":"蛋炒饭","meal":"午餐/晚餐","time":8,"diff":"简单","tags":["快手","一人食","入门","主食"],"ingredients":["隔夜米饭1碗","鸡蛋2个","葱花","盐","油10g","火腿丁/虾仁/玉米粒可选"],"steps":["鸡蛋打散加少许盐搅匀","大火热油，倒入蛋液用筷子快速搅散","蛋液还没完全凝固时倒入米饭","中火不停翻炒把米饭炒散","加盐调味，加火腿丁等配料","炒到米饭粒粒分明加葱花出锅"],"nutrition":{"calories":380,"protein_g":14,"fat_g":16,"carbs_g":48},"tips":"隔夜米饭水分少，才炒得出粒粒分明的效果"},
    {"type":"recipe","name":"葱油拌面","meal":"午餐/晚餐","time":15,"diff":"简单","tags":["快手","一人食","主食","上海"],"ingredients":["面条150g","小葱100g","生抽","老抽","糖","油60ml"],"steps":["小葱洗净完全沥干（有水会溅油）切段","冷锅冷油小火慢炸葱段至焦黄酥脆（约10分钟）","关火加生抽+老抽+糖搅匀成葱油","面条煮熟捞出","淋2-3勺葱油拌匀，放上炸好的葱段"],"nutrition":{"calories":420,"protein_g":10,"fat_g":22,"carbs_g":48},"tips":"做一大瓶葱油放冰箱，每次煮面挖一勺，1分钟搞定"},
    {"type":"recipe","name":"番茄鸡蛋盖浇面","meal":"午餐/晚餐","time":12,"diff":"简单","tags":["快手","一人食","入门"],"ingredients":["面条150g","鸡蛋2个","番茄2个","葱花","盐","糖","生抽","油"],"steps":["鸡蛋打散炒熟盛出","番茄切块炒出汁加少许水炖3分钟","加盐+糖+生抽调味","倒回鸡蛋拌匀","面条煮熟捞出","番茄鸡蛋浇在面上撒葱花"],"nutrition":{"calories":400,"protein_g":18,"fat_g":14,"carbs_g":52},"tips":"番茄一定要炒出沙才够味，可以加一小勺番茄酱提味"},
    {"type":"recipe","name":"蛋包饭","meal":"午餐/晚餐","time":15,"diff":"中等","tags":["快手","一人食","日式"],"ingredients":["米饭1碗","鸡胸肉100g","洋葱1/4个","青豆","番茄酱","鸡蛋2个","牛奶","黄油","盐"],"steps":["洋葱切丁，鸡肉切小丁","黄油炒香洋葱，加鸡肉炒变色","加米饭青豆翻炒，加番茄酱和盐调味","鸡蛋+牛奶打散，平底锅摊成薄蛋皮","蛋皮半熟时把炒饭放中间","蛋皮包起翻扣在盘子里","挤番茄酱装饰"],"nutrition":{"calories":460,"protein_g":32,"fat_g":16,"carbs_g":50},"tips":"蛋皮不要全熟再包，半熟时包利用余温定型"},
    {"type":"recipe","name":"杏鲍菇炒肉","meal":"午餐/晚餐","time":12,"diff":"简单","tags":["快手","家常","下饭"],"ingredients":["杏鲍菇2个","猪瘦肉150g","青椒","蒜","生抽","蚝油","淀粉","料酒","油"],"steps":["肉切丝加料酒+生抽+淀粉腌10分钟","杏鲍菇撕成细条（不要切，撕的入味）","热油滑炒肉丝变色盛出","余油炒杏鲍菇至出水变软","加青椒蒜末翻炒","倒回肉丝加蚝油生抽炒匀"],"nutrition":{"calories":280,"protein_g":28,"fat_g":12,"carbs_g":14},"tips":"杏鲍菇手撕比刀切更入味，口感像肉"},

    # ── 减脂加餐/零食 ──
    {"type":"recipe","name":"烤红薯","meal":"加餐/早餐","time":50,"diff":"简单","tags":["减脂","加餐","高纤维","甜点替代"],"ingredients":["红薯（选细长的蜜薯）2个"],"steps":["红薯洗净不要去皮","烤箱200度预热","红薯放烤架上（中层）","烤40-50分钟至流蜜","用筷子能轻松扎透就行"],"nutrition":{"calories":200,"protein_g":3,"fat_g":0.5,"carbs_g":46},"tips":"选细长形状的蜜薯比圆胖的干粉薯甜得多"},
    {"type":"recipe","name":"水煮毛豆","meal":"加餐","time":15,"diff":"简单","tags":["减脂","加餐","高蛋白","零食"],"ingredients":["毛豆300g","盐","八角","花椒","干辣椒"],"steps":["毛豆剪掉两端（入味关键）","搓洗去掉表面绒毛","水加盐+八角+花椒+干辣椒烧开","下毛豆煮5-8分钟（不要盖锅盖）","捞出过凉水即可吃"],"nutrition":{"calories":180,"protein_g":16,"fat_g":8,"carbs_g":12},"tips":"不盖锅盖煮毛豆才保持翠绿，盖盖会闷黄"},

    # ── 更多汤羹 ──
    {"type":"recipe","name":"紫菜蛋花汤","meal":"午餐/晚餐","time":5,"diff":"简单","tags":["汤羹","快手","入门"],"ingredients":["紫菜1片","鸡蛋1个","虾皮","葱花","盐","香油","白胡椒粉"],"steps":["紫菜撕碎放入大碗里加虾皮","水烧开淋入蛋液形成蛋花","关火倒进放了紫菜虾皮的碗里","加盐+白胡椒粉+香油+葱花搅匀"],"nutrition":{"calories":80,"protein_g":8,"fat_g":4,"carbs_g":3},"tips":"紫菜不要下锅煮，用热汤冲熟才嫩不腥"},
    {"type":"recipe","name":"萝卜排骨汤","meal":"午餐/晚餐","time":70,"diff":"简单","tags":["汤羹","家常","冬季"],"ingredients":["排骨400g","白萝卜1根","姜片","料酒","盐","白胡椒粉","葱花"],"steps":["排骨焯水洗净","白萝卜去皮切滚刀块","排骨+姜片+料酒+足水大火烧开","转小火炖40分钟","加白萝卜再炖20分钟","加盐白胡椒粉调味撒葱花"],"nutrition":{"calories":350,"protein_g":28,"fat_g":20,"carbs_g":12},"tips":"白萝卜后放，否则炖烂了没口感且汤会发苦"},

    # ── 更多早餐 ──
    {"type":"recipe","name":"鸡蛋灌饼","meal":"早餐","time":15,"diff":"中等","tags":["早餐","中式","街边小吃"],"ingredients":["面粉150g","热水+冷水","鸡蛋1个","生菜","甜面酱","辣酱","油","盐"],"steps":["面粉半烫面（一半热水一半冷水和面），醒20分钟","擀成薄饼","平底锅热油下饼","饼鼓起大泡时用筷子戳个洞","鸡蛋打散从洞口灌进去","两面煎至金黄","刷甜面酱和辣酱，放生菜卷起"],"nutrition":{"calories":350,"protein_g":14,"fat_g":14,"carbs_g":45},"tips":"半烫面做的饼凉了也不硬，是饼皮的诀窍"},
    {"type":"recipe","name":"红豆薏米粥","meal":"早餐","time":50,"diff":"简单","tags":["早餐","消肿","养生"],"ingredients":["红豆50g","薏米50g","冰糖可选","水"],"steps":["红豆薏米提前泡4小时（或过夜）","加水大火烧开转小火熬40分钟","熬至红豆开花薏米软烂","喜欢甜的加冰糖"],"nutrition":{"calories":280,"protein_g":14,"fat_g":2,"carbs_g":56},"tips":"薏米性寒，怕寒的可以先干锅炒一下再煮"},

    # ── 更多增肌/蛋白 ──
    {"type":"recipe","name":"剁椒鱼头","meal":"午餐/晚餐","time":25,"diff":"中等","tags":["家常","湘菜","宴客","高蛋白"],"ingredients":["胖头鱼头1个（约800g）","剁椒100g","姜","蒜","料酒","蒸鱼豉油","葱花","油"],"steps":["鱼头洗净对半切开（不要完全切断）抹料酒腌制10分钟","盘底铺姜片，放上鱼头","剁椒+蒜末+姜末拌匀铺在鱼头上","水开上锅大火蒸10分钟","出锅倒掉多余汤汁","淋蒸鱼豉油撒葱花浇热油"],"nutrition":{"calories":380,"protein_g":42,"fat_g":18,"carbs_g":8},"tips":"蒸出来的汤汁要倒掉，那是腥味的来源"},
    {"type":"recipe","name":"沙姜鸡","meal":"午餐/晚餐","time":30,"diff":"中等","tags":["家常","粤菜","高蛋白"],"ingredients":["三黄鸡半只","沙姜50g","姜","葱","生抽","老抽","料酒","盐","油"],"steps":["鸡斩块加生抽+老抽+料酒腌20分钟","沙姜和姜剁成蓉","热油炒沙姜姜蓉出香","下鸡块炒至表面金黄","加少许水焖10分钟","收汁至浓稠裹住鸡块撒葱段"],"nutrition":{"calories":380,"protein_g":40,"fat_g":22,"carbs_g":4},"tips":"沙姜是这道菜的灵魂，不能用普通姜替代"},

    # ── 素食/清淡 ──
    {"type":"recipe","name":"蚝油杏鲍菇","meal":"午餐/晚餐","time":10,"diff":"简单","tags":["素菜","快手","下饭"],"ingredients":["杏鲍菇2个","蚝油","生抽","蒜","糖少许","油5g","葱花"],"steps":["杏鲍菇切厚片，表面划十字花刀","热锅少油两面煎至金黄","加蒜末炒香","加蚝油+生抽+少许糖+2勺水","中火焖2分钟收汁撒葱花"],"nutrition":{"calories":80,"protein_g":4,"fat_g":5,"carbs_g":8},"tips":"划花刀不仅好看，还能让酱汁更好地渗进去"},
    {"type":"recipe","name":"西芹炒百合","meal":"午餐/晚餐","time":8,"diff":"简单","tags":["素菜","清淡","快手"],"ingredients":["西芹200g","鲜百合1个","盐","油5g","枸杞几颗"],"steps":["西芹削去外皮（口感更嫩）切斜段","鲜百合掰开洗净","水开加盐和油，西芹焯水30秒","热油下西芹和百合快速翻炒1分钟","加盐调好味，撒枸杞出锅"],"nutrition":{"calories":70,"protein_g":3,"fat_g":5,"carbs_g":8},"tips":"百合不要久炒，炒久了会化掉变粉"},

    # ── 健身便当/备餐 ──
    {"type":"recipe","name":"照烧鸡腿便当","meal":"午餐","time":25,"diff":"简单","tags":["便当","备餐","高蛋白"],"ingredients":["去骨鸡腿1个","西兰花","胡萝卜","米饭","照烧酱：生抽2+味醂2+蜂蜜1"],"steps":["鸡腿用叉子戳孔加照烧酱腌20分钟","皮朝下入锅中小火煎至金黄翻面","倒入剩余酱汁+少许水，盖盖焖8分钟","汤汁浓稠后切片","西兰花焯水，胡萝卜切花焯水","配米饭装便当"],"nutrition":{"calories":520,"protein_g":36,"fat_g":16,"carbs_g":55},"tips":"便当公式=1拳蛋白质+1拳主食+2拳蔬菜"},
    {"type":"recipe","name":"牛肉藜麦沙拉","meal":"午餐","time":20,"diff":"简单","tags":["便当","高蛋白","低碳"],"ingredients":["牛排150g","藜麦50g","混合生菜","樱桃萝卜","橄榄油","巴萨米克醋","盐","黑胡椒"],"steps":["藜麦煮15分钟沥干放凉","牛排煎至5分熟切片","生菜铺底，放上藜麦、牛排片、萝卜片","淋橄榄油+巴萨米克醋+盐+黑胡椒"],"nutrition":{"calories":420,"protein_g":38,"fat_g":18,"carbs_g":28},"tips":"带便当的话牛排可以前一晚煎好冷藏切好，第二天冷吃也好吃"},

]

# ═══════════════════════════════════════════════════════════════
# FitChef 加载器
# ═══════════════════════════════════════════════════════════════

class FitChefLoader:
    """FitChef 知识库加载器：食材 + 食谱 + 膳食指南"""

    def __init__(self):
        self.documents: List[FitChefDocument] = []
        self.doc_texts: List[str] = []
        self.stats = {"ingredients": 0, "recipes": 0, "xiachufang_recipes": 0, "guidelines": 0, "total_chunks": 0}

    def load(self) -> List[FitChefDocument]:
        if self.documents:
            return self.documents
        self.documents = []

        # ── 1. 加载食材营养成分 ──
        self._load_ingredients()

        # ── 2. 加载内置精选食谱 ──
        self._load_recipes()

        # ── 2.5 加载下厨房食谱语料库 ──
        self._load_xiachufang()

        # ── 3. 加载膳食指南 ──
        self._load_guidelines()

        self.doc_texts = [d.text for d in self.documents]
        self.stats["total_chunks"] = len(self.documents)
        return self.documents

    def _load_ingredients(self):
        """加载《中国食物成分表》数据，每条食材一个文档"""
        comp_path = DATA_DIR / "china_food_composition.json"
        if not comp_path.exists():
            return

        with open(comp_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        for i, item in enumerate(items):
            name = item.get("foodName", f"食材_{i}")
            if not name or len(name) < 2:
                continue

            # 构建结构化文本
            parts = [f"【食材】{name}"]
            nutrition_parts = []
            if item.get("energyKCal"):
                nutrition_parts.append(f"热量{item['energyKCal']}大卡")
            if item.get("protein"):
                nutrition_parts.append(f"蛋白质{item['protein']}g")
            if item.get("fat"):
                nutrition_parts.append(f"脂肪{item['fat']}g")
            if item.get("CHO"):
                nutrition_parts.append(f"碳水{item['CHO']}g")
            if item.get("dietaryFiber"):
                nutrition_parts.append(f"膳食纤维{item['dietaryFiber']}g")

            if nutrition_parts:
                parts.append("每100g：" + "，".join(nutrition_parts))

            # 微量元素
            micro = []
            for label, key in [("钙", "Ca"), ("铁", "Fe"), ("锌", "Zn"), ("钾", "K"),
                               ("维生素C", "vitaminC"), ("维生素A", "vitaminA")]:
                val = item.get(key, "")
                if val and val != "" and val != "…":
                    try:
                        if float(val) > 0:
                            micro.append(f"{label}{val}")
                    except ValueError:
                        pass
            if micro:
                parts.append("微量元素：" + " ".join(micro))

            if item.get("remark") and item["remark"].strip() and item["remark"] != "…":
                parts.append(f"备注：{item['remark']}")

            text = "\n".join(parts)
            doc_id = f"ingredient_{i}"
            self.documents.append(FitChefDocument(
                doc_id=doc_id,
                text=text,
                metadata={
                    "type": "ingredient",
                    "name": name,
                    "food_code": item.get("foodCode", ""),
                    "calories": item.get("energyKCal"),
                    "protein": item.get("protein"),
                    "fat": item.get("fat"),
                    "carbs": item.get("CHO"),
                }
            ))

        self.stats["ingredients"] = sum(1 for d in self.documents if d.metadata.get("type") == "ingredient")

    def _load_recipes(self):
        """加载内置精选食谱，每条一个文档"""
        for i, recipe in enumerate(RECIPES):
            parts = [
                f"【食谱】{recipe['name']}",
                f"食材：{'、'.join(recipe['ingredients'])}",
                f"耗时：{recipe['time']}分钟 | 难度：{recipe['diff']} | 类型：{recipe['meal']}",
                f"标签：{'、'.join(recipe['tags'])}",
                f"步骤：{'；'.join(recipe['steps'])}",
            ]
            n = recipe["nutrition"]
            parts.append(f"营养估算：热量约{n['calories']}大卡，蛋白质{n['protein_g']}g，脂肪{n['fat_g']}g，碳水{n['carbs_g']}g")
            if recipe.get("tips"):
                parts.append(f"小贴士：{recipe['tips']}")

            text = "\n".join(parts)
            doc_id = f"recipe_{i}"
            self.documents.append(FitChefDocument(
                doc_id=doc_id,
                text=text,
                metadata={
                    "type": "recipe",
                    "name": recipe["name"],
                    "meal": recipe["meal"],
                    "time": recipe["time"],
                    "difficulty": recipe["diff"],
                    "tags": recipe["tags"],
                    "ingredients": recipe["ingredients"],
                    "nutrition": recipe["nutrition"],
                }
            ))

        self.stats["recipes"] = sum(1 for d in self.documents if d.metadata.get("type") == "recipe")

    def _load_xiachufang(self):
        """加载下厨房食谱语料库（筛选后的 JSON）"""
        xcf_path = DATA_DIR / "xiachufang_recipes.json"
        if not xcf_path.exists():
            return

        with open(xcf_path, "r", encoding="utf-8") as f:
            recipes = json.load(f)

        for i, recipe in enumerate(recipes):
            self.documents.append(FitChefDocument(
                doc_id=f"xcf_{i}",
                text=recipe.get("text", ""),
                metadata={
                    "type": "recipe",
                    "name": recipe.get("name", ""),
                    "dish": recipe.get("dish", ""),
                    "ingredients": recipe.get("ingredients", []),
                    "steps": recipe.get("steps", []),
                    "source": "xiachufang",
                }
            ))

        self.stats["xiachufang_recipes"] = len(recipes)

    def _load_guidelines(self):
        """加载《中国居民膳食指南》并分块（准则 → ●分点）"""
        gl_path = DATA_DIR / "dietary_guidelines.md"
        if not gl_path.exists():
            return

        with open(gl_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        # 先按准则标题切分
        criteria = re.split(r"(?=准则[一二三四五六七八九十])", content)
        for i, criterion in enumerate(criteria):
            criterion = criterion.strip()
            if not criterion or len(criterion) < 20:
                continue

            lines = criterion.split("\n")
            title = lines[0].lstrip("# ").strip() if lines else f"膳食指南_{i}"

            # 过滤图片和空行
            clean_lines = [l for l in lines[1:] if not l.startswith("<img") and not l.startswith("![") and l.strip()]
            body = "\n".join(clean_lines)

            # 检查是否有 ● 分点
            bullets = [l.strip() for l in clean_lines if l.strip().startswith("●")]
            if bullets:
                # 提取概述（●之前的文字）
                first_bullet_idx = next((j for j, l in enumerate(clean_lines) if l.strip().startswith("●")), 0)
                overview_lines = [l for l in clean_lines[:first_bullet_idx] if l.strip()]
                overview = "\n".join(overview_lines) if overview_lines else ""

                for bi, bullet in enumerate(bullets):
                    # 每个分点 = 准则标题 + 概述 + 该分点
                    parts = [f"【膳食指南】{title}"]
                    if overview:
                        parts.append(overview)
                    parts.append(bullet)
                    text = "\n".join(parts)

                    self.documents.append(FitChefDocument(
                        doc_id=f"guideline_{i}_{bi}",
                        text=text,
                        metadata={
                            "type": "guideline",
                            "name": title,
                            "source": "中国居民膳食指南2022",
                        }
                    ))
            else:
                # 无分点，保持完整
                text = f"【膳食指南】{title}\n{body}"
                self.documents.append(FitChefDocument(
                    doc_id=f"guideline_{i}",
                    text=text,
                    metadata={
                        "type": "guideline",
                        "name": title,
                        "source": "中国居民膳食指南2022",
                    }
                ))

        self.stats["guidelines"] = sum(1 for d in self.documents if d.metadata.get("type") == "guideline")

    def get_documents(self) -> List[FitChefDocument]:
        if not self.documents:
            self.load()
        return self.documents

    def get_texts(self) -> List[str]:
        if not self.doc_texts:
            self.load()
        return self.doc_texts

    def get_stats(self) -> dict:
        if not self.documents:
            self.load()
        return self.stats


# 全局单例（替换 tcm_loader）
fitchef_loader = FitChefLoader()
