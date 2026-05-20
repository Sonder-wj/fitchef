import json
from pathlib import Path
from typing import List, Dict, Optional


class FoodDBService:
    """食物营养数据库服务，从 china_food_composition.json 加载 1657 种食材"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        data_path = Path(__file__).parent.parent / "data" / "china_food_composition.json"
        with open(data_path, "r", encoding="utf-8") as f:
            self._foods: List[Dict] = json.load(f)
        self._loaded = True

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """按食物名搜索，返回匹配项"""
        self._load()
        q = query.strip().lower()
        if not q:
            return []
        results = []
        for i, item in enumerate(self._foods):
            name = item.get("foodName", "")
            if not name:
                continue
            if q in name.lower():
                results.append({
                    "id": f"food_{i}",
                    "food_name": name,
                    "calories": self._to_float(item.get("energyKCal")),
                    "protein": self._to_float(item.get("protein")),
                    "fat": self._to_float(item.get("fat")),
                    "carbs": self._to_float(item.get("CHO")),
                    "dietary_fiber": self._to_float(item.get("dietaryFiber")),
                })
            if len(results) >= limit:
                break
        return results

    def get_by_id(self, food_id: str) -> Optional[Dict]:
        """根据 ID 获取食物详情（含微量元素）"""
        self._load()
        if not food_id.startswith("food_"):
            return None
        try:
            idx = int(food_id.split("_")[1])
        except (ValueError, IndexError):
            return None
        if idx < 0 or idx >= len(self._foods):
            return None
        item = self._foods[idx]
        name = item.get("foodName", "")
        if not name:
            return None
        return {
            "id": food_id,
            "food_name": name,
            "calories": self._to_float(item.get("energyKCal")),
            "protein": self._to_float(item.get("protein")),
            "fat": self._to_float(item.get("fat")),
            "carbs": self._to_float(item.get("CHO")),
            "dietary_fiber": self._to_float(item.get("dietaryFiber")),
            "vitamin_c": item.get("vitaminC", ""),
            "vitamin_a": item.get("vitaminA", ""),
            "calcium": item.get("Ca", ""),
            "iron": item.get("Fe", ""),
            "zinc": item.get("Zn", ""),
            "potassium": item.get("K", ""),
            "remark": item.get("remark", ""),
        }

    def calculate_nutrition(self, food_id: str, amount_g: float) -> Optional[Dict]:
        """根据食物 ID 和重量计算营养素"""
        food = self.get_by_id(food_id)
        if not food:
            return None
        ratio = amount_g / 100.0
        return {
            "food_name": food["food_name"],
            "amount_g": amount_g,
            "calories": round((food["calories"] or 0) * ratio, 1),
            "protein_g": round((food["protein"] or 0) * ratio, 1),
            "fat_g": round((food["fat"] or 0) * ratio, 1),
            "carbs_g": round((food["carbs"] or 0) * ratio, 1),
        }

    @staticmethod
    def _to_float(val) -> Optional[float]:
        if val is None or val == "" or val == "…":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None


food_db_service = FoodDBService()
