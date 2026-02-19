'''
[O]: 外部，非雷区域四方向联通；雷区域与题板外部四方向联通
'''
from multiprocessing import Value
import numpy as np
import utils

def create_constraints(table: np.ndarray) -> dict:
    results = dict()

    # 1. 非雷区域四方向联通
    # 2. 雷区域与题板外部四方向联通，这个暂时找不到
    # 上面两个条件确实不好有推出条件，但做题发现其实有如下方式：

    '''
    一定不可能出现如下的组合：
    mine   | nomine    or      nomine | mine
    nomine | mine              mine   | nomine
    所以可以三定一
    '''
    bad_combines = [
        ['mine', 'nomine', 'nomine', 'mine'],
        ['nomine', 'mine', 'mine', 'nomine']
    ]
    directions = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for i in range(table.shape[0]-1):
        for j in range(table.shape[1]-1):
            now_combine = []
            for di, dj in directions:
                if table[i+di, j+dj] == 'mine' or table[i+di, j+dj] == 'unknown':
                    now_combine.append(table[i+di, j+dj])
                else:
                    now_combine.append('nomine')
            
            unknown_idxs = [i for i in range(4) if now_combine[i] == 'unknown']
            # 如果有超过一个 unknown，不考虑；

            # print(f'({i}, {j}) --> {now_combine}, unknown_idxs = {unknown_idxs}')
            # 如果没有 unknown，查看是否符合要求
            if len(unknown_idxs) == 0:
                for bad_combine in bad_combines:
                    if now_combine == bad_combine:
                        print(f'出现错误的组合，位置 ({i}, {j}) 的组合为：{now_combine}')
                        raise ValueError(f'出现错误的组合，位置 ({i}, {j}) 的组合为：{now_combine}')

            # 如果只有一个 unknown，查看是否可以确定这个坐标
            if len(unknown_idxs) == 1:
                unknown_idx = unknown_idxs[0]
                for bad_combine in bad_combines:
                    temp_bad_combine = bad_combine.copy()
                    temp_bad_combine[unknown_idx] = 'unknown'

                    # 如果相等，那么 unknown 对应的位置就知道是 mine 还是 nomine 了
                    if temp_bad_combine == now_combine:
                        di, dj = directions[unknown_idx]
                        if bad_combine[unknown_idx] == 'mine':
                            # 如果对应的位置是 mine，说明这里不应该是 mine
                            results[tuple([(i+di, j+dj)])] = (0, 0)
                        else:
                            results[tuple([(i+di, j+dj)])] = (1, 1)


    # 还有一个可以探索的：每个已知块组合的区域，如果四周只有一个 unknown，那么这个 unknown 一定是 safe
    known_coordinates = []
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] != 'unknown' and table[i, j] != 'mine':
                known_coordinates.append((i, j))

    # 使用通用函数找到所有与 not_mine 四连通的区域
    connected_regions = utils.find_all_connected_regions(
        table, known_coordinates, connected_type=4,
        allowed_cell_types={'question', '0', '1', '2', '3', '4', '5', '6', '7', '8'}
    )

    for connected_region in connected_regions:
        is_ok = True
        unknown_coordinates = []
        for coordinate in connected_region:
            for neighbor in utils.get_four_directions(coordinate, table.shape):
                if table[neighbor[0], neighbor[1]] == 'unknown':
                    unknown_coordinates.append(neighbor)
                    if len(unknown_coordinates) > 1:
                        is_ok = False
                        break
            if not is_ok:
                break
        if len(unknown_coordinates) == 1:
            results[tuple([unknown_coordinates[0]])] = (0, 0)

    return results

def is_legal(table: np.ndarray, mine_count: int, weeper=None) -> bool:
    # 1. 已确定区域四方向联通
    known_coordinates = []
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] != 'unknown' and table[i, j] != 'mine':
                known_coordinates.append((i, j))

    # 使用通用函数找到所有与 not_mine 四连通的区域
    connected_regions = utils.find_all_connected_regions(
        table, known_coordinates, connected_type=4,
        allowed_cell_types={'unknown', 'question', '0', '1', '2', '3', '4', '5', '6', '7', '8'}
    )
    if len(connected_regions) > 1:
        # weeper.print_table(table)
        # print(f'connected_regions > 1, connected_regions = {connected_regions}')
        return False

    # 2. 雷区域与题板外部四方向联通 --> 每个雷 BFS，unkown 也可以通过，最后组成的区域要有一个在临界上
    # 这样做，即使最后没有雷了，仍然也能用上面的方法去检查
    mine_coordinates = [(i, j) for i in range(table.shape[0]) for j in range(table.shape[1]) if table[i, j] == 'mine']
    connected_regions = utils.find_all_connected_regions(
        table, mine_coordinates, connected_type=4,
        allowed_cell_types={'mine', 'unknown'}
    )
    for connected_region in connected_regions:
        # 每个区域要有一个 x 或者 y 坐标是临界区域
        is_ok = False
        for coordinate in connected_region:
            if coordinate[0] == 0 or coordinate[1] == 0 or coordinate[0] == table.shape[0]-1 or coordinate[1] == table.shape[1]-1:
                is_ok = True
                break
        if not is_ok:
            return False
    
    return True