'''
[W]: 数墙，线索表示周围八格内的连续雷的长度
例如：1x2 表示有两段连续雷，长度分别为 1 和 2
'''
import numpy as np
from constraint import ConstraintsDict
from rule_base import CircularRuleBase


class WRule(CircularRuleBase):
    """数墙规则：线索表示周围八格内的连续雷的长度列表"""
    
    def compute_key(self, mine_groups: list) -> tuple:
        """返回排序后的长度元组"""
        group_sizes = sorted(len(g) for g in mine_groups)
        return tuple(group_sizes)
    
    def get_zero_key(self) -> tuple:
        return (0,)
    
    def translate_cell(self, cell: str):
        """支持 1x2 格式和纯数字格式"""
        if 'x' in cell:
            lengths = [int(i) for i in cell.split('x')]
            lengths.sort()
            return tuple(lengths)
        if cell.isdigit():
            return (int(cell),)
        return None
    
    def get_total_mines(self, key) -> int:
        """总雷数是所有长度之和"""
        if isinstance(key, tuple):
            return sum(key)
        return None


# 单例实例
_rule = WRule()

# 模块级函数（保持向后兼容）
def create_constraints(table: np.ndarray) -> ConstraintsDict:
    return _rule.create_constraints(table)

def is_legal(table: np.ndarray) -> bool:
    return _rule.is_legal(table)

# 导出组合表（向后兼容）
W_COMBINATIONS = _rule.combinations
