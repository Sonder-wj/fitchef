"""分析 XiaChuFang Recipe Corpus 字段，筛选 + 转换为 fitchef 格式"""
import json, sys, os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "data")
ZIP_FILE = os.path.join(DATA_DIR, "recipe_corpus_finetune.zip")
OUTPUT = os.path.join(DATA_DIR, "xiachufang_recipes.json")

# === Step 1: 看一眼原始字段 ===
import zipfile, io

if not os.path.exists(ZIP_FILE):
    print(f"找不到 {ZIP_FILE}，请等待下载完成")
    sys.exit(1)

with zipfile.ZipFile(ZIP_FILE, "r") as zf:
    names = zf.namelist()
    print(f"ZIP 内文件数: {len(names)}")
    json_files = [n for n in names if n.endswith(".json") or n.endswith(".jsonl")]
    print(f"JSON 文件: {json_files[:5]}")

    # 读第一条看结构
    if json_files:
        with zf.open(json_files[0]) as f:
            first_bytes = f.read(5000)
            try:
                data = json.loads(first_bytes)
                print("\n=== 第一条记录字段 ===")
                for k, v in data.items():
                    val_str = str(v)[:200] if v else "empty"
                    print(f"  {k}: {val_str}")
            except:
                print(first_bytes.decode("utf-8")[:2000])
    else:
        # 可能是单文件 JSON 或 tar
        biggest = sorted(names, key=lambda n: zf.getinfo(n).file_size, reverse=True)[:3]
        print(f"最大文件: {[(n, zf.getinfo(n).file_size) for n in biggest]}")
        for n in biggest[:1]:
            with zf.open(n) as f:
                raw = f.read(20000)
                try:
                    text = raw.decode("utf-8")
                    print(text[:3000])
                except:
                    print(f"二进制文件，前200字节: {raw[:200]}")
