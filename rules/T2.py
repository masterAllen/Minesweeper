'''
[T']: 雷必须是三连
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict

def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                # 获取所有可能的三连区域
                triplets = possible_triplets(table, (i, j))

                if len(triplets) == 0:
                    raise ValueError(f'某个雷没有三连区域，坐标：{(i, j)}')

                # 如果只有一个三连，那么一定是雷
                if len(triplets) == 1:
                    for point in triplets[0]:
                        if table[point] == 'unknown':
                            results[Constraint([point])] = (1, 1)

                # 如果有两个三连，观察是否其中有交集
                if len(triplets) == 2:
                    set1 = {x for x in triplets[0] if table[x] == 'unknown'}
                    set2 = {x for x in triplets[1] if table[x] == 'unknown'}
                    if len(set1 & set2) > 0:
                        results[Constraint(list(set1 & set2))] = (1, 1)

            elif table[i, j] == 'unknown':
                # 获取所有可能的三连区域
                triplets = possible_triplets(table, (i, j))

                # 如果未知格子没有三连，那么他一定不可能是雷
                if len(triplets) == 0:
                    results[Constraint([(i, j)])] = (0, 0)

    return results


def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    """
    检查当前雷的坐标是否有三连，如果有则返回 False
    四个方向：水平、垂直、左上-右下对角线、右上-左下对角线
    """
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                # 获取所有可能的三连区域
                triplets = possible_triplets(table, (i, j))

                if len(triplets) == 0:
                    return False
    return True

def possible_triplets(table: np.ndarray, p_in: tuple[int, int]) -> list[tuple[int, int, int]]:
    '''
    假设 point 是雷，返回其涉及到三连的三个点
    '''
    x, y = p_in
    triplets = [
        # 竖方向
        [(x-2, y), (x-1, y), (x, y)],
        [(x-1, y), (x, y), (x+1, y)],
        [(x, y), (x+1, y), (x+2, y)],
        # 横方向
        [(x, y-2), (x, y-1), (x, y)],
        [(x, y-1), (x, y), (x, y+1)],
        [(x, y), (x, y+1), (x, y+2)],
        # 对角线方向
        [(x-2, y-2), (x-1, y-1), (x, y)],
        [(x-1, y-1), (x, y), (x+1, y+1)],
        [(x, y), (x+1, y+1), (x+2, y+2)],
        # 对角线方向
        [(x+2, y-2), (x+1, y-1), (x, y)],
        [(x+1, y-1), (x, y), (x-1, y+1)],
        [(x, y), (x-1, y+1), (x-2, y+2)],
    ]

    # 先计算各个点是不是符合要求
    point_result = dict()
    for triplet in triplets:
        for point in triplet:
            is_ok = True
            if point[0] < 0 or point[0] >= table.shape[0] or point[1] < 0 or point[1] >= table.shape[1]:
                is_ok = False
            elif table[point] != 'unknown' and table[point] != 'mine':
                is_ok = False
            point_result[point] = is_ok

    results = []
    for triplet in triplets:
        if all(point_result[point] for point in triplet):
            results.append(triplet)

    return results