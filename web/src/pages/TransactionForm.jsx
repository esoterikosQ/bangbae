import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createTransaction, getCategories } from '../api';

export default function TransactionForm() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    payment_method: '',
    merchant: '',
    amount: '',
    category_id: '',
    memo: '',
    date: new Date().toISOString().slice(0, 10),
    time: new Date().toTimeString().slice(0, 5),
  });

  useEffect(() => {
    getCategories().then((res) => setCategories(res.data));
  }, []);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!form.amount) return;

    setSaving(true);
    try {
      const transacted_at = new Date(`${form.date}T${form.time}:00`).toISOString();
      await createTransaction({
        payment_method: form.payment_method || null,
        merchant: form.merchant || null,
        amount: parseInt(form.amount),
        category_id: form.category_id ? Number(form.category_id) : null,
        memo: form.memo || null,
        transacted_at,
      });
      navigate('/transactions');
    } catch (err) {
      alert('저장 실패: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const presets = ['현금', '계좌이체', '카카오페이', '네이버페이'];

  return (
    <div className="py-4">
      <h2 className="mb-6 text-lg font-semibold text-slate-100">지출 직접 입력</h2>

      <div className="space-y-4">
        {/* 금액 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-500">금액</label>
          <div className="relative">
            <input
              type="number"
              inputMode="numeric"
              value={form.amount}
              onChange={(e) => handleChange('amount', e.target.value)}
              placeholder="0"
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 pr-10 text-xl font-semibold text-slate-100 outline-none focus:border-emerald-500"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-slate-500">원</span>
          </div>
        </div>

        {/* 날짜 / 시간 */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">날짜</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => handleChange('date', e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">시간</label>
            <input
              type="time"
              value={form.time}
              onChange={(e) => handleChange('time', e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* 결제수단 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-500">결제수단</label>
          <input
            type="text"
            value={form.payment_method}
            onChange={(e) => handleChange('payment_method', e.target.value)}
            placeholder="결제수단 입력"
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
          />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {presets.map((p) => (
              <button
                key={p}
                onClick={() => handleChange('payment_method', p)}
                className={`rounded-lg px-3 py-1.5 text-xs transition-colors ${
                  form.payment_method === p
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* 거래처 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-500">거래처</label>
          <input
            type="text"
            value={form.merchant}
            onChange={(e) => handleChange('merchant', e.target.value)}
            placeholder="거래처 입력"
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
          />
        </div>

        {/* 분류 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-500">분류</label>
          <select
            value={form.category_id}
            onChange={(e) => handleChange('category_id', e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
          >
            <option value="">미분류</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* 메모 */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-500">메모</label>
          <input
            type="text"
            value={form.memo}
            onChange={(e) => handleChange('memo', e.target.value)}
            placeholder="메모 (선택)"
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
          />
        </div>

        {/* 저장 */}
        <button
          onClick={handleSubmit}
          disabled={!form.amount || saving}
          className="mt-2 w-full rounded-xl bg-emerald-600 py-3.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        >
          {saving ? '저장 중...' : '저장'}
        </button>
      </div>
    </div>
  );
}
