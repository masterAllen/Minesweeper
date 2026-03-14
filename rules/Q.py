'''
[Q]: 无方，2x2 至少有一个雷
'''
import numpy as np
import utils

def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> dict:
    results = dict()
    for i in range(table.shape[0]-1):
        for j in range(table.shape[1]-1):
            coordinates = []
            already_has_mine = False
            for dx, dy in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                if table[i+dx, j+dy] == 'unknown':
                    coordinates.append((i+dx, j+dy))
                if table[i+dx, j+dy] == 'mine':
                    already_has_mine = True
            if len(coordinates) > 0 and not already_has_mine:
                results[tuple(coordinates)] = (1, len(coordinates))
    return results

def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    """
    检查 [Q] 的规则是否合法
    """
    for i in range(table.shape[0]-1):
        for j in range(table.shape[1]-1):
            has_unknown_or_mine = False
            for dx, dy in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                if table[i+dx, j+dy] == 'unknown' or table[i+dx, j+dy] == 'mine':
                    has_unknown_or_mine = True
                    break
            if not has_unknown_or_mine:
                return False
    return True