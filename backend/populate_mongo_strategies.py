import asyncio
from pathlib import Path
import ast
import json
import os
import sys

# Add the project root to sys.path so we can import backend modules
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from backend.database import get_async_db

async def main():
    lib_path = ROOT / "strategies_lib"
    if not lib_path.exists():
        print(f"Directory not found: {lib_path}")
        return

    db = get_async_db()
    
    files = [f.name for f in lib_path.iterdir() if f.name.endswith(".py") and f.name not in ("__init__.py", "hyper.py")]
    
    for f in files:
        strat_id = f.replace(".py", "")
        name = strat_id.replace("_", " ").title()
        strategy_file = lib_path / f
        
        desc = None
        strat_tags = []
        try:
            with open(strategy_file, 'r', encoding='utf-8') as sf:
                tree = ast.parse(sf.read())
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        cls_doc = ast.get_docstring(node)
                        if cls_doc:
                            desc = cls_doc.strip().split('\n\n')[0].replace('\n', ' ')
                            break
                if not desc:
                    doc = ast.get_docstring(tree)
                    if doc:
                        desc = doc.strip().split('\n\n')[0].replace('\n', ' ')
                
                if desc:
                    if len(desc) > 150: desc = desc[:147] + "..."
                else:
                    desc = f"Quantitative trading logic for {name}."
                    
                content_lower = (desc or "").lower() + name.lower()
                if "reversion" in content_lower: strat_tags.append("Mean Reversion")
                if "trend" in content_lower: strat_tags.append("Trend Following")
                if "breakout" in content_lower: strat_tags.append("Breakout")
                if "scalp" in content_lower: strat_tags.append("Scalping")
                if "momentum" in content_lower: strat_tags.append("Momentum")
                if "grid" in content_lower: strat_tags.append("Grid")
                if "ob" in content_lower or "order block" in content_lower: strat_tags.append("Order Blocks")
                if "smc" in content_lower or "ict" in content_lower: strat_tags.append("SMC")
                if "volatil" in content_lower: strat_tags.append("Volatility")
                
                if not strat_tags:
                    strat_tags = ["Technical", "Indicator"]
        except Exception as e:
            print(f"Error parsing {f}: {e}")
            desc = f"Algorithmic model based on {name}."
            strat_tags = ["Quantitative"]

        doc = {
            "strategy_id": strat_id,
            "name": name,
            "description": desc,
            "tags": strat_tags
        }
        
        await db.strategies_metadata.update_one(
            {"strategy_id": strat_id},
            {"$set": doc},
            upsert=True
        )
        print(f"Upserted {strat_id} metadata.")

if __name__ == "__main__":
    asyncio.run(main())
