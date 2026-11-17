import server as base
import json, time, re, sqlite3, secrets, hmac, base64, hashlib, math
from urllib.parse import parse_qs
from datetime import datetime, timezone
from urllib.parse import urlparse

_original_connect=base.connect
def connect():
    c=_original_connect()
    c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY COLLATE NOCASE, name TEXT NOT NULL DEFAULT '', avatar TEXT NOT NULL DEFAULT '', team TEXT NOT NULL DEFAULT '市场部', tag TEXT NOT NULL DEFAULT '', joined TEXT NOT NULL, must_change INTEGER NOT NULL DEFAULT 0, read_cursor INTEGER NOT NULL DEFAULT 0)")
    c.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, time TEXT NOT NULL, kind TEXT NOT NULL, entry_id TEXT NOT NULL, title TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, time TEXT, entry_id TEXT, before_json TEXT, after_json TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id TEXT NOT NULL, actor TEXT NOT NULL, time TEXT NOT NULL, content TEXT NOT NULL)')
    c.execute("INSERT OR IGNORE INTO profiles(username,name,joined) SELECT username,username,? FROM users",(now(),))
    c.execute('CREATE TABLE IF NOT EXISTS event_reads (actor TEXT,event_id INTEGER,PRIMARY KEY(actor,event_id))')
    if 'batch_id' not in [r[1] for r in c.execute('PRAGMA table_info(events)')]:c.execute("ALTER TABLE events ADD COLUMN batch_id TEXT DEFAULT ''")
    if 'recipient' not in [r[1] for r in c.execute('PRAGMA table_info(events)')]:c.execute("ALTER TABLE events ADD COLUMN recipient TEXT DEFAULT ''")
    c.execute('CREATE TABLE IF NOT EXISTS likes (comment_id INTEGER, actor TEXT, PRIMARY KEY(comment_id,actor))')
    c.execute('CREATE TABLE IF NOT EXISTS archive (entry_id TEXT PRIMARY KEY, content TEXT, actor TEXT, time TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, mime TEXT, data BLOB)')
    c.commit();return c
base.connect=connect

def now():return datetime.now(timezone.utc).isoformat()
def profile(c,name):
    r=c.execute('SELECT name,avatar,team,tag,joined,must_change,read_cursor FROM profiles WHERE username=?',(name,)).fetchone()
    return dict(zip(['name','avatar','team','tag','joined','mustChange','readCursor'],r))
def avatar_valid(a):
    if not a:return True
    if not isinstance(a,str) or len(a)>450000:return False
    try:
        mime,payload=a.split(';base64,');raw=base64.b64decode(payload,validate=True)
        return (mime=='data:image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime=='data:image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (mime=='data:image/webp' and raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')
    except:return False

def media_store(c,value):
    if isinstance(value,list):return [media_store(c,x) for x in value]
    if isinstance(value,dict):return {k:media_store(c,v) for k,v in value.items()}
    if isinstance(value,str) and re.match(r'^data:image/(png|jpeg|webp|gif|avif|svg\+xml);base64,',value):
        head,payload=value.split(',',1)
        try:raw=base64.b64decode(payload,validate=True)
        except:return value
        key=hashlib.sha256(raw).hexdigest();c.execute('INSERT OR IGNORE INTO media VALUES(?,?,?)',(key,head[5:-7],raw))
        try:
            from app.object_store import put_object
            put_object(key, head[5:-7], raw)
        except Exception:
            pass
        return '/media/'+key
    return value

class Handler(base.Handler):
    def serve_asset(self,path,ses):
        if not path.startswith(('/assets/','/modules/','/vendor/')):return False
        if '\\' in path or '..' in path.split('/'):return base.respond(self,400,{'error':'无效的访问地址'}) or True
        file=(base.PAGES/path.lstrip('/')).resolve();root=base.PAGES.resolve()
        if file!=root and root not in file.parents:return base.respond(self,400,{'error':'无效的访问地址'}) or True
        if file.suffix not in ('.js','.css') or not file.is_file():return base.respond(self,404,{'error':'文件不存在'}) or True
        if path!='/vendor/gsap.min.js' and not ses:return base.respond(self,401,{'error':'请先登录'}) or True
        raw=file.read_bytes();ctype='text/css; charset=utf-8' if file.suffix=='.css' else 'text/javascript; charset=utf-8'
        self.send_response(200);self.security_headers(ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return True
    def do_GET(self):
        if not self.allowed_host():return base.respond(self,400,{'error':'无效的访问地址'})
        path=urlparse(self.path).path;ses=self.session()
        if self.serve_asset(path,ses):return
        if path in ('/index.html','/login.html','/first-password.html') or (path=='/admin' and not ses):
            self.send_response(302);self.send_header('Location','/');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length','0');self.end_headers();return
        if path in ('/','/admin'):
            if not ses:
                raw=(base.PAGES/'login.html').read_bytes().replace(
                    b'</head>',
                    b'<style>body{display:flex!important;align-items:center!important;justify-content:center!important}.shell{align-self:auto!important;transform:none!important}</style></head>'
                )
                return base.html(self,200,raw)
            with base.LOCK,connect() as c:p=profile(c,ses['username'])
            if p['mustChange']:
                if path!='/':
                    self.send_response(302);self.send_header('Location','/');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length','0');self.end_headers();return
                return base.html(self,200,(base.PAGES/'first-password.html').read_bytes())
            if path=='/admin' and ses['role']!='admin':return base.respond(self,403,{'error':'仅管理员可访问管理端'})
            return base.html(self,200,(base.PAGES/'index.html').read_bytes())
        if not ses:return base.respond(self,401,{'error':'请先登录'})
        with base.LOCK,connect() as c:
            p=profile(c,ses['username'])
            if path=='/api/session':return base.respond(self,200,{'username':ses['username'],'role':ses['role'],'csrf':ses['csrf'],'profile':p})
            if p['mustChange']:return base.respond(self,403,{'error':'请先修改初始密码'})
            if path.startswith('/media/'):
                key=path[7:]
                row=c.execute('SELECT mime,data FROM media WHERE id=?',(key,)).fetchone()
                raw=None
                mime=row[0] if row else 'application/octet-stream'
                try:
                    from app.object_store import get_object
                    raw=get_object(key)
                except Exception:
                    raw=None
                if raw is None and row:raw=row[1]
                if raw is None:
                    disk=base.DATA/'media'/'originals'/key
                    if disk.is_file():raw=disk.read_bytes()
                if raw is None:return base.respond(self,404,{'error':'图片不存在'})
                if isinstance(raw,memoryview):raw=raw.tobytes()
                self.send_response(200);self.security_headers(mime);self.send_header('Content-Security-Policy',"sandbox; default-src 'none'; style-src 'unsafe-inline'");self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            if path=='/api/presence':
                base.SESSIONS[ses['token']]['activeAt']=time.time()
                users={x['username'] for x in base.SESSIONS.values() if time.time()-x.get('activeAt',0)<120}
                return base.respond(self,200,{'count':len(users)})
            if path=='/api/archive':
                if ses['role']!='admin':return base.respond(self,403,{'error':'仅管理员可访问归档'})
                rows=c.execute('SELECT entry_id,content,actor,time FROM archive ORDER BY time DESC').fetchall()
                return base.respond(self,200,[{'id':r[0],'title':json.loads(r[1])['title'],'actor':r[2],'time':r[3]} for r in rows])
            if path=='/api/comments/all':
                rows=c.execute('SELECT c.id,c.entry_id,c.actor,p.name,c.time,c.content FROM comments c LEFT JOIN profiles p ON c.actor=p.username ORDER BY c.id DESC').fetchall()
                items=[]
                for r in rows:
                    x=dict(zip(['id','entryId','username','name','time','content'],r));x['likes']=c.execute('SELECT count(DISTINCT actor) FROM (SELECT actor FROM likes WHERE comment_id=? UNION ALL SELECT actor FROM comment_likes WHERE comment_id=?) q',(r[0],r[0])).fetchone()[0];x['liked']=bool(c.execute('SELECT 1 FROM (SELECT actor FROM likes WHERE comment_id=? UNION ALL SELECT actor FROM comment_likes WHERE comment_id=?) q WHERE actor=?',(r[0],r[0],ses['username'])).fetchone());replies=c.execute('SELECT id,actor,time,content FROM comment_replies WHERE comment_id=? ORDER BY id',(r[0],)).fetchall();x['replies']=[dict(zip(['id','actor','time','content'],reply)) for reply in replies];items.append(x)
                return base.respond(self,200,items)
            if path=='/api/events':
                rows=c.execute('SELECT e.id,e.actor,p.name,e.time,e.kind,e.entry_id,e.title,e.batch_id FROM events e LEFT JOIN profiles p ON e.actor=p.username WHERE length(e.recipient)=0 OR e.recipient=? ORDER BY e.id DESC LIMIT 100',(ses['username'],)).fetchall()
                unread=c.execute('SELECT count(*) FROM events WHERE (length(recipient)=0 OR recipient=?) AND id>? AND actor<>? AND id NOT IN (SELECT event_id FROM event_reads WHERE actor=?)',(ses['username'],p['readCursor'],ses['username'],ses['username'])).fetchone()[0]
                return base.respond(self,200,{'unread':unread,'cursor':rows[0][0] if rows else 0,'items':[dict(zip(['id','username','name','time','kind','entryId','title','batchId'],r)) for r in rows]})
            if path=='/api/team':
                if ses['role']!='admin':return base.respond(self,403,{'error':'仅管理员可管理成员'})
                rows=c.execute('SELECT u.username,u.role,u.active,p.name,p.team,p.tag,p.joined FROM users u JOIN profiles p ON u.username=p.username ORDER BY u.username').fetchall()
                return base.respond(self,200,[dict(zip(['username','role','active','name','team','tag','joined'],r)) for r in rows])
            if path=='/api/comments':
                from urllib.parse import parse_qs
                entry=parse_qs(urlparse(self.path).query).get('entry',[''])[0]
                rows=c.execute('''SELECT c.id,c.actor,p.name,c.time,c.content,
 (SELECT count(DISTINCT actor) FROM (SELECT actor FROM likes WHERE comment_id=c.id UNION ALL SELECT actor FROM comment_likes WHERE comment_id=c.id) q),
 EXISTS(SELECT 1 FROM (SELECT actor FROM likes WHERE comment_id=c.id UNION ALL SELECT actor FROM comment_likes WHERE comment_id=c.id) q WHERE actor=?)
 FROM comments c LEFT JOIN profiles p ON c.actor=p.username WHERE entry_id=? ORDER BY c.id DESC''',(ses['username'],entry)).fetchall()
                return base.respond(self,200,[dict(zip(['id','username','name','time','content','likes','liked'],[r[0],r[1],r[2],r[3],r[4],r[5],bool(r[6])])) for r in rows])
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        if path=='/api/login':return super().do_POST()
        if not self.allowed_host() or not self.same_origin():return base.respond(self,403,{'error':'请求来源无效'})
        ses=self.session()
        if not ses:return base.respond(self,401,{'error':'请先登录'})
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),ses['csrf']):return base.respond(self,403,{'error':'请求校验失败'})
        with base.LOCK,connect() as c:p=profile(c,ses['username'])
        if p['mustChange'] and path not in ('/api/password','/api/logout'):return base.respond(self,403,{'error':'请先修改初始密码'})
        if path not in ('/api/profile','/api/events/read','/api/team/update','/api/comments','/api/comments/delete','/api/comments/like','/api/entries/patch','/api/archive/restore','/api/archive/purge','/api/events/read-one'):return super().do_POST()
        try:data=self.body()
        except:return base.respond(self,400,{'error':'无效请求'})
        with base.LOCK,connect() as c:
            if path=='/api/entries/patch':
                if ses['role']=='viewer':return base.respond(self,403,{'error':'只读账号不能修改内容'})
                changes=data.get('changes');deleted=data.get('deleted',[])
                if not isinstance(changes,list) or not isinstance(deleted,list):return base.respond(self,400,{'error':'无效的修改'})
                version,raw=c.execute('SELECT version,entries FROM state WHERE id=1').fetchone();current={x['id']:x for x in json.loads(raw or '[]')}
                for change in changes+deleted:
                    if not isinstance(change,dict) or not isinstance(change.get('id'),str):return base.respond(self,400,{'error':'无效记录'})
                    if current.get(change['id'])!=change.get('before'):return base.respond(self,409,{'error':'此条内容已被其他成员修改，草稿已保留，请重新打开后比较。','entry':current.get(change['id'])})
                for change in changes:
                    item=change.get('after')
                    if not isinstance(item,dict) or item.get('id')!=change['id']:return base.respond(self,400,{'error':'无效记录'})
                    current[change['id']]=item
                for change in deleted:current.pop(change['id'],None)
                return self.save_state(ses,{'version':version,'entries':list(current.values())})
            if path=='/api/archive/restore':
                if ses['role']!='admin':return base.respond(self,403,{'error':'仅管理员可恢复'})
                row=c.execute('SELECT content FROM archive WHERE entry_id=?',(data.get('id'),)).fetchone()
                if not row:return base.respond(self,404,{'error':'归档不存在'})
                version,raw=c.execute('SELECT version,entries FROM state WHERE id=1').fetchone();items=json.loads(raw or '[]');item=json.loads(row[0])
                if any(x['id']==item['id'] for x in items):return base.respond(self,409,{'error':'同编号内容已存在'})
                items.append(item);c.execute('UPDATE state SET version=?,entries=? WHERE id=1',(version+1,json.dumps(items,ensure_ascii=False)));c.execute('DELETE FROM archive WHERE entry_id=?',(item['id'],));base.log(c,ses['username'],'恢复归档 '+item['title']);c.commit();return base.respond(self,200,{'ok':True})
            if path=='/api/archive/purge':
                if ses['role']!='admin':return base.respond(self,403,{'error':'仅管理员可删除'})
                row=c.execute('SELECT content FROM archive WHERE entry_id=?',(data.get('id'),)).fetchone()
                if not row:return base.respond(self,404,{'error':'归档不存在'})
                try:title=json.loads(row[0]).get('title') or ''
                except Exception:title=''
                c.execute('DELETE FROM archive WHERE entry_id=?',(data.get('id'),));base.log(c,ses['username'],'永久删除归档 '+title);c.commit();return base.respond(self,200,{'ok':True})
            if path in ('/api/comments/delete','/api/comments/like'):
                if ses['role']=='viewer':return base.respond(self,403,{'error':'只读账号不能修改评价'})
                row=c.execute('SELECT actor FROM comments WHERE id=?',(data.get('id'),)).fetchone()
                if not row:return base.respond(self,404,{'error':'评价已删除'})
                if path.endswith('/delete'):
                    if ses['role']!='admin' and row[0]!=ses['username']:return base.respond(self,403,{'error':'只能删除自己的评价'})
                    c.execute('DELETE FROM comment_replies WHERE comment_id=?',(data['id'],));c.execute('DELETE FROM comment_likes WHERE comment_id=?',(data['id'],));c.execute('DELETE FROM likes WHERE comment_id=?',(data['id'],));c.execute('DELETE FROM comments WHERE id=?',(data['id'],));base.log(c,ses['username'],'删除评价 '+str(data['id']))
                elif data.get('liked'):
                    inserted=c.execute('INSERT OR IGNORE INTO likes VALUES(?,?)',(data['id'],ses['username'])).rowcount
                    c.execute('INSERT OR IGNORE INTO comment_likes(comment_id,actor) VALUES(?,?)',(data['id'],ses['username']))
                    if inserted and row[0]!=ses['username']:
                        info=c.execute('SELECT entry_id,content FROM comments WHERE id=?',(data['id'],)).fetchone()
                        c.execute('INSERT INTO events(actor,time,kind,entry_id,title,batch_id,recipient) VALUES(?,?,?,?,?,?,?)',(ses['username'],now(),'点赞',info[0],info[1][:100],secrets.token_hex(12),row[0]))
                else:c.execute('DELETE FROM likes WHERE comment_id=? AND actor=?',(data['id'],ses['username']));c.execute('DELETE FROM comment_likes WHERE comment_id=? AND actor=?',(data['id'],ses['username']))
                c.commit();return base.respond(self,200,{'ok':True})
            if path=='/api/profile':
                if set(data)-{'name','avatar'}:return base.respond(self,403,{'error':'团队、岗位和加入日期只能由管理员设置或系统记录'})
                name=data.get('name',p['name']);avatar=data.get('avatar',p['avatar'])
                if not isinstance(name,str) or not 1<=len(name.strip())<=40 or not avatar_valid(avatar):return base.respond(self,400,{'error':'名字为 1–40 字；头像请用小于 300 KB 的 PNG/JPG/WebP'})
                c.execute('UPDATE profiles SET name=?,avatar=? WHERE username=?',(name.strip(),avatar,ses['username']));base.log(c,ses['username'],'更新个人资料');c.commit()
                return base.respond(self,200,profile(c,ses['username']))
            if path=='/api/team/update':
                if ses['role']!='admin':return base.respond(self,403,{'error':'仅管理员可修改团队和岗位'})
                if not all(isinstance(data.get(k,''),str) and len(data.get(k,''))<=80 for k in ('username','team','tag')):return base.respond(self,400,{'error':'字段过长或无效'})
                c.execute('UPDATE profiles SET team=?,tag=? WHERE username=?',(data.get('team',''),data.get('tag',''),data.get('username','')));base.log(c,ses['username'],'更新成员团队与岗位 '+data.get('username',''));c.commit();return base.respond(self,200,{'ok':True})
            if path=='/api/events/read-one':
                event_id=data.get('id')
                if not isinstance(event_id,int) or not c.execute('SELECT 1 FROM events WHERE id=?',(event_id,)).fetchone():return base.respond(self,400,{'error':'无效动态'})
                c.execute('INSERT OR IGNORE INTO event_reads VALUES(?,?)',(ses['username'],event_id));c.commit();return base.respond(self,200,{'ok':True})
            if path=='/api/events/read':
                cursor=data.get('cursor');maximum=c.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
                if not isinstance(cursor,int) or not 0<=cursor<=maximum:return base.respond(self,400,{'error':'无效通知位置'})
                c.execute('UPDATE profiles SET read_cursor=max(read_cursor,?) WHERE username=?',(cursor,ses['username']));c.commit();return base.respond(self,200,{'ok':True})
            if path=='/api/comments':
                content=data.get('content','');entry=data.get('entryId','');raw=c.execute('SELECT entries FROM state WHERE id=1').fetchone()[0]
                if not isinstance(content,str) or not 1<=len(content.strip())<=2000:return base.respond(self,400,{'error':'评价为 1–2000 字'})
                if not any(x['id']==entry for x in json.loads(raw or '[]')):return base.respond(self,404,{'error':'内容不存在'})
                owner=next((x.get('createdBy') for x in json.loads(raw or '[]') if x['id']==entry),None)
                if owner and owner!=ses['username']:c.execute('INSERT INTO events(actor,time,kind,entry_id,title,batch_id,recipient) VALUES(?,?,?,?,?,?,?)',(ses['username'],now(),'评价',entry,content.strip()[:100],secrets.token_hex(12),owner))
                c.execute('INSERT INTO comments(entry_id,actor,time,content) VALUES(?,?,?,?)',(entry,ses['username'],now(),content.strip()));base.log(c,ses['username'],'添加评价 '+entry);c.commit();return base.respond(self,200,{'ok':True})
    def body(self):
        if urlparse(self.path).path in ('/api/profile','/api/entries/patch'):
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<(100*1024*1024 if self.path=='/api/entries/patch' else 500000) or self.headers.get_content_type()!='application/json':raise ValueError()
            v=json.loads(self.rfile.read(n))
            if not isinstance(v,dict):raise ValueError()
            return v
        return super().body()
    def change_password(self,ses,body):
        old=body.get('current','');new=body.get('password','')
        if not isinstance(old,str) or not isinstance(new,str) or new==old:return base.respond(self,400,{'error':'新密码不能与当前密码相同'})
        if not base.valid_password(new):return base.respond(self,400,{'error':'密码只能使用数字和字母'})
        with base.LOCK,connect() as c:
            row=c.execute('SELECT salt,password_hash FROM users WHERE username=? AND active=1',(ses['username'],)).fetchone()
            if not row or not hmac.compare_digest(base.password_hash(old,row[0]),row[1]):return base.respond(self,403,{'error':'当前密码不正确'})
            salt=secrets.token_bytes(16);c.execute('UPDATE users SET salt=?,password_hash=? WHERE username=?',(salt,base.password_hash(new,salt),ses['username']));c.execute('UPDATE profiles SET must_change=0 WHERE username=?',(ses['username'],));base.log(c,ses['username'],'修改密码');c.commit()
            for token,x in list(base.SESSIONS.items()):
                if x['username'].casefold()==ses['username'].casefold():base.SESSIONS.pop(token,None)
        return base.respond(self,200,{'ok':True,'relogin':True})
    def manage_user(self,ses,body,create):
        # Base handler preserves last-admin and session revocation checks.
        with base.LOCK,connect() as c:
            before=c.execute('SELECT password_hash FROM users WHERE username=?',(body.get('username',''),)).fetchone()
        result=super().manage_user(ses,body,create)
        with base.LOCK,connect() as c:
            after=c.execute('SELECT password_hash FROM users WHERE username=?',(body.get('username',''),)).fetchone()
        if body.get('password') and after and after!=before:
            with base.LOCK,connect() as c:c.execute('UPDATE profiles SET must_change=1 WHERE username=?',(body.get('username',''),));c.commit()
        return result
    def audit_creative(self,c,ses,action,object_type,object_id):
        meta=base.REQUEST_META.get({}) or {}
        c.execute('INSERT INTO activity_logs(time,actor,module,action,object_type,object_id,result,ip,user_agent,repeat_count) VALUES(?,?,?,?,?,?,?,?,?,1)',(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),ses['username'],'creative',str(action)[:300],str(object_type)[:40],str(object_id)[:80],'success',str(meta.get('ip',''))[:64],str(meta.get('ua',''))[:300]))
    def save_state(self,ses,body):
        incoming=body.get('entries');v=body.get('version')
        if not isinstance(incoming,list) or not isinstance(v,int) or not all(isinstance(x,dict) and isinstance(x.get('id'),str) and isinstance(x.get('title'),str) for x in incoming):return base.respond(self,400,{'error':'记录无效'})
        if len({x['id'] for x in incoming})!=len(incoming):return base.respond(self,400,{'error':'编号重复'})
        for item in incoming:
            if item.get('kind') not in ('开头创意','产品出场','完整脚本','类型定义','图片素材'):return base.respond(self,400,{'error':'内容类型无效'})
            ad=item.get('ad')
            if ad is None:continue
            if not isinstance(ad,dict) or not isinstance(ad.get('rows',[]),list):return base.respond(self,400,{'error':'投放数据格式无效'})
            seen=set()
            for row in ad.get('rows',[]):
                if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] in seen:return base.respond(self,400,{'error':'周期记录编号无效或重复'})
                seen.add(row['id'])
                try:
                    start=datetime.strptime(row.get('periodStart') or row.get('date',''),'%Y-%m-%d');end=datetime.strptime(row.get('periodEnd') or row.get('date',''),'%Y-%m-%d')
                    if end<start or (end-start).days>3660:raise ValueError()
                except:return base.respond(self,400,{'error':'统计周期日期无效或跨度过长'})
                for key in ('spend','impressions','clicks','lpv','purchases','cpm','ctr','cpa','roas','view3','view50'):
                    value=row.get(key)
                    if value is not None and (not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<0):return base.respond(self,400,{'error':'广告指标必须为非负有限数值'})

        with base.LOCK,connect() as c:
            version,raw=c.execute('SELECT version,entries FROM state WHERE id=1').fetchone()
            if version!=v:return base.respond(self,409,{'error':'其他成员刚刚保存了内容，请刷新后再试'})
            old={x['id']:x for x in json.loads(raw or '[]')};new={x['id']:x for x in incoming}
            if ses['role']!='admin':
                if set(old)-set(new):return base.respond(self,403,{'error':'操作者不能删除记录，请联系管理员归档'})
                for id,x in new.items():
                    prev=old.get(id)
                    if prev and prev!=x and prev.get('createdBy')!=ses['username']:return base.respond(self,403,{'error':'不能修改其他成员的内容，可在内容下添加评价'})
                    if x.get('ad')!=(prev or {}).get('ad'):return base.respond(self,403,{'error':'操作者不能新增或修改广告数据'})
                    if prev and x.get('createdBy')!=prev.get('createdBy'):return base.respond(self,403,{'error':'不能修改内容归属'})
            save_batch=secrets.token_hex(12)
            for id,x in new.items():
                prev=old.get(id)
                if prev and prev!=x and x.get('createdBy')!=prev.get('createdBy'):return base.respond(self,403,{'error':'内容作者不可更改'})
                if not prev:
                    if x.get('kind')=='图片素材':return base.respond(self,400,{'error':'图片素材库已停用'})
                    x['createdBy']=ses['username']
                x=media_store(c,x);new[id]=x
                if prev!=x:
                    c.execute('INSERT INTO revisions(actor,time,entry_id,before_json,after_json) VALUES(?,?,?,?,?)',(ses['username'],now(),id,json.dumps(prev,ensure_ascii=False),json.dumps(x,ensure_ascii=False)))
                    verb='新增' if not prev else '修改'
                    label={'开头创意':'创意钩子','产品出场':'产品出场','完整脚本':'完整脚本','图片素材':'图片素材','类型定义':'类型'}.get(x.get('kind'),'内容')
                    base.log(c,ses['username'],verb+' '+x['title'])
                    self.audit_creative(c,ses,f'{verb}{label} {x["title"]}',x.get('kind') or '',id)
                    old_shots=(prev or {}).get('shots') if isinstance((prev or {}).get('shots'),list) else []
                    new_shots=x.get('shots') if isinstance(x.get('shots'),list) else []
                    if len(new_shots)>len(old_shots):self.audit_creative(c,ses,f'新增分镜 {x["title"]}（{len(new_shots)-len(old_shots)} 个镜头）','分镜',id)
                    if not prev:c.execute('INSERT INTO events(actor,time,kind,entry_id,title,batch_id) VALUES(?,?,?,?,?,?)',(ses['username'],now(),x.get('kind','内容'),id,x['title'],save_batch))
            for id in set(old)-set(new):
                c.execute('INSERT OR REPLACE INTO archive VALUES(?,?,?,?)',(id,json.dumps(old[id],ensure_ascii=False),ses['username'],now()))
                c.execute('INSERT INTO revisions(actor,time,entry_id,before_json,after_json) VALUES(?,?,?,?,?)',(ses['username'],now(),id,json.dumps(old[id],ensure_ascii=False),'null'));base.log(c,ses['username'],'删除 '+old[id]['title'])
            c.execute('UPDATE state SET version=?,entries=? WHERE id=1',(version+1,json.dumps(list(new.values()),ensure_ascii=False)));c.commit()
        from app.services.creative_hooks import synchronize_from_entries
        from app.services.product_entries import synchronize_from_entries as synchronize_product_entries
        from app.services.scripts import synchronize_from_entries as synchronize_scripts
        synchronize_from_entries(list(new.values()),ses['username'])
        synchronize_product_entries(list(new.values()),ses['username'])
        synchronize_scripts(list(new.values()),ses['username'])
        return base.respond(self,200,{'version':version+1,'entries':list(new.values())})

base.Handler=Handler
if __name__=='__main__':base.start()
