import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMonthlySummary, getBudgetComparison } from '../api';

function MonthSelector({ year, month, onChange }) {
  const prev = () => {
    if (month === 1) onChange(year - 1, 12);
    else onChange(year, month - 1);
  };
  const next = () => {
    if (month === 12) onChange(year + 1, 1);
    else onChange(year, month + 1);
  };

  return (
    <div className="flex items-center justify-between py-4">
      <button onClick={prev} className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200">
        ◀
      </button>
      <h2 className="text-lg font-semibold text-slate-100">
        {year}년 {month}월
      </h2>
      <button onClick={next} className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200">
        ▶
      </button>
    </div>
  );
}

function formatAmount(amount) {
  const abs = Math.abs(amount);
  return (amount < 0 ? '-' : '') + abs.toLocaleString() + '원';
}

export default function Dashboard() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [summary, setSummary] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, [year, month]);

  const loadData = async () => {
    setLoading(true);
    try {
      const yearMonth = `${year}-${String(month).padStart(2, '0')}`;
      const [sumRes, cmpRes] = await Promise.all([
        getMonthlySummary(year, month),
        getBudgetComparison(yearMonth).catch(() => ({ data: [] })),
      ]);
      setSummary(sumRes.data);
      setComparison(cmpRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleMonthChange = (y, m) => {
    setYear(y);
    setMonth(m);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-500">불러오는 중...</p>
      </div>
    );
  }

  return (
    <div className="py-2">
      <MonthSelector year={year} month={month} onChange={handleMonthChange} />

      {/* 총 지출 카드 */}
      <div className="mb-6 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 p-5 shadow-lg">
        <p className="mb-1 text-xs font-medium uppercase tracking-widest text-slate-500">
          총 지출
        </p>
        <p className="text-3xl font-bold tracking-tight text-slate-50">
          {summary ? formatAmount(summary.total_amount) : '0원'}
        </p>
        <p className="mt-1 text-sm text-slate-500">
          {summary?.transaction_count || 0}건
        </p>
      </div>

      {/* 분류별 지출 */}
      {summary?.by_category?.length > 0 && (
        <section className="mb-6">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
            분류별
          </h3>
          <div className="space-y-2">
            {summary.by_category.map((cat, i) => {
              const pct = summary.total_amount
                ? Math.round((cat.total / summary.total_amount) * 100)
                : 0;
              return (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3"
                >
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-200">
                        {cat.category || '미분류'}
                      </span>
                      <span className="text-sm font-semibold text-slate-100">
                        {formatAmount(cat.total)}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-800">
                      <div
                        className="h-1.5 rounded-full bg-emerald-500 transition-all duration-500"
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                  <span className="ml-3 text-xs text-slate-500 w-8 text-right">{pct}%</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 결제수단별 */}
      {summary?.by_payment_method?.length > 0 && (
        <section className="mb-6">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
            결제수단별
          </h3>
          <div className="space-y-1.5">
            {summary.by_payment_method.map((pm, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3"
              >
                <span className="text-sm text-slate-300">
                  {pm.payment_method || '미분류'}
                </span>
                <div className="text-right">
                  <span className="text-sm font-semibold text-slate-100">
                    {formatAmount(pm.total)}
                  </span>
                  <span className="ml-2 text-xs text-slate-500">{pm.count}건</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 예산 대비 */}
      {comparison.length > 0 && (
        <section className="mb-6">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
            예산 대비
          </h3>
          <div className="space-y-2">
            {comparison.map((item, i) => {
              const pct = item.budget ? Math.round((item.actual / item.budget) * 100) : 0;
              const over = item.actual > item.budget;
              return (
                <div
                  key={i}
                  className="rounded-xl bg-slate-900 px-4 py-3"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-200">
                      {item.category || '미분류'}
                    </span>
                    <span className={`text-xs font-semibold ${over ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {pct}%
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-800">
                    <div
                      className={`h-1.5 rounded-full transition-all duration-500 ${
                        over ? 'bg-rose-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  <div className="mt-1 flex justify-between text-xs text-slate-500">
                    <span>{formatAmount(item.actual)}</span>
                    <span>/ {formatAmount(item.budget)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
