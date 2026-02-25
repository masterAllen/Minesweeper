'''
[D]:  对偶，雷必须是 1x2 或者 2x1，并且矩形互不接触
'''
import numpy as np
import utils

def create_constraints(table: np.ndarray) -> dict:
    results = dict()

    '''
    先找出肯定不可能出现的坐标
    '''
    must_nomine_coorinates = set()
    # 横向检查
    for i in range(table.shape[0]):
        j = 0
        while j < table.shape[1] - 1:
            if table[i, j] == 'mine' and table[i, j+1] == 'mine':
                for neighbor in _get_neighbors((i, j), table.shape, True):
                    if table[neighbor] == 'unknown':
                        must_nomine_coorinates.add(neighbor)
                j += 2
            else:
                j += 1
    
    # 纵向检查
    for j in range(table.shape[1]):
        i = 0
        while i < table.shape[0] - 1:
            if table[i, j] == 'mine' and table[i+1, j] == 'mine':
                for neighbor in _get_neighbors((i, j), table.shape, False):
                    if table[neighbor] == 'unknown':
                        must_nomine_coorinates.add(neighbor)
                i += 2
            else:
                i += 1
    
    results[tuple(must_nomine_coorinates)] = (0, 0)

    '''
    在这之后，对于单独的 mine，他的四周一定要有一个点是 mine
    '''
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                has_mine = False
                coordinates = []
                for neighbor in utils.get_four_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        # 如果四周已经有一个是 mine，那么这个坐标可以跳过了
                        has_mine = True
                        break
                    elif table[neighbor] == 'unknown':
                        # 还要检查一下他是否是肯定不可能出现的坐标
                        if neighbor not in must_nomine_coorinates:
                            coordinates.append(neighbor)

                # 如果四周有 mine，则不处理
                if has_mine:
                    continue

                # 如果四周没有 mine，并且四周有 unknown，这里面选一个是 mine
                if len(coordinates) > 0:
                    results[tuple(coordinates)] = (1, 1)

    # '''
    # 对于单独的 unknown，如果四周都是已知块，那么他一定是安全的 --> 这个可以直接和下一段的逻辑合并了
    # '''
    # for i in range(table.shape[0]):
    #     for j in range(table.shape[1]):
    #         if table[i, j] == 'unknown':
    #             is_lone = True
    #             for neighbor in utils.get_four_directions((i, j), table.shape):
    #                 if table[neighbor] == 'mine' or table[neighbor] == 'unknown':
    #                     is_lone = False
    #                     break
    #             if is_lone:
    #                 results[tuple([(i, j)])] = (0, 0)

    '''
    最后做一次强遍历，如果 unknown，四周都是非雷已知块或者 mine周围块，那么他一定是安全的

    这里的 mine 周围块，就是指四周有 mine 的块，比如下面的组合，假设在左上角，虽然左上角 unknown 有两个出口，但是他不可能是 mine：

    unknown | unknown
    unknown | mine
    '''
    # 先找出 mine 四周块
    mine_neigbor_coordinates = set()
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                for neighbor in utils.get_four_directions((i, j), table.shape):
                    if table[neighbor] == 'unknown':
                        mine_neigbor_coordinates.add(neighbor)
    # 遍历 unknown
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'unknown':
                is_lone = True
                for neigbor in utils.get_four_directions((i, j), table.shape):
                    if not ((table[neigbor] != 'mine' and table[neigbor] != 'unknown') or neigbor in mine_neigbor_coordinates):
                        is_lone = False
                        break
                if is_lone:
                    results[tuple([(i, j)])] = (0, 0)

    return results

def is_legal(table: np.ndarray, weeper) -> bool:
    # 横向检查
    for i in range(table.shape[0]):
        j = 0
        while j < table.shape[1] - 1:
            if table[i, j] == 'mine' and table[i, j+1] == 'mine':
                for neighbor in _get_neighbors((i, j), table.shape, True):
                    if table[neighbor] == 'mine':
                        # weeper.print_table(table)
                        # print(f'横向检查失败: {i}, {j}, neighbor = {neighbor}')
                        return False
                j += 2
            else:
                j += 1
    
    # 纵向检查
    for j in range(table.shape[1]):
        i = 0
        while i < table.shape[0] - 1:
            if table[i, j] == 'mine' and table[i+1, j] == 'mine':
                for neighbor in _get_neighbors((i, j), table.shape, False):
                    if table[neighbor] == 'mine':
                        # weeper.print_table(table)
                        # print(f'纵向检查失败: {i}, {j}, neighbor = {neighbor}')
                        return False
                i += 2
            else:
                i += 1

    # 如果某个坐标是 mine，而它的四周又都是已知块，那不行
    # 换句话说，如果某个坐标是 mine，他的四周一定要有一个 unknown 或者 mine
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                is_ok = False
                neighbors = utils.get_four_directions((i, j), table.shape)
                for neighbor in neighbors:
                    if table[neighbor] == 'mine' or table[neighbor] == 'unknown':
                        is_ok = True
                        break
                if not is_ok:
                    # weeper.print_table(table)
                    # print(f'单点检查失败: {i}, {j}, neighbors = {neighbors}')
                    return False
    
    return True


def _get_neighbors(coordinate: tuple, shape: tuple, is_horizontal: bool) -> list:
    if is_horizontal:
        directions = [(0, -1), (0, 2), (-1, 0), (1, 0), (-1, 1), (1, 1)]
    else:
        directions = [(-1, 0), (2, 0), (0, -1), (0, 1), (1, -1), (1, 1)]
    neighbors = []
    for di, dj in directions:
        if 0 <= coordinate[0] + di < shape[0] and 0 <= coordinate[1] + dj < shape[1]:
            neighbors.append((coordinate[0] + di, coordinate[1] + dj))
    return neighbors

def check_constraints(constraints: dict) -> bool:
    for coordinates, (min_mine_count, max_mine_count) in constraints.items():
        # 必须要是 3 个连续的组合
        if len(coordinates) == 3 and min_mine_count == max_mine_count:
            coordinates = list(coordinates)

            is_continue = False
            if coordinates[0][0] == coordinates[1][0] == coordinates[2][0]:
                # 必须是横向
                if coordinates[0][1] + 1 == coordinates[1][1] and coordinates[1][1] + 1 == coordinates[2][1]:
                    is_continue = True
            elif coordinates[0][1] == coordinates[1][1] == coordinates[2][1]:
                # 必须是纵向
                if coordinates[0][0] + 1 == coordinates[1][0] and coordinates[1][0] + 1 == coordinates[2][0]:
                    is_continue = True

            if not is_continue:
                continue

            # 如果三个连续的 unknown 中，都是雷，那么有问题！
            if min_mine_count == 3:
                print(coordinates, min_mine_count, max_mine_count)
                print('三个连续的 unknown 中，都是雷，有问题！')
                return False

    return True