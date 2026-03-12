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
            directions = [ (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1) ]
            neigbor_coordinates = []
            neigbor_str = ''
            for direction in directions:
                neighbor = (i + direction[0], j + direction[1])
                neigbor_coordinates.append(neighbor)
                # 如果不在表格范围内，当成是非雷
                if neighbor[0] < 0 or neighbor[0] >= table.shape[0] or neighbor[1] < 0 or neighbor[1] >= table.shape[1]:
                    neigbor_str += '0'
                    continue

                if table[neighbor] == 'mine':
                    neigbor_str += '1'
                elif table[neighbor] != 'unknown':
                    neigbor_str += '0'
                else:
                    neigbor_str += '?'
            
            # print(f'center = ({i}, {j}), neigbors = {neigbors}')

            # 根据已知条件 筛选 candidates
            for idx in range(8):
                if neigbor_str[idx] == '1':
                    candidates = [c for c in candidates if c[idx] == '1']
                elif neigbor_str[idx] == '0':
                    candidates = [c for c in candidates if c[idx] == '0']

            if len(candidates) == 0:
                raise ValueError(f'center = ({i}, {j}), neigbors = {neigbor_str}, but no candidates')

            # 筛选可能性
            for idx, coordinate in enumerate(neigbor_coordinates):
                # 检查 candidates 是否对应位置都一样
                if neigbor_str[idx] == '?':
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

            # 1. 总雷数应该是 sum(cell) 个
            found_mines, unknown_count = 0, 0
            for neighbor in utils.get_eight_directions((i, j), table.shape):
                if table[neighbor] == 'mine':
                    found_mines += 1
                if table[neighbor] == 'unknown':
                    unknown_count += 1
            if found_mines > sum(cell):
                print(f'found_mines = {found_mines} > sum(cell) = {sum(cell)}')
                return False
            if found_mines + unknown_count < sum(cell):
                print(f'found_mines + unknown_count = {found_mines} + {unknown_count} < sum(cell) = {sum(cell)}')
                return False

            # 2. 检查各个联通域，和雷数的情况
            candidate_regions = _get_candidate_regions(table, (i, j))

            # 如果是环
            if len(candidate_regions) == 8:
                # 如果里面全是雷，那么跳过处理
                if all(table[coordinate] == 'mine' for coordinate in candidate_regions[0]):
                    return (cell[0] == 8)
                
                # 否则调整一下，第一个一定要是 unknown，末尾是 mine
                idx = 0
                while idx < len(candidate_regions[0]):
                    idx2 = (idx - 1) % len(candidate_regions[0])
                    if table[candidate_regions[0][idx]] == 'unknown':
                        if table[candidate_regions[0][idx2]] == 'mine':
                            break
                    idx += 1
                candidate_regions[0] = candidate_regions[0][idx:] + candidate_regions[0][:idx]

            # 求解最大的连续雷
            max_continuous_mine_num = 0
            for region in candidate_regions:
                mine_regions_idx = [[]]
                for idx in range(0, len(region)):
                    if table[region[idx]] == 'mine':
                        mine_regions_idx[-1].append(idx)
                    else:
                        mine_regions_idx.append([])
                mine_regions_idx = [r for r in mine_regions_idx if len(r) > 0]
                for r in mine_regions_idx:
                    max_continuous_mine_num = max(max_continuous_mine_num, len(r))

            max_cell = max(cell)
            if max_continuous_mine_num > max_cell:
                print(f'max_continuous_mine_num = {max_continuous_mine_num} > max_cell = {max_cell}')
                return False
            
            # 求最小的连续雷（确定的）
            min_continuous_mine_num = 8
            for region in candidate_regions:
                if all(table[coordinate] == 'mine' for coordinate in region):
                    min_continuous_mine_num = min(min_continuous_mine_num, len(region))
            min_cell = min(cell)
            if min_continuous_mine_num < min_cell:
                print(f'min_continuous_mine_num = {min_continuous_mine_num} < min_cell = {min_cell}')
                return False

            # 如果已经确定好了，检查是否符合要求
            for region in candidate_regions:
                if all(table[coordinate] == 'mine' for coordinate in region):
                    # 判断是否有，没有就报错
                    if len(region) not in cell:
                        print(f'center = ({i}, {j}), region = {region}, not in cell = {cell}')
                        return False
                    # 如果有就删除这个，防止有重复，比如 1, 3；而块是 1, 1
                    cell.remove(len(region))

    return True

def _get_candidate_regions(table: np.ndarray, center: tuple) -> list:
    '''
    输入一个坐标，返回周围八个格子的 mine/unknown 的连续区域
    '''
    # 使用通用函数找到所有与 mine 四连通的区域
    neighbors = utils.get_eight_directions(center, table.shape)

    valid_points = set()
    for neighbor in neighbors:
        if table[neighbor] == 'unknown' or table[neighbor] == 'mine':
            valid_points.add(neighbor)

    visited = set()
    candidate_regions = []
    for neighbor in valid_points:
        if neighbor in visited:
            continue
        candidate_regions.append(utils.get_contiguous_regions(table, neighbor, valid_points))
        visited.update(candidate_regions[-1])

    for i, region in enumerate(candidate_regions):
        candidate_regions[i] = utils.resort_contiguous_regions(region)
    return candidate_regions