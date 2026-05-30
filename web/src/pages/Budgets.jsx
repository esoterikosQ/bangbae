import { useState, useEffect } from 'react';
import { getBudgets, createBudget, updateBudget, deleteBudget, getCategories } from '../api';

function formatAmount(amount) {
  return Math.abs(amount).toLocaleString() + '원';
}

export default function Budgets() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [form, setForm] = useState({
    category_id: '',
    budget_amount: '',
    is_income: false,
  });

  const yearMonth = `${year}-${String(month).padStart(2, '0')}`;

  useEffect(() => {
    loadData();
  }, [year, month]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [budRes, catRes] = await Promise.all([
        getBudgets(yearMonth),
        getCategories(),
      ]);
      setBudgets(budRes.data);
      setCategories(catRes.data);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!form.budget_amount) return;
    await createBudget({
      year_month: yearMonth,
      category_id: form.category_id ? Number(form.category_id) : null,
      budget_amount: parseInt(form.budget_amount),
      is_income: form.is_income,
    });
    setForm({ category_id: '', budget_amount: '', is_income: false });
    setShowForm(false);
    await loadData();
  };

  const handleDelete = async (id) => {
    if (!confirm('이 예산을 삭제하시겠습니까?')) return;
    await deleteBudget(id);
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

  const incomeBudgets = budgets.filter((b) => b.is_income);
  const expenseBudgets = budgets.filter((b) => !b.is_income);
  const totalIncome = incomeBudgets.reduce((s, b) => s + b.budget_amount, 0);
  const totalExpense = expenseBudgets.reduce((s, b) => s + b.budget_amount, 0);

  return (
    <div className="py-2">
      <div className="flex items-center justify-between py-4">
        <button onClick={prev} className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-800">◀</button>
        <h2 className="text-lg font-semibold text-slate-100">{year}년 {month}월 예산</h2>
        <button onClick={next} className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-800">▶</button>
      </div>

      {/* 요약 */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-slate-900 p-4">
          <p className="text-xs text-slate-500">예상 수입</p>
          <p className="text-lg font-bold text-emerald-400">{formatAmount(totalIncome)}</p>
        </div>
        <div className="rounded-xl bg-slate-900 p-4">
          <p className="text-xs text-slate-500">예상 지출</p>
          <p className="text-lg font-bold text-rose-400">{formatAmount(totalExpense)}</p>
        </div>
      </div>

      {loading ? (
        <p className="py-8 text-center text-slate-500">불러오는 중...</p>
      ) : (
        <>
          {/* 수입 예산 */}
          {incomeBudgets.length > 0 && (
            <section className="mb-5">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">수입</h3>
              <div className="space-y-1.5">
                {incomeBudgets.map((b) => (
                  <div key={b.id} className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3">
                    <span className="text-sm text-slate-200">{b.category_name || '기타'}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-emerald-400">{formatAmount(b.budget_amount)}</span>
                      <button onClick={() => handleDelete(b.id)} className="text-xs text-slate-600 hover:text-rose-400">삭제</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 지출 예산 */}
          {expenseBudgets.length > 0 && (
            <section className="mb-5">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">지출</h3>
              <div className="space-y-1.5">
                {expenseBudgets.map((b) => (
                  <div key={b.id} className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3">
                    <span className="text-sm text-slate-200">{b.category_name || '기타'}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-100">{formatAmount(b.budget_amount)}</span>
                      <button onClick={() => handleDelete(b.id)} className="text-xs text-slate-600 hover:text-rose-400">삭제</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {budgets.length === 0 && (
            <p className="py-8 text-center text-slate-500">등록된 예산이 없습니다</p>
          )}
        </>
      )}

      {/* 추가 폼 */}
      {showForm ? (
        <div className="mt-4 space-y-3 rounded-2xl bg-slate-900 p-4">
          <div className="flex gap-2">
            <button
              onClick={() => setForm((f) => ({ ...f, is_income: false }))}
              className={`flex-1 rounded-lg py-2 text-sm font-medium ${
                !form.is_income ? 'bg-slate-700 text-slate-100' : 'bg-slate-800 text-slate-500'
              }`}
            >
              지출
            </button>
            <button
              onClick={() => setForm((f) => ({ ...f, is_income: true }))}
              className={`flex-1 rounded-lg py-2 text-sm font-medium ${
                form.is_income ? 'bg-slate-700 text-slate-100' : 'bg-slate-800 text-slate-500'
              }`}
            >
              수입
            </button>
          </div>
          <select
            value={form.category_id}
            onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 outline-none"
          >
            <option value="">분류 선택</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <div className="relative">
            <input
              type="number"
              inputMode="numeric"
              value={form.budget_amount}
              onChange={(e) => setForm((f) => ({ ...f, budget_amount: e.target.value }))}
              placeholder="금액"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 pr-8 text-sm text-slate-100 outline-none"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">원</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!form.budget_amount}
              className="flex-1 rounded-lg bg-emerald-600 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
            >
              저장
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg bg-slate-800 px-4 py-2.5 text-sm text-slate-400"
            >
              취소
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="mt-4 w-full rounded-xl border border-dashed border-slate-700 py-3 text-sm text-slate-500 hover:border-slate-500 hover:text-slate-300"
        >
          + 예산 추가
        </button>
      )}
    </div>
  );
}
