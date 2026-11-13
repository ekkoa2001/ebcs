import hashlib
from io import BytesIO
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text
from app.database import SessionLocal
from app.dependencies import require_permission, require_session
from app.dependencies import require_csrf
from app.object_store import get_object, list_objects, put_object

router = APIRouter(prefix="/api/v1", tags=["media"])


@router.get("/media")
def list_media(request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db: return [dict(x._mapping) for x in db.execute(text("SELECT * FROM media_files ORDER BY created_at DESC")).all()]


@router.get("/media/{identifier}")
def media_detail(identifier:str, request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db:
        row=db.execute(text("SELECT * FROM media_files WHERE id=:id"),{"id":identifier}).first()
        if not row: raise HTTPException(404,"图片不存在")
        return dict(row._mapping)


@router.post("/media/upload")
async def upload_media(request:Request,file:UploadFile=File(...)):
    current=require_session(request); require_csrf(request,current); require_permission(current,"content.create")
    raw=await file.read(25*1024*1024+1)
    if not raw or len(raw)>25*1024*1024: raise HTTPException(400,"图片为空或超过 25 MB")
    digest=hashlib.sha256(raw).hexdigest()
    with SessionLocal() as db:
        found=db.execute(text("SELECT * FROM media_files WHERE sha256=:sha LIMIT 1"),{"sha":digest}).first()
        if found: return {**dict(found._mapping),"deduplicated":True}
    try:
        image=Image.open(BytesIO(raw)); image.verify(); image=Image.open(BytesIO(raw)); source_format=image.format; image=ImageOps.exif_transpose(image); image.load()
    except (UnidentifiedImageError,OSError,ValueError): raise HTTPException(400,"文件不是可解码的图片")
    allowed={"JPEG","PNG","WEBP","GIF"}
    if source_format not in allowed: raise HTTPException(400,"仅支持 JPG、PNG、WebP、GIF")
    width,height=image.size
    if width<1 or height<1 or width*height>80_000_000: raise HTTPException(400,"图片尺寸无效或像素过大")
    mime={"JPEG":"image/jpeg","PNG":"image/png","WEBP":"image/webp","GIF":"image/gif"}[source_format]
    ext={"JPEG":"jpg","PNG":"png","WEBP":"webp","GIF":"gif"}[source_format]
    identifier=digest; original=f"originals/{digest}.{ext}"; preview=f"previews/{digest}.webp"; thumbnail=f"thumbnails/{digest}.webp"
    put_object(original,mime,raw)
    def rendition(limit,quality):
        frame=image.convert("RGB"); frame.thumbnail((limit,limit),Image.Resampling.LANCZOS); out=BytesIO(); frame.save(out,"WEBP",quality=quality,method=6); return out.getvalue()
    put_object(preview,"image/webp",rendition(1800,85)); put_object(thumbnail,"image/webp",rendition(480,78))
    now=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    with SessionLocal() as db:
        db.execute(text("INSERT INTO media_files(id,mime,sha256,byte_size,width,height,original_path,preview_path,thumbnail_path,created_at) VALUES(:id,:mime,:sha,:size,:w,:h,:original,:preview,:thumb,:created)"),{"id":identifier,"mime":mime,"sha":digest,"size":len(raw),"w":width,"h":height,"original":original,"preview":preview,"thumb":thumbnail,"created":now}); db.commit()
    return {"id":identifier,"mime":mime,"sha256":digest,"byte_size":len(raw),"width":width,"height":height,"original_path":original,"preview_path":preview,"thumbnail_path":thumbnail,"created_at":now,"deduplicated":False}


@router.get("/media/{identifier}/{variant}")
def read_media(identifier:str,variant:str,request:Request):
    require_session(request)
    if variant not in {"original","preview","thumbnail"}: raise HTTPException(404,"图片版本不存在")
    with SessionLocal() as db:
        row=db.execute(text("SELECT mime,original_path,preview_path,thumbnail_path FROM media_files WHERE id=:id"),{"id":identifier}).first()
    if not row: raise HTTPException(404,"图片不存在")
    path={"original":row.original_path,"preview":row.preview_path,"thumbnail":row.thumbnail_path}[variant]; raw=get_object(path)
    if raw is None: raise HTTPException(404,"图片文件不存在")
    legacy_original = path == row.original_path
    return Response(raw,media_type=row.mime if variant=="original" or legacy_original else "image/webp",headers={"Cache-Control":"private, max-age=86400"})


@router.get("/media-maintenance/orphans")
def orphan_media(request:Request):
    current=require_session(request); require_permission(current,"admin.access")
    with SessionLocal() as db:
        referenced=set(db.execute(text("SELECT original_path FROM media_files UNION SELECT preview_path FROM media_files UNION SELECT thumbnail_path FROM media_files")).scalars())
    stored=set(list_objects()); return {"orphanObjects":sorted(stored-referenced),"missingObjects":sorted(referenced-stored),"stored":len(stored),"referenced":len(referenced)}
