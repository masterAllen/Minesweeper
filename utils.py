import numpy as np

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
