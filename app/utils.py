"""General utils functions."""


def divide_list(target_list: list, item_size: int) -> list[list]:
    n = len(target_list)
    res = [None] * ((n - 1) // item_size + 1)

    for i in range(0, n, item_size):
        res[i // item_size] = target_list[i : i + item_size]

    return res
