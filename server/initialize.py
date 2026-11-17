import sys, json, os, getpass, secrets
import team_server as app
b=app.base
with app.connect() as c:
    if c.execute('SELECT count(*) FROM users').fetchone()[0]:
        print('已有账号，初始化已跳过。');sys.exit(0)
    username=os.environ.get('EKKO_INITIAL_USER') or input('管理员账号：').strip()
    password=os.environ.get('EKKO_INITIAL_PASSWORD') or getpass.getpass('初始密码（数字和字母，首次登录后更换）：')
    if not b.valid_name(username) or not b.valid_password(password):raise SystemExit('账号或初始密码不符合要求')
    salt=secrets.token_bytes(16)
    c.execute('INSERT INTO users(username,salt,password_hash,role,active) VALUES(?,?,?,?,1)',(username,salt,b.password_hash(password,salt),'admin'))
    c.execute('INSERT INTO profiles(username,name,team,tag,joined,must_change) VALUES(?,?,?,?,?,1)',(username,username,'市场部','市场部主管',app.now()))
    demo=b.DATA/'demo.json'
    if demo.exists():
        entries=json.loads(demo.read_text(encoding='utf-8-sig'))['entries']
        for e in entries:e['createdBy']=username
        c.execute('UPDATE state SET entries=?,version=1 WHERE id=1',(json.dumps(entries,ensure_ascii=False),))
    b.log(c,username,'初始化团队工作台');c.commit()
print('管理员和五组联动示例已初始化，首次登录需要修改密码。')
