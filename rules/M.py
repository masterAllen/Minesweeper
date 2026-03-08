'''
M 的规则：每个染色格的雷算两个
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    # 遍历所有格子，创建约束
    '''
    先计算各个格子组合的 SUM，然后根据 SUM 创建约束
    '''
    sum_dict = dict()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                unknown_coordinates = []
                mine_count = int(table[i, j])
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'unknown':
                        unknown_coordinates.append(neighbor)
                    if table[neighbor] == 'mine':
                        mine_count -= utils.minenum_in_M(neighbor, table.shape)

                sum_dict[Constraint(unknown_coordinates)] = mine_count

    # '''
    # 循环，让 SUM 最后收敛
    # '''
    # sum_dict_bak = sum_dict.copy()

    # # 这里和 utils 的 refresh constraints 不同，我们只考虑那些完全包含的部分
    # for A, mineA in sum_dict_bak.items():
    #     for B, mineB in sum_dict_bak.items():
    #         A_only = A - B
    #         B_only = B - A
    #         if len(A_only) == 0 and len(B_only) != 0:
    #             sum_dict[B_only] = mineB-mineA

    '''
    检查 SUM 中的约束
    '''
    results = ConstraintsDict()
    for coordinates, mine_count in sum_dict.items():

        odd_coordinates = []
        even_coordinates = []
        for coordinate in coordinates:
            if utils.minenum_in_M(coordinate, table.shape) == 1:
                odd_coordinates.append(coordinate)
            else:
                even_coordinates.append(coordinate)

        if mine_count < 0:
            raise ValueError(f'mine_count < 0: {mine_count}')
            
        # m * odd +  n * 2 * even = mine_count
        # odd 的个数，最多是 mine_count 个
        # odd 的个数，最少是 (mine_count - 2 * even) 个
        min_odd = max(0, mine_count - 2 * len(even_coordinates))
        max_odd = min(mine_count, len(odd_coordinates))
        # 几个特殊情况：
        # 1. 如果雷的数目是奇数，那么一定有 odd
        # 2. 如果雷的数目是偶数，并且 odd 个数为 1，那么一定不能是 odd
        if mine_count % 2 == 1 and min_odd == 0:
            min_odd = 1
        if mine_count % 2 == 0 and len(odd_coordinates) == 1:
            max_odd = 0
        # print(f'odd_coordinates = {odd_coordinates}, min_odd = {min_odd}, max_odd = {max_odd}, coordinates = {coordinates}, mine_count = {mine_count}')
        results[tuple(odd_coordinates)] = (min_odd, max_odd)

        # even 的个数，最多是 mine_count // 2 个
        # even 的个数，最少是 ceil((mine_count - odd) / 2) 个
        min_even = max(0, math.ceil((mine_count - len(odd_coordinates)) / 2))
        max_even = min(mine_count // 2, len(even_coordinates))
        # print(f'even_coordinates = {even_coordinates}, min_even = {min_even}, max_even = {max_even}, coordinates = {coordinates}, mine_count = {mine_count}')
        results[tuple(even_coordinates)] = (min_even, max_even)

    return results

def is_legal(table: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                found_mines = 0
                found_unknowns = 0
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        found_mines += utils.minenum_in_M(neighbor, table.shape)
                    if table[neighbor] == 'unknown':
                        found_unknowns += utils.minenum_in_M(neighbor, table.shape)

                if int(table[i, j]) < found_mines:
                    print(f'found_mines = {found_mines}, int(table[{i}, {j}]) = {int(table[i, j])}')
                    return False
                if int(table[i, j]) > found_mines + found_unknowns:
                    print(f'found_mines = {found_mines}, found_unknowns = {found_unknowns}, int(table[i, j]) = {int(table[i, j])}')
                    return False
    return True