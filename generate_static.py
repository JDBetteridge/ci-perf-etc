from collections import defaultdict
import json
from pprint import pprint
import sqlite3

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True
)

con = sqlite3.connect('/home/jack/Documents/firedrake/firedrake/src/PyOP2/.pymon')
cur = con.cursor()

session_table = cur.execute('SELECT * FROM TEST_SESSIONS')
branchlist = list(set(json.loads(s[3])["pipeline_branch"] for s in session_table))
branchlist_safe = [b.replace('/', '-') for b in branchlist]

branch_template = env.get_template("branches.html")
with open('static/branches.html', 'w') as fh:
    fh.write(branch_template.render(
        branchlist=branchlist_safe,
    ))

metrics = env.get_template("two_col.html")
for branch in branchlist:
    branch_sessions = cur.execute(
        'SELECT RUN_DATE,SESSION_H'
        ' FROM TEST_SESSIONS'
        ' WHERE RUN_DESCRIPTION LIKE :branch_query',
        {'branch_query': f'%"pipeline_branch": "{branch}"%'}
    )
    sessions = tuple(s[1] for s in branch_sessions)
    testpath_table = cur.execute(
        'SELECT ITEM_FS_LOC,ITEM_VARIANT'
        ' FROM TEST_METRICS'
        f' WHERE SESSION_H IN ({",".join("?"*len(sessions))})',
        sessions
    )

    testpaths = defaultdict(list)
    for row in testpath_table:
        safe_key = row[0].replace('/', '_')
        safe_val = row[1].replace('[', '_').replace(']', '_').replace(', ', '_')
        testpaths[safe_key].append(safe_val)

    # ~ pprint(testpaths)
    testpaths2 = {}
    for key in list(testpaths.keys())[:2]:
        testpaths2[key] = testpaths[key]
    branch_safe = branch.replace('/', '-')
    with open(f'static/{branch_safe}.html', 'w') as fh:
        fh.write(metrics.render(
            branch=branch,
            branch_safe=branch_safe,
            testpaths=testpaths
        ))
