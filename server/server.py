from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from http.cookies import SimpleCookie
from datetime import datetime
import sqlite3, json, threading, socket, ssl, secrets, hashlib, hmac, time, getpass, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PAGES=ROOT/'web'
DATA=ROOT/'data'
DB=DATA/'sana_data.sqlite3'
CONFIG=HERE/'server_config.json'
LOCK=threading.RLock()
SESSIONS={}
ATTEMPTS={}
IP_ATTEMPTS={}
ROLES=('admin','editor','viewer')
ITERATIONS=600000
MAX_SESSION=8*60*60

class ClosingConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()

def connect():
    c=sqlite3.connect(DB,timeout=20,factory=ClosingConnection)
    c.execute('PRAGMA busy_timeout=20000')
    c.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, entries TEXT)')
    c.execute('INSERT OR IGNORE INTO state(id,version,entries) VALUES(1,0,NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS log (id INTEGER PRIMARY KEY, time TEXT, actor TEXT, action TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY COLLATE NOCASE, salt BLOB NOT NULL, password_hash BLOB NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)')
    c.commit()
    return c

def log(c, actor, message):
    c.execute('INSERT INTO log(time,actor,action) VALUES(?,?,?)',(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),str(actor)[:100],str(message)[:300]))

def valid_name(name):return isinstance(name,str) and 1<=len(name)<=64 and all(ch.isalnum() or ch in '._-@' for ch in name)
def valid_password(password):return isinstance(password,str) and 12<=len(password)<=200

def password_hash(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,ITERATIONS)
def create_user(c,name,password,role):
    if not valid_name(name) or not valid_password(password) or role not in ROLES:raise ValueError('账号、密码或权限不符合要求')
    salt=secrets.token_bytes(16)
    c.execute('INSERT INTO users(username,salt,password_hash,role,active) VALUES(?,?,?,?,1)',(name,salt,password_hash(password,salt),role))

def bootstrap():
    with LOCK,connect() as c:
        if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]:return
        if not sys.stdin.isatty():raise SystemExit('首次启动需要在主机终端交互创建管理员。')
        print('首次启动：请创建管理员账号。密码至少 12 个字符。',flush=True)
        username=input('管理员账号（字母、数字和 . _ - @）：').strip()
        password=getpass.getpass('管理员密码（输入时不显示）：')
        confirm=getpass.getpass('再次输入密码：')
        if password!=confirm:raise SystemExit('两次密码不一致，请重新启动。')
        try:create_user(c,username,password,'admin')
        except (ValueError,sqlite3.IntegrityError) as e:raise SystemExit(str(e))
        log(c,username,'创建初始管理员');c.commit()
        print('管理员已创建。',flush=True)

def respond(h,status,obj,cookie=None):
    raw=json.dumps(obj,ensure_ascii=False).encode('utf-8')
    h.send_response(status);h.security_headers('application/json; charset=utf-8')
    if cookie:h.send_header('Set-Cookie',cookie)
    h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)

def html(h,status,raw):
    raw=raw.encode('utf-8') if isinstance(raw,str) else raw
    h.send_response(status);h.security_headers('text/html; charset=utf-8');h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)

LOGIN='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>登录 · EkkoHub 创意工坊</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f4f7fb;color:#172b46;font:15px system-ui,"Microsoft YaHei",sans-serif}.box{box-sizing:border-box;width:min(400px,calc(100% - 32px));padding:32px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 12px 35px #16365a0b}h1{font-size:21px;margin:0 0 8px}p{color:#71839a;font-size:13px;line-height:1.6}label{display:block;font-size:13px;margin:18px 0 7px}input{box-sizing:border-box;width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:7px;font:inherit}button{margin-top:22px;width:100%;padding:11px;background:#2563eb;border:0;border-radius:7px;color:#fff;font:inherit;cursor:pointer}button:hover{background:#1d4ed8}#error{color:#b91c1c;min-height:1em}</style></head><body><form class="box" id="login"><h1>EkkoHub 创意工坊</h1><p>请输入管理员分配的账号和密码。</p><label for="u">账号</label><input id="u" autocomplete="username" required><label for="p">密码</label><input id="p" type="password" autocomplete="current-password" required><div id="error" role="alert"></div><button type="submit">登录</button></form><script>document.querySelector('#login').onsubmit=async e=>{e.preventDefault();let error=document.querySelector('#error');error.textContent='';try{let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.querySelector('#u').value,password:document.querySelector('#p').value})});let x=await r.json();if(r.ok)location.reload();else error.textContent=x.error||'登录失败';}catch{error.textContent='无法连接，请检查主机。'}};</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    server_version='GiannaLocal/1.0'
    def log_message(self,fmt,*args):pass
    def security_headers(self,ctype):
        self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','same-origin');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    def allowed_host(self):
        host=self.headers.get('Host','').lower().split(':')[0]
        return host in self.server.allowed_hosts
    def same_origin(self):
        expected=('https://' if self.server.secure else 'http://')+self.headers.get('Host','')
        return self.headers.get('Origin','')==expected
    def session(self):
        try:
            cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''));token=cookies['sana_session'].value
        except (KeyError,ValueError):return None
        with LOCK:
            ses=SESSIONS.get(token)
            if not ses or time.time()-ses['created']>MAX_SESSION:
                SESSIONS.pop(token,None);return None
            with connect() as c:row=c.execute('SELECT username,role,active FROM users WHERE username=?',(ses['username'],)).fetchone()
            if not row or not row[2]:SESSIONS.pop(token,None);return None
            return {'token':token,'username':row[0],'role':row[1],'csrf':ses['csrf']}
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        limit=100*1024*1024 if urlparse(self.path).path=='/api/state' else 32768
        if n<=0 or n>limit or self.headers.get_content_type()!='application/json':raise ValueError('无效请求')
        value=json.loads(self.rfile.read(n))
        if not isinstance(value,dict):raise ValueError('无效请求')
        return value
    def do_GET(self):
        if not self.allowed_host():return respond(self,400,{'error':'无效的访问地址，请检查允许的主机名设置。'})
        path=urlparse(self.path).path;ses=self.session()
        if path in ('/','/index.html'):
            return html(self,200,(PAGES/'index.html').read_bytes() if ses else LOGIN)
        if not ses:return respond(self,401,{'error':'请先登录'})
        if path=='/api/session':return respond(self,200,{'username':ses['username'],'role':ses['role'],'csrf':ses['csrf']})
        if path=='/api/state':
            with LOCK,connect() as c:v,raw=c.execute('SELECT version,entries FROM state WHERE id=1').fetchone()
            return respond(self,200,{'version':v,'entries':json.loads(raw) if raw else None})
        if path=='/api/log':
            if ses['role']!='admin':return respond(self,403,{'error':'仅管理员可查看操作记录'})
            with LOCK,connect() as c:rows=c.execute('SELECT time,actor,action FROM log ORDER BY id DESC LIMIT 1000').fetchall()
            return respond(self,200,[{'time':t,'actor':a,'action':x} for t,a,x in rows])
        if path=='/api/users':
            if ses['role']!='admin':return respond(self,403,{'error':'仅管理员可管理账号'})
            with LOCK,connect() as c:rows=c.execute('SELECT username,role,active FROM users ORDER BY username').fetchall()
            return respond(self,200,[{'username':n,'role':r,'active':bool(a)} for n,r,a in rows])
        return respond(self,404,{'error':'未找到'})
    def do_POST(self):
        if not self.allowed_host() or not self.same_origin():return respond(self,403,{'error':'请求来源无效'})
        path=urlparse(self.path).path
        try:body=self.body()
        except (ValueError,TypeError,json.JSONDecodeError):return respond(self,400,{'error':'无效请求'})
        if path=='/api/login':return self.login(body)
        ses=self.session()
        if not ses:return respond(self,401,{'error':'登录已过期，请重新登录'})
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),ses['csrf']):return respond(self,403,{'error':'请求校验失败，请刷新重试'})
        if path=='/api/logout':
            with LOCK:SESSIONS.pop(ses['token'],None)
            return respond(self,200,{'ok':True},'sana_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'+('; Secure' if self.server.secure else ''))
        if path=='/api/password':return self.change_password(ses,body)
        if path=='/api/state':
            if ses['role'] not in ('admin','editor'):return respond(self,403,{'error':'只读账号不能修改数据'})
            return self.save_state(ses,body)
        if path in ('/api/users/create','/api/users/update'):
            if ses['role']!='admin':return respond(self,403,{'error':'仅管理员可管理账号'})
            return self.manage_user(ses,body,path.endswith('/create'))
        return respond(self,404,{'error':'未找到'})
    def login(self,body):
        name=body.get('username','');pw=body.get('password','');ip=self.client_address[0];key=(ip,str(name).casefold()[:64]);now=time.time()
        if not isinstance(name,str) or not isinstance(pw,str) or len(name)>64 or len(pw)>200:return respond(self,400,{'error':'账号或密码错误'})
        with LOCK:
            attempts=[x for x in ATTEMPTS.get(key,[]) if now-x<900];ATTEMPTS[key]=attempts
            ip_attempts=[x for x in IP_ATTEMPTS.get(ip,[]) if now-x<900];IP_ATTEMPTS[ip]=ip_attempts
            if len(attempts)>=5 or len(ip_attempts)>=25:return respond(self,429,{'error':'登录尝试过多，请 15 分钟后再试。'})
            with connect() as c:row=c.execute('SELECT username,salt,password_hash,role,active FROM users WHERE username=?',(name,)).fetchone()
        salt=row[1] if row else bytes(16);expected=row[2] if row else bytes(32)
        matched=hmac.compare_digest(password_hash(pw,salt),expected)
        if not row or not row[4] or not matched:
            with LOCK:
                ATTEMPTS.setdefault(key,[]).append(now);IP_ATTEMPTS.setdefault(ip,[]).append(now)
            return respond(self,401,{'error':'账号或密码错误'})
        with LOCK:
            ATTEMPTS.pop(key,None);IP_ATTEMPTS.pop(ip,None)
            for old_token,old_session in list(SESSIONS.items()):
                if now-old_session['created']>MAX_SESSION:SESSIONS.pop(old_token,None)
            token=secrets.token_urlsafe(32);SESSIONS[token]={'username':row[0],'csrf':secrets.token_urlsafe(32),'created':now}
            with connect() as c:log(c,row[0],'登录成功');c.commit()
        cookie='sana_session='+token+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+str(MAX_SESSION)+('; Secure' if self.server.secure else '')
        return respond(self,200,{'ok':True},cookie)
    def save_state(self,ses,body):
        incoming=body.get('entries');version=body.get('version')
        if not isinstance(incoming,list) or not all(isinstance(x,dict) and isinstance(x.get('id'),str) and isinstance(x.get('title'),str) for x in incoming) or not isinstance(version,int):return respond(self,400,{'error':'数据格式无效'})
        if len({x['id'] for x in incoming})!=len(incoming):return respond(self,400,{'error':'记录编号重复'})
        with LOCK,connect() as c:
            permission=c.execute('SELECT role,active FROM users WHERE username=?',(ses['username'],)).fetchone()
            if not permission or not permission[1]:return respond(self,401,{'error':'账号已停用'})
            if permission[0] not in ('admin','editor'):return respond(self,403,{'error':'只读账号不能修改数据'})
            current,raw=c.execute('SELECT version,entries FROM state WHERE id=1').fetchone()
            if version!=current:return respond(self,409,{'error':'conflict','version':current})
            old=json.loads(raw) if raw else [];om={x['id']:x for x in old};nm={x['id']:x for x in incoming}
            labels={'title':'标题','code':'编号','kind':'记录类型','hook':'开头类型','transition':'出场类型','parent':'关联开头','created':'创意日期','createdTime':'创意时间','producedDate':'产出状态/日期','usedDate':'使用状态/日期','videoCount':'视频数量','content':'脚本内容','notes':'备注','shots':'镜头','images':'图片','ad':'广告数据'}
            for id,x in nm.items():
                if id not in om or om[id]!=x:
                    action=('新增 ' if id not in om else '修改 ')+str(x.get('code',''))+' '+str(x.get('title',''))
                    if id in om:
                        changed=[labels.get(k,k) for k in set(om[id])|set(x) if om[id].get(k)!=x.get(k)]
                        if changed:action+='（'+'、'.join(sorted(changed))+'）'
                    log(c,ses['username'],action)
            for id,x in om.items():
                if id not in nm:log(c,ses['username'],'删除 '+str(x.get('code',''))+' '+str(x.get('title','')))
            c.execute('UPDATE state SET version=?,entries=? WHERE id=1',(current+1,json.dumps(incoming,ensure_ascii=False)));c.commit()
        return respond(self,200,{'version':current+1})
    def change_password(self,ses,body):
        old=body.get('current','');new=body.get('password','')
        if not isinstance(old,str) or len(old)>200 or not valid_password(new):return respond(self,400,{'error':'新密码至少 12 个字符'})
        with LOCK,connect() as c:
            row=c.execute('SELECT salt,password_hash FROM users WHERE username=? AND active=1',(ses['username'],)).fetchone()
            if not row or not hmac.compare_digest(password_hash(old,row[0]),row[1]):return respond(self,403,{'error':'当前密码不正确'})
            salt=secrets.token_bytes(16);c.execute('UPDATE users SET salt=?,password_hash=? WHERE username=?',(salt,password_hash(new,salt),ses['username']));log(c,ses['username'],'修改密码');c.commit()
            for token,x in list(SESSIONS.items()):
                if x['username'].casefold()==ses['username'].casefold():SESSIONS.pop(token,None)
        return respond(self,200,{'ok':True,'relogin':True})
    def manage_user(self,ses,body,create):
        name=body.get('username','');role=body.get('role','');password=body.get('password','');active=body.get('active',True)
        if not valid_name(name) or role not in ROLES or not isinstance(active,bool):return respond(self,400,{'error':'账号或权限无效'})
        if password and not valid_password(password):return respond(self,400,{'error':'密码至少 12 个字符'})
        with LOCK,connect() as c:
            permission=c.execute('SELECT role,active FROM users WHERE username=?',(ses['username'],)).fetchone()
            if not permission or not permission[1]:return respond(self,401,{'error':'账号已停用'})
            if permission[0]!='admin':return respond(self,403,{'error':'仅管理员可管理账号'})
            try:
                if create:
                    if not valid_password(password):return respond(self,400,{'error':'新账号密码至少 12 个字符'})
                    create_user(c,name,password,role);log(c,ses['username'],'创建账号 '+name+'（'+role+'）')
                else:
                    row=c.execute('SELECT username,role,active FROM users WHERE username=?',(name,)).fetchone()
                    if not row:return respond(self,404,{'error':'账号不存在'})
                    if row[0].casefold()==ses['username'].casefold() and (not active or role!='admin'):return respond(self,400,{'error':'不能停用或降权当前登录的管理员'})
                    if row[1]=='admin' and row[2] and (role!='admin' or not active) and c.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1:return respond(self,400,{'error':'至少保留一个启用的管理员'})
                    c.execute('UPDATE users SET role=?,active=? WHERE username=?',(role,int(active),name))
                    if password:
                        salt=secrets.token_bytes(16);c.execute('UPDATE users SET salt=?,password_hash=? WHERE username=?',(salt,password_hash(password,salt),name))
                    log(c,ses['username'],'更新账号 '+name+'（'+role+'，'+('启用' if active else '停用')+('，重置密码' if password else '')+'）')
                    for token,x in list(SESSIONS.items()):
                        if x['username'].casefold()==name.casefold():SESSIONS.pop(token,None)
                c.commit()
            except sqlite3.IntegrityError:return respond(self,409,{'error':'账号已存在'})
            except ValueError as e:return respond(self,400,{'error':str(e)})
        return respond(self,200,{'ok':True})

def start():
    cfg={'host':'127.0.0.1','port':8765,'allowed_hosts':['127.0.0.1','localhost'],'cert':'','key':''}
    if CONFIG.exists():
        supplied=json.loads(CONFIG.read_text(encoding='utf-8-sig'))
        if not isinstance(supplied,dict):raise SystemExit('配置格式无效。')
        cfg.update(supplied)
    host=cfg['host'];port=int(cfg['port']);cert=cfg.get('cert','');key=cfg.get('key','');secure=bool(cert and key)
    if bool(cert)!=bool(key):raise SystemExit('HTTPS 必须同时配置证书和私钥。')
    if not secure and host not in ('127.0.0.1','localhost'):raise SystemExit('未配置 HTTPS，禁止向其他电脑开放。请先配置可信证书和私钥。')
    allowed=cfg.get('allowed_hosts')
    if not isinstance(allowed,list) or not allowed or not all(isinstance(x,str) and x for x in allowed):raise SystemExit('必须配置 allowed_hosts。')
    bootstrap()
    server=ThreadingHTTPServer((host,port),Handler);server.daemon_threads=True;server.allowed_hosts={x.lower() for x in allowed};server.secure=secure
    if secure:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2;ctx.load_cert_chain(certfile=cert,keyfile=key);server.socket=ctx.wrap_socket(server.socket,server_side=True)
    print('Ekko Script Web 已启动。允许的访问地址：',flush=True)
    for name in allowed:print(('https://' if secure else 'http://')+name+':'+str(port),flush=True)
    if not secure:print('当前仅本机可访问；要在内网共享，请配置可信 HTTPS 证书。',flush=True)
    print('保持窗口开启，关闭窗口会停止服务。',flush=True);server.serve_forever()
if __name__=='__main__':start()
