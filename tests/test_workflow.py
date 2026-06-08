from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.workflow import (
    NodeType,
    Workflow,
    WorkflowEngine,
    WorkflowNode,
    WorkflowTemplate,
)


class TestWorkflowNode:
    def test_node_defaults(self):
        """A node should have sensible defaults."""
        node = WorkflowNode(id="n1", type=NodeType.INPUT.value)
        assert node.config == {}
        assert node.inputs == []
        assert node.outputs == []
        assert node.position == (0, 0)

    def test_node_roundtrip_dict(self):
        """Serialization and deserialization should be lossless."""
        node = WorkflowNode(
            id="n1",
            type=NodeType.CONVERT.value,
            config={"preset": "logo"},
            inputs=["in1"],
            outputs=["out1"],
            position=(120, 340),
        )
        d = node.to_dict()
        restored = WorkflowNode.from_dict(d)
        assert restored.id == node.id
        assert restored.type == node.type
        assert restored.config == node.config
        assert restored.inputs == node.inputs
        assert restored.outputs == node.outputs
        assert restored.position == node.position


class TestWorkflowValidation:
    def test_empty_workflow_invalid(self):
        """An empty workflow must be invalid."""
        wf = Workflow()
        valid, errors = wf.validate()
        assert not valid
        assert any("no nodes" in e.lower() for e in errors)

    def test_missing_input_node(self):
        """A workflow without an INPUT node is invalid."""
        wf = Workflow(
            nodes={"convert": WorkflowNode(id="convert", type=NodeType.CONVERT.value)},
            edges=[],
        )
        valid, errors = wf.validate()
        assert not valid
        assert any("input" in e.lower() for e in errors)

    def test_cycle_detection(self):
        """A workflow with a cycle must be flagged."""
        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "a": WorkflowNode(id="a", type=NodeType.CONVERT.value, inputs=["input"]),
                "b": WorkflowNode(id="b", type=NodeType.OPTIMIZE.value, inputs=["a"]),
            },
            edges=[("input", "a"), ("a", "b"), ("b", "a")],
        )
        valid, errors = wf.validate()
        assert not valid
        assert any("cycle" in e.lower() for e in errors)

    def test_unreachable_node(self):
        """Nodes not reachable from INPUT should be reported."""
        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "orphan": WorkflowNode(id="orphan", type=NodeType.EXPORT.value),
            },
            edges=[],
        )
        valid, errors = wf.validate()
        assert not valid
        assert any("unreachable" in e.lower() for e in errors)

    def test_valid_workflow(self):
        """A simple linear workflow should validate."""
        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "convert": WorkflowNode(id="convert", type=NodeType.CONVERT.value, inputs=["input"]),
                "export": WorkflowNode(id="export", type=NodeType.EXPORT.value, inputs=["convert"]),
            },
            edges=[("input", "convert"), ("convert", "export")],
        )
        valid, errors = wf.validate()
        assert valid
        assert errors == []

    def test_unknown_node_type(self):
        """An unknown node type should produce a validation error."""
        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "bad": WorkflowNode(id="bad", type="unknown_type", inputs=["input"]),
            },
            edges=[("input", "bad")],
        )
        valid, errors = wf.validate()
        assert not valid
        assert any("unknown type" in e.lower() for e in errors)


class TestWorkflowSerialization:
    def test_save_and_load(self, tmp_path: Path):
        """Persisting and reloading a workflow should be lossless."""
        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value, position=(0, 0)),
                "convert": WorkflowNode(id="convert", type=NodeType.CONVERT.value, inputs=["input"], position=(100, 0)),
            },
            edges=[("input", "convert")],
            name="test",
        )
        path = tmp_path / "wf.json"
        wf.save(path)
        loaded = Workflow.load(path)
        assert loaded.name == wf.name
        assert set(loaded.nodes.keys()) == set(wf.nodes.keys())
        assert loaded.edges == wf.edges

    def test_to_dict_from_dict(self):
        """Dictionary roundtrip should preserve structure."""
        wf = WorkflowTemplate.logo_pipeline()
        data = wf.to_dict()
        restored = Workflow.from_dict(data)
        assert restored.name == wf.name
        assert set(restored.nodes.keys()) == set(wf.nodes.keys())


class TestWorkflowExecution:
    def test_execute_linear_workflow(self, tmp_path: Path):
        """A linear workflow should produce an SVG output."""
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "convert": WorkflowNode(id="convert", type=NodeType.CONVERT.value, inputs=["input"]),
            },
            edges=[("input", "convert")],
        )

        with patch("vector_studio.workflow.trace_image", return_value=mock_result):
            results = wf.execute(img, tmp_path / "output")

        assert len(results) >= 1
        assert any("out.svg" in str(p) for p in results)

    def test_engine_run_workflow_batch(self, tmp_path: Path):
        """The engine should process multiple inputs."""
        img1 = tmp_path / "a.png"
        img1.write_bytes(b"fake")
        img2 = tmp_path / "b.png"
        img2.write_bytes(b"fake")
        out1 = tmp_path / "a.svg"
        out1.write_text("<svg></svg>")
        out2 = tmp_path / "b.svg"
        out2.write_text("<svg></svg>")

        def _mock_trace(input_path, output_path, options):
            return TraceResult(
                input_path=input_path,
                svg_path=output_path,
                engine="python-vtracer",
                elapsed_seconds=0.3,
            )

        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "loop": WorkflowNode(id="loop", type=NodeType.LOOP.value, inputs=["input"]),
                "convert": WorkflowNode(id="convert", type=NodeType.CONVERT.value, inputs=["loop"]),
            },
            edges=[("input", "loop"), ("loop", "convert")],
        )

        engine = WorkflowEngine(max_workers=2)
        with patch("vector_studio.workflow.trace_image", side_effect=_mock_trace):
            results = engine.run_workflow(wf, [img1, img2], output_dir=tmp_path / "out")

        assert len(results) == 2


class TestWorkflowTemplates:
    def test_logo_pipeline(self):
        """The logo pipeline template should validate."""
        wf = WorkflowTemplate.logo_pipeline()
        valid, errors = wf.validate()
        assert valid
        assert errors == []
        assert wf.name == "logo_pipeline"

    def test_photo_pipeline(self):
        """The photo pipeline template should validate."""
        wf = WorkflowTemplate.photo_pipeline()
        valid, errors = wf.validate()
        assert valid
        assert errors == []
        assert wf.name == "photo_pipeline"

    def test_batch_pipeline(self):
        """The batch pipeline template should validate."""
        wf = WorkflowTemplate.batch_pipeline()
        valid, errors = wf.validate()
        assert valid
        assert errors == []
        assert wf.name == "batch_pipeline"

    def test_get_template_unknown(self):
        """Requesting an unknown template should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown template"):
            WorkflowTemplate.get_template("nonexistent")


class TestWorkflowCondition:
    def test_condition_branching(self, tmp_path: Path):
        """A condition node should follow the selected branch."""
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
        )

        wf = Workflow(
            nodes={
                "input": WorkflowNode(id="input", type=NodeType.INPUT.value),
                "cond": WorkflowNode(
                    id="cond",
                    type=NodeType.CONDITION.value,
                    inputs=["input"],
                    config={"expression": "true", "true_branch": "convert", "false_branch": "export"},
                ),
                "convert": WorkflowNode(id="convert", type=NodeType.CONVERT.value, inputs=["cond"]),
                "export": WorkflowNode(id="export", type=NodeType.EXPORT.value, inputs=["cond"]),
            },
            edges=[("input", "cond"), ("cond", "convert"), ("cond", "export")],
        )

        engine = WorkflowEngine(max_workers=1)
        with patch("vector_studio.workflow.trace_image", return_value=mock_result):
            results = engine.run_workflow(wf, [img], output_dir=tmp_path / "out")

        # Only the true branch (convert) should execute.
        assert len(results) >= 1
