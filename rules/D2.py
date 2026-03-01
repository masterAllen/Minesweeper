'''
[D']: 雷必须组成 1x1, 1x2, 1x3, 1x4 的矩形，矩形之间互不接触（对角接触也不行）
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict

def create_constraints(table: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    # 定理一：不存在对角相邻的雷
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                for neighbor in utils.get_diagonal_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        raise ValueError(f'对角相邻的雷，坐标：{(i, j)}')
                    elif table[neighbor] == 'unknown':
                        results[Constraint([neighbor])] = (0, 0)

    # 定理二：不存在横竖方向连续的5个雷。
    for i in range(table.shape[0]):
        j = 0
        continous_cols = []
        while j < table.shape[1]:
            if table[i, j] == 'unknown':
                if len(continous_cols) == 4:
                    results[Constraint([(i, j)])] = (0, 0)

            if table[i, j] == 'mine':
                if len(continous_cols) > 0 and j == continous_cols[-1] + 1:
                    continous_cols.append(j)
                    if len(continous_cols) >= 5:
                        raise ValueError(f'横向方向连续的5个雷，坐标：{(i, j)}')
                else:
                    continous_cols = [j]
            else:
                continous_cols = []
            j += 1
    
    for j in range(table.shape[1]):
        i = 0
        continous_rows = []
        while i < table.shape[0]:
            if table[i, j] == 'unknown':
                if len(continous_rows) == 4:
                    results[Constraint([(i, j)])] = (0, 0)

            if table[i, j] == 'mine':
                if len(continous_rows) > 0 and i == continous_rows[-1] + 1:
                    continous_rows.append(i)
                    if len(continous_rows) >= 5:
                        raise ValueError(f'纵向方向连续的5个雷，坐标：{(i, j)}')
                else:
                    continous_rows = [i]
            else:
                continous_rows = []
            i += 1

    return results


def is_legal(table: np.ndarray) -> bool:
    # 定理一：不存在对角相邻的雷
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j] == 'mine':
                for neighbor in utils.get_diagonal_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        return False

    # 定理二：不存在横竖方向连续的5个雷。
    for i in range(table.shape[0]):
        j = 0
        continous_cols = []
        while j < table.shape[1]:
            if table[i, j] == 'mine':
                if len(continous_cols) > 0 and j == continous_cols[-1] + 1:
                    continous_cols.append(j)
                    if len(continous_cols) >= 5:
                        return False
                else:
                    continous_cols = [j]
            else:
                continous_cols = []
            j += 1
    
    for j in range(table.shape[1]):
        i = 0
        continous_rows = []
        while i < table.shape[0]:
            if table[i, j] == 'mine':
                if len(continous_rows) > 0 and i == continous_rows[-1] + 1:
                    continous_rows.append(i)
                    if len(continous_rows) >= 5:
                        return False
                else:
                    continous_rows = [i]
            else:
                continous_rows = []
            i += 1

    return True