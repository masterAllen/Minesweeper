'''
[E]: 十字，线索表示周围两格范围内的雷数
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    '''
    1. 首先对每个格子创建约束
    2. 如果格子和格子之间相邻，其实可以进行扩散
    '''
    horizontal_constraints = ConstraintsDict()
    vertical_constraints = ConstraintsDict()

    # 遍历所有格子，创建横向和纵向约束
    # 之所以有这一步，是两个相邻的格子之间可以分享信息，比如 ... 10 5 ...，可以知道 10 的格子水平方向最多只有五个，这个信息单独看是看不到的
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                coordinates, max_values, min_values = get_eyesight_result(table, (i, j))

                n = int(table[i, j])

                # 统计格子的横向和纵向的最大值和最小值（包括自己）
                v_max_value = max_values[0] + max_values[1] + 1
                v_min_value = min_values[0] + min_values[1] + 1
                h_max_value = max_values[2] + max_values[3] + 1
                h_min_value = min_values[2] + min_values[3] + 1

                # print(f'point={(i, j)}, v_max_value={v_max_value}, v_min_value={v_min_value}, h_max_value={h_max_value}, h_min_value={h_min_value}')
                # print(f'coordinates = {coordinates}')

                # 这里的 key 是以这个坐标为中心，横纵方向的范围；
                # 为什么要乘以一个 table.shape[0]，因为 ConstraintsDict 内部会自动调整 max 小于等于 len(key)
                # 如果我们只传入这个坐标，那么 max 最多就为 1 了
                key = Constraint([(i, j) for _ in range(table.shape[0])])

                # 统计 horizontal 方向的 key，注意这里是包含已知格子的
                horizontal_constraints[key] = (n-v_max_value+1, n-v_min_value+1)
                horizontal_constraints[key] = (1, h_max_value+1)

                vertical_constraints[key] = (n-h_max_value+1, n-h_min_value+1)
                vertical_constraints[key] = (1, v_max_value+1)

                h_min, h_max = horizontal_constraints[key]
                v_min, v_max = vertical_constraints[key]

                # 向四周已知块蔓延
                for idx in range(4):
                    for coordinate in coordinates[idx]:
                        if table[coordinate] == 'unknown':
                            break
                        now_key = Constraint([coordinate for _ in range(table.shape[0])])
                        if 0 <= idx < 2:
                            vertical_constraints[now_key] = (v_min, v_max)
                        if 2 <= idx < 4:
                            horizontal_constraints[now_key] = (h_min, h_max)

    # 再进行一次...
    results = ConstraintsDict()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
                coordinates, max_values, min_values = get_eyesight_result(table, (i, j))

                # 各个方向上的情况，
                # 1. 比如最小值，那么就是其他三个方向取最大值
                # 2. 但是上面我们还推出了这个格子横向纵向的最大值和最小值，所以也可以：
                #   2.1 如最小值，假设是横向，纵向取最大，横向另一个方向也取最大
                #   2.2 如最小值，假设是横向，横向取最小，横向另一个方向取最大

                # 但最后其实可以统一归纳为 2.2 方法，可以想象一下，如果上面求横纵的时候没有用到别的格子信息
                # 比如：第一个选项，三个方向取最大值，那不就是纵向取最大，也就是横向取最小；然后另一个方向取最大吗

                key = Constraint([(i, j) for _ in range(table.shape[0])])

                # print(f'center = {(i, j)}, max_values = {max_values}, min_values = {min_values}')

                # 更新一下横纵方向的情况
                n = int(table[i, j])
                h_min_value, h_max_value = horizontal_constraints[key]
                v_min_value, v_max_value = vertical_constraints[key]

                # print(f'horizontal_key = {key}, horizontal_constraints = {horizontal_constraints[key]}')
                # print(f'vertical_key = {key}, vertical_constraints = {vertical_constraints[key]}')
                horizontal_constraints[key] = (n - v_max_value + 1, n - v_min_value + 1)
                vertical_constraints[key] = (n - h_max_value + 1, n - h_min_value + 1)

                for idx in range(4):
                    # x 的范围：min = max(0, n-other_max)；max = min(k, n)
                    if idx >= 2:
                        min_value = horizontal_constraints[key][0] - 1 - max_values[5-idx]
                        max_value = horizontal_constraints[key][1] - 1 - min_values[5-idx]
                    else:
                        min_value = vertical_constraints[key][0] - 1 - max_values[1-idx]
                        max_value = vertical_constraints[key][1] - 1 - min_values[1-idx]
                    
                    min_value = max(min_values[idx], min_value)
                    max_value = min(max_values[idx], max_value)

                    # print(f'({i}, {j}), 第 {idx} 个方向，坐标: {coordinates[idx]}, 最小值: {min_value}, 最大值: {max_value}')
                    # print(f'horizontal_constraints = {horizontal_constraints[key]}, vertical_constraints = {vertical_constraints[key]}')

                    # 上面的值是某个方向上整条的最大值最小值，即 now --> [? ? ? x x ? x *]
                    # 我们需要的是 unknown 顺序下的最大值最小值，即其中的 x 集合
                    # 所以应该分为三段：[...] [...] [...]
                    # 1. 第一段是 min_value，这里面的 unknown 一定不是雷
                    # 2. 第二段是 min_value - max_value，这里面的 unknown 一定要有雷
                    # 3. 第三段是 max_value，这里面的 unknown 不一定，无法确定
                    unknown_coordinates = []
                    for coordinate in coordinates[idx][0:min_value]:
                        if table[coordinate] == 'unknown':
                            unknown_coordinates.append(coordinate)
                    results[Constraint(unknown_coordinates)] = (0, 0)
                    # print(f'---> unknown_coordinates: {unknown_coordinates}, 0, 0')

                    if len(coordinates[idx]) >= (max_value + 1):
                        for coordinate in coordinates[idx][min_value:max_value+1]:
                            if table[coordinate] == 'unknown':
                                unknown_coordinates.append(coordinate)
                        results[Constraint(unknown_coordinates)] = (1, len(unknown_coordinates))

    
    return results

def is_legal(table: np.ndarray) -> bool:
    # 遍历所有格子，创建约束
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():
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