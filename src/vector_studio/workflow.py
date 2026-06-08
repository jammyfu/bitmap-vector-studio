from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .models import TraceOptions, TraceResult
from .presets import options_from_preset
from .tracer import SUPPORTED_EXTENSIONS, trace_image

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Supported node types in a workflow."""

    INPUT = "input"
    PREPROCESS = "preprocess"
    CONVERT = "convert"
    OPTIMIZE = "optimize"
    EXPORT = "export"
    AI_PROCESS = "ai_process"
    CONDITION = "condition"
    LOOP = "loop"
    MERGE = "merge"


@dataclass
class WorkflowNode:
    """A single node in a visual workflow graph.

    Parameters
    ----------
    id:
        Unique node identifier.
    type:
        Node type (see :class:`NodeType`).
    config:
        Node-specific configuration dictionary.
    inputs:
        IDs of upstream nodes that feed into this node.
    outputs:
        IDs of downstream nodes that this node feeds into.
    position:
        Canvas coordinates ``(x, y)`` for UI rendering.
    """

    id: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    position: tuple[int, int] = (0, 0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a plain dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "config": dict(self.config),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "position": list(self.position),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowNode":
        """Reconstruct a :class:`WorkflowNode` from a plain dictionary."""
        pos = data.get("position", [0, 0])
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            position = (int(pos[0]), int(pos[1]))
        else:
            position = (0, 0)
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            config=dict(data.get("config", {})),
            inputs=list(data.get("inputs", [])),
            outputs=list(data.get("outputs", [])),
            position=position,
        )


class Workflow:
    """A directed graph of :class:`WorkflowNode` instances.

    The workflow can be validated, persisted, and executed against one or
    more input files.
    """

    def __init__(
        self,
        nodes: dict[str, WorkflowNode] | None = None,
        edges: list[tuple[str, str]] | None = None,
        name: str = "untitled",
    ) -> None:
        self.nodes: dict[str, WorkflowNode] = dict(nodes) if nodes else {}
        self.edges: list[tuple[str, str]] = list(edges) if edges else []
        self.name = name

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the workflow graph.

        Returns
        -------
        tuple[bool, list[str]]
            ``(is_valid, error_messages)``.
        """
        errors: list[str] = []

        if not self.nodes:
            errors.append("Workflow contains no nodes.")
            return False, errors

        # Check for unknown node types.
        valid_types = {t.value for t in NodeType}
        for node in self.nodes.values():
            if node.type not in valid_types:
                errors.append(f"Node '{node.id}' has unknown type '{node.type}'.")

        # Check edge endpoints exist.
        for src, dst in self.edges:
            if src not in self.nodes:
                errors.append(f"Edge references unknown source node '{src}'.")
            if dst not in self.nodes:
                errors.append(f"Edge references unknown destination node '{dst}'.")

        # Check for cycles using DFS.
        white = set(self.nodes.keys())
        grey: set[str] = set()
        black: set[str] = set()

        adjacency: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for src, dst in self.edges:
            if src in adjacency:
                adjacency[src].append(dst)

        def _dfs(node_id: str) -> bool:
            white.discard(node_id)
            grey.add(node_id)
            for neighbor in adjacency.get(node_id, []):
                if neighbor in grey:
                    errors.append(f"Cycle detected involving node '{neighbor}'.")
                    return False
                if neighbor in black:
                    continue
                if not _dfs(neighbor):
                    return False
            grey.discard(node_id)
            black.add(node_id)
            return True

        while white:
            start = white.pop()
            white.add(start)
            if not _dfs(start):
                break

        # Check that every node is reachable from at least one INPUT node.
        input_nodes = [n.id for n in self.nodes.values() if n.type == NodeType.INPUT.value]
        if not input_nodes:
            errors.append("Workflow must contain at least one INPUT node.")

        reachable: set[str] = set()
        queue = deque(input_nodes)
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for src, dst in self.edges:
                if src == current and dst in self.nodes:
                    queue.append(dst)

        unreachable = set(self.nodes.keys()) - reachable
        if unreachable:
            errors.append(f"Nodes unreachable from INPUT: {', '.join(sorted(unreachable))}.")

        return len(errors) == 0, errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, input_path: Path, output_dir: Path) -> list[Path]:
        """Execute the workflow for a single input file.

        Parameters
        ----------
        input_path:
            Source bitmap image.
        output_dir:
            Directory to write intermediate and final outputs.

        Returns
        -------
        list[Path]
            Paths of all exported output files.
        """
        engine = WorkflowEngine()
        results = engine.run_workflow(self, [input_path], output_dir=output_dir)
        # Collect exported paths from the last trace results.
        exported: list[Path] = []
        for r in results:
            if r.svg_path.exists():
                exported.append(r.svg_path)
            if r.pdf_path and r.pdf_path.exists():
                exported.append(r.pdf_path)
            if r.png_path and r.png_path.exists():
                exported.append(r.png_path)
            if r.eps_path and r.eps_path.exists():
                exported.append(r.eps_path)
        return exported

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the workflow to a plain dictionary."""
        return {
            "name": self.name,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [list(edge) for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workflow":
        """Reconstruct a :class:`Workflow` from a plain dictionary."""
        nodes_data = data.get("nodes", {})
        nodes = {nid: WorkflowNode.from_dict(nd) for nid, nd in nodes_data.items()}
        edges_raw = data.get("edges", [])
        edges = [(str(e[0]), str(e[1])) for e in edges_raw if isinstance(e, (list, tuple)) and len(e) >= 2]
        return cls(nodes=nodes, edges=edges, name=str(data.get("name", "untitled")))

    def save(self, path: Path) -> None:
        """Persist the workflow to *path* as JSON."""
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Workflow":
        """Load a workflow from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


class WorkflowEngine:
    """Executes :class:`Workflow` instances with topological ordering,
    parallel dispatch, condition branching, and loop support.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._node_registry: dict[str, Callable[..., Any]] = {
            NodeType.INPUT.value: self._run_input,
            NodeType.PREPROCESS.value: self._run_preprocess,
            NodeType.CONVERT.value: self._run_convert,
            NodeType.OPTIMIZE.value: self._run_optimize,
            NodeType.EXPORT.value: self._run_export,
            NodeType.AI_PROCESS.value: self._run_ai_process,
            NodeType.CONDITION.value: self._run_condition,
            NodeType.LOOP.value: self._run_loop,
            NodeType.MERGE.value: self._run_merge,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        workflow: Workflow,
        inputs: list[Path],
        output_dir: Path | None = None,
    ) -> list[TraceResult]:
        """Run *workflow* over *inputs*.

        Parameters
        ----------
        workflow:
            The workflow graph to execute.
        inputs:
            List of input image paths.
        output_dir:
            Optional base output directory.  Defaults to the parent of the
            first input file.

        Returns
        -------
        list[TraceResult]
            One result per successfully processed input.
        """
        valid, errors = workflow.validate()
        if not valid:
            raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

        if output_dir is None and inputs:
            output_dir = inputs[0].parent / "workflow_output"
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Build adjacency and reverse adjacency.
        adjacency: dict[str, list[str]] = {nid: [] for nid in workflow.nodes}
        reverse: dict[str, list[str]] = {nid: [] for nid in workflow.nodes}
        for src, dst in workflow.edges:
            adjacency[src].append(dst)
            reverse[dst].append(src)

        # Compute in-degree for topological sort.
        in_degree = {nid: 0 for nid in workflow.nodes}
        for src, dst in workflow.edges:
            in_degree[dst] += 1

        # Shared execution state.
        state: dict[str, Any] = {
            "_inputs": inputs,
            "_output_dir": output_dir,
            "_results": [],
        }
        lock = threading.Lock()

        # Track which nodes have been executed.
        executed: set[str] = set()
        results_by_node: dict[str, Any] = {}

        # Kahn's algorithm with parallel execution of ready nodes.
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])

        while queue:
            # Gather all currently ready nodes.
            ready = []
            while queue:
                ready.append(queue.popleft())

            # Execute ready nodes in parallel.
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(
                        self._execute_node,
                        workflow.nodes[nid],
                        state,
                        lock,
                        results_by_node,
                    ): nid
                    for nid in ready
                }
                for future in as_completed(futures):
                    nid = futures[future]
                    try:
                        node_result = future.result()
                    except Exception as exc:
                        logger.error("Node %s failed: %s", nid, exc)
                        node_result = None
                    results_by_node[nid] = node_result
                    executed.add(nid)

                    # Update downstream in-degrees and enqueue new ready nodes.
                    for dst in adjacency[nid]:
                        # For CONDITION nodes, only follow the selected branch.
                        if workflow.nodes[nid].type == NodeType.CONDITION.value:
                            branch = (node_result or {}).get("branch")
                            if branch is not None and dst != branch:
                                continue
                        in_degree[dst] -= 1
                        if in_degree[dst] == 0 and dst not in executed:
                            queue.append(dst)

        return state.get("_results", [])

    # ------------------------------------------------------------------
    # Node executors
    # ------------------------------------------------------------------

    def _execute_node(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> Any:
        """Dispatch a single node to its registered handler."""
        handler = self._node_registry.get(node.type)
        if handler is None:
            raise ValueError(f"No handler for node type '{node.type}'")
        return handler(node, state, lock, results_by_node)

    def _run_input(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Pass through the current input file."""
        inputs: list[Path] = state["_inputs"]
        return {"files": inputs}

    def _run_preprocess(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply preprocessing (e.g. background removal, resize)."""
        cfg = node.config
        files = self._collect_upstream_files(node, results_by_node)
        processed: list[Path] = []
        for f in files:
            # Simple passthrough; real implementation would call preprocess.
            processed.append(f)
        return {"files": processed}

    def _run_convert(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Trace images using the configured preset."""
        cfg = node.config
        preset = cfg.get("preset", "poster")
        opts = options_from_preset(preset)
        files = self._collect_upstream_files(node, results_by_node)
        output_dir: Path = state["_output_dir"]
        converted: list[Path] = []
        trace_results: list[TraceResult] = []

        for f in files:
            if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            out = output_dir / f"{f.stem}.svg"
            try:
                result = trace_image(f, out, opts)
                converted.append(out)
                trace_results.append(result)
            except Exception as exc:
                logger.warning("Conversion failed for %s: %s", f, exc)

        with lock:
            state["_results"].extend(trace_results)

        return {"files": converted, "results": trace_results}

    def _run_optimize(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Run SVG optimization on upstream SVG files."""
        from .svg_optimizer import optimize_svg_comprehensive
        from .svg_tools import optimize_svg_file

        cfg = node.config
        level = cfg.get("level", "basic")
        files = self._collect_upstream_files(node, results_by_node)
        optimized: list[Path] = []
        for f in files:
            if f.suffix.lower() == ".svg":
                try:
                    if level in ("comprehensive", "aggressive"):
                        optimize_svg_comprehensive(f, f)
                    else:
                        optimize_svg_file(f)
                    optimized.append(f)
                except Exception as exc:
                    logger.warning("Optimization failed for %s: %s", f, exc)
            else:
                optimized.append(f)
        return {"files": optimized}

    def _run_export(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Export to additional formats (PDF, PNG, EPS)."""
        from .svg_tools import export_svg_to_eps_with_inkscape, export_svg_to_pdf, export_svg_to_png

        cfg = node.config
        files = self._collect_upstream_files(node, results_by_node)
        exported: list[Path] = []
        for f in files:
            if f.suffix.lower() != ".svg":
                exported.append(f)
                continue
            try:
                if cfg.get("pdf"):
                    pdf = f.with_suffix(".pdf")
                    export_svg_to_pdf(f, pdf)
                    exported.append(pdf)
                if cfg.get("png"):
                    png = f.with_suffix(".png")
                    export_svg_to_png(f, png)
                    exported.append(png)
                if cfg.get("eps"):
                    eps = f.with_suffix(".eps")
                    export_svg_to_eps_with_inkscape(f, eps)
                    exported.append(eps)
                exported.append(f)
            except Exception as exc:
                logger.warning("Export failed for %s: %s", f, exc)
        return {"files": exported}

    def _run_ai_process(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply AI enhancement or simplification."""
        cfg = node.config
        files = self._collect_upstream_files(node, results_by_node)
        # Placeholder: real implementation would call ai_simplify / ai_ocr.
        return {"files": files}

    def _run_condition(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a condition and return the selected branch."""
        cfg = node.config
        expression = cfg.get("expression", "true")
        # Simple evaluation: support ``true`` / ``false`` literals.
        if expression.lower() == "true":
            branch = cfg.get("true_branch")
        elif expression.lower() == "false":
            branch = cfg.get("false_branch")
        else:
            branch = cfg.get("true_branch")
        files = self._collect_upstream_files(node, results_by_node)
        return {"branch": branch, "files": files}

    def _run_loop(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Iterate over upstream files and process each one."""
        cfg = node.config
        files = self._collect_upstream_files(node, results_by_node)
        # The loop node simply passes files through; the engine handles
        # parallel execution of downstream nodes per file implicitly by
        # treating files as a batch.
        return {"files": files}

    def _run_merge(
        self,
        node: WorkflowNode,
        state: dict[str, Any],
        lock: threading.Lock,
        results_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge multiple upstream file lists into one."""
        files = self._collect_upstream_files(node, results_by_node)
        return {"files": files}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_upstream_files(
        node: WorkflowNode,
        results_by_node: dict[str, Any],
    ) -> list[Path]:
        """Gather file lists from all upstream nodes."""
        files: list[Path] = []
        for upstream_id in node.inputs:
            upstream_result = results_by_node.get(upstream_id)
            if isinstance(upstream_result, dict):
                upstream_files = upstream_result.get("files", [])
                for f in upstream_files:
                    if isinstance(f, Path):
                        files.append(f)
                    else:
                        files.append(Path(f))
        return files


class WorkflowTemplate:
    """Factory for built-in workflow templates."""

    @staticmethod
    def logo_pipeline() -> Workflow:
        """Input -> Background transparent -> Convert -> Optimize -> Export."""
        nodes = {
            "input": WorkflowNode(id="input", type=NodeType.INPUT.value, position=(0, 0)),
            "preprocess": WorkflowNode(
                id="preprocess",
                type=NodeType.PREPROCESS.value,
                config={"remove_bg": True, "transparent": True},
                inputs=["input"],
                position=(200, 0),
            ),
            "convert": WorkflowNode(
                id="convert",
                type=NodeType.CONVERT.value,
                config={"preset": "logo"},
                inputs=["preprocess"],
                position=(400, 0),
            ),
            "optimize": WorkflowNode(
                id="optimize",
                type=NodeType.OPTIMIZE.value,
                config={"level": "comprehensive"},
                inputs=["convert"],
                position=(600, 0),
            ),
            "export": WorkflowNode(
                id="export",
                type=NodeType.EXPORT.value,
                config={"png": True, "pdf": False},
                inputs=["optimize"],
                position=(800, 0),
            ),
        }
        edges = [
            ("input", "preprocess"),
            ("preprocess", "convert"),
            ("convert", "optimize"),
            ("optimize", "export"),
        ]
        return Workflow(nodes=nodes, edges=edges, name="logo_pipeline")

    @staticmethod
    def photo_pipeline() -> Workflow:
        """Input -> AI enhance -> Convert -> Optimize -> Export."""
        nodes = {
            "input": WorkflowNode(id="input", type=NodeType.INPUT.value, position=(0, 0)),
            "ai": WorkflowNode(
                id="ai",
                type=NodeType.AI_PROCESS.value,
                config={"enhance": "photo"},
                inputs=["input"],
                position=(200, 0),
            ),
            "convert": WorkflowNode(
                id="convert",
                type=NodeType.CONVERT.value,
                config={"preset": "photo"},
                inputs=["ai"],
                position=(400, 0),
            ),
            "optimize": WorkflowNode(
                id="optimize",
                type=NodeType.OPTIMIZE.value,
                config={"level": "basic"},
                inputs=["convert"],
                position=(600, 0),
            ),
            "export": WorkflowNode(
                id="export",
                type=NodeType.EXPORT.value,
                config={"png": True, "pdf": True},
                inputs=["optimize"],
                position=(800, 0),
            ),
        }
        edges = [
            ("input", "ai"),
            ("ai", "convert"),
            ("convert", "optimize"),
            ("optimize", "export"),
        ]
        return Workflow(nodes=nodes, edges=edges, name="photo_pipeline")

    @staticmethod
    def batch_pipeline() -> Workflow:
        """Input -> Loop -> Convert -> Merge -> Export."""
        nodes = {
            "input": WorkflowNode(id="input", type=NodeType.INPUT.value, position=(0, 0)),
            "loop": WorkflowNode(
                id="loop",
                type=NodeType.LOOP.value,
                config={"batch": True},
                inputs=["input"],
                position=(200, 0),
            ),
            "convert": WorkflowNode(
                id="convert",
                type=NodeType.CONVERT.value,
                config={"preset": "poster"},
                inputs=["loop"],
                position=(400, 0),
            ),
            "merge": WorkflowNode(
                id="merge",
                type=NodeType.MERGE.value,
                inputs=["convert"],
                position=(600, 0),
            ),
            "export": WorkflowNode(
                id="export",
                type=NodeType.EXPORT.value,
                config={"pdf": True},
                inputs=["merge"],
                position=(800, 0),
            ),
        }
        edges = [
            ("input", "loop"),
            ("loop", "convert"),
            ("convert", "merge"),
            ("merge", "export"),
        ]
        return Workflow(nodes=nodes, edges=edges, name="batch_pipeline")

    @classmethod
    def get_template(cls, name: str) -> Workflow:
        """Return a built-in template by name.

        Raises
        ------
        ValueError
            If *name* does not match a known template.
        """
        mapping = {
            "logo_pipeline": cls.logo_pipeline,
            "photo_pipeline": cls.photo_pipeline,
            "batch_pipeline": cls.batch_pipeline,
        }
        if name not in mapping:
            raise ValueError(f"Unknown template: {name}. Available: {', '.join(mapping.keys())}")
        return mapping[name]()
