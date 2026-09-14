import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BookOpen, ChevronDown, FileText, MessageCircle, PanelRight, RefreshCw, Search, Send, ShieldCheck, X } from 'lucide-react';
import './styles.css';

type Track = { name: string; display_name: string; task_count: number };
type Task = { task_id: string; version: number; status: string; summary: string };
type Detail = Record<string, any>;
type User = { id: number; username: string; role: string; active: boolean };
type Tab = 'content' | 'scoring' | 'schema' | 'discussion';
type ResizeTarget = 'sidebar' | 'attachments';

const api = async (path: string, options: RequestInit = {}) => {
  const response = await fetch(path, { credentials: 'include', ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('change-me-now');
  const [error, setError] = useState('');

  return <main className="login"><div className="login-card"><div className="mark">VGB</div><p className="eyebrow">VERIFIER GROUNDED BENCHMARK</p><h1>题目审核工作台</h1><p className="muted">登录后查看题目、评分规则与协作批注。</p><input value={username} onChange={e => setUsername(e.target.value)} placeholder="用户名"/><input value={password} onChange={e => setPassword(e.target.value)} placeholder="密码" type="password"/><button onClick={async () => { try { const result = await api('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) }); localStorage.setItem('csrf', result.csrf_token); onLogin(); } catch { setError('登录失败，请检查账号。'); } }}>进入工作台</button>{error && <p className="error">{error}</p>}</div></main>;
}

function App() {
  const [logged, setLogged] = useState(false);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [track, setTrack] = useState('');
  const [expandedTrack, setExpandedTrack] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState('');
  const [detail, setDetail] = useState<Detail | null>(null);
  const [scoring, setScoring] = useState<Detail | null>(null);
  const [schema, setSchema] = useState<Detail | null>(null);
  const [attachment, setAttachment] = useState<any>(null);
  const [attachmentLoading, setAttachmentLoading] = useState('');
  const [comments, setComments] = useState<any[]>([]);
  const [comment, setComment] = useState('');
  const [commentSending, setCommentSending] = useState(false);
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('content');
  const [refreshing, setRefreshing] = useState(false);
  const [attachmentCollapsed, setAttachmentCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [attachmentWidth, setAttachmentWidth] = useState(320);
  const [resizeTarget, setResizeTarget] = useState<ResizeTarget | null>(null);
  const [notice, setNotice] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [userDialog, setUserDialog] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  const noticeTimer = useRef<number | undefined>(undefined);
  const resizeState = useRef<{ target: ResizeTarget; startX: number; startWidth: number } | null>(null);

  const notify = (message: string) => {
    setNotice(message);
    if (noticeTimer.current) window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(''), 2600);
  };

  useEffect(() => () => { if (noticeTimer.current) window.clearTimeout(noticeTimer.current); }, []);

  const loadTask = async (trackName: string, taskId: string) => {
    const [nextDetail, nextScoring, nextSchema, nextComments] = await Promise.all([
      api(`/api/v1/tracks/${trackName}/tasks/${taskId}`),
      api(`/api/v1/tracks/${trackName}/tasks/${taskId}/scoring`),
      api(`/api/v1/tracks/${trackName}/tasks/${taskId}/schema`),
      api(`/api/v1/tasks/${taskId}/comments`),
    ]);
    setDetail(nextDetail);
    setScoring(nextScoring);
    setSchema(nextSchema);
    setComments(nextComments);
    setAttachment(null);
    setActiveTab('content');
  };

  const refreshData = async () => {
    setRefreshing(true);
    try {
      const result = await api('/api/v1/tracks');
      setTracks(result.tracks);
      if (track) {
        const taskResult = await api(`/api/v1/tracks/${track}/tasks?q=${encodeURIComponent(query)}`);
        setTasks(taskResult.tasks);
        if (selected) await loadTask(track, selected);
      }
      notify('已刷新题库和当前题目');
    } catch {
      notify('刷新失败，请稍后重试');
    } finally {
      setRefreshing(false);
    }
  };

  const openUsers = async () => {
    setUserDialog(true);
    setUsersLoading(true);
    try {
      setUsers(await api('/api/v1/users'));
    } catch {
      notify('无法加载用户管理');
    } finally {
      setUsersLoading(false);
    }
  };

  const openAttachment = async (item: any) => {
    if (!item) return;
    setAttachmentLoading(item.name);
    try {
      const response = await fetch(`/api/v1/tracks/${track}/tasks/${selected}/attachments/${encodeURIComponent(item.name)}`, { credentials: 'include' });
      if (!response.ok) throw new Error('附件加载失败');
      setAttachment({ ...item, content: await response.text() });
    } catch {
      notify('附件加载失败，请重试');
    } finally {
      setAttachmentLoading('');
    }
  };

  const sendComment = async () => {
    const body = comment.trim();
    if (!body || commentSending) return;
    setCommentSending(true);
    try {
      await api(`/api/v1/tasks/${selected}/comments`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': localStorage.getItem('csrf') || '' }, body: JSON.stringify({ body }) });
      setComment('');
      setComments(await api(`/api/v1/tasks/${selected}/comments`));
      notify('批注已发布');
    } catch {
      notify('批注发布失败，请重试');
    } finally {
      setCommentSending(false);
    }
  };

  const beginResize = (target: ResizeTarget, event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    resizeState.current = { target, startX: event.clientX, startWidth: target === 'sidebar' ? sidebarWidth : attachmentWidth };
    setResizeTarget(target);
  };

  useEffect(() => {
    if (!resizeTarget) return;
    const move = (event: PointerEvent) => {
      const state = resizeState.current;
      if (!state) return;
      const delta = event.clientX - state.startX;
      if (state.target === 'sidebar') setSidebarWidth(Math.min(420, Math.max(220, state.startWidth + delta)));
      else setAttachmentWidth(Math.min(480, Math.max(240, state.startWidth - delta)));
    };
    const stop = () => { resizeState.current = null; setResizeTarget(null); };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop, { once: true });
    return () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', stop); };
  }, [resizeTarget]);

  useEffect(() => { api('/api/v1/auth/me').then(() => setLogged(true)).catch(() => {}); }, []);
  useEffect(() => {
    if (!logged) return;
    api('/api/v1/tracks').then(result => {
      setTracks(result.tracks);
      if (result.tracks[0]) {
        setTrack(result.tracks[0].name);
        setExpandedTrack(result.tracks[0].name);
      }
    }).catch(() => notify('题库加载失败，请刷新重试'));
  }, [logged]);
  useEffect(() => {
    if (!track) return;
    api(`/api/v1/tracks/${track}/tasks?q=${encodeURIComponent(query)}`).then(result => {
      setTasks(result.tasks);
      if (!selected && result.tasks[0]) setSelected(result.tasks[0].task_id);
    }).catch(() => notify('题目列表加载失败'));
  }, [track, query]);
  useEffect(() => {
    if (!selected || !track) return;
    loadTask(track, selected).catch(() => notify('题目详情加载失败'));
  }, [selected, track]);

  if (!logged) return <Login onLogin={() => setLogged(true)} />;

  const workspaceStyle = {
    '--sidebar-width': `${sidebarWidth}px`,
    '--attachments-width': attachmentCollapsed ? '0px' : `${attachmentWidth}px`,
  } as React.CSSProperties;
  const promptParts = String(detail?.prompt || '').split(/\[附件：[^\]]+\]/);

 return <main className="app"><header><div className="brand"><div className="mark small">VGB</div><div><strong>题目审核</strong><span>Verifier Grounded Benchmark</span></div></div><div className="header-actions"><span className="live"><i />源码快照同步</span><button className="icon" aria-label="刷新题库" title="刷新题库" onClick={refreshData} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''} /></button><button className="avatar" aria-label="用户管理" title="用户管理" onClick={openUsers}>A</button></div></header><div className="workspace" style={workspaceStyle}><aside className="sidebar"><div className="side-title"><span>目录</span><span className="count">{tracks.length} tracks</span></div><label className="search"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="搜索题目 ID" /></label>{tracks.map(item => { const expanded = expandedTrack === item.name; return <div className="track" key={item.name}><button className="track-button" aria-expanded={expanded} onClick={() => { setExpandedTrack(expanded ? '' : item.name); if (!expanded && track !== item.name) { setTrack(item.name); setSelected(''); setTasks([]); } }}><BookOpen size={16} /><span>{item.display_name}</span><ChevronDown size={14} className={expanded ? 'chevron-open' : ''} /></button>{expanded && <div className="task-list">{track === item.name && tasks.map(task => <button className={`task ${selected === task.task_id ? 'active' : ''}`} onClick={() => setSelected(task.task_id)} key={task.task_id}><span>{task.task_id}</span><em>{task.status === 'pending' ? '待审核' : '已同步'}</em></button>)}</div>}</div>; })}<div className="sidebar-bottom"><button className="draft" onClick={() => notify('草稿提交功能即将开放')}><span>＋</span>提交 task 草稿</button><p>V1 · {new Date().getFullYear()}</p></div></aside><div className={`resize-handle ${resizeTarget === 'sidebar' ? 'resizing' : ''}`} role="separator" aria-label="调整目录栏宽度" onPointerDown={event => beginResize('sidebar', event)} /><section className="main-panel">{detail ? <><div className="content-head"><div><p className="eyebrow">{track} · v{detail.version}</p><h1>{selected}</h1></div><span className="status"><i />{detail.review_status === 'pending' ? '待审核' : '已同步'}</span></div><div className="tabs"><button className={activeTab === 'content' ? 'selected' : ''} onClick={() => setActiveTab('content')}>题目内容</button><button className={activeTab === 'scoring' ? 'selected' : ''} onClick={() => setActiveTab('scoring')}>评分细则</button><button className={activeTab === 'schema' ? 'selected' : ''} onClick={() => setActiveTab('schema')}>Schema</button><button className={activeTab === 'discussion' ? 'selected' : ''} onClick={() => setActiveTab('discussion')}>讨论 <span>{comments.length}</span></button></div><article>{activeTab === 'content' && <div className="prompt-card"><div className="section-label">题目说明</div><p className="prompt">{promptParts.map((part, index) => <React.Fragment key={index}>{part}{index < promptParts.length - 1 && <button className="attachment-ref" onClick={() => openAttachment(detail.attachments?.[index])}><FileText size={14} />{attachmentLoading === detail.attachments?.[index]?.name ? '加载中…' : '查看附件'}</button>}</React.Fragment>)}</p></div>}{activeTab === 'scoring' && <div className="rule-card"><div className="section-label">评分规则</div><div className="rules">{scoring?.rules?.map((rule: any) => <div className="rule" key={rule.property}><strong>{rule.property}</strong><span>{rule.type || rule.profile?.type}</span><small>{rule.profile?.unit || '—'}</small></div>)}</div></div>}{activeTab === 'schema' && <div className="meta-card"><div className="section-label">Schema 元数据</div><pre>{JSON.stringify(schema, null, 2)}</pre></div>}{activeTab === 'discussion' && <div className="discussion"><div className="section-label"><MessageCircle size={15} />题目讨论</div>{comments.map(item => <div className="comment" key={item.id}><b>{item.author}</b><span>{item.body}</span></div>)}<div className="comment-box"><input value={comment} onChange={e => setComment(e.target.value)} placeholder="写下审核备注…" onKeyDown={event => { if (event.key === 'Enter') void sendComment(); }} /><button onClick={() => void sendComment()} disabled={commentSending || !comment.trim()} aria-label="发布批注"><Send size={15} /></button></div></div>}</article></> : <div className="empty"><ShieldCheck size={30} /><h2>选择一道题目开始审核</h2></div>}</section><div className={`resize-handle attachment-resize ${resizeTarget === 'attachments' ? 'resizing' : ''}`} role="separator" aria-label="调整附件栏宽度" onPointerDown={event => beginResize('attachments', event)}><button className="collapse-handle" aria-label={attachmentCollapsed ? '展开附件栏' : '折叠附件栏'} title={attachmentCollapsed ? '展开附件栏' : '折叠附件栏'} onClick={() => setAttachmentCollapsed(collapsed => !collapsed)}><PanelRight size={14} /></button></div><aside className={`attachments ${attachmentCollapsed ? 'collapsed' : ''}`}><div className="attachment-head"><div><p className="eyebrow">辅助资料</p><h2>附件</h2></div><button className="collapse-button" aria-label="折叠附件栏" title="折叠附件栏" onClick={() => setAttachmentCollapsed(true)}><PanelRight size={18} /></button></div>{detail?.attachments?.length ? <>{detail.attachments.map((item: any) => <button className={`attachment-item ${attachment?.name === item.name ? 'active' : ''}`} onClick={() => void openAttachment(item)} key={item.name}><FileText size={17} /><span><b>{item.name}</b><small>{item.media_type} · 右栏预览</small></span></button>)}{attachment && <div className="preview"><div className="preview-title">{attachment.name}<span>仅右栏显示</span></div><pre>{attachment.content}</pre></div>}</> : <div className="no-attachment">本题没有附件</div>}</aside></div>{notice && <div className="toast" role="status">{notice}</div>}{userDialog && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setUserDialog(false); }}><section className="user-dialog" role="dialog" aria-modal="true" aria-labelledby="user-dialog-title"><div className="user-dialog-head"><h2 id="user-dialog-title">用户管理</h2><button className="close-button" aria-label="关闭用户管理" onClick={() => setUserDialog(false)}><X size={17} /></button></div>{usersLoading ? <p className="muted">正在加载用户…</p> : <div className="user-list">{users.map(user => <div className="user-row" key={user.id}><span><b>{user.username}</b><small>{user.role}</small></span><em className={user.active ? 'active' : ''}>{user.active ? '启用' : '停用'}</em></div>)}</div>}</section></div>}</main>;
}

createRoot(document.getElementById('root')!).render(<App />);
