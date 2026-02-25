'''
[B]:  平衡，每行每列雷数相同
'''
import numpy as np
import utils
from constraint import ConstraintsDict

def create_constraints(table: np.ndarray, mine_total) -> ConstraintsDict:
    results = ConstraintsDict()

    for i in range(table.shape[0]):
        coordinates = [(i, j) for j in range(table.shape[1]) if table[i, j] == 'unknown']
        mine_count = len([j for j in range(table.shape[1]) if table[i, j] == 'mine'])

        mine_left = mine_total // table.shape[0] - mine_count
        if len(coordinates) > 0:
            results[tuple(coordinates)] = (mine_left, mine_left)

    for j in range(table.shape[1]):
        coordinates = [(i, j) for i in range(table.shape[0]) if table[i, j] == 'unknown']
        mine_count = len([i for i in range(table.shape[0]) if table[i, j] == 'mine'])

        mine_left = mine_total // table.shape[1] - mine_count
        if len(coordinates) > 0:
            results[tuple(coordinates)] = (mine_left, mine_left)

    return results

def is_legal(table: np.ndarray, mine_total: int) -> bool:
    for i in range(table.shape[0]):
        mine_count = len([j for j in range(table.shape[1]) if table[i, j] == 'mine'])
        if mine_count > mine_total // table.shape[0]:
            return False
        unknown_count = len([j for j in range(table.shape[1]) if table[i, j] == 'unknown'])
        if unknown_count < mine_total // table.shape[0] - mine_count:
            return False

    for j in range(table.shape[1]):
        mine_count = len([i for i in range(table.shape[0]) if table[i, j] == 'mine'])
        if mine_count > mine_total // table.shape[1]:
            return False
        unknown_count = len([i for i in range(table.shape[0]) if table[i, j] == 'unknown'])
        if unknown_count < mine_total // table.shape[1] - mine_count:
            return False
    return True