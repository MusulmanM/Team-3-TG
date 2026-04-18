def check_luhn(card_no: str) -> bool:
    n_digits = len(card_no)
    n_sum = 0
    is_second = False
    for i in range(n_digits - 1, -1, -1):
        d = ord(card_no[i]) - ord('0')
        if is_second:
            d = d * 2
        n_sum += d // 10
        n_sum += d % 10
        is_second = not is_second
    return n_sum % 10 == 0
