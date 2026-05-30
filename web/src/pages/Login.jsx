import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authLogin } from '../api';

export default function Login() {
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRefs = useRef([]);
  const navigate = useNavigate();

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (index, value) => {
    if (!/^\d*$/.test(value)) return;

    const newDigits = [...digits];
    newDigits[index] = value.slice(-1);
    setDigits(newDigits);
    setError('');

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // 6자리 모두 입력되면 자동 로그인
    if (index === 5 && value) {
      const code = newDigits.join('');
      if (code.length === 6) submit(code);
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    const newDigits = [...digits];
    for (let i = 0; i < pasted.length; i++) {
      newDigits[i] = pasted[i];
    }
    setDigits(newDigits);
    if (pasted.length === 6) submit(pasted);
  };

  const submit = async (code) => {
    setLoading(true);
    setError('');
    try {
      const res = await authLogin(code);
      localStorage.setItem('token', res.data.token);
      navigate('/', { replace: true });
    } catch {
      setError('인증 코드가 올바르지 않습니다');
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="mb-10 text-center">
        <h1 className="mb-2 text-3xl font-bold tracking-tight text-slate-50">
          지출 관리
        </h1>
        <p className="text-sm text-slate-500">인증 코드 6자리를 입력하세요</p>
      </div>

      <div className="flex gap-2.5" onPaste={handlePaste}>
        {digits.map((d, i) => (
          <input
            key={i}
            ref={(el) => (inputRefs.current[i] = el)}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={d}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            disabled={loading}
            className={`h-14 w-11 rounded-lg border bg-slate-900 text-center text-xl font-semibold text-slate-50 outline-none transition-all
              ${error ? 'border-rose-500' : 'border-slate-700 focus:border-emerald-500'}
              disabled:opacity-50`}
          />
        ))}
      </div>

      {error && (
        <p className="mt-4 text-sm text-rose-400">{error}</p>
      )}

      {loading && (
        <p className="mt-4 text-sm text-slate-500">확인 중...</p>
      )}
    </div>
  );
}
