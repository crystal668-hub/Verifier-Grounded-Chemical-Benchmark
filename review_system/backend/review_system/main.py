import io, json, os, secrets, zipfile
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from .config import MAX_ATTACHMENT_BYTES, DATA_DIR
from .db import SessionLocal, init_db
from .models import Attachment, Comment, Draft, DraftRevision, ReviewEvent, SnapshotTask, SnapshotTrack, SourceSnapshot, User
from .schemas import CommentIn, DecisionIn, DraftIn, LoginIn, UserIn
from .security import create_session, current_user, hash_password, require_developer, verify_password
from .source import load_catalog

app=FastAPI(title="VGB Task Review API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def db():
    session=SessionLocal()
    try: yield session
    finally: session.close()

def auth(request: Request, database: DBSession = Depends(db)) -> User: return current_user(request, database)
def developer(user: User = Depends(auth)) -> User: return require_developer(user)

@app.on_event("startup")
def startup():
    init_db()
    with SessionLocal() as database:
        if database.scalar(select(User).limit(1)) is None:
            username=os.getenv("REVIEW_ADMIN_USER", "admin"); password=os.getenv("REVIEW_ADMIN_PASSWORD", "change-me-now")
            database.add(User(username=username,password_hash=hash_password(password),role="developer")); database.commit()
        if database.scalar(select(SourceSnapshot).where(SourceSnapshot.status=="active")) is None:
            sync_catalog(database)

def sync_catalog(database: DBSession) -> SourceSnapshot:
    catalog=load_catalog(); existing=database.scalar(select(SourceSnapshot).where(SourceSnapshot.fingerprint==catalog["fingerprint"]))
    if existing: return existing
    snapshot=SourceSnapshot(commit=catalog["commit"], fingerprint=catalog["fingerprint"], status="active")
    database.add(snapshot); database.flush()
    for track in catalog["tracks"]:
        st=SnapshotTrack(snapshot_id=snapshot.id,name=track["name"],version=track["version"],display_name=track["display_name"]); database.add(st); database.flush()
        for task in track["tasks"]:
            database.add(SnapshotTask(track_id=st.id,task_id=task["task_id"],version=task["version"],fingerprint=task["fingerprint"],data_json=json.dumps(task["data"],ensure_ascii=False),view_json=json.dumps(task["view"],ensure_ascii=False),scoring_json=json.dumps(task["scoring"],ensure_ascii=False),schema_json=json.dumps(task["schema"],ensure_ascii=False),attachments_json=json.dumps(task["attachments"],ensure_ascii=False)))
    database.commit(); return snapshot

def active_snapshot(database: DBSession) -> SourceSnapshot:
    snapshot=database.scalar(select(SourceSnapshot).where(SourceSnapshot.status=="active").order_by(SourceSnapshot.id.desc()))
    if not snapshot: raise HTTPException(503,"题库尚未同步")
    return snapshot

@app.post("/api/v1/auth/login")
def login(payload: LoginIn, response: Response, database: DBSession = Depends(db)):
    user=database.scalar(select(User).where(User.username==payload.username))
    if not user or not user.active or not verify_password(payload.password,user.password_hash): raise HTTPException(401,"用户名或密码错误")
    token,csrf=create_session(database,user); response.set_cookie("review_session",token,httponly=True,samesite="lax",secure=False,max_age=604800); return {"user":{"id":user.id,"username":user.username,"role":user.role},"csrf_token":csrf}

@app.post("/api/v1/auth/logout")
def logout(response: Response, request: Request, database: DBSession = Depends(db), user: User = Depends(auth)):
    response.delete_cookie("review_session"); return {"ok":True}

@app.get("/api/v1/auth/me")
def me(user: User = Depends(auth)): return {"id":user.id,"username":user.username,"role":user.role}

@app.get("/api/v1/users")
def users(database: DBSession=Depends(db), user: User=Depends(developer)):
    return [{"id":x.id,"username":x.username,"role":x.role,"active":x.active} for x in database.scalars(select(User).order_by(User.username)).all()]

@app.post("/api/v1/users")
def create_user(payload: UserIn, database: DBSession=Depends(db), user: User=Depends(developer)):
    if database.scalar(select(User).where(User.username==payload.username)):
        raise HTTPException(409,"用户名已存在")
    row=User(username=payload.username,password_hash=hash_password(payload.password),role=payload.role); database.add(row); database.commit(); database.refresh(row); return {"id":row.id,"username":row.username,"role":row.role}

@app.get("/api/v1/tracks")
def tracks(database: DBSession=Depends(db), user: User=Depends(auth)):
    snapshot=active_snapshot(database); return {"snapshot":{"id":snapshot.id,"commit":snapshot.commit,"fingerprint":snapshot.fingerprint},"tracks":[{"name":x.name,"version":x.version,"display_name":x.display_name,"task_count":len(x.tasks)} for x in snapshot.tracks]}

@app.get("/api/v1/tracks/{track}/tasks")
def task_list(track: str, q: str|None=None, status: str|None=None, database: DBSession=Depends(db), user: User=Depends(auth)):
    snapshot=active_snapshot(database); item=next((x for x in snapshot.tracks if x.name==track),None)
    if not item: raise HTTPException(404,"track 不存在")
    tasks=[x for x in item.tasks if (not q or q.lower() in x.task_id.lower() or q.lower() in json.loads(x.view_json).get("prompt","").lower()) and (not status or x.review_status==status)]
    return {"track":track,"tasks":[{"task_id":x.task_id,"version":x.version,"status":x.review_status,"summary":json.loads(x.view_json).get("object_type")} for x in tasks]}

def find_task(track: str, task_id: str, database: DBSession) -> SnapshotTask:
    snapshot=active_snapshot(database); item=next((x for x in snapshot.tracks if x.name==track),None)
    task=next((x for x in item.tasks if x.task_id==task_id),None) if item else None
    if not task: raise HTTPException(404,"题目不存在")
    return task

@app.get("/api/v1/tracks/{track}/tasks/{task_id}")
def task_detail(track: str, task_id: str, database: DBSession=Depends(db), user: User=Depends(auth)):
    task=find_task(track,task_id,database); view=json.loads(task.view_json); view["task_id"]=task.task_id; view["review_status"]=task.review_status; view["source_fingerprint"]=task.fingerprint; view["attachments"]=[{k:v for k,v in a.items() if k not in {"content"}} for a in json.loads(task.attachments_json)]; return view

@app.get("/api/v1/tracks/{track}/tasks/{task_id}/scoring")
def task_scoring(track: str, task_id: str, database: DBSession=Depends(db), user: User=Depends(auth)): return json.loads(find_task(track,task_id,database).scoring_json)
@app.get("/api/v1/tracks/{track}/tasks/{task_id}/schema")
def task_schema(track: str, task_id: str, database: DBSession=Depends(db), user: User=Depends(auth)): return json.loads(find_task(track,task_id,database).schema_json)
@app.get("/api/v1/tracks/{track}/tasks/{task_id}/attachments")
def task_attachments(track: str, task_id: str, database: DBSession=Depends(db), user: User=Depends(auth)): return {"attachments":[{k:v for k,v in a.items() if k not in {"content"}} for a in json.loads(find_task(track,task_id,database).attachments_json)]}

@app.get("/api/v1/tracks/{track}/tasks/{task_id}/attachments/{name}")
def task_attachment(track: str, task_id: str, name: str, database: DBSession=Depends(db), user: User=Depends(auth)):
    item=next((x for x in json.loads(find_task(track,task_id,database).attachments_json) if x.get("name")==name),None)
    if not item: raise HTTPException(404,"附件不存在")
    return Response(item.get("content","") if isinstance(item.get("content"),str) else "", media_type=item.get("media_type","text/plain"), headers={"Content-Disposition": f'inline; filename="{name}"'})

@app.get("/api/v1/tasks/{task_id}/comments")
def comments(task_id: str, database: DBSession=Depends(db), user: User=Depends(auth)):
    rows=database.scalars(select(Comment).where(Comment.target_id==task_id).order_by(Comment.created_at)).all(); return [{"id":x.id,"body":x.body,"author":x.author.username,"resolved":x.resolved,"parent_id":x.parent_id,"created_at":x.created_at} for x in rows]

@app.post("/api/v1/tasks/{task_id}/comments")
def add_comment(task_id: str, payload: CommentIn, database: DBSession=Depends(db), user: User=Depends(auth)):
    row=Comment(target_type="task",target_id=task_id,author_id=user.id,body=payload.body,parent_id=payload.parent_id); database.add(row); database.commit(); database.refresh(row); return {"id":row.id,"body":row.body}

@app.post("/api/v1/comments/{comment_id}/resolve")
def resolve_comment(comment_id: int, database: DBSession=Depends(db), user: User=Depends(auth)):
    row=database.get(Comment,comment_id)
    if not row: raise HTTPException(404,"批注不存在")
    row.resolved=True; database.commit(); return {"ok":True}

@app.post("/api/v1/tasks/{task_id}/review")
def review_task(task_id: str, payload: DecisionIn, database: DBSession=Depends(db), user: User=Depends(developer)):
    task = database.scalar(select(SnapshotTask).where(SnapshotTask.task_id == task_id))
    if not task: raise HTTPException(404, "题目不存在")
    previous = task.review_status; task.review_status = payload.status
    database.add(ReviewEvent(target_type="task", target_id=task_id, from_status=previous, to_status=payload.status, note=payload.note, actor_id=user.id)); database.commit()
    return {"task_id": task_id, "status": task.review_status}

@app.post("/api/v1/source-sync")
def source_sync(database: DBSession=Depends(db), user: User=Depends(developer)):
    try: snapshot=sync_catalog(database); return {"ok":True,"snapshot_id":snapshot.id,"fingerprint":snapshot.fingerprint}
    except Exception as exc: raise HTTPException(422,f"同步失败：{exc}") from exc

@app.post("/api/v1/drafts")
def create_draft(payload: DraftIn, database: DBSession=Depends(db), user: User=Depends(auth)):
    row=Draft(owner_id=user.id,track=payload.track,title=payload.title,current_revision=1); database.add(row); database.flush(); database.add(DraftRevision(draft_id=row.id,revision=1,payload_json=json.dumps(payload.payload,ensure_ascii=False),created_by=user.id)); database.commit(); return {"id":row.id,"status":row.status,"revision":1}

@app.get("/api/v1/drafts")
def drafts(database: DBSession=Depends(db), user: User=Depends(auth)):
    rows=database.scalars(select(Draft).order_by(Draft.updated_at.desc())).all(); rows=[x for x in rows if x.owner_id==user.id or user.role=="developer" or x.status not in {"draft"}]; return [{"id":x.id,"track":x.track,"title":x.title,"status":x.status,"revision":x.current_revision} for x in rows]

@app.post("/api/v1/drafts/{draft_id}/submit")
def submit_draft(draft_id:int,database:DBSession=Depends(db),user:User=Depends(auth)):
    row=database.get(Draft,draft_id)
    if not row or (row.owner_id!=user.id and user.role!="developer"): raise HTTPException(404,"草稿不存在")
    row.status="pending"; database.commit(); return {"id":row.id,"status":row.status}

@app.post("/api/v1/drafts/{draft_id}/validate")
def validate_draft(draft_id:int,database:DBSession=Depends(db),user:User=Depends(auth)):
    row=database.get(Draft,draft_id)
    if not row or (row.owner_id!=user.id and user.role!="developer"): raise HTTPException(404,"草稿不存在")
    revision=database.scalar(select(DraftRevision).where(DraftRevision.draft_id==row.id,DraftRevision.revision==row.current_revision))
    try:
        payload=json.loads(revision.payload_json) if revision else {}
        errors=[]
        for key in ("task_id","prompt","answer_schema"):
            if not payload.get(key): errors.append(f"缺少 {key}")
        return {"valid":not errors,"errors":errors}
    except Exception as exc:
        return {"valid":False,"errors":[str(exc)]}

@app.post("/api/v1/drafts/{draft_id}/decision")
def draft_decision(draft_id:int,payload:DecisionIn,database:DBSession=Depends(db),user:User=Depends(developer)):
    row=database.get(Draft,draft_id)
    if not row: raise HTTPException(404,"草稿不存在")
    previous=row.status; row.status=payload.status; row.approved_revision=row.current_revision if payload.status=="approved" else None; database.add(ReviewEvent(target_type="draft",target_id=str(draft_id),from_status=previous,to_status=payload.status,note=payload.note,actor_id=user.id)); database.commit(); return {"id":row.id,"status":row.status}

@app.get("/api/v1/drafts/{draft_id}/export")
def export_draft(draft_id:int,database:DBSession=Depends(db),user:User=Depends(developer)):
    row=database.get(Draft,draft_id)
    if not row or row.status!="approved": raise HTTPException(409,"仅已批准草稿可导出")
    revision=database.scalar(select(DraftRevision).where(DraftRevision.draft_id==row.id,DraftRevision.revision==row.approved_revision)); payload=revision.payload_json if revision else "{}"
    content=io.BytesIO();
    with zipfile.ZipFile(content,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("draft.json",payload); archive.writestr("README.txt","由 VGB 题目审核系统导出，请开发者补全并合入题库。\n")
    content.seek(0); return StreamingResponse(content,media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="draft-{draft_id}.zip"'})

_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
