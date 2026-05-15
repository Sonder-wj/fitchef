"""XiaChuFang Recipe Corpus -> fitchef 格式筛选转换"""
import json, zipfile, re, sys, io
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_DIR = "E:/develop/my_project1/app/data"
ZIP_FILE = f"{DATA_DIR}/recipe_corpus_finetune.zip"
OUTPUT = f"{DATA_DIR}/xiachufang_recipes.json"

FITNESS_KEYWORDS = [
    "减脂", "减肥", "低卡", "低脂", "瘦身", "轻食", "少油", "无油",
    "低热量", "控卡", "减重", "增肌", "高蛋白", "健身", "增重",
    "营养", "健康", "养生", "清淡",
    "鸡胸", "鸡胸肉", "虾仁", "西兰花", "三文鱼", "牛油果",
    "燕麦", "藜麦", "全麦", "糙米", "红薯", "紫薯",
    "豆腐", "鸡蛋", "牛肉", "鱼", "沙拉",
    "炒", "蒸", "煮", "炖", "拌", "汤", "煲",
]
FITNESS_PATTERN = re.compile("|".join(FITNESS_KEYWORDS))

def is_fitness(obj):
    return bool(FITNESS_PATTERN.search(json.dumps(obj, ensure_ascii=False)))

def quality(obj):
    s = 0
    if len((obj.get("description") or "").strip()) > 10:
        s += 1
    s += min(len(obj.get("recipeInstructions") or []), 5)
    s += min(len(obj.get("recipeIngredient") or []) // 3, 3)
    return s

# === 第一轮：统计 ===
print("=== 第一轮: 统计 ===")
total = 0
known_dish = 0
fitness_count = 0
dish_counter = Counter()

with zipfile.ZipFile(ZIP_FILE, "r") as zf:
    with zf.open("recipe_corpus_finetune.json") as f:
        for line in f:
            total += 1
            if total % 500000 == 0:
                print(f"  已扫 {total} 条...")
            obj = json.loads(line)
            dish = obj.get("dish", "Unknown")
            if dish != "Unknown":
                known_dish += 1
                dish_counter[dish] += 1
            if is_fitness(obj):
                fitness_count += 1

print(f"总数: {total}")
print(f"已知菜品: {known_dish} ({known_dish/total*100:.0f}%)")
print(f"不同菜品: {len(dish_counter)}")
print(f"健身相关: {fitness_count} ({fitness_count/total*100:.0f}%)")

vd = Counter(dish_counter.values())
print(f"每道菜版本数: {vd.most_common(5)}")

# === 第二轮: 筛选 ===
print("\n=== 第二轮: 筛选 ===")

best_per_dish = defaultdict(list)  # dish -> [(score, obj)]
orphans = []  # 健身相关但 dish=Unknown

with zipfile.ZipFile(ZIP_FILE, "r") as zf:
    with zf.open("recipe_corpus_finetune.json") as f:
        for line in f:
            obj = json.loads(line)
            dish = obj.get("dish", "Unknown")
            score = quality(obj)
            if dish != "Unknown":
                best_per_dish[dish].append((score, obj))
                if len(best_per_dish[dish]) > 3:
                    best_per_dish[dish].sort(key=lambda x: x[0], reverse=True)
                    best_per_dish[dish] = best_per_dish[dish][:2]
            elif is_fitness(obj):
                orphans.append((score, obj))

selected = []
for dish, candidates in best_per_dish.items():
    candidates.sort(key=lambda x: x[0], reverse=True)
    for _, obj in candidates[:2]:
        selected.append(obj)

print(f"已知菜品选取: {len(selected)} 条, 覆盖 {len(best_per_dish)} 道菜")

orphans.sort(key=lambda x: x[0], reverse=True)
needed = max(20000 - len(selected), 0)
for _, obj in orphans[:needed]:
    selected.append(obj)
print(f"补充 orphan: {min(len(orphans), needed)} 条")
print(f"总计: {len(selected)} 条")

# === 转换 ===
print("\n=== 转换格式 ===")
output = []
for obj in selected:
    name = obj.get("name", "")
    ingrs = obj.get("recipeIngredient", [])
    steps = obj.get("recipeInstructions", [])
    desc = (obj.get("description") or "")[:200]
    dish = obj.get("dish", "")

    parts = [f"[食谱] {name}"]
    if dish and dish != "Unknown":
        parts.append(f"菜品: {dish}")
    if ingrs:
        parts.append(f"食材: {', '.join(ingrs[:15])}")
    if desc.strip():
        parts.append(f"简介: {desc}")
    if steps:
        parts.append(f"步骤: {'; '.join([s.replace(chr(10), ' ') for s in steps])}")

    output.append({
        "name": name,
        "dish": dish,
        "ingredients": ingrs,
        "steps": steps,
        "description": desc,
        "text": "\n".join(parts),
    })

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

size_mb = len(json.dumps(output, ensure_ascii=False)) / 1024 / 1024
print(f"输出: {OUTPUT}")
print(f"大小: {size_mb:.1f} MB, 共 {len(output)} 条")
print("完成!")
