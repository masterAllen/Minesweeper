'''
[W2]: 最长数墙，线索表示周围八格内的连续雷的最长长度
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint, ConstraintsDictV2

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 1. 先求周围八个格子的 mine/unknown 的连续区域
                candidate_regions = _get_candidate_regions(table, (i, j))
                n = int(table[i, j])

                if n == 0:
                    unknown_coordinates = []
                    for region in candidate_regions:
                        unknown_coordinates.extend([p for p in region if table[p] == 'unknown'])
                    results[Constraint(unknown_coordinates)] = (0, 0)
                    continue

                # 有一个特殊情况，如果是一个环，那么单独处理
                if len(candidate_regions) == 1 and len(candidate_regions[0]) == 8:
                    # 如果里面全是雷，那么跳过处理
                    if all(table[coordinate] == 'mine' for coordinate in candidate_regions[0]):
                        continue

                    # 否则调整一下，第一个一定要是 unknown，末尾是 mine
                    idx = 0
                    while idx < len(candidate_regions[0]):
                        idx2 = (idx - 1) % len(candidate_regions[0])
                        if table[candidate_regions[0][idx]] == 'unknown':
                            if table[candidate_regions[0][idx2]] == 'mine':
                                break
                        idx += 1
                    candidate_regions[0] = candidate_regions[0][idx:] + candidate_regions[0][:idx]

                # 2. 检查各个区域，小于 n 的联通一定是 safe --> 这是错误的推测
                # new_candidate_regions = []
                # for region in candidate_regions:
                #     if len(region) < n:
                #         unknown_coordinates = [p for p in region if table[p] == 'unknown']
                #         results[Constraint(unknown_coordinates)] = (0, 0)
                #     else:
                #         new_candidate_regions.append(region)
                # candidate_regions = new_candidate_regions

                candidate_regions = [region for region in candidate_regions if len(region) >= n]

                # 3. 如果只有一个大于等于 n 的区域，一定是这里面有雷，并且至少 n 个雷
                if len(candidate_regions) == 1 and len(candidate_regions[0]) >= n:
                    now_region = candidate_regions[0]

                    mine_num = sum(1 for p in now_region if table[p] == 'mine')
                    unknown_coordinates = [p for p in now_region if table[p] == 'unknown']
                    results[Constraint(unknown_coordinates)] = (n - mine_num, len(unknown_coordinates))

                    # 两种推测：从开始到最后；从最后到开始；如果这两个有交叉，说明肯定是雷
                    if len(now_region) != 8:
                        test1 = {idx for idx in range(0, n, 1)}
                        test2 = {idx for idx in range(len(now_region)-1, len(now_region)-1-n, -1)}
                        coordinates = list(test1 & test2)
                        for idx in coordinates:
                            if table[now_region[idx]] == 'unknown':
                                results[Constraint([now_region[idx]])] = (1, 1)

                # 4. 更细节的推测
                for region in candidate_regions:
                    # 1. 求解区域内的 mine 的之间的联通情况
                    mine_regions_idx = [[]]
                    for idx in range(0, len(region)):
                        if table[region[idx]] == 'mine':
                            mine_regions_idx[-1].append(idx)
                        else:
                            mine_regions_idx.append([])
                    mine_regions_idx = [r for r in mine_regions_idx if len(r) > 0]

                    # 2. 如果有 n 个雷，那么两边一定是 safe
                    for now_region_idxs in mine_regions_idx:
                        if len(now_region_idxs) == n:
                            idx0 = now_region_idxs[0] - 1
                            idx1 = now_region_idxs[-1] + 1
                            if idx0 >= 0:
                                if table[region[idx0]] == 'unknown':
                                    results[Constraint([region[idx0]])] = (0, 0)

                            if idx1 < len(region):
                                if table[region[idx1]] == 'unknown':
                                    results[Constraint([region[idx1]])] = (0, 0)
                            else:
                                # 如果是环的话，那么 idx1 要特殊处理
                                if len(region) == 8:
                                    if table[region[0]] == 'unknown':
                                        results[Constraint([region[0]])] = (0, 0)

                    # # 3. 求最大的 unknown 区域
                    # max_unknown_len1 = mine_regions_idx[0][0]
                    # max_unknown_len2 = len(region) - mine_regions_idx[-1][-1] - 1
                    # max_unknown_len = max(max_unknown_len1, max_unknown_len2)
                    # for idx in range(1, len(mine_regions_idx)):
                    #     idx0 = mine_regions_idx[idx][0]
                    #     idx1 = mine_regions_idx[idx-1][-1]
                    #     max_unknown_len = max(max_unknown_len, idx1 - idx0 - 1)

                    # # 4. 如果最大 unknown 区域小于 n，那么可以确定哪些是 safe
                    # if max_unknown_len < n:
                    
    return results


def is_legal(table: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 1. 先求周围八个格子的 mine/unknown 的连续区域
                candidate_regions = _get_candidate_regions(table, (i, j))
                n = int(table[i, j])

                if n == 0:
                    for region in candidate_regions:
                        for coordinate in region:
                            if table[coordinate] == 'mine':
                                return False
                    continue

                # print(f'point = ({i}, {j}), candidate_regions = {candidate_regions}')

                # 有一个特殊情况，如果是一个环，那么单独处理
                if len(candidate_regions) == 1 and len(candidate_regions[0]) == 8:
                    # 如果里面全是雷，那么跳过处理
                    if all(table[coordinate] == 'mine' for coordinate in candidate_regions[0]):
                        if n != 8:
                            return False
                        continue

                    # 否则调整一下，第一个一定要是 unknown，末尾是 mine
                    idx = 0
                    while idx < len(candidate_regions[0]):
                        idx2 = (idx - 1) % len(candidate_regions[0])
                        if table[candidate_regions[0][idx]] == 'unknown':
                            if table[candidate_regions[0][idx2]] == 'mine':
                                break
                        idx += 1
                    candidate_regions[0] = candidate_regions[0][idx:] + candidate_regions[0][:idx]

                # 2. 检查各个区域，不考虑小于 n 的联通
                new_candidate_regions = []
                for region in candidate_regions:
                    if len(region) < n:
                        continue
                    new_candidate_regions.append(region)

                # 需要至少有一个
                if len(new_candidate_regions) == 0:
                    return False

                # 3. 连续雷的个数要小于等于 n
                for region in candidate_regions:
                    # 1. 求解区域内的 mine 的之间的联通情况
                    mine_regions_idx = [[]]
                    for idx in range(0, len(region)):
                        if table[region[idx]] == 'mine':
                            mine_regions_idx[-1].append(idx)
                        else:
                            mine_regions_idx.append([])
                    mine_regions_idx = [r for r in mine_regions_idx if len(r) > 0]
                    for mine_region_idxs in mine_regions_idx:
                        if len(mine_region_idxs) > n:
                            print(f'coordinate = ({i}, {j}), region = {candidate_regions}, mine_region_idxs = {mine_region_idxs}')
                            return False

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
    