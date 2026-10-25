def array_statistics(state):
    return f"Сравнений: {state['comparisons']}  ·  Перестановок: {state['swaps']}"


def merge_statistics(state):
    return (f"Сравнений: {state['comparisons']}  ·  "
            f"Записей: {state['writes']}  ·  Слияний: {state['merges']}")
