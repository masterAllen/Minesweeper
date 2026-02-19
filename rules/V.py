'''
V 的规则：普通扫雷的规则
'''
import numpy as np
import utils

def create_constraints(table: np.ndarray) -> dict:
    results = dict()

    # 遍历所有格子，创建约束
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit():

                coordinates = []
                found_mines = 0
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        found_mines += 1
                    if table[neighbor] == 'unknown':
                        coordinates.append(neighbor)
                mine_count = int(table[i, j]) - found_mines
                if len(coordinates) > 0:
                    results[tuple(coordinates)] = (mine_count, mine_count)
    
    return results

def is_legal(table: np.ndarray) -> bool:
    # TODO: 普通规则就默认是合法的
    return True