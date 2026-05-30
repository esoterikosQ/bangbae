import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTransactions, updateTransaction, deleteTransaction, getCategories } from '../api';

function formatAmount(amount) {
  const abs = Math.abs(amount);
  return (amount < 0 ? '-' : '') + abs.toLocaleString() + '원';
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function TransactionItem({ tx, categories, onUpdate, onDelete, onReceipt }) {
  const [editing, setEditing] = useState(false);
  const [categoryId, setCategoryId] = useState(tx.category_id || '');
  const [memo, setMemo] = useState(tx.memo || '');
  const [merchant, setMerchant] = useState(tx.merchant || '');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const data = {};
      if (categoryId !== (tx.category_id || '')) data.category_id = categoryId || null;
      if (memo !== (tx.memo || '')) data.memo = memo || null;
      if (merchant !== (tx.merchant || '')) data.merchant = merchant || null;
      if (Object.keys(data).length > 0) {
        await onUpdate(tx.id, data);
      }
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const isCancel = tx.amount < 0;

  return (
    <div className={`rounded-xl bg-slate-900 px-4 py-3 transition-all ${editing ? 'ring-1 ring-emerald-500/50' : ''}`}>
      <div className="flex items-start justify-between" onClick={() => !editing && setEditing(true)}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-200 truncate">
              {tx.merchant || '미상'}
            </span>
            {isCancel && (
              <span className="shrink-0 rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] font-medium text-rose-400">
                취소
              </span>
            )}
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
            <span>{formatDate(tx.transacted_at)}</span>
            <span>·</span>
            <span>{tx.payment_method || '미분류'}</span>
          </div>
          {tx.category_name && (
            <span className="mt-1 inline-block rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400">
              {tx.category_name}
            </span>
          )}
          {tx.memo && (
            <p className="mt-1 text-xs text-slate-500 italic">{tx.memo}</p>
          )}
        </div>
        <span className={`ml-3 shrink-0 text-sm font-semibold ${isCancel ? 'text-rose-400' : 'text-slate-100'}`}>
          {formatAmount(tx.amount)}
        </span>
      </div>

      {editing && (
        <div className="mt-3 space-y-2 border-t border-slate-800 pt-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">거래처</label>
            <input
              type="text"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">분류</label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-500"
            >
              <option value="">미분류</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">메모</label>
            <input
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="메모 입력"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-500"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={save}
              disabled={saving}
              className="flex-1 rounded-lg bg-emerald-600 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              {saving ? '저장 중...' : '저장'}
            </button>
            <button
              onClick={() => onReceipt(tx.id)}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-amber-400 hover:text-amber-300"
            >
              {tx.has_receipt ? '🧾 재스캔' : '🧾 영수증'}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
            >
              취소
            </button>
            <button
              onClick={() => { if (confirm('삭제하시겠습니까?')) onDelete(tx.id); }}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-rose-400 hover:text-rose-300"
            >
              삭제
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Transactions() {
  const now = new Date();
  const navigate = useNavigate();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [year, month]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [txRes, catRes] = await Promise.all([
        getTransactions(year, month),
        getCategories(),
      ]);
      setTransactions(txRes.data);
      setCategories(catRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (id, data) => {
    await updateTransaction(id, data);
    await loadData();
  };

  const handleDelete = async (id) => {
    await deleteTransaction(id);
    await loadData();
  };

  const prev = () => {
    if (month === 1) { setYear(year - 1); setMonth(12); }
    else setMonth(month - 1);
  };
  const next = () => {
    if (month === 12) { setYear(year + 1); setMonth(1); }
    else setMonth(month + 1);
  };

  return (
    <div className="py-2">
      <div className="flex items-center justify-between py-4">
        <button onClick={prev} className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-800">◀</button>
        <h2 className="text-lg font-semibold text-slate-100">{year}년 {month}월</h2>
        <button onClick={next} className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-800">▶</button>
      </div>

      {loading ? (
        <p className="py-8 text-center text-slate-500">불러오는 중...</p>
      ) : transactions.length === 0 ? (
        <p className="py-8 text-center text-slate-500">거래 내역이 없습니다</p>
      ) : (
        <div className="space-y-2">
          {transactions.map((tx) => (
            <TransactionItem
              key={tx.id}
              tx={tx}
              categories={categories}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              onReceipt={(id) => navigate(`/receipt/${id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
