/**
 * 多行汇聚布局引擎 v2
 *
 * 思路：
 * 1. 找所有 root 节点（无入边）
 * 2. 从每个 root 追踪到叶子，找到首个共享节点 (= 汇聚点)
 * 3. 汇聚点及之后 → 主链（中间行）
 * 4. 汇聚前的每条路径 → 分支行（顶/底）
 * 5. listener 放底行，其他放顶行
 */

const NODE_W = 96
const NODE_H = 34
const H_GAP = 12
const V_GAP = 44
const PAD = 10

export function computePipelineLayout(nodes) {
  if (!nodes || nodes.length === 0)
    return { positions: {}, arrowPaths: [], svgW: 0, svgH: 0, nodeW: NODE_W, nodeH: NODE_H, mergeNode: null }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]))

  // 1. 构建边（trigger + input_mapping）
  const allEdges = []
  for (const n of nodes) {
    if (n.trigger?.source_node && nodeMap.has(n.trigger.source_node))
      allEdges.push({ from: n.trigger.source_node, to: n.id, type: 'trigger' })
    for (const m of n.input_mappings || []) {
      if (nodeMap.has(m.from_node) && !(n.trigger?.source_node === m.from_node))
        allEdges.push({ from: m.from_node, to: n.id, type: 'data' })
    }
  }

  // 邻接表
  const children = new Map()
  const parents = new Map()
  for (const n of nodes) { children.set(n.id, []); parents.set(n.id, []) }
  for (const e of allEdges) {
    children.get(e.from).push(e.to)
    parents.get(e.to).push(e.from)
  }

  // 2. 找 root 节点和老叶
  const roots = nodes.filter((n) => parents.get(n.id).length === 0)
  const leaves = nodes.filter((n) => children.get(n.id).length === 0)

  // 3. 从每个 root 追踪到叶子
  function traceAllPaths(startId) {
    const paths = []
    function dfs(id, path) {
      const p = [...path, id]
      const ch = children.get(id) || []
      if (ch.length === 0) { paths.push(p); return }
      for (const c of ch) dfs(c, p)
    }
    dfs(startId, [])
    return paths
  }

  const rootPaths = roots.map((r) => traceAllPaths(r.id)).flat()

  // 4. 找汇聚点：首个出现在多条 rootPath 中的节点（且不是全相同）
  // 更简单：找入度 > 1 的节点（多个上游来源）
  let mergeNodeId = null
  for (const n of nodes) {
    if ((parents.get(n.id) || []).length >= 2) {
      mergeNodeId = n.id
      break
    }
  }
  // 如果没有入度 > 1 的节点，用第一个有多个路径经过的节点
  if (!mergeNodeId && nodes.length > 0) {
    // 单链情况：用中间节点
    const mid = nodes[Math.floor(nodes.length / 2)]
    mergeNodeId = mid.id
  }

  // 5. 从汇聚点向后找主链
  const mainChainIds = []
  function traceDown(id) {
    if (mainChainIds.includes(id)) return
    mainChainIds.push(id)
    const ch = children.get(id) || []
    // 选第一个子节点（主链是线性的，汇聚后只有一个出口）
    if (ch.length >= 1) traceDown(ch[0])
  }
  traceDown(mergeNodeId)

  const mainSet = new Set(mainChainIds)

  // 6. 找分支路径（从 root 到合并点之前）
  const branchPaths = [] // [{ids: [], row: 0|1}]

  for (const path of rootPaths) {
    // 截取到合并点之前的节点
    const beforeMerge = []
    for (const id of path) {
      if (mainSet.has(id)) break
      beforeMerge.push(id)
    }
    if (beforeMerge.length > 0) {
      // 判断放顶行还是底行
      const lastNode = nodeMap.get(beforeMerge[beforeMerge.length - 1])
      const isTop = lastNode && !lastNode.listener
      branchPaths.push({ ids: beforeMerge, row: isTop ? 0 : 2 })
    }
  }

  // 监听节点即使不在路径中也放底行（它们是持续运行的）
  for (const n of nodes) {
    if (n.listener && !mainSet.has(n.id) && !branchPaths.some((bp) => bp.ids.includes(n.id))) {
      branchPaths.push({ ids: [n.id], row: 2 })
    }
  }

  // 7. 分配列
  const CENTER = 1
  const rowMap = new Map()

  // 主链放中间行
  mainChainIds.forEach((id, i) => rowMap.set(id, { row: CENTER, col: i }))

  const mergeCol = rowMap.get(mergeNodeId)?.col ?? 0

  // 分支：从 mergeCol 往左排
  for (const bp of branchPaths) {
    const startCol = mergeCol - bp.ids.length
    bp.ids.forEach((id, i) => {
      rowMap.set(id, { row: bp.row, col: startCol + i })
    })
  }

  // 8. 坐标
  const allCols = [...rowMap.values()].map((v) => v.col)
  const minCol = Math.min(...allCols)
  const maxCol = Math.max(...allCols)

  const positions = {}
  for (const n of nodes) {
    const rc = rowMap.get(n.id) || { row: CENTER, col: 0 }
    positions[n.id] = {
      id: n.id,
      x: PAD + (rc.col - minCol) * (NODE_W + H_GAP),
      y: PAD + rc.row * V_GAP,
      w: NODE_W, h: NODE_H,
      row: rc.row, col: rc.col,
    }
  }

  // 9. 箭头
  const makeArrow = (from, to, type) => {
    const p1 = positions[from]
    const p2 = positions[to]
    if (!p1 || !p2) return null
    const sameRow = p1.row === p2.row
    const x1 = p1.x + p1.w
    const y1 = p1.y + p1.h / 2
    const x2 = p2.x
    const y2 = p2.y + p2.h / 2
    let d
    if (sameRow) {
      d = `M ${x1} ${y1} L ${x2} ${y2}`
    } else {
      const cx = x1 + (x2 - x1) * 0.55
      d = `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`
    }
    return { from, to, d, type }
  }

  const trigEdges = allEdges.filter((e) => e.type === 'trigger')
  const dataEdges = allEdges.filter((e) => e.type === 'data')

  const arrowPaths = [
    ...trigEdges.map((e) => makeArrow(e.from, e.to, 'trigger')).filter(Boolean),
    ...dataEdges.map((e) => makeArrow(e.from, e.to, 'data')).filter(Boolean),
  ]

  // 10. SVG 尺寸
  const svgW = PAD + (maxCol - minCol + 1) * (NODE_W + H_GAP) + PAD
  const usedRows = new Set(Object.values(positions).map((p) => p.row))
  const svgH = PAD + Math.max(...usedRows) * V_GAP + NODE_H + PAD

  return {
    positions, arrowPaths, svgW, svgH,
    nodeW: NODE_W, nodeH: NODE_H,
    mergeNode: mergeNodeId,
  }
}
