'''
[W]: 数墙，线索表示周围八格内的连续雷的长度
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint, ConstraintsDictV2
from itertools import permutations

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

            # 2. 检查各个联通域，和雷数的情况
            candidate_regions = _get_candidate_regions(table, (i, j))

            # 如果是环
            if len(candidate_regions) == 8:
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

            # 求解区域内的 mine 的之间的联通情况
            candidate_mine_regions_idx = []
            for region in candidate_regions:
                mine_regions_idx = [[]]
                for idx in range(0, len(region)):
                    if table[region[idx]] == 'mine':
                        mine_regions_idx[-1].append(idx)
                    else:
                        mine_regions_idx.append([])
                mine_regions_idx = [r for r in mine_regions_idx if len(r) > 0]
                candidate_mine_regions_idx.append(mine_regions_idx)

            # 先记录各个联通域中的 mine-联通域的信息，分别是：联通域的索引、mine_region 数组、最小值、最大值
            record_mine_regions = []
            for idx, region in enumerate(candidate_regions):
                mine_regions_idx = candidate_mine_regions_idx[idx]

                for _, mine_region in enumerate(mine_regions_idx):
                    now_info = {
                        'region_idx': idx,
                        'mine_region': mine_region,
                        'min_mine_num': len(mine_region),
                        'max_mine_num': len(region),
                        'combined_cell': None,
                    }
                    record_mine_regions.append(now_info)

            max_unknown_len = 0
            for idx, region in enumerate(candidate_regions):
                mine_regions_idx = candidate_mine_regions_idx[idx]

                start = -2
                for _, mine_region in enumerate(mine_regions_idx):
                    end = mine_region[0]
                    max_unknown_len = max(max_unknown_len, (end - start) - 1 - 2)
                    start = mine_region[-1]
                max_unknown_len = max(max_unknown_len, len(region) + 1 - start - 1 - 2)


            # 遍历三次，挑出确定匹配的
            for _ in range(2):
                for info in record_mine_regions:
                    # 1. 如果已经找到了绑定 cell，那跳过处理
                    if info['combined_cell'] is not None:
                        continue

                    # 2. 否则寻找 cells 中满足要求的选项：[mine_region 长度, 联通域长度]，去重
                    region = candidate_regions[info['region_idx']]
                    mine_regions_idx = info['mine_region']

                    min_mine_num = info['min_mine_num']
                    max_mine_num = info['max_mine_num']

                    possible_nums = list(set([x for x in cell if x >= min_mine_num and x <= max_mine_num]))

                    # 3. 检查 possible 中的 各个 cell，相当于你是我的唯一，但我也要是你的唯一才行
                    possible_nums_filtered = []
                    for possible_num in possible_nums:
                        # 如果某个候选值（比如 1），可以在 unknown 中生成，那说明这个已经不行了
                        if possible_num <= max_unknown_len:
                            possible_nums_filtered = []
                            break

                        possible_info_nums = 0
                        for info2 in record_mine_regions:
                            if info2['combined_cell'] is not None:
                                continue
                            min_mine_num2 = info2['min_mine_num']
                            max_mine_num2 = info2['max_mine_num']
                            if possible_num >= min_mine_num2 and possible_num <= max_mine_num2:
                                possible_info_nums += 1
                        
                        if possible_info_nums == 1:
                            possible_nums_filtered.append(possible_num)

                    # 4. 如果发现两人一对一，那么绑定...
                    if len(possible_nums_filtered) == 1:
                        cell.remove(possible_nums_filtered[0])
                        info['combined_cell'] = possible_nums_filtered[0]

            # 各个连通域可以用于分配的数量，后面会用到
            candidate_regions_leftnums = [len(region) for region in candidate_regions]

            # 1. 进行处理，如果匹配到唯一，如果个数恰好相等，那么可以确定范围
            for info in record_mine_regions:
                if info['combined_cell'] is None:
                    continue

                region = candidate_regions[info['region_idx']]
                mine_region = info['mine_region']
                mine_num = info['combined_cell']

                # 有 mine_num+1 个用于给分配这个 cell，所以要减去
                candidate_regions_leftnums[info['region_idx']] -= (mine_num + 1)

                if len(mine_region) == mine_num:
                    # 如果 mine 长度等于 mine_num，两边为 safe
                    idx0 = mine_region[0] - 1
                    idx1 = mine_region[-1] + 1
                    if len(region) == 8:
                        idx0 = idx0 % 8
                        idx1 = idx1 % 8

                    if idx0 >= 0:
                        if table[region[idx0]] == 'unknown':
                            results[Constraint([region[idx0]])] = (0, 0)
                    if idx1 < len(region):
                        if table[region[idx1]] == 'unknown':
                            results[Constraint([region[idx1]])] = (0, 0)

                else:
                    # 如果 mine 长度小于 mine_num，那么需要查看后面的区域
                    idxs = []
                    idxs.extend([mine_region[0] - k for k in range(1, mine_num - len(mine_region) + 1)])
                    idxs.extend([mine_region[-1] + k for k in range(1, mine_num - len(mine_region) + 1)])
                    if len(region) == 8:
                        idxs = [k % 8 for k in idxs]

                    # print(f'({i}, {j}): idxs = {idxs}, region={region}, mine_num={mine_num}, mine_region={mine_region}')

                    unknown_coordinates = []
                    for idx in idxs:
                        if idx >= 0 and idx < len(region) and table[region[idx]] == 'unknown':
                            unknown_coordinates.append(region[idx])

                    need_mine_count = mine_num - len(mine_region)
                    results[Constraint(unknown_coordinates)] = (need_mine_count, len(unknown_coordinates))

            # 2. 对剩下的那些 cell 进行处理，看看他们有可能在哪些 **联通域** 中
            # 要求：必须明确，每一个 cell 都要有唯一对应的联通域，否则这个就不进行处理

            # print(f'({i}, {j}): cell = {cell}, candidate_regions_leftnums = {candidate_regions_leftnums}')

            # 连通域中的可能 cells
            candidate_region_possible_cells = [[] for _ in range(len(candidate_regions))]
            is_ok = True
            for num in cell:
                ok_idxs = []
                for idx, region in enumerate(candidate_regions):
                    if num <= candidate_regions_leftnums[idx]:
                        ok_idxs.append(idx)

                if len(ok_idxs) == 1:
                    candidate_region_possible_cells[ok_idxs[0]].append(num)
                if len(ok_idxs) > 1:
                    is_ok = False
                    break

            if is_ok:
                for ridx, region in enumerate(candidate_regions):
                    possible_num = candidate_region_possible_cells[ridx]
                    mine_regions_idx = candidate_mine_regions_idx[ridx]
                    possible_num.sort()

                    # 比如 1,2 要在一个区域，那一定要有四个格子才行（中间要隔离）
                    if len(region) < sum(possible_num) + len(possible_num) - 1:
                        # print(f'center = ({i}, {j}), region = {region}, possible_num = {possible_num}')
                        return False

                    # candidates: 所有可能的组合

                    candidates = []
                    if len(possible_num) == 1:
                        n = possible_num[0]
                        # 如果联通只有一个选择: xx **** xxx
                        for a in range(0, len(region)-n+1):
                            b = len(region) - a - n
                            candidate = ['question'] * a + ['mine'] * n + ['question'] * b
                            candidates.append(candidate)
                    
                    if len(possible_num) == 2:
                        n1, n2 = possible_num
                        # . . . *** . . **** . .
                        #   a   n1   c   n2   b
                        # a>=0, b>=0, c>=1
                        for g1, g2 in set(permutations([n1, n2])):
                            remain = len(region) - g1 - g2
                            for a in range(remain+1):
                                for c in range(1, remain-a+1):
                                    b = remain - a - c
                                    candidate = ['question'] * a + ['mine'] * g1 + ['question'] * c + ['mine'] * g2 + ['question'] * b
                                    candidates.append(candidate)
                    
                    if len(possible_num) == 3:
                        n1, n2, n3 = possible_num
                        for g1, g2, g3 in set(permutations([n1, n2, n3])):
                            remain = len(region) - g1 - g2 - g3
                            for a in range(remain+1):
                                for c1 in range(1, remain-a):
                                    for c2 in range(1, remain-a-c1+1):
                                        b = remain - a - c
                                        candidate = ['question'] * a + ['mine'] * g1 + ['question'] * c1 + ['mine'] * g2 + ['question'] * c2 + ['mine'] * g3 + ['question'] * b
                                        candidates.append(candidate)

                    # 根据已知条件 筛选 candidates
                    for idx, coordinate in enumerate(region):
                        if table[coordinate] == 'mine':
                            candidates = [c for c in candidates if c[idx] == 'mine']

                    # 筛选出可能的选择
                    for idx, coordinate in enumerate(region):
                        # 检查 candidates 是否对应位置都一样
                        if table[coordinate] == 'unknown':
                            c0 = candidates[0][idx]
                            if all(c[idx] == c0 for c in candidates):
                                if c0 == 'mine':
                                    results[Constraint([coordinate])] = (1, 1)
                                else:
                                    results[Constraint([coordinate])] = (0, 0)

                    # 2.1 如果这个联通只有一个选择，那么把他的雷全部连起来
                    if len(possible_num) == 1:
                        print(f'({i}, {j}): region = {region}, possible_num = {possible_num}')
                        mine_num = possible_num[0]
                        if len(region) != 8 and len(mine_regions_idx) > 0:
                            idx0 = mine_regions_idx[0][0]
                            idx1 = mine_regions_idx[-1][-1]

                            while idx0 <= idx1:
                                if table[region[idx0]] == 'unknown':
                                    results[Constraint([region[idx0]])] = (1, 1)
                                idx0 += 1

                            # 连接 idx0 - idx1 之后，可以确定雷的范围
                            idxs = []
                            idx0 = mine_regions_idx[0][0]
                            idx1 = mine_regions_idx[-1][-1]
                            left_num = mine_num - (idx1 - idx0 + 1)
                            idxs.extend([idx0 - k for k in range(1, left_num + 1)])
                            idxs.extend([idx1 + k for k in range(1, left_num + 1)])
                            unknown_coordinates = []
                            for idx in idxs:
                                if idx >= 0 and idx < len(region) and table[region[idx]] == 'unknown':
                                    unknown_coordinates.append(region[idx])
                            results[Constraint(unknown_coordinates)] = (left_num, len(unknown_coordinates))

                        if len(region) != 8 and len(mine_regions_idx) == 0:
                            # 如果没有雷，但是连通域长度可以确定是 min_num
                            if len(region) == mine_num:
                                unknown_coordinates = [p for p in region if table[p] == 'unknown']
                                results[Constraint(unknown_coordinates)] = (len(unknown_coordinates), len(unknown_coordinates))

                    # 2.2 如果是 1xn，并且联通宽度是 (n+1)+1，那么两边一定是雷
                    if len(possible_num) == 2 and possible_num[0] == 1:
                        if len(region) == (possible_num[1] + 2):
                            print(f'region = {region}, possible_num = {possible_num}')
                            # 两边一定是雷
                            if table[region[0]] == 'unknown':
                                results[Constraint([region[0]])] = (1, 1)
                            if table[region[-1]] == 'unknown':
                                results[Constraint([region[-1]])] = (1, 1)

                            # # 中间一定是 safe（如果长度是偶数）
                            # if len(region) % 2 == 0:
                            #     idx = len(region) // 2
                            #     if table[region[idx]] == 'unknown':
                            #         results[Constraint([region[idx]])] = (0, 0)
                        
                    # 2.3 如果连通域中存在最大的 cell，那他两边一定是 safe
                    if len(mine_regions_idx) > 0 and len(possible_num) > 0:
                        mine_regions_idx.sort(key=lambda x: len(x))
                        mine_region = mine_regions_idx[-1]
                        if len(mine_region) == possible_num[-1]:
                            # 如果 mine 长度等于 mine_num，两边为 safe
                            idx0 = mine_region[0] - 1
                            idx1 = mine_region[-1] + 1
                            if len(region) == 8:
                                idx0 = idx0 % 8
                                idx1 = idx1 % 8

                            if idx0 >= 0:
                                if table[region[idx0]] == 'unknown':
                                    results[Constraint([region[idx0]])] = (0, 0)
                            if idx1 < len(region):
                                if table[region[idx1]] == 'unknown':
                                    results[Constraint([region[idx1]])] = (0, 0)


            # 3. 进行处理，如果发现 cell 已经被删除干净了，那么那些没有雷的联通区域，一定没有雷
            if len(cell) == 0:
                for idx, region in enumerate(candidate_regions):
                    region = candidate_regions[idx]
                    mine_regions_idx = candidate_mine_regions_idx[idx]

                    if len(mine_regions_idx) == 0:
                        coordinates = [p for p in region if table[p] == 'unknown']
                        results[Constraint(coordinates)] = (0, 0)
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
    