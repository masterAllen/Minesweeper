'''
[L]: 误差，所有线索比真实值大一或减一
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict, ConstraintsDictV2

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    '''
    TODO: 需要和 [M] 类似，while 循环创建约束，这里可以直接用 集合来做了
    '''
    count_dict = ConstraintsDictV2()
    # 遍历所有格子，创建约束
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():

                coordinates = []
                found_mines = 0
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        found_mines += 1
                    if table[neighbor] == 'unknown':
                        coordinates.append(neighbor)
                mine_count = int(table[i, j]) - found_mines

                if len(coordinates) == 0:
                    continue

                # 只可能是 n-1 和 n+1
                if len(coordinates) < mine_count + 1:
                    count_dict[tuple(coordinates)] = {mine_count - 1}
                else:
                    if mine_count == 0:
                        count_dict[tuple(coordinates)] = {1}
                    else:
                        count_dict[tuple(coordinates)] = {mine_count - 1, mine_count + 1}

    # 为了便于简洁，我们直接迭代三次；而且每次只是对存在子集关系才更新；并且没有遇到过这个 key 才会更新
    for _ in range(3):
        count_dict_bak = count_dict.copy()
        for A, A_counts in count_dict_bak.items():
            setA = set(A)
            for B, B_counts in count_dict_bak.items():
                setB = set(B)
                key = Constraint(setB - setA)

                # 只有 A 是 B 的子集，并且没有遇到过才会更新
                if setA < setB and key not in count_dict:
                    set_now = set()
                    for A_count in A_counts:
                        for B_count in B_counts:
                            if 0 <= B_count - A_count <= len(key):
                                set_now.add(B_count - A_count)

                    count_dict[key] = set_now
    
    for coordinates, set_counts in count_dict.items():
        if len(set_counts) == 1:
            results[Constraint(coordinates)] = (list(set_counts)[0], list(set_counts)[0])
        else:
            results[Constraint(coordinates)] = (min(set_counts), max(set_counts))
    
    return results

def is_legal(table: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                found_mines = 0
                found_unknowns = 0
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        found_mines += 1
                    if table[neighbor] == 'unknown':
                        found_unknowns += 1

                if int(table[i, j]) + 1 < found_mines:
                    return False
                if int(table[i, j]) - 1 > found_mines + found_unknowns:
                    return False
    return True