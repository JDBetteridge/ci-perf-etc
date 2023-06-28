from argparse import ArgumentParser
# ~ from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import json
import os
from pathlib import Path
from pprint import pprint
from random import seed, randint
import sqlite3
from textwrap import wrap

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.patheffects import withStroke
import pandas as pd

seed(1000)
DPI = 100
URL = 'https://github.com/OP2/PyOP2'

# ~ SAVE_executor = ThreadPoolExecutor(max_workers=4)
# ~ SAVE_executor = ProcessPoolExecutor()

def save_and_close(fig, filename):
    fig.savefig(filename, bbox_inches='tight', dpi=DPI)
    plt.close(fig)

def timeseries_thumbnail(df, filename, **kwargs):
    # Turning off the layout engine and manually adjusting plots is ~33% speedup
    title = kwargs.pop('title', None)
    wrapped_title = wrap(title, 40)

    fig, ax = plt.subplots(1, 1)
    height = 2 + 0.4*(len(wrapped_title) - 1)
    fig.set_size_inches(4, height)
    fig.set_layout_engine('none')

    df.plot('ITEM_START_TIME', 'TOTAL_TIME', color="C0", ax=ax, legend=False, **kwargs)
    axy2 = ax.twinx()
    df.plot('ITEM_START_TIME', 'MEM_USAGE', color="C1", ax=axy2, legend=False, **kwargs)

    ax.set_title('\n'.join(wrapped_title))
    ax.set_xticklabels([])
    ax.set_xlabel(None)
    ax.set_yticklabels([])
    axy2.set_yticklabels([])
    # ~ SAVE_executor.submit(save_and_close, fig, filename)
    fig.subplots_adjust(bottom=0.22/height, top=1.74/height)
    fig.savefig(filename, dpi=DPI)
    plt.close(fig)


def timeseries(df, filename, branch='master', **kwargs):
    fig, axes = plt.subplots(1, 2)
    fig.set_size_inches(16, 4)
    fig.set_layout_engine('none')

    title = kwargs.pop('title', None)
    column = ['TOTAL_TIME', 'MEM_USAGE']
    ylabel = ['Execution time (s)', 'Memory use (MB)']

    for ii, ax in enumerate(axes):
        df.plot(
            'ITEM_START_TIME',
            column[ii],
            ax=ax,
            legend=False,
            color=f'C{ii}',
            marker='o',
            ylabel=ylabel[ii],
            **kwargs
        )
        # ~ points = ax.collections[0]
        # ~ points.set_urls([f'{URL}/blob/{commit}/{f}' for f in df['COMMIT']])
        xdata = ax.axes.lines[0].get_xdata()
        ydata = ax.axes.lines[0].get_ydata()
        # White outline of black text (always readable)
        path_effects = [withStroke(linewidth=2, foreground='w')]
        for label, fs_loc, x, y in zip(df['COMMIT'], df['ITEM_FS_LOC'], xdata, ydata):
            ax.annotate(
                label[:8],
                (x, y),
                xytext=(3, 3),
                textcoords='offset points',
                path_effects=path_effects,
                url=f'{URL}/blob/{label}/{fs_loc}'
            )

    fig.suptitle(title, url=f'{URL}/tree/{branch.replace("---", "/")}')
    # ~ SAVE_executor.submit(save_and_close, fig, filename)
    fig.subplots_adjust(left=0.075, right=0.95)
    fig.savefig(filename, dpi=DPI)
    plt.close(fig)


def plot_summary_scatter(df, filename, branch='master', **kwargs):
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches(6, 6)
    points = df.plot.scatter("TOTAL_TIME", "MEM_USAGE", marker='.', s=1, ax=ax, **kwargs)
    # ~ df.plot.scatter("TOTAL_TIME", "MEM_USAGE", ax=ax, **kwargs)
    # ~ rect = Rectangle((0, 0), 60, 4096, color='red', alpha=0.3)
    # ~ ax.add_patch(rect)
    points = ax.collections[0]
    points.set_urls([f'{URL}/blob/{branch.replace("---", "/")}/{f}' for f in df['ITEM_FS_LOC']])
    # Hovertext???
    # ~ points.set_url([f'{URL}/blob/{branch}/{f}' for f in df["ITEM_FS_LOC"]])
    # ~ for label, x, y in zip(df['ITEM_VARIANT'], xdata, ydata):
        # ~ branch = 'master'
        # ~ link = f'{URL}/blob/{branch}/{df["ITEM_FS_LOC"]}'
        # ~ ax.annotate(label[:8], (x, y))
    # ~ SAVE_executor.submit(save_and_close, fig, filename)
    fig.savefig(filename, dpi=DPI) #bbox_inches='tight'
    plt.close(fig)



def main(args):
    con = sqlite3.connect(args.db)
    cur = con.cursor()
    session_table = cur.execute('SELECT * FROM TEST_SESSIONS')
    for session in session_table:
        # ~ session_hash = session[0]
        df = pd.read_sql(
            'SELECT ITEM_FS_LOC,ITEM_VARIANT,TOTAL_TIME,CPU_USAGE,MEM_USAGE'
            ' FROM TEST_METRICS'
            ' WHERE SESSION_H= :session_hash',
            con,
            params={'session_hash': session[0]}
        )
        ci = json.loads(session[3])
        branch = ci.get('pipeline_branch', 'master').replace('/', '---')
        count = ci.get('pipeline_build_no', randint(0, 2000))
        plot_summary_scatter(df, f'{branch}_{count}.svg', branch=branch)

    session_table = cur.execute('SELECT * FROM TEST_SESSIONS')
    branches = list(set(json.loads(s[3])["pipeline_branch"] for s in session_table))
    session_table = cur.execute('SELECT SESSION_H,SCM_ID FROM TEST_SESSIONS')
    commit = {row[0]: row[1] for row in session_table}

    for branch in branches:
        directory = Path(branch.replace('/', '-'))
        directory.mkdir(exist_ok=True)
        branch_sessions = cur.execute(
            'SELECT RUN_DATE,SESSION_H'
            ' FROM TEST_SESSIONS'
            ' WHERE RUN_DESCRIPTION LIKE :branch_query',
            {'branch_query': f'%"pipeline_branch": "{branch}"%'}
        )
        sessions = tuple(s[1] for s in branch_sessions)
        df = pd.read_sql(
            'SELECT SESSION_H,ITEM_FS_LOC,ITEM_VARIANT,ITEM_START_TIME,TOTAL_TIME,MEM_USAGE'
            ' FROM TEST_METRICS'
            f' WHERE SESSION_H IN ({",".join("?"*len(sessions))})',
            con,
            params=sessions,
            parse_dates={'ITEM_START_TIME': {}}
        )

        df['TEST'] = df['ITEM_FS_LOC'] + '::' + df['ITEM_VARIANT']
        df['COMMIT'] = df['SESSION_H'].apply(commit.get)
        # ~ breakpoint()
        futures = []
        for test in df['TEST'].unique():
            safe_name = test.replace('/', '_').replace('[', '_').replace(']', '_').replace(', ', '_')
            thumbnail_filename = directory/Path(f'{safe_name}_thumb.png')
            filename = directory/Path(f'{safe_name}.svg')
            df_view = df[df['TEST']==test]
            timeseries_thumbnail(df_view, thumbnail_filename, title=test)
            timeseries(df_view, filename, branch=branch, title=test)
            # ~ futures.append(
                # ~ PLOT_executor.submit(timeseries_thumbnail, df_view, thumbnail_filename, title=test)
            # ~ )
            # ~ futures.append(
                # ~ PLOT_executor.submit(timeseries, df_view, filename, branch=branch, title=test)
            # ~ )
            # ~ for label, args, kwargs in fargs:
                # ~ filename = directory/Path(f'{safe_name}_{label}.png')
                # ~ timeseries_test(df[df['TEST']==test], filename, *args, title=test, **kwargs)
            # ~ break

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--db', type=str)
    # --url
    # --branch
    # --compare-branch=master
    args, _ = parser.parse_known_args()
    main(args)
