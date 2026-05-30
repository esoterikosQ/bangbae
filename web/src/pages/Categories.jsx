import { useState, useEffect } from 'react';
import { getCategories, createCategory, updateCategory, deleteCategory } from '../api';

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    setLoading(true);
    try {
      const res = await getCategories();
      setCategories(res.data);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    await createCategory({ name: newName.trim() });
    setNewName('');
    await loadCategories();
  };

  const handleUpdate = async (id) => {
    if (!editName.trim()) return;
    await updateCategory(id, { name: editName.trim() });
    setEditingId(null);
    await loadCategories();
  };

  const handleDelete = async (id) => {
    if (!confirm('이 분류를 삭제하시겠습니까?')) return;
    try {
      await deleteCategory(id);
      await loadCategories();
    } catch (err) {
      alert('삭제 실패: 이 분류에 거래가 연결되어 있을 수 있습니다.');
    }
  };

  const startEdit = (cat) => {
    setEditingId(cat.id);
    setEditName(cat.name);
  };

  return (
    <div className="py-4">
      <h2 className="mb-6 text-lg font-semibold text-slate-100">지출 분류 관리</h2>

      {/* 새 분류 추가 */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          placeholder="새 분류 이름"
          className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-500"
        />
        <button
          onClick={handleCreate}
          disabled={!newName.trim()}
          className="rounded-xl bg-emerald-600 px-5 py-3 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
        >
          추가
        </button>
      </div>

      {/* 분류 목록 */}
      {loading ? (
        <p className="py-8 text-center text-slate-500">불러오는 중...</p>
      ) : categories.length === 0 ? (
        <p className="py-8 text-center text-slate-500">등록된 분류가 없습니다</p>
      ) : (
        <div className="space-y-2">
          {categories.map((cat) => (
            <div
              key={cat.id}
              className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3"
            >
              {editingId === cat.id ? (
                <div className="flex flex-1 gap-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleUpdate(cat.id)}
                    autoFocus
                    className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-emerald-500"
                  />
                  <button
                    onClick={() => handleUpdate(cat.id)}
                    className="text-sm text-emerald-400 hover:text-emerald-300"
                  >
                    저장
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="text-sm text-slate-500 hover:text-slate-300"
                  >
                    취소
                  </button>
                </div>
              ) : (
                <>
                  <span
                    className="flex-1 text-sm text-slate-200 cursor-pointer"
                    onClick={() => startEdit(cat)}
                  >
                    {cat.name}
                  </span>
                  <button
                    onClick={() => handleDelete(cat.id)}
                    className="ml-2 text-xs text-slate-600 hover:text-rose-400"
                  >
                    삭제
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
