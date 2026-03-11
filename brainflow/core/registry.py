from __future__ import annotations

import importlib.util
import json
import os
from typing import Any, Callable, Dict


class PluginRegistry:
    def __init__(self, registry_dir: str):
        self.registry_dir = registry_dir
        self.plugins_dir = os.path.join(os.path.dirname(registry_dir), "plugins")
        os.makedirs(self.registry_dir, exist_ok=True)
        os.makedirs(self.plugins_dir, exist_ok=True)

    def load_callable(self, plugin_name: str, fn_name: str) -> Callable[..., Any]:
        # plugin_name 对应 plugins/<plugin_name>/plugin.py
        plugin_path = os.path.join(self.plugins_dir, plugin_name, "plugin.py")
        if not os.path.exists(plugin_path):
            raise FileNotFoundError(f"Plugin not found: {plugin_path}")

        module_name = f"brainflow_plugin_{plugin_name}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load plugin spec")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore

        fn = getattr(mod, fn_name, None)
        if fn is None:
            raise AttributeError(f"Function not found: {fn_name}")
        if not callable(fn):
            raise TypeError(f"Not callable: {fn_name}")
        return fn

    def create_skeleton_from_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """根据 spec 创建一个插件骨架（MVP）。

        spec 最小字段：
        - name: 插件名（文件夹名）
        - description: 描述
        - inputs: {arg: desc}
        - outputs: desc
        """
        name = spec.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("spec.name required")

        plugin_dir = os.path.join(self.plugins_dir, name)
        os.makedirs(plugin_dir, exist_ok=True)

        manifest = {
            "name": name,
            "description": spec.get("description", ""),
            "inputs": spec.get("inputs", {}),
            "outputs": spec.get("outputs", ""),
            "version": "0.0.1",
            "status": "draft",
            "generated_by": "brainflow-mvp",
        }

        with open(os.path.join(plugin_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        plugin_py = os.path.join(plugin_dir, "plugin.py")
        if not os.path.exists(plugin_py):
            with open(plugin_py, "w", encoding="utf-8") as f:
                f.write(
                    """\
# Auto-generated plugin skeleton (draft)
# Fill in `run()` and add tests before promoting to stable.

from typing import Any


def run(**kwargs) -> Any:
    \"\"\"Entry point. Replace with real implementation.\"\"\"
    return {"echo": kwargs}
"""
                )

        # 记录到 registry
        rec = {
            "name": name,
            "path": os.path.relpath(plugin_dir, os.path.dirname(self.registry_dir)),
            "manifest": manifest,
        }
        with open(os.path.join(self.registry_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)

        return rec
