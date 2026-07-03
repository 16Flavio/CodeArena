import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, Plus, Trash2, Save, Code2, ArrowLeft,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../AuthContext';
import { useConfirm } from '../components/Confirm';
import {
  adminLearnListWidgets, adminLearnCreateWidget, adminLearnGetWidget,
  adminLearnUpdateWidget, adminLearnDeleteWidget,
} from '../api';
import CustomWidget from '../components/learning/CustomWidget';
import * as widgetsStore from '../components/learning/widgetsStore';
import { extractErrorMessage } from '../utils/apiError';

const STARTER_TEMPLATE = `<!-- Le widget reçoit ses paramètres dans window.__params -->
<canvas id="cv" width="600" height="200"
        style="width:100%;height:auto;background:#0f172a;border-radius:8px"></canvas>
<script>
  const ctx = document.getElementById('cv').getContext('2d');
  const data = JSON.parse(window.__params.data || '[10,30,50,80,40,20]');
  const max = Math.max(...data, 1);
  const w = 600 / data.length;
  data.forEach((v, i) => {
    const h = (v / max) * 180;
    ctx.fillStyle = '#a855f7';
    ctx.fillRect(i * w + 4, 200 - h, w - 8, h);
  });
</script>`;

const STARTER_PARAMS_SCHEMA = JSON.stringify(
  [{ name: 'data', description: 'Tableau JSON à visualiser', example: '[5,10,3,8]' }],
  null, 2,
);

const STARTER_EXAMPLE_PARAMS = JSON.stringify({ data: '[5,10,3,8]' }, null, 2);

function slugifyName(s) {
  return (s || '')
    .toLowerCase().trim()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/(^-|-$)+/g, '')
    .slice(0, 80) || 'widget';
}

export default function AdminLearningWidgets() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const confirm = useConfirm();

  const [widgets, setWidgets] = useState([]);
  const [editing, setEditing] = useState(null);  // current widget being edited
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.is_admin) navigate('/dashboard');
  }, [user, navigate]);

  const reload = async () => {
    try {
      const r = await adminLearnListWidgets();
      setWidgets(r.data || []);
      setLoading(false);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.learningWidgets.toastFailed')));
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await adminLearnListWidgets();
        if (!cancelled) {
          setWidgets(r.data || []);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          toast.error(extractErrorMessage(err, t('admin.learningWidgets.toastFailed')));
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [t]);

  const handleCreate = async () => {
    const title = window.prompt(t('admin.learningWidgets.promptTitle'));
    if (!title) return;
    const name = slugifyName(title);
    try {
      const r = await adminLearnCreateWidget({
        name, title_fr: title, title_en: title,
        description_fr: '', description_en: '',
        html_template: STARTER_TEMPLATE,
        params_schema: STARTER_PARAMS_SCHEMA,
        example_params: STARTER_EXAMPLE_PARAMS,
        is_published: false,
      });
      toast.success(t('admin.learningWidgets.toastCreated'));
      setEditing(r.data);
      reload();
      widgetsStore.invalidate();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.learningWidgets.toastFailed')));
    }
  };

  const handleEdit = async (w) => {
    try {
      const r = await adminLearnGetWidget(w.id);
      setEditing(r.data);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.learningWidgets.toastFailed')));
    }
  };

  const handleSave = async () => {
    if (!editing) return;
    try {
      const r = await adminLearnUpdateWidget(editing.id, {
        name: editing.name,
        title_fr: editing.title_fr,
        title_en: editing.title_en,
        description_fr: editing.description_fr || '',
        description_en: editing.description_en || '',
        html_template: editing.html_template || '',
        params_schema: editing.params_schema || '',
        example_params: editing.example_params || '',
        is_published: !!editing.is_published,
      });
      toast.success(t('admin.learningWidgets.toastSaved'));
      setEditing(r.data);
      reload();
      widgetsStore.invalidate();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.learningWidgets.toastFailed')));
    }
  };

  const handleDelete = async (w) => {
    const ok = await confirm({
      message: t('admin.learningWidgets.confirmDelete', { name: w.name }),
      danger: true,
    });
    if (!ok) return;
    try {
      await adminLearnDeleteWidget(w.id);
      toast.success(t('admin.learningWidgets.toastDeleted'));
      if (editing?.id === w.id) setEditing(null);
      reload();
      widgetsStore.invalidate();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.learningWidgets.toastFailed')));
    }
  };

  // Parse example_params for the live preview. If the JSON is malformed
  // we silently fall back to {} so the preview still renders.
  let previewParams = {};
  try { previewParams = JSON.parse(editing?.example_params || '{}') || {}; }
  catch { previewParams = {}; }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/admin/learning')}
            className="text-sm text-violet-600 hover:text-violet-500 inline-flex items-center gap-1 dark:text-violet-400"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            {t('admin.learningWidgets.backToLearning')}
          </button>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3 mt-2">
            <Sparkles className="w-8 h-8 text-violet-500" />
            {t('admin.learningWidgets.title')}
          </h1>
        </div>
        <button onClick={handleCreate} className="btn-primary inline-flex items-center gap-2">
          <Plus className="w-4 h-4" />
          {t('admin.learningWidgets.newWidget')}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Widget list */}
        <div className="lg:col-span-3 space-y-2">
          {widgets.length === 0 && (
            <div className="glass-card p-6 text-center text-sm text-slate-500 dark:text-gray-400">
              {t('admin.learningWidgets.empty')}
            </div>
          )}
          {widgets.map((w) => (
            <div
              key={w.id}
              className={`glass-card p-3 cursor-pointer transition-colors ${
                editing?.id === w.id ? 'border-violet-300 bg-violet-50 dark:bg-violet-500/10' : ''
              }`}
              onClick={() => handleEdit(w)}
            >
              <div className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-slate-900 dark:text-white truncate">
                    {w.title_fr || w.title_en || w.name}
                  </div>
                  <code className="text-xs text-violet-600 dark:text-violet-400">
                    :::{w.name}
                  </code>
                </div>
                {!w.is_published && (
                  <span className="text-[10px] uppercase text-slate-400">
                    {t('admin.learningWidgets.draft')}
                  </span>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(w); }}
                  className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Editor */}
        <div className="lg:col-span-9">
          {!editing ? (
            <div className="glass-card p-12 text-center">
              <Code2 className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 dark:text-gray-400">
                {t('admin.learningWidgets.selectHint')}
              </p>
            </div>
          ) : (
            <div className="glass-card p-4 space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  className="input-field flex-1"
                  placeholder={t('admin.learningWidgets.titleFr')}
                  value={editing.title_fr || ''}
                  onChange={(e) => setEditing((p) => ({ ...p, title_fr: e.target.value }))}
                />
                <input
                  className="input-field flex-1"
                  placeholder={t('admin.learningWidgets.titleEn')}
                  value={editing.title_en || ''}
                  onChange={(e) => setEditing((p) => ({ ...p, title_en: e.target.value }))}
                />
                <button
                  onClick={() => setEditing((p) => ({ ...p, is_published: !p.is_published }))}
                  className={`text-sm px-3 py-1.5 rounded-lg ${editing.is_published
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                    : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-gray-400'}`}
                >
                  {editing.is_published ? t('admin.learningWidgets.published') : t('admin.learningWidgets.draft')}
                </button>
                <button onClick={handleSave} className="btn-primary inline-flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  {t('admin.learningWidgets.save')}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                <input
                  className="input-field"
                  placeholder={t('admin.learningWidgets.namePlaceholder')}
                  value={editing.name || ''}
                  onChange={(e) => setEditing((p) => ({ ...p, name: e.target.value }))}
                />
                <span className="text-slate-400 dark:text-gray-500 self-center">
                  :::{editing.name}{'{...}'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <textarea
                  className="input-field text-sm h-20"
                  placeholder={t('admin.learningWidgets.descFr')}
                  value={editing.description_fr || ''}
                  onChange={(e) => setEditing((p) => ({ ...p, description_fr: e.target.value }))}
                />
                <textarea
                  className="input-field text-sm h-20"
                  placeholder={t('admin.learningWidgets.descEn')}
                  value={editing.description_en || ''}
                  onChange={(e) => setEditing((p) => ({ ...p, description_en: e.target.value }))}
                />
              </div>

              {/* Code editor + live preview */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400 mb-1 block">
                    {t('admin.learningWidgets.htmlTemplate')}
                  </label>
                  <textarea
                    className="input-field font-mono text-xs h-[400px] resize-none"
                    value={editing.html_template || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, html_template: e.target.value }))}
                    spellCheck={false}
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400 mb-1 block">
                    {t('admin.learningWidgets.preview')}
                  </label>
                  <div className="border border-gray-200 rounded-lg overflow-hidden h-[400px] dark:border-slate-700/50">
                    <CustomWidget
                      template={editing.html_template || ''}
                      height="100%"
                      __title={editing.title_fr || editing.name}
                      {...previewParams}
                    />
                  </div>
                </div>
              </div>

              {/* Schemas */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400 mb-1 block">
                    {t('admin.learningWidgets.paramsSchema')}
                  </label>
                  <textarea
                    className="input-field font-mono text-xs h-32"
                    placeholder='[{"name":"data","description":"...","example":"[1,2,3]"}]'
                    value={editing.params_schema || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, params_schema: e.target.value }))}
                    spellCheck={false}
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400 mb-1 block">
                    {t('admin.learningWidgets.exampleParams')}
                  </label>
                  <textarea
                    className="input-field font-mono text-xs h-32"
                    placeholder='{"data":"[1,2,3]"}'
                    value={editing.example_params || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, example_params: e.target.value }))}
                    spellCheck={false}
                  />
                </div>
              </div>

              <p className="text-xs text-slate-500 dark:text-gray-400">
                {t('admin.learningWidgets.helpHint')}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
