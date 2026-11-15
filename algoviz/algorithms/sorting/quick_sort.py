from algoviz.algorithms.spec import Algorithm
from algoviz.traces.array_trace import ArrayTrace

ID = "quick_sort"


def build(values):
    trace = ArrayTrace(values, ID)
    def quick_sort(lo, hi, op):
        if(hi-lo<2):
            left, right = trace.compare(lo, lo+1)
            if(left > right):
                trace.swap(lo, lo+1)
            trace.mark_sorted([lo, lo+1])
            return
        else:
            index = lo
            while (index < op):
                left, right = trace.compare(index, op)
                if (left > right):
                    trace.swap(index, op - 1)
                    trace.swap(op - 1, op)
                    op -= 1
                else:
                    index += 1
            trace.mark_sorted([index])
            if(op - 1 > lo):quick_sort(lo, op, op - 1)
            else:
                trace.mark_sorted([lo])
            if(hi - 1 > op + 1):quick_sort(op + 1, hi, hi - 1)
            else:
                trace.mark_sorted([op + 1])
            return

    quick_sort(0, len(values), len(values)-1)
    return trace.finish()


ALGORITHM = Algorithm(
    id=ID,
    title="Быстрая сортировка",
    category="Сортировки",
    description="Выбирам элемент и сортируем массив по половинам больше и меньше элемента.",
    input_type="integer_array",
    visualization="array",
    example="5, 11, 2, 9, 12, 1, 7, 4, 10, 3, 8, 6",
    build=build,
)