import { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { scanReceipt, confirmReceipt } from '../api';

function formatAmount(amount) {
  if (amount == null) return '-';
  return Math.abs(amount).toLocaleString() + '원';
}

export default function ReceiptScan() {
  const { txId } = useParams();
  const navigate = useNavigate();
  const cameraRef = useRef();
  const fileRef = useRef();

  const [step, setStep] = useState('upload');  // upload → processing → review
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [items, setItems] = useState([]);
  const [discounts, setDiscounts] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleFile = async (file) => {
    if (!file) return;

    // 미리보기
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);

    // OCR + LLM 처리
    setStep('processing');
    setError('');
    try {
      const res = await scanReceipt(file);
      setResult(res.data);
      setItems(res.data.items || []);
      setDiscounts(res.data.discounts || []);
      setStep('review');
    } catch (err) {
      setError('영수증 처리에 실패했습니다: ' + (err.response?.data?.detail || err.message));
      setStep('upload');
    }
  };

  const handleCapture = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const updateItem = (index, field, value) => {
    setItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const removeItem = (index) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const addItem = () => {
    setItems((prev) => [...prev, { item_name: '', unit_price: 0, quantity: 1, item_total: 0 }]);
  };

  const handleConfirm = async () => {
    setSaving(true);
    try {
      await confirmReceipt({
        transaction_id: parseInt(txId),
        items: items.map((item) => ({
          item_name: item.item_name,
          unit_price: item.unit_price ? parseInt(item.unit_price) : null,
          quantity: item.quantity ? parseInt(item.quantity) : 1,
          item_total: item.item_total ? parseInt(item.item_total) : null,
        })),
        discounts: discounts.map((d) => ({
          description: d.description,
          amount: parseInt(d.amount),
        })),
      });
      navigate('/transactions');
    } catch (err) {
      setError('저장 실패: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="py-4">
      <h2 className="mb-6 text-lg font-semibold text-slate-100">영수증 스캔</h2>

      {/* 업로드 단계 */}
      {step === 'upload' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => cameraRef.current?.click()}
              className="rounded-2xl border-2 border-dashed border-slate-700 py-12 text-center hover:border-slate-500"
            >
              <span className="text-4xl">📷</span>
              <p className="mt-3 text-sm text-slate-400">카메라 촬영</p>
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              className="rounded-2xl border-2 border-dashed border-slate-700 py-12 text-center hover:border-slate-500"
            >
              <span className="text-4xl">🖼️</span>
              <p className="mt-3 text-sm text-slate-400">이미지 선택</p>
            </button>
          </div>
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleCapture}
            className="hidden"
          />
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={handleCapture}
            className="hidden"
          />
          {error && <p className="text-sm text-rose-400">{error}</p>}
        </div>
      )}

      {/* 처리 중 */}
      {step === 'processing' && (
        <div className="py-16 text-center">
          {preview && (
            <img src={preview} alt="영수증" className="mx-auto mb-6 max-h-48 rounded-xl opacity-50" />
          )}
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
          <p className="text-sm text-slate-400">영수증을 분석하고 있습니다...</p>
          <p className="mt-1 text-xs text-slate-600">OCR + AI 분석 중 (최대 2분)</p>
        </div>
      )}

      {/* 리뷰 단계 */}
      {step === 'review' && (
        <div className="space-y-4">
          {/* OCR 원문 토글 */}
          {result?.raw_text && (
            <details className="rounded-xl bg-slate-900 px-4 py-3">
              <summary className="cursor-pointer text-xs text-slate-500">OCR 원문 보기</summary>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-slate-400">
                {result.raw_text}
              </pre>
            </details>
          )}

          {/* 거래처 / 총계 요약 */}
          <div className="rounded-xl bg-slate-900 px-4 py-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">거래처</span>
              <span className="text-slate-200">{result?.merchant || '미상'}</span>
            </div>
            {result?.total && (
              <div className="mt-1 flex justify-between text-sm">
                <span className="text-slate-400">총계</span>
                <span className="font-semibold text-slate-100">{formatAmount(result.total)}</span>
              </div>
            )}
            {result?.paid && result.paid !== result.total && (
              <div className="mt-1 flex justify-between text-sm">
                <span className="text-slate-400">실결제</span>
                <span className="font-semibold text-emerald-400">{formatAmount(result.paid)}</span>
              </div>
            )}
          </div>

          {/* 품목 목록 (편집 가능) */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              품목 ({items.length}개)
            </h3>
            <div className="space-y-2">
              {items.map((item, i) => (
                <div key={i} className="rounded-xl bg-slate-900 px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <input
                      type="text"
                      value={item.item_name}
                      onChange={(e) => updateItem(i, 'item_name', e.target.value)}
                      className="flex-1 border-b border-slate-700 bg-transparent pb-1 text-sm text-slate-200 outline-none focus:border-emerald-500"
                    />
                    <button
                      onClick={() => removeItem(i)}
                      className="text-xs text-slate-600 hover:text-rose-400"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-600">단가</label>
                      <input
                        type="number"
                        value={item.unit_price || ''}
                        onChange={(e) => updateItem(i, 'unit_price', e.target.value)}
                        className="w-full rounded bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-600">수량</label>
                      <input
                        type="number"
                        value={item.quantity || ''}
                        onChange={(e) => updateItem(i, 'quantity', e.target.value)}
                        className="w-full rounded bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-600">합계</label>
                      <input
                        type="number"
                        value={item.item_total || ''}
                        onChange={(e) => updateItem(i, 'item_total', e.target.value)}
                        className="w-full rounded bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={addItem}
              className="mt-2 w-full rounded-xl border border-dashed border-slate-700 py-2 text-xs text-slate-500 hover:border-slate-500"
            >
              + 품목 추가
            </button>
          </div>

          {/* 할인 내역 */}
          {discounts.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                할인
              </h3>
              {discounts.map((d, i) => (
                <div key={i} className="flex justify-between rounded-xl bg-slate-900 px-4 py-3 text-sm">
                  <span className="text-slate-300">{d.description}</span>
                  <span className="text-rose-400">-{formatAmount(d.amount)}</span>
                </div>
              ))}
            </div>
          )}

          {error && <p className="text-sm text-rose-400">{error}</p>}

          {/* 버튼 */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleConfirm}
              disabled={saving || items.length === 0}
              className="flex-1 rounded-xl bg-emerald-600 py-3 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
            >
              {saving ? '저장 중...' : '확인 및 저장'}
            </button>
            <button
              onClick={() => { setStep('upload'); setResult(null); setItems([]); }}
              className="rounded-xl bg-slate-800 px-5 py-3 text-sm text-slate-400"
            >
              다시 스캔
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
