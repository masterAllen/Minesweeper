'''
[H]: 横向，任意两雷不能横向相邻
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
                if j+1 < table.shape[1]:
                    if table[i, j+1] == 'mine':
                        raise ValueError(f'横向相邻的雷，坐标：{(i, j)}')
                    elif table[i, j+1] == 'unknown':
                        results[Constraint([(i, j+1)])] = (0, 0)
                if j-1 >= 0:
                    if table[i, j-1] == 'mine':
                        raise ValueError(f'横向相邻的雷，坐标：{(i, j)}')
                    elif table[i, j-1] == 'unknown':
                        results[Constraint([(i, j-1)])] = (0, 0)

    return results


def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    # 雷的马步对应的格子不能有雷
    for i in range(table.shape[0]):
        for j in range(table.shape[1]-1):
            if table[i, j] == 'mine':
                if j+1 < table.shape[1]:
                    if table[i, j+1] == 'mine':
                        return False
                if j-1 >= 0:
                    if table[i, j-1] == 'mine':
                        return False
    return True