def get_market(code: str):
    market_code_dict = {
        '600': 'SH',
        '601': 'SH',
        '603': 'SH',
        '605': 'SH',
        '000': 'SZ',  # 主板
        '001': 'SZ',
        '688': 'IB',
        '300': 'SZ',  # 创业板
        '301': 'SZ',  # 创业板（新）
        '002': 'SZ',  # 中小板
    }
    return market_code_dict.get(code[:3], None)