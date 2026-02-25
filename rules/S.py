'''
[S]:  蛇，雷要组成蛇形
'''
import numpy as np
import utils

def create_constraints(table: np.ndarray, mine_count) -> dict:
    results = dict()

    # 先找出雷的区域
    mine_coordinates = [(i, j) for i in range(table.shape[0]) for j in range(table.shape[1]) if table[i, j] == 'mine']
    # 使用通用函数找到所有与 mine 四连通的区域
    mine_regions = utils.find_all_connected_regions(
        table, mine_coordinates, connected_type=4,
        allowed_cell_types={'mine'}
    )

    # 每个区域，找出首尾
    for mine_region in mine_regions:
        is_snake, head, tail = _is_snake_and_find_endpoints(mine_region, table.shape)
        
        if not is_snake:
            # 如果当前不是蛇形，说明有问题
            raise ValueError(f'蛇形区域 {mine_region} 不是蛇形')

        # 1. 首尾两个点，他们的 unknown 一定要有一个是 mine
        if mine_count > 0:
            unknown_neighbors = set()
            for endpoint in [head, tail]:
                for neigbor in utils.get_four_directions(endpoint, table.shape):
                    if table[neigbor] == 'unknown':
                        unknown_neighbors.add(neigbor)

            # 这些点加入之后，需要检查是否是蛇形
            coordinates = set()
            for point in unknown_neighbors:
                # 也就是加入之后，他们成了端点，也就是邻居数为 1 的点
                neigbor_count = 0
                for neigbor in utils.get_four_directions(point, table.shape):
                    if neigbor in mine_region:
                        neigbor_count += 1
                if neigbor_count == 1:
                    coordinates.add(point)

            if len(coordinates) > 0:
                results[tuple(coordinates)] = (1, len(coordinates))
        
        # 2. 除开首尾的点，他们的邻居不可能是 mine
        for point in mine_region:
            if point not in [head, tail]:
                for neigbor in utils.get_four_directions(point, table.shape):
                    if table[neigbor] == 'unknown':
                        results[tuple([neigbor])] = (0, 0)

    # 2x2 区域中如果三个雷，剩下的一个不可能是雷
    for i in range(table.shape[0]-1):
        for j in range(table.shape[1]-1):
            mine_coordinates = []
            unknown_coordinates = []
            for dx, dy in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                if table[i+dx, j+dy] == 'mine':
                    mine_coordinates.append((i+dx, j+dy))
                if table[i+dx, j+dy] == 'unknown':
                    unknown_coordinates.append((i+dx, j+dy))
            if len(mine_coordinates) == 3:
                results[tuple(unknown_coordinates)] = (0, 0)

    return results

def is_legal(table: np.ndarray, mine_count: int, mine_total: int, weeper) -> bool:
    # 先找出雷的区域
    mine_coordinates = [(i, j) for i in range(table.shape[0]) for j in range(table.shape[1]) if table[i, j] == 'mine']
    if len(mine_coordinates) == 0:
        return True

    # 1. 可联通：使用通用函数找到所有与 mine 四连通的区域；要求区域只能为一个，并且里面的 unknown 数量要满足要求
    connected_regions = utils.find_all_connected_regions(
        table, mine_coordinates, connected_type=4,
        allowed_cell_types={'mine', 'unknown'}
    )
    if len(connected_regions) != 1:
        # print(f'len(connected_regions) = {len(connected_regions)} != 1')
        return False

    # 区域里面的 unknown 也要小于 mine_count
    unknown_count = 0
    for coordinate in connected_regions[0]:
        if table[coordinate[0], coordinate[1]] == 'unknown':
            unknown_count += 1
    if unknown_count < mine_count:
        # print(f'unknown_count = {unknown_count} < mine_count = {mine_count}')
        return False

    # 使用通用函数找到所有与 mine 四连通的区域
    mine_regions = utils.find_all_connected_regions(
        table, mine_coordinates, connected_type=4,
        allowed_cell_types={'mine'}
    )

    # 每个区域，找出首尾
    all_endpoints = []
    for mine_region in mine_regions:
        is_snake, head, tail = _is_snake_and_find_endpoints(mine_region, table.shape)
        all_endpoints.append((head, tail))
        
        if not is_snake:
            # 如果当前不是蛇形，说明有问题
            # print(f'蛇形区域 {mine_region} 不是蛇形')
            return False

    # 判断各个区域的类型，三种：
    # 0: 只有一个端点可以往外走
    # 1: 有两个端点可以延申
    # 2: 特殊情况
    region_types = []
    for endpoint in all_endpoints:
        p = choose_extend_point(endpoint, table)
        if p is not None:
            region_types.append(0)
        elif check_speical_case(endpoint, table):
            region_types.append(2)
        else:
            region_types.append(1)

    # 一个特殊情况：如果有两个区域，都只有一个端点可以往外走，此时雷数的奇偶性是确定的
    def min_steps(p1, p2):
        # 计算 p1 -> p2 要走的步数
        return (p1[0] - p2[0]) + (p1[1] - p2[1]) - 1
    can_extend_idxs = [i for i, region_type in enumerate(region_types) if region_type == 0]
    if len(can_extend_idxs) == 2:
        i, j = can_extend_idxs
        p1 = choose_extend_point(all_endpoints[i], table)
        p2 = choose_extend_point(all_endpoints[j], table)
        if p1 is not None and p2 is not None:
            p1 = all_endpoints[i][0] if p1 == all_endpoints[i][1] else all_endpoints[i][1]
            p2 = all_endpoints[j][0] if p2 == all_endpoints[j][1] else all_endpoints[j][1]
            # 都是奇数，说明两个区域之间的雷一定要是奇数；都是偶数，说明两个区域之间的雷一定要是偶数
            if min_steps(p1, p2) % 2 != mine_total % 2:
                # print(f'min_steps(p1, p2) % 2 != mine_count % 2, p1 = {p1}, p2 = {p2}, mine_count = {mine_count}')
                return False

    # 第二个特殊情况：如果有多个区域，最多只能由两个区域可以里面由一个端点往外走
    can_extend_idxs = [i for i, region_type in enumerate(region_types) if region_type == 0 or region_type == 2]
    if len(all_endpoints) > 2:
        if len(can_extend_idxs) > 2:
            # print(f'len(can_extend_idxs) > 2, can_extend_idxs = {can_extend_idxs}; region_types = {region_types}')
            return False

    # 第三个特殊情况：如果有三个区域，两个区域是确定只能一个端点往外走，那么剩下区域的两个点要能和这两个端点连接上
    def is_connected(point, region):
        for neigbor in utils.get_four_directions(point, table.shape):
            if neigbor in region:
                return True
        return False

    if len(all_endpoints) == 3 and len(can_extend_idxs) == 2:
        p1 = choose_extend_point(all_endpoints[can_extend_idxs[0]], table)
        p2 = choose_extend_point(all_endpoints[can_extend_idxs[1]], table)
        if p1 is None:
            p1 = all_endpoints[can_extend_idxs[0]][0]
        if p2 is None:
            p2 = all_endpoints[can_extend_idxs[1]][0]

        # 计算他们的 BFS 区域
        p1_region = utils.bfs_connected_region(table, [p1], connected_type=4, allowed_cell_types={'unknown'})
        p2_region = utils.bfs_connected_region(table, [p2], connected_type=4, allowed_cell_types={'unknown'})

        # 其他区域，两个端点需要和它们连接上
        for i in range(len(all_endpoints)):
            if i not in can_extend_idxs:
                head, tail = all_endpoints[i]

                is_ok = False
                if is_connected(head, p1_region) and is_connected(tail, p2_region):
                    is_ok = True
                if is_connected(head, p2_region) and is_connected(tail, p1_region):
                    is_ok = True
                if not is_ok:
                    # print(f'is_connecte(head, p1_region) = {is_connected(head, p1_region)}')
                    # print(f'is_connecte(tail, p1_region) = {is_connected(tail, p1_region)}')
                    # print(f'is_connecte(head, p2_region) = {is_connected(head, p2_region)}')
                    # print(f'is_connecte(tail, p2_region) = {is_connected(tail, p2_region)}')
                    # print(f'p1_region = {p1_region}, p2_region = {p2_region}')
                    return False


    # 如果 mine_count 是 0，那么 region 需要一个
    if mine_count == 0:
        if len(mine_regions) != 1:
            # print(f'len(mine_regions) = {len(mine_regions)} != 1')
            return False

    return True
    


def _is_snake_and_find_endpoints(region: set, table_shape: tuple) -> tuple:
    """
    判断一个区域是否是蛇形，如果是则返回首尾两个端点
    
    蛇形的特点：
    1. 每个点最多有 2 个邻居（四连通）
    2. 有且仅有 2 个端点（邻居数为 1）
    3. 其他点都恰好有 2 个邻居
    
    Returns:
        (is_snake, head, tail): 
        - is_snake: bool，是否是蛇形
        - head, tail: 首尾坐标，如果不是蛇形则为 None
    """
    if len(region) == 0:
        return False, None, None
    
    if len(region) == 1:
        # 单个点也算蛇形，首尾相同
        point = list(region)[0]
        return True, point, point
    
    # 统计每个点在区域内的邻居数
    endpoints = []  # 邻居数为 1 的点（端点）
    
    for coord in region:
        neighbors_in_region = []
        for neighbor in utils.get_four_directions(coord, table_shape):
            if neighbor in region:
                neighbors_in_region.append(neighbor)
        
        neighbor_count = len(neighbors_in_region)
        
        # 如果邻居数 > 2，不是蛇形（有分叉）
        if neighbor_count > 2:
            return False, None, None
        
        # 如果邻居数 == 0，不是蛇形（孤立点，但区域 > 1）
        if neighbor_count == 0:
            return False, None, None
        
        # 邻居数 == 1 的是端点
        if neighbor_count == 1:
            endpoints.append(coord)
    
    # 蛇形必须有且仅有 2 个端点
    if len(endpoints) != 2:
        return False, None, None
    
    return True, endpoints[0], endpoints[1]

def check_constraints(constraints: dict) -> bool:
    return True

# 输入两个端点，返回可以往外延申的点；如果两个端点都不是最终蛇形的端点，那么返回 None
def choose_extend_point(points, table: np.ndarray) -> tuple:
    p1, p2 = points

    # 如果是单独一个点，查看是否只有一个邻居是 unknown
    if p1 == p2:
        unknown_count = 0
        for neigbor in utils.get_four_directions(p1, table.shape):
            if table[neigbor] == 'unknown':
                unknown_count += 1
        if unknown_count == 1:
            return p1
        return None

    p1_can_extend = False
    for neigbor in utils.get_four_directions(p1, table.shape):
        if table[neigbor] == 'unknown':
            p1_can_extend = True
            break
    p2_can_extend = False
    for neigbor in utils.get_four_directions(p2, table.shape):
        if table[neigbor] == 'unknown':
            p2_can_extend = True
            break

    if p1_can_extend and p2_can_extend:
        return None
    if p1_can_extend:
        return p1
    if p2_can_extend:
        return p2
    return None

# 判断如下特殊情况，下面的情况一定是蛇的端点
# . x x .
# x * * x
def check_speical_case(points, table: np.ndarray) -> bool:
    def is_unknown(i, j):
        if i < 0 or i >= table.shape[0] or j < 0 or j >= table.shape[1]:
            return True
        return (table[i, j] == 'unknown')

    p1, p2 = points
    if (p1[0] + p1[1]) > (p2[0] + p2[1]):
        p1, p2 = p2, p1

    # . x x .
    # x * * x
    if p1[0] == p2[0] and (p2[1] - p1[1]) == 1:
        count0 = is_unknown(p1[0], p1[1]-1) + is_unknown(p2[0], p2[1]+1)
        count1 = is_unknown(p1[0]-1, p1[1]) + is_unknown(p2[0]-1, p2[1])
        count2 = is_unknown(p1[0]+1, p1[1]) + is_unknown(p2[0]+1, p2[1])

        if count0 == 0:
            if count1 == 0 and count2 == 2:
                return True
            if count1 == 2 and count2 == 0:
                return True
    
    # . x
    # x *
    # x *
    # . x
    if p1[1] == p2[1] and (p2[0] - p1[0]) == 1:
        count0 = is_unknown(p1[0]-1, p1[1]) + is_unknown(p2[0]+1, p2[1])
        count1 = is_unknown(p1[0], p1[1]-1) + is_unknown(p2[0], p2[1]-1)
        count2 = is_unknown(p1[0], p1[1]+1) + is_unknown(p2[0], p2[1]+1)

        if count0 == 0:
            if count1 == 0 and count2 == 2:
                return True
            if count1 == 2 and count2 == 0:
                return True

    return False
