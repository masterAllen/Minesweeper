# 性能优化说明

本文档解释 `Constraint` 类和 `refresh_constraints` 函数的性能优化原理。

---

## 1. Constraint 类优化

### 1.1 原始实现的问题

```python
class Constraint:
    def __init__(self, coordinates):
        coordinates = list(coordinates)
        coordinates_sorted = sorted(coordinates, key=lambda x: (x[0], x[1]))  # O(n log n)
        self.coordinates = tuple(coordinates_sorted)

    def __sub__(self, other):
        my_set = set(self.coordinates)           # O(n) 创建 set
        other_set = set(other.coordinates)       # O(m) 创建 set
        return Constraint(list(my_set - other_set))  # O(k) + O(k log k) 排序

    def __and__(self, other):
        my_set = set(self.coordinates)           # O(n) 创建 set
        other_set = set(other.coordinates)       # O(m) 创建 set
        return Constraint(list(my_set & other_set))  # O(min(n,m)) + O(k log k) 排序

    def __eq__(self, other):
        return set(self.coordinates) == set(other.coordinates)  # O(n + m) 每次比较
```

**问题分析：**

| 操作 | 时间复杂度 | 问题 |
|-----|-----------|------|
| `__init__` | O(n log n) | 每次创建都要排序 |
| `__sub__`, `__and__` | O(n + m + k log k) | 每次都要创建 set，结果还要排序 |
| `__eq__` | O(n + m) | 每次比较都要创建两个 set |
| `__hash__` | O(n) | 每次都要计算 |

在 `refresh_constraints` 中，**每对约束都要执行 3 次集合操作**（`A & B`, `A - B`, `B - A`），创建 3 个新 Constraint。如果有 1000 个约束对，就是：
- 6000 次 set 创建
- 3000 次排序
- 3000 次 Constraint 创建

### 1.2 优化后的实现

```python
class Constraint:
    __slots__ = ('_coords_set', '_coords_tuple', '_hash', '_len')
    
    def __init__(self, coordinates, length=None):
        if isinstance(coordinates, frozenset):
            self._coords_set = coordinates  # 直接使用，O(1)
        else:
            coords_list = list(coordinates)
            self._coords_set = frozenset(coords_list)  # O(n)，无需排序
        self._coords_tuple = None  # 延迟计算
        self._hash = None          # 延迟计算

    def __sub__(self, other):
        return Constraint(self._coords_set - other._coords_set)  # O(n)，直接操作

    def __and__(self, other):
        return Constraint(self._coords_set & other._coords_set)  # O(min(n,m))

    def __eq__(self, other):
        return self._coords_set == other._coords_set  # O(min(n,m))，直接比较

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self._coords_set)  # 只计算一次
        return self._hash
```

**优化效果：**

| 操作 | 原来 | 优化后 | 提升 |
|-----|------|--------|------|
| `__init__` | O(n log n) | O(n) | **去掉排序** |
| `__sub__`, `__and__` | O(n + m + k log k) | O(n) 或 O(min(n,m)) | **去掉中间 set 创建和排序** |
| `__eq__` | O(n + m) | O(min(n,m)) | **直接比较 frozenset** |
| `__hash__` | O(n) 每次 | O(1) 缓存后 | **缓存结果** |

### 1.3 关键技术

1. **使用 `frozenset` 替代 `tuple`**
   - `frozenset` 是不可变集合，可以直接进行集合运算
   - 集合运算后返回新的 `frozenset`，无需转换

2. **延迟计算（Lazy Evaluation）**
   - `coordinates` 属性只在需要时才排序计算
   - `__hash__` 只计算一次，之后返回缓存值

3. **使用 `__slots__`**
   - 减少内存占用（不使用 `__dict__`）
   - 略微提升属性访问速度
   

### 1.4 测试结果

这个提升巨大。之前对于 `300x200` 的规模，需要四秒钟，现在直接缩短到 0.1 秒。

---

## 2. refresh_constraints 函数优化

### 2.1 原始实现的问题

```python
def refresh_constraints(constraints, new_constraints):
    for A in constraints:           # n 个约束
        for B in new_constraints:   # m 个约束
            A_and_B = A & B
            if len(A_and_B) == 0:
                continue
            # ... 处理有交集的情况
```

**问题：O(n × m) 双重循环**

假设有 500 个约束，新约束有 100 个：
- 总遍历次数：500 × 100 = **50,000 次**
- 大部分约束对**没有交集**，但还是要计算 `A & B` 来检查

### 2.2 优化后的实现

```python
def refresh_constraints(constraints, new_constraints):
    # 建立坐标反向索引
    coord_to_constraints = {}
    for A in constraints:
        for coord in A.coordinates:
            if coord not in coord_to_constraints:
                coord_to_constraints[coord] = set()
            coord_to_constraints[coord].add(A)
    
    for B in new_constraints:
        # 只找可能有交集的约束 A
        candidate_As = set()
        for coord in B.coordinates:
            if coord in coord_to_constraints:
                candidate_As.update(coord_to_constraints[coord])
        
        for A in candidate_As:  # 只遍历有交集的
            # ... 处理
```

**优化原理：反向索引**

```
坐标 (0, 1) → {约束A, 约束C, 约束F}
坐标 (0, 2) → {约束B, 约束C}
坐标 (1, 1) → {约束A, 约束D}
...
```

对于新约束 B，只需要查找 B 包含的坐标对应的约束集合，而不是遍历所有约束。

### 2.3 时间复杂度对比

| 场景 | 原来 | 优化后 |
|-----|------|--------|
| 建立索引 | - | O(总坐标数) |
| 查找有交集的约束对 | O(n × m) | O(实际有交集的对数) |
| **总体** | O(n × m) | O(总坐标数 + k)，k 是有交集的对数 |

**实际例子：**
- 500 个约束，100 个新约束
- 平均每个约束包含 5 个坐标
- 假设只有 5% 的约束对有交集

| 指标 | 原来 | 优化后 |
|-----|------|--------|
| 遍历次数 | 50,000 | 2,500 (5%) |
| 提升 | - | **20 倍** |

### 2.4 测试结果

这个实测下来改进不是很大。对于 `300x200` 的规模，原来需要四秒多一点，使用这个大概是 3.6-3.8 秒之间。