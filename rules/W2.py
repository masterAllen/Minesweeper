'''
[W2]: 最长数墙，线索表示周围八格内的连续雷的最长长度
'''
import numpy as np
from constraint import ConstraintsDict
from rule_base import CircularRuleBase


class W2Rule(CircularRuleBase):
    """最长数墙规则：线索表示周围八格内的连续雷的最长长度"""
    
    def compute_key(self, mine_groups: list) -> int:
        """返回最长长度"""
        if not mine_groups:
            return 0
        return max(len(g) for g in mine_groups)
    
    def get_zero_key(self) -> int:
        return 0


# 单例实例
_rule = W2Rule('W2')

# 模块级函数（保持向后兼容）
def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
    return _rule.create_constraints(table, table_rules)

def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    return _rule.is_legal(table, table_rules)

# 导出组合表（向后兼容）
W2_COMBINATIONS = _rule.combinations
