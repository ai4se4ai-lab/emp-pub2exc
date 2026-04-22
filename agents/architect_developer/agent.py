"""
agents/architect_developer/agent.py
Generates software architecture, code, tests, and deployment config.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from shared.base_agent import BaseAgent
from shared.llm_client import call_claude, call_claude_json
from shared.message_schema import AgentName, MessageType

logger = logging.getLogger(__name__)

ARCHITECT_SYSTEM = """
You are a senior software architect. Design clean, modular architectures for research software.
Be specific about module names, responsibilities, and interfaces.
Respond ONLY with valid JSON unless asked for Markdown.
"""

DEVELOPER_SYSTEM = """
You are a senior Python engineer implementing research software.
Write clean, well-typed, well-documented Python 3.11+ code.
Add # Implements: FR-XXX comments to every function.
Respond ONLY with the raw code — no markdown fences, no preamble.
"""

TEST_SYSTEM = """
You are a senior test engineer. Write comprehensive pytest tests for research software.
Cover happy path and edge cases. Mock LLM calls. Respond with raw Python code only.
"""


class ArchitectDeveloperAgent(BaseAgent):
    name = AgentName.ARCHITECT_DEVELOPER

    def _execute(self) -> None:
        requirements = self._load_json("formalizer", "functional_requirements.json")
        data_contracts = self._load_json("formalizer", "data_contracts.json")
        concept_model = self._load_json("formalizer", "concept_model.json")

        self._post(AgentName.BROADCAST, MessageType.STATUS, {"status": "designing_architecture"})

        # Phase 1: Architecture
        architecture_md, modules = self._design_architecture(requirements, concept_model)
        (self.output_dir / "architecture.md").write_text(architecture_md, encoding="utf-8")
        self._write("modules.json", modules)
        logger.info("Architecture phase complete — %d modules.", len(modules.get("modules", [])))

        # Phase 2: Code generation
        self._post(AgentName.BROADCAST, MessageType.STATUS, {"status": "generating_code"})
        src_dir = self.output_dir / "src"
        src_dir.mkdir(exist_ok=True)
        self._generate_code(modules, data_contracts, requirements, src_dir)

        # Phase 3: Tests + Deployment
        self._post(AgentName.BROADCAST, MessageType.STATUS, {"status": "generating_tests"})
        tests_dir = self.output_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        self._generate_tests(modules, requirements, tests_dir)
        self._generate_deployment(modules, requirements)

        artifact_refs = [
            f"outputs/{self.run_id}/architect_developer/architecture.md",
            f"outputs/{self.run_id}/architect_developer/src/",
            f"outputs/{self.run_id}/architect_developer/tests/",
        ]

        self._post(
            to_agent=AgentName.AUDITOR_SUPERVISOR,
            message_type=MessageType.OUTPUT,
            payload={
                "src_path": artifact_refs[1],
                "tests_path": artifact_refs[2],
                "architecture_path": artifact_refs[0],
            },
            artifact_refs=artifact_refs,
        )
        logger.info("Architect+Developer complete.")

    # ------------------------------------------------------------------
    # Phase 1: Architecture
    # ------------------------------------------------------------------

    def _design_architecture(self, requirements: dict, concept_model: dict) -> tuple[str, dict]:
        self._log_assumption(
            "A layered Python package structure is appropriate for this research software.",
            confidence=0.85, impact="medium",
        )
        modules = call_claude_json(
            system=ARCHITECT_SYSTEM,
            user=f"""Design the software architecture as a list of Python modules.

Return JSON:
{{
  "modules": [{{
    "name": "module_name",
    "file": "src/module_name.py",
    "responsibility": "...",
    "fr_refs": ["FR-001"],
    "depends_on": [],
    "public_functions": [{{"name": "fn", "signature": "fn(x: Type) -> ReturnType", "description": "..."}}]
  }}]
}}

REQUIREMENTS:
{json.dumps(requirements.get("items", []), indent=2)[:6000]}

CONCEPT MODEL:
{json.dumps(concept_model, indent=2)[:3000]}""",
        )

        architecture_md = call_claude(
            system=ARCHITECT_SYSTEM,
            user=f"""Write an architecture.md document (Markdown) describing the modules and their relationships.
Include a Mermaid dependency diagram.

MODULES:
{json.dumps(modules, indent=2)[:5000]}""",
        )
        return architecture_md, modules

    # ------------------------------------------------------------------
    # Phase 2: Code generation
    # ------------------------------------------------------------------

    def _generate_code(
        self,
        modules: dict,
        data_contracts: dict,
        requirements: dict,
        src_dir: Path,
    ) -> None:
        # Generate pydantic models from data contracts first
        models_code = self._generate_models(data_contracts)
        (src_dir / "models.py").write_text(models_code, encoding="utf-8")
        self._validate_python(src_dir / "models.py")

        # Generate __init__.py
        (src_dir / "__init__.py").write_text("# Generated research software package\n")

        for module in modules.get("modules", []):
            code = call_claude(
                system=DEVELOPER_SYSTEM,
                user=f"""Implement this Python module for research software.
Import from .models for data types. Add # Implements: FR-XXX to each function.

MODULE SPEC:
{json.dumps(module, indent=2)}

REQUIREMENTS (relevant):
{json.dumps([r for r in requirements.get("items", []) if r["id"] in module.get("fr_refs", [])], indent=2)}
""",
            )
            file_path = src_dir / Path(module["file"]).name
            file_path.write_text(code, encoding="utf-8")
            self._validate_python(file_path)
            logger.debug("Generated %s", file_path.name)

    def _generate_models(self, data_contracts: dict) -> str:
        return call_claude(
            system=DEVELOPER_SYSTEM,
            user=f"""Generate a models.py file with pydantic BaseModel classes derived from these JSON Schema data contracts.
Use Python 3.11+ type hints. Export all models.

DATA CONTRACTS:
{json.dumps(data_contracts.get("schemas", []), indent=2)[:6000]}""",
        )

    # ------------------------------------------------------------------
    # Phase 3: Tests + Deployment
    # ------------------------------------------------------------------

    def _generate_tests(self, modules: dict, requirements: dict, tests_dir: Path) -> None:
        (tests_dir / "__init__.py").write_text("")
        conftest = self._generate_conftest(modules)
        (tests_dir / "conftest.py").write_text(conftest, encoding="utf-8")

        for module in modules.get("modules", []):
            test_code = call_claude(
                system=TEST_SYSTEM,
                user=f"""Write pytest tests for this module. Mock any LLM or external calls.
Cover every public function. Include at least one edge case per function.

MODULE:
{json.dumps(module, indent=2)}
""",
            )
            test_file = tests_dir / f"test_{Path(module['file']).stem}.py"
            test_file.write_text(test_code, encoding="utf-8")
            logger.debug("Generated %s", test_file.name)

    def _generate_conftest(self, modules: dict) -> str:
        return call_claude(
            system=TEST_SYSTEM,
            user=f"""Write a conftest.py with shared pytest fixtures for these modules.
Include fixtures for mocking the Anthropic API client.

MODULES: {json.dumps([m['name'] for m in modules.get('modules', [])], indent=2)}""",
        )

    def _generate_deployment(self, modules: dict, requirements: dict) -> None:
        dockerfile = call_claude(
            system="You are a DevOps engineer. Write minimal, reproducible Dockerfiles. No markdown.",
            user=f"""Write a Dockerfile for this Python 3.11 research software package.
Use multi-stage build. Install from requirements.txt.
MODULES: {[m['name'] for m in modules.get('modules', [])]}""",
        )
        (self.output_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")

        requirements_txt = call_claude(
            system="Output only a requirements.txt file. No markdown, no explanation.",
            user=f"""Generate a requirements.txt for a Python 3.11 research software project with these modules:
{[m['name'] for m in modules.get('modules', [])]}
Always include: anthropic, pydantic, pytest, pytest-cov""",
        )
        (self.output_dir / "requirements.txt").write_text(requirements_txt, encoding="utf-8")

        deploy_config = {
            "run_id": self.run_id,
            "python_version": "3.11",
            "entry_point": "scripts/run_pipeline.py",
            "environment_variables": ["ANTHROPIC_API_KEY", "HUMAN_REVIEW_ENABLED"],
            "resource_requirements": {"memory_gb": 4, "cpu_cores": 2},
        }
        self._write("deployment_config.json", deploy_config)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_python(self, path: Path) -> None:
        import py_compile
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            logger.error("Syntax error in generated file %s: %s", path, e)
            self._log_assumption(
                f"Generated file {path.name} had a syntax error — may require manual fix.",
                confidence=0.5, impact="high",
            )

    def _load_json(self, agent_name: str, filename: str) -> dict:
        path = self._read_prior_output(agent_name, filename)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, filename: str, data: dict) -> None:
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
