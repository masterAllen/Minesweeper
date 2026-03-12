'''
[P]: 划分，线索表示周围八格内的连续雷组数
'''
import numpy as np
import math
import utils
from constraint import ConstraintsDict, Constraint, ConstraintsDictV2

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    '''
    第一件事情，还是进行约束，只不过这里的 value 是 cooridnates 可能的连续组雷数
    1. 交集时候，value 也是取交集：
    2. 交集要防止 coordinates 非连续
    '''
    sum_dict = dict()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 1. 先求周围八个格子的 mine/unknown 的连续区域
                candidate_regions = _get_candidate_regions(table, (i, j))

                keys = []
                for region in candidate_regions:
                    # 如果首尾都是雷
                    # TODO: 暂时不考虑那么多吧，直接就看看有没有雷，有雷最小值为 1，没有则最小值是 0
                    mine_num = 0
                    for coordinate in region:
                        if table[coordinate] == 'mine':
                            mine_num += 1

                    # 如果某个区域都是雷，那么不放入后续处理
                    if len(region) == mine_num:
                        continue

                    keys.append(tuple(region))

                # 剩下的总数，因为 Keys 只保存没有塞满雷的联通，所以要减去这些塞满雷的区域
                n = int(table[i, j]) - (len(candidate_regions) - len(keys))
                sum_dict[tuple(keys)] = n

    '''
    进行约束，且只考虑包含的部分
    '''
    keys = list(sum_dict.keys())
    for i in range(len(keys)):
        for j in range(len(keys)):
            if i == j:
                continue

            A, B = keys[i], keys[j]

            is_ok = True
            for region in A:
                if region not in B:
                    is_ok = False
                    break
            if not is_ok:
                continue

            now_key = []
            for region in B:
                if region not in A:
                    now_key.append(region)

            sum_dict[tuple(now_key)] = sum_dict[B] - sum_dict[A]
    

    '''
    开始处理各个约束
    '''
    relations_dict = ConstraintsDictV2()
    for regions, regions_sum in sum_dict.items():
        for region in regions:
            # 算出这几个联通区域的可能值
            #   - 如果没有雷，那么最多可能产生 ceil(n/2) 个区域
            #   - 如果有雷，那么和雷有关，比如三个区域时，* ? ? 最多可以有两种情况，? * ? 最多只能一种情况
            # 最小值，如果有雷，那么最小值为 1，没有雷，那么最小值为 0
            has_mine = any(table[coordinate] == 'mine' for coordinate in region)
            min_value = 1 if has_mine else 0
            # 最大值，开始遍历所有点，依次是雷、无雷...，最后看看数量多少，如果中途遇到雷，那么跳过
            max_value1 = _get_max_continuous_mine_num(table, region)
            max_value2 = _get_max_continuous_mine_num(table, region[::-1])
            value = {i for i in range(min_value, max(max_value1, max_value2)+1)}

            relations_dict[Constraint(region)] = value
        
        # 利用总数进行更新，相当于 k1={..}, k2={..}, k3={..}，并且 k1+k2+..=n
        # 那么 k1 的约束：min_k1 = n - (others max); max_k1 = n - (others min);
        # 剩下的总数，因为 Keys 只保存没有塞满雷的联通，所以要减去这些塞满雷的区域
        n = regions_sum - (len(regions) - len(regions))

        max_sum = sum(max(relations_dict[Constraint(region)]) for region in regions)
        min_sum = sum(min(relations_dict[Constraint(region)]) for region in regions)
        for region in regions:
            value = relations_dict[Constraint(region)]
            others_max = max_sum - max(value)
            others_min = min_sum - min(value)
            new_value = {i for i in value if i >= n - others_max and i <= n - others_min}
            relations_dict[Constraint(region)] = new_value

    results = ConstraintsDict()
    for coordinates, values in relations_dict.items():
        # 要始终注意 values 表示 coordinates 的连续组数
        values = list(values)
        coordinates = utils.resort_contiguous_regions(coordinates)

        # print(coordinates, values)

        # 连续区域中，如果使用 雷、非雷、雷、非雷 这种组合，会有最大的雷数，如果组数正好是这个理论上限
        # 为什么要理论上限才会处理，可以看这个组合：unknown mine mine unknown，此时有四种可能，并且都不重复...
        if len(values) == 1:
            # 去除连续的 mines
            now_coordinates = []
            is_prev_mine = False
            for i in range(0, len(coordinates)):
                if table[coordinates[i]] == 'mine' and is_prev_mine:
                    continue
                now_coordinates.append(coordinates[i])
                is_prev_mine = (table[coordinates[i]] == 'mine')

            # print(coordinates, now_coordinates, values[0])

            # 如果是奇数，那么可以直接判断出来...
            if values[0] == math.ceil(len(now_coordinates)/2) and len(now_coordinates) % 2 == 1:
                # mine, nomine, mine, ... 这样排列
                for idx, coordinate in enumerate(now_coordinates):
                    if table[coordinate] == 'unknown':
                        results[Constraint([coordinate])] = (1, 1) if idx % 2 == 0 else (0, 0)

            # 如果是偶数，就不好办了；如果中间有雷那么可以通过这个雷来确定可能性；如果中间没有雷，那么....
            # 偶数，以四个举例：(* ? * ?) 和 (? * ? *) 和 (* * ? *) 和 (* ? ? *）,太多情况了
            # 只好举几个例子，强行收敛了


        # 如果发现只有一个连续区域，并且连续区域数量是 1，其中如果只有两个雷，那么雷之间肯定都是雷
        if len(values) == 1 and values[0] == 1:
            coordinates = utils.resort_contiguous_regions(coordinates)

            # 如果是 8 个组成的环，那么这个规则就不适用了（他有两条路径）
            if len(coordinates) == 8:
                continue

            # 否则寻找两个雷的坐标，中间必须是雷
            points_idx = [i for i in range(len(coordinates)) if table[coordinates[i]] == 'mine']
            if len(points_idx) == 2:
                for coordinate in coordinates[points_idx[0]:points_idx[1]]:
                    if table[coordinate] == 'unknown':
                        results[Constraint([coordinate])] = (1, 1)
                continue

        # 1. 连续组数为 0，此时 coordinates 没有雷
        # 2. 连续组数 n，此时 coordinates 最少 n 个雷，最多 len+1-n 个雷
        min_mine_count, max_mine_count =  len(coordinates), 0
        for now_value in values:
            if now_value == 0:
                now_min, now_max = 0, 0
            else:
                now_min, now_max = now_value, len(coordinates) + 1 - now_value
            min_mine_count = min(min_mine_count, now_min)
            max_mine_count = max(max_mine_count, now_max)

        # 解析其中的 unkown 和 mine 的坐标
        unknown_coordinates = [p for p in coordinates if table[p] == 'unknown']
        mine_coordinates = [p for p in coordinates if table[p] == 'mine']

        min_mine_count -= len(mine_coordinates)
        max_mine_count -= len(mine_coordinates)
        results[unknown_coordinates] = (min_mine_count, max_mine_count)

    # print('==================================')
    # for keys, values in results.items():
    #     print(keys, values)
    # import time
    # time.sleep(1000)

    return results


def is_legal(table: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                # 1. 先求周围八个格子的 mine/unknown 的连续区域
                candidate_regions = _get_candidate_regions(table, (i, j))

                # 2. 算出这几个联通区域的可能值
                mins, maxs = [], []
                for region in candidate_regions:
                    # 如果首尾都是雷
                    mine_num = 0
                    for coordinate in region:
                        if table[coordinate] == 'mine':
                            mine_num += 1

                    if len(region) == mine_num:
                        continue

                    mins.append(1 if mine_num > 0 else 0)
                    max_value1 = _get_max_continuous_mine_num(table, region)
                    max_value2 = _get_max_continuous_mine_num(table, region[::-1])
                    maxs.append(max(max_value1, max_value2))

                # 检查总数是否符合要求，sum(mins) 和 sum(maxs)
                n = int(table[i, j]) - (len(candidate_regions) - len(mins))
                if n < sum(mins) or n > sum(maxs):
                    # print(f'mins = {mins}, maxs = {maxs}, n = {n}')
                    return False

    return True

def _get_max_continuous_mine_num(table: np.ndarray, region: list) -> int:
    '''
    输入一串连续的 unknown/mine 的区域，返回最大可能连续雷数
    方法：
    从第一个格子就开始标记 有雷、无雷、有雷... 这种组合，最后看看有多少个雷
    '''
    result = 0
    should_mine = True
    for coordinate in region:
        if table[coordinate] == 'unknown':
            should_mine = not should_mine
        else:
            if should_mine:
                should_mine = not should_mine
        # 本次标记为无雷（标记无雷那么翻转之后就应该想要雷），那么组数加一
        if should_mine:
            result += 1

    # 如果最后标记的是雷（标记雷那么翻转之后就应该想要无雷），那么组数加一
    if not should_mine:
        result += 1
    return result

def _get_candidate_regions_v1(table: np.ndarray, center: tuple) -> list:
    '''
    输入一个坐标，返回周围八个格子的 mine/unknown 的连续区域
    '''
    # 1. 先求周围八个格子的 mine/unknown 的连续区域
    neighbors = utils.get_eight_directions(center, table.shape)

    # 先完善 neigbors，如果是边缘地带，其实要把 center 加上去：
    # x c x
    # x x x
    neighbors.append(neighbors[0])
    for i in range(1, len(neighbors)):
        if abs(neighbors[i-1][0] - neighbors[i][0]) + abs(neighbors[i-1][1] - neighbors[i][1]) > 1:
            neighbors.insert(i, center)
            break
    neighbors = neighbors[:-1]

    # 2. 找出八个格子当中，第一个非 mine/unknown
    idx = 0
    while idx < len(neighbors):
        neighbor = neighbors[idx]
        if table[neighbor] != 'mine' and table[neighbor] != 'unknown':
            break
        idx += 1

    # 开始找出连续的区域
    candidate_regions = [[]]
    for k in range(0, len(neighbors)):
        neighbor = neighbors[(idx + k) % len(neighbors)]
        if table[neighbor] == 'unknown' or table[neighbor] == 'mine':
            candidate_regions[-1].append(neighbor)
        else:
            candidate_regions.append([])
    candidate_regions = [region for region in candidate_regions if len(region) > 0]
    return candidate_regions
    
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
    