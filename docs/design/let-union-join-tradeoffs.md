# Tradeoff Evaluation: let, union, join

## 背景

adxlite 的定位是**轻量级本地分析引擎**，不是 Kusto 的完整实现。实现这三个特性时需要在以下维度做权衡：

- **实现复杂度** vs **用户价值**
- **Kusto 语义忠实度** vs **SQLite/pandas 的天然能力**
- **功能完整性** vs **代码可维护性**

---

## 1. `let` — 权衡评估

### 三种形式的成本/收益分析

| 形式 | 用户价值 | 实现成本 | 建议 |
|------|----------|----------|------|
| Scalar let (`let x = 5`) | ⭐⭐⭐ 高频使用，参数化查询 | 低 — 纯文本替换/参数绑定 | ✅ 实现 |
| Tabular let (`let t = T \| where ...`) | ⭐⭐ 方便复用中间结果 | 中 — 需要 temp table 生命周期管理 | ✅ 实现 |
| Function let (`let f = (x) { ... }`) | ⭐ 少数高级场景 | 高 — 需要 lambda 解析、参数绑定、递归调用 | ❌ 不实现 |

### 决策

**不实现 function let。** 原因：
1. 需要完整的 lambda 表达式解析器（参数类型声明、函数体作为独立 pipeline）
2. 需要调用时参数替换引擎
3. 用户可以通过 Python 侧组合查询字符串达到相同效果
4. 投入产出比太低

**Scalar let 的语义简化：**
- Kusto 中 scalar let 的 value 可以是任意表达式（包含函数调用）
- adxlite 限制：value 只能是 **字面量**（数字、字符串、bool、timespan、datetime）或 **简单算术表达式**
- 理由：避免需要在 let 解析阶段就执行表达式求值。如果用户需要动态计算，可以在 Python 侧完成

**Tabular let 的简化：**
- 不支持 tabular let 之间的相互引用（即 `let b = a | where ...` 其中 a 是另一个 tabular let）
- 实际上可以支持——按顺序执行即可——但第一版先限制为只引用真实表
- 后续根据用户反馈决定是否放开

### 与 SQLite/pandas 的弥合

| 问题 | 方案 |
|------|------|
| Scalar let 如何传入 SQL？ | 作为参数绑定 `?`，在 translator 层注入到 params 列表 |
| Tabular let 存储？ | SQLite temp table（`CREATE TEMP TABLE`），查询结束后 DROP |
| Tabular let 的 schema？ | 执行子查询后从 DataFrame 推断，注册到 QueryContext |
| 命名冲突（column vs let）？ | Planner 层检查：如果当前 schema 有同名列，忽略 let binding |

---

## 2. `union` — 权衡评估

### 与 SQL UNION 的差异

| Kusto union | SQL UNION ALL | 差异 |
|-------------|---------------|------|
| 自动 schema 对齐（missing → NULL） | 要求列数和类型完全匹配 | 需要手动生成对齐的 SELECT |
| `kind=outer` 取所有列 | 无此概念 | 需要 planner 层计算合并 schema |
| `kind=inner` 取交集列 | 无此概念 | 需要 planner 层计算交集 |
| `withsource` 自动加来源列 | 无此概念 | 在每个 SELECT 中添加字面量列 |
| 支持通配符表名 `union T*` | 不支持 | ❌ 不实现 |
| 支持子查询作为参数 | 支持 | ❌ MVP 不实现，只支持表名 |

### 决策

**实现 kind=outer（默认）和 kind=inner，withsource。**

**不实现：**
- 通配符表名（`union T*`）— 需要表名模式匹配，罕见场景
- 子查询参数（`union (T1 | where x > 5), T2`）— 需要递归解析，复杂度高，推迟
- `isfuzzy` / `hint.*` 参数 — 性能提示在本地场景无意义

### 与 pandas 的弥合

pandas 的 `pd.concat()` 天然支持 schema 对齐（自动 NaN fill），这比 SQL 更方便：

```python
# pandas union 实现极为简洁
result = pd.concat([df1, df2], ignore_index=True)  # 自动 outer join columns
result = df1[common_cols].append(df2[common_cols])  # inner
```

**策略：union 在 pandas 侧的实现比 SQL 侧更自然。** 但为了性能（大数据集不想全部载入内存），SQL 侧仍需实现。

---

## 3. `join` — 权衡评估（最复杂）

### 与 SQL JOIN 的差异

| Kusto join | SQL JOIN | 差异 | 弥合方案 |
|------------|----------|------|----------|
| 默认 `innerunique`（右表去重） | 无此行为 | Kusto 先对右表按 key 去重再 join | 暂按 `inner` 处理，文档标注 |
| `leftanti` / `leftsemi` | `NOT EXISTS` / `EXISTS` | 语义等价但语法不同 | 翻译为 EXISTS 模式 |
| `fullouter` | SQLite 不支持 FULL OUTER JOIN | 需要 workaround | LEFT JOIN + UNION ALL 未匹配右 |
| 输出列：key 不重复，冲突加后缀 | JOIN 默认所有列都出现 | 需要显式 SELECT 列 | Planner 计算输出列 |
| `$left.col` / `$right.col` 语法 | 用 alias 限定 | 需要 parser 识别 | 新 token `$left`/`$right` |
| 右侧可以是 sub-pipeline | 右侧可以是子查询 | 语义相同 | 递归翻译右侧 pipeline |

### 与 pandas 的弥合

pandas `merge()` 天然支持所有 join 类型：

```python
pd.merge(left, right, on='key', how='inner')     # inner
pd.merge(left, right, on='key', how='left')      # leftouter
pd.merge(left, right, on='key', how='right')     # rightouter
pd.merge(left, right, on='key', how='outer')     # fullouter
# anti join:
left[~left['key'].isin(right['key'])]
# semi join:
left[left['key'].isin(right['key'])]
```

**pandas 侧实现 join 比 SQL 简单得多，尤其是 fullouter 和 anti/semi。**

### 决策：分层实现

| 优先级 | Join Kind | SQL 方案 | pandas 方案 | 风险 |
|--------|-----------|----------|-------------|------|
| P0 | inner | INNER JOIN | merge(how='inner') | 低 |
| P0 | leftouter | LEFT JOIN | merge(how='left') | 低 |
| P1 | leftanti | NOT EXISTS | ~isin() | 低 |
| P1 | leftsemi | EXISTS | isin() filter | 低 |
| P1 | rightanti/rightsemi | 交换后用 left 变体 | 同上 | 低 |
| P2 | rightouter | SQLite 不支持→交换为 LEFT | merge(how='right') | 低 |
| P2 | fullouter | LEFT + UNION未匹配 | merge(how='outer') | 中 |
| P3 | innerunique | 先对右表去重再 INNER | drop_duplicates + merge | 中 |

### innerunique 的处理决策

Kusto 默认 `innerunique`：对右表按 join key 去重（保留第一行），再做 inner join。

**方案对比：**
- A) 忠实实现：SQL 中用 `ROW_NUMBER()` 或 GROUP BY 去重子查询 → 复杂
- B) 忠实实现（pandas）：`right.drop_duplicates(subset=keys)` → 简单
- C) 等同于 inner：不去重，文档说明差异

**选择方案 B+C：** SQL 侧当作 inner 处理（大多数情况结果相同），pandas 侧实现真正的去重。文档中明确说明行为差异。

### $left / $right 语法的处理

需要 parser 识别 `$left.col` 和 `$right.col`：
- 新增 `QualifiedIdentifier(scope, name)` AST 节点
- Tokenizer 遇到 `$` 后读取 `left`/`right`，然后 `.`，然后列名
- 翻译时映射到 `_l.[col]` / `_r.[col]`（SQL 中的 alias）

---

## 4. 总体实现策略决策

### 执行引擎策略

当前架构是 "SQL prefix → pandas suffix"。加入 join/union 后：

**关键问题：join/union 是 SQL-compatible 还是 pandas-only？**

| 操作 | SQL-compatible? | 理由 |
|------|-----------------|------|
| union (表名) | ✅ | 直接翻译为 UNION ALL |
| join (inner/left) | ✅ | 直接翻译为 JOIN |
| join (anti/semi) | ✅ | 翻译为 EXISTS |
| join (fullouter) | ⚠️ 复杂 | 需要 workaround，但可行 |
| union/join 在 parse 之后 | ❌ | 必须用 pandas |

**决策：union 和 join 都是 SQL-compatible。** 在 planner 中标记为可 SQL 执行。如果出现在 parse 之后（pandas 阶段），则用 pandas 实现。

### 模块职责分配

| 模块 | 新增职责 |
|------|----------|
| `parser/tokenizer.py` | SEMICOLON token, `$` handling |
| `parser/ast_nodes.py` | LetBinding, KqlStatement, UnionOp, UnionSource, UnionPipeline, JoinOp, JoinCondition, QualifiedIdentifier |
| `parser/parser.py` | let 解析, union 解析, join 解析 (含子 pipeline 递归) |
| `translator/translator.py` | union SQL, join SQL (各种 kind) |
| `engine/planner.py` | union/join schema 计算, let 解析, QueryContext |
| `engine/executor.py` | let 绑定执行, temp table 生命周期, QueryContext 传递 |
| `engine/pandas_ops.py` | pandas union (concat), pandas join (merge) |
| `storage/database.py` | temp table 创建/清理 API |

---

## 5. 不实现的能力（明确边界）

| 能力 | 原因 |
|------|------|
| function let | 实现成本极高，Python 侧有替代方案 |
| union 通配符 (`union T*`) | 罕见场景，可用 Python list_tables + 循环替代 |
| union 子查询参数 | 递归解析复杂度高，推迟到有需求时 |
| join hint 参数 (`hint.strategy`) | 本地场景无性能优化意义 |
| innerunique 精确语义（SQL 侧） | SQL 实现复杂，pandas 侧实现，SQL 侧按 inner 处理 |
| cross-database join | 架构限制，明确不支持 |

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Tabular let temp table 泄漏 | 磁盘/内存浪费 | try/finally 清理 + 使用 SQLite TEMP 表 |
| Join 右侧子查询递归翻译 | 代码复杂度 | Translator 已支持 Pipeline→SQL，复用 |
| fullouter 在 SQLite 的 workaround 性能差 | 大表慢 | 文档标注，建议用 pandas 侧（内存足够时） |
| union 不同类型列的对齐 | 类型混乱 | 使用 SQLite 动态类型特性，结果以实际值为准 |
| let 变量名与列名冲突 | 语义歧义 | 遵循 Kusto 规则：列名优先 |

---

## 7. 实现顺序建议

基于依赖关系和风险排序：

1. **Parser 基础** — semicolon, $left/$right, new keywords
2. **Scalar let** — 最简单，验证 parser→executor 通路
3. **Union (source form)** — schema 对齐逻辑，为 join 做准备
4. **Union (pipe form)** — 复用 source form 逻辑
5. **Join (inner + leftouter)** — 核心 join 能力
6. **Join (anti + semi)** — EXISTS 模式
7. **Tabular let** — temp table 生命周期
8. **Join (fullouter, rightouter)** — 复杂 SQL workaround
9. **Pandas fallback** — union/join 在 parse 之后的情况
10. **Tests + docs** — 贯穿全程，每步都写
