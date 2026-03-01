import numpy as np
from constraint import Constraint, ConstraintsDict

def get_eight_directions(coordinate: tuple[int, int], shape: tuple[int, int]) -> list[tuple[int, int]]:
    """
    返回八连通的坐标：上下左右 + 四个对角线
    """
    directions = [
        (-1, -1), (-1, 0), (-1, 1),  # 上左、上、上右
        (0, -1),           (0, 1),    # 左、右
        (1, -1),  (1, 0),  (1, 1)     # 下左、下、下右
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

def bfs_connected_region(table: np.ndarray, start_coords: list, connected_type: int, allowed_cell_types: set) -> set:
    """
    使用 BFS 找到从起始坐标开始的四/八连通区域
    
    Args:
        table: 表格
        start_coords: 起始坐标列表（可以是单个坐标的列表）
        connected_type: 4 - 四连通，8 - 八连通
        allowed_cell_types: 允许通过的格子类型集合，例如 {'mine', 'unknown'}
    
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
            if cell_value in allowed_cell_types:
                connected_region.add(neighbor)
                queue.append(neighbor)
    
    return connected_region

def find_all_connected_regions(table: np.ndarray, target_coords: list, connected_type: int, allowed_cell_types: set) -> list:
    """
    找到所有分离的连通区域
    
    Args:
        table: 全局表格
        target_coords: 目标坐标列表（例如所有 mine 的坐标）
        allowed_cell_types: 允许通过的格子类型集合，例如 {'mine'} 或 {'mine', 'unknown'}
    
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
            allowed_cell_types=allowed_cell_types
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

    def two_constraints(A: Constraint, B: Constraint) -> tuple[Constraint, Constraint, Constraint]:
        """
        返回 A_only, B_only, A_and_B
        """
        A_only = A - B
        B_only = B - A
        A_and_B = A & B
        return A_only, B_only, A_and_B


    constraints_bak = constraints.copy()

    for A, (minA, maxA) in constraints_bak.items():
        for B, (minB, maxB) in new_constraints.items():
            A_only, B_only, A_and_B = two_constraints(A, B)

            # A_and_B 范围
            z_min = max(0, minA - len(A_only), minB - len(B_only))
            z_max = min(maxA, maxB, len(A_and_B))

            # if z_min > z_max:
            # print(A, minA, maxA)
            # print(B, minB, maxB)
            # print(A_and_B, z_min, z_max)
            # print('--------------------------------------------')

            try:
                constraints[A_and_B] = (z_min, z_max)
            except:
                print(f'A: {A}, minA: {minA}, maxA: {maxA}')
                print(f'B: {B}, minB: {minB}, maxB: {maxB}')
                print(f'A_and_B: {A_and_B}, z_min: {z_min}, z_max: {z_max}')
                print('--------------------------------------------')
                raise ValueError(f'z_min > z_max: {z_min} > {z_max}')


            # A_only, B_only 范围
            x_min = max(0, minA - z_max)
            x_max = min(len(A_only), maxA - z_min)

            # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
            # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
            # print(f'A_only: {A_only}, x_min: {x_min}, x_max: {x_max}')
            # print('--------------------------------------------')
            try:
                constraints[A_only] = (x_min, x_max)
            except:
                raise ValueError(f'x_min > x_max: {x_min} > {x_max}')

            y_min = max(0, minB - z_max)
            y_max = min(len(B_only), maxB - z_min)
            # print(f'A: {A}, minA: {minA}, maxA: {maxA}')
            # print(f'B: {B}, minB: {minB}, maxB: {maxB}')
            # print(f'B_only: {B_only}, y_min: {y_min}, y_max: {y_max}')
            # print('--------------------------------------------')
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