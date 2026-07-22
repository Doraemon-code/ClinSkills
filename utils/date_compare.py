import pandas as pd

def compare_dates(date1, date2, mode=1):
    """
    比较两个日期的大小。

    :param date1: 第一个日期，格式为 'YYYY-MM-DD' 或部分日期，允许 NaN/None
    :param date2: 第二个日期，格式为 'YYYY-MM-DD' 或部分日期，允许 NaN/None
    :param mode: 比较方式，1 为直接比较日期，2 为将 "uk" 或 "unk" 替换为 01 后再比较
    :return: 1 如果 date1 > date2，-1 如果 date1 < date2，0 如果相等，2 如果无法比较
    """

    UNKNOWN = {"uk", "unk", ""}

    def parse_date(date_val):
        """
        解析日期字符串，处理部分日期的情况。
        遇到 NaN/None/空值 -> 返回 None（表示无法比较）
        """
        if date_val is None:
            return None

        # 兼容 pandas 的 NaN
        try:
            if pd.isna(date_val):
                return None
        except (TypeError, ValueError):
            pass

        s = str(date_val).strip()
        if s == "" or s.lower() in {"nan", "none"}:
            return None

        # 统一分隔符
        s = s.replace("/", "-")

        parts = s.split("-")
        while len(parts) < 3:
            parts.append("uk")
        parts = parts[:3]

        # 统一转换为小写+去空格
        parts = [p.strip().lower() for p in parts]
        return parts

    def safe_int(x):
        """把数字字符串转 int；如果不是纯数字 -> 返回 None"""
        if x in UNKNOWN:
            return None
        try:
            return int(x)
        except Exception:
            return None

    def compare_mode1(parts1, parts2):
        """
        方式1：直接比较年月日，如果遇到 uk/unk 或无法转数字则无法比较，返回2
        """
        for p1, p2 in zip(parts1, parts2):
            n1 = safe_int(p1)
            n2 = safe_int(p2)
            if n1 is None or n2 is None:
                return 2
            if n1 != n2:
                return 1 if n1 > n2 else -1
        return 0

    def compare_mode2(parts1, parts2):
        """
        方式2：将 "uk" 或 "unk" 替换为 01 后再比较
        同时：若出现无法转数字的字段（比如 'xx'），也视为无法比较 -> 返回2
        """
        parts1 = ["01" if p in ["uk", "unk"] else p for p in parts1]
        parts2 = ["01" if p in ["uk", "unk"] else p for p in parts2]

        nums1, nums2 = [], []
        for p in parts1:
            try:
                nums1.append(int(p))
            except Exception:
                return 2
        for p in parts2:
            try:
                nums2.append(int(p))
            except Exception:
                return 2

        for n1, n2 in zip(nums1, nums2):
            if n1 != n2:
                return 1 if n1 > n2 else -1
        return 0

    parts1 = parse_date(date1)
    parts2 = parse_date(date2)

    # 任一为空/NaN -> 无法比较
    if parts1 is None or parts2 is None:
        return 2

    if mode == 1:
        return compare_mode1(parts1, parts2)
    elif mode == 2:
        return compare_mode2(parts1, parts2)
    else:
        raise ValueError("Invalid mode. Use 1 or 2.")


# 测试示例
if __name__ == "__main__":
    print(compare_dates("2024-01-15", "2024-01-10", mode=1))   # 1
    print(compare_dates("2024-01-15", "2024-01-15", mode=1))   # 0
    print(compare_dates("2024-01-15", "2024-01-20", mode=1))   # -1
    print(compare_dates("2024-uk-15", "2024-01-10", mode=1))   # 2
    print(compare_dates("2024-UNK-15", "2024-01-10", mode=2))  # 1
    print(compare_dates("2024-Uk-15", "2024-UK-15", mode=2))   # 0
    print(compare_dates(float("nan"), "2024-01-01", mode=2))   # 2（不报错）
