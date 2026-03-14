'''
[P]: 划分，线索表示周围八格内的连续雷组数
'''
import numpy as np
from constraint import ConstraintsDict
from rule_base import CircularRuleBase


class PRule(CircularRuleBase):
    """划分规则：线索表示周围八格内的连续雷组数"""
    
    def compute_key(self, mine_groups: list) -> int:
        """返回雷组数量"""
        return len(mine_groups)
    
    def get_zero_key(self) -> int:
        return 0


# 单例实例
_rule = PRule('P')

# 模块级函数（保持向后兼容）
def create_constraints(table: np.ndarray, table_rules: np.ndarray) -> ConstraintsDict:
    return _rule.create_constraints(table, table_rules)

def is_legal(table: np.ndarray, table_rules: np.ndarray) -> bool:
    return _rule.is_legal(table, table_rules)

# 导出组合表（向后兼容）
P_COMBINATIONS = _rule.combinations
