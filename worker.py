import json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'engine'))
from xhs_engine.templates import run_templates
result=run_templates('',sys.argv[1],plan_path=sys.argv[2],pages_dir=sys.argv[3])
Path(sys.argv[1],'worker-result.json').write_text(json.dumps(result,ensure_ascii=False))
