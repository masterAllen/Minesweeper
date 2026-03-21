import numpy as np
from constraint import Constraint, ConstraintsDict

def get_eight_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回八连通的坐标：上下左右 + 四个对角线
    """
    # directions = [
    #     (-1, -1), (-1, 0), (-1, 1),  # 上左、上、上右
    #     (0, -1),           (0, 1),    # 左、右
    #     (1, -1),  (1, 0),  (1, 1)     # 下左、下、下右
    # ]

    # 按照顺时针来
    directions = [
        (-1, -1), (-1, 0), (-1, 1), (0, 1), 
        (1, 1), (1, 0), (1, -1), (0, -1)
    ]

    results = []
    for dx, dy in directions:
        coord = (coordinate[0] + dx, coordinate[1] + dy)
        if coord[0] < 0 or coord[0] >= shape[0] or coord[1] < 0 or coord[1] >= shape[1]:
            continue
        results.append(coord)
    return results

def get_four_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回四个方向的坐标：上下左右
    """
    directions = [
        (-1, 0), (0, 1), (1, 0), (0, -1)    # 左、右
    ]
    results = []
    for dx, dy in directions:
        coord = (coordinate[0] + dx, coordinate[1] + dy)
        if coord[0] < 0 or coord[0] >= shape[0] or coord[1] < 0 or coord[1] >= shape[1]:
            continue
        results.append(coord)
    return results

def get_diagonal_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回四个对角线的坐标：左上、右上、左下、右下
    """
    directions = [
        (-1, -1), (-1, 1), (1, -1), (1, 1)
    ]
    results = []
    for dx, dy in directions:
        coord = (coordinate[0] + dx, coordinate[1] + dy)
        if coord[0] < 0 or coord[0] >= shape[0] or coord[1] < 0 or coord[1] >= shape[1]:
            continue
        results.append(coord)
    return results

def get_knight_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回马步的坐标：两个方向的组合
    """
    directions = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)
    ]
    results = []
    for dx, dy in directions:
        coord = (coordinate[0] + dx, coordinate[1] + dy)
        if coord[0] < 0 or coord[0] >= shape[0] or coord[1] < 0 or coord[1] >= shape[1]:
            continue
        results.append(coord)
    return results

def get_cross2_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回十字的坐标：周围两格十字
    """
    directions = [
        (-2, 0), (-1, 0), (1, 0), (2, 0), 
        (0, -2), (0, -1), (0, 1), (0, 2),
    ]
    results = []
    for dx, dy in directions:
        coord = (coordinate[0] + dx, coordinate[1] + dy)
        if coord[0] < 0 or coord[0] >= shape[0] or coord[1] < 0 or coord[1] >= shape[1]:
            continue
        results.append(coord)
    return results

def get_cross1_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回小十字的坐标：周围一格十字
    """
    directions = [
        (-1, 0), (1, 0), (0, -1), (0, 1)
    ]
    results = []
    for dx, dy in directions:
        coord = (coordinate[0] + dx, coordinate[1] + dy)
        if coord[0] < 0 or coord[0] >= shape[0] or coord[1] < 0 or coord[1] >= shape[1]:
            continue
        results.append(coord)
    return results

def bfs_connected_region(table: np.ndarray, start_coords: list, connected_type: int, cell_types: set, types_is_allowed: bool = True) -> set:
    """
    使用 BFS 找到从起始坐标开始的四/八连通区域
    
    Args:
        table: 表格
        start_coords: 起始坐标列表（可以是单个坐标的列表）
        connected_type: 4 - 四连通，8 - 八连通
        cell_types: 允许通过的格子类型集合，例如 {'mine', 'unknown'}
        types_is_allowed: 是否允许通过 cell_types 中的类型，True - 允许，False - 不允许
    
    Returns:
        连通区域的坐标集合
    """
    if len(start_coords) == 0:
        return set()
    
    connected_region = set()
    queue = start_coords.copy()
    
    for coord in start_coords:
        connected_region.add(coord)
    
    while queue:
        current = queue.pop(0)
        
        # 检查八个方向的邻居
        if connected_type == 8:
            neighbors = get_eight_directions(current, table.shape)
        elif connected_type == 4:
            neighbors = get_four_directions(current, table.shape)

        for neighbor in neighbors:
            # 如果已经访问过，跳过
            if neighbor in connected_region:
                continue
            
            # 判断是否可以访问：检查格子类型是否在允许的集合中
            cell_value = table[neighbor[0], neighbor[1]]
            if types_is_allowed:
                if cell_value in cell_types:
                    connected_region.add(neighbor)
                    queue.append(neighbor)
            else:
                if cell_value not in cell_types:
                    connected_region.add(neighbor)
                    queue.append(neighbor)
    
    return connected_region

def find_all_connected_regions(table: np.ndarray, target_coords: list, connected_type: int, cell_types: set, types_is_allowed: bool = True) -> list:
    """
    找到所有分离的连通区域
    
    Args:
        table: 全局表格
        target_coords: 目标坐标列表（例如所有 mine 的坐标）
        cell_types: 允许通过的格子类型集合，例如 {'mine'} 或 {'mine', 'unknown'}
    
    Returns:
        连通区域列表，每个元素是一个坐标集合
    """
    if len(target_coords) == 0:
        return []
    
    visited = set()
    connected_regions = []
    
    for start_coord in target_coords:
        if start_coord in visited:
            continue
        
        # 找到从当前坐标开始的连通区域
        connected_region = bfs_connected_region(
            table, [start_coord], connected_type,
            cell_types=cell_types,
            types_is_allowed=types_is_allowed
        )
        
        # 只保留目标坐标（例如只保留 mine）
        if len(connected_region) > 0:
            connected_regions.append(connected_region)
            visited.update(connected_region)
    
    return connected_regions


def get_cost(table: np.ndarray, point1: tuple, point2: tuple, connected_type: int = 4) -> int:
    """
    计算 point1 -> point2 的最短步数，中间只能经过 unknown，用 BFS 计算
    
    Args:
        table: 表格
        point1: 起点坐标
        point2: 终点坐标
        connected_type: 4 - 四连通，8 - 八连通
    
    Returns:
        最短步数，如果无法到达返回 -1
    """
    if point1 == point2:
        return 0
    
    # BFS 求最短路径
    queue = [(point1, 0)]  # (坐标, 步数)
    visited = {point1}
    
    while queue:
        current, steps = queue.pop(0)
        
        # 获取邻居
        if connected_type == 8:
            neighbors = get_eight_directions(current, table.shape)
        else:
            neighbors = get_four_directions(current, table.shape)
        
        for neighbor in neighbors:
            if neighbor in visited:
                continue
            
            # 到达终点
            if neighbor == point2:
                return steps + 1
            
            # 只能经过 unknown
            if table[neighbor[0], neighbor[1]] == 'unknown':
                visited.add(neighbor)
                queue.append((neighbor, steps + 1))
    
    # 无法到达
    return -1

def minenum_in_M(coordinate: tuple[int, int], shape: tuple[int, int]) -> int:
    """
    计算 M 规则下，某个坐标的雷数
    """
    if (coordinate[0] + coordinate[1]) % 2 == 0:
        return 1
    return 2


def refresh_constraints(constraints: ConstraintsDict, new_constraints: ConstraintsDict) -> ConstraintsDict:

    constraints_bak = constraints.copy()

    # 下面的代码相当于是双重循环，循环 A 和 B，去查看他们能否生成新的限制
    # 为了优化性能，进行了反向索引，具体可以看 docs/performance_optimization.md
    
    # 优化：建立坐标到约束的反向索引，避免遍历所有约束对
    coord_to_constraints = {}  # 坐标 -> 包含该坐标的约束集合
    for A in constraints_bak.keys():
        for coord in A.coordinates:
            if coord not in coord_to_constraints:
                coord_to_constraints[coord] = set()
            coord_to_constraints[coord].add(A)
    
    # 记录已处理的约束对，避免重复处理
    processed_pairs = set()
    
    for B, (minB, maxB) in new_constraints.items():
        # 找到所有可能与 B 有交集的约束 A
        candidate_As = set()
        for coord in B.coordinates:
            if coord in coord_to_constraints:
                candidate_As.update(coord_to_constraints[coord])
        
        for A in candidate_As:
            # 避免重复处理同一对约束
            pair_key = (id(A), id(B)) if id(A) < id(B) else (id(B), id(A))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)
            
            minA, maxA = constraints_bak[A]
            
            # 计算交集和差集
            A_and_B = A & B
            if len(A_and_B) == 0:
                continue
            
            A_only = A - B
            B_only = B - A

            # A_and_B 范围
            z_min = max(0, minA - len(A_only), minB - len(B_only))
            z_max = min(maxA, maxB, len(A_and_B))

            try:
                constraints[A_and_B] = (z_min, z_max)
            except:
                print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                print(f'A_and_B: {A_and_B}, z_min: {z_min}, z_max: {z_max}')
                raise ValueError(f'z_min > z_max: {z_min} > {z_max}')

            # A_only, B_only 范围
            x_min = max(0, minA - z_max)
            x_max = min(len(A_only), maxA - z_min)

            try:
                constraints[A_only] = (x_min, x_max)
            except:
                raise ValueError(f'x_min > x_max: {x_min} > {x_max}')

            y_min = max(0, minB - z_max)
            y_max = min(len(B_only), maxB - z_min)

            try:
                constraints[B_only] = (y_min, y_max)
            except:
                raise ValueError(f'y_min > y_max: {y_min} > {y_max}')
    
    # 找出新增的 constraints
    return_new_constraints = ConstraintsDict()
    for coordinates, (min_mine_count, max_mine_count) in constraints.items():
        if coordinates not in constraints_bak:
            return_new_constraints[coordinates] = (min_mine_count, max_mine_count)
        else:
            old_min, old_max = constraints_bak[coordinates]
            if old_min != min_mine_count or old_max != max_mine_count:
                return_new_constraints[coordinates] = (min_mine_count, max_mine_count)

    return return_new_constraints


def get_contiguous_regions(table: np.ndarray, start_point: tuple, valid_points: set()) -> set:
    """
    使用 BFS 找到从 start_point 开始的连续区域
    其中区域只能是某个点为中心的八个格子，所以传入 valid_points 表示这八个格子
    """
    connected_region = set()
    queue = [start_point]
    
    connected_region.add(start_point)
    
    while queue:
        current = queue.pop(0)
        neighbors = get_four_directions(current, table.shape)
        for neighbor in neighbors:
            if neighbor in valid_points and neighbor not in connected_region:
                connected_region.add(neighbor)
                queue.append(neighbor)
    
    return connected_region

def resort_contiguous_regions(contiguous_regions: set) -> list:
    '''
    输入一组四联通的坐标，返回一个头部到另一个头部的列表
    '''
    if len(contiguous_regions) == 0:
        return []
    if len(contiguous_regions) == 1:
        return list(contiguous_regions)
    
    # 四连通方向
    directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    
    # 建立邻接关系：每个点在集合内的邻居
    neighbors_map = {}
    for coord in contiguous_regions:
        neighbors_map[coord] = []
        for dx, dy in directions:
            neighbor = (coord[0] + dx, coord[1] + dy)
            if neighbor in contiguous_regions:
                neighbors_map[coord].append(neighbor)
    
    # 找到端点（只有一个邻居的点）
    start = None
    for coord, neighbors in neighbors_map.items():
        if len(neighbors) == 1:
            start = coord
            break
    
    # 如果没有端点，说明是环形，任选一个起点
    if start is None:
        start = next(iter(contiguous_regions))
    
    # 从起点开始遍历，按顺序收集
    result = [start]
    visited = {start}
    
    while len(result) < len(contiguous_regions):
        current = result[-1]
        for neighbor in neighbors_map[current]:
            if neighbor not in visited:
                result.append(neighbor)
                visited.add(neighbor)
                break
    
    return result

def hash_table(table: np.ndarray) -> str:
    """
    将 table 转换为哈希值
    """
    import hashlib
    return hashlib.md5(table.tobytes()).hexdigest()

def get_mine_coordinates(table: np.ndarray) -> tuple[tuple[int, int]]:
    """
    获取表格中所有标记为 mine 的格子的坐标
    """
    coords = np.argwhere(table == 'mine')
    coords = tuple((int(coord[0]), int(coord[1])) for coord in coords)
    return coords

def get_unknown_coordinates(table: np.ndarray, center: tuple[int, int], center_thresh: int | None = None, remove_sparse: bool = True) -> list[tuple[int, int]]:
    """
    获取表格中所有标记为 unknown 的格子的坐标，并按优先级排序。

    Args:
        table: 扫雷局面的二维数组
        center: 中心点坐标 (row, col)，用于距离计算和范围筛选
        center_thresh: 距离阈值，超出该值的坐标将被排除；None 表示不限制
        remove_sparse: 是否排除孤立格子（八邻域内全是 unknown 的格子）

    Returns:
        筛选并排序后的 unknown 坐标列表。排序规则：
        1. 周围已知点越多越靠前（信息更丰富）
        2. 同等级下，距中心 Manhattan 距离越近越靠前
    """
    threshold = center_thresh if center_thresh is not None else 10000
    rows, cols = table.shape
    center_row, center_col = center

    # (coord, known_count)：收集时统一用 get_eight_directions 计算一次
    candidates: list[tuple[tuple[int, int], int]] = []
    for i in range(rows):
        for j in range(cols):
            if table[i, j] != 'unknown':
                continue

            # Chebyshev 距离（棋盘距离）筛选
            dist_chebyshev = max(abs(i - center_row), abs(j - center_col))
            if dist_chebyshev >= threshold:
                continue

            coord = (i, j)
            neighbors = get_eight_directions(coord, table.shape)
            known_count = sum(1 for r, c in neighbors if table[r, c] != 'unknown')

            if remove_sparse and known_count == 0:
                continue

            candidates.append((coord, known_count))

    # 排序：已知邻域越多越优先，同等级按 Manhattan 距离
    def sort_key(item: tuple[tuple[int, int], int]) -> tuple[int, int]:
        coord, known_count = item
        dist = abs(coord[0] - center_row) + abs(coord[1] - center_col)
        return (-known_count, dist)

    candidates.sort(key=sort_key)

    return [coord for coord, _ in candidates]
