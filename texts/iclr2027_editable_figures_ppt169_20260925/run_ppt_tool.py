"""Run the installed PPT skill with project-local binary dependencies."""
from pathlib import Path
import sys, runpy
root = Path(__file__).resolve().parent
scripts = Path('C:/Users/phoen/.codex/skills/ppt-master/scripts')
allowed = {'svg_quality_checker.py', 'svg_to_pptx.py', 'svg_position_calculator.py'}
tool = sys.argv[1]
if tool not in allowed:
    raise SystemExit('Unsupported tool')
sys.path[:0] = [str(root/'.deps'), str(scripts)]
sys.argv = [str(scripts/tool)] + sys.argv[2:]
runpy.run_path(str(scripts/tool), run_name='__main__')
