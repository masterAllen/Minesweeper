'''
[W2]: 最长数墙，线索表示周围八格内的连续雷的最长长度
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint, ConstraintsDictV2

# 8 个格子，每个格子有 0 或 1 组合，1 表示有雷，0 表示无雷；因此一共有 255 种
# 给出这 8 个格子的组合，计算其中的雷组合情况
def circular_groups(mask):
    n = 8 # 8-bit

    # 传入数字，如 0b1011..，拆分成数组：[1, 0, 1, 1, ...]
    arr = tuple((mask>>i)&1 for i in range(n))

    # 雷的连续段
    mine_groups = [[]]
    for i in range(n):
        if arr[i] == 1:
            # 遇到雷，放进去
            mine_groups[-1].append(i)
        else:
            # 遇到非雷，结束当前连续段
            mine_groups.append([])

    # 首尾看是否可以相连
    if arr[0] == 1 and arr[-1] == 1 and len(mine_groups) > 1:
        first, last = mine_groups[0], mine_groups[-1]

        # 合并 + 替换
        merged = last + first
        mine_groups = [merged] + mine_groups[1:-1]

    # 筛选出雷的连续段
    mine_groups = [group for group in mine_groups if len(group) > 0]

    # 算出最长长度
    max_mine = max(len(g) for g in mine_groups)
    return max_mine

# 以 k 为中心的 8 个格子中的组合情况
def make_combinations() -> dict:
    results = {}
    for i in range(1, 256):
        max_len = circular_groups(i)
        if max_len not in results:
            results[max_len] = []
        results[max_len].append(format(i, '08b'))
    # 加上全是非雷的情况
    results[0] = ['00000000']
    return results
W2_COMBINATIONS = make_combinations()

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 按照顺时针来
                neighbor_coordinates, neighbor_str = utils.get_eight_coordinates_force(table, (i, j))
                
                candidates = W2_COMBINATIONS[int(table[i, j])]
                # 根据已知条件 筛选 candidates
                for idx in range(8):
                    if neighbor_str[idx] == '1':
                        candidates = [c for c in candidates if c[idx] == '1']
                    elif neighbor_str[idx] == '0':
                        candidates = [c for c in candidates if c[idx] == '0']

                if len(candidates) == 0:
                    raise ValueError(f'center = ({i}, {j}), neigbors = {neighbor_str}, but no candidates')

                # 筛选可能性
                for idx, coordinate in enumerate(neighbor_coordinates):
                    # 检查 candidates 是否对应位置都一样
                    if neighbor_str[idx] == '?':
                        c0 = candidates[0][idx]
                        if all(c[idx] == c0 for c in candidates):
                            if c0 == '1':
                                results[Constraint([coordinate])] = (1, 1)
                            if c0 == '0':
                                results[Constraint([coordinate])] = (0, 0)

                    
    return results


def is_legal(table: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 按照顺时针来
                neighbor_coordinates, neighbor_str = utils.get_eight_coordinates_force(table, (i, j))
                
                candidates = W2_COMBINATIONS[int(table[i, j])]
                # 根据已知条件 筛选 candidates
                for idx in range(8):
                    if neighbor_str[idx] == '1':
                        candidates = [c for c in candidates if c[idx] == '1']
                    elif neighbor_str[idx] == '0':
                        candidates = [c for c in candidates if c[idx] == '0']

                if len(candidates) == 0:
                    return False
    return True
