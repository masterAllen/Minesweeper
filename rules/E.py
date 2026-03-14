'''
[E]: 十字，线索表示周围两格范围内的雷数
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict

def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
    '''
    1. 首先对每个格子创建约束
    2. 如果格子和格子之间相邻，其实可以进行扩散
    '''
    # 使用普通 dict 存储中间结果，而不是 ConstraintsDict
    # key: (i, j) 坐标，value: (min, max) 范围
    horizontal_ranges = {}  # 每个格子横向方向的雷数范围
    vertical_ranges = {}    # 每个格子纵向方向的雷数范围

    # 遍历所有格子，创建横向和纵向约束，之所以有这一步，是两个相邻的格子之间可以分享信息
    # 比如 ... 10 5 ...，可以知道 10 的格子水平方向最多只有五个
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit() and 'E' in table_rules[i, j]:
                coordinates, max_values, min_values = get_eyesight_result(table, (i, j))

                n = int(table[i, j])

                # 统计格子的横向和纵向的最大值和最小值（包括自己）
                v_max_value = max_values[0] + max_values[1] + 1
                v_min_value = min_values[0] + min_values[1] + 1
                h_max_value = max_values[2] + max_values[3] + 1
                h_min_value = min_values[2] + min_values[3] + 1

                # print(f'point={(i, j)}, v_max_value={v_max_value}, v_min_value={v_min_value}, h_max_value={h_max_value}, h_min_value={h_min_value}')
                # print(f'coordinates = {coordinates}')

                key = (i, j)

                # 统计 horizontal 方向的范围
                h_min = max(n - v_max_value + 1, 1)
                h_max = min(n - v_min_value + 1, h_max_value + 1)
                horizontal_ranges[key] = _merge_range(horizontal_ranges.get(key), (h_min, h_max))

                # 统计 vertical 方向的范围
                v_min = max(n - h_max_value + 1, 1)
                v_max = min(n - h_min_value + 1, v_max_value + 1)
                vertical_ranges[key] = _merge_range(vertical_ranges.get(key), (v_min, v_max))

                h_min, h_max = horizontal_ranges[key]
                v_min, v_max = vertical_ranges[key]

                # 向四周已知块蔓延
                for idx in range(4):
                    for coordinate in coordinates[idx]:
                        if table[coordinate] == 'unknown':
                            break
                        if 0 <= idx < 2:
                            vertical_ranges[coordinate] = _merge_range(
                                vertical_ranges.get(coordinate), (v_min, v_max))
                        if 2 <= idx < 4:
                            horizontal_ranges[coordinate] = _merge_range(
                                horizontal_ranges.get(coordinate), (h_min, h_max))

    # 再进行一次推导，生成最终的约束
    results = ConstraintsDict()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit() and 'E' in table_rules[i, j]:
                coordinates, max_values, min_values = get_eyesight_result(table, (i, j))

                # 各个方向上的情况，
                # 1. 比如最小值，那么就是其他三个方向取最大值
                # 2. 但是上面我们还推出了这个格子横向纵向的最大值和最小值，所以也可以：
                #   2.1 如最小值，假设是横向，纵向取最大，横向另一个方向也取最大
                #   2.2 如最小值，假设是横向，横向取最小，横向另一个方向取最大

                # 但最后其实可以统一归纳为 2.2 方法，可以想象一下，如果上面求横纵的时候没有用到别的格子信息
                # 比如：第一个选项，三个方向取最大值，那不就是纵向取最大，也就是横向取最小；然后另一个方向取最大吗

                key = (i, j)
                n = int(table[i, j])
                
                # 获取当前格子的横纵范围
                h_min_value, h_max_value = horizontal_ranges.get(key, (1, n))
                v_min_value, v_max_value = vertical_ranges.get(key, (1, n))

                # print(f'horizontal_key = {key}, horizontal_constraints = {horizontal_ranges[key]}')
                # print(f'vertical_key = {key}, vertical_constraints = {vertical_ranges[key]}')

                # 更新横纵方向的情况
                new_h_min = max(n - v_max_value + 1, h_min_value)
                new_h_max = min(n - v_min_value + 1, h_max_value)
                horizontal_ranges[key] = (new_h_min, new_h_max)
                
                new_v_min = max(n - h_max_value + 1, v_min_value)
                new_v_max = min(n - h_min_value + 1, v_max_value)
                vertical_ranges[key] = (new_v_min, new_v_max)

                for idx in range(4):
                    # x 的范围：min = max(0, n-other_max)；max = min(k, n)
                    if idx >= 2:
                        min_value = horizontal_ranges[key][0] - 1 - max_values[5-idx]
                        max_value = horizontal_ranges[key][1] - 1 - min_values[5-idx]
                    else:
                        min_value = vertical_ranges[key][0] - 1 - max_values[1-idx]
                        max_value = vertical_ranges[key][1] - 1 - min_values[1-idx]
                    
                    min_value = max(min_values[idx], min_value)
                    max_value = min(max_values[idx], max_value)

                    # print(f'({i}, {j}), 第 {idx} 个方向，坐标: {coordinates[idx]}, 最小值: {min_value}, 最大值: {max_value}')
                    # print(f'horizontal_ranges = {horizontal_ranges[key]}, vertical_ranges = {vertical_ranges[key]}')

                    # 上面的值是某个方向上整条的最大值最小值
                    # 我们需要的是 unknown 顺序下的最大值最小值
                    # 分为三段：
                    # 1. 第一段是 min_value，这里面的 unknown 一定不是雷
                    # 2. 第二段是 min_value - max_value，这里面的 unknown 一定要有雷
                    # 3. 第三段是 max_value，这里面的 unknown 不一定，无法确定
                    unknown_coordinates = []
                    for coordinate in coordinates[idx][0:min_value]:
                        if table[coordinate] == 'unknown':
                            unknown_coordinates.append(coordinate)
                    if unknown_coordinates:
                        results[Constraint(unknown_coordinates)] = (0, 0)
                    # print(f'---> unknown_coordinates: {unknown_coordinates}, 0, 0')

                    if len(coordinates[idx]) >= (max_value + 1):
                        for coordinate in coordinates[idx][min_value:max_value+1]:
                            if table[coordinate] == 'unknown':
                                unknown_coordinates.append(coordinate)
                        if unknown_coordinates:
                            results[Constraint(unknown_coordinates)] = (1, len(unknown_coordinates))

    return results


def _merge_range(old_range, new_range):
    """合并两个范围，取交集"""
    if old_range is None:
        return new_range
    old_min, old_max = old_range
    new_min, new_max = new_range
    return (max(old_min, new_min), min(old_max, new_max))


def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    # 遍历所有格子，创建约束
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit() and 'E' in table_rules[i, j]:
                # 获取上下左右，四个方向的 unknown 坐标，并且获取他们的最大值
                coordinates, max_values, min_values = get_eyesight_result(table, (i, j))

                # 包括了自己，所以减 1
                n = int(table[i, j]) - 1
                sum_max_value = sum(max_values)
                sum_min_value = sum(min_values)
                if n < sum_min_value or n > sum_max_value:
                    return False
    return True


def get_eyesight_result(table: np.ndarray, center: tuple):
    '''
    统计视野范围内，四个方向的结果（上下左右）
    有哪些坐标，最小值是多少，最大值是多少
    '''
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    coordinates = [[] for _ in range(4)]
    max_values = [0 for _ in range(4)]
    min_values = [0 for _ in range(4)]
    for idx, (dx, dy) in enumerate(directions):
        coord = [center[0], center[1]]
        
        # 第一次遇到未知块，才可以停止 min_value 的累加
        has_meet_non_unknown = False
        while True:
            coord = [coord[0] + dx, coord[1] + dy]
            if coord[0] < 0 or coord[0] >= table.shape[0] or coord[1] < 0 or coord[1] >= table.shape[1]:
                break
            if table[coord[0], coord[1]] == 'mine':
                break
            if table[coord[0], coord[1]] == 'unknown':
                has_meet_non_unknown = True

            coordinates[idx].append((coord[0], coord[1]))
            if not has_meet_non_unknown:
                min_values[idx] += 1
            max_values[idx] += 1

    return coordinates, max_values, min_values
