#!/usr/bin/env python3
"""
inspector.py  – workspace.sqlite inspector

Usage (web server):
    python3 bin/inspector.py <workspace.sqlite> [--port PORT]
    Open http://localhost:8765/ in a browser.

Usage (CLI / stdout):
    python3 bin/inspector.py <workspace.sqlite> <id> > out.svg

Options:
    -p, --port PORT    Port for the web server (default: 8765)
    -h, --help         Show this help message and exit

In the browser:
    /                  Index page — lists all spaces
    /?id=<id>          Detail SVG for any entity (page, blog post, space,
                       attachment, body content, comment, user)
    /?id=<id>&list=<type>
                       List view (pages, blog_posts, attachments, comments,
                       children, history, comments_by_user)

All SVG items are clickable <a href> links for navigation.
"""

import sys, sqlite3, json, math, html as _html, re
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

DB_PATH = None  # set at startup

# ── palette ──────────────────────────────────────────────────────────────────

COLORS = {
    'page':         ('#2563EB', '#DBEAFE', '#1D4ED8'),
    'blog_post':    ('#D97706', '#FEF3C7', '#B45309'),
    'attachment':   ('#059669', '#D1FAE5', '#047857'),
    'space':        ('#7C3AED', '#EDE9FE', '#6D28D9'),
    'user':         ('#DC2626', '#FEE2E2', '#B91C1C'),
    'body_content': ('#0891B2', '#CFFAFE', '#0E7490'),
    'comment':      ('#EA580C', '#FFEDD5', '#C2410C'),
    'label':        ('#475569', '#F1F5F9', '#334155'),
    'unknown':      ('#6B7280', '#F3F4F6', '#4B5563'),
}
ICONS = {
    'page': '📄', 'blog_post': '📝', 'attachment': '📎',
    'space': '🏠', 'user': '👤', 'body_content': '📦',
    'comment': '💬', 'label': '🏷', 'unknown': '❓',
}

# ── layout constants ──────────────────────────────────────────────────────────

CARD_W   = 290
CENTER_W = 340
LINE_H   = 18
PAD      = 10
HDR_H    = 38
CORNER   = 8
FONT     = "font-family='Segoe UI,system-ui,sans-serif'"
MONO     = "font-family='Consolas,monospace'"

SVG_STYLE = ("<style>a{cursor:pointer} a:hover rect{opacity:.85} "
             "a text{text-decoration:none}</style>")

# ── db helpers ────────────────────────────────────────────────────────────────

def qone(con, sql, *args):
    cur = con.execute(sql, args)
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    return dict(zip(cols, row)) if row else None

def qall(con, sql, *args):
    cur = con.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def jlist(val):
    try:
        return json.loads(val) if val else []
    except Exception:
        return []

def jdict(val):
    try:
        return json.loads(val) if val else {}
    except Exception:
        return {}

def strip_tags(text, maxlen=70):
    return re.sub(r'<[^>]+>', ' ', text or '').strip()[:maxlen]

def trunc(v, n=35):
    s = str(v) if v is not None else ''
    return s[:n] + '…' if len(s) > n else s

def h(s):
    return _html.escape(str(s)) if s is not None else ''

# ── URL helpers ───────────────────────────────────────────────────────────────

def url_id(entity_id):
    return f'/?id={entity_id}'

def url_list(entity_id, list_type):
    return f'/?id={entity_id}&list={list_type}'

# ── entity detection ──────────────────────────────────────────────────────────

def find_entity(con, id_str):
    try:
        iid = int(id_str)
    except ValueError:
        iid = None

    if iid is not None:
        for tbl, pk, typ in [
            ('pages',         'page_id',         'page'),
            ('blog_posts',    'page_id',          'blog_post'),
            ('attachments',   'attachment_id',    'attachment'),
            ('spaces',        'space_id',         'space'),
            ('body_contents', 'body_content_id',  'body_content'),
            ('comments',      'comment_id',       'comment'),
        ]:
            row = qone(con, f'SELECT * FROM {tbl} WHERE {pk} = ?', iid)
            if row:
                return typ, row

    row = qone(con, 'SELECT * FROM users WHERE user_key = ?', id_str)
    if row:
        return 'user', row

    raise ValueError(f'ID {id_str!r} not found in any known table.')

# ── center field builders ─────────────────────────────────────────────────────

def _cf_page(r):
    return [('id', r['page_id']), ('title', trunc(r.get('confluence_title'), 40)),
            ('wiki title', trunc(r.get('wiki_title'), 40)), ('status', r.get('content_status')),
            ('version', r.get('version')), ('modified', (r.get('revision_timestamp') or '')[:16]),
            ('last modifier', trunc(r.get('last_modifier'), 30)),
            ('orig version', r.get('original_version_id'))]

def _cf_blog(r):
    return [('id', r['page_id']), ('title', trunc(r.get('confluence_title'), 40)),
            ('wiki title', trunc(r.get('wiki_title'), 40)), ('status', r.get('content_status')),
            ('version', r.get('version')), ('modified', (r.get('revision_timestamp') or '')[:16]),
            ('last modifier', trunc(r.get('last_modifier'), 30))]

def _cf_attachment(r):
    return [('id', r['attachment_id']), ('filename', trunc(r.get('filename'), 40)),
            ('extension', r.get('file_extension')), ('status', r.get('content_status')),
            ('version', r.get('version')), ('modified', (r.get('revision_timestamp') or '')[:16]),
            ('modifier', trunc(r.get('last_modifier'), 30)),
            ('reference', trunc(r.get('attachment_reference'), 35))]

def _cf_space(r):
    return [('id', r['space_id']), ('key', r.get('space_key')),
            ('name', trunc(r.get('space_name'), 40)), ('prefix', trunc(r.get('space_prefix'), 35)),
            ('homepage', r.get('homepage_id')), ('desc id', r.get('description_id'))]

def _cf_user(r):
    props = jdict(r.get('properties'))
    return [('user_key', trunc(r.get('user_key'), 40)),
            ('wiki name', trunc(r.get('wiki_user_name'), 35)),
            ('email', trunc(r.get('email'), 40)),
            ('full name', trunc(props.get('fullName'), 35))]

def _cf_body(r):
    return [('id', r['body_content_id']), ('content_id', r.get('content_id')),
            ('class', r.get('class'))]

def _cf_comment(r):
    return [('id', r['comment_id']), ('container_id', r.get('container_id')),
            ('content_class', r.get('content_class')), ('status', r.get('content_status')),
            ('user_key', trunc(r.get('user_key'), 35)),
            ('created', (r.get('created') or '')[:16]),
            ('modified', (r.get('modified') or '')[:16])]

CENTER_FIELDS = {
    'page': _cf_page, 'blog_post': _cf_blog, 'attachment': _cf_attachment,
    'space': _cf_space, 'user': _cf_user, 'body_content': _cf_body, 'comment': _cf_comment,
}

# ── node builder ──────────────────────────────────────────────────────────────

def node(typ, label, fields, edge_label, href=None):
    return {'type': typ, 'label': label, 'fields': fields, 'edge': edge_label, 'href': href}

# ── shared gather helpers ─────────────────────────────────────────────────────

def _resolve_labels(con, labelling_ids):
    names = []
    for lid in labelling_ids[:8]:
        row = qone(con, '''SELECT l.name FROM labellings lg
                           JOIN labels l ON lg.label_id = l.label_id
                           WHERE lg.labelling_id = ?''', int(lid))
        if row:
            names.append(row['name'])
    return names

def _body_node(con, bcid, edge_lbl='has body'):
    bc = qone(con, 'SELECT * FROM body_contents WHERE body_content_id = ?', int(bcid))
    if not bc:
        return None
    body = qone(con, 'SELECT body FROM body_content_bodies WHERE body_content_id = ?', int(bcid))
    invalid = qone(con, 'SELECT text FROM body_content_invalids WHERE body_content_id = ?', int(bcid))
    excerpt = strip_tags(body['body'] if body else '', 65) if body else ''
    return node('body_content', f'body {bcid}', [
        ('class', bc['class']),
        ('excerpt', excerpt or '(empty)'),
        ('invalid', '⚠ yes' if invalid else 'no'),
    ], edge_lbl, href=url_id(bcid))

def _page_bcs(con, page_id, body_content_ids_json):
    bcs = qall(con, 'SELECT body_content_id FROM body_contents WHERE content_id = ? LIMIT 3', page_id)
    if not bcs:
        bcs = [{'body_content_id': x} for x in jlist(body_content_ids_json)[:3]]
    return bcs

# ── gatherers ─────────────────────────────────────────────────────────────────

def gather_page(con, row):
    nodes = []
    pid = row['page_id']
    coll = jdict(row.get('collection'))

    # If this is a historic version, link back to the current version first
    orig_id = row.get('original_version_id')
    if orig_id and orig_id != -1 and orig_id != pid:
        cur = qone(con, 'SELECT page_id, confluence_title, version, content_status FROM pages WHERE page_id = ?', orig_id)
        if cur:
            nodes.append(node('page', trunc(cur['confluence_title'], 28), [
                ('id', cur['page_id']), ('version', cur['version']), ('status', cur['content_status'])
            ], 'current version', href=url_id(cur['page_id'])))

    sp = qone(con, 'SELECT * FROM spaces WHERE space_id = ?', row['space_id'])
    if sp:
        nodes.append(node('space', sp['space_key'], [
            ('name', trunc(sp['space_name'], 30)), ('id', sp['space_id'])
        ], 'in space', href=url_id(sp['space_id'])))

    if row.get('parent_page_id'):
        pp = qone(con, 'SELECT page_id, confluence_title, content_status FROM pages WHERE page_id = ?', row['parent_page_id'])
        if pp:
            nodes.append(node('page', trunc(pp['confluence_title'], 28), [
                ('id', pp['page_id']), ('status', pp['content_status'])
            ], 'child of', href=url_id(pp['page_id'])))

    for bc in _page_bcs(con, pid, row.get('body_content_ids')):
        n = _body_node(con, bc['body_content_id'])
        if n:
            nodes.append(n)

    hist = jlist(row.get('historical_ids'))
    for hid in hist[:3]:
        hp = qone(con, 'SELECT page_id, version, content_status FROM pages WHERE page_id = ?', int(hid))
        if hp:
            nodes.append(node('page', f'v{hp["version"]} (hist)', [
                ('id', hp['page_id']), ('status', hp['content_status'])
            ], 'historical', href=url_id(hp['page_id'])))
    if len(hist) > 3:
        nodes.append(node('page', f'+{len(hist)-3} more versions', [],
                          'historical', href=url_list(pid, 'history')))

    atts = qall(con, 'SELECT * FROM page_attachments WHERE page_id = ? LIMIT 4', pid)
    total_atts = con.execute('SELECT COUNT(*) FROM page_attachments WHERE page_id = ?', (pid,)).fetchone()[0]
    for a in atts:
        nodes.append(node('attachment', trunc(a.get('original_attachment_filename'), 28), [
            ('id', a['attachment_id']),
            ('target', trunc(a.get('target_attachment_filename'), 32)),
        ], 'attachment', href=url_id(a['attachment_id'])))
    if total_atts > 4:
        nodes.append(node('attachment', f'+{total_atts-4} more', [],
                          'attachment', href=url_list(pid, 'attachments')))

    comm_count = con.execute('SELECT COUNT(*) FROM page_comments WHERE page_id = ?', (pid,)).fetchone()[0]
    if comm_count:
        nodes.append(node('comment', f'{comm_count} comment(s)', [],
                          'has comments', href=url_list(pid, 'comments')))

    children_ids = coll.get('childrens', [])
    for cid in children_ids[:4]:
        cp = qone(con, 'SELECT page_id, confluence_title, content_status FROM pages WHERE page_id = ?', int(cid))
        if cp:
            nodes.append(node('page', trunc(cp['confluence_title'], 28), [
                ('id', cp['page_id']), ('status', cp['content_status'])
            ], 'parent of', href=url_id(cp['page_id'])))
    if len(children_ids) > 4:
        nodes.append(node('page', f'+{len(children_ids)-4} more children', [],
                          'parent of', href=url_list(pid, 'children')))

    label_names = _resolve_labels(con, coll.get('labellings', []))
    if label_names:
        nodes.append(node('label', 'labels', [('names', trunc(', '.join(label_names), 40))], 'labelled as'))

    return nodes

def gather_blog_post(con, row):
    nodes = []
    pid = row['page_id']
    coll = jdict(row.get('collection'))

    orig_id = row.get('original_version_id')
    if orig_id and orig_id != -1 and orig_id != pid:
        cur = qone(con, 'SELECT page_id, confluence_title, version, content_status FROM blog_posts WHERE page_id = ?', orig_id)
        if cur:
            nodes.append(node('blog_post', trunc(cur['confluence_title'], 28), [
                ('id', cur['page_id']), ('version', cur['version']), ('status', cur['content_status'])
            ], 'current version', href=url_id(cur['page_id'])))

    sp = qone(con, 'SELECT * FROM spaces WHERE space_id = ?', row['space_id'])
    if sp:
        nodes.append(node('space', sp['space_key'], [
            ('name', trunc(sp['space_name'], 30)), ('id', sp['space_id'])
        ], 'in space', href=url_id(sp['space_id'])))

    for bc in _page_bcs(con, pid, row.get('body_content_ids')):
        n = _body_node(con, bc['body_content_id'])
        if n:
            nodes.append(n)

    hist = jlist(row.get('historical_ids'))
    for hid in hist[:3]:
        hp = qone(con, 'SELECT page_id, version, content_status FROM blog_posts WHERE page_id = ?', int(hid))
        if hp:
            nodes.append(node('blog_post', f'v{hp["version"]} (hist)', [
                ('id', hp['page_id']), ('status', hp['content_status'])
            ], 'historical', href=url_id(hp['page_id'])))
    if len(hist) > 3:
        nodes.append(node('blog_post', f'+{len(hist)-3} more versions', [],
                          'historical', href=url_list(pid, 'history')))

    atts = qall(con, 'SELECT * FROM blog_post_attachments WHERE blog_post_id = ? LIMIT 4', pid)
    total_atts = con.execute('SELECT COUNT(*) FROM blog_post_attachments WHERE blog_post_id = ?', (pid,)).fetchone()[0]
    for a in atts:
        nodes.append(node('attachment', trunc(a.get('original_attachment_filename'), 28), [
            ('id', a['attachment_id']),
            ('target', trunc(a.get('target_attachment_filename'), 32)),
        ], 'attachment', href=url_id(a['attachment_id'])))
    if total_atts > 4:
        nodes.append(node('attachment', f'+{total_atts-4} more', [],
                          'attachment', href=url_list(pid, 'attachments')))

    comm_count = con.execute('SELECT COUNT(*) FROM blog_post_comments WHERE blog_post_id = ?', (pid,)).fetchone()[0]
    if comm_count:
        nodes.append(node('comment', f'{comm_count} comment(s)', [],
                          'has comments', href=url_list(pid, 'comments')))

    label_names = _resolve_labels(con, coll.get('labellings', []))
    if label_names:
        nodes.append(node('label', 'labels', [('names', trunc(', '.join(label_names), 40))], 'labelled as'))

    return nodes

def gather_attachment(con, row):
    nodes = []
    sp = qone(con, 'SELECT * FROM spaces WHERE space_id = ?', row['space_id'])
    if sp:
        nodes.append(node('space', sp['space_key'], [('name', trunc(sp['space_name'], 30))],
                          'in space', href=url_id(sp['space_id'])))

    cid = row.get('container_id')
    if cid:
        pg = qone(con, 'SELECT page_id, confluence_title FROM pages WHERE page_id = ?', cid)
        if pg:
            nodes.append(node('page', trunc(pg['confluence_title'], 28), [('id', pg['page_id'])],
                              'on page', href=url_id(pg['page_id'])))
        else:
            bp = qone(con, 'SELECT page_id, confluence_title FROM blog_posts WHERE page_id = ?', cid)
            if bp:
                nodes.append(node('blog_post', trunc(bp['confluence_title'], 28), [('id', bp['page_id'])],
                                  'on blog post', href=url_id(bp['page_id'])))

    for hid in jlist(row.get('historical_ids'))[:3]:
        ha = qone(con, 'SELECT attachment_id, version, content_status FROM attachments WHERE attachment_id = ?', int(hid))
        if ha:
            nodes.append(node('attachment', f'v{ha["version"]} (hist)', [
                ('id', ha['attachment_id']), ('status', ha['content_status'])
            ], 'historical', href=url_id(ha['attachment_id'])))

    coll = jdict(row.get('collection'))
    label_names = _resolve_labels(con, coll.get('labellings', []))
    if label_names:
        nodes.append(node('label', 'labels', [('names', trunc(', '.join(label_names), 40))], 'labelled as'))

    return nodes

def gather_space(con, row):
    nodes = []
    sid = row['space_id']

    if row.get('homepage_id'):
        hp = qone(con, 'SELECT page_id, confluence_title FROM pages WHERE page_id = ?', row['homepage_id'])
        if hp:
            nodes.append(node('page', trunc(hp['confluence_title'], 28), [('id', hp['page_id'])],
                              'homepage', href=url_id(hp['page_id'])))

    pg_count = con.execute('SELECT COUNT(*) FROM pages WHERE space_id = ?', (sid,)).fetchone()[0]
    bp_count = con.execute('SELECT COUNT(*) FROM blog_posts WHERE space_id = ?', (sid,)).fetchone()[0]
    att_count = con.execute('SELECT COUNT(*) FROM attachments WHERE space_id = ?', (sid,)).fetchone()[0]

    nodes.append(node('page', f'{pg_count} pages', [('space', row['space_key'])],
                      'contains', href=url_list(sid, 'pages')))
    nodes.append(node('blog_post', f'{bp_count} blog posts', [('space', row['space_key'])],
                      'contains', href=url_list(sid, 'blog_posts')))
    if att_count:
        nodes.append(node('attachment', f'{att_count} attachments', [],
                          'contains', href=url_list(sid, 'attachments')))

    if row.get('description_id'):
        sd = qone(con, 'SELECT * FROM spaces_descriptions WHERE space_description_id = ?', row['description_id'])
        if sd:
            for bcid in jlist(sd.get('body_content_ids'))[:1]:
                n = _body_node(con, bcid, 'description')
                if n:
                    nodes.append(n)

    return nodes

def gather_user(con, row):
    nodes = []
    uk = row['user_key']

    pages = qall(con, 'SELECT page_id, confluence_title FROM pages WHERE last_modifier = ? LIMIT 4', uk)
    for p in pages:
        nodes.append(node('page', trunc(p['confluence_title'], 28), [('id', p['page_id'])],
                          'last modified', href=url_id(p['page_id'])))

    bps = qall(con, 'SELECT page_id, confluence_title FROM blog_posts WHERE last_modifier = ? LIMIT 3', uk)
    for b in bps:
        nodes.append(node('blog_post', trunc(b['confluence_title'], 28), [('id', b['page_id'])],
                          'last modified', href=url_id(b['page_id'])))

    comm_count = con.execute('SELECT COUNT(*) FROM comments WHERE user_key = ?', (uk,)).fetchone()[0]
    if comm_count:
        nodes.append(node('comment', f'{comm_count} comment(s)', [],
                          'authored', href=url_list(uk, 'comments_by_user')))

    return nodes

def gather_body_content(con, row):
    nodes = []
    bcid = row['body_content_id']
    cid = row.get('content_id')

    body = qone(con, 'SELECT body FROM body_content_bodies WHERE body_content_id = ?', bcid)
    invalid = qone(con, 'SELECT text FROM body_content_invalids WHERE body_content_id = ?', bcid)

    if body and body.get('body'):
        excerpt = strip_tags(body['body'], 80)
        nodes.append(node('unknown', 'body text', [
            ('len', f'{len(body["body"])} chars'), ('excerpt', trunc(excerpt, 55))
        ], 'body'))
    if invalid:
        nodes.append(node('unknown', 'invalid body', [
            ('excerpt', trunc(strip_tags(invalid.get('text', ''), 55), 55))
        ], 'invalid body'))

    if cid:
        pg = qone(con, 'SELECT page_id, confluence_title FROM pages WHERE page_id = ?', cid)
        if pg:
            nodes.append(node('page', trunc(pg['confluence_title'], 28), [('id', pg['page_id'])],
                              'body of', href=url_id(pg['page_id'])))
        else:
            bp = qone(con, 'SELECT page_id, confluence_title FROM blog_posts WHERE page_id = ?', cid)
            if bp:
                nodes.append(node('blog_post', trunc(bp['confluence_title'], 28), [('id', bp['page_id'])],
                                  'body of', href=url_id(bp['page_id'])))

    return nodes

def gather_comment(con, row):
    nodes = []
    cid = row.get('container_id')
    uk = row.get('user_key')

    if uk:
        u = qone(con, 'SELECT wiki_user_name, email FROM users WHERE user_key = ?', uk)
        if u:
            nodes.append(node('user', trunc(u.get('wiki_user_name') or uk, 28), [
                ('email', trunc(u.get('email'), 35))
            ], 'by user', href=url_id(uk)))

    if cid:
        pg = qone(con, 'SELECT page_id, confluence_title FROM pages WHERE page_id = ?', cid)
        if pg:
            nodes.append(node('page', trunc(pg['confluence_title'], 28), [('id', pg['page_id'])],
                              'on page', href=url_id(pg['page_id'])))
        else:
            bp = qone(con, 'SELECT page_id, confluence_title FROM blog_posts WHERE page_id = ?', cid)
            if bp:
                nodes.append(node('blog_post', trunc(bp['confluence_title'], 28), [('id', bp['page_id'])],
                                  'on blog post', href=url_id(bp['page_id'])))

    for bcid in jlist(row.get('body_content_ids'))[:2]:
        n = _body_node(con, bcid)
        if n:
            nodes.append(n)

    return nodes

GATHERERS = {
    'page': gather_page, 'blog_post': gather_blog_post, 'attachment': gather_attachment,
    'space': gather_space, 'user': gather_user, 'body_content': gather_body_content,
    'comment': gather_comment,
}

# ── SVG card rendering ────────────────────────────────────────────────────────

def card_height(fields):
    visible = [(k, v) for k, v in fields if v is not None and v != '']
    return HDR_H + PAD + len(visible) * LINE_H + PAD

def render_card(x, y, typ, title, fields, width, shadow=False, href=None):
    fg, bg, border = COLORS.get(typ, COLORS['unknown'])
    visible = [(k, v) for k, v in fields if v is not None and v != '']
    ht = HDR_H + PAD + len(visible) * LINE_H + PAD
    cx = x - width / 2
    cy_top = y - ht / 2
    icon = ICONS.get(typ, '❓')
    parts = []

    if shadow:
        parts.append(f"<rect x='{cx+3}' y='{cy_top+3}' width='{width}' height='{ht}' "
                     f"rx='{CORNER}' fill='#00000022'/>")

    parts.append(f"<rect x='{cx}' y='{cy_top}' width='{width}' height='{ht}' rx='{CORNER}' "
                 f"fill='{bg}' stroke='{border}' stroke-width='1.5'/>")
    parts.append(f"<rect x='{cx}' y='{cy_top}' width='{width}' height='{HDR_H}' rx='{CORNER}' fill='{fg}'/>")
    parts.append(f"<rect x='{cx}' y='{cy_top+CORNER}' width='{width}' height='{HDR_H-CORNER}' fill='{fg}'/>")
    parts.append(f"<text x='{cx+PAD+4}' y='{cy_top+HDR_H/2+5}' {FONT} font-size='13' "
                 f"font-weight='600' fill='white'>{icon} {h(typ.replace('_',' '))} · {h(title)}</text>")

    fy = cy_top + HDR_H + PAD + LINE_H - 4
    for key, val in visible:
        parts.append(f"<text x='{cx+PAD+4}' y='{fy}' {MONO} font-size='10' fill='#64748B'>{h(key)}</text>")
        parts.append(f"<text x='{cx+PAD+92}' y='{fy}' {MONO} font-size='10' fill='#1E293B'>{h(val)}</text>")
        fy += LINE_H

    content = '\n'.join(parts)
    if href:
        content = f"<a href='{h(href)}'>\n{content}\n</a>"
    return content, cy_top, cy_top + ht

def edge_point(cx, cy, tx, ty, half_w, top_y, bot_y):
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1 and abs(dy) < 1:
        return cx, cy
    half_h = (bot_y - top_y) / 2
    if abs(dy) < 1:
        return cx + math.copysign(half_w, dx), cy
    if abs(dx) < 1:
        return cx, cy + math.copysign(half_h, dy)
    tx_e = half_w / abs(dx)
    ty_e = half_h / abs(dy)
    if tx_e < ty_e:
        return cx + math.copysign(half_w, dx), cy + dy * tx_e
    return cx + dx * ty_e, cy + math.copysign(half_h, dy)

def compute_radius(n):
    if n == 0:
        return 0
    MIN_GAP = 80
    r_center = CENTER_W / 2 + CARD_W / 2 + MIN_GAP
    r_adjacent = (CARD_W + MIN_GAP) / (2 * math.sin(math.pi / n)) if n > 1 else 0
    return max(r_center, r_adjacent)

def render_detail_svg(entity_type, center_label, center_fields, related_nodes, title=None):
    n = len(related_nodes)
    R = compute_radius(n)
    W = int(max(900, 2 * R + CARD_W + 60))
    H = int(max(700, 2 * R + 200))
    cx, cy = W // 2, H // 2

    lines_svg, cards_svg = [], []

    positions = [(cx + R * math.cos(2*math.pi*i/n - math.pi/2),
                  cy + R * math.sin(2*math.pi*i/n - math.pi/2))
                 for i in range(n)] if n else []

    cfields = [(k, v) for k, v in center_fields if v is not None and v != '']
    c_svg, c_top, c_bot = render_card(cx, cy, entity_type, center_label, cfields, CENTER_W, shadow=True)
    cards_svg.append(c_svg)

    for i, rn in enumerate(related_nodes):
        px, py = positions[i]
        r_svg, r_top, r_bot = render_card(px, py, rn['type'], rn['label'], rn['fields'],
                                           CARD_W, href=rn.get('href'))
        cards_svg.append(r_svg)

        ex1, ey1 = edge_point(cx, cy, px, py, CENTER_W/2, c_top, c_bot)
        ex2, ey2 = edge_point(px, py, cx, cy, CARD_W/2, r_top, r_bot)
        mx, my = (ex1+ex2)/2, (ey1+ey2)/2
        fg = COLORS.get(rn['type'], COLORS['unknown'])[0]
        lines_svg.append(
            f"<line x1='{ex1:.1f}' y1='{ey1:.1f}' x2='{ex2:.1f}' y2='{ey2:.1f}' "
            f"stroke='{fg}' stroke-width='1.5' stroke-dasharray='4,3' opacity='0.7'/>")
        lines_svg.append(
            f"<text x='{mx:.1f}' y='{my:.1f}' {FONT} font-size='10' fill='{fg}' "
            f"text-anchor='middle' dominant-baseline='middle' "
            f"style='paint-order:stroke;stroke:#fff;stroke-width:3px'>{h(rn['edge'])}</text>")

    svg_title = h(title or f'{entity_type.replace("_", " ").title()}: {center_label}')
    return '\n'.join([
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
        f"<title>{svg_title}</title>",
        SVG_STYLE,
        f"<rect width='{W}' height='{H}' fill='#F8FAFC'/>",
        "<pattern id='grid' width='30' height='30' patternUnits='userSpaceOnUse'>",
        "<circle cx='1' cy='1' r='1' fill='#CBD5E1' opacity='0.5'/>",
        "</pattern>",
        f"<rect width='{W}' height='{H}' fill='url(#grid)'/>",
        *lines_svg, *cards_svg,
        f"<text x='16' y='28' {FONT} font-size='13' fill='#94A3B8'>workspace.sqlite inspector</text>",
        "</svg>",
    ])

# ── list SVG ──────────────────────────────────────────────────────────────────

ROW_H  = 40
LIST_W = 820
LPAD   = 20
MAX_LIST = 100

def render_list_svg(con, id_str, list_type):
    try:
        entity_type, row = find_entity(con, id_str)
    except ValueError as e:
        return render_error_svg(str(e))

    # resolve entity label and primary key
    pk_map = {'page': 'page_id', 'blog_post': 'page_id', 'attachment': 'attachment_id',
              'space': 'space_id', 'user': 'user_key', 'body_content': 'body_content_id',
              'comment': 'comment_id'}
    eid = row[pk_map[entity_type]]

    # query items: (item_type, item_id, title, extra)
    items = []
    title = f'{list_type.replace("_", " ").title()} — {entity_type.replace("_"," ")} {eid}'

    if list_type == 'pages' and entity_type == 'space':
        for r in qall(con, 'SELECT page_id, confluence_title, content_status FROM pages WHERE space_id = ? ORDER BY confluence_title LIMIT 500', eid):
            items.append(('page', r['page_id'], r['confluence_title'], r['content_status']))

    elif list_type == 'blog_posts' and entity_type == 'space':
        for r in qall(con, 'SELECT page_id, confluence_title, content_status FROM blog_posts WHERE space_id = ? LIMIT 500', eid):
            items.append(('blog_post', r['page_id'], r['confluence_title'], r['content_status']))

    elif list_type == 'attachments':
        if entity_type == 'space':
            rows = qall(con, 'SELECT attachment_id, filename, content_status FROM attachments WHERE space_id = ? LIMIT 500', eid)
        elif entity_type == 'page':
            rows = qall(con, '''SELECT a.attachment_id, a.filename, a.content_status
                                FROM attachments a JOIN page_attachments pa ON pa.attachment_id = a.attachment_id
                                WHERE pa.page_id = ? LIMIT 200''', eid)
        elif entity_type == 'blog_post':
            rows = qall(con, '''SELECT a.attachment_id, a.filename, a.content_status
                                FROM attachments a JOIN blog_post_attachments ba ON ba.attachment_id = a.attachment_id
                                WHERE ba.blog_post_id = ? LIMIT 200''', eid)
        else:
            rows = []
        items = [('attachment', r['attachment_id'], r['filename'], r['content_status']) for r in rows]

    elif list_type == 'comments':
        if entity_type == 'page':
            rows = qall(con, '''SELECT c.comment_id, c.content_status, c.created
                                FROM comments c JOIN page_comments pc ON pc.comment_id = c.comment_id
                                WHERE pc.page_id = ? LIMIT 500''', eid)
        elif entity_type == 'blog_post':
            rows = qall(con, '''SELECT c.comment_id, c.content_status, c.created
                                FROM comments c JOIN blog_post_comments bpc ON bpc.comment_id = c.comment_id
                                WHERE bpc.blog_post_id = ? LIMIT 500''', eid)
        else:
            rows = []
        items = [('comment', r['comment_id'], f'Comment {r["comment_id"]}',
                  (r.get('created') or '')[:10]) for r in rows]

    elif list_type == 'comments_by_user' and entity_type == 'user':
        rows = qall(con, 'SELECT comment_id, content_status, created FROM comments WHERE user_key = ? LIMIT 500', eid)
        items = [('comment', r['comment_id'], f'Comment {r["comment_id"]}',
                  (r.get('created') or '')[:10]) for r in rows]

    elif list_type == 'children' and entity_type == 'page':
        rows = qall(con, 'SELECT page_id, confluence_title, content_status FROM pages WHERE parent_page_id = ? ORDER BY confluence_title LIMIT 500', eid)
        items = [('page', r['page_id'], r['confluence_title'], r['content_status']) for r in rows]

    elif list_type == 'history':
        hist_ids = jlist(row.get('historical_ids', '[]'))
        if entity_type in ('page', 'blog_post'):
            tbl, pk = ('pages', 'page_id') if entity_type == 'page' else ('blog_posts', 'page_id')
            for hid in hist_ids[:200]:
                hr = qone(con, f'SELECT * FROM {tbl} WHERE {pk} = ?', int(hid))
                if hr:
                    items.append((entity_type, hr[pk], f'v{hr.get("version","?")}',
                                  hr.get('content_status', '')))
        elif entity_type == 'attachment':
            for hid in hist_ids[:200]:
                hr = qone(con, 'SELECT * FROM attachments WHERE attachment_id = ?', int(hid))
                if hr:
                    items.append(('attachment', hr['attachment_id'], f'v{hr.get("version","?")}',
                                  hr.get('content_status', '')))
    else:
        return render_error_svg(f'Unknown list type {list_type!r} for entity type {entity_type!r}',
                                back_href=url_id(id_str))

    return _render_list(title, items, back_href=url_id(id_str), total_count=len(items))

def _render_list(title, items, back_href, total_count=None):
    capped = items[:MAX_LIST]
    n = len(capped)
    SVG_W = LIST_W + 2 * LPAD
    SVG_H = 100 + n * ROW_H + 30

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{SVG_W}' height='{SVG_H}'>",
        f"<title>{h(title)}</title>",
        SVG_STYLE,
        f"<rect width='{SVG_W}' height='{SVG_H}' fill='#F8FAFC'/>",
        f"<text x='{LPAD}' y='34' {FONT} font-size='18' font-weight='600' fill='#1E293B'>{h(title)}</text>",
    ]
    if total_count is not None and total_count > MAX_LIST:
        parts.append(
            f"<text x='{SVG_W-LPAD}' y='34' {FONT} font-size='11' fill='#EF4444' text-anchor='end'>"
            f"showing first {MAX_LIST} of {total_count}</text>")

    # Back button
    parts += [
        f"<a href='{h(back_href)}'>",
        f"<rect x='{LPAD}' y='48' width='72' height='24' rx='5' fill='#E2E8F0'/>",
        f"<text x='{LPAD+36}' y='64' {FONT} font-size='12' fill='#475569' text-anchor='middle'>← Back</text>",
        "</a>",
        # column headers
        f"<text x='{LPAD+30}' y='90' {MONO} font-size='10' fill='#94A3B8'>ID</text>",
        f"<text x='{LPAD+150}' y='90' {MONO} font-size='10' fill='#94A3B8'>TITLE / NAME</text>",
        f"<text x='{SVG_W-LPAD-10}' y='90' {MONO} font-size='10' fill='#94A3B8' text-anchor='end'>STATUS</text>",
    ]

    y = 100
    for i, (typ, eid, item_title, extra) in enumerate(capped):
        fg, bg, border = COLORS.get(typ, COLORS['unknown'])
        icon = ICONS.get(typ, '❓')
        row_bg = '#FFFFFF' if i % 2 == 0 else '#F1F5F9'
        parts += [
            f"<a href='{h(url_id(eid))}'>",
            f"<rect x='{LPAD}' y='{y}' width='{LIST_W}' height='{ROW_H-2}' rx='4' "
            f"fill='{row_bg}' stroke='#E2E8F0' stroke-width='1'/>",
            f"<rect x='{LPAD}' y='{y}' width='5' height='{ROW_H-2}' rx='2' fill='{fg}'/>",
            f"<text x='{LPAD+14}' y='{y+ROW_H//2+5}' font-size='14'>{icon}</text>",
            f"<text x='{LPAD+34}' y='{y+ROW_H//2+4}' {MONO} font-size='10' fill='#64748B'>{h(str(eid))}</text>",
            f"<text x='{LPAD+150}' y='{y+ROW_H//2+4}' {FONT} font-size='12' fill='#1E293B'>"
            f"{h(trunc(item_title or '', 65))}</text>",
        ]
        if extra:
            parts.append(
                f"<text x='{LPAD+LIST_W-8}' y='{y+ROW_H//2+4}' {FONT} font-size='10' "
                f"fill='#94A3B8' text-anchor='end'>{h(str(extra))}</text>")
        parts.append("</a>")
        y += ROW_H

    parts.append("</svg>")
    return '\n'.join(parts)

# ── error SVG ─────────────────────────────────────────────────────────────────

def render_error_svg(message, back_href=None):
    W, H = 660, 220
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}'>",
        f"<title>Error — {h(message[:60])}</title>",
        SVG_STYLE,
        f"<rect width='{W}' height='{H}' fill='#FEF2F2'/>",
        f"<rect x='20' y='20' width='{W-40}' height='{H-40}' rx='8' fill='white' "
        f"stroke='#EF4444' stroke-width='2'/>",
        f"<text x='40' y='62' {FONT} font-size='16' font-weight='600' fill='#DC2626'>⚠ Error</text>",
        f"<text x='40' y='94' {FONT} font-size='13' fill='#374151'>{h(message)}</text>",
        f"<text x='40' y='124' {MONO} font-size='11' fill='#6B7280'>Usage: /?id=&lt;entity_id&gt;</text>",
    ]
    if back_href:
        parts += [
            f"<a href='{h(back_href)}'>",
            f"<rect x='40' y='144' width='80' height='28' rx='5' fill='#DC2626'/>",
            f"<text x='80' y='162' {FONT} font-size='12' fill='white' text-anchor='middle'>← Back</text>",
            "</a>",
        ]
    parts.append("</svg>")
    return '\n'.join(parts)

# ── entity → SVG ─────────────────────────────────────────────────────────────

_LABEL_FIELD = {
    'page': 'confluence_title', 'blog_post': 'confluence_title', 'attachment': 'filename',
    'space': 'space_key', 'user': 'wiki_user_name', 'body_content': 'body_content_id',
    'comment': 'comment_id',
}

def render_entity_svg(con, id_str):
    entity_type, row = find_entity(con, id_str)
    cfields = CENTER_FIELDS[entity_type](row)
    label_key = _LABEL_FIELD.get(entity_type, 'id')
    center_label = trunc(str(row.get(label_key) or id_str), 30)
    related = GATHERERS[entity_type](con, row)
    title = f'{entity_type.replace("_", " ").title()}: {center_label}'
    return render_detail_svg(entity_type, center_label, cfields, related, title=title)

# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        id_str = params.get('id', [None])[0]
        list_type = params.get('list', [None])[0]

        try:
            con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
            try:
                if not id_str:
                    rows = qall(con, 'SELECT space_id, space_key, space_name FROM spaces ORDER BY space_key')
                    items = [('space', r['space_id'], r['space_name'], r['space_key']) for r in rows]
                    svg = _render_list('Spaces', items, back_href='/', total_count=None)
                elif list_type:
                    svg = render_list_svg(con, id_str, list_type)
                else:
                    svg = render_entity_svg(con, id_str)
            except ValueError as e:
                svg = render_error_svg(str(e), back_href='javascript:history.back()')
            except Exception as e:
                svg = render_error_svg(f'Internal error: {e}')
            finally:
                con.close()
        except Exception as e:
            svg = render_error_svg(f'DB error: {e}')

        data = svg.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'image/svg+xml; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}', flush=True)

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    global DB_PATH
    import argparse
    parser = argparse.ArgumentParser(
        prog='inspector.py',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('db', metavar='<workspace.sqlite>', help='Path to workspace.sqlite')
    parser.add_argument('id', metavar='<id>', nargs='?', help='Entity ID — prints SVG to stdout instead of starting a server')
    parser.add_argument('-p', '--port', type=int, default=8765, metavar='PORT', help='Web server port (default: 8765)')
    args = parser.parse_args()

    DB_PATH = args.db

    if args.id:
        con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
        try:
            if args.list if hasattr(args, 'list') else False:
                svg = render_list_svg(con, args.id, args.list)
            else:
                svg = render_entity_svg(con, args.id)
        except ValueError as e:
            svg = render_error_svg(str(e))
        finally:
            con.close()
        print(svg)
        return

    server = HTTPServer(('', args.port), Handler)
    print(f'Inspector running at http://localhost:{args.port}/', flush=True)
    print(f'Database: {DB_PATH}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nBye.', flush=True)

if __name__ == '__main__':
    main()
