from algoviz.algorithms.spec import Algorithm
from algoviz.traces.array_trace import ArrayTrace

ID = "bubble_sort"


def build(values):
    trace = ArrayTrace(values, ID)
    for end in range(len(values) - 1, 0, -1):
        swapped = False
        for index in range(end):
            left, right = trace.compare(index, index + 1)
            if left > right:
                trace.swap(index, index + 1)
                swapped = True
        trace.mark_sorted([end])
        if not swapped:
            trace.mark_sorted(range(end))
            break
    return trace.finish()


ALGORITHM = Algorithm(
    id=ID,
    title="Пузырьковая сортировка",
    category="Сортировки",
    description="Соседние элементы меняются местами.",
    input_type="integer_array", visualization="array",
    example="7, 3, 9, 1, 5, 2",
    build=build,
)
