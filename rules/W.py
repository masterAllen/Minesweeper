'''
[W]: 数墙，线索表示周围八格内的连续雷的长度
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint, ConstraintsDictV2
from itertools import permutations

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

    # 算出长度
    group_sizes = sorted(len(g) for g in mine_groups)
    return tuple(group_sizes)

# 以 k 为中心的 8 个格子中的组合情况
def make_combinations() -> dict:
    results = {}
    for i in range(1, 256):
        combinations = circular_groups(i)
        if combinations not in results:
            results[combinations] = []
        results[combinations].append(format(i, '08b'))
    # 加上全是非雷的情况
    results[tuple([0])] = ['00000000']
    return results
W_COMBINATIONS = make_combinations()

def translate_cell(cell: str):
    if 'x' in cell:
        return [int(i) for i in cell.split('x')]
    if cell.isdigit():
        return [int(cell)]
    return None

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            cell = translate_cell(table[i, j])
            if cell is None:
                continue

            # 1. 总雷数应该是 sum(cell) 个
            coordinates = []
            found_mines = 0
            for neighbor in utils.get_eight_directions((i, j), table.shape):
                if table[neighbor] == 'mine':
                    found_mines += 1
                if table[neighbor] == 'unknown':
                    coordinates.append(neighbor)
            mine_count = sum(cell) - found_mines
            results[Constraint(coordinates)] = (mine_count, mine_count)

            # candidates: 所有可能的组合
            cell.sort()
            candidates = W_COMBINATIONS[tuple(cell)]

            # print(f'center = ({i}, {j}), cell = {cell}, candidates = {candidates}')

            # 按照顺时针来
            neighbor_coordinates, neighbor_str = utils.get_eight_coordinates_force(table, (i, j))
            
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
            cell = translate_cell(table[i, j])
            if cell is None:
                continue

            # candidates: 所有可能的组合
            cell.sort()
            candidates = W_COMBINATIONS[tuple(cell)]

            # 按照顺时针来
            neighbor_coordinates, neighbor_str = utils.get_eight_coordinates_force(table, (i, j))
            
            # 根据已知条件 筛选 candidates
            for idx in range(8):
                if neighbor_str[idx] == '1':
                    candidates = [c for c in candidates if c[idx] == '1']
                elif neighbor_str[idx] == '0':
                    candidates = [c for c in candidates if c[idx] == '0']

            if len(candidates) == 0:
                return False
    return True
