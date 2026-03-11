from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import yaml
from rich.console import Console

from .registry import PluginRegistry

console = Console()


@dataclass
class StepResult:
    ok: bool
    output: Any = None
    error: str | None = None


class WorkflowEngine:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.registry = PluginRegistry(os.path.join(self.base_dir, "registry"))
        self.runs_dir = os.path.join(self.base_dir, "runs")
        os.makedirs(self.runs_dir, exist_ok=True)

    def run_from_file(self, wf_path: str) -> Dict[str, Any]:
        wf_abspath = wf_path
        if not os.path.isabs(wf_path):
            wf_abspath = os.path.join(self.base_dir, wf_path)
        with open(wf_abspath, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)
        return self.run(wf, source=wf_abspath)

    def run(self, wf: Dict[str, Any], source: str | None = None) -> Dict[str, Any]:
        run_id = time.strftime("%Y%m%d-%H%M%S")
        trace_path = os.path.join(self.runs_dir, f"trace-{run_id}.jsonl")
        ctx: Dict[str, Any] = {"_run_id": run_id, "_source": source, "vars": wf.get("vars", {})}
        # Expose run metadata to workflow vars for downstream plugins (eval, logging).
        ctx["vars"].setdefault("_run_id", run_id)
        ctx["vars"].setdefault("_source", source)
        # Precompute trace path so plugins can read it.
        ctx["vars"].setdefault("_trace_path", trace_path)
        # Resolve ${ENV:...} and ${vars...} inside initial vars once.
        ctx["vars"] = self._format_obj(ctx["vars"], ctx)

        def trace(event: Dict[str, Any]):
            event = {"t": time.time(), **event}
            with open(trace_path, "a", encoding="utf-8") as tf:
                tf.write(json.dumps(event, ensure_ascii=False) + "\n")

        console.rule(f"RUN {run_id}")
        trace({"type": "run_start", "source": source, "workflow": wf.get("name")})

        for i, step in enumerate(wf.get("steps", []), start=1):
            trace({"type": "step_start", "i": i, "step": step})
            console.print(f"[bold]\nStep {i}:[/bold] {step.get('name','(unnamed)')}")

            r = self._exec_step(step, ctx)
            trace({"type": "step_end", "i": i, "ok": r.ok, "output": r.output, "error": r.error})

            if not r.ok:
                # Self-repair mode: allow specific steps to fail without aborting the whole run.
                # This is a key capability for moving from planner-agent -> self-repair-agent.
                if step.get("allow_fail") is True:
                    ctx["vars"]["_last_error"] = {
                        "i": i,
                        "name": step.get("name"),
                        "kind": step.get("kind"),
                        "error": r.error,
                    }
                    # If the workflow expects a variable, write a structured error object.
                    if step.get("save_as"):
                        ctx["vars"][step["save_as"]] = {"ok": False, "error": r.error}
                    trace({"type": "step_allowed_fail", "i": i, "error": r.error})
                    console.print(f"[yellow]Step {i} failed but allow_fail=true; continuing.[/yellow]")
                    continue

                trace({"type": "run_end", "ok": False})
                return {"ok": False, "error": r.error, "run_id": run_id, "trace": trace_path}

            # 写回变量
            if step.get("save_as"):
                ctx["vars"][step["save_as"]] = r.output

        trace({"type": "run_end", "ok": True})
        return {"ok": True, "vars": ctx["vars"], "run_id": run_id, "trace": trace_path}

    def _exec_step(self, step: Dict[str, Any], ctx: Dict[str, Any]) -> StepResult:
        kind = step.get("kind")

        if kind == "echo":
            text = step.get("text", "")
            return StepResult(True, self._format(text, ctx))

        if kind == "plugin":
            plugin_name = step["plugin"]
            fn_name = step.get("fn", "run")
            args = step.get("args", {})
            args = self._format_obj(args, ctx)

            retries = int(step.get("retries") or 0)
            retry_delay = float(step.get("retry_delay_sec") or 1.0)
            attempt = 0
            last_err: str | None = None

            while attempt <= retries:
                try:
                    fn = self.registry.load_callable(plugin_name, fn_name)
                    out = fn(**args)
                    return StepResult(True, out)
                except Exception as e:
                    attempt += 1
                    last_err = f"Plugin {plugin_name}.{fn_name} failed (attempt {attempt}/{retries+1}): {e}"
                    if attempt > retries:
                        break
                    time.sleep(retry_delay)

            return StepResult(False, error=last_err)

        if kind == "synthesize_plugin":
            # MVP: 先不真的调用 LLM 生成代码；只把 spec 落盘，让你手工/后续接入生成器。
            spec = step.get("spec", {})
            spec = self._format_obj(spec, ctx)
            try:
                rec = self.registry.create_skeleton_from_spec(spec)
                return StepResult(True, rec)
            except Exception as e:
                return StepResult(False, error=f"synthesize_plugin failed: {e}")

        return StepResult(False, error=f"Unknown step kind: {kind}")

    def _format(self, template: str, ctx: Dict[str, Any]) -> str:
        """简单模板替换：

        - ${vars.x}  来自工作流变量
        - ${ENV:NAME} 来自环境变量（用于 daemon 注入目标）
        """
        s = template

        # env
        import os
        while "${ENV:" in s:
            start = s.find("${ENV:")
            end = s.find("}", start)
            if end == -1:
                break
            key = s[start + len("${ENV:") : end]
            val = os.environ.get(key, "")
            s = s[:start] + val + s[end + 1 :]

        # vars: support ${vars.x} and nested ${vars.a.b.c}
        import re

        def get_path(root, path: str):
            cur = root
            for part in path.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return None
            return cur

        pat = re.compile(r"\$\{vars\.([A-Za-z0-9_\.]+)\}")
        while True:
            m = pat.search(s)
            if not m:
                break
            keypath = m.group(1)
            val = get_path(ctx.get("vars", {}), keypath)
            s = s[: m.start()] + ("" if val is None else str(val)) + s[m.end() :]

        return s

    def _format_obj(self, obj: Any, ctx: Dict[str, Any]) -> Any:
        if isinstance(obj, str):
            # If the whole string is a single ${vars.path} token and the value is non-string,
            # return the underlying object to support passing lists/dicts into plugins.
            import re
            m = re.fullmatch(r"\$\{vars\.([A-Za-z0-9_\.]+)\}", obj)
            if m:
                keypath = m.group(1)
                def get_path(root, path: str):
                    cur = root
                    for part in path.split("."):
                        if isinstance(cur, dict) and part in cur:
                            cur = cur[part]
                        else:
                            return None
                    return cur
                val = get_path(ctx.get("vars", {}), keypath)
                if val is not None and not isinstance(val, str):
                    return val
            return self._format(obj, ctx)
        if isinstance(obj, list):
            return [self._format_obj(x, ctx) for x in obj]
        if isinstance(obj, dict):
            # Special case: if dict has only one key and its value is a string template,
            # still format normally.
            return {k: self._format_obj(v, ctx) for k, v in obj.items()}
        return obj
