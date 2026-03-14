'''
[A]: 无马步，马步对应的两个格子不能有雷
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict

def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    # 雷的马步对应的格子不能有雷
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                for neighbor in utils.get_knight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        raise ValueError(f'马步相邻的雷，坐标：{(i, j)}')
                    elif table[neighbor] == 'unknown':
                        results[Constraint([neighbor])] = (0, 0)

    return results


def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    # 雷的马步对应的格子不能有雷
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                for neighbor in utils.get_knight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        return False
    return True