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

const displayValue = (value: any) => {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const rangeLabel = (rule: any) => {
  const range = rule.score_range;
  if (!range) return '按配置评分';
  const unit = range.unit ? ` ${range.unit}` : '';
  if (range.kind === '满分区间') return `${displayValue(range.min)} – ${displayValue(range.max)}${unit} 满分`;
  if (range.kind === '误差范围') return `${displayValue(range.min)} – ${displayValue(range.max)}${unit} 满分`;
  if (range.kind === '越高越好') return `≥ ${displayValue(range.full_score_target)}${unit} 满分；≤ ${displayValue(range.zero_score_anchor)}${unit} 0 分`;
  if (range.kind === '越低越好') return `≤ ${displayValue(range.full_score_target)}${unit} 满分；≥ ${displayValue(range.zero_score_anchor)}${unit} 0 分`;
  if (range.kind === '目标值') return `目标 ${displayValue(range.target)}${unit}`;
  if (range.kind === '精确匹配') return `精确匹配：${displayValue(range.expected)}`;
  if (range.kind === '结构身份匹配') return '按结构身份匹配';
  return '按配置评分';
};

const typeLabel = (type: string | undefined) => ({
  maximize: '最大化', minimize: '最小化', window: '区间', target: '目标值', numeric_gold: '数值答案', exact_string: '精确文本', atom_identity: '结构身份', gold_answer: '标准答案',
}[type || ''] || type || '评分规则');

const answerLabel = (rule: any) => rule.standard_answer === null || rule.standard_answer === undefined
  ? (rule.type === 'gold_answer' ? '未提供' : '无固定答案（按目标评分）')
  : displayValue(rule.standard_answer);

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

}

createRoot(document.getElementById('root')!).render(<App />);
