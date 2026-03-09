'''
[N]: 负雷，表示染色格和非染色格之间的差值的绝对值
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint, ConstraintsDictV2

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    '''
    先得到各个格子组合的关系
    '''
    relations_dict = ConstraintsDictV2()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                unknown_coordinates = []
                # 奇数坐标、偶数坐标 的已知 mine 数目
                found_mines = [0, 0]
                found_unknowns = [0, 0]

                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    idx = 0 if utils.minenum_in_M(neighbor, table.shape) == 1 else 1
                    if table[neighbor] == 'unknown':
                        unknown_coordinates.append(neighbor)
                        found_unknowns[idx] += 1
                    if table[neighbor] == 'mine':
                        found_mines[idx] += 1

                if len(unknown_coordinates) == 0:
                    continue

                # 本质：|(x+k1) - (y+k2)| = n，其中 0<=x<=len(odd), 0<=y<=len(even)
                # 我们转成两种可能，先让 (k1-k2)=k，然后得到 x-y = n-k 或者 x-y = -k-n
                k = found_mines[0] - found_mines[1]
                n = int(table[i, j])

                key = tuple(unknown_coordinates)
                value = {n-k, -n-k}

                # 但是 value，即 x-y 有一个范围，最小值是 minx-maxy，最大值是 maxx-miny
                min_value = 0 - found_unknowns[1]
                max_value = found_unknowns[0] - 0

                value = {i for i in value if i >= min_value and i <= max_value}
                relations_dict[key] = value

    for _ in range(3):
        keys = list(relations_dict.keys())
        for i in range(len(keys)):
            for j in range(i+1, len(keys)):
                A, B = keys[i], keys[j]
                valueA, valueB = relations_dict[A], relations_dict[B]
                A_only, B_only, A_and_B = A - B, B - A, A & B

                if len(A_and_B) == 0:
                    continue

                A_only_odd_num = len([1 for p in A_only if utils.minenum_in_M(p, table.shape) == 1])
                A_only_even_num = len(A_only) - A_only_odd_num
                A_only_delta = {i for i in range(-A_only_even_num, A_only_odd_num + 1)}

                B_only_odd_num = len([1 for p in B_only if utils.minenum_in_M(p, table.shape) == 1])
                B_only_even_num = len(B_only) - B_only_odd_num
                B_only_delta = {i for i in range(-B_only_even_num, B_only_odd_num + 1)}

                A_and_B_odd_num = len([1 for p in A_and_B if utils.minenum_in_M(p, table.shape) == 1])
                A_and_B_even_num = len(A_and_B) - A_and_B_odd_num
                A_and_B_delta = {i for i in range(-A_and_B_even_num, A_and_B_odd_num + 1)}

                A_and_B_value = {i-j for i in valueA for j in A_only_delta} & {i-j for i in valueB for j in B_only_delta}
                A_only_value = {i-j for i in valueA for j in A_and_B_value}
                B_only_value = {i-j for i in valueB for j in A_and_B_value}

                A_and_B_value &= A_and_B_delta
                A_only_value &= A_only_delta
                B_only_value &= B_only_delta

                relations_dict[A_and_B] = A_and_B_value
                relations_dict[A_only] = A_only_value
                relations_dict[B_only] = B_only_value
        new_keys = list(relations_dict.keys())
        if len(new_keys) == len(keys):
            break

    results = ConstraintsDict()
    for coordinates, values in relations_dict.items():
        odds = {i for i in coordinates if utils.minenum_in_M(i, table.shape) == 1}
        evens = set(coordinates) - odds

        x1, y1 = len(odds), len(evens)

        # 相当于 x - y = ki，我们去求 x 和 y 范围
        xrange, yrange = set(), set()
        for k in values:
            now_xrange = {i for i in range(max(0, k), min(x1, y1 + k) + 1)}
            now_yrange = {i for i in range(max(0, -k), min(y1, x1 - k) + 1)}
            xrange = xrange | now_xrange
            yrange = yrange | now_yrange

        if len(odds) > 0 and len(xrange) == 0:
            raise ValueError(f'coordinates: {coordinates}; values: {values}')
        if len(evens) > 0 and len(yrange) == 0:
            raise ValueError(f'coordinates: {coordinates}; values: {values}')

        if len(xrange) == 1:
            results[Constraint(odds)] = (list(xrange)[0], list(xrange)[0])
        if len(yrange) == 1:
            results[Constraint(evens)] = (list(yrange)[0], list(yrange)[0])

        if len(xrange) > 1 or len(yrange) > 1:
            minx, maxx = min(xrange), max(xrange)
            miny, maxy = min(yrange), max(yrange)
            results[Constraint(odds)] = (minx, maxx)
            results[Constraint(evens)] = (miny, maxy)

    # print(results)
    return results


def is_legal(table: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 奇数 unknown 坐标、偶数坐标
                unknown_coordinates = [[], []]
                # 奇数坐标、偶数坐标 的已知 mine 数目
                found_mines = [0, 0]

                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    idx = 0 if utils.minenum_in_M(neighbor, table.shape) == 1 else 1
                    if table[neighbor] == 'unknown':
                        unknown_coordinates[idx].append(neighbor)
                    if table[neighbor] == 'mine':
                        found_mines[idx] += 1

                # 本质：|x - y| = n，其中 x1<=x<=x2, y1<=y<=y2
                x1, x2 = found_mines[0], found_mines[0] + len(unknown_coordinates[0])
                y1, y2 = found_mines[1], found_mines[1] + len(unknown_coordinates[1])
                n = int(table[i, j])

                if n < max(0, x1-y2, y1-x2) or n > max(x2-y1, y2-x1):
                    # print(f'coordinate ({i}, {j}) is not legal, n = {n}, x1 = {x1}, x2 = {x2}, y1 = {y1}, y2 = {y2}')
                    # print(f'max(0, x1-y1, x2-y2) = {max(0, x1-y1, x2-y2)}, max(x2-y1, y2-x1) = {max(x2-y1, y2-x1)}')
                    return False
    return True