#!/usr/bin/env python3
"""
Session Manager - Antigravity Kit
=================================
Analyzes project state, detects tech stack, tracks file statistics, and provides
a summary of the current session.

Usage:
    python .agent/scripts/session_manager.py status [path]
    python .agent/scripts/session_manager.py info [path]
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

def get_project_root(path: str) -> Path:
    return Path(path).resolve()

def analyze_package_json(root: Path) -> Dict[str, Any]:
    pkg_file = root / "package.json"
    if not pkg_file.exists():
        return {"type": "unknown", "dependencies": {}}
    
    try:
        with open(pkg_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        
        # Frontend and backend frameworks can coexist (e.g. React + Express)
        frontend = [("next", "Next.js"), ("nuxt", "Nuxt"), ("@remix-run/react", "Remix"),
                    ("astro", "Astro"), ("react", "React"), ("vue", "Vue"), ("svelte", "Svelte")]
        backend = [("@nestjs/core", "NestJS"), ("express", "Express"), ("fastify", "Fastify"),
                   ("hono", "Hono")]
        extras = [("tailwindcss", "Tailwind CSS"), ("prisma", "Prisma"), ("drizzle-orm", "Drizzle"),
                  ("typescript", "TypeScript"), ("vitest", "Vitest"), ("jest", "Jest"),
                  ("@playwright/test", "Playwright")]

        stack = []
        for group in (frontend, backend):
            match = next((label for dep, label in group if dep in all_deps), None)
            if match:
                stack.append(match)
        stack += [label for dep, label in extras if dep in all_deps]
        
        return {
            "name": data.get("name", "unnamed"),
            "version": data.get("version", "0.0.0"),
            "stack": stack,
            "scripts": list(data.get("scripts", {}).keys())
        }
    except Exception as e:
        return {"error": str(e)}

def detect_other_stacks(root: Path) -> List[str]:
    markers = [("pyproject.toml", "Python"), ("requirements.txt", "Python"), ("go.mod", "Go"),
               ("Cargo.toml", "Rust"), ("pubspec.yaml", "Flutter"), ("composer.json", "PHP"),
               ("Gemfile", "Ruby"), ("Dockerfile", "Docker")]
    found = []
    for marker, label in markers:
        if (root / marker).exists() and label not in found:
            found.append(label)
    return found

def count_files(root: Path) -> Dict[str, int]:
    stats = {"created": 0, "modified": 0, "total": 0}
    # Simple count for now, comprehensive tracking would require git diff or extensive history
    exclude = {".git", "node_modules", ".next", "dist", "build", ".agent", ".gemini", "__pycache__"}
    
    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in exclude]
        stats["total"] += len(files)
        
    return stats

def detect_features(root: Path) -> List[str]:
    # Heuristic: look at folder names in src/
    features = []
    src = root / "src"
    if src.exists():
        possible_dirs = ["components", "modules", "features", "app", "pages", "services"]
        for d in possible_dirs:
            p = src / d
            if p.exists() and p.is_dir():
                # List subdirectories as likely features
                for child in p.iterdir():
                    if child.is_dir():
                        features.append(child.name)
    return features[:10] # Limit to top 10

def print_status(root: Path):
    info = analyze_package_json(root)
    info["stack"] = info.get("stack", []) + detect_other_stacks(root)
    stats = count_files(root)
    features = detect_features(root)
    
    print("\n=== Project Status ===")
    print(f"\n📁 Project: {info.get('name', root.name)}")
    print(f"📂 Path: {root}")
    print(f"🏷️  Type: {', '.join(info['stack']) or 'Generic'}")
    print(f"📊 Status: Active")
    
    print("\n🔧 Tech Stack:")
    for tech in info.get('stack', []):
        print(f"   • {tech}")
        
    print(f"\n✅ Detected Modules/Features ({len(features)}):")
    for feat in features:
        print(f"   • {feat}")
    if not features:
        print("   (No distinct feature modules detected)")
        
    print(f"\n📄 Files: {stats['total']} total files tracked")
    print("\n====================\n")

def main():
    parser = argparse.ArgumentParser(description="Session Manager")
    parser.add_argument("command", choices=["status", "info"], help="Command to run")
    parser.add_argument("path", nargs="?", default=".", help="Project path")
    
    args = parser.parse_args()
    root = get_project_root(args.path)
    
    if args.command == "status":
        print_status(root)
    elif args.command == "info":
        print(json.dumps(analyze_package_json(root), indent=2))

if __name__ == "__main__":
    main()
