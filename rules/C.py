
'''
[C]: 所有雷的区域是八连通的
'''
import numpy as np
import utils

def create_constraints(table: np.ndarray) -> dict:
    # 如果某个点是雷，四周要有一个雷
    # --> 1. 修改为求解雷的联通区域（unknown不可通），每个区域的四周会一定要有雷

    # 四周如果全是已知的，那么这块区域一定是安全的
    # --> 2. 修改为直接求雷的联通区域（unknown可通），那么剩下的 unknown 一定不可能是雷

    results = dict()

    # 找到所有 mine 的坐标
    mine_coordinates = [(i, j) for i in range(table.shape[0]) for j in range(table.shape[1]) if table[i, j] == 'mine']

    # 1. 求解所有 mine 的联通区域（只考虑 mine，不考虑 unknown），然后每个联通区域的四周要有雷
    if len(mine_coordinates) > 0:
        
        # 找到所有分离的 mine 连通区域（只考虑 mine，不考虑 unknown）
        connected_regions = utils.find_all_connected_regions(
            table, mine_coordinates, connected_type=8,
            allowed_cell_types={'mine'}  # 只允许通过 mine
        )

        # 现在 connected_regions 包含了所有分离的 mine 连通区域
        # 每个连通区域的四周要有雷
        for connected_region in connected_regions:
            neighbors = set()
            for coordinate in connected_region:
                for neighbor in utils.get_eight_directions(coordinate, table.shape):
                    if table[neighbor[0], neighbor[1]] == 'unknown':
                        neighbors.add(neighbor)
            if len(neighbors) > 0:
                results[tuple(neighbors)] = (1, len(neighbors))
            else:
                raise ValueError(f'某个连通区域的四周没有 unknown，坐标：{connected_region}')
        
    # 2. 求当前雷的联通区域，剩下的 unknown 一定不是雷
    if len(mine_coordinates) > 0:

        # 使用通用函数找到所有与 mine 八连通的区域（包括可以连接的 unknown）
        connected_regions = utils.find_all_connected_regions(
            table, [mine_coordinates[0]], connected_type=8,
            allowed_cell_types={'mine', 'unknown'}
        )

        if len(connected_regions) > 1:
            raise ValueError(f'找到多个连通区域：{connected_regions}')
        
        # 找到所有不在连通区域中的 unknown，它们一定不是雷
        safe_unknowns = []
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                if table[i, j] == 'unknown' and (i, j) not in connected_regions[0]:
                    safe_unknowns.append((i, j))
        
        # 为这些安全的 unknown 添加约束：它们一定不是雷
        if len(safe_unknowns) > 0:
            print(f'这些坐标一定是安全的：{safe_unknowns}')
            results[tuple(safe_unknowns)] = (0, 0)
    return results


def is_legal(table: np.ndarray) -> bool:
    """
    检查当前雷的坐标是否形成八连通区域（八连通：上下左右 + 四个对角线方向）
    允许通过 unknown 格子连接，但不能通过数字或 question 格子连接
    
    Args:
        table: 全局表格
    
    Returns:
        True 如果所有雷八连通，False 否则
    """
    mine_coordinates = []
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                mine_coordinates.append((i, j))

    if len(mine_coordinates) == 0 or len(mine_coordinates) == 1:
        return True
    
    # 使用通用函数找到连通区域（允许通过 mine 和 unknown）
    connected_region = utils.bfs_connected_region(
        table, [mine_coordinates[0]], connected_type=8,
        allowed_cell_types={'mine', 'unknown'}
    )
    
    # 检查是否所有雷都被访问到
    mine_set = set(mine_coordinates)
    visited_mines = connected_region & mine_set
    return len(visited_mines) == len(mine_coordinates)
