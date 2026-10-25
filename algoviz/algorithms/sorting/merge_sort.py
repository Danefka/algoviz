from algoviz.algorithms.spec import Algorithm
from algoviz.traces.merge_trace import MergeTrace

ID = "merge_sort"


def build(values):
    trace = MergeTrace(values, ID)

    def divide(lo, hi, depth=0):
        if hi - lo < 2:
            return
        middle = (lo + hi) // 2
        trace.split(lo, middle, hi, depth)
        divide(lo, middle, depth + 1)
        divide(middle, hi, depth + 1)

    def assemble(lo, hi, depth=0):
        if hi - lo < 2:
            return
        middle = (lo + hi) // 2
        assemble(lo, middle, depth + 1)
        assemble(middle, hi, depth + 1)
        trace.begin_merge(lo, middle, hi, depth)
        while trace.has_next("left") and trace.has_next("right"):
            left, right = trace.compare()
            trace.copy_next("left" if left <= right else "right")
        for side in ("left", "right"):
            while trace.has_next(side):
                trace.copy_next(side)
        trace.commit()

    # Show the complete recursion tree before walking back up in postorder.
    divide(0, len(values))
    assemble(0, len(values))
    return trace.finish()


ALGORITHM = Algorithm(
    id=ID, title="Сортировка слиянием", category="Сортировки",
    description="Раскрываем дерево разбиений и собираем массив снизу вверх.",
    input_type="integer_array", visualization="merge_tree", example="7, 3, 5, 1", build=build,
)
