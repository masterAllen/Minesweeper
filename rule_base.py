'''
圆环连续雷规则的基类
用于 W (数墙)、W2 (最长数墙)、P (划分) 等规则
'''
import numpy as np
import utils
from constraint import ConstraintsDict, Constraint
from abc import ABC, abstractmethod


def get_circular_mine_groups(mask: int) -> list:
    """
    分析 8 位掩码中的连续雷段
    返回: 雷段列表，每个雷段是一个索引列表
    """
    n = 8

    # 传入数字，如 0b1011..，拆分成数组：[1, 0, 1, 1, ...]
    arr = tuple((mask >> i) & 1 for i in range(n))

    # 雷的连续段
    mine_groups = [[]]
    for i in range(n):
        if arr[i] == 1:
            mine_groups[-1].append(i)
        else:
            mine_groups.append([])

    # 首尾看是否可以相连
    if arr[0] == 1 and arr[-1] == 1 and len(mine_groups) > 1:
        first, last = mine_groups[0], mine_groups[-1]
        merged = last + first
        mine_groups = [merged] + mine_groups[1:-1]

    # 筛选出非空的雷段
    mine_groups = [group for group in mine_groups if len(group) > 0]
    return mine_groups


class CircularRuleBase(ABC):
    """圆环连续雷规则的基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.combinations = self._make_combinations()
    
    @abstractmethod
    def compute_key(self, mine_groups: list) -> any:
        """
        从雷段列表计算用于索引的键值
        子类需要实现此方法
        """
        pass
    
    @abstractmethod
    def get_zero_key(self) -> any:
        """返回全为非雷时的键值"""
        pass
    
    def _make_combinations(self) -> dict:
        """预计算所有 256 种组合"""
        results = {}
        for i in range(1, 256):
            mine_groups = get_circular_mine_groups(i)
            key = self.compute_key(mine_groups)
            if key not in results:
                results[key] = []
            results[key].append(format(i, '08b'))
        # 加上全是非雷的情况
        results[self.get_zero_key()] = ['00000000']
        return results
    
    def translate_cell(self, cell: str):
        """
        解析单元格值，返回键值
        默认实现：纯数字返回 int，否则返回 None
        子类可以覆盖此方法以支持特殊格式（如 W 的 1x2）
        """
        if cell.isdigit():
            return int(cell)
        return None
    
    def get_total_mines(self, key) -> int:
        """
        获取该键值对应的总雷数
        默认返回 None（不添加总雷数约束）
        子类可以覆盖此方法
        """
        return None
    
    def create_constraints(self, table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
        """创建约束"""
        results = ConstraintsDict()

        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                key = self.translate_cell(table[i, j])
                if key is None or self.name not in table_rules[i, j]:
                    continue

                # 按照顺时针来
                neighbor_coordinates, neighbor_str = utils.get_eight_coordinates_force(table, (i, j))
                
                # 获取候选组合
                candidates = self.combinations.get(key, [])
                if not candidates:
                    raise ValueError(f'center = ({i}, {j}), key = {key}, no candidates in combinations')
                candidates = list(candidates)  # 复制一份避免修改原数据
                
                # 添加总雷数约束（如果需要）
                total_mines = self.get_total_mines(key)
                if total_mines is not None:
                    coordinates = []
                    found_mines = 0
                    for neighbor in utils.get_eight_directions((i, j), table.shape):
                        if table[neighbor] == 'mine':
                            found_mines += 1
                        if table[neighbor] == 'unknown':
                            coordinates.append(neighbor)
                    mine_count = total_mines - found_mines
                    if coordinates:
                        results[Constraint(coordinates)] = (mine_count, mine_count)

                # 根据已知条件筛选 candidates
                for idx in range(8):
                    if neighbor_str[idx] == '1':
                        candidates = [c for c in candidates if c[idx] == '1']
                    elif neighbor_str[idx] == '0':
                        candidates = [c for c in candidates if c[idx] == '0']

                if len(candidates) == 0:
                    raise ValueError(f'center = ({i}, {j}), neighbors = {neighbor_str}, but no candidates')

                # 筛选可能性
                for idx, coordinate in enumerate(neighbor_coordinates):
                    if neighbor_str[idx] == '?':
                        c0 = candidates[0][idx]
                        if all(c[idx] == c0 for c in candidates):
                            if c0 == '1':
                                results[Constraint([coordinate])] = (1, 1)
                            if c0 == '0':
                                results[Constraint([coordinate])] = (0, 0)

        return results

    def is_legal(self, table: np.ndarray, table_rules: np.ndarray) -> bool:
        """检查表格是否合法"""
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                key = self.translate_cell(table[i, j])
                if key is None or self.name not in table_rules[i, j]:
                    continue

                # 按照顺时针来
                neighbor_coordinates, neighbor_str = utils.get_eight_coordinates_force(table, (i, j))
                
                candidates = self.combinations.get(key, [])
                if not candidates:
                    return False
                candidates = list(candidates)

                # 根据已知条件筛选 candidates
                for idx in range(8):
                    if neighbor_str[idx] == '1':
                        candidates = [c for c in candidates if c[idx] == '1']
                    elif neighbor_str[idx] == '0':
                        candidates = [c for c in candidates if c[idx] == '0']

                if len(candidates) == 0:
                    return False
        return True

