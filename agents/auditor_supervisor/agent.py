"""
agents/auditor_supervisor/agent.py
Verifies traceability and generates the final audit report.
"""
from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from urllib import error, parse, request

from shared.base_agent import BaseAgent, OUTPUT_ROOT
from shared.channel import read_messages
from shared.llm_client import call_claude, call_claude_json
from shared.message_schema import AgentName, MessageType

logger = logging.getLogger(__name__)

AUDITOR_SYSTEM = """
You are a meticulous research software auditor. Verify that generated code faithfully 
implements the original research paper. Be precise about fidelity. Respond ONLY with valid JSON
unless asked for Markdown.
"""


class AuditorSupervisorAgent(BaseAgent):
    name = AgentName.AUDITOR_SUPERVISOR

    def _execute(self) -> None:
        self._check_pipeline_errors()

        # Load all prior outputs
        intent = self._load_json("paper_analyst", "research_intent.json")
        rqs = self._load_json("paper_analyst", "research_questions.json")
        methods = self._load_json("paper_analyst", "methods_models.json")
        metrics = self._load_json("paper_analyst", "metrics_results.json")
        requirements = self._load_json("formalizer", "functional_requirements.json")
        ambiguity_log = self._load_json("formalizer", "ambiguity_log.json")
        architecture_md = self._read_prior_output("architect_developer", "architecture.md").read_text()
        assumptions = self._load_assumptions()

        self._post(AgentName.BROADCAST, MessageType.STATUS, {"status": "auditing"})

        # Step 1: Code analysis
        code_inventory = self._analyze_code()
        generated_assets = self._collect_generated_assets()

        # Step 2: Traceability links
        traceability = self._build_traceability(requirements, code_inventory, methods)
        self._write("traceability_links.json", traceability)

        # Step 3: Gap detection
        gaps = self._detect_gaps(requirements, traceability)
        self._write("gaps.json", gaps)

        # Step 4: Human review points
        review_points = self._identify_review_points(gaps, ambiguity_log, traceability)
        self._write("human_review_points.json", review_points)

        # Step 5: Assumption deviation report
        deviation_report = self._build_deviation_report(assumptions, traceability, code_inventory)
        self._write("assumption_deviation_report.json", deviation_report)

        # Step 6: Reference repo validation
        repo_inventory = self._build_reference_repo_inventory(intent)
        self._write("repo_comparison_inventory.json", repo_inventory)

        repo_coverage = self._build_repo_coverage_report(
            repo_inventory,
            requirements,
            traceability,
            code_inventory,
            generated_assets,
            architecture_md,
        )
        self._write("repo_coverage_report.json", repo_coverage)

        repo_gap_analysis = self._build_repo_gap_analysis(repo_coverage)
        self._write("repo_gap_analysis.json", repo_gap_analysis)

        validation_md = self._generate_validation_report(
            intent,
            repo_inventory,
            repo_coverage,
            repo_gap_analysis,
        )
        (self.output_dir / "validation_report.md").write_text(validation_md, encoding="utf-8")

        # Step 7: Final Markdown report
        report_md = self._generate_report(
            intent,
            traceability,
            gaps,
            review_points,
            deviation_report,
            architecture_md,
            repo_coverage,
            repo_gap_analysis,
        )
        (self.output_dir / "traceability_report.md").write_text(report_md, encoding="utf-8")

        # HITL-4
        artifact_refs = [
            f"outputs/{self.run_id}/auditor_supervisor/traceability_report.md",
            f"outputs/{self.run_id}/auditor_supervisor/gaps.json",
            f"outputs/{self.run_id}/auditor_supervisor/validation_report.md",
        ]
        self._request_human_review("HITL-4", artifact_refs)

        missing_critical = [
            g for g in gaps.get("items", [])
            if g.get("severity") == "critical"
        ]
        status = "requires_human_review" if missing_critical else "complete"

        self._post(
            to_agent=AgentName.BROADCAST,
            message_type=MessageType.OUTPUT,
            payload={"report_path": artifact_refs[0], "status": status},
            artifact_refs=artifact_refs,
        )
        logger.info("Audit complete. Status: %s", status)

    # ------------------------------------------------------------------
    # Supervisor: check for pipeline errors
    # ------------------------------------------------------------------

    def _check_pipeline_errors(self) -> None:
        errors = read_messages(run_id=self.run_id, message_type=MessageType.ERROR)
        if errors:
            error_summary = [
                {"agent": e.from_agent, "detail": e.error_detail, "retry": e.retry_count}
                for e in errors
            ]
            logger.warning("Pipeline had %d error(s): %s", len(errors), error_summary)
            self._log_assumption(
                f"Pipeline completed with {len(errors)} error(s); audit may be incomplete.",
                confidence=0.6, impact="high",
                context=json.dumps(error_summary),
            )

    # ------------------------------------------------------------------
    # Code analysis
    # ------------------------------------------------------------------

    def _analyze_code(self) -> dict:
        src_dir = OUTPUT_ROOT / self.run_id / "architect_developer" / "src"
        inventory: list[dict] = []

        if not src_dir.exists():
            logger.warning("src/ directory not found — skipping code analysis.")
            return {"functions": []}

        for py_file in src_dir.glob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        docstring = ast.get_docstring(node) or ""
                        # Extract # Implements: FR-XXX from comments via raw text
                        raw = py_file.read_text()
                        fr_refs = self._extract_fr_refs(raw, node.name)
                        inventory.append({
                            "file": str(py_file.relative_to(OUTPUT_ROOT / self.run_id)),
                            "function": node.name,
                            "line": node.lineno,
                            "docstring": docstring[:200],
                            "fr_refs": fr_refs,
                        })
            except SyntaxError as e:
                logger.warning("Syntax error in %s: %s", py_file, e)

        return {"functions": inventory}

    def _collect_generated_assets(self) -> dict:
        base_dir = OUTPUT_ROOT / self.run_id / "architect_developer"
        src_dir = base_dir / "src"
        tests_dir = base_dir / "tests"

        src_files = (
            sorted(str(path.relative_to(base_dir)) for path in src_dir.rglob("*.py"))
            if src_dir.exists()
            else []
        )
        test_files = (
            sorted(str(path.relative_to(base_dir)) for path in tests_dir.rglob("*.py"))
            if tests_dir.exists()
            else []
        )
        deployment_files = [
            name
            for name in ["Dockerfile", "requirements.txt", "deployment_config.json", "api_spec.json"]
            if (base_dir / name).exists()
        ]
        return {
            "src_files": src_files,
            "test_files": test_files,
            "deployment_files": deployment_files,
            "has_architecture": (base_dir / "architecture.md").exists(),
        }

    @staticmethod
    def _extract_fr_refs(source: str, fn_name: str) -> list[str]:
        import re
        pattern = rf"def {fn_name}[^#]*#\s*Implements:\s*([\w,\s-]+)"
        match = re.search(pattern, source)
        if match:
            return [r.strip() for r in match.group(1).split(",")]
        return []

    # ------------------------------------------------------------------
    # Traceability
    # ------------------------------------------------------------------

    def _build_traceability(self, requirements: dict, code_inventory: dict, methods: dict) -> dict:
        return call_claude_json(
            system=AUDITOR_SYSTEM,
            user=f"""Build traceability links between requirements and code.

Return JSON:
{{
  "links": [{{
    "requirement_id": "FR-001",
    "requirement_desc": "...",
    "code_locations": [{{"file": "...", "function": "...", "line": 0}}],
    "fidelity": "exact|approximate|missing",
    "notes": ""
  }}]
}}

REQUIREMENTS:
{json.dumps(requirements.get("items", []), indent=2)[:5000]}

CODE INVENTORY:
{json.dumps(code_inventory.get("functions", []), indent=2)[:5000]}

METHODS FROM PAPER:
{json.dumps(methods.get("items", []), indent=2)[:3000]}""",
        )

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    def _detect_gaps(self, requirements: dict, traceability: dict) -> dict:
        missing = [
            link for link in traceability.get("links", [])
            if link.get("fidelity") == "missing"
        ]
        critical_ids = {
            r["id"] for r in requirements.get("items", [])
            if r.get("priority") == "must"
        }
        items = []
        for link in missing:
            items.append({
                "requirement_id": link["requirement_id"],
                "description": link.get("requirement_desc", ""),
                "severity": "critical" if link["requirement_id"] in critical_ids else "major",
                "recommendation": "Implement or map to existing code.",
            })
        return {"items": items, "total_missing": len(items)}

    # ------------------------------------------------------------------
    # Human review points
    # ------------------------------------------------------------------

    def _identify_review_points(
        self, gaps: dict, ambiguity_log: dict, traceability: dict
    ) -> dict:
        return call_claude_json(
            system=AUDITOR_SYSTEM,
            user=f"""Identify items that require human expert review.
Consider: critical gaps, unresolved ambiguities, approximate fidelity links.

Return JSON:
{{
  "items": [{{
    "id": "HRP-001",
    "type": "gap|ambiguity|fidelity_concern",
    "description": "...",
    "priority": "critical|high|medium",
    "context": "..."
  }}]
}}

GAPS:
{json.dumps(gaps.get("items", []), indent=2)}

AMBIGUITIES (unresolved):
{json.dumps([a for a in ambiguity_log.get("items", []) if not a.get("resolved")], indent=2)[:3000]}

APPROXIMATE LINKS:
{json.dumps([l for l in traceability.get("links", []) if l.get("fidelity") == "approximate"], indent=2)[:3000]}""",
        )

    # ------------------------------------------------------------------
    # Assumption deviation report
    # ------------------------------------------------------------------

    def _build_deviation_report(
        self, assumptions: list[dict], traceability: dict, code_inventory: dict
    ) -> dict:
        return call_claude_json(
            system=AUDITOR_SYSTEM,
            user=f"""Identify deviations between stated assumptions and the actual implementation.

Return JSON:
{{
  "deviations": [{{
    "assumption_id": "...",
    "assumption": "...",
    "agent": "...",
    "deviation": "...",
    "impact": "low|medium|high",
    "code_evidence": "..."
  }}],
  "total_deviations": 0
}}

ASSUMPTIONS MADE DURING PIPELINE:
{json.dumps(assumptions[:30], indent=2)}

TRACEABILITY LINKS:
{json.dumps(traceability.get("links", [])[:20], indent=2)[:4000]}""",
        )

    # ------------------------------------------------------------------
    # Reference repo validation
    # ------------------------------------------------------------------

    def _build_reference_repo_inventory(self, intent: dict) -> dict:
        repo_url = self._resolve_reference_repo_url(intent)
        if not repo_url:
            return {
                "status": "unavailable",
                "repo_url": None,
                "reason": "No repo.txt found next to the input paper.",
                "components": [],
            }

        parsed = self._parse_github_repo(repo_url)
        if not parsed:
            return {
                "status": "unsupported",
                "repo_url": repo_url,
                "reason": "Only GitHub repository URLs are supported for automated comparison.",
                "components": [],
            }

        owner, repo = parsed
        try:
            repo_meta = self._fetch_json(f"https://api.github.com/repos/{owner}/{repo}")
            default_branch = repo_meta.get("default_branch", "main")
            tree = self._fetch_json(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
            )
            paths = sorted(
                item["path"]
                for item in tree.get("tree", [])
                if item.get("type") == "blob"
            )
            sampled_paths = self._select_reference_paths(paths)
            sampled_files = {
                path: self._fetch_github_file(owner, repo, default_branch, path)
                for path in sampled_paths
            }
        except Exception as exc:
            logger.warning("Reference repo inventory failed for %s: %s", repo_url, exc)
            return {
                "status": "error",
                "repo_url": repo_url,
                "reason": str(exc),
                "components": [],
            }

        raw_inventory = {
            "repo_url": repo_url,
            "repo_name": f"{owner}/{repo}",
            "default_branch": default_branch,
            "path_count": len(paths),
            "paths": paths[:300],
            "sampled_files": sampled_files,
        }
        inventory = call_claude_json(
            system=AUDITOR_SYSTEM,
            user=f"""Summarize the reference repository into a compact software inventory.

Return JSON:
{{
  "status": "ok",
  "repo_url": "{repo_url}",
  "repo_name": "{owner}/{repo}",
  "default_branch": "{default_branch}",
  "structure_summary": {{
    "python_files": 0,
    "test_files": 0,
    "configs": [],
    "experiments": []
  }},
  "components": [{{
    "name": "...",
    "category": "module|pipeline|experiment|test|deployment|dataset|utility",
    "purpose": "...",
    "evidence": ["path/to/file.py"]
  }}],
  "notable_existing_functionality": ["..."],
  "test_assets": ["..."],
  "deployment_assets": ["..."],
  "notes": ["..."]
}}

REFERENCE REPO SNAPSHOT:
{json.dumps(raw_inventory, indent=2)[:14000]}""",
        )
        inventory["raw_snapshot"] = {
            "path_count": len(paths),
            "sampled_paths": sampled_paths,
        }
        return inventory

    def _build_repo_coverage_report(
        self,
        repo_inventory: dict,
        requirements: dict,
        traceability: dict,
        code_inventory: dict,
        generated_assets: dict,
        architecture_md: str,
    ) -> dict:
        if repo_inventory.get("status") != "ok":
            return {
                "status": "skipped",
                "summary": {
                    "overall_coverage": 0,
                    "structure_coverage": 0,
                    "functionality_coverage": 0,
                    "tests_coverage": 0,
                    "deployment_coverage": 0,
                },
                "matched_components": [],
                "partial_components": [],
                "missing_components": [],
                "extra_generated_components": [],
                "notes": [repo_inventory.get("reason", "Reference repo inventory unavailable.")],
            }

        return call_claude_json(
            system=AUDITOR_SYSTEM,
            user=f"""Compare generated artifacts against the reference repository and score coverage.

Return JSON:
{{
  "status": "ok",
  "summary": {{
    "overall_coverage": 0,
    "structure_coverage": 0,
    "functionality_coverage": 0,
    "tests_coverage": 0,
    "deployment_coverage": 0
  }},
  "matched_components": [{{
    "name": "...",
    "category": "module|pipeline|experiment|test|deployment|dataset|utility",
    "coverage": "full",
    "reference_evidence": ["..."],
    "generated_evidence": ["..."],
    "notes": ""
  }}],
  "partial_components": [{{
    "name": "...",
    "category": "module|pipeline|experiment|test|deployment|dataset|utility",
    "coverage": "partial",
    "reference_evidence": ["..."],
    "generated_evidence": ["..."],
    "notes": ""
  }}],
  "missing_components": [{{
    "name": "...",
    "category": "module|pipeline|experiment|test|deployment|dataset|utility",
    "reason": "...",
    "reference_evidence": ["..."],
    "suggested_requirement_ids": ["FR-001"]
  }}],
  "extra_generated_components": [{{
    "name": "...",
    "category": "module|test|deployment|utility",
    "generated_evidence": ["..."],
    "notes": ""
  }}],
  "notes": ["..."]
}}

REFERENCE INVENTORY:
{json.dumps(repo_inventory, indent=2)[:7000]}

GENERATED ASSETS:
{json.dumps(generated_assets, indent=2)[:3000]}

GENERATED CODE INVENTORY:
{json.dumps(code_inventory, indent=2)[:4000]}

TRACEABILITY:
{json.dumps(traceability, indent=2)[:4000]}

REQUIREMENTS:
{json.dumps(requirements.get("items", []), indent=2)[:4000]}

ARCHITECTURE:
{architecture_md[:2500]}""",
        )

    def _build_repo_gap_analysis(self, repo_coverage: dict) -> dict:
        missing = repo_coverage.get("missing_components", [])
        partial = repo_coverage.get("partial_components", [])
        return {
            "status": repo_coverage.get("status", "unknown"),
            "missing_count": len(missing),
            "partial_count": len(partial),
            "items": [
                {
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "coverage": "missing",
                    "details": item.get("reason", ""),
                    "reference_evidence": item.get("reference_evidence", []),
                    "suggested_requirement_ids": item.get("suggested_requirement_ids", []),
                }
                for item in missing
            ] + [
                {
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "coverage": "partial",
                    "details": item.get("notes", ""),
                    "reference_evidence": item.get("reference_evidence", []),
                    "suggested_requirement_ids": [],
                }
                for item in partial
            ],
        }

    def _generate_validation_report(
        self,
        intent: dict,
        repo_inventory: dict,
        repo_coverage: dict,
        repo_gap_analysis: dict,
    ) -> str:
        return call_claude(
            system="You are a technical auditor. Write a precise Markdown validation report.",
            user=f"""Generate a Markdown report comparing the generated implementation against the reference repository.

Include sections:
1. Reference Repository Summary
2. Coverage Scorecard
3. Matched Components
4. Partial Coverage
5. Missing Functionality
6. Recommendation

PAPER: {intent.get('paper_path', 'Unknown')}
REFERENCE INVENTORY: {json.dumps(repo_inventory, indent=2)[:5000]}
REPO COVERAGE: {json.dumps(repo_coverage, indent=2)[:5000]}
REPO GAPS: {json.dumps(repo_gap_analysis, indent=2)[:3000]}""",
        )

    # ------------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------------

    def _generate_report(
        self,
        intent: dict,
        traceability: dict,
        gaps: dict,
        review_points: dict,
        deviation_report: dict,
        architecture_md: str,
        repo_coverage: dict,
        repo_gap_analysis: dict,
    ) -> str:
        links = traceability.get("links", [])
        total = len(links)
        exact = sum(1 for l in links if l.get("fidelity") == "exact")
        approx = sum(1 for l in links if l.get("fidelity") == "approximate")
        missing = gaps.get("total_missing", 0)

        return call_claude(
            system="You are a technical writer. Generate a detailed Markdown audit report.",
            user=f"""Generate a comprehensive traceability report in Markdown.

Include sections:
1. Executive Summary (fidelity score: {exact}/{total} exact, {approx} approximate, {missing} missing)
2. Paper Overview
3. Traceability Matrix (table)
4. Gap Analysis
5. Reference Repo Coverage Summary
6. Human Review Points
7. Assumption Deviation Report
8. Recommendations

PAPER TITLE: {intent.get('paper_path', 'Unknown')}
TRACEABILITY: {json.dumps(traceability, indent=2)[:4000]}
GAPS: {json.dumps(gaps, indent=2)[:2000]}
REPO COVERAGE: {json.dumps(repo_coverage, indent=2)[:2500]}
REPO GAPS: {json.dumps(repo_gap_analysis, indent=2)[:2000]}
REVIEW POINTS: {json.dumps(review_points, indent=2)[:2000]}
DEVIATIONS: {json.dumps(deviation_report, indent=2)[:2000]}""",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_assumptions(self) -> list[dict]:
        path = OUTPUT_ROOT / self.run_id / "assumptions.jsonl"
        if not path.exists():
            return []
        assumptions = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    assumptions.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return assumptions

    def _load_json(self, agent_name: str, filename: str) -> dict:
        path = self._read_prior_output(agent_name, filename)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, filename: str, data: dict) -> None:
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Wrote %s", path)

    @staticmethod
    def _resolve_reference_repo_url(intent: dict) -> str | None:
        paper_path = intent.get("paper_path")
        if not paper_path:
            return None
        repo_path = Path(paper_path).parent / "repo.txt"
        if not repo_path.exists():
            return None
        raw = repo_path.read_text(encoding="utf-8").strip()
        return raw or None

    @staticmethod
    def _parse_github_repo(repo_url: str) -> tuple[str, str] | None:
        parsed = parse.urlparse(repo_url)
        if parsed.netloc.lower() != "github.com":
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            return None
        return parts[0], parts[1].removesuffix(".git")

    @staticmethod
    def _select_reference_paths(paths: list[str], limit: int = 12) -> list[str]:
        preferred: list[str] = []
        keywords = (
            "readme",
            "requirements",
            "pyproject",
            "setup.py",
            "src/",
            "tests/",
            "train",
            "model",
            "dataset",
            "experiment",
        )
        for path in paths:
            lower = path.lower()
            if lower.endswith((".md", ".py", ".toml", ".txt", ".yaml", ".yml", ".json")) and any(
                key in lower for key in keywords
            ):
                preferred.append(path)
        if len(preferred) >= limit:
            return preferred[:limit]
        remaining = [
            path
            for path in paths
            if path not in preferred and path.lower().endswith((".py", ".md", ".toml", ".txt"))
        ]
        return (preferred + remaining)[:limit]

    @staticmethod
    def _fetch_json(url: str) -> dict:
        req = request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "research-to-software-auditor",
            },
        )
        try:
            with request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub request failed ({exc.code}): {body}") from exc

    @staticmethod
    def _fetch_github_file(owner: str, repo: str, branch: str, path: str) -> str:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        req = request.Request(url, headers={"User-Agent": "research-to-software-auditor"})
        try:
            with request.urlopen(req) as response:
                return response.read().decode("utf-8", errors="replace")[:4000]
        except error.HTTPError as exc:
            logger.warning("Skipping reference file %s: HTTP %s", path, exc.code)
            return ""
