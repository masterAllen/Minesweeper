'''
V 的规则：普通扫雷的规则
'''
import numpy as np
import utils
from constraint import Constraint, ConstraintsDict

def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
    results = ConstraintsDict()

    # 遍历所有格子，创建约束
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit() and 'V' in table_rules[i, j]:

                coordinates = []
                found_mines = 0
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        found_mines += 1
                    if table[neighbor] == 'unknown':
                        coordinates.append(neighbor)
                mine_count = int(table[i, j]) - found_mines
                if len(coordinates) > 0:
                    results[Constraint(coordinates)] = (mine_count, mine_count)
    
    return results

def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            if table[i, j].isdigit() and 'V' in table_rules[i, j]:
                found_mines = 0
                found_unknowns = 0
                for neighbor in utils.get_eight_directions((i, j), table.shape):
                    if table[neighbor] == 'mine':
                        found_mines += 1
                    if table[neighbor] == 'unknown':
                        found_unknowns += 1

                if int(table[i, j]) < found_mines:
                    return False
                if int(table[i, j]) > found_mines + found_unknowns:
                    return False
    return True